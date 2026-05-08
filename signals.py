import pandas as pd
import logging

logger = logging.getLogger(__name__)

# OTM threshold: contracts with moneyness outside this range are considered OTM
OTM_CALL_MIN = 1.02   # call is OTM if strike > 2% above underlying
OTM_PUT_MAX = 0.98    # put is OTM if strike < 2% below underlying
ATM_BAND = 0.01       # ATM if moneyness within 1% of 1.0


def compute_flow_imbalance(df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute delta-weighted flow imbalance per ticker per day.
    Returns DataFrame with columns: DataDate, UnderlyingSymbol, flow_imbalance
    """
    df['delta_volume'] = (df['Delta']*df['volume'])
    calls = df[df['PutCall']=='call']
    puts = df[df['PutCall']=='put']
    call_flow = calls.groupby(['DataDate', 'UnderlyingSymbol']).agg(
        call_flow=('delta_volume', 'sum')
    ).reset_index()
    put_flow = puts.groupby(['DataDate', 'UnderlyingSymbol']).agg(
        put_flow=('delta_volume', 'sum')
    ).reset_index()
    result = pd.merge(call_flow, put_flow, on=['DataDate', 'UnderlyingSymbol'])
    result['flow_imbalance'] = result['call_flow'] - result['put_flow']
    logger.info(f"compute_flow_imbalance: {len(result)} ticker-days, mean={result['flow_imbalance'].mean():.2f} std={result['flow_imbalance'].std():.2f}")
    return result


def compute_skew(df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute put/call skew per ticker per day.
    skew = mean OTM put IV - mean OTM call IV, normalized by mean ATM IV
    Returns DataFrame with columns: DataDate, UnderlyingSymbol, skew
    """
    atm = df[(df['moneyness'] >= 0.99) & (df['moneyness'] <= 1.01)]
    calls = df[df['PutCall']=='call']
    puts = df[df['PutCall']=='put']
    otm_call = calls[calls['moneyness'] >= OTM_CALL_MIN]
    otm_put = puts[puts['moneyness'] <= OTM_PUT_MAX]
    otm_put_iv = otm_put.groupby(['DataDate', 'UnderlyingSymbol']).agg(
        otm_put_iv=('impliedVolatility', 'mean')
    ).reset_index()
    otm_call_iv = otm_call.groupby(['DataDate', 'UnderlyingSymbol']).agg(
        otm_call_iv=('impliedVolatility', 'mean')
    ).reset_index()
    atm_iv = atm.groupby(['DataDate', 'UnderlyingSymbol']).agg(
        atm_iv=('impliedVolatility', 'mean')
    ).reset_index()
    results = pd.merge(otm_put_iv, otm_call_iv, on=['DataDate', 'UnderlyingSymbol'])
    results = pd.merge(results, atm_iv, on=['DataDate', 'UnderlyingSymbol'])
    results['skew'] = (results['otm_put_iv'] - results['otm_call_iv']) / results['atm_iv']
    logger.info(f"compute_skew: {len(results)} ticker-days, mean={results['skew'].mean():.2f} std={results['skew'].std():.2f}")
    return results



def compute_signals(df: pd.DataFrame) -> pd.DataFrame:
    """Compute all signals and return merged DataFrame."""
    flow = compute_flow_imbalance(df)
    skew = compute_skew(df)
    df = pd.merge(flow, skew, on=['DataDate', 'UnderlyingSymbol'])
    return df


if __name__ == "__main__":
    from pathlib import Path
    from enrich import enrich
    df = pd.read_parquet(Path("data/raw/options/date=2026-05-08/options.parquet"))
    df = enrich(df)
    signals = compute_signals(df)
    print(signals.head())