"""
Cowan Planetary Engine - Layer 2 (Lesson VIII).

Dependency-free: a pure-Python Kepler solver on the standard JPL approximate
Keplerian elements (valid ~1800-2050). Computes HELIOCENTRIC ecliptic longitudes
(Cowan works heliocentrically), the SYNODIC ANGLES between planets, and detects
the 15/30/45/90 degree axis crossings Cowan correlates with the market.

Because it solves Kepler's equation (true anomaly, not mean), the planet speed
VARIES around the orbit - exactly the elliptical, variable-rate behaviour Cowan
stresses for his 15-degree timing.

Verification note: absolute zodiac positions depend on conventions (tropical vs
sidereal, precession). The checks below therefore use CONVENTION-FREE quantities:
differences of two longitudes (synodic angle) and the motion of a single planet.
"""

import math

J2000 = 2451545.0  # Julian Day of 2000-01-01 12:00 TT

# --------------------------------------------------------------------------
# JPL approximate Keplerian elements (epoch J2000, rates per Julian century).
# Order: a[AU], e, I[deg], L[deg], longPeri[deg], longNode[deg]; each with rate.
# Source: standard "Keplerian Elements for Approximate Positions" (1800-2050).
# --------------------------------------------------------------------------
ELEMENTS = {
    #            a           adot       e           edot       I          Idot
    #            L           Ldot       peri        peridot    node       nodedot
    "Mercury": (0.38709927, 0.00000037, 0.20563593, 0.00001906, 7.00497902, -0.00594749,
                252.25032350, 149472.67411175, 77.45779628, 0.16047689, 48.33076593, -0.12534081),
    "Venus":   (0.72333566, 0.00000390, 0.00677672, -0.00004107, 3.39467605, -0.00078890,
                181.97909950, 58517.81538729, 131.60246718, 0.00268329, 76.67984255, -0.27769418),
    "Mars":    (1.52371034, 0.00001847, 0.09339410, 0.00007882, 1.84969142, -0.00813131,
                -4.55343205, 19140.30268499, -23.94362959, 0.44441088, 49.55953891, -0.29257343),
    "Jupiter": (5.20288700, -0.00011607, 0.04838624, -0.00013253, 1.30439695, -0.00183714,
                34.39644051, 3034.74612775, 14.72847983, 0.21252668, 100.47390909, 0.20469106),
    "Saturn":  (9.53667594, -0.00125060, 0.05386179, -0.00050991, 2.48599187, 0.00193609,
                49.95424423, 1222.49362201, 92.59887831, -0.41897216, 113.66242448, -0.28867794),
    "Uranus":  (19.18916464, -0.00196176, 0.04725744, -0.00004397, 0.77263783, -0.00242939,
                313.23810451, 428.48202785, 170.95427630, 0.40805281, 74.01692503, 0.04240589),
}


# --------------------------------------------------------------------------
# calendar <-> Julian Day (Gregorian)
# --------------------------------------------------------------------------
def julian_day(year, month, day, hour=12):
    a = (14 - month) // 12
    y = year + 4800 - a
    m = month + 12 * a - 3
    jdn = day + (153 * m + 2) // 5 + 365 * y + y // 4 - y // 100 + y // 400 - 32045
    return jdn + (hour - 12) / 24.0


def jd_to_date(jd):
    jd = jd + 0.5
    Z = int(jd); F = jd - Z
    if Z < 2299161:
        A = Z
    else:
        alpha = int((Z - 1867216.25) / 36524.25)
        A = Z + 1 + alpha - alpha // 4
    B = A + 1524
    C = int((B - 122.1) / 365.25)
    D = int(365.25 * C)
    E = int((B - D) / 30.6001)
    day = B - D - int(30.6001 * E) + F
    month = E - 1 if E < 14 else E - 13
    year = C - 4716 if month > 2 else C - 4715
    return (year, month, int(day))


# --------------------------------------------------------------------------
# Kepler solver + heliocentric ecliptic longitude
# --------------------------------------------------------------------------
def _solve_kepler(M_deg, e):
    """Solve Kepler's equation; return eccentric anomaly E in degrees."""
    estar = math.degrees(e)                       # e* = 57.29578 * e
    E = M_deg + estar * math.sin(math.radians(M_deg))
    for _ in range(60):
        dM = M_deg - (E - estar * math.sin(math.radians(E)))
        dE = dM / (1.0 - e * math.cos(math.radians(E)))
        E += dE
        if abs(dE) < 1e-9:
            break
    return E


