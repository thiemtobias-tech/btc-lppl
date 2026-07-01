"""
Cowan Projection - Layer 1: projects the NEXT turning point.

Two projection modes from the book:
  1. project_mated_point   - Lesson II: the mated PTV forms an EQUILATERAL
     triangle (60 deg interior angle) with the completed leg, fixing the next
     turning point in BOTH price and time. Verified by geometric self-consistency.
  2. project_level_on_axis - Lesson II ellipse major-axis projection: given an
     origin price, a PTV length and the time to the terminus -> the projected
     price LEVEL. Verified against Cowan's own 3423 example.
"""

import math
from cowan_geometry import ptv, price_from_ptv, TRADING_HOURS_PER_DAY


# --------------------------------------------------------------------------
# geometry helpers (work in the 'squared' plane: x = scaled time, y = price)
# --------------------------------------------------------------------------
def _rotate(px, py, ox, oy, deg):
    """Rotate point (px,py) about (ox,oy) by deg degrees (CCW positive)."""
    th = math.radians(deg)
    c, s = math.cos(th), math.sin(th)
    dx, dy = px - ox, py - oy
    return (ox + c * dx - s * dy, oy + s * dx + c * dy)


def _dist(t1, p1, t2, p2, scale):
    """PTV length between two points (= Euclidean distance in squared plane)."""
    return math.hypot(p2 - p1, scale * (t2 - t1))


def _angle_at(qt, qp, at, ap, rt, rp, scale):
    """Interior angle (deg) at vertex Q for points A-Q-R, in squared coords."""
    v1 = (scale * (at - qt), ap - qp)
    v2 = (scale * (rt - qt), rp - qp)
    dot = v1[0] * v2[0] + v1[1] * v2[1]
    n1 = math.hypot(*v1)
    n2 = math.hypot(*v2)
    return math.degrees(math.acos(max(-1.0, min(1.0, dot / (n1 * n2)))))


# --------------------------------------------------------------------------
# Mode 1: mated 60 deg projection (Lesson II)
# --------------------------------------------------------------------------
def project_mated_point(a_time, a_price, b_time, b_price, scale=1.0):
    """
    Given a completed PTV leg A->B, return the projected next turning point C
    such that A, B, C form an equilateral triangle (Cowan's mated-ellipse rule).

    Rotates A about B by +/-60 deg in the squared plane. Returns both candidates
    plus the FORWARD one (time_C > time_B) - the future turning point.
    """
    ax, ay = a_time * scale, a_price
    bx, by = b_time * scale, b_price
    cands = []
    for deg in (+60.0, -60.0):
        cx, cy = _rotate(ax, ay, bx, by, deg)
        cands.append({"deg": deg, "time": cx / scale, "price": cy})
    forward = [c for c in cands if c["time"] > b_time]
    return {"candidates": cands, "forward": forward}


# --------------------------------------------------------------------------
# Mode 2: ellipse major-axis level projection (Lesson II)
# --------------------------------------------------------------------------
def project_level_on_axis(origin_price, ptv_length, time_units,
                          direction=+1, scale=1.0):
    """
    Given the origin price, the PTV length and the elapsed time to the terminus,
    the projected price LEVEL.  direction = +1 for a top, -1 for a bottom.
    """
    price_change = price_from_ptv(ptv_length, time_units, scale=scale)
    return origin_price + direction * price_change


# ==========================================================================
# SELF-VERIFICATION
# ==========================================================================
def _fmt(x, nd=2):
    return f"{x:.{nd}f}"


def run_verification():
    line = "=" * 80
    print(line)
    print("COWAN PROJEKTOR  -  Verifikation")
    print(line)

    all_ok = True

    # ---- A) 60-Grad-Projektion: geometrische Selbstkonsistenz -------------
    print("\n[A] MATED 60-GRAD-PROJEKTION  (geometrische Selbstkonsistenz)")
    print("    Prueft: |AB| = |BC| = |CA|  und  alle Innenwinkel = 60 Grad")
    print("-" * 80)
    test_legs = [
        # a_time, a_price, b_time, b_price, scale
        (0.0,   0.0,  10.0, 200.0, 1.0),
        (5.0, 100.0,  40.0, 130.0, 1.0),
        (0.0,   0.0,  30.0, 300.0, 0.5),   # anderer Skalierungsfaktor
    ]
    print(f"    {'Fall':<26}{'|AB|':>9}{'|BC|':>9}{'|CA|':>9}{'Winkel':>10}  Status")
    for i, (at, ap, bt, bp, sc) in enumerate(test_legs, 1):
        res = project_mated_point(at, ap, bt, bp, scale=sc)
        c = res["forward"][0]
        ct, cp = c["time"], c["price"]
        d_ab = _dist(at, ap, bt, bp, sc)
        d_bc = _dist(bt, bp, ct, cp, sc)
        d_ca = _dist(ct, cp, at, ap, sc)
        ang_b = _angle_at(bt, bp, at, ap, ct, cp, sc)
        ang_a = _angle_at(at, ap, bt, bp, ct, cp, sc)
        ang_c = _angle_at(ct, cp, at, ap, bt, bp, sc)
        sides_ok = abs(d_ab - d_bc) < 1e-6 and abs(d_ab - d_ca) < 1e-6
        ang_ok = all(abs(a - 60.0) < 1e-6 for a in (ang_a, ang_b, ang_c))
        ok = sides_ok and ang_ok
        all_ok &= ok
        print(f"    Leg {i} (scale {sc})".ljust(30)
              + f"{_fmt(d_ab):>9}{_fmt(d_bc):>9}{_fmt(d_ca):>9}"
              + f"{_fmt(ang_b,1):>9} {'OK' if ok else 'FEHLER'}")

    # ---- B) Achsen-Projektion gegen Cowans eigenes 3423-Beispiel ----------
    print("\n[B] ACHSEN-PROJEKTION  (Cowans eigenes Beispiel, Lektion II)")
    print("    Ursprung F = 3273,03 ; PTV = 236 ; Zeit bis Terminus = 182 Std")
    print("-" * 80)
    proj = project_level_on_axis(3273.03, 236.0, 182.0, direction=+1)
    ref_book = 3423.27      # Cowans projizierter Wert
    actual_mkt = 3422.8     # tatsaechliches Markt-Hoch 8.6.1992
    e_book = abs(proj - ref_book) / ref_book * 100.0
    ok = e_book <= 0.1
    all_ok &= ok
    print(f"    {'Groesse':<34}{'App':>10}{'Cowan':>10}{'Abw.%':>9}  Status")
    print(f"    {'projiziertes Hoch':<34}{_fmt(proj):>10}{_fmt(ref_book):>10}"
          f"{_fmt(e_book,3):>9}  {'OK' if ok else 'FEHLER'}")
    print(f"    -> tatsaechliches Markt-Hoch: {actual_mkt}   "
          f"(Cowans Projektionsfehler: {_fmt(abs(proj-actual_mkt)/actual_mkt*100,3)} %)")

    print("\n" + line)
    if all_ok:
        print("ERGEBNIS:  ALLE PRUEFUNGEN BESTANDEN")
        print("Der Projektor fixiert den naechsten Wendepunkt (60 Grad) und trifft")
        print("Cowans veroeffentlichte Achsen-Projektion 1:1.")
    else:
        print("ERGEBNIS:  ABWEICHUNG GEFUNDEN - bitte pruefen.")
    print(line)
    return all_ok


if __name__ == "__main__":
    run_verification()
