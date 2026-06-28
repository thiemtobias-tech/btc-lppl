# -*- coding: utf-8 -*-
"""
app.py — BTC LPPL-Fitter (Sornette), EINE Datei, keine internen Importe.

Schaetzt das kritische Datum tc (Top oder Tief), omega und m aus dem Kurs und
legt die tc-Verteilung gegen ein Zielfenster. Endogenes Modell ohne externe Uhr
- gedacht als unabhaengige Gegenprobe zu Carolan/Hurst/Lunation.

Start lokal:  streamlit run app.py
Deploy:       Repo (app.py + requirements.txt) -> share.streamlit.io -> app.py

Methodik: Johansen-Ledoit-Sornette mit Filimonov-Sornette-Reparametrisierung
(nur 3 nichtlineare Parameter tc,m,omega; A,B,C1,C2 per OLS). Filter:
0.1<=m<=0.9 ; 6<=omega<=13 ; B<0 (Top) bzw. B>0 (Tief) ; Daempfung>=1.
"""
from __future__ import annotations
import datetime as dt
import numpy as np
import pandas as pd
from scipy.optimize import least_squares
import streamlit as st

# ===========================================================================
#  ENGINE
# ===========================================================================

def day_to_date(start_date, day):
    return start_date + pd.Timedelta(days=float(day))


def _linear_solve(tc, m, omega, t, y):
    tau = tc - t
    if np.any(tau <= 0):
        return None, None, np.inf
    f = tau ** m
    lt = np.log(tau)
    g = f * np.cos(omega * lt)
    h = f * np.sin(omega * lt)
    X = np.column_stack([np.ones_like(t), f, g, h])
    try:
        beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    except np.linalg.LinAlgError:
        return None, None, np.inf
    resid = y - X @ beta
    return beta, resid, float(resid @ resid)


def _residuals_for_ls(theta, t, y):
    tc, m, omega = theta
    _, resid, _ = _linear_solve(tc, m, omega, t, y)
    if resid is None:
        return np.full_like(y, 1e3)
    return resid


def fit_lppl(t, y, n_starts=200, tc_max_frac=0.25, seed=0, mode="top"):
    if mode not in ("top", "bottom"):
        raise ValueError("mode muss 'top' oder 'bottom' sein.")
    rng = np.random.default_rng(seed)
    t = np.asarray(t, float); y = np.asarray(y, float)
    span = t[-1] - t[0]
    tc_lo = t[-1] + 1.0
    tc_hi = t[-1] + tc_max_frac * span
    lower = np.array([tc_lo, 0.05, 4.0])
    upper = np.array([tc_hi, 0.99, 15.0])
    fits = []
    for _ in range(n_starts):
        x0 = [rng.uniform(tc_lo, tc_hi), rng.uniform(0.1, 0.9), rng.uniform(6.0, 13.0)]
        try:
            res = least_squares(_residuals_for_ls, x0=x0, bounds=(lower, upper),
                                args=(t, y), method="trf", max_nfev=2000,
                                ftol=1e-10, xtol=1e-10)
        except Exception:
            continue
        tc, m, omega = res.x
        beta, _, rss = _linear_solve(tc, m, omega, t, y)
        if beta is None:
            continue
        A, B, C1, C2 = beta
        C = np.hypot(C1, C2)
        damping = (m * abs(B)) / (omega * C) if C > 0 else np.inf
        b_ok = (B < 0) if mode == "top" else (B > 0)
        valid = (0.1 <= m <= 0.9 and 6.0 <= omega <= 13.0 and b_ok and damping >= 1.0)
        fits.append(dict(tc=tc, m=m, omega=omega, A=A, B=B, C1=C1, C2=C2,
                         rss=rss, damping=damping, valid=valid))
    fits.sort(key=lambda d: d["rss"])
    return fits

# ===========================================================================
#  DATEN (live)
# ===========================================================================

