# options_flow_alpha

A quantitative research pipeline for generating and backtesting options flow signals. Ingests daily options chain data, computes Greeks-weighted flow imbalance and put/call skew signals, and measures predictive power via Information Coefficient (IC) and annualized Sharpe ratio across multiple forward return horizons.

---

## Motivation

Options flow data encodes directional conviction in a way that equity price data doesn't. A large delta-weighted call position tells you an institutional participant is making a sized directional bet — not just hedging. This project builds a systematic pipeline to capture that signal, measure its decay curve, and evaluate it as a long/short strategy.

---

## Pipeline

```
collect.py      →    validate.py    →    enrich.py
  options chain        drop bad           DTE, moneyness,
  ingestion            ticks + IV         dollar volume, delta

       ↓
  signals.py     →    backtest.py    →    results/
  flow imbalance       IC, Sharpe,        ic_results.parquet
  + skew signal        decay curve        signals.parquet
```

Run the full pipeline for any date range:

```bash
python pipeline.py --start 2026-01-01 --end 2026-05-08
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
├── collect.py        # Options chain ingestion, parquet storage
├── validate.py       # IV filtering, zero-volume removal, spread flagging
├── enrich.py         # DTE, moneyness, dollar volume, Black-Scholes delta
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
| [yfinance](https://github.com/ranaroussi/yfinance) | Options chain + OHLCV price data | Free |
| [Databento](https://databento.com) | Historical options snapshots with Greeks (in progress) | Free tier available |
| [Unusual Whales API](https://unusualwhales.com) | Live flow data | Free tier available |

> **Data limitation:** The current yfinance implementation returns the current options chain snapshot regardless of the requested historical date. This means backtesting across a historical date range produces repeated snapshots rather than true historical data — the pipeline architecture and signal logic are correct, but IC and Sharpe results are not meaningful until the Databento integration is complete. Forward testing (collecting today's snapshot daily going forward) produces genuine time-series data immediately.

---

## Roadmap

- [x] Options chain ingestion pipeline
- [x] Validation and enrichment layer
- [x] Delta-weighted flow imbalance signal
- [x] Put/call skew signal
- [x] IC and Sharpe backtesting framework
- [ ] Databento integration for true historical data
- [ ] Signal decay curve visualization
- [ ] Live signal feed into options_dashboard

---

## Requirements

```bash
pip install -r requirements.txt
```

---

## Related work

This project extends [options_dashboard](https://github.com/ifrancis2313/options_dashboard) — adding a signal research layer on top of the existing pricing infrastructure. The signal output is designed to feed directly into the live signal runner as a next step.
