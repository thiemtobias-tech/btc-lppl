"""
Cowan Confluence - Layer 4: where an INDEPENDENT geometric turning point aligns
in time with a planetary axis.

The whole value of this layer rests on independence: the geometry (Part I) is
computed from price pivots and the 'squaring' scale; the planetary axes (Part II)
are computed from ephemerides. They share NO input. So when a geometric turning
point and a planetary axis land on the same date, that agreement is meaningful -
not a circular restatement of one method in the other's terms.
"""

from cowan_planets import julian_day, jd_to_date, find_axis_crossings

DEFAULT_PAIRS = [
    ("Jupiter", "Uranus", "J-U"),   # ~7 months per 15 deg
    ("Jupiter", "Saturn", "J-S"),   # ~10 months per 15 deg
    ("Saturn",  "Uranus", "S-U"),   # ~22 months per 15 deg
]


def planetary_axes_in_range(start_ymd, end_ymd, pairs=DEFAULT_PAIRS, step_deg=15.0):
    """All 15-degree axis crossings for several planet pairs over a date range."""
    out = []
    for faster, slower, label in pairs:
        for (y, m, d), deg in find_axis_crossings(faster, slower, start_ymd, end_ymd, step_deg):
            out.append({"jd": julian_day(y, m, d), "ymd": (y, m, d), "pair": label, "deg": deg})
    out.sort(key=lambda x: x["jd"])
    return out


def find_confluences(geometric_events, axes, tol_days=12):
    """
    For each geometric turning point, find the nearest planetary axis and the gap.
    Flag a confluence when the gap is within tol_days.
    geometric_events: list of {'jd', 'label'}.
    """
    res = []
    for ev in geometric_events:
        if axes:
            nearest = min(axes, key=lambda a: abs(a["jd"] - ev["jd"]))
            gap = abs(nearest["jd"] - ev["jd"])
        else:
            nearest, gap = None, None
        res.append({"geo": ev, "axis": nearest, "gap_days": gap,
                    "confluence": gap is not None and gap <= tol_days})
    return res


def summarize(confluences):
    hits = sum(1 for c in confluences if c["confluence"])
    return hits, len(confluences)
