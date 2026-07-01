"""
Cowan Geometry Engine - Layer 1 core: the Price-Time Radius Vector (PTV).

Implements Bradley F. Cowan's PTV mathematics EXACTLY as defined in
"Four-Dimensional Stock Market Structures and Cycles", Lesson I.

Design principle: this module is the single source of truth for the PTV.
Nothing here is interpreted or "improved" - it is Cowan's formula, verbatim.
The engine must reproduce his OWN published numbers (run this file to check)
before it is trusted on any real market.
"""

import math
from dataclasses import dataclass

# --------------------------------------------------------------------------
# Constants
# --------------------------------------------------------------------------
TRADING_HOURS_PER_DAY = 6.5   # NYSE session length Cowan uses throughout Lesson I


# --------------------------------------------------------------------------
# Pivot ("point of force") - where the app will let the user drag points later
# --------------------------------------------------------------------------
@dataclass
class Pivot:
    label: str
    price: float
    # time is stored as a trading-day index; intraday offset kept separately
    trading_day_index: float = 0.0
    intraday_hour: float = 0.0   # hour-of-day, e.g. 10.0 = 10am, 14.0 = 2pm


# --------------------------------------------------------------------------
# TIME model - Cowan's trading-hour convention
# --------------------------------------------------------------------------
def time_component(trading_days, intraday_offset_hours=0.0,
                   hours_per_day=TRADING_HOURS_PER_DAY):
    """
    Cowan's TIME leg, in trading hours.

        time = full_trading_days * hours_per_day  +/-  intraday hour offset

    The intraday offset is the difference in time-of-day between the two
    points (e.g. 10am->2pm = +4h ; 2pm->3pm = +1h ; same time = 0).

    This is the DJIA-intraday convention of Lesson I. For a 24/7 market
    like BTC the offset is 0 and `hours_per_day` becomes the chosen bar
    unit; that adaptation lives in the market adapters, not here.
    """
    return trading_days * hours_per_day + intraday_offset_hours


# --------------------------------------------------------------------------
# The Price-Time Radius Vector  (Lesson I, Figure 1.1)
# --------------------------------------------------------------------------
def ptv(price_change, time_hours, scale=1.0):
    """
    PTV = hypotenuse of the right triangle whose legs are the PRICE move and
    the (scaled) TIME move:

        PTV = sqrt( price^2 + (scale * time)^2 )

    `scale` is Cowan's chart-"squaring" factor = price units per time unit.
    In Lesson I price and trading-hours are combined 1:1, so scale = 1.0.
    On BTC / Gold this single factor is the one global calibration parameter
    we discussed - here it is simply equal to 1.
    """
    return math.hypot(price_change, scale * time_hours)


def price_from_ptv(ptv_length, time_hours, scale=1.0):
    """Reverse solve (Lesson I review Q3): given PTV length + time -> PRICE leg."""
    t = scale * time_hours
    return math.sqrt(ptv_length ** 2 - t ** 2)


def time_from_ptv(ptv_length, price_change, scale=1.0):
    """Reverse solve (Lesson I review Q4): given PTV length + price -> TIME leg (hours)."""
    t = math.sqrt(ptv_length ** 2 - price_change ** 2)
    return t / scale


def ratio(ptv_a, ptv_b):
    """Length ratio of two PTVs (used later to spot octave / sqrt(n) relations)."""
    return ptv_a / ptv_b


# ==========================================================================
# SELF-VERIFICATION against Cowan's own worked examples (Lesson I)
# ==========================================================================
def _fmt(x, nd=2):
    return f"{x:.{nd}f}"


def _pct_err(got, ref):
    return abs(got - ref) / abs(ref) * 100.0 if ref else 0.0


