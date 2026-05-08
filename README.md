# options_flow_alpha

A quantitative research pipeline for generating and backtesting options flow signals. Ingests daily options chain data, computes Greeks-weighted flow imbalance and put/call skew signals, and measures predictive power via Information Coefficient (IC) and annualized Sharpe ratio across multiple forward return horizons.

---

## Motivation

Options flow data encodes directional conviction in a way that equity price data doesn't. A large delta-weighted call position tells you an institutional participant is making a sized directional bet — not just hedging. This project builds a systematic pipeline to capture that signal, measure its decay curve, and evaluate it as a long/short strategy.

---

## Pipeline

```
collect.py      →    validate.py    →    enrich.py
  CBOE bulk            drop bad           DTE, moneyness,
  options data         ticks + IV         dollar volume

       ↓
  signals.py     →    backtest.py    →    results/
  flow imbalance       IC, Sharpe,        ic_results.parquet
  + skew signal        decay curve        signals.parquet
```

Run the full pipeline for any date range:

```bash
python pipeline.py --start 2023-01-01 --end 2024-01-01
```

---

## Signals

### Delta-weighted flow imbalance

Measures net directional conviction in options flow, weighted by delta to control for moneyness:

```
flow_imbalance = Σ(call_delta × volume) - Σ(put_delta × volume)
```

A far OTM contract with delta 0.05 contributes 10x less than an ATM contract with delta 0.50. This filters noise from speculative lottery-ticket flow and isolates contracts where participants have real directional exposure.

### Put/call skew

Measures relative demand for downside protection vs upside participation, normalized by ATM IV as a baseline:

```
skew = (mean OTM put IV - mean OTM call IV) / mean ATM IV
```

Widening skew signals elevated institutional hedging demand — historically a bearish leading indicator.

---

## Evaluation

Signals are evaluated using:

- **Information Coefficient (IC)** — Spearman correlation between signal and forward returns at 1, 5, 10, and 21-day horizons. IC > 0.05 is considered meaningful in practice.
- **Signal decay curve** — IC plotted across horizons to identify when the edge decays. Determines optimal trading frequency and holding period.
- **Annualized Sharpe ratio** — long/short portfolio constructed by ranking tickers into terciles by signal each day. Long top tercile, short bottom tercile.

---

## Project structure

```
options_flow_alpha/
├── collect.py        # CBOE bulk file ingestion, parquet storage
├── validate.py       # IV filtering, zero-volume removal, spread flagging
├── enrich.py         # DTE, moneyness, dollar volume computation
├── signals.py        # Flow imbalance + skew signal construction
├── backtest.py       # IC, Sharpe, decay curve
├── pipeline.py       # End-to-end orchestrator with CLI
└── data/
    ├── raw/
    │   ├── options/  # Partitioned by date=YYYY-MM-DD/
    │   └── prices/   # Daily OHLCV per ticker
    ├── signals/      # Computed signal output
    └── results/      # IC and Sharpe results
```

---

## Data sources

| Source | Usage | Cost |
|--------|-------|------|
| [CBOE bulk files](https://www.cboe.com/us/options/market_statistics/historical_data/) | Historical options chain (2+ years) | Free |
| [Unusual Whales API](https://unusualwhales.com) | Live flow data with Greeks | Free tier available |
| yfinance | Daily OHLCV price data | Free |

---

## Requirements

```bash
pip install pandas numpy scipy requests yfinance pyarrow
```

---

## Related work

This project extends [options_dashboard](https://github.com/ifrancis2313/options_dashboard) — adding a signal research layer on top of the existing pricing infrastructure. The signal output is designed to feed directly into the live signal runner as a next step.
