# Installation (lokal auf dem Mac)

Läuft auf MacBook oder Mac Mini (nicht iPhone/iPad — Python/Streamlit brauchen
einen Rechner). Für iPhone-Zugriff siehe `DEPLOY.md`.

## 1. Dateien holen
`cowan_toolkit.zip` herunterladen, im Finder doppelklicken → Ordner `cowan_toolkit`.

## 2. Terminal öffnen
⌘ + Leertaste → „Terminal" tippen → Enter. Jede folgende Zeile mit Enter bestätigen.

## 3. Python prüfen
```
python3 --version
```
`Python 3.10` oder höher → weiter. Sonst von python.org den macOS-Installer laden,
`.pkg` doppelklicken, durchklicken, Terminal neu öffnen.

## 4. In den Ordner wechseln
`cd` tippen, **Leerzeichen**, dann den Ordner `cowan_toolkit` aus dem Finder ins
Terminal ziehen → Enter. Kontrolle:
```
ls
```
Die `.py`-Dateien und `README.md` sollten erscheinen.

## 5. Saubere Umgebung (empfohlen)
```
python3 -m venv venv
source venv/bin/activate
```
Am Zeilenanfang steht jetzt `(venv)`.

## 6. Pakete installieren
```
pip install -r requirements.txt
```

## 7. Verifikation
```
python cowan_app.py
```
Am Ende muss stehen: `[Motor gegen das Buch verifiziert: JA]`.

## 8. Oberfläche starten
```
streamlit run streamlit_app.py
```
Browser öffnet sich (sonst `http://localhost:8501`). Erst Quelle „Demo" testen,
dann „CCXT (Live)" mit `binance` / `BTC/USDT` / `1d`.

## Beenden / Wiederstarten
`Strg + C` beendet die App. Nächstes Mal: in den Ordner wechseln (Schritt 4),
`source venv/bin/activate`, `streamlit run streamlit_app.py`.

## Wenn etwas hakt
- `command not found: python` → `python3` statt `python`.
- pip: „externally-managed-environment" → Schritt 5 (venv) machen, oder hinten
  `--break-system-packages` anhängen.
- `streamlit: command not found` → `python -m streamlit run streamlit_app.py`.
- CCXT-Fehler → Internet prüfen; Binance-Kursdaten gehen ohne Login/Keys.
- Gold: statt CCXT den CSV-Upload nutzen (Spalten `high, low, close`), Export aus
  Pepperstone/MT5 oder einem Datenprovider.
