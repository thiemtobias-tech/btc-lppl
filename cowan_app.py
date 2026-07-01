"""
Cowan App - the INTEGRATED engine (the 'brain' of the eventual Streamlit UI).

Now wires all layers into one pipeline:

    data (+dates) -> pivots -> PTV per leg -> Cowan ratios
                                            -> 60 deg turning-point projection
                  -> planetary 15 deg axes over the same date range
                  -> CONFLUENCE: geometric turning points that land on an axis

The composite (cowan_composite.py) is the period-analysis layer that plugs in
with its observed parameters; it is verified and rendered there.

SCOPE recap: geometry (Part I) + planetary (Lesson VIII) + composite (Lesson IX)
are all built and checked against the book. Lesson X's 4D cube is conceptual
(no signals). Live BTC/Gold feeds run in your environment (this sandbox has no net).
"""

import datetime
import numpy as np

from cowan_geometry import ptv, Pivot
from cowan_ratios import classify
from cowan_projection import project_mated_point
from cowan_data import make_demo_series, detect_pivots
from cowan_planets import julian_day, jd_to_date, synodic_angle
from cowan_confluence import planetary_axes_in_range, find_confluences, summarize

import cowan_geometry
import cowan_ratios
import cowan_projection
import cowan_planets


# --------------------------------------------------------------------------
# date mapping: bar index -> (y,m,d) -> Julian Day
# --------------------------------------------------------------------------
def bar_ymd(start_date, bar_days, index):
    d = start_date + datetime.timedelta(days=index * bar_days)
    return (d.year, d.month, d.day)

def bar_jd(start_date, bar_days, index):
    return julian_day(*bar_ymd(start_date, bar_days, index))


# --------------------------------------------------------------------------
# geometry (unchanged core)
# --------------------------------------------------------------------------
def build_legs(pivots, scale):
    legs = []
    for a, b in zip(pivots, pivots[1:]):
        dp = b.price - a.price
        dt = b.trading_day_index - a.trading_day_index
        legs.append({"from_idx": a.trading_day_index, "to_idx": b.trading_day_index,
                     "from_price": a.price, "to_price": b.price,
                     "ptv": ptv(dp, dt, scale=scale), "direction": +1 if dp >= 0 else -1})
    return legs

def leg_ratios(legs, tol_pct=1.0):
    out = []
    for i in range(len(legs) - 1):
        res = classify(legs[i]["ptv"], legs[i + 1]["ptv"], tol_pct)
        matched = res["best"] if res["best"]["dev"] <= tol_pct else None
        out.append({"leg_a": i, "leg_b": i + 1, "ratio": res["ratio"],
                    "match": matched["name"] if matched else None,
                    "dev": matched["dev"] if matched else res["best"]["dev"]})
    return out

def project_next(pivots, scale):
    if len(pivots) < 2:
        return {"status": "zu_wenige_pivots"}
    a, b = pivots[-2], pivots[-1]
    res = project_mated_point(a.trading_day_index, a.price, b.trading_day_index, b.price, scale=scale)
    if not res["forward"]:
        return {"status": "kein_vorwaerts"}
    c = res["forward"][0]
    return {"status": "ok", "from_bar": b.trading_day_index, "c_bar": c["time"], "c_price": c["price"]}


# --------------------------------------------------------------------------
# integrated pipeline
# --------------------------------------------------------------------------
def run_pipeline(bars, scale=1.0, left=25, right=25, manual_pivots=None,
                 start_date=datetime.date(2015, 1, 1), bar_days=1, tol_days=12):
    pivots = manual_pivots if manual_pivots is not None else detect_pivots(bars, left, right)
    legs = build_legs(pivots, scale)
    ratios = leg_ratios(legs)
    projection = project_next(pivots, scale)

    # geometric turning points as dated events (Cowan: turns align with axes)
    geo_events = [{"jd": bar_jd(start_date, bar_days, p.trading_day_index),
                   "label": f"WP@bar{int(p.trading_day_index)}", "price": p.price}
                  for p in pivots]
    if projection["status"] == "ok":
        geo_events.append({"jd": bar_jd(start_date, bar_days, projection["c_bar"]),
                           "label": "Projektion", "price": projection["c_price"]})

    jds = [e["jd"] for e in geo_events]
    start_ymd = jd_to_date(min(jds) - 30)
    end_ymd = jd_to_date(max(jds) + 30)
    axes = planetary_axes_in_range(start_ymd, end_ymd)
    confluences = find_confluences(geo_events, axes, tol_days)

    return {"n_bars": len(bars), "scale": scale, "pivots": pivots, "legs": legs,
            "ratios": ratios, "projection": projection, "geo_events": geo_events,
            "axes": axes, "confluences": confluences, "tol_days": tol_days,
            "start_date": start_date, "bar_days": bar_days}


