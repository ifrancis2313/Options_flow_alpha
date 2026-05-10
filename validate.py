import pandas as pd
import logging

logger = logging.getLogger(__name__)

IV_MAX = 5.0      # 500% IV ceiling
SPREAD_MAX = 0.5  # 50% bid-ask spread threshold


def drop_zero_iv(df: pd.DataFrame) -> pd.DataFrame:
    """Drop rows where close price is zero — indicates bad tick."""
    before = len(df)
    df = df[df['close'] > 0]
    dropped = before - len(df)
    logger.info(f"drop_zero_iv: dropped {dropped} rows")
    return df


def drop_zero_volume(df: pd.DataFrame) -> pd.DataFrame:
    """Drop rows where volume is zero."""
    before = len(df)
    df = df[df['volume'] > 0]
    dropped = before - len(df)
    logger.info(f"drop_zero_volume: dropped {dropped} rows")
    return df

def flag_wide_spreads(df: pd.DataFrame) -> pd.DataFrame:
    """Add a boolean column 'wide_spread' where bid-ask spread exceeds SPREAD_MAX."""
    df['spread_pct'] = (df['ask'] - df['bid']) / df['ask']
    df['wide_spread'] = df['spread_pct'] > SPREAD_MAX
    logger.info(f"flag_wide_spreads: flagged {df['wide_spread'].sum()} wide spread contracts")
    return df


def validate(df: pd.DataFrame) -> pd.DataFrame:
    """Run all validation checks and return cleaned DataFrame."""
    df = drop_zero_iv(df)
    df = drop_zero_volume(df)
    df = flag_wide_spreads(df)
    return df


if __name__ == "__main__":
    from pathlib import Path
    df = pd.read_parquet(Path("data/raw/options/date=2026-01-02/options.parquet"))
    df = validate(df)
    print(df.shape)