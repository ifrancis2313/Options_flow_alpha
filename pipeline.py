import argparse
import pandas as pd
from pathlib import Path
import logging

from collect import collect , RAW_DIR
from validate import validate
from enrich import enrich
from signals import compute_signals
from backtest import add_forward_returns, compute_ic, compute_sharpe, compute_decay_curve, HORIZONS

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(name)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

SIGNALS_DIR = Path("data/signals")
RESULTS_DIR = Path("data/results")


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Run options flow pipeline')
    parser.add_argument('--start', type=str, required=True, help='Start date (YYYY-MM-DD)')
    parser.add_argument('--end', type=str, required=True, help='End date (YYYY-MM-DD)')
    args = parser.parse_args()
    return args

def load_prices(start: str, end: str) -> pd.DataFrame:
    """Load price data for the date range from parquet."""
    df = pd.read_parquet(Path('data/raw/prices/prices.parquet'))
    df = df[(df['DataDate'] >= pd.to_datetime(start)) & (df['DataDate'] <= pd.to_datetime(end))]
    return df


def run_collection(start: str, end: str) -> pd.DataFrame:
    """Collect, validate and enrich data for every business day in range."""
    dt_range = pd.bdate_range(start=start, end=end)
    frames = []
    for date in dt_range:
        collect(date)  # saves to disk
        df = pd.read_parquet(RAW_DIR / f"date={date.strftime('%Y-%m-%d')}" / "options.parquet")  # load it back
        df = validate(df)  # clean it
        df = enrich(df)  # enrich it
        frames.append(df)  # accumulate
    result = pd.concat(frames, ignore_index=True)
    logger.info(f"run_collection: {len(result)} total rows collected")
    return result


def run_pipeline(args) -> None:
    """Main pipeline orchestrator."""
    df = run_collection(args.start, args.end)
    signals = compute_signals(df)
    SIGNALS_DIR.mkdir(parents=True, exist_ok=True)
    signals.to_parquet(SIGNALS_DIR / "signals.parquet")
    prices = load_prices(args.start, args.end)
    prices = add_forward_returns(prices, HORIZONS)
    ic = compute_decay_curve(signals, prices)
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    ic.to_parquet(RESULTS_DIR / "ic_results.parquet")
    for signal in ['flow_imbalance', 'skew']:
        sharpe = compute_sharpe(signals, prices, signal, horizon=1)
        logger.info(f"Sharpe {signal}: {sharpe:.3f}")

if __name__ == "__main__":
    args = parse_args()
    run_pipeline(args)