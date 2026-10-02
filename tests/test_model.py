import numpy as np
import pandas as pd
import pytest
from event_skew.model import black_price,implied_vol,compare,clean_snapshot


@pytest.mark.parametrize('kind',['Call','Put'])
@pytest.mark.parametrize('strike',[80,100,120])
def test_price_iv_roundtrip(kind,strike):
    price=black_price(102,strike,.25,.04,.3,kind)
    assert implied_vol(price,102,strike,.25,.04,kind)==pytest.approx(.3,abs=1e-8)


def test_put_call_parity():
    assert black_price(102,100,.3,.05,.2,'Call')-black_price(102,100,.3,.05,.2,'Put')==pytest.approx(np.exp(-.05*.3)*2)


def test_arbitrage_bounds_and_expiration():
    with pytest.raises(ValueError):implied_vol(200,100,100,.1,.05)
    with pytest.raises(ValueError):implied_vol(-1,100,100,.1,.05)
    with pytest.raises(ValueError):implied_vol(1,100,100,0,.05)


def synthetic_quotes():
    # Explicit synthetic fixture ONLY: validates recovery, never used in empirical reports.
    rows=[]
    for date,atm in [('2024-09-17',.25),('2024-09-19',.22)]:
        t=(pd.Timestamp('2024-10-18')-pd.Timestamp(date)).days/365
        for strike in np.arange(92,109,2):
            x=np.log(strike/100);vol=atm-.3*x+1.2*x*x
            for kind in ['Call','Put']:
                mid=black_price(100,strike,t,.05,vol,kind)
                rows.append(dict(date=date,expiration='2024-10-18',spot=100,strike=strike,
                                 call_put=kind,bid=mid*.99,ask=mid*1.01))
    return pd.DataFrame(rows)


def test_recovers_known_skew_curvature_and_event_change():
    summary,_,_,audit=compare(synthetic_quotes())
    assert summary.atm_iv.tolist()==pytest.approx([.25,.22],abs=1e-7)
    assert summary.slope.tolist()==pytest.approx([-.3,-.3],abs=1e-7)
    assert summary.curvature.tolist()==pytest.approx([2.4,2.4],abs=1e-6)
    assert all(a['inversion_failures']==0 for a in audit)


def test_mismatched_expiry_and_duplicate_rejected():
    d=synthetic_quotes();d.loc[0,'expiration']='2024-11-15'
    with pytest.raises(ValueError):compare(d)
    d=synthetic_quotes();one=d[d.date=='2024-09-17']
    with pytest.raises(ValueError):clean_snapshot(pd.concat([one,one.iloc[:1]]))


def test_comparison_grid_never_extrapolates_after_window_clipping():
    summary,quotes,curves,_=compare(synthetic_quotes(),max_abs_moneyness=.07)
    for date,q in quotes.groupby('date'):
        retained=q[q.log_moneyness.between(-.07,.07)]
        grid=curves[curves.date==date].log_moneyness
        assert grid.min()>=retained.log_moneyness.min()
        assert grid.max()<=retained.log_moneyness.max()
