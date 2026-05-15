# Anspruchssystem

Desktop-Verwaltungssoftware in Python mit PyQt6 für Anspruchsprüfung und Kartenverwaltung.

## Stand Woche 1

Aktuell umgesetzt:

- Python-Projektstruktur
- virtuelle Umgebung `.venv`
- PyQt6 installiert
- startbare Desktop-App
- Hauptfenster mit Login-Platzhalter
- Eingabefelder für Benutzername und Passwort
- einfache Validierung
- Enter-Taste im Passwortfeld löst Login-Test aus
- Statusleiste im Hauptfenster
- SQLite-Datei in `data/system.db`
- Datenbankstatus sichtbar

## Projektstruktur

```text
anspruchssystem/
├── app/
├── core/
├── database/
│   └── repositories/
├── services/
├── ui/
│   ├── login/
│   ├── shell/
│   └── shared/
├── data/
├── tests/
├── main.py
├── requirements.txt
├── .gitignore
└── README.md
```

## Starten

```powershell
.\.venv\Scripts\Activate.ps1
python main.py
```

## Hinweis

Dies ist nur das technische Grundgerüst aus Woche 1.
Es gibt noch keine echte Benutzeranmeldung, keine Rollen, keine Fachlogik und keine Fallverwaltung.