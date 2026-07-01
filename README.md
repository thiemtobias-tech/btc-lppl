# Cowan Toolkit — Four-Dimensional Structures & Cycles

Ein Werkzeugkasten, der die Methoden aus Bradley F. Cowans „Four-Dimensional
Stock Market Structures and Cycles" **originalgetreu** umsetzt — die Mathematik
1:1 wie im Buch, ohne eigene Interpretationen — und **jede Ebene gegen Cowans
eigene veröffentlichte Zahlen** verifiziert.

## Grundprinzip

Zwei getrennte Fragen, die das Paket getrennt beantwortet:

1. **Ist es originalgetreu?** — Ja, und beweisbar: Jeder Motor reproduziert
   Cowans eigene durchgerechnete Beispiele (PTV = 235,7 / Projektion 3423,27 /
   √-Verhältnisse / Planeten-Grade). Die Verifikation läuft mit `python cowan_app.py`.
2. **Trifft es den Markt?** — Das ist **nicht** dasselbe. „Baubar" heißt nicht
   „prädiktiv". Diese Frage beantwortet der Selektivitäts-Test (`cowan_backtest.py`)
   ehrlich: Schlägt echte Struktur den Zufall (p < 0,05)? Auf Zufallsdaten muss
   „kein Signal" herauskommen — und tut es.

Cowans Methode ist an zwei Stellen **bewusst diskretionär**: die Wahl der Pivots
(„points of force") und der Skalierungsfaktor („Squaring" des Charts). Dafür gibt
es im Buch keine mechanische Regel. Deshalb: die App rechnet Cowans Mathematik
exakt, und **du triffst die Urteile, die auch Cowan trifft** — Standard automatisch,
Pivots von Hand editierbar.

## Module

| Datei | Ebene | Inhalt |
|---|---|---|
| `cowan_geometry.py` | 1 | Price-Time Radius Vector (PTV), Zeit-Modell, Vorwärts/Rückwärts-Projektion |
| `cowan_ratios.py` | 1 | Verhältnis-Detektor: √2, √3, √5, √10, π, Oktaven; PHI nur als Nebenprodukt |
| `cowan_projection.py` | 1 | 60°-Projektion des nächsten Wendepunkts + Ellipsen-Achsen-Projektion |
| `cowan_data.py` | 0 | Daten-Adapter (CCXT/CSV/Demo) + Pivot-Erkennung |
| `cowan_planets.py` | 2 | reiner Kepler-Löser: heliozentrische Längen, Synodalwinkel, Achsen (Lektion VIII) |
| `cowan_composite.py` | 3 | Composite = Summe der Harmonischen × Trend (Lektion IX), gerendert als Chart |
| `cowan_confluence.py` | 4 | Geometrie ↔ Planeten: unabhängige Wendepunkte, die auf eine Achse fallen |
| `cowan_app.py` | — | integrierter Motor + Ein-Kommando-Verifikation gegen das Buch |
| `cowan_backtest.py` | 5 | Selektivitäts-Test (Surrogat-Daten) — der ehrliche Schiedsrichter |
| `streamlit_app.py` | UI | Oberfläche: Daten laden, Pivots editieren, Chart, Ratios, Confluence, Test |

Lektion X (das 4D-Würfel-Kapitel) ist bei Cowan reine Deutung/Visualisierung und
**kein Signalgeber** — daher bewusst nicht als Motor umgesetzt.

## Installation

```bash
pip install -r requirements.txt
```

## Ausführen

```bash
python cowan_app.py        # verifiziert ALLE Ebenen gegen das Buch + integrierter Demo-Lauf
python cowan_backtest.py   # Selektivitaets-Test (Demo -> muss "kein Signal" zeigen)
python cowan_composite.py  # rendert den Composite-Chart 1982-1987
streamlit run streamlit_app.py   # die Oberflaeche
```

## Echte Daten anbinden

- **BTC** (24/7, gratis): in der UI Quelle „CCXT (Live)" wählen, z.B. `binance`,
  `BTC/USDT`, `1d`. Im Code: `cowan_data.fetch_ccxt("binance", "BTC/USDT", "1d", 500)`.
- **Gold**: kein einzelner kanonischer Handelsplatz. Zwei Wege — dein
  **Pepperstone**-Konto (MT5-API, `XAUUSD`) oder ein Provider (Twelve Data /
  Polygon / Alpha Vantage) bzw. der GC-Future. Als CSV (Spalten `high, low, close`)
  über den CSV-Upload einspielen.
- TradingView lässt sich **nicht** als Feed anzapfen (kein offizieller Markt-API).

Zeit-Konvention: Bei 24/7-Märkten (BTC) ist die Zeiteinheit = 1 Bar (kein Abzug
von Handelspausen). Bei Session-Märkten (Gold) fehlen Wochenenden/Feiertage ohnehin
im Feed — das setzt Cowans Regel „Nicht-Handelszeit abziehen" bereits um.

## Die zwei Regler

- **Skalierung** (Preis pro Bar): Cowans „Squaring". Nur bei richtiger Skala gelten
  konstante PTV-Länge, 60°-Winkel und die sauberen √-Verhältnisse. Ein Kalibrator
  schlägt eine Skala vor — aber **in-sample**, also kein Edge; out-of-sample prüfen.
- **Pivots**: automatisch erkannt, in der UI editierbar (hinzufügen/verschieben/
  löschen), „Auf Auto zurücksetzen" jederzeit möglich.

## Ehrliche Einschränkungen

- **Skalierungs-Empfindlichkeit**: Bei falscher Skala degeneriert die Geometrie
  (flache Beine, keine Vorwärts-Projektion). Der Motor meldet das transparent,
  statt Scheinzahlen auszugeben.
- **Composite**: Cowan präsentiert ihn als Grafik mit *beobachteten* Parametern
  (Orb, Phase, Amplitude, Trend). Reproduziert sind seine **Methode** und die
  **verifizierten Achsen-Eingaben**; der exakte Kurvenverlauf hängt an den
  beobachteten Größen.
- **Ephemeriden**: reiner Kepler-Löser auf JPL-Elementen, am genauesten ~1800–2050.
  Die konventionsfreien Prüfgrößen (Synodalwinkel, Eigenbewegung) sind der
  belastbare Abgleich; absolute Tierkreis-Positionen hingen von tropisch/siderisch
  und Präzession ab.
- **Ein Fund am Rande**: Der Motor liefert für 10/1966 den Saturn-Uranus-Winkel 187°,
  im Buch steht 173° — das passt weder zu Cowans Achsen (+30° → 180°) noch zu seiner
  eigenen Angabe „7° nach der Achse" (→187°). Wahrscheinlich ein Druckfehler im Buch,
  den die Engine unabhängig aufdeckt.
- **Selektivität ist entscheidend**: Eine hohe Trefferquote allein bedeutet nichts.
  Erst wenn echte Daten die Zufalls-Basislinie schlagen, ist etwas dran.
