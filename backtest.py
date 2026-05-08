import pandas as pd
import numpy as np
from scipy import stats
import logging

logger = logging.getLogger(__name__)

HORIZONS = [1, 5, 10, 21]  # trading days forward


def add_forward_returns(prices: pd.DataFrame, horizons: list[int]) -> pd.DataFrame:
    """
    Add forward return columns to a prices DataFrame.
    prices has columns: DataDate, UnderlyingSymbol, close
    Returns same DataFrame with added columns: fwd_1d, fwd_5d, fwd_10d, fwd_21d
    """
    for h in horizons:
        prices[f'fwd_{h}'] = prices.groupby('UnderlyingSymbol')['close'].transform(
            lambda x, h=h: x.shift(-h) / x - 1
        )
    return prices


def compute_ic(signals: pd.DataFrame, prices: pd.DataFrame) -> pd.DataFrame:
    """
    Compute IC between each signal and each forward return horizon.
    Returns DataFrame with columns: horizon, signal, ic
    """
    merged = pd.merge(signals, prices, on=['UnderlyingSymbol','DataDate'])
    signal_cols = ['flow_imbalance', 'skew']
    results = []
    for signal in signal_cols:
        for h in HORIZONS:
            # drop NaNs for this specific pair
            pair = merged[[signal, f'fwd_{h}']].dropna()
            ic, pvalue = stats.spearmanr(pair[signal], pair[f'fwd_{h}'])
            results.append({'signal': signal,'horizon':h, 'ic': ic, 'pvalue': pvalue})
            logger.info(f"IC {signal} fwd_{h}d: {ic:.4f} (p={pvalue:.3f})")
    return pd.DataFrame(results)


def compute_sharpe(signals: pd.DataFrame, prices: pd.DataFrame,
                   signal_col: str, horizon: int = 1) -> float:
    """
    Compute annualized Sharpe ratio of a long/short portfolio based on signal ranking.
    """
    # rank tickers within each day
    merged = pd.merge(signals, prices, on=['UnderlyingSymbol','DataDate'])
    merged['rank'] = merged.groupby('DataDate')[signal_col].transform(
        lambda x: pd.qcut(x, q=3, labels=['bottom', 'mid', 'top'])
    )
    top = merged[merged['rank'] == 'top']
    bottom = merged[merged['rank'] == 'bottom']
    top_returns = top.groupby('DataDate')[f'fwd_{horizon}'].agg('mean')
    bottom_returns = bottom.groupby('DataDate')[f'fwd_{horizon}'].agg('mean')
    daily_pnl = top_returns - bottom_returns
    sharpe = daily_pnl.mean()/daily_pnl.std()*np.sqrt(252)
    logger.info(f"compute_sharpe: {signal_col} fwd_{horizon}d Sharpe={sharpe:.3f}")
    return sharpe



def compute_decay_curve(signals: pd.DataFrame, prices: pd.DataFrame) -> pd.DataFrame:
    """Compute IC at every horizon in HORIZONS for both signals. Returns DataFrame for plotting."""
    ic = compute_ic(signals, prices)
    logger.info(f"compute_decay_curve: IC range {ic['ic'].min():.4f} to {ic['ic'].max():.4f}")
    return ic


if __name__ == "__main__":
    from pathlib import Path
    signals = pd.read_parquet(Path("data/signals/signals.parquet"))
    prices = pd.read_parquet(Path("data/raw/prices/prices.parquet"))
    ic = compute_ic(signals, prices)
    print(ic)