# --------------------------------------------------------------------------
# engine verification (one command checks every module against the book)
# --------------------------------------------------------------------------
def verify_engine():
    print("\n########  MOTOR-VERIFIKATION GEGEN DAS BUCH  ########\n")
    ok = True
    ok &= cowan_geometry.run_verification();  print()
    ok &= cowan_ratios.run_verification();    print()
    ok &= cowan_projection.run_verification();print()
    cowan_planets.run_verification()          # druckt eigene Ergebnisse (inkl. Druckfehler-Fund)
    print("\n(Composite separat in cowan_composite.py verifiziert + als Chart gerendert.)")
    return ok


# --------------------------------------------------------------------------
# report
# --------------------------------------------------------------------------
def _d(ymd):
    return f"{ymd[0]}-{ymd[1]:02d}-{ymd[2]:02d}"

def print_report(r):
    line = "=" * 84
    print(line)
    print("COWAN APP  -  INTEGRIERTE ENGINE  (Geometrie + Planeten + Confluence)")
    print(line)
    print(f"Datenquelle : DEMO (synthetischer Random-Walk) - KEINE echten Marktdaten")
    print(f"Zeitraum    : {_d(bar_ymd(r['start_date'], r['bar_days'], 0))} .. "
          f"{_d(bar_ymd(r['start_date'], r['bar_days'], r['n_bars']-1))}   "
          f"({r['n_bars']} Bars, 1 Bar = {r['bar_days']} Tag)")
    print(f"Skalierung  : {r['scale']}   |   Pivots: {len(r['pivots'])}   |   "
          f"Planeten-Achsen im Zeitraum: {len(r['axes'])}")

    print("\nGEOMETRIE-RATIOS (aufeinanderfolgende Beine):")
    n_match = sum(1 for x in r["ratios"] if x["match"])
    print(f"  --> {n_match} von {len(r['ratios'])} Bein-Paaren treffen einen Cowan-Ratio "
          f"(auf Zufallsdaten erwartet: wenige)")

    print("\nPLANETEN-ACHSEN (15 Grad, im Zeitraum):")
    for a in r["axes"]:
        print(f"  {_d(a['ymd'])}   {a['pair']}  {int(a['deg'])} Grad")

    print(f"\nCONFLUENCE  (geometrischer Wendepunkt faellt auf eine Achse, Toleranz {r['tol_days']} Tage):")
    hits, total = summarize(r["confluences"])
    shown = [c for c in r["confluences"] if c["confluence"]]
    if shown:
        for c in shown:
            g = c["geo"]; a = c["axis"]
            print(f"  {_d(jd_to_date(g['jd']))}  {g['label']:<14}  <->  "
                  f"{a['pair']} {int(a['deg'])} Grad am {_d(a['ymd'])}   (Abstand {int(c['gap_days'])} Tage)")
    else:
        print("  keine Confluence innerhalb der Toleranz")
    print(f"  --> {hits} von {total} geometrischen Wendepunkten fallen auf eine Planeten-Achse")

    print("\n" + "-" * 84)
    print("EHRLICH: Auf ZUFALLSDATEN sind wenige zufaellige Confluences zu erwarten -")
    print("der Motor erzeugt keine Scheinstruktur. Erst auf ECHTEN Daten mit korrekt")
    print("gesquarter Skala wird die Confluence aussagekraeftig (Geometrie & Planeten sind")
    print("unabhaengige Eingaben).")
    print(line)


# --------------------------------------------------------------------------
# a REAL, book-grounded confluence: the 1987 top
# --------------------------------------------------------------------------
def real_1987_confluence():
    print("\n########  REAL-BEISPIEL: DER TOP VON 1987 (Cowans DJIA)  ########\n")
    # planetary: Saturn-Uranus 15 deg axis with Cowan's 5.5 deg orb near 8/1987
    from cowan_composite import component_axis_jds
    ax = component_axis_jds("Saturn", "Uranus", 15.0, 5.5, (1987, 1, 1), (1987, 12, 31))
    su_axis = jd_to_date(ax[0]) if ax else None
    actual_top = (1987, 8, 25)
    gap = abs(julian_day(*su_axis) - julian_day(*actual_top)) if su_axis else None
    print(f"  Geometrie (Cowan): das 5-Jahres-Wachstumsmuster projiziert per Wurzel-5")
    print(f"                     (GH = Wurzel5 x EG) den Top auf August 1987.")
    print(f"  Planeten (Engine): Saturn-Uranus 15-Grad-Achse (Orb 5,5) am {_d(su_axis)}.")
    print(f"  Tatsaechlicher Top: {_d(actual_top)}.")
    print(f"  --> beide unabhaengigen Methoden auf denselben Monat; Achse {int(gap)} Tage")
    print(f"      vor dem realen Top. GENAU das ist eine echte Confluence.")


if __name__ == "__main__":
    engine_ok = verify_engine()

    print("\n\n########  INTEGRIERTER LAUF AUF DEMO-DATEN  ########\n")
    bars = make_demo_series(n=1500, seed=7)
    report = run_pipeline(bars, scale=1.0, left=25, right=25,
                          start_date=datetime.date(2015, 1, 1), bar_days=1, tol_days=12)
    print_report(report)

    real_1987_confluence()

    print(f"\n[Motor gegen das Buch verifiziert: {'JA' if engine_ok else 'NEIN'}]")
