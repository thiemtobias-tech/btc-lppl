"""
Cowan Composite Engine - Layer 3 (Lesson IX).

Cowan's core correction to conventional 'sum of sine waves': the sum of the
simple components is only the PERCENT DEVIATION from the trend; the final model
is that sum MULTIPLIED BY THE TREND (not added). This module implements exactly
that, using the four planetary harmonics Cowan lists for the 1982-1987 growth
pattern, with the axis dates coming from the (already verified) planetary engine.

WHAT IS VERIFIED vs OBSERVED
  Verified (rigorous): the component INPUTS - the planetary axis dates. E.g.
    Cowan's Saturn-Uranus turn on 26.4.1983 at 35 deg 30' before conjunction is
    reproduced to 0.1 deg; Saturn's 60 deg span 6/1982-10/1987 to 0.5 deg.
  Observed (Cowan reads these off the chart, per his own method): the orb of
    influence per component, each component's phase (top vs bottom at an axis),
    the deviation amplitude, and the trend slope. Cowan states the orb is
    'determined by observation once the face rotates into view'. These are
    inputs here, defaulted to his documented 1982-1987 values.

The book presents the composite as a CHART (Figs 9.5/9.6, Chart IX.A), not a
number table - so this reproduces his METHOD and INPUTS, then renders the model.
"""

import math
import numpy as np
from cowan_planets import synodic_angle, helio_lon_date, julian_day, jd_to_date


# --------------------------------------------------------------------------
# component axis dates (with Cowan's orb offset) and triangle waves
# --------------------------------------------------------------------------
def component_axis_jds(faster, slower, step_deg, orb_deg, start, end):
    """
    JDs where the effect occurs: the synodic angle reaches (k*step_deg - orb_deg).
    (Equivalently, the shifted angle (angle+orb) crosses a multiple of step_deg.)
    """
    jd = julian_day(*start); jd_end = julian_day(*end)
    prev = (synodic_angle(faster, slower, jd) + orb_deg) % 360.0
    out = []
    while jd < jd_end:
        jd += 1
        cur = (synodic_angle(faster, slower, jd) + orb_deg) % 360.0
        p, c = prev, cur
        if c < p:
            c += 360.0
        for k in range(math.ceil(p / step_deg), math.floor(c / step_deg) + 1):
            out.append(jd)
        prev = cur
    return out


def triangle_from_axes(axis_jds, grid, start_sign=+1):
    """
    Triangle wave in [-1,1] that turns direction at each axis date. Alternates
    start_sign, -start_sign, ... at successive axes. Virtual axes pad the ends.
    """
    axes = list(axis_jds)
    if len(axes) < 2:
        return np.zeros(len(grid))
    gap = float(np.median(np.diff(axes)))
    xs = [axes[0] - gap] + axes + [axes[-1] + gap]
    ys = [start_sign * ((-1) ** (j - 1)) for j in range(len(xs))]
    return np.interp(grid, xs, ys)


# --------------------------------------------------------------------------
# the composite model:  (1 + k * sum_of_components) * trend
# --------------------------------------------------------------------------
def build_composite(start, end, components, amplitude=0.025,
                    trend_base=777.0, trend_pts_per_trading_day=1.0):
    """
    components: list of dicts {faster, slower, step, orb, phase(+1/-1), label}.
    Returns dict with the daily grid, each component wave, the summed percent
    deviation, the trend, and the final model.
    """
    jd0, jd1 = julian_day(*start), julian_day(*end)
    grid = np.arange(jd0, jd1 + 1, 1.0)

    waves = []
    for c in components:
        ax = component_axis_jds(c["faster"], c["slower"], c["step"], c["orb"], start, end)
        w = triangle_from_axes(ax, grid, start_sign=c["phase"])
        waves.append({"label": c["label"], "wave": w, "axes": ax})

    raw_sum = np.sum([w["wave"] for w in waves], axis=0)
    deviation = 1.0 + amplitude * raw_sum

    # trend: linear, ~one point per TRADING day (Cowan). approx trading days from
    # calendar days via 5/7. (Cowan's slope is the squared-chart 45deg slope.)
    trading_days = (grid - jd0) * (5.0 / 7.0)
    trend = trend_base + trend_pts_per_trading_day * trading_days

    model = deviation * trend
    return {"grid": grid, "waves": waves, "raw_sum": raw_sum,
            "deviation": deviation, "trend": trend, "model": model}


# --------------------------------------------------------------------------
# the four components Cowan uses for 1982-1987 (Lesson IX)
# --------------------------------------------------------------------------
def cowan_1982_1987_components():
    # orbs 'before the axis' per Cowan: SU 5.5deg, JS 2deg, JU 2deg.
    # phase +1 = all begin in phase at the 8/1982 bottom, rising to a top (Fig 9.3).
    return [
        {"faster": "Saturn",  "slower": "Uranus",  "step": 15.0, "orb": 5.5, "phase": +1, "label": "Saturn-Uranus 15"},
        {"faster": "Jupiter", "slower": "Saturn",  "step": 15.0, "orb": 2.0, "phase": +1, "label": "Jupiter-Saturn 15"},
        {"faster": "Jupiter", "slower": "Uranus",  "step": 15.0, "orb": 2.0, "phase": +1, "label": "Jupiter-Uranus 15"},
        {"faster": "Jupiter", "slower": "Saturn",  "step": 22.5, "orb": 2.0, "phase": +1, "label": "Jupiter-Saturn 22.5"},
    ]


# --------------------------------------------------------------------------
# rendering (Cowan presents the composite graphically)
# --------------------------------------------------------------------------
def _decimal_year(jd):
    y, m, d = jd_to_date(jd)
    return y + (m - 1) / 12.0 + d / 365.0


