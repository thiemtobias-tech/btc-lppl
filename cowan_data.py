"""
Cowan Data Adapter - Layer 0: get OHLC bars and detect pivots ('points of force').

LIVE FEEDS (run in YOUR environment - this sandbox has no network):
  - BTC : ccxt (Binance / Kraken / Bybit), 24/7, continuous bars.
  - Gold: MT5 / Pepperstone, or a data provider (XAUUSD / GC future) - has
          sessions + weekends.

OFFLINE: load_csv(), or make_demo_series() - a synthetic random walk purely to
exercise the pipeline. It carries NO market meaning and is labelled DEMO.

TIME CONVENTION (Cowan adapted per market):
  - 24/7 markets (BTC): time-unit = 1 bar; no session subtraction.
  - session markets (Gold): non-trading time is simply absent from the feed
    (weekends/holidays), so counting bars already implements Cowan's rule of
    subtracting non-trading time.
  => in both cases the TIME leg between two pivots = number of bars between them.
     The `scale` factor then makes price and bar-count commensurable
     ('squaring the chart').
"""

import math
import random
from dataclasses import dataclass, field
from cowan_geometry import Pivot


@dataclass
class Bar:
    index: int
    high: float
    low: float
    close: float


# --------------------------------------------------------------------------
# LIVE FEED - BTC via ccxt (runs in the user's environment)
# --------------------------------------------------------------------------
def fetch_ccxt(exchange="binance", symbol="BTC/USDT", timeframe="1d", limit=500):
    """
    Fetch OHLC via ccxt. Requires `pip install ccxt` and network access.
    Returns list[Bar]. Raises a clear message if unavailable.
    """
    try:
        import ccxt  # noqa
    except ImportError:
        raise RuntimeError(
            "ccxt nicht installiert. In deiner Umgebung:  pip install ccxt")
    ex = getattr(ccxt, exchange)()
    ohlcv = ex.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
    # ohlcv rows: [ts, open, high, low, close, volume]
    return [Bar(i, row[2], row[3], row[4]) for i, row in enumerate(ohlcv)]


# --------------------------------------------------------------------------
# OFFLINE - CSV loader and synthetic demo series
# --------------------------------------------------------------------------
def load_csv(path, high_col="high", low_col="low", close_col="close"):
    """Load OHLC from a CSV with header row. Returns list[Bar]."""
    import csv
    bars = []
    with open(path, newline="") as f:
        for i, row in enumerate(csv.DictReader(f)):
            bars.append(Bar(i, float(row[high_col]),
                            float(row[low_col]), float(row[close_col])))
    return bars


def make_demo_series(n=200, seed=7, start=100.0, drift=0.03, vol=1.4):
    """
    DEMO ONLY - synthetic random walk. NOT real market data, NO market claim.
    Used to show the pipeline runs end-to-end without a live feed.
    """
    rng = random.Random(seed)
    close = start
    bars = []
    for i in range(n):
        close += drift + rng.gauss(0, vol)
        wick = abs(rng.gauss(0, vol))
        bars.append(Bar(i, close + wick, close - wick, close))
    return bars


# --------------------------------------------------------------------------
# PIVOT DETECTION - the 'points of force' (auto; user may override later)
# --------------------------------------------------------------------------
def _raw_pivots(bars, left, right):
    """Window pivot detection. Returns list of (index, price, kind)."""
    highs = [b.high for b in bars]
    lows = [b.low for b in bars]
    out = []
    for i in range(left, len(bars) - right):
        win_hi = highs[i - left:i + right + 1]
        win_lo = lows[i - left:i + right + 1]
        if highs[i] == max(win_hi) and win_hi.count(highs[i]) == 1:
            out.append((i, highs[i], "high"))
        if lows[i] == min(win_lo) and win_lo.count(lows[i]) == 1:
            out.append((i, lows[i], "low"))
    out.sort(key=lambda x: x[0])
    return out


def detect_pivots(bars, left=5, right=5):
    """
    Detect turning points and collapse them into a clean alternating zigzag
    (a high must be followed by a low and vice versa; keep the more extreme of
    any same-type run). Returns list[Pivot] with trading_day_index = bar index.
    """
    raw = _raw_pivots(bars, left, right)
    zig = []
    for idx, price, kind in raw:
        if not zig:
            zig.append((idx, price, kind))
            continue
        last_idx, last_price, last_kind = zig[-1]
        if kind == last_kind:
            # same type in a row -> keep the more extreme one
            keep_new = (price > last_price) if kind == "high" else (price < last_price)
            if keep_new:
                zig[-1] = (idx, price, kind)
        else:
            zig.append((idx, price, kind))
    return [Pivot(label=f"{k[0]}:{kind[0].upper()}", price=price,
                  trading_day_index=float(idx))
            for (idx, price, kind) in zig
            for k, kind in [((idx,), kind)]]  # keep label readable


if __name__ == "__main__":
    bars = make_demo_series()
    pivots = detect_pivots(bars, left=5, right=5)
    print(f"DEMO-Serie: {len(bars)} Bars, {len(pivots)} Pivots erkannt")
    for p in pivots[:12]:
        print(f"  Bar {int(p.trading_day_index):>3}  Preis {p.price:8.2f}  ({p.label})")