def heliocentric_longitude(planet, jd):
    """Heliocentric ecliptic longitude of `planet` at Julian Day `jd`, in [0,360)."""
    (a0, ad, e0, ed, I0, Id, L0, Ld, w0, wd, O0, Od) = ELEMENTS[planet]
    T = (jd - J2000) / 36525.0
    a = a0 + ad * T
    e = e0 + ed * T
    I = I0 + Id * T
    L = L0 + Ld * T
    peri = w0 + wd * T           # longitude of perihelion (varpi)
    node = O0 + Od * T           # longitude of ascending node (Omega)
    omega = peri - node          # argument of perihelion
    M = L - peri
    M = ((M + 180.0) % 360.0) - 180.0
    E = _solve_kepler(M, e)
    Er = math.radians(E)
    xp = a * (math.cos(Er) - e)
    yp = a * math.sqrt(1 - e * e) * math.sin(Er)
    ow, sw = math.cos(math.radians(omega)), math.sin(math.radians(omega))
    cO, sO = math.cos(math.radians(node)), math.sin(math.radians(node))
    cI, sI = math.cos(math.radians(I)), math.sin(math.radians(I))
    xec = (ow * cO - sw * sO * cI) * xp + (-sw * cO - ow * sO * cI) * yp
    yec = (ow * sO + sw * cO * cI) * xp + (-sw * sO + ow * cO * cI) * yp
    return math.degrees(math.atan2(yec, xec)) % 360.0


def helio_lon_date(planet, year, month, day, hour=12):
    return heliocentric_longitude(planet, julian_day(year, month, day, hour))


# --------------------------------------------------------------------------
# synodic angle + axis / conjunction detection
# --------------------------------------------------------------------------
def synodic_angle(faster, slower, jd):
    """Separation (faster - slower) in [0,360). Grows 0->360 over one synodic period."""
    return (heliocentric_longitude(faster, jd) - heliocentric_longitude(slower, jd)) % 360.0


def find_conjunction(faster, slower, approx_year, half_window_years=2.5):
    """Heliocentric conjunction (min separation) near approx_year, scanning daily."""
    jd0 = julian_day(approx_year, 1, 1)
    lo = int(jd0 - half_window_years * 365.25)
    hi = int(jd0 + half_window_years * 365.25)
    best_jd, best_sep = lo, 999.0
    for jd in range(lo, hi + 1):
        s = synodic_angle(faster, slower, jd)
        s = min(s, 360.0 - s)   # angular distance to 0
        if s < best_sep:
            best_sep, best_jd = s, jd
    return jd_to_date(best_jd), best_sep


def find_axis_crossings(faster, slower, start, end, step_deg=15):
    """
    Dates where the synodic angle crosses a multiple of step_deg, over calendar
    (start)-(end) tuples (year,month,day). Returns list of (date, target_deg).
    """
    jd = julian_day(*start)
    jd_end = julian_day(*end)
    prev = synodic_angle(faster, slower, jd)
    out = []
    while jd < jd_end:
        jd += 1
        cur = synodic_angle(faster, slower, jd)
        # detect crossing of any k*step within [prev,cur], handling 360 wrap
        p, c = prev, cur
        if c < p:
            c += 360.0
        k0 = math.ceil(p / step_deg)
        k1 = math.floor(c / step_deg)
        for k in range(k0, k1 + 1):
            out.append((jd_to_date(jd), (k * step_deg) % 360))
        prev = cur
    return out


# ==========================================================================
# SELF-VERIFICATION against Cowan's dated tables (Lesson VIII)
# ==========================================================================
def _fmt(x, nd=1):
    return f"{x:.{nd}f}"


