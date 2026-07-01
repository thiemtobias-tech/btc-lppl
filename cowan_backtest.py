"""
Cowan Backtest / Selectivity - Layer 5: the honest arbiter.

'Buildable' and 'faithful to the book' do NOT mean 'predictive'. This module
answers the only question that matters for a trading tool: do the REAL turning
points align with the (deterministic) planetary axes MORE than random data would?
This is the same selectivity logic that falsified Oreste's QPL.

Method - surrogate data: shuffle the series' daily returns many times to build
synthetic series with the SAME return distribution but destroyed real timing.
Re-detect pivots and re-measure the confluence hit-rate (and the Cowan-ratio hit
rate) on each surrogate -> a NULL distribution. Compare the real hit-rate to that
null (z-score, one-sided p-value).

A high real hit-rate means nothing on its own; it must beat the null.
The planetary axes do not depend on price, so they are computed ONCE and reused.
"""

import datetime
import numpy as np

from cowan_data import Bar, make_demo_series, detect_pivots
from cowan_app import build_legs, leg_ratios, bar_jd
from cowan_planets import jd_to_date
from cowan_confluence import planetary_axes_in_range, find_confluences


# --------------------------------------------------------------------------
def _rates(bars, axes, scale, left, right, start_date, bar_days, tol_days):
    """Confluence hit-rate and Cowan-ratio hit-rate for one series (fixed axes)."""
    pivots = detect_pivots(bars, left, right)
    ratios = leg_ratios(build_legs(pivots, scale))
    geo = [{"jd": bar_jd(start_date, bar_days, p.trading_day_index)} for p in pivots]
    conf = find_confluences(geo, axes, tol_days)
    hits = sum(1 for c in conf if c["confluence"])
    total = len(conf)
    nmatch = sum(1 for x in ratios if x["match"])
    nt = len(ratios)
    return (hits / total if total else 0.0), (nmatch / nt if nt else 0.0)


def _surrogate(bars, rng):
    """New series: same daily returns, shuffled (destroys real timing)."""
    closes = np.array([b.close for b in bars], dtype=float)
    rets = np.diff(closes)
    rng.shuffle(rets)
    new = np.concatenate([[closes[0]], closes[0] + np.cumsum(rets)])
    out = []
    for i in range(len(new)):
        w = abs(rets[i - 1]) if i > 0 else 0.0
        out.append(Bar(i, new[i] + w, new[i] - w, new[i]))
    return out


def selectivity_test(bars, n_surrogates=200, seed=1, scale=1.0, left=25, right=25,
                     start_date=datetime.date(2015, 1, 1), bar_days=1, tol_days=12):
    rng = np.random.default_rng(seed)
    n = len(bars)

    # planetary axes over the full bar span (price-independent) - computed once
    s_ymd = jd_to_date(bar_jd(start_date, bar_days, 0) - 30)
    e_ymd = jd_to_date(bar_jd(start_date, bar_days, n - 1) + 30)
    axes = planetary_axes_in_range(s_ymd, e_ymd)

    real_conf, real_ratio = _rates(bars, axes, scale, left, right, start_date, bar_days, tol_days)

    null_conf, null_ratio = [], []
    for _ in range(n_surrogates):
        sc, sr = _rates(_surrogate(bars, rng), axes, scale, left, right, start_date, bar_days, tol_days)
        null_conf.append(sc); null_ratio.append(sr)

    def stat(real_v, null):
        null = np.array(null)
        mu, sd = float(null.mean()), float(null.std())
        z = (real_v - mu) / sd if sd > 1e-12 else 0.0
        p = float(np.mean(null >= real_v))     # one-sided: null as good or better
        return {"real": real_v, "null_mean": mu, "null_std": sd, "z": z, "p": p}

    return {"n": n_surrogates, "n_axes": len(axes),
            "confluence": stat(real_conf, null_conf),
            "ratio": stat(real_ratio, null_ratio)}


# --------------------------------------------------------------------------
def print_report(res, label="DEMO"):
    line = "=" * 78
    print(line)
    print(f"COWAN SELEKTIVITAETS-TEST  ({label})")
    print(line)
    print(f"Surrogate: {res['n']}  |  Planeten-Achsen: {res['n_axes']}")

    def block(name, s):
        print(f"\n{name}")
        print(f"  echt        : {s['real']*100:6.1f} %")
        print(f"  Zufall (Ø)  : {s['null_mean']*100:6.1f} %  (SD {s['null_std']*100:.1f} %)")
        print(f"  z-Wert      : {s['z']:+.2f}")
        print(f"  p-Wert      : {s['p']:.3f}   (Anteil Zufalls-Laeufe >= echt)")
        verdict = ("SIGNAL - echt schlaegt den Zufall (p < 0,05)" if s["p"] < 0.05
                   else "KEIN Signal - nicht vom Zufall unterscheidbar")
        print(f"  Urteil      : {verdict}")

    block("CONFLUENCE (Wendepunkte auf Planeten-Achsen):", res["confluence"])
    block("COWAN-RATIOS (Bein-Paare mit sqrt-Verhaeltnis):", res["ratio"])

    print("\n" + "-" * 78)
    print("Auf ZUFALLSDATEN MUSS hier 'KEIN Signal' stehen (echt ~ Zufall). Auf ECHTEN")
    print("BTC/Gold-Daten mit korrekt gesquarter Skala ist ein p < 0,05 der Beleg, dass")
    print("Cowans Struktur mehr ist als Rauschen. Das ist der ehrliche Lackmustest.")
    print(line)


if __name__ == "__main__":
    bars = make_demo_series(n=1500, seed=7)
    res = selectivity_test(bars, n_surrogates=200)
    print_report(res, label="DEMO (Random-Walk)")
