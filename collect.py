import yfinance as yf
import pandas as pd
from pathlib import Path
from datetime import date
import logging

logger = logging.getLogger(__name__)

RAW_DIR = Path("data/raw/options")

TICKERS = [
    "SPY", "QQQ", "AAPL", "NVDA", "TSLA",
    "MSFT", "AMZN", "AMD", "META", "GOOG"
]


def download_raw(trade_date: date) -> pd.DataFrame:
    """Download options chain for all tickers via yfinance."""
    frames = []
    for ticker in TICKERS:
        tk = yf.Ticker(ticker)
        for expiry in tk.options:
            chain = tk.option_chain(expiry)
            calls = chain.calls.copy()
            calls['PutCall'] = 'call'
            puts = chain.puts.copy()
            puts['PutCall'] = 'put'
            combined = pd.concat([calls, puts], ignore_index=True)
            combined['UnderlyingSymbol'] = ticker
            combined['DataDate'] = trade_date
            combined['Expiration'] = pd.to_datetime(expiry)  # ← add this
            combined['Underlying'] = tk.fast_info['lastPrice']
            frames.append(combined)
    df = pd.concat(frames, ignore_index=True)
    logger.info(f"Downloaded {len(df)} rows for {trade_date}")
    return df


def filter_tickers(df: pd.DataFrame, tickers: list[str]) -> pd.DataFrame:
    """Keep only rows where the underlying is in our ticker list."""
    return df[df['UnderlyingSymbol'].isin(tickers)]


def save_parquet(df: pd.DataFrame, trade_date: date) -> Path:
    """Save filtered DataFrame to data/raw/options/date=YYYY-MM-DD/options.parquet"""
    date_str = trade_date.strftime("%Y-%m-%d")
    out_path = RAW_DIR / f"date={date_str}" / "options.parquet"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(out_path)
    return out_path


def collect(trade_date: date) -> None:
    """Main entry point: download, filter, save for one trading date."""
    df = download_raw(trade_date)
    df = filter_tickers(df, TICKERS)
    out_path = save_parquet(df, trade_date)
    logger.info(f"Saved to {out_path}")


if __name__ == "__main__":
    from datetime import date
    collect(date.today())