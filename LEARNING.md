# Learn the event study

## 1. Price versus implied volatility

An option price depends on forward, strike, time, rate and volatility in the European Black model. Implied volatility is the volatility input that reproduces the observed price. Root finding searches for that input; it does not estimate a future realized outcome directly.

Read `black_price` and `implied_vol`. Price a synthetic option at 20% IV, invert it and verify you recover 20%. The tests do this across puts, calls and strikes. A root solver must reject prices outside model bounds rather than silently invent a number.

## 2. Why the forward and moneyness matter

Using the same strike before and after a spot move compares different economic moneyness. The project uses `log(K/F)` to normalize. Under European parity, `F = K + exp(rT)*(C-P)`. The median of near-spot pairs reduces the effect of one unusual quote, but American exercise and unsynchronized observations can still bias it.

SPY pays dividends; forward is not simply spot times exp(rT). Both snapshots precede an ex-dividend date inside the option maturity. Explain how carry and early exercise complicate parity.

## 3. Skew and curvature

For `IV=a+b*x+c*x^2`, slope at x=0 is b and curvature is 2c. A negative slope means lower strikes have higher local IV. A positive curvature means the curve bends upward. Check units: IV is decimal, x is log-moneyness. Increasing x by 0.01 changes IV by approximately 0.01*b decimal, or b volatility percentage points.

The ATM value is a fitted local level, not necessarily the IV of a single strike exactly equal to forward. Check common support, residuals, sample size and shape before trusting coefficients. No static-arbitrage guarantees are imposed.

## 4. Uncertainty and identification

Bid/ask prices create a range of plausible IVs, not repeated independent observations. Fitting bid and ask curves gives sensitivity, not a confidence interval. Some quote points can have disproportionate influence on curvature, especially near domain edges.

The observation interval includes the Fed announcement but also other news and two days of time decay. A same-expiry comparison is not a constant-tenor comparison. The source lacks precise quote timestamps. None of this supports a strong claim that the Fed alone caused the change.

## 5. Extend after understanding

Add another expiry, inspect total implied variance rather than IV alone, check call-price convexity, and test wider/narrower spread filters. For a causal event design, consider more events, narrow synchronized windows and control securities. For a pricing surface, use an appropriate constrained model rather than a quadratic extrapolation.

## Interview checkpoints

- Why can two option prices imply different volatility under different exercise models?
- Why compare in log-forward-moneyness rather than raw strike?
- Why is curvature 2c, not c?
- What is lost by using daily snapshots?
- What would you need to claim an event effect or a tradable signal?

An accurate description: 'The study inverts real historical SPY quotes and compares a descriptive smile before and after a Fed event, with explicit American-option, liquidity, timing and tenor limitations.'
