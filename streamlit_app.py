"""
Cowan Toolkit - Streamlit UI (run in YOUR environment):

    pip install -r requirements.txt
    streamlit run streamlit_app.py

The visual wrapper on top of the verified engine. Load BTC (ccxt), Gold, a CSV,
or the demo series; set the 'squaring' scale; edit the pivots by hand (Cowan
chooses points himself - so can you); see PTV legs, planetary axes and confluences
on the chart; and run the selectivity test.
"""

import datetime
import numpy as np
import pandas as pd
import streamlit as st
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from cowan_data import Bar, make_demo_series, detect_pivots, fetch_ccxt
from cowan_geometry import Pivot
from cowan_app import run_pipeline, build_legs, leg_ratios, project_next, bar_jd
from cowan_planets import julian_day, jd_to_date
from cowan_confluence import summarize
import cowan_backtest

st.set_page_config(page_title="Cowan Toolkit", layout="wide")
PAIR_COLORS = {"S-U": "tab:purple", "J-S": "tab:green", "J-U": "tab:orange"}


# --------------------------------------------------------------------------
# data loading
# --------------------------------------------------------------------------
def load_bars(source, **kw):
    if source == "Demo":
        return make_demo_series(n=kw["n"], seed=kw["seed"])
    if source == "CSV":
        df = pd.read_csv(kw["file"])
        cols = {c.lower(): c for c in df.columns}
        h, l, c = cols.get("high"), cols.get("low"), cols.get("close")
        return [Bar(i, float(r[h]), float(r[l]), float(r[c])) for i, r in df.iterrows()]
    if source == "CCXT (Live)":
        return fetch_ccxt(kw["exchange"], kw["symbol"], kw["timeframe"], kw["limit"])
    return []


# --------------------------------------------------------------------------
# chart
# --------------------------------------------------------------------------
def plot_chart(bars, rep, start_date, bar_days):
    jd0 = bar_jd(start_date, bar_days, 0)
    n = len(bars)
    fig, ax = plt.subplots(figsize=(12, 6))
    ax.plot([b.index for b in bars], [b.close for b in bars], color="0.45", lw=0.8, zorder=1)

    for lg in rep["legs"]:
        ax.plot([lg["from_idx"], lg["to_idx"]], [lg["from_price"], lg["to_price"]],
                color="tab:blue", lw=1.3, alpha=0.75, zorder=3)
    for p in rep["pivots"]:
        ax.scatter(p.trading_day_index, p.price, color="black", s=28, zorder=5)

    for a in rep["axes"]:
        x = (a["jd"] - jd0) / bar_days
        if 0 <= x <= n - 1:
            ax.axvline(x, color=PAIR_COLORS.get(a["pair"], "grey"), lw=0.7, alpha=0.45, zorder=2)

    for c in rep["confluences"]:
        if c["confluence"]:
            x = (c["geo"]["jd"] - jd0) / bar_days
            ax.scatter(x, c["geo"].get("price", np.nan), color="red", marker="*", s=160, zorder=6)

    if rep["projection"]["status"] == "ok":
        ax.scatter(rep["projection"]["c_bar"], rep["projection"]["c_price"],
                   color="tab:red", marker="D", s=55, zorder=6, label="Projektion")
        ax.legend(loc="upper left", fontsize=8)

    ax.set_xlabel("Bar-Index"); ax.set_ylabel("Preis")
    ax.set_title("Preis + PTV-Beine (blau) + Planeten-Achsen (senkrecht) + Confluence (rote Sterne)")
    fig.tight_layout()
    return fig


def pivots_to_df(pivots):
    return pd.DataFrame([{"bar_index": int(p.trading_day_index), "price": round(p.price, 4),
                          "typ": "H" if p.label.endswith("H") else "L"} for p in pivots])

def df_to_pivots(df):
    df = df.dropna().sort_values("bar_index")
    return [Pivot(label=f"{int(r.bar_index)}:{str(r.typ)[:1].upper()}",
                  price=float(r.price), trading_day_index=float(int(r.bar_index)))
            for r in df.itertuples()]


# --------------------------------------------------------------------------
# UI
# --------------------------------------------------------------------------
st.title("Cowan Toolkit  -  Four-Dimensional Structures & Cycles")
st.caption("Geometrie (Teil I) + Planeten (Lektion VIII) + Composite (IX) + Confluence, "
           "gegen das Buch verifiziert. Standard automatisch; Pivots von Hand editierbar.")

with st.sidebar:
    st.header("Daten")
    source = st.radio("Quelle", ["Demo", "CSV", "CCXT (Live)"])
    kw = {}
    if source == "Demo":
        kw["n"] = st.slider("Bars", 300, 3000, 1500, 100)
        kw["seed"] = st.number_input("Seed", 0, 9999, 7)
    elif source == "CSV":
        kw["file"] = st.file_uploader("CSV (Spalten high, low, close)", type=["csv"])
    else:
        kw["exchange"] = st.text_input("Boerse (ccxt)", "binance")
        kw["symbol"] = st.text_input("Symbol", "BTC/USDT")
        kw["timeframe"] = st.selectbox("Timeframe", ["1d", "4h", "1h", "1w"], 0)
        kw["limit"] = st.slider("Anzahl Bars", 100, 1000, 500, 50)

    st.header("Datum / Zeit")
    start_date = st.date_input("Startdatum (Bar 0)", datetime.date(2015, 1, 1))
    bar_days = st.number_input("Tage pro Bar", 0.04, 30.0, 1.0)

    st.header("Cowan-Parameter")
    scale = st.number_input("Skalierung (Preis pro Bar) - das 'Squaring'", 0.001, 100000.0, 1.0)
    left = st.slider("Pivot-Fenster links", 2, 60, 25)
    right = st.slider("Pivot-Fenster rechts", 2, 60, 25)
    tol_days = st.slider("Confluence-Toleranz (Tage)", 1, 45, 12)

