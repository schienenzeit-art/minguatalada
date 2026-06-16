# Min Guata Lada — Anspruchsverwaltung

Produktive Verwaltungssoftware für Tischlein Deck Dich Vorarlberg

Desktop-Anwendung zur Prüfung von Anspruchsberechtigungen, Haushalts- und Personenverwaltung sowie Kartenausstellung. Entwickelt für den internen Betrieb des Vereins an den Standorten Bludenz, Feldkirch und Dornbirn.

[![CI](https://github.com/schienenzeit-art/minguatalada/actions/workflows/ci.yml/badge.svg)](https://github.com/schienenzeit-art/minguatalada/actions/workflows/ci.yml)

---

## Inhalt

- [Hauptfunktionen](#hauptfunktionen)
- [Systemvoraussetzungen](#systemvoraussetzungen)
- [Projektstruktur](#projektstruktur)
- [Lokales Setup](#lokales-setup)
- [Datenbank](#datenbank)
- [Authentifizierung und Benutzer](#authentifizierung-und-benutzer)
- [Testen](#testen)
- [Logging](#logging)
- [Backup und Restore](#backup-und-restore)
- [Deployment / CI/CD](#deployment--cicd)
- [Troubleshooting](#troubleshooting)
- [Roadmap](#roadmap)
- [Wartungshinweise](#wartungshinweise)
- [Kontakt](#kontakt)

---

## Hauptfunktionen

| Modul | Beschreibung |
|---|---|
| **Anspruchsprüfung** | Einnahmen-/Ausgaben-Berechnung, Grenzwertvergleich, Ergebnisprotokoll als PDF |
| **4-Augen-Regel** | Mitarbeiter darf einmal eigenständig prüfen; jede weitere Prüfung erfordert Supervisor-Freigabe |
| **Haushaltsverwaltung** | Erfassung aller Haushaltsmitglieder inkl. Kategorie für Erwachsene, 20-Jahre-Alters-Alert |
| **Personendossier** | Antragshistorie, Dokumente, Notizen, Status je Person |
| **Kartenverwaltung** | Ausstellung, Verwaltung und Ablaufüberwachung von Kundenkarten |
| **Dokumentenmanagement** | Upload, Archivierung und Kategorisierung von Belegen |
| **Aufgaben / Actionboard** | Operative To-dos, Fristensteuerung, Wiedervorlagen |
| **Reporting** | Kennzahlen, Standortauswertungen, Excel- und PDF-Export |
| **Benutzerverwaltung** | Rollen, Standortzuweisung, Passwort-Management, Sperrung |
| **System-Updates** | Integriertes Update-System via `.mugala`-Pakete mit Backup und Migrationsschutz |
| **Audit-Log** | Nachvollziehbares Protokoll aller relevanten Systemereignisse |

---

## Systemvoraussetzungen

| Komponente | Anforderung |
|---|---|
| **Betriebssystem** | Windows 10 / Windows 11 (64-Bit) |
| **Python** | 3.11 (`.python-version`), kompatibel mit 3.12 und 3.13 |
| **Virtuelle Umgebung** | `.venv` im Projektverzeichnis |
| **Datenbank** | SQLite (Standard, kein Server nötig) oder PostgreSQL via `DATABASE_URL` |
| **Build-Tool** | PyInstaller (nur für Release-Build) |
| **Paketmanager** | pip |

**Nicht erforderlich** (aktuell): Datenbankserver, Redis, Docker, Node.js (außer für lokale Icon-Tooling-Skripte).

---

## Projektstruktur

```text
minguatalada/
├── app/                        App-Bootstrap und Konfiguration
│   ├── bootstrap.py            Startpunkt: Logging, DB-Init, Login, Hauptfenster
│   ├── config.py               Pfade (DB_PATH, DATA_DIR), Secrets, JWT-Config
│   ├── container.py            Dependency-Injection-Container (ServiceContainer)
│   ├── app_registry.py         Sichtbare Apps je Rolle
│   ├── session.py              Aktuell eingeloggter Benutzer (globale Klasse)
│   └── ports.py                Repository-Interfaces (Abstract Base Classes)
│
├── core/                       Gemeinsame Enums, Konstanten, Typen
│   ├── claim_status.py         Antragsstatus + Rollenübergänge
│   ├── session.py              Session-Klasse (wird von app/session.py genutzt)
│   └── constants.py            App-Titel, NON_LOGIN_ROLES
│
├── domain/                     Reine Fachlogik ohne DB-Zugriff
│   ├── categories.py           Anspruchskategorien (CATEGORIES, CATEGORY_RENAMES)
│   └── services/
│       └── pruefung_service.py Anspruchsberechnungslogik (zustandslos)
│
├── database/                   Datenbankschema, Migrationen, Seed
│   ├── db.py                   initialize_database(), Migrationen, Healthcheck
│   ├── seed.py                 Seed-Funktionen (Standorte, Rollen, Vorlagen, …)
│   └── repositories/           Eine Klasse je Entität (ClaimRepository, UserRepository, …)
│
├── domain/                     Reine Fachlogik ohne DB-Zugriff
│   ├── categories.py           Anspruchskategorien
│   ├── types.py                ClaimSnapshot – typsicherer Ersatz für rohe dicts
│   └── services/
│       └── pruefung_service.py Anspruchsberechnungslogik (zustandslos, versioniert)
│
├── services/                   Fachlogik mit DB-Zugriff
│   ├── auth_service.py         Login, Lockout, Audit-Logging
│   ├── claim_service.py        Antragsverwaltung, persist_evaluation
│   ├── re_evaluation_service.py 4-Augen-Regel + Supervisor-Notification
│   ├── update_service.py       Update-System, Backup, Restore
│   ├── user_service.py         Benutzerverwaltung
│   ├── household_service.py    Haushaltsmitglieder
│   ├── audit_service.py        Audit-Log schreiben und lesen
│   ├── password_service.py     bcrypt-Hashing und -Verifikation
│   └── service_factory.py      Fallback-Fabriken für UI ohne DI-Container
│
├── ui/                         PyQt6-Oberfläche
│   ├── login/                  Login-Dialog
│   ├── shell/                  Hauptfenster, Workspace-Host
│   ├── pages/                  Alle Seiten (Anträge, Personen, Karten, …)
│   ├── dialogs/                Modale Dialoge
│   └── components/             Wiederverwendbare UI-Bausteine
│
├── tests/                      Automatisierte Tests (282 Tests, davon 279 ohne PostgreSQL grün)
│   ├── conftest.py             Gemeinsame Fixtures (isolierte Test-DB, Session-Helpers)
│   ├── test_auth_service.py    Auth-Tests (10 Szenarien)
│   ├── test_claim_status.py    Rollenübergänge, reine Unit-Tests
│   ├── test_re_evaluation_service.py  4-Augen-Regel (19 Tests)
│   ├── test_update_service.py  Backup, Validierung, destruktive-SQL-Block
│   ├── test_logging_audit.py   Audit-Events, kein Passwort im Log
│   ├── test_password_service.py bcrypt-Tests
│   ├── test_household_service.py Haushalt-Kategorie-Feature
│   └── test_pg_adapter_integration.py  PgConnectionAdapter gegen echtes PostgreSQL (skipped ohne TEST_DATABASE_URL)
│
├── scripts/                    Hilfsskripte (Entwicklung und Betrieb)
│   ├── reset_admin.py          Admin-Passwort zurücksetzen
│   ├── list_users.py           Benutzer in der DB anzeigen
│   ├── build_mugala.py         Update-Paket (.mugala) erstellen
│   └── smoke_pruefung.py       Schnelltest der Prüfungslogik
│
├── installer/                  Inno-Setup-Installer und Versionsinfos
│   └── setup.iss               Inno-Setup-Konfiguration
│
├── assets/                     Logo, Icons
├── data/                       Laufzeitdaten (NICHT einchecken)
│   ├── system.db               SQLite-Datenbank (Entwicklungsmodus)
│   ├── backups/                Automatische DB-Backups
│   ├── documents/              Hochgeladene Dokumente
│   ├── logs/                   Logdateien (app.log)
│   └── pdfs/                   Erzeugte PDFs
│
├── .github/workflows/ci.yml    GitHub Actions CI/CD-Pipeline
├── main.py                     Einstiegspunkt
├── requirements.txt            Abhängigkeiten (gepinnt)
├── pytest.ini                  Test-Konfiguration
├── anspruchssystem.spec        PyInstaller-Build-Konfiguration
├── build.bat                   Windows Build-Skript
├── TECHNICAL_DESIGN_DOCUMENT.md  Architektur, Komponenten, Datenmodell, Schnittstellen
├── OPERATIONS_GUIDE.md         Vereins-PC-Diagnose, Backup/Restore, Deployment, Troubleshooting
└── SECURITY_GUIDE.md           Threat Model, Berechtigungen, DSGVO, Audit-Logging
```

---

## Lokales Setup

### 1. Repository klonen

```powershell
git clone https://github.com/schienenzeit-art/minguatalada.git
cd minguatalada
```

### 2. Virtuelle Umgebung anlegen und aktivieren

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

> **Windows-Hinweis**: Falls die Ausführungsrichtlinie Probleme macht:
> ```powershell
> Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
> ```

### 3. Abhängigkeiten installieren

```powershell
pip install -r requirements.txt
```

### 4. Anwendung starten (Entwicklungsmodus)

```powershell
python main.py
```

Die Datenbank wird beim ersten Start automatisch angelegt unter `data/system.db`.
Standard-Login: `admin` / `Admin2024!`

> **Wichtig**: Das Passwort nach dem ersten Login sofort ändern.

### Typische Stolperfallen

| Problem | Ursache | Lösung |
|---|---|---|
| `ModuleNotFoundError: PyQt6` | Venv nicht aktiviert | `.\.venv\Scripts\Activate.ps1` ausführen |
| `DeprecationWarning: utcnow()` | Alter Code (vor v1.1) | Bereits behoben, Update einspielen |
| Login schlägt fehl | Falsche DB oder gesperrter User | Siehe [Troubleshooting](#troubleshooting) |
| `data/system.db` fehlt | Noch kein Start erfolgt | `python main.py` ausführen — legt DB an |
| Zwei `.venv`-Verzeichnisse | Sowohl `.venv` als auch `venv` vorhanden | Nur `.venv` verwenden, `venv/` löschen |

---

## Datenbank

### Aktuelle Lösung: SQLite

Im **installierten Modus** (PyInstaller-Build) liegt die Datenbank unter:
```
%LOCALAPPDATA%\Anspruchssystem\system.db
```

Im **Entwicklungsmodus** (direkt aus Quellcode):
```
data/system.db
```

> **Achtung**: Jedes Gerät hat eine **eigene** Datenbank. Daten werden nicht automatisch synchronisiert. Das ist die häufigste Ursache für Unterschiede zwischen Geräten.

### Schema und Migrationen

Das Schema wird bei jedem Start in `database/db.py → initialize_database()` idempotent aufgebaut. Neue Spalten werden via `ALTER TABLE … ADD COLUMN` ergänzt. Es gibt keine separaten Migrationsdateien für den normalen Betrieb — alle Migrationen sind in `db.py` integriert.

Für Updates über das integrierte Update-System können zusätzliche SQL-Migrationsskripte im `.mugala`-Paket mitgeliefert werden (idempotent, Schutz gegen destruktive SQL).

### Seed-Daten (automatisch)

Beim Start werden angelegt (wenn nicht vorhanden):
- Standorte: Bludenz, Feldkirch, Dornbirn
- Rollen: Mitarbeiter, Standortleitung, Supervisor, Admin, Freiwillige
- Kategorien: Pensionist, Alleinerziehend, Menschen mit Beeinträchtigung, Familie, Sozialhilfebezieher, Freiwillige Mitarbeiter
- Admin-Benutzer (`admin` / `Admin2024!`)
- Standard-Einstellungen (Anspruchsgrenzen, Hätefallfaktor)
- Dokumenttypen und Briefvorlagen

### Datenbank direkt abfragen (Diagnose)

```powershell
# SQLite-CLI (falls installiert)
sqlite3 "%LOCALAPPDATA%\Anspruchssystem\system.db"

# Oder via Python:
.\.venv\Scripts\python.exe -c "
import sqlite3
con = sqlite3.connect('data/system.db'); con.row_factory = sqlite3.Row
for r in con.execute('SELECT u.username, u.is_active, u.locked_until, r.name role FROM users u LEFT JOIN roles r ON u.role_id=r.id'):
    print(dict(r))
"
```

### PostgreSQL (Dual-Backend, bereits implementiert)

Seit v1.6.0 unterstützt `database/db.py` zwei Backends parallel — gesteuert über die Umgebungsvariable `DATABASE_URL`:

- **Keine `DATABASE_URL`**: SQLite wie gehabt (`data/system.db`)
- **`DATABASE_URL` gesetzt**: PostgreSQL über `database/connection_adapter.py` (psycopg3), sqlite3-kompatibles Interface — alle Repository-Klassen funktionieren unverändert

`PgConnectionAdapter` übersetzt `?`-Platzhalter zu `%s`, hängt `RETURNING id` nur an INSERTs in Tabellen mit `id`-Spalte an (Whitelist + Savepoint-Fallback für unbekannte id-lose Tabellen wie `schema_migrations`), und garantiert die korrekte SQL-Reihenfolge `ON CONFLICT … RETURNING id`. Details siehe [TECHNICAL_DESIGN_DOCUMENT.md](TECHNICAL_DESIGN_DOCUMENT.md#12-datenbankentscheidung).

**Empfehlung**: Eigener Raspberry-Pi-Server via Tailscale-VPN (siehe `docs/SERVER_SETUP_RASPBERRY_PI.md`) statt Cloud-Anbieter — Daten bleiben selbst gehostet.

---

## Authentifizierung und Benutzer

### Login-Prozess

1. Benutzername + Passwort eingeben
2. Prüfkette (in Reihenfolge):
   - Felder nicht leer
   - Benutzer in DB vorhanden
   - `is_active = 1`
   - Rolle erlaubt Login (nicht in `NON_LOGIN_ROLES`)
   - `locked_until` nicht in der Zukunft
   - bcrypt-Passwortverifikation
3. Nach 5 Fehlversuchen: Account für 15 Minuten gesperrt
4. Alle Ereignisse in `audit_logs` protokolliert (ohne Passwort)

### Rollenmodell

| Rolle | Erstprüfung | Erneute Prüfung | Archivieren | Freigaben | Administration |
|---|---|---|---|---|---|
| **Mitarbeiter** | Ja (1×) | Nur mit Freigabe | Nein | Nein | Nein |
| **Standortleitung** | Ja | Ja | Ja | Ja | Nein |
| **Supervisor** | Ja | Ja | Ja | Ja | Ja |
| **Admin** | Ja | Ja | Ja | Ja | Ja |
| **Freiwillige** | — | — | — | — | — (kein Login) |

### Admin-Konto zurücksetzen

```powershell
.\.venv\Scripts\python.exe scripts/reset_admin.py
```

Setzt `admin` auf Passwort `Admin2024!`, aktiviert den Account und hebt Sperren auf. Wirkt auf die zuerst gefundene Datenbank (installiert oder Entwicklungsmodus).

### Benutzer anzeigen (Diagnose)

```powershell
.\.venv\Scripts\python.exe -c "
import sqlite3
con = sqlite3.connect('data/system.db'); con.row_factory = sqlite3.Row
for r in con.execute('''SELECT u.id, u.username, u.full_name, u.is_active,
    u.failed_attempts, u.locked_until, r.name role
    FROM users u LEFT JOIN roles r ON u.role_id=r.id ORDER BY u.id'''):
    print(dict(r))
"
```

### Häufige Login-Probleme

| Symptom | Ursache | Lösung |
|---|---|---|
| Nur `admin` kann sich einloggen | Andere Benutzer deaktiviert oder gesperrt | Benutzer in DB reaktivieren |
| `locked_until` zeigt Jahr 2099 | Manueller DB-Eingriff | `UPDATE users SET locked_until=NULL WHERE username=?` |
| Login funktioniert auf einem Gerät, nicht auf einem anderen | Andere Datenbankdatei | Datenbank des betroffenen Geräts prüfen (`%LOCALAPPDATA%\Anspruchssystem\system.db`) |
| „Benutzer deaktiviert" | `is_active = 0` | `UPDATE users SET is_active=1 WHERE username=?` |

---

## Testen

### Tests ausführen

```powershell
# Alle Tests
.\.venv\Scripts\python.exe -m pytest tests/ -v

# Nur schnelle Unit-Tests (kein DB-Zugriff, ~0.1s)
.\.venv\Scripts\python.exe -m pytest tests/ -m unit -v

# Nur Integrationstests (mit DB)
.\.venv\Scripts\python.exe -m pytest tests/ -m integration -v

# Langsame Tests ausschließen (Update/Backup)
.\.venv\Scripts\python.exe -m pytest tests/ -m "not slow" -v

# PostgreSQL-Adapter-Integrationstests (nur mit echter Test-DB)
$env:TEST_DATABASE_URL = "postgresql://user:pass@host/testdb"
.\.venv\Scripts\python.exe -m pytest tests/test_pg_adapter_integration.py -v
```

### Testübersicht

| Datei | Typ | Tests | Was wird getestet |
|---|---|---|---|
| `test_auth_service.py` | Integration | 10 | Login-Szenarien, Lockout, deaktiviert, gesperrt, must_change_password |
| `test_claim_status.py` | Unit | 34 | Alle Rollenübergänge, Display-Namen, Genehmigungspflicht |
| `test_re_evaluation_service.py` | Integration | 19 | 4-Augen-Regel: Sperre, Freigabe, Genehmigung, Ablehnung |
| `test_update_service.py` | Slow | 25 | Backup, Paketvalidierung, BOM, destruktive-SQL-Block, Restore |
| `test_logging_audit.py` | Integration | 12 | Audit-Events korrekt, kein Passwort im Log |
| `test_password_service.py` | Unit | 13 | bcrypt Hash/Verify, Sonderzeichen, Zufallspasswort |
| `test_household_service.py` | Integration | 12 | Haushalt-Kategorien hinzufügen/aktualisieren/entfernen |
| `test_pruefung_service.py` | Unit | 8 | Berechnungslogik, Wohnbeihilfe, Grenzwerte |
| `test_settings_service.py` | Integration | 4 | Einstellungen, Admin-Rechte, Audit |
| `test_card_service.py` | Unit (Mock) | 4 | Kartenausstellung, Statusprüfung |
| `test_task_service.py` | Unit (Mock) | 5 | Aufgaben, Rollenrechte |
| `test_app_registry.py` | Unit (Mock) | 3 | App-Sichtbarkeit je Rolle |
| `test_document_service.py` | Integration | 4 | Dokumente hochladen, Fehlerbehandlung |
| `test_person_service.py` | Unit (Mock) | 2 | Personen filtern, abrufen |
| `test_dashboard_service.py` | Unit (Mock) | 2 | KPI-Daten, Filter |
| `test_pg_adapter_integration.py` | Integration (PostgreSQL, optional) | 3 | RETURNING id bei/ohne id-Spalte, ON-CONFLICT-Konflikt ohne Crash |
| **Gesamt** | | **282** (279 ohne PostgreSQL) | |

### Test-Infrastruktur

- `tests/conftest.py`: Isolierte SQLite-Testdatenbank in `tmp_path` (Produktionsdaten unberührt)
- `pytest.ini`: Marker (`unit`, `integration`, `slow`), `testpaths`, `filterwarnings`
- Umgebungsvariable `PYTEST_RUNNING=1` aktiviert Test-Modus in der DB-Initialisierung

### Datenbanktests

Alle Integrationstests arbeiten mit einer **frischen, temporären SQLite-Datenbank** pro Test. Die Produktionsdatenbank (`data/system.db`) wird nie berührt. Bei späterer PostgreSQL-Migration: gleiche Fixtures mit anderem Connection-String nutzbar.

---

## Logging

### Logdatei

Im installierten Modus:
```
%LOCALAPPDATA%\Anspruchssystem\logs\app.log
```

Im Entwicklungsmodus:
```
data/logs/app.log
```

- **Format**: `DATUM UHRZEIT [LEVEL] Modulname: Nachricht`
- **Rotation**: 2 MB pro Datei, 5 Backups (max. ~10 MB gesamt)
- **Level**: INFO und höher

### Protokollierte Ereignisse (Auswahl)

| Ereignis | Level | Beispiel |
|---|---|---|
| Login erfolgreich | INFO | `LOGIN_SUCCESS: Benutzer 'admin' angemeldet (Rolle: Admin)` |
| Login fehlgeschlagen | WARNING | `LOGIN_FAILED: Benutzer 'xyz' nicht gefunden` |
| Account gesperrt | WARNING | `ACCOUNT_LOCKED: 'user' nach 5 Fehlversuchen gesperrt` |
| Prüfung abgeschlossen | INFO | `first_evaluation_completed` in `audit_logs` |
| Prüfung blockiert | WARNING | `evaluation_blocked` in `audit_logs` |
| Backup erstellt | INFO | `UPDATE_APPLIED`/`BACKUP_RESTORED` in `audit_logs` |
| Exception/Fehler | ERROR | Stack-Trace in `app.log` |

### Audit-Log (Datenbank)

Separate Tabelle `audit_logs` in der DB. Sichtbar in der Anwendung unter **Administration → Audit-Log**.

### Datenschutz

- **Passwörter werden nie geloggt** — weder im Klartext noch als Hash.
- Benutzernamen erscheinen in Auth-Events (für Nachvollziehbarkeit erforderlich).
- Inhaltliche Prüfungsdaten (Einnahmen, Ausgaben) stehen nicht im Audit-Log.
- Aufbewahrung Audit-Log: 7 Jahre (konfigurierbar via Archivierungsregeln).

---

## Backup und Restore

### Manuelles Backup

In der Anwendung: **Einstellungen → Backup erstellen**

Oder über Python (Entwicklungsmodus):

```powershell
.\.venv\Scripts\python.exe -c "
from services.update_service import UpdateService
svc = UpdateService()
path = svc.create_backup()
print('Backup erstellt:', path)
"
```

Backups liegen unter:
```
%LOCALAPPDATA%\Anspruchssystem\backups\backup_YYYYMMDD_HHMMSS_v1.0.3.db
```

Es werden maximal 10 Backups aufbewahrt (älteste werden automatisch gelöscht).

### Vor jedem Update

Das System erstellt **automatisch** ein Backup vor dem Einspielen eines Updates. Manuell zusätzlich sichern:

```powershell
copy "%LOCALAPPDATA%\Anspruchssystem\system.db" "backup_manuell_%date:~-4,4%%date:~-7,2%%date:~-10,2%.db"
```

### Restore

In der Anwendung: **Einstellungen → Backup wiederherstellen → Backup auswählen**

Das System erstellt automatisch ein Sicherheits-Backup des aktuellen Stands vor der Wiederherstellung. **Neustart der Anwendung ist danach erforderlich.**

### Admin-Passwort nach Restore

Nach einem Restore aus einem alten Backup kann das Admin-Passwort abweichen:

```powershell
.\.venv\Scripts\python.exe scripts/reset_admin.py
```

---

## Deployment / CI/CD

### CI/CD-Pipeline (GitHub Actions)

Bei jedem Push auf `main`:

```
Push → Tests (Windows, Python 3.12 + 3.13) → [bei Erfolg] PyInstaller-Build → Artifact
```

Testlauf: `python -m pytest tests/ -v --tb=short`  
Build: `pyinstaller anspruchssystem.spec --noconfirm`  
Artifact: `dist/` (14 Tage aufbewahrt)

### Lokaler Release-Build

```powershell
.\build.bat
```

Schritte (automatisch):
1. Abhängigkeiten installieren
2. Logo/Icon erzeugen
3. Alte Build-Artefakte löschen
4. PyInstaller-Build
5. Ergebnis prüfen
6. Release-Verzeichnis auf Desktop anlegen

### Update-Paket erstellen (.mugala)

```powershell
.\.venv\Scripts\python.exe scripts/build_mugala.py
```

> Anforderungen an `manifest.json` und Paketstruktur siehe `services/update_service.py`.

### Reihenfolge vor Produktivdeploy

- [ ] `python -m pytest tests/` — alle Tests grün
- [ ] Manuelles Backup erstellen (auf Zielgerät)
- [ ] Versionsnummer in `services/update_service.py → APP_VERSION` erhöhen
- [ ] `.\build.bat` — Build erfolgreich
- [ ] Installer testen (frische VM oder Testgerät)
- [ ] Auf Zielgerät einspielen (via `.mugala` oder direkter Installer)
- [ ] Admin-Login auf Zielgerät testen
- [ ] `audit_logs` auf auffällige Einträge prüfen

---

## Troubleshooting

### Login funktioniert nur als Admin

**Ursache**: Pro-Gerät-Datenbank — andere Benutzer sind in der lokalen DB deaktiviert oder gesperrt.

**Diagnose**:

```powershell
.\.venv\Scripts\python.exe -c "
import sqlite3, os
db = os.path.join(os.environ.get('LOCALAPPDATA',''), 'Anspruchssystem', 'system.db')
if not __import__('os.path', fromlist=['exists']).exists(db):
    db = 'data/system.db'
con = sqlite3.connect(db); con.row_factory = sqlite3.Row
for r in con.execute('SELECT username, is_active, locked_until FROM users'):
    print(dict(r))
"
```

**Lösung**:
```sql
-- Benutzer reaktivieren und Sperre aufheben:
UPDATE users SET is_active=1, locked_until=NULL, failed_attempts=0 WHERE username='benutzername';
```

### Unterschied Vereins-PC vs. funktionierendes Gerät

**Prüfliste**:

| Prüfpunkt | Befehl / Ort |
|---|---|
| Richtige Datenbank? | `%LOCALAPPDATA%\Anspruchssystem\system.db` vorhanden? |
| Gleiche App-Version? | Titelleiste / `APP_VERSION` in `update_service.py` |
| Python-Version | `python --version` |
| Alle Abhängigkeiten? | `pip install -r requirements.txt` erneut ausführen |
| Benutzer gesperrt? | SQL-Abfrage oben |
| Doppelte Konten? | Mehrere Einträge für gleichen Namen in `users`? |
| `locked_until` = 2099? | Manueller DB-Eingriff — `locked_until=NULL` setzen |

### App startet nicht / Datenbankfehler

```powershell
# Datenbank neu initialisieren (keine Daten verloren, nur Schema ergänzt):
.\.venv\Scripts\python.exe -c "from database.db import initialize_database; initialize_database(); print('OK')"
```

### Admin-Zugang verloren

```powershell
.\.venv\Scripts\python.exe scripts/reset_admin.py
```

### Dependency-Konflikt

```powershell
# Venv komplett neu aufsetzen:
Remove-Item -Recurse -Force .venv
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### Logs prüfen

```powershell
# Letzte 50 Zeilen der Logdatei:
Get-Content "$env:LOCALAPPDATA\Anspruchssystem\logs\app.log" -Tail 50

# Entwicklungsmodus:
Get-Content "data\logs\app.log" -Tail 50
```

### Prüfungsmatrix schließt sich / Datenverlust

Betrifft nur Versionen **vor v1.1**. Seit v1.1: Beim Schließen des Prüfdialogs mit eingegebenen Daten erscheint eine Rückfrage. Update auf v1.1 oder höher einspielen.

---

## Roadmap

### Geplant (priorisiert)

| Thema | Priorität | Status |
|---|---|---|
| Zentrale Datenbank (PostgreSQL, Raspberry Pi) | Hoch | **in Umsetzung** |
| API-Schicht (FastAPI, REST) | Mittel | Vorbereitet (web_api.py), nicht aktiv |
| Audit-Log-Filter im Admin-Bereich | Mittel | Basisansicht vorhanden |
| Integrationstests `persist_evaluation` | Mittel | ✓ Abgeschlossen (v1.3.0) |
| Automatisches Log-Monitoring / Alerting | Niedrig | Offen |

### Bewusst noch nicht umgesetzt

- **REST-API**: FastAPI, uvicorn und PyJWT sind installiert, aber nicht produktiv aktiv. `app/web_api.py` ist Platzhalter.
- **Redis**: Kein Caching- oder Queue-Bedarf erkennbar. Wird erst implementiert wenn konkrete Anforderung entsteht.
- **Mobile / Web-Client**: Kein aktueller Bedarf.

### SQLite → PostgreSQL (in Umsetzung)

Architektur: Raspberry Pi (24/7) als PostgreSQL-Server, erreichbar über Tailscale-VPN.
Alle drei Standorte greifen auf dieselbe zentrale Datenbank zu.

**Implementierter Stand:**
- `database/connection_adapter.py` — psycopg3-Adapter mit sqlite3-kompatiblem Interface, inkl. Savepoint-basiertem Fallback für id-lose Tabellen und robustem `executescript()`-Parser (ignoriert `;` in Kommentaren/Stringliteralen)
- `database/schema_postgres.sql` — vollständiges PostgreSQL-Schema (alle 26 Migrationen eingebettet)
- `database/db.py` — Dual-Backend: SQLite (Standard) oder PostgreSQL (wenn `DATABASE_URL` gesetzt)
- `scripts/migrate_sqlite_to_postgres.py` — Einmalige Datenmigration SQLite → PostgreSQL
- `docs/SERVER_SETUP_RASPBERRY_PI.md` — vollständige Pi-Setup-Anleitung
- `.env.example` — Konfigurationsvorlage
- `tests/test_pg_adapter_integration.py` — Adapter-Integrationstests gegen echtes PostgreSQL (optional, via `TEST_DATABASE_URL`)

**Aktivieren:** `DATABASE_URL=postgresql://user:pw@tailscale-ip:5432/minguatalada` in `.env` setzen.
Tests laufen weiterhin mit SQLite (kein PostgreSQL-Server nötig für CI).

---

## Wartungshinweise

### Vor jedem Release

1. `python -m pytest tests/` — alle 279 Tests müssen grün sein (3 weitere PostgreSQL-Integrationstests nur mit `TEST_DATABASE_URL`)
2. Manuelles Backup auf dem Produktivgerät erstellen
3. Versionsnummer erhöhen (`services/update_service.py → APP_VERSION`)
4. Changelog in `manifest.json` des Update-Pakets pflegen
5. Build ausführen und Installer testen

### Nach einem Update

1. Admin-Login auf dem Zielgerät prüfen
2. Audit-Log auf Fehlereinträge prüfen
3. Logdatei (`app.log`) auf Exceptions scannen

### Regelmäßige Wartung

- Audit-Log-Größe prüfen (Tabelle `audit_logs`, Cleanup nach 7 Jahren)
- Backup-Verzeichnis überwachen (max. 10 Backups, Rest wird automatisch gelöscht)
- Abhängigkeiten regelmäßig aktualisieren und Kompatibilität mit `requirements.txt` prüfen

### Bekannte Stolperfallen

- `data/system.db` darf nicht in Git eingecheckt werden (`.gitignore` schützt davor)
- Backups in `data/backups/` ebenfalls nicht einchecken
- `scripts/list_users.py` enthält einen hardcodierten Pfad — vor Nutzung anpassen

---

## Kontakt

| | |
|---|---|
| **Projekt** | Min Guata Lada — Tischlein Deck Dich Vorarlberg |
| **Repository** | https://github.com/schienenzeit-art/minguatalada |
| **Owner** | Dario Schaer |
| **Kontakt** | dario.schaer89@gmail.com |
| **Nutzung** | Internes Vereinsprojekt — kein öffentliches Release |
| **Lizenz** | Proprietary - All Rights Reserved |

> **Technische Architektur**: Siehe [TECHNICAL_DESIGN_DOCUMENT.md](TECHNICAL_DESIGN_DOCUMENT.md)
> **Betrieb und Troubleshooting**: Siehe [OPERATIONS_GUIDE.md](OPERATIONS_GUIDE.md)
> **Sicherheit und Datenschutz**: Siehe [SECURITY_GUIDE.md](SECURITY_GUIDE.md)

---

*Stand: 2026-06-16 — Version 1.6.0*