def run_verification():
    line = "=" * 80
    print(line)
    print("COWAN PLANETEN-ENGINE  -  Verifikation gegen Cowans datierte Tabellen (Lektion VIII)")
    print(line)

    # ---- A) Saturn-Uranus Synodalwinkel (konventionsfrei: Differenz) ------
    print("\n[A] SATURN-URANUS SYNODALWINKEL  (Cowans Grad-Angaben, Lektion VIII)")
    print("    konventionsfrei: Differenz zweier heliozentrischer Laengen")
    print("-" * 80)
    # (name, y, m, d, axis, orb) - Cowan: Wendepunkt liegt 'orb' Grad nach der 30-Grad-Achse
    su_cases = [
        ("6/1949", 1949, 6, 15, 60, 6),
        ("6/1953", 1953, 6, 15, 90, 6),
        ("10/1957", 1957, 10, 15, 120, 6),
        ("6/1962", 1962, 6, 15, 150, 6),
        ("10/1966", 1966, 10, 15, 180, 7),
    ]
    printed = {"10/1966": 173}   # so im Buch abgedruckt
    print(f"    {'Datum':<9}{'App':>7}{'Achse+Orb':>11}{'gedruckt':>10}{'Diff':>7}")
    max_dev = 0.0
    for name, y, m, d, axis, orb in su_cases:
        ang = synodic_angle("Saturn", "Uranus", julian_day(y, m, d))
        expected = axis + orb
        dev = abs(ang - expected)
        max_dev = max(max_dev, dev)
        book_val = printed.get(name, expected)
        mark = " !" if book_val != expected else ""
        print(f"    {name:<9}{_fmt(ang):>7}{expected:>11}{book_val:>10}{_fmt(dev):>7}{mark}")
    print(f"    -> Diff = App gegen (Achse+Orb). Groesste Abweichung: {_fmt(max_dev)} Grad")
    print("    ! 10/1966: '173' passt weder zu den +30-Achsen (->180) noch zu 'orb 7 nach'")
    print("      (->187). Die Engine liefert 186,8 = 187: wahrscheinlicher Druckfehler im Buch.")

    # ---- B) Jupiter-Saturn Konjunktionen (20-Jahres-Zyklus) --------------
    print("\n[B] JUPITER-SATURN KONJUNKTIONEN  (heliozentrisch, ~19,86 Jahre)")
    print("-" * 80)
    print(f"    {'~Jahr':>6}{'gefundene Konj.':>20}{'min Sep Grad':>14}")
    conj_dates = []
    for yr in (1921, 1941, 1961, 1981, 2000, 2020):
        (cy, cm, cd), sep = find_conjunction("Jupiter", "Saturn", yr)
        conj_dates.append(cy + cm / 12.0)
        print(f"    {yr:>6}{f'{cy}-{cm:02d}-{cd:02d}':>20}{_fmt(sep,2):>14}")
    gaps = [conj_dates[i + 1] - conj_dates[i] for i in range(len(conj_dates) - 1)]
    print(f"    -> Abstaende (Jahre): {', '.join(_fmt(g) for g in gaps)}   "
          f"(Erwartung ~19,86)")

    # ---- C) Uranus-Viertelzyklus (konventionsfrei: Eigenbewegung) --------
    print("\n[C] URANUS-VIERTELZYKLUS  (Cowan: ~90 Grad Eigenbewegung, Tabelle 8.3)")
    print("-" * 80)
    quarter_cases = [
        ("4/1942 -> 6/1962", (1942, 4, 15), (1962, 6, 15), 90),
        ("6/1962 -> 9/1981", (1962, 6, 15), (1981, 9, 15), 90),
    ]
    print(f"    {'Intervall':<22}{'App Bewegung':>14}{'Cowan':>8}{'Diff':>8}")
    for name, (y1, m1, d1), (y2, m2, d2), ref in quarter_cases:
        l1 = helio_lon_date("Uranus", y1, m1, d1)
        l2 = helio_lon_date("Uranus", y2, m2, d2)
        moved = (l2 - l1) % 360.0
        print(f"    {name:<22}{_fmt(moved):>13} {ref:>8}{_fmt(abs(moved-ref)):>8}")

    # ---- D) Demonstration: 15-Grad-Achsen mit VARIABLER Zeit -------------
    print("\n[D] SATURN-URANUS 15-GRAD-ACHSEN 1982-1990  (variable Zeit durch Ellipse)")
    print("-" * 80)
    cross = find_axis_crossings("Saturn", "Uranus", (1982, 1, 1), (1990, 12, 31), step_deg=15)
    prev = None
    for (y, m, d), deg in cross:
        gap = ""
        if prev is not None:
            months = (julian_day(y, m, d) - prev) / 30.44
            gap = f"   (+{_fmt(months)} Monate)"
        prev = julian_day(y, m, d)
        print(f"    {y}-{m:02d}-{d:02d}   Synodalwinkel = {deg} Grad{gap}")
    print("    -> die Monatsabstaende variieren - genau Cowans Punkt (elliptische Bahn)")

    print("\n" + line)
    print("Hinweis: reiner Kepler-Loeser auf JPL-Elementen (~1800-2050). Die konventions-")
    print("freien Groessen (Synodalwinkel, Eigenbewegung) sind der belastbare Abgleich.")
    print(line)


if __name__ == "__main__":
    run_verification()
