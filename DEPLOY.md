# Deployment: iPhone-Zugriff über Streamlit Cloud

Ziel: die App wie die Carolan-App unter einer eigenen `…streamlit.app`-Adresse,
die du am iPhone im Browser öffnest. Das Prinzip ist dasselbe — der Code läuft
auf einem Server, dein iPhone öffnet nur die Webseite. Kein Mac im Betrieb nötig,
sobald es einmal deployt ist.

Der Ablauf: Code zu **GitHub** → auf **Streamlit Community Cloud** verbinden →
URL bekommen. Alles kostenlos. Das einmalige Hochladen geht am Mac oder direkt
im Browser (auch am iPad).

## Schritt 0 — Konten anlegen (einmalig, kostenlos)

1. **GitHub-Konto**: auf `github.com` registrieren, falls noch nicht vorhanden.
2. **Streamlit Community Cloud**: auf `share.streamlit.io` gehen und mit deinem
   GitHub-Konto anmelden („Continue with GitHub"). Das verbindet beide.

## Schritt 1 — Dateien vorbereiten

Entpacke `cowan_toolkit.zip`. Auf dem iPhone/iPad: in der **Dateien**-App auf das
ZIP tippen, es entpackt sich zum Ordner. Du brauchst diese Dateien (die Charts/PNG
nicht — die erzeugt die App selbst):

```
cowan_geometry.py      cowan_planets.py      cowan_app.py
cowan_ratios.py        cowan_composite.py    cowan_backtest.py
cowan_projection.py    cowan_confluence.py   streamlit_app.py
cowan_data.py          requirements.txt
```

**Wichtig:** Alle `.py`-Dateien und die `requirements.txt` müssen später im
**Wurzelverzeichnis** des Repos liegen (direkt nebeneinander), sonst finden sich
die Module gegenseitig nicht.

## Schritt 2 — GitHub-Repository erstellen und Dateien hochladen

1. Auf `github.com` oben rechts **„+" → „New repository"**.
2. Name z.B. `cowan-toolkit`. Sichtbarkeit **Public** wählen (dazu unten mehr).
   „Create repository".
3. Auf der neuen Repo-Seite: **„Add file" → „Upload files"**.
4. Alle oben genannten Dateien reinziehen (Mehrfachauswahl geht). Unten
   **„Commit changes"** klicken.

Das war der einzige Schritt, der einen Datei-Upload braucht — danach ist der Mac raus.

## Schritt 3 — Auf Streamlit Cloud deployen

1. Auf `share.streamlit.io` **„Create app"** (bzw. „New app") → „Deploy a public
   app from GitHub".
2. Auswählen:
   - **Repository:** `dein-name/cowan-toolkit`
   - **Branch:** `main`
   - **Main file path:** `streamlit_app.py`
3. **„Deploy"** klicken. Streamlit installiert automatisch die `requirements.txt`
   und startet die App. Der erste Build dauert ein paar Minuten.

Optional unter „Advanced settings" kannst du die Python-Version setzen — der
Standard (aktuell 3.12/3.13) passt für dieses Paket.

## Schritt 4 — Am iPhone öffnen

Du bekommst eine URL wie `https://dein-name-cowan-toolkit.streamlit.app`. Die im
Safari am iPhone aufrufen — genau wie Carolan. Tipp: „Zum Home-Bildschirm" tippen,
dann liegt sie als App-Icon auf dem iPhone.

Erster Test: in der App Quelle **„Demo"** wählen und prüfen, dass Chart und
Confluence erscheinen. Dann **„CCXT (Live)"** mit `binance` / `BTC/USDT` / `1d`.

## Später ändern

Du willst etwas anpassen? Datei im GitHub-Repo editieren (oder neu hochladen) und
„Commit". Streamlit merkt die Änderung und **deployt automatisch neu** — nichts
weiter zu tun.

## Ehrliche Hinweise

- **Public-Repo heißt: der Code ist öffentlich sichtbar.** Das ist hier
  unproblematisch, weil nichts Geheimes drin ist — **aber lege niemals API-Keys,
  Passwörter oder ähnliches in den Code oder das Repo.** BTC-Kurse über Binance
  brauchen ohnehin keinen Login. (Private Repos gehen auch, brauchen aber eine
  extra Freigabe und sind in der Gratis-Version limitiert.)
- **BTC läuft in der Cloud problemlos** (CCXT → Binance, kein Key nötig).
- **Gold ist der Haken:** Dein **Pepperstone/MT5-Feed läuft nicht in der Cloud**,
  weil MT5 eine lokale Anwendung ist. Für Gold in der Cloud nimmst du den
  **CSV-Upload** (Spalten `high, low, close`) oder einen Provider mit API
  (z.B. Twelve Data). MT5-Daten also lokal exportieren und als CSV hochladen.
- **Die App schläft ein** nach längerer Inaktivität (wie Carolan). Beim ersten
  Aufruf danach braucht sie ~30 Sekunden zum Aufwachen — das ist normal.
- **Ressourcen** der Gratis-Version sind begrenzt (~1 GB). Der Selektivitäts-Test
  mit 200 Surrogaten läuft dort, kann aber ein paar Sekunden dauern.

## Alternative: Upload per Git (falls du am Mac bist und Git nutzt)

```bash
cd cowan_toolkit
git init
git add cowan_*.py streamlit_app.py requirements.txt
git commit -m "Cowan Toolkit"
git branch -M main
git remote add origin https://github.com/DEIN-NAME/cowan-toolkit.git
git push -u origin main
```
Danach weiter bei Schritt 3.
