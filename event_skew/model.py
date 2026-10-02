import math
import numpy as np
import pandas as pd
from scipy.optimize import brentq
from scipy.special import ndtr


def black_price(forward,strike,t,rate,sigma,kind='Call'):
    if kind not in ('Call','Put'):raise ValueError('kind must be Call or Put')
    if min(forward,strike,t)<=0 or sigma<0:raise ValueError('invalid Black inputs')
    discount=math.exp(-rate*t)
    if sigma==0:return discount*max((forward-strike) if kind=='Call' else (strike-forward),0)
    s=sigma*math.sqrt(t);d1=math.log(forward/strike)/s+s/2;d2=d1-s
    if kind=='Call':return discount*(forward*ndtr(d1)-strike*ndtr(d2))
    return discount*(strike*ndtr(-d2)-forward*ndtr(-d1))


def implied_vol(price,forward,strike,t,rate,kind='Call'):
    if not np.isfinite([price,forward,strike,t,rate]).all():raise ValueError('non-finite pricing input')
    if min(forward,strike,t)<=0:raise ValueError('positive forward, strike and time required')
    lower=black_price(forward,strike,t,rate,0,kind)
    upper=math.exp(-rate*t)*(forward if kind=='Call' else strike)
    if price<=lower+1e-10 or price>=upper-1e-10:
        raise ValueError('quote outside invertible European bounds')
    if black_price(forward,strike,t,rate,5,kind)<price:raise ValueError('IV exceeds 500% bracket')
    return brentq(lambda v:black_price(forward,strike,t,rate,v,kind)-price,1e-8,5,xtol=1e-11)


def clean_snapshot(frame,rate=.05,max_relative_spread=.35):
    d=frame.copy()
    if d.date.nunique()!=1 or d.expiration.nunique()!=1:raise ValueError('one date and expiration per snapshot')
    for col in ['strike','bid','ask','spot']:d[col]=pd.to_numeric(d[col],errors='raise')
    if not np.isfinite(d[['strike','bid','ask','spot']]).all().all():raise ValueError('nonfinite quote')
    if d.duplicated(['strike','call_put']).any():raise ValueError('duplicate option contract')
    if not d.call_put.isin(['Call','Put']).all():raise ValueError('unknown option type')
    date=pd.Timestamp(d.date.iloc[0]);expiry=pd.Timestamp(d.expiration.iloc[0])
    t=(expiry-date).days/365
    if t<=0:raise ValueError('expired option')
    valid=(d.bid>0)&(d.ask>=d.bid)&(d.strike>0)&(d.spot>0)
    audit={'raw_quotes':len(d),'invalid_quotes':int((~valid).sum())}
    d=d[valid].copy();d['mid']=(d.bid+d.ask)/2
    d['relative_spread']=(d.ask-d.bid)/d.mid
    # Estimate forward via near-spot call-put parity, absorbing dividend carry.
    pairs=d.pivot(index='strike',columns='call_put',values='mid').dropna()
    if not {'Call','Put'}.issubset(pairs.columns) or len(pairs)<3:raise ValueError('need >=3 call-put pairs for forward')
    spot=float(d.spot.iloc[0]);pairs=pairs.iloc[np.argsort(abs(pairs.index.to_numpy()/spot-1))[:5]]
    forwards=pairs.index.to_numpy()+math.exp(rate*t)*(pairs.Call-pairs.Put).to_numpy()
    forward=float(np.median(forwards))
    if forward<=0:raise ValueError('invalid parity forward')
    audit.update(date=str(date.date()),expiry=str(expiry.date()),spot=spot,forward=forward,
                 forward_pair_count=len(forwards),forward_pair_range=float(np.ptp(forwards)),days_to_expiry=int(t*365+.1))
    otm=((d.call_put=='Put')&(d.strike<forward))|((d.call_put=='Call')&(d.strike>=forward))
    filtered=otm&(d.relative_spread<=max_relative_spread)&(d.bid>=.05)
    audit['removed_itm_or_spread']=int((~filtered).sum());d=d[filtered].copy()
    rows=[];failed=0
    for row in d.to_dict('records'):
        try:
            for field in ['bid','mid','ask']:
                row['iv_'+field]=implied_vol(row[field],forward,row['strike'],t,rate,row['call_put'])
            row['log_moneyness']=math.log(row['strike']/forward);rows.append(row)
        except ValueError:failed+=1
    audit['inversion_failures']=failed;audit['valid_otm_quotes']=len(rows)
    if len(rows)<5:raise ValueError(f'Too few usable strikes after filtering: {audit}')
    return pd.DataFrame(rows),audit


def compare(frame,rate=.05,max_relative_spread=.35,max_abs_moneyness=.10):
    dates=sorted(frame.date.unique())
    if len(dates)!=2:raise ValueError('need exactly two dates')
    if frame.expiration.nunique()!=1:raise ValueError('both dates must use same expiration')
    snapshots=[];audits=[]
    for date in dates:
        d,a=clean_snapshot(frame[frame.date==date],rate,max_relative_spread);snapshots.append(d);audits.append(a)
    lo=max(-max_abs_moneyness,*[d.log_moneyness.min() for d in snapshots])
    hi=min(max_abs_moneyness,*[d.log_moneyness.max() for d in snapshots])
    if not lo<0<hi:raise ValueError('No shared domain covering ATM; refusing extrapolation')
    fit_snapshots=[d[d.log_moneyness.between(lo,hi)].copy() for d in snapshots]
    if any(len(d)<5 for d in fit_snapshots):raise ValueError('need >=5 strikes in fitting window')
    # Clipping a window can discard endpoint observations. Recompute evaluation
    # support from the retained points, so the displayed curve never extrapolates.
    lo=max(d.log_moneyness.min() for d in fit_snapshots)
    hi=min(d.log_moneyness.max() for d in fit_snapshots)
    if not lo<0<hi:raise ValueError('Retained fit support must bracket ATM')
    metrics=[];fitted=[]
    grid=np.linspace(lo,hi,101)
    for d,a in zip(fit_snapshots,audits):
        if len(d)<5 or d.log_moneyness.nunique()<5:raise ValueError('need >=5 distinct strikes in shared domain')
        x=d.log_moneyness.to_numpy();y=d.iv_mid.to_numpy()
        coeff=np.polynomial.polynomial.polyfit(x,y,2)
        prediction=np.polynomial.polynomial.polyval(x,coeff)
        residual=y-prediction
        metric=dict(date=a['date'],n=len(d),atm_iv=coeff[0],slope=coeff[1],curvature=2*coeff[2],
                    rmse=float(np.sqrt(np.mean(residual**2))),domain_low=lo,domain_high=hi)
        for field in ['bid','ask']:
            c=np.polynomial.polynomial.polyfit(x,d['iv_'+field],2)
            metric[f'atm_{field}']=c[0];metric[f'slope_{field}']=c[1];metric[f'curvature_{field}']=2*c[2]
        metrics.append(metric)
        fitted.append(pd.DataFrame(dict(date=a['date'],log_moneyness=grid,
                                         fitted_iv=np.polynomial.polynomial.polyval(grid,coeff))))
        a['fit_quotes']=len(d)
    return pd.DataFrame(metrics),pd.concat(snapshots),pd.concat(fitted),audits