SOURCES = ["Yahoo (BTC-USD)", "Coinbase", "Kraken", "Binance"]
_CCXT_SYMBOL = {"Coinbase": "BTC/USD", "Kraken": "BTC/USD", "Binance": "BTC/USDT"}


def fetch_prices(source, days=1100):
    if source.startswith("Yahoo"):
        try:
            import yfinance as yf
            d = yf.download("BTC-USD", period=f"{days}d", interval="1d",
                            progress=False, auto_adjust=True).reset_index()
            out = pd.DataFrame({"date": pd.to_datetime(d["Date"]),
                                "price": pd.to_numeric(d["Close"].squeeze(), errors="coerce")}).dropna()
            if out.empty:
                raise RuntimeError("Yahoo lieferte keine Daten.")
            return out.sort_values("date").reset_index(drop=True)
        except Exception as e:
            raise RuntimeError(f"Yahoo-Download fehlgeschlagen: {e}")
    try:
        import ccxt, time
    except Exception:
        raise RuntimeError("Paket 'ccxt' fehlt (requirements.txt).")
    sym = _CCXT_SYMBOL.get(source)
    ex_cls = {"Coinbase": "coinbase", "Kraken": "kraken", "Binance": "binance"}.get(source)
    if not sym or not ex_cls:
        raise RuntimeError(f"Unbekannte Quelle: {source}")
    try:
        ex = getattr(ccxt, ex_cls)()
        cursor = ex.parse8601((dt.datetime.utcnow() - dt.timedelta(days=days)).isoformat())
        rows = []
        for _ in range(20):
            batch = ex.fetch_ohlcv(sym, timeframe="1d", since=cursor, limit=1000)
            if not batch:
                break
            rows += batch
            cursor = batch[-1][0] + 86_400_000
            if len(batch) < 1000:
                break
            time.sleep(ex.rateLimit / 1000)
        if not rows:
            raise RuntimeError("Keine OHLCV-Daten erhalten.")
        df = pd.DataFrame(rows, columns=["ts", "o", "h", "l", "c", "v"]).drop_duplicates("ts")
        return pd.DataFrame({"date": pd.to_datetime(df["ts"], unit="ms"),
                             "price": df["c"].astype(float)}).sort_values("date").reset_index(drop=True)
    except Exception as e:
        raise RuntimeError(f"{source}-Download fehlgeschlagen: {e}")

# ===========================================================================
#  KENNZAHLEN + PLOT
# ===========================================================================

def summarize(data, fits, target_lo, target_hi, mode="top"):
    start = data["date"].iloc[0]
    valids = [f for f in fits if f["valid"]]
    res = dict(n_fits=len(fits), n_valid=len(valids), mode=mode,
               label=("TOP" if mode == "top" else "TIEF"), valids=valids,
               start=start, last=data["date"].iloc[-1])
    if not valids:
        res.update(median_tc=None, q25=None, q75=None, share_in_window=0.0, best=None)
        return res
    tcs = np.array([day_to_date(start, f["tc"]).value for f in valids], dtype="int64")
    res["median_tc"] = pd.Timestamp(np.median(tcs).astype("datetime64[ns]"))
    res["q25"] = pd.Timestamp(np.quantile(tcs, 0.25).astype("datetime64[ns]"))
    res["q75"] = pd.Timestamp(np.quantile(tcs, 0.75).astype("datetime64[ns]"))
    in_win = [(target_lo <= day_to_date(start, f["tc"]) <= target_hi) for f in valids]
    res["share_in_window"] = float(100.0 * np.mean(in_win))
    b = valids[0]
    res["best"] = dict(tc=day_to_date(start, b["tc"]), m=b["m"], omega=b["omega"],
                       B=b["B"], damping=b["damping"], A=b["A"], C1=b["C1"],
                       C2=b["C2"], tc_day=b["tc"])
    return res


