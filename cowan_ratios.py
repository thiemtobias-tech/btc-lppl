"""
Cowan Ratio Detector - Layer 1: identifies the price-time ratios Cowan declares
more important than Fibonacci (Lesson IV): root2, root3, root5, root10, Pi, and
the musical octaves x2 / x4.

PHI is included ONLY as a flagged BYPRODUCT, because Cowan explicitly ranks it
as a derived, secondary ratio ("far down the list") - not a primary one.

The target set is CLOSED (taken verbatim from the book), not chosen by us.
Verified against Cowan's own worked ratio examples from Lessons IV and V.
"""

import math
from cowan_geometry import ratio   # single source of truth for a/b

# --------------------------------------------------------------------------
# Cowan's target ratios (Lesson IV). name, value, kind, note
# --------------------------------------------------------------------------
TARGETS = [
    ("root2",     math.sqrt(2),        "primaer",     "Diagonale des Quadrats"),
    ("root3",     math.sqrt(3),        "primaer",     "Diagonale des Wuerfels (3D)"),
    ("root5",     math.sqrt(5),        "primaer",     "Diagonale zweier Quadrate; Wachstumsspirale"),
    ("root10",    math.sqrt(10),       "primaer",     "root2 x root5; Diagonale dreier Quadrate"),
    ("Pi",        math.pi,             "primaer",     "Umfang/Durchmesser; Vollendung des Wachstums"),
    ("Oktave x2", 2.0,                 "primaer",     "musikalische Oktave"),
    ("Oktave x4", 4.0,                 "primaer",     "musikalische Doppeloktave"),
    ("PHI",       (1 + math.sqrt(5))/2, "Nebenprodukt", "Cowan: abgeleitet aus root5 - KEIN primaeres Verhaeltnis"),
]


def classify(a, b, tol_pct=1.0):
    """
    Classify the ratio of two PTV lengths against Cowan's target ratios.

    The ratio is normalised to >= 1 (Cowan's relationships are symmetric,
    whether the sequence grows or decays). Tolerance defaults to 1.0 %, which
    matches Cowan's own loosest documented example (his root3 case is ~0.97 %).

    Returns: {'ratio', 'best', 'matches'} where matches = every target within
    tolerance - this is what surfaces the Pi / root10 near-degeneracy that
    Cowan himself points out (3.14159 vs 3.16228 differ by only 0.66 %).
    """
    r = ratio(a, b)
    if r < 1:
        r = 1.0 / r
    scored = []
    for name, val, kind, note in TARGETS:
        dev = abs(r - val) / val * 100.0
        scored.append({"name": name, "val": val, "kind": kind, "note": note, "dev": dev})
    scored.sort(key=lambda s: s["dev"])
    matches = [s for s in scored if s["dev"] <= tol_pct]
    return {"ratio": r, "best": scored[0], "matches": matches}


# ==========================================================================
# SELF-VERIFICATION against Cowan's own worked ratio examples (Lessons IV / V)
# ==========================================================================
def _fmt(x, nd=2):
    return f"{x:.{nd}f}"


def run_verification(tol_pct=1.0):
    line = "=" * 82
    print(line)
    print("COWAN RATIO-DETEKTOR  -  Verifikation gegen die Beispiele aus dem Buch (Lektion IV/V)")
    print(line)

    # (label, PTV_a, PTV_b, Cowans behaupteter Ratio-Typ)
    cases = [
        ("root2  EF/FG  1966->74 / 74->82",        631,   447,   "root2"),
        ("root2  EG/EF  1966->82 / 66->74",        891,   631,   "root2"),
        ("root2  LE/DE  1937->66 / 49->66",        1710,  1209,  "root2"),
        ("root2  JE/BE  1914->66 / 32->66 (52 J.)",2832,  1998,  "root2"),
        ("root2  JK/IM",                            494,   350,   "root2"),
        ("root2  AK/LB",                            406,   287,   "root2"),
        ("root5  GH/EG  1982->87 / 1966->82",       1994,  891,   "root5"),
        ("root5  JA/AB",                            838,   375,   "root5"),
        ("root5  BE/BD  1932->66 / 1932->49",       1998,  891,   "root5"),
        ("root3  BD/BC",                            891,   514,   "root3"),
        ("root3  JK/LB  (Cowans loseste)",          494,   288,   "root3"),
        ("Pi     AG/AC  Ellipsen-Umfang 82-86",     2323,  737,   "Pi"),
        ("root10 GH/EF  = EF x root10",             1994,  631,   "root10"),
        ("root10 JE/BD  = BD x root10",             2832,  891,   "root10"),
        ("Oktave Q1/CD  (Lektion-I-Gegenprobe)",    473.4, 236.6, "Oktave x2"),
    ]

    print(f"\n{'Fall':<42}{'Ratio':>8}{'Bester Treffer':>18}{'Abw.%':>8}  Anspruch  Status")
    print("-" * 82)

    all_ok = True
    for label, a, b, claim in cases:
        res = classify(a, b, tol_pct)
        r = res["ratio"]
        best = res["best"]
        match_names = {m["name"] for m in res["matches"]}
        ok = claim in match_names
        all_ok &= ok
        near = [m["name"] for m in res["matches"] if m["name"] != best["name"]]
        near_txt = ("  auch nahe: " + ", ".join(f"{n}" for n in near)) if near else ""
        print(f"{label:<42}{_fmt(r,4):>8}{best['name']:>18}{_fmt(best['dev'],3):>8}"
              f"  {claim:<9} {'OK' if ok else 'FEHLER'}{near_txt}")

    # ---- Illustration: Cowans PHI-Hierarchie -----------------------------
    print("\n" + "-" * 82)
    print("ILLUSTRATION - warum PHI bei Cowan nur Nebenprodukt ist")
    print("-" * 82)

    phi_true = classify(1.61803, 1.0)
    print(f"  Wert 1,618 (echtes PHI):   bester Treffer = {phi_true['best']['name']} "
          f"({phi_true['best']['kind']}, Abw. {_fmt(phi_true['best']['dev'],3)} %)")
    print(f"     -> {phi_true['best']['note']}")

    false_phi = classify(1.5811, 1.0)   # root10 / 2 - der 'falsche PHI', vor dem Cowan warnt
    fp_primary = [m for m in false_phi["matches"] if m["kind"] == "primaer"]
    print(f"  Wert 1,5811 (= root10 / 2, der 'falsche PHI'):")
    if fp_primary:
        print(f"     -> primaerer Treffer: {fp_primary[0]['name']}")
    else:
        print(f"     -> KEIN primaerer Treffer innerhalb {tol_pct} % "
              f"(naechster: {false_phi['best']['name']}, Abw. {_fmt(false_phi['best']['dev'],2)} %)")
        print(f"        genau Cowans Warnung: 1,581 wird oft faelschlich fuer 1,618 gehalten.")

    # ---- Ergebnis --------------------------------------------------------
    print("\n" + line)
    if all_ok:
        print(f"ERGEBNIS:  ALLE {len(cases)} PRUEFUNGEN BESTANDEN  (Toleranz {tol_pct} %)")
        print("Der Ratio-Detektor ordnet Cowans eigene Verhaeltnisse 1:1 seinen eigenen Typen zu.")
        print("Beide geometrischen Primitive (PTV + Ratio) sind jetzt gegen das Buch verifiziert.")
    else:
        print("ERGEBNIS:  ABWEICHUNG GEFUNDEN - bitte pruefen.")
    print(line)
    return all_ok


if __name__ == "__main__":
    run_verification()
