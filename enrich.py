import pandas as pd
import logging
import numpy as np
from scipy.stats import norm
from scipy.optimize import brentq

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

def bs_price(S, K, T, r, sigma, option_type):
    """Black-Scholes option price."""
    if T <= 0 or sigma <= 0:
        return 0.0
    d1 = (np.log(S/K) + (r + sigma**2/2) * T) / (sigma * np.sqrt(T))
    d2 = d1 - sigma * np.sqrt(T)
    if option_type == 'call':
        return S * norm.cdf(d1) - K * np.exp(-r * T) * norm.cdf(d2)
    else:
        return K * np.exp(-r * T) * norm.cdf(-d2) - S * norm.cdf(-d1)


def compute_iv(row, r=0.05):
    """Compute implied volatility for a single row using Brent's method."""
    try:
        S = row['Underlying']
        K = row['strike']
        T = row['dte'] / 252
        price = row['close']
        option_type = row['PutCall']
        if T <= 0 or price <= 0 or S <= 0 or K <= 0:
            return np.nan
        iv = brentq(
            lambda sigma: bs_price(S, K, T, r, sigma, option_type) - price,
            1e-6, 10.0, maxiter=100
        )
        return iv
    except:
        return np.nan


def add_iv(df: pd.DataFrame) -> pd.DataFrame:
    """Compute implied volatility for each contract and add as 'impliedVolatility'."""
    df['impliedVolatility'] = df.apply(compute_iv, axis=1)
    logger.info(f"add_iv: mean IV {df['impliedVolatility'].mean():.3f}, "
                f"nan count {df['impliedVolatility'].isna().sum()}")
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
    df = add_iv(df)
    df = add_delta(df)
    return df


if __name__ == "__main__":
    from pathlib import Path
    df = pd.read_parquet(Path("data/raw/options/date=2026-01-02/options.parquet"))
    df = enrich(df)
    print(df[['dte', 'moneyness', 'dollar_volume']].describe())