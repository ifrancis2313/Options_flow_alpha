import pandas as pd
import logging
import numpy as np
from scipy.stats import norm

logger = logging.getLogger(__name__)


def add_dte(df: pd.DataFrame) -> pd.DataFrame:
    """Add 'dte' column: days between trade date and expiry."""
    df['dte'] = (df['Expiration'] - pd.to_datetime(df['DataDate'])).dt.days
    logger.info(f"add_dte: dte range {df['dte'].min()} to {df['dte'].max()} days")
    return df


def add_moneyness(df: pd.DataFrame) -> pd.DataFrame:
    """Add 'moneyness' column: underlying_price / strike."""
    df['moneyness'] = df['Underlying'] / df['strike']
    logger.info(f"add_moneyness: mean moneyness {df['moneyness'].mean():.3f}")
    return df


def add_dollar_volume(df: pd.DataFrame) -> pd.DataFrame:
    """Add 'dollar_volume' column: contract volume * midpoint * 100."""
    df['dollar_volume'] = df['volume'] * ((df['bid']+df['ask'])/2) * 100
    logger.info(f"add_dollar_volume: mean dollar volume ${df['dollar_volume'].mean():,.0f}")
    return df


def add_delta(df: pd.DataFrame, r: float = 0.05) -> pd.DataFrame:
    """Compute Black-Scholes delta for each contract and add as 'Delta' column."""
    T = df['dte']/252
    d1 = ((np.log(df['Underlying']/df['strike'])+(r+df['impliedVolatility']**2/2)*T)/(df['impliedVolatility']*np.sqrt(T)))
    call_delta = norm.cdf(d1)
    put_delta = norm.cdf(d1)-1
    df['Delta'] = np.where(df['PutCall'] == 'call', call_delta, put_delta)
    logger.info(f"add_delta: mean delta {df['Delta'].mean():.3f}")
    return df


def enrich(df: pd.DataFrame) -> pd.DataFrame:
    """Add all enrichment columns and return."""
    df = add_dte(df)
    df = add_moneyness(df)
    df = add_dollar_volume(df)
    df = add_delta(df)
    return df


if __name__ == "__main__":
    from pathlib import Path
    df = pd.read_parquet(Path("data/raw/options/date=2026-05-08/options.parquet"))
    df = enrich(df)
    print(df[['dte', 'moneyness', 'dollar_volume']].describe())