def run_verification(tol_pct=0.1):
    line = "=" * 78
    print(line)
    print("COWAN PTV-ENGINE  -  Verifikation gegen die Beispiele aus dem Buch (Lektion I)")
    print(line)

    all_ok = True

    # ---- A) TIME-Modell: Cowans Handelsstunden-Umrechnung -----------------
    print("\n[A] ZEIT-MODELL  (Handelsstunden = Tage x 6,5  +/- Intraday-Offset)")
    print("-" * 78)
    time_cases = [
        # name, trading_days, offset, published_hours
        ("B->C  (20 Tage, +1h von 14->15 Uhr)",      20, +1.0, 131.0),
        ("Q1    (56 Tage, -4h von 14->10 Uhr)",      56, -4.0, 360.0),
        ("Q2    (14 Tage, 0h, gleiche Uhrzeit 15h)", 14,  0.0,  91.0),
        ("Q3    (29 Tage, 0h)",                       29,  0.0, 188.5),
    ]
    print(f"{'Fall':<40}{'App':>10}{'Cowan':>10}{'Abw.%':>10}  Status")
    for name, days, off, ref in time_cases:
        got = time_component(days, off)
        e = _pct_err(got, ref)
        ok = e <= tol_pct
        all_ok &= ok
        print(f"{name:<40}{_fmt(got):>10}{_fmt(ref):>10}{_fmt(e,3):>10}  {'OK' if ok else 'FEHLER'}")

    # ---- B) VORWAERTS: PTV aus (Preis, Zeit) ------------------------------
    print("\n[B] PTV VORWAERTS  =  sqrt(Preis^2 + Zeit^2)   [scale = 1,0]")
    print("-" * 78)
    fwd_cases = [
        # name, price, time_hours, published_ptv
        ("B->C   Preis 195,9  Zeit 131",   195.9, 131.0, 235.7),
        ("Q1     Preis 307,42 Zeit 360",   307.42, 360.0, 473.4),
        ("Q2     Preis 215,59 Zeit 91",    215.59,  91.0, 234.01),
    ]
    print(f"{'Fall':<40}{'App':>10}{'Cowan':>10}{'Abw.%':>10}  Status")
    for name, p, t, ref in fwd_cases:
        got = ptv(p, t)
        e = _pct_err(got, ref)
        ok = e <= tol_pct
        all_ok &= ok
        print(f"{name:<40}{_fmt(got):>10}{_fmt(ref):>10}{_fmt(e,3):>10}  {'OK' if ok else 'FEHLER'}")

    # ---- C) RUECKWAERTS: Preis aus (PTV, Zeit)  -> Kursprojektion ----------
    print("\n[C] PTV RUECKWAERTS -> PREIS   (Review-Frage 3: Projektion eines Hochs)")
    print("-" * 78)
    # Q3: PTV = Oktave von 236 = 472 ; Zeit = 188,5h ; Basis-Tief = 2584,65
    q3_price = price_from_ptv(472.0, 188.5)
    q3_level = 2584.65 + q3_price
    for name, got, ref in [
        ("Preis-Bein aus PTV 472 / Zeit 188,5", q3_price, 432.73),
        ("Projiziertes Hoch (2584,65 + Bein)",  q3_level, 3017.38),
    ]:
        e = _pct_err(got, ref)
        ok = e <= tol_pct
        all_ok &= ok
        print(f"{name:<40}{_fmt(got):>10}{_fmt(ref):>10}{_fmt(e,3):>10}  {'OK' if ok else 'FEHLER'}")
    # Vergleich mit dem tatsaechlichen Markt-Hoch am 6.3.1991
    actual_high = 3017.82
    print(f"    -> tatsaechliches Markt-Hoch 6.3.1991: {actual_high}   "
          f"(Cowans Projektionsfehler: {_fmt(_pct_err(q3_level, actual_high),3)} %)")

    # ---- D) RUECKWAERTS: Zeit aus (PTV, Preis) ----------------------------
    print("\n[D] PTV RUECKWAERTS -> ZEIT   (Review-Frage 4: Projektion eines Datums)")
    print("-" * 78)
    # Q4: PTV = Doppeloktave = 4 x 236 = 944 ; Preis = 676
    q4_hours = time_from_ptv(944.0, 676.0)
    q4_days = q4_hours / TRADING_HOURS_PER_DAY
    for name, got, ref in [
        ("Zeit-Bein (Stunden) aus PTV 944 / Preis 676", q4_hours, 658.9),
    ]:
        e = _pct_err(got, ref)
        ok = e <= tol_pct
        all_ok &= ok
        print(f"{name:<44}{_fmt(got):>8}{_fmt(ref):>10}{_fmt(e,3):>10}  {'OK' if ok else 'FEHLER'}")
    print(f"    -> in Handelstagen: {_fmt(q4_days,1)}  (Cowan rundet auf 101; "
          f"tatsaechlich waren es 100 Tage)")

    # ---- E) ILLUSTRATION (Cowans eigene Werte, keine Neuberechnung) --------
    print("\n[E] ILLUSTRATION VON COWANS AUSSAGEN  (seine veroeffentlichten PTV-Werte)")
    print("-" * 78)
    print("    Behauptung: alle PTVs einer Rotation haben ~gleiche Laenge ('constant length')")
    c_cluster = {"CA": 243.6, "CB": 235.7, "CD": 236.6, "CF": 237.5}
    i_cluster = {"IE": 233.5, "IG": 239.3, "IJ": 237.0, "IK": 234.9}
    for name, cl in [("Rotation um C", c_cluster), ("Rotation um I", i_cluster)]:
        vals = list(cl.values())
        mn, mx, mean = min(vals), max(vals), sum(vals) / len(vals)
        spread = (mx - mn) / mean * 100.0
        print(f"    {name}: {cl}")
        print(f"        min {mn}  max {mx}  Mittel {_fmt(mean)}  Streubreite {_fmt(spread,1)} %")

    print("\n    Behauptung: starke Bewegungen sind musikalische Vielfache (Oktave x2, Doppeloktave x4)")
    base = 236.6  # CD als Basis-Energieniveau
    print(f"        Basis (CD)      = {base}")
    print(f"        Oktave  x2      = {_fmt(base*2)}   <->  Q1 gemessen 473,40   (schneller 56-Tage-Anstieg)")
    print(f"        Doppeloktave x4 = {_fmt(base*4)}   <->  Q4 gemessen 944,00")

    # ---- Ergebnis ---------------------------------------------------------
    print("\n" + line)
    if all_ok:
        print(f"ERGEBNIS:  ALLE PRUEFUNGEN BESTANDEN  (Toleranz {tol_pct} %)")
        print("Die Engine reproduziert Cowans eigene Zahlen 1:1. Fundament steht.")
    else:
        print("ERGEBNIS:  ABWEICHUNG GEFUNDEN - bitte pruefen.")
    print(line)
    return all_ok


if __name__ == "__main__":
    run_verification()