def build_figure(data, summary, target_lo, target_hi, top_k=30):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    start = data["date"].iloc[0]
    t = (data["date"] - start).dt.days.to_numpy(float)
    y = np.log(data["price"].to_numpy(float))
    fits = summary["valids"][:top_k]
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(11, 8),
                                   gridspec_kw={"height_ratios": [3, 1]})
    ax1.plot(data["date"], y, color="black", lw=1.3, label="ln(BTC)")
    for f in fits:
        tc = f["tc"]; tt = np.linspace(t[0], tc - 1e-6, 400); tau = tc - tt
        model = (f["A"] + f["B"] * tau ** f["m"] + tau ** f["m"] *
                 (f["C1"] * np.cos(f["omega"] * np.log(tau)) +
                  f["C2"] * np.sin(f["omega"] * np.log(tau))))
        ax1.plot([day_to_date(start, x) for x in tt], model, color="tab:red", alpha=0.10, lw=0.8)
        ax1.axvline(day_to_date(start, tc), color="tab:red", alpha=0.10, lw=0.8)
    ax1.axvspan(target_lo, target_hi, color="tab:blue", alpha=0.18, label="Zielfenster")
    ax1.set_ylabel("ln(Preis)")
    ax1.set_title(f"LPPL-Fits (rot) ueber ln(BTC) - rote Linien = tc ({summary['label']})")
    ax1.legend(loc="upper left")
    ax1.xaxis.set_major_locator(mdates.AutoDateLocator())
    ax1.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
    plt.setp(ax1.get_xticklabels(), rotation=45, ha="right")
    ax2.hist([day_to_date(start, f["tc"]) for f in fits], bins=24, color="tab:red", alpha=0.7)
    ax2.axvspan(target_lo, target_hi, color="tab:blue", alpha=0.22)
    ax2.set_title(f"Verteilung der tc ({summary['label']}) - blau = Zielfenster")
    ax2.xaxis.set_major_locator(mdates.AutoDateLocator())
    ax2.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
    plt.setp(ax2.get_xticklabels(), rotation=45, ha="right")
    fig.tight_layout()
    return fig

# ===========================================================================
#  STREAMLIT-UI
# ===========================================================================

st.set_page_config(page_title="BTC LPPL-Fitter", page_icon="📈", layout="wide")


@st.cache_data(show_spinner=False, ttl=3600)
def get_prices(source, days):
    return fetch_prices(source, days)


st.title("BTC LPPL-Fitter — Sornette-Kritikalität")
st.caption("Schätzt das kritische Datum tc (Top bzw. Tief), omega und m aus dem "
           "Kurs und legt die tc-Verteilung gegen dein Zielfenster. Endogenes "
           "Modell ohne externe Uhr — unabhängige Gegenprobe zu Carolan/Hurst/Lunation.")

with st.sidebar:
    st.header("Einstellungen")
    source = st.selectbox("Datenquelle (live)", SOURCES, index=0,
                          help="Auf Streamlit-Cloud eher Yahoo/Coinbase/Kraken; Binance lokal in DE.")
    days = st.slider("Historie (Tage)", 365, 2200, 1100, step=30)
    mode = st.radio("Modus", ["top", "bottom"], horizontal=True,
                    format_func=lambda m: "Top (Hochlauf)" if m == "top" else "Tief (Abstieg)")
    start_date = st.date_input("Fenster-Start (Zyklus-Anker)", value=dt.date(2022, 11, 21))
    c1, c2 = st.columns(2)
    target_lo = c1.date_input("Zielfenster von", value=dt.date(2026, 10, 1))
    target_hi = c2.date_input("Zielfenster bis", value=dt.date(2026, 10, 31))
    with st.expander("Feineinstellung"):
        n_starts = st.slider("Random-Starts", 50, 600, 200, step=50)
        tc_max_frac = st.slider("tc max. (Anteil Fensterlänge voraus)", 0.05, 0.5, 0.25, step=0.05)
        seed = st.number_input("Seed", value=0, step=1)
    run = st.button("🔄 Daten holen & rechnen", type="primary", use_container_width=True)