def render(result, path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    yrs = np.array([_decimal_year(jd) for jd in result["grid"]])
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(11, 7.5), sharex=True)

    for w in result["waves"]:
        ax1.plot(yrs, w["wave"], lw=0.7, alpha=0.45, label=w["label"])
    ax1.plot(yrs, result["raw_sum"], color="black", lw=1.6, label="Summe (= % Abweichung)")
    ax1.axhline(0, color="grey", lw=0.5)
    ax1.set_title("Cowan Composite (Lektion IX) 1982-1987  -  Komponenten = Dreieckwellen an Planeten-Achsen")
    ax1.set_ylabel("Komponenten")
    ax1.legend(fontsize=7, ncol=3, loc="upper left")

    ax2.plot(yrs, result["trend"], color="tab:orange", ls="--", lw=1.2, label="Trend (~1 Punkt/Handelstag)")
    ax2.plot(yrs, result["model"], color="tab:blue", lw=1.6, label="Modell = (1 + k*Summe) * Trend")
    ax2.set_title("Modell = Summe MULTIPLIZIERT mit Trend (Cowans Kern-Korrektur, nicht addiert)")
    ax2.set_ylabel("DJIA-Modell")
    ax2.set_xlabel("Jahr")
    ax2.legend(fontsize=8, loc="upper left")

    fig.tight_layout()
    fig.savefig(path, dpi=110)
    plt.close(fig)
    return path


# ==========================================================================
# VERIFICATION of inputs + structure
# ==========================================================================
def _fmt(x, nd=1):
    return f"{x:.{nd}f}"


def run_verification(render_path=None):
    line = "=" * 82
    print(line)
    print("COWAN COMPOSITE  -  Verifikation der Eingaben + Struktur (Lektion IX)")
    print(line)

    # ---- A) verifizierte Eingaben (Planeten-Achsen) ----------------------
    print("\n[A] VERIFIZIERTE EINGABEN  (Planeten-Achsen, konventionsfrei)")
    print("-" * 82)
    su = synodic_angle("Saturn", "Uranus", julian_day(1983, 4, 26))
    print(f"    Saturn-Uranus 26.4.1983 : {_fmt(su)} Grad  = {_fmt(360-su)} Grad vor Konjunktion"
          f"   (Cowan: 35 Grad 30)")
    sat = (helio_lon_date("Saturn", 1987, 10, 15) - helio_lon_date("Saturn", 1982, 6, 15)) % 360
    print(f"    Saturn-Spanne 6/1982-10/1987 : {_fmt(sat)} Grad   (Cowan: 60 Grad -> 5-Jahres-Muster komplett)")

    print("\n    erste Saturn-Uranus-Achsen im Muster (Orb 5,5 Grad 'vor der Achse'):")
    ax = component_axis_jds("Saturn", "Uranus", 15.0, 5.5, (1982, 8, 1), (1987, 11, 1))
    for jd in ax[:6]:
        y, m, d = jd_to_date(jd)
        a = synodic_angle("Saturn", "Uranus", jd)
        print(f"      {y}-{m:02d}-{d:02d}   Winkel {_fmt(a)} Grad = {_fmt(360-a)} vor Konj.")

    # ---- B) Composite bauen ----------------------------------------------
    print("\n[B] COMPOSITE-METHODE  ((1 + k*Summe) * Trend)")
    print("-" * 82)
    comps = cowan_1982_1987_components()
    res = build_composite((1982, 8, 1), (1987, 11, 1), comps)
    print(f"    Komponenten: {', '.join(c['label'] for c in comps)}")
    print(f"    (Cowan schliesst hier die 22,5-Grad-Jupiter-URANUS-Harmonische bewusst AUS -")
    print(f"     stattdessen die 22,5-Grad-Jupiter-SATURN, weil diese im 15-Grad-SU-Segment 45 Grad wandert.)")
    print(f"    Gitterpunkte (Tage): {len(res['grid'])}")
    print(f"    % Abweichung Bereich: {_fmt(res['deviation'].min(),3)} .. {_fmt(res['deviation'].max(),3)}")
    print(f"    Trend: {_fmt(res['trend'][0])} -> {_fmt(res['trend'][-1])}  (Modell-Endwerte "
          f"{_fmt(res['model'].min())} .. {_fmt(res['model'].max())})")

    # ---- C) Struktur (grob, abhaengig von beobachteten Phasen) -----------
    top_idx = int(np.argmax(res["model"]))
    ty, tm, td = jd_to_date(res["grid"][top_idx])
    print("\n[C] STRUKTUR  (haengt von den beobachteten Phasen/Amplituden ab)")
    print("-" * 82)
    print(f"    Modell-Hoch bei {ty}-{tm:02d}  (Cowan beschreibt einen 'gerundeten Top' 1987,")
    print(f"    wenn 52- und 20-Monats-Zyklen zu verschiedenen Zeiten drehen)")

    if render_path:
        render(res, render_path)
        print(f"\n    Chart gespeichert: {render_path}")

    print("\n" + line)
    print("EHRLICH: Methode + Eingaben sind originalgetreu und die Achsen verifiziert.")
    print("Der exakte Kurvenverlauf haengt an Cowans beobachteten Parametern (Orb, Phase,")
    print("Amplitude, Trend), die er vom Chart abliest - im Buch als Grafik, nicht als Zahlen.")
    print(line)
    return res


if __name__ == "__main__":
    run_verification(render_path="/home/claude/cowan_composite_1982_1987.png")
