# Event Volatility Skew

**How did SPY's implied-volatility smile change around the September 18, 2024 Fed decision?** A real-data before/after study using option bid/ask snapshots on September 17 and 19 and the same October 18 expiry.

![Tests](https://github.com/yash9518/event-volatility-skew/actions/workflows/tests.yml/badge.svg)
![Event smile](reports/event_smile.png)

The event is the Fed's 50-basis-point rate cut, announced at 14:00 EDT on September 18. [Official statement](https://www.federalreserve.gov/newsevents/pressreleases/monetary20240918a.htm). The comparison describes changes; it cannot isolate the causal effect of the announcement from time decay or other news.

## Read first

- [Executed notebook](notebooks/research.ipynb)
- [Results and caveats](reports/RESULTS.md)
- [Learning guide](LEARNING.md)

## Run

Python 3.12+:

```bash
python -m venv .venv
# Windows PowerShell: .\.venv\Scripts\Activate.ps1
# macOS/Linux: source .venv/bin/activate
python -m pip install -e ".[dev,notebook]"
python -m event_skew.data
python -m event_skew
python -m pytest -q
jupyter lab notebooks/research.ipynb
```

Windows activation is optional: use `.\.venv\Scripts\python.exe` if needed. Tested top-level package versions are in `requirements-tested.txt`; this is not a full transitive lockfile. Unit tests use explicitly synthetic, known-volatility fixtures and require no network.

## Data that actually exists

The public DoltHub `post-no-preference/options` database contains historical snapshots at the two selected dates. `post-no-preference/stocks` supplies underlying closes. The downloader requests only SPY and the selected common expiry, validates nonempty responses and records exact SQL queries, retrieval time and hashes. It never replaces missing market observations with generated prices.

Raw third-party data stays in ignored `data/raw/`. Derived curves, coefficient tables, quote-audit counts and the source manifest are committed. A fresh clone needs `python -m event_skew.data` to run the market notebook. Source revisions can change a later download; saved checksums identify the run used here.

The default source branch is mutable `master`; `python -m event_skew.data --ref COMMIT_OR_BRANCH` supports a source reference if available in both databases. The manifest explicitly records the ref; it is not falsely labelled a pinned snapshot.

## Method

1. Keep positive, non-crossed bids and asks; estimate a forward from near-spot paired call/put midquotes.
2. Use OTM puts below the forward and OTM calls at/above it.
3. Reject bid below $0.05, relative bid/ask spread above 35%, and non-invertible quotes.
4. Invert a European Black forward model separately at bid, midpoint and ask.
5. Fit `IV(x) = a + b*x + c*x^2`, with `x=log(K/F)`, only in the common observed domain inside +/-0.10.
6. Compare ATM level `a`, local skew `b` and curvature `2c`, plus residual errors and rate sensitivity.

No extrapolation is used for the comparison. The fit is an unweighted local descriptive quadratic, **not an arbitrage-free pricing surface**. Bid/ask-fit sensitivity is not a confidence interval. Future extensions should test convexity in option-price space, liquidity weights and alternative smile parametrizations.

## Essential limitations

- **SPY options are American-style.** These are European-equivalent IVs, and put-call parity can be affected by early exercise and dividends. The forward absorbs approximate carry rather than assuming zero dividends.
- Both observations are before the September 20 SPY ex-distribution date, which lies within the option's remaining life. Carry remains relevant; the dividend date is not inside the September 17-19 observation interval.
- Daily source rows have no intraday timestamp, volume or open interest. Synchronization and execution quality cannot be established.
- Source chains are sparse. Counts and rejected quotes are reported, not hidden.
- The same expiry has 31 days left before the event and 29 afterward. It is not a constant-tenor comparison.
- A 5% continuous rate is an explicit assumption; +/-1 percentage-point sensitivity is exported.
- One event cannot establish causality or a profitable trading strategy.

## Capture future observations

Yahoo usually exposes **current**, not historical, option chains. To record a current snapshot for a future event:

```bash
python -m event_skew.data --snapshot-symbol SPY --expiry YYYY-MM-DD
```

Replace the placeholder with a currently listed expiration. The CSV includes retrieval UTC and provider last-trade times. Retrieval time is not quote time. Run manually before and after the chosen event; this command does not schedule anything or backfill history. The historical analysis's CSV contract differs from Yahoo snapshots, so adapt and validate columns before using snapshots with the analysis CLI.

## Sources

- [DoltHub options](https://www.dolthub.com/repositories/post-no-preference/options) and [stock prices](https://www.dolthub.com/repositories/post-no-preference/stocks)
- [DoltHub's description of the source](https://www.dolthub.com/blog/2024-09-27-dolt-post-no-preference/)
- [Federal Reserve event statement](https://www.federalreserve.gov/newsevents/pressreleases/monetary20240918a.htm)
- [SPY issuer announcement for September 2024 distribution](https://announcements.asx.com.au/asxpdf/20240920/pdf/068358hmf01f2j.pdf)

MIT applies to code, not external market data. AI-assisted implementation; reproduce and understand the analysis before presenting it as research expertise.

Related: [Quiz Risk Simulator](https://github.com/yash9518/quiz-risk-simulator) · [Volatility Risk Premium](https://github.com/yash9518/volatility-risk-premium).