# load data
try:
    bars = load_bars(source, **kw)
except Exception as e:
    st.error(f"Daten konnten nicht geladen werden: {e}")
    st.stop()
if not bars:
    st.info("Bitte Datenquelle konfigurieren (bei CSV eine Datei hochladen).")
    st.stop()

# pivots: auto, then editable
if "pivots_df" not in st.session_state or st.session_state.get("src_sig") != (source, len(bars)):
    st.session_state.pivots_df = pivots_to_df(detect_pivots(bars, left, right))
    st.session_state.src_sig = (source, len(bars))

c1, c2 = st.columns([1, 3])
with c1:
    st.subheader("Pivots (editierbar)")
    if st.button("Auf Auto zuruecksetzen"):
        st.session_state.pivots_df = pivots_to_df(detect_pivots(bars, left, right))
    edited = st.data_editor(st.session_state.pivots_df, num_rows="dynamic", use_container_width=True)
    st.session_state.pivots_df = edited
    if st.button("Skalierung heuristisch kalibrieren"):
        from cowan_app import build_legs as _bl
        from cowan_ratios import classify as _cl
        pv = df_to_pivots(edited)
        best, best_hits = 1.0, -1
        for k in range(241):
            s = 0.05 + (6.0 - 0.05) * k / 240
            legs = _bl(pv, s)
            hits = sum(1 for i in range(len(legs) - 1)
                       if _cl(legs[i]["ptv"], legs[i + 1]["ptv"], 1.0)["best"]["dev"] <= 1.0)
            if hits > best_hits:
                best, best_hits = s, hits
        st.warning(f"Beste In-Sample-Skalierung ~ {best:.3f} ({best_hits} Treffer). "
                   f"Achtung: in-sample, KEIN Edge - out-of-sample pruefen!")

pivots = df_to_pivots(edited)
rep = run_pipeline(bars, scale=scale, left=left, right=right, manual_pivots=pivots,
                   start_date=start_date, bar_days=bar_days, tol_days=tol_days)

with c2:
    m = st.columns(4)
    hits, total = summarize(rep["confluences"])
    n_ratio = sum(1 for x in rep["ratios"] if x["match"])
    m[0].metric("Pivots", len(rep["pivots"]))
    m[1].metric("Planeten-Achsen", len(rep["axes"]))
    m[2].metric("Confluences", f"{hits}/{total}")
    m[3].metric("Cowan-Ratios", f"{n_ratio}/{len(rep['ratios'])}")
    st.pyplot(plot_chart(bars, rep, start_date, bar_days))

st.subheader("Ratio-Beziehungen (aufeinanderfolgende Beine)")
st.dataframe(pd.DataFrame([{"Beine": f"{x['leg_a']}->{x['leg_b']}", "Ratio": round(x["ratio"], 3),
                            "Cowan-Typ": x["match"] or "-", "Abw.%": round(x["dev"], 2)}
                           for x in rep["ratios"]]), use_container_width=True, height=240)

st.subheader("Confluence (Wendepunkt auf Planeten-Achse)")
conf_rows = [{"Wendepunkt": f"{jd_to_date(c['geo']['jd'])}", "Achse": c["axis"]["pair"],
              "Grad": int(c["axis"]["deg"]), "Achsen-Datum": f"{c['axis']['ymd']}",
              "Abstand (Tage)": int(c["gap_days"])}
             for c in rep["confluences"] if c["confluence"]]
st.dataframe(pd.DataFrame(conf_rows) if conf_rows else pd.DataFrame({"Info": ["keine Confluence"]}),
             use_container_width=True)

st.subheader("Selektivitaets-Test (schlaegt es den Zufall?)")
st.caption("Surrogat-Daten: gleiche Renditeverteilung, zerstoerte Zeitstruktur. "
           "p < 0,05 = echte Struktur, nicht Rauschen.")
nsur = st.slider("Surrogate", 50, 500, 200, 50)
if st.button("Test laufen lassen"):
    with st.spinner("Surrogate rechnen..."):
        res = cowan_backtest.selectivity_test(bars, n_surrogates=nsur, scale=scale, left=left,
                                              right=right, start_date=start_date,
                                              bar_days=bar_days, tol_days=tol_days)
    for name, key in [("Confluence", "confluence"), ("Cowan-Ratios", "ratio")]:
        s = res[key]
        verdict = "SIGNAL (p<0,05)" if s["p"] < 0.05 else "kein Signal"
        st.write(f"**{name}** — echt {s['real']*100:.1f}% | Zufall {s['null_mean']*100:.1f}% "
                 f"(SD {s['null_std']*100:.1f}%) | z {s['z']:+.2f} | p {s['p']:.3f} -> {verdict}")

with st.expander("Composite-Referenz (Cowans DJIA 1982-1987, Lektion IX)"):
    st.caption("Methode: Summe der Planeten-Harmonischen MULTIPLIZIERT mit dem Trend. "
               "Beobachtete Parameter (Orb/Phase/Amplitude/Trend) nach Cowan.")
    if st.button("Composite rendern"):
        from cowan_composite import build_composite, cowan_1982_1987_components, render
        r = build_composite((1982, 8, 1), (1987, 11, 1), cowan_1982_1987_components())
        render(r, "/tmp/_composite.png")
        st.image("/tmp/_composite.png")

st.caption("Hinweis: JPL-Bahnelemente ~1800-2050. Skalierung und der 'charakteristische Koerper' "
           "sind marktspezifisch. Der Selektivitaets-Test ist der ehrliche Schiedsrichter.")
