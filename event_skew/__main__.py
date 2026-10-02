import argparse
import json
from pathlib import Path
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from .model import compare


def main():
    p=argparse.ArgumentParser(description='Real historical SPY smile event study')
    p.add_argument('--data',type=Path,default=Path('data/raw/options.csv'))
    p.add_argument('--rate',type=float,default=.05)
    p.add_argument('--output',type=Path,default=Path('reports'))
    a=p.parse_args()
    if not a.data.exists():p.error('Run python -m event_skew.data first; no synthetic fallback.')
    data=pd.read_csv(a.data);out=a.output;out.mkdir(parents=True,exist_ok=True)
    summary,quotes,curves,audit=compare(data,a.rate)
    summary.to_csv(out/'smile_metrics.csv',index=False)
    curves.to_csv(out/'fitted_curves.csv',index=False)
    (out/'quote_audit.json').write_text(json.dumps(audit,indent=2))
    manifest=a.data.parent/'manifest.json'
    if manifest.exists():(out/'data_provenance.json').write_text(manifest.read_text())
    sensitivities=[]
    for rate in [a.rate-.01,a.rate,a.rate+.01]:
        m,_,_,_=compare(data,rate);m['assumed_rate']=rate;sensitivities.append(m)
    pd.concat(sensitivities).to_csv(out/'rate_sensitivity.csv',index=False)
    fig,ax=plt.subplots(1,2,figsize=(12,4.8))
    colors=['#2563eb','#dc6245']
    for (date,d),color in zip(quotes.groupby('date'),colors):
        lo,hi=summary.domain_low.iloc[0],summary.domain_high.iloc[0]
        d=d[d.log_moneyness.between(lo,hi)].sort_values('log_moneyness')
        curve=curves[curves.date==date]
        ax[0].errorbar(d.log_moneyness,d.iv_mid*100,
                       yerr=[(d.iv_mid-d.iv_bid)*100,(d.iv_ask-d.iv_mid)*100],
                       fmt='o',ms=3,color=color,alpha=.7,label=f'{date} quote IV +/- bid/ask')
        ax[0].plot(curve.log_moneyness,curve.fitted_iv*100,color=color)
    pivot=curves.pivot(index='log_moneyness',columns='date',values='fitted_iv')
    ax[1].plot(pivot.index,(pivot.iloc[:,1]-pivot.iloc[:,0])*100,color='#7c3aed')
    ax[1].axhline(0,color='gray',lw=.7)
    ax[0].set(title='SPY: before/after September 18, 2024 FOMC',xlabel='log(strike / parity forward)',ylabel='European-equivalent IV (%)')
    ax[0].legend(fontsize=8)
    ax[1].set(title='After minus before: matched moneyness',xlabel='log(strike / parity forward)',ylabel='IV change (percentage points)')
    fig.tight_layout();fig.savefig(out/'event_smile.png',dpi=160);plt.close(fig)
    delta=summary.iloc[1][['atm_iv','slope','curvature']]-summary.iloc[0][['atm_iv','slope','curvature']]
    table=summary[['date','n','atm_iv','slope','curvature','rmse']].to_string(index=False)
    (out/'RESULTS.md').write_text(f"# SPY smile around the September 18, 2024 FOMC\n\nThe Fed announced a 50 bp cut at 14:00 EDT on September 18. [Official event statement](https://www.federalreserve.gov/newsevents/pressreleases/monetary20240918a.htm). We compare third-party daily option snapshots from September 17 and 19, both expiring October 18, 2024. These are real historical bid/ask observations, not generated option prices.\n\n![Smile comparison](event_smile.png)\n\n```text\n{table}\n```\n\nATM IV change: **{delta.atm_iv*100:+.3f} volatility percentage points**. Local slope change: **{delta.slope:+.4f}**; curvature change: **{delta.curvature:+.4f}**. IV is decimal; slope is d(IV)/d log(K/F), curvature is its second derivative. A 1% log-moneyness move changes IV by approximately slope x 1 volatility point locally. The quadratic is descriptive, not an arbitrage-free surface.\n\n## Method and caveats\n\nInvert bid, midpoint and ask through a European Black forward model; use OTM puts below forward and OTM calls above it. Infer each forward from the median of the five closest-to-spot call/put parity pairs (or all available if fewer). Base continuously compounded rate {a.rate:.1%} is an assumption, not an observed yield. Rate sensitivity is in the CSV.\n\nReject nonpositive bids, crossed markets, bid below $0.05, relative spreads above 35%, expired contracts and non-invertible prices. Fit local quadratics inside +/-0.10 and restrict comparison curves to the shared support of the retained fitting observations. See quote_audit.json for counts, inversion failures and forward-pair dispersion. Bid/ask-fit coefficients indicate spread sensitivity, not statistical confidence intervals.\n\nSPY options are American-style and SPY pays dividends: the European-equivalent IV and parity forward are approximations. Both observations precede the September 20 ex-distribution date, which lies within the option maturity, so carry and early-exercise effects matter; we do not assume zero dividends. No intraday timestamps, volume or open interest are provided by the dataset, so synchronous/executable quotes cannot be verified. The common expiration has 31 days remaining before and 29 after; time decay and all other intervening news remain confounders. One before/after pair does not identify a causal Fed effect. No option P&L or profitable strategy is inferred.\n\nRaw data is downloaded locally and excluded from Git; the provenance file contains retrieval times, source queries and SHA-256 checksums. Re-run the downloader to reproduce from the public source; a mutable source can be revised.\n",encoding='utf-8')
    print(table)


if __name__=='__main__':main()