if run:
    try:
        with st.spinner(f"Lade BTC von {source} …"):
            data_all = get_prices(source, int(days))
    except Exception as e:
        st.error(f"Download fehlgeschlagen: {e}\n\nTipp: andere Quelle wählen.")
        st.stop()
    data = data_all[data_all["date"] >= pd.Timestamp(start_date)].reset_index(drop=True)
    if len(data) < 60:
        st.error("Zu wenige Datenpunkte (<60) ab dem Fenster-Start. Setze den Start früher.")
        st.stop()
    t = (data["date"] - data["date"].iloc[0]).dt.days.to_numpy(float)
    y = np.log(data["price"].to_numpy(float))
    with st.spinner(f"LPPL-Fit ({n_starts} Starts, Modus „{mode}“) …"):
        fits = fit_lppl(t, y, n_starts=int(n_starts), tc_max_frac=float(tc_max_frac),
                        seed=int(seed), mode=mode)
        s = summarize(data, fits, pd.Timestamp(target_lo), pd.Timestamp(target_hi), mode=mode)
    top = float(data["price"].iloc[-1])
    st.write(f"**{len(data)}** Tageskerzen · {data['date'].iloc[0].date()} → "
             f"{data['date'].iloc[-1].date()} · letzter Kurs ≈ **{top:,.0f}**".replace(",", "."))
    if s["n_valid"] == 0:
        sig = "Blasensignatur (Top)" if mode == "top" else "negative Blasensignatur (Tief)"
        st.warning(f"Kein gültiger LPPL-Fit ({s['n_fits']} Versuche). Lesart: derzeit "
                   f"**keine** saubere log-periodische {sig}. Echtes Ergebnis — nichts "
                   f"erzwingen. Der Tief-Modus braucht einen real fallenden Schenkel.")
        st.stop()
    m1, m2, m3, m4 = st.columns(4)
    m1.metric(f"Median tc ({s['label']})", s["median_tc"].strftime("%Y-%m-%d"))
    m2.metric("IQR", f"{s['q25'].strftime('%d.%m.%y')}–{s['q75'].strftime('%d.%m.%y')}")
    m3.metric("tc im Zielfenster", f"{s['share_in_window']:.0f}%")
    m4.metric("Gültige Fits", f"{s['n_valid']}/{s['n_fits']}")
    share = s["share_in_window"]
    if share >= 50:
        st.success("Starke **endogene** Bestätigung deines Fensters — unabhängige Methode.")
    elif share >= 20:
        st.info("Teilweise Überlappung — schwaches, kein starkes Signal.")
    else:
        st.warning("tc liegt überwiegend **außerhalb** deines Fensters. Externe Uhr und "
                   "endogene Kritikalität messen hier Verschiedenes.")
    st.pyplot(build_figure(data, s, pd.Timestamp(target_lo), pd.Timestamp(target_hi)),
              use_container_width=True)
    b = s["best"]
    with st.expander("Bester Fit & Parameter für das Pine-Overlay"):
        st.write(f"- **tc** = {b['tc'].date()}　**m** = {b['m']:.3f}　**omega** = "
                 f"{b['omega']:.2f}　**B** = {b['B']:+.4f}　**Dämpfung** = {b['damping']:.2f}")
        st.code(f"tc_day = {b['tc_day']:.2f}   // Tage ab {s['start'].date()}\n"
                f"m      = {b['m']:.4f}\nomega  = {b['omega']:.4f}\nA      = {b['A']:.5f}\n"
                f"B      = {b['B']:.6f}\nC1     = {b['C1']:.6f}\nC2     = {b['C2']:.6f}",
                language="text")
else:
    st.info("Links Einstellungen wählen, dann **Daten holen & rechnen**.")
