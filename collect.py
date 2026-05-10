import databento as db
import pandas as pd
from pathlib import Path
from datetime import date
import logging
import os
import re
from dotenv import load_dotenv
import yfinance as yf

load_dotenv()
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(name)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

RAW_DIR = Path("data/raw/options")

TICKERS = [
    "SPY", "QQQ", "AAPL", "NVDA", "TSLA",
    "MSFT", "AMZN", "AMD", "META", "GOOG"
]


def get_client() -> db.Historical:
    api_key = os.getenv("DATABENTO_API_KEY")
    return db.Historical(api_key)


def parse_symbol(symbol: str) -> dict:
    """
    Parse OCC symbol string into components.
    Example: 'SPY   260206C00660000'
    Returns dict with keys: UnderlyingSymbol, Expiration, PutCall, strike
    """
    match = re.match(r'([A-Z]+)\s*(\d{6})([CP])(\d+)', symbol)

    if match:
        tick = match.group(1)
        expiry = match.group(2)
        pc = match.group(3)
        strike = match.group(4)
        comps = {
            'UnderlyingSymbol': tick,
            'Expiration': pd.to_datetime(expiry, format="%y%m%d"),
            'Strike': int(strike) / 1000,
            'PutCall': 'call' if pc == 'C' else 'put',
        }
        return comps


def download_raw(trade_date: date, tickers: list[str]) -> pd.DataFrame:
    """Download options chain for tickers via Databento for a single date."""
    client = get_client()
    db_tickers = [f"{t}.OPT" for t in tickers]
    start = trade_date.strftime("%Y-%m-%d")
    end = (trade_date + pd.Timedelta(days=1)).strftime("%Y-%m-%d")
    data = client.timeseries.get_range(
        dataset = 'OPRA.PILLAR',
        symbols = db_tickers,
        schema='ohlcv-1d',
        start=start,
        end=end,
        stype_in='parent'
    )
    df = data.to_df().reset_index()
    parsed = df['symbol'].apply(parse_symbol)
    parsed_df = pd.DataFrame(parsed.tolist())
    df = pd.concat([df, parsed_df], axis=1)
    df['bid'] = df['close'] * 0.998
    df['ask'] = df['close'] * 1.002
    df['DataDate'] = trade_date
    df = df.sort_values('volume', ascending=False).drop_duplicates(
        subset=['UnderlyingSymbol', 'Expiration', 'Strike', 'PutCall'],
        keep='first'
    )
    prices = {t: yf.Ticker(t).fast_info['lastPrice'] for t in tickers}
    df['Underlying'] = df['UnderlyingSymbol'].map(prices)
    df = df.rename(columns={'Strike': 'strike'})
    logger.info(f'download_raw: Downloaded {len(df)} rows for {trade_date}')
    return df


def save_parquet(df: pd.DataFrame, trade_date: date) -> Path:
    """Save to data/raw/options/date=YYYY-MM-DD/options.parquet"""
    date_str = trade_date.strftime("%Y-%m-%d")
    out_path = RAW_DIR / f"date={date_str}" / "options.parquet"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(out_path)
    return out_path


def collect(trade_date: date) -> None:
    """Main entry point: download, save for one trading date."""
    df = download_raw(trade_date, TICKERS)
    out_path = save_parquet(df, trade_date)
    logger.info(f"Saved to {out_path}")


if __name__ == "__main__":
    collect(date(2026, 1, 2))