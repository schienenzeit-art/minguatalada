# Operations Guide
## Min Guata Lada — Anspruchsverwaltung

| Feld | Wert |
|---|---|
| **Dokumentname** | Operations Guide — Min Guata Lada ERP |
| **Version** | 1.0 |
| **Status** | Draft |
| **Datum** | 2026-06-16 |
| **Owner** | Dario Schaer / IT-Verantwortlicher Verein |
| **Verwandte Dokumente** | [TECHNICAL_DESIGN_DOCUMENT.md](TECHNICAL_DESIGN_DOCUMENT.md), [SECURITY_GUIDE.md](SECURITY_GUIDE.md) |

---

## 1. Zweck und Geltungsbereich

Dieses Dokument richtet sich an den **IT-Verantwortlichen des Vereins** und beschreibt die operativen Tätigkeiten im laufenden Betrieb: Diagnose von Problemen auf den Vereins-PCs, Backup/Restore, Deployment von Updates und Behebung typischer Fehlerbilder.

Architektur- und Designentscheidungen stehen im [Technical Design Document](TECHNICAL_DESIGN_DOCUMENT.md). Sicherheits- und Datenschutzthemen stehen im [Security Guide](SECURITY_GUIDE.md).

**Nicht Teil dieses Dokuments**: Code-Architektur, Datenmodell, API-Design.

---

## 2. Vereins-PC: Diagnose-Checkliste

Der Vereins-PC zeigt historisch wiederkehrende Probleme (Login nur als Admin, abweichender Datenstand). Ursache ist die Per-Gerät-SQLite-Architektur — siehe [TECHNICAL_DESIGN_DOCUMENT.md, Problem- und Risikokontext](TECHNICAL_DESIGN_DOCUMENT.md#4-problem--und-risikokontext).

### Schritt 1: Richtige Datenbank lokalisieren

```
%LOCALAPPDATA%\Anspruchssystem\system.db   (installierte Version)
<Projektverzeichnis>\data\system.db        (Entwickler-Version)
```

### Schritt 2: Benutzerstatus prüfen (SQL direkt)

```sql
SELECT u.id, u.username, u.full_name, u.is_active,
       u.failed_attempts, u.locked_until, r.name AS rolle
FROM users u
LEFT JOIN roles r ON u.role_id = r.id
ORDER BY u.id;
```

Verdächtig: `is_active = 0`, `locked_until` in der Zukunft (besonders Jahr 2099 — Hinweis auf manuellen DB-Eingriff statt regulärem Lockout).

Per PowerShell ohne SQLite-CLI:

```powershell
.\.venv\Scripts\python.exe -c "
import sqlite3
con = sqlite3.connect('data/system.db'); con.row_factory = sqlite3.Row
for r in con.execute('SELECT u.username, u.is_active, u.locked_until, r.name role FROM users u LEFT JOIN roles r ON u.role_id=r.id'):
    print(dict(r))
"
```

### Schritt 3: Umgebungsvergleich

| Prüfpunkt | Funktionierendes Gerät | Vereins-PC |
|---|---|---|
| Python-Version | `python --version` | |
| Installierter Pfad | `%LOCALAPPDATA%\Anspruchssystem` | |
| DB-Größe | `system.db` in KB | |
| App-Version | Titelleiste / Info | |
| Benutzerkonten | s. SQL oben | |

### Schritt 4: Typische Fehlerbilder

| Symptom | Wahrscheinliche Ursache | Lösung |
|---|---|---|
| Login schlägt für bestimmten User fehl | `is_active=0` oder `locked_until` in Zukunft | DB: User reaktivieren (siehe Abschnitt 3) |
| Login funktioniert nur als Admin | Admin-Auto-Reaktivierung in `seed_basic_data()`, andere User nicht | Andere User manuell reaktivieren |
| Prüfungsmatrix schließt sich unerwartet | Betrifft nur Versionen vor v1.1 | Update einspielen |
| Keine Daten nach Gerätewechsel | Per-Gerät-SQLite, kein gemeinsamer Stand | DB-Export/Import oder `DATABASE_URL` auf zentralen PostgreSQL-Server umstellen |
| Manuelle Sperren mit Datum 2099 | Direkter DB-Eingriff durch IT | `UPDATE users SET locked_until=NULL WHERE ...` |

---

## 3. Login-Fehler beheben

Die formale Fehlerkette ist in [TECHNICAL_DESIGN_DOCUMENT.md, Modul- und Komponentenbeschreibung](TECHNICAL_DESIGN_DOCUMENT.md#10-modul--und-komponentenbeschreibung) (`AuthService`) dokumentiert. Operativ:

| Symptom | Ursache | Lösung |
|---|---|---|
| „Benutzer nicht gefunden" | Tippfehler oder Konto existiert nicht | Benutzername in `users`-Tabelle prüfen |
| „Benutzer ist deaktiviert" | `is_active = 0` | `UPDATE users SET is_active=1 WHERE username='...';` |
| „Account ist gesperrt" | `locked_until` in der Zukunft (regulärer Lockout nach 5 Fehlversuchen ODER manueller Eingriff) | `UPDATE users SET locked_until=NULL, failed_attempts=0 WHERE username='...';` |
| „Passwort ist falsch" trotz korrektem PW | Caps-Lock, falsches Gerät/falsche DB, oder Passwort wurde zwischenzeitlich von Admin geändert | Passwort über Admin zurücksetzen lassen |
| Nur `admin` kann sich einloggen | Pro-Gerät-Datenbank — andere Benutzer lokal deaktiviert/gesperrt | Siehe Diagnose-Checkliste (Abschnitt 2) |

**Admin-Konto zurücksetzen:**

```powershell
.\.venv\Scripts\python.exe scripts/reset_admin.py
```

Setzt `admin` auf Passwort `Admin2024!`, aktiviert den Account und hebt Sperren auf. Wirkt auf die zuerst gefundene Datenbank (installiert oder Entwicklungsmodus). **Nach Reset sofort neues Passwort vergeben.**

---

## 4. Backup und Restore

### Backup-Mechanismus

1. WAL-Checkpoint wird ausgeführt
2. `shutil.copy2(DB_PATH, BACKUPS_DIR/backup_DATUM_vVERSION.db)`
3. Maximal 10 Backups werden aufbewahrt — älteste werden automatisch gelöscht
4. Backup wird **automatisch vor jedem Update** erstellt

Backups liegen unter:
```
%LOCALAPPDATA%\Anspruchssystem\backups\backup_YYYYMMDD_HHMMSS_v1.0.3.db
```

### Manuelles Backup erstellen

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

Zusätzliche manuelle Sicherung außerhalb der App:

```powershell
copy "%LOCALAPPDATA%\Anspruchssystem\system.db" "backup_manuell_%date:~-4,4%%date:~-7,2%%date:~-10,2%.db"
```

### Restore durchführen

1. In der Anwendung: **Einstellungen → Backup wiederherstellen → Backup auswählen**
2. Das System erstellt automatisch ein Sicherheits-Backup des aktuellen Stands vor der Wiederherstellung
3. Backup-Datei überschreibt `DB_PATH`
4. **Neustart der Anwendung erforderlich**

### Nach einem Restore: Admin-Passwort prüfen

Nach Restore aus einem alten Backup kann das Admin-Passwort vom aktuellen Stand abweichen:

```powershell
.\.venv\Scripts\python.exe scripts/reset_admin.py
```

### Restore-Zielwerte (RPO/RTO)

Siehe [TECHNICAL_DESIGN_DOCUMENT.md, Nicht-funktionale Anforderungen](TECHNICAL_DESIGN_DOCUMENT.md#5-nicht-funktionale-anforderungen) für die Ziel-Wiederherstellungszeit. Ein realer Restore-Test (Zeitmessung von „Backup auswählen" bis „App wieder produktiv nutzbar") ist bisher **nicht durchgeführt** — empfohlen vor dem nächsten größeren Release.

---

## 5. Deployment-Ablauf

### Aktueller Deploy-Modus

1. Entwickler baut Installer mit PyInstaller + Inno Setup
2. Installer wird als `.mugala`-Paket verpackt
3. Admin spielt Update über die Anwendungsoberfläche ein (oder direkt per Installer)
4. Anwendung erstellt automatisch Backup → wendet Migrationen an → startet Installer → beendet sich

### Update-Paket erstellen (.mugala)

```powershell
.\.venv\Scripts\python.exe scripts/build_mugala.py
```

> Anforderungen an `manifest.json` und Paketstruktur siehe `services/update_service.py`.

### Lokaler Release-Build

```powershell
.\build.bat
```

Schritte (automatisch): Abhängigkeiten installieren → Logo/Icon erzeugen → alte Build-Artefakte löschen → PyInstaller-Build → Ergebnis prüfen → Release-Verzeichnis auf Desktop anlegen.

### CI/CD-Ablauf

```
git push → GitHub Actions
  ├── Tests (python -m pytest tests/)
  └── [main] PyInstaller Build → Artifact (14 Tage aufbewahrt)
```

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

## 6. Rollback

1. Backup aus `BACKUPS_DIR` wählen → Restore → Neustart (siehe Abschnitt 4)
2. Alternativ: altes Installationspaket erneut ausführen (Inno Setup überschreibt die aktuelle Installation)

---

## 7. Betriebscheckliste vor Produktiveinsatz

- [ ] Admin-Passwort geändert (`Admin2024!` ist Default → sofort ändern)
- [ ] `APP_SECRET_KEY` Umgebungsvariable gesetzt
- [ ] Backup-Verzeichnis gesichert (Dateisystem-Berechtigungen)
- [ ] Log-Verzeichnis zugänglich für Admin-Review
- [ ] Keine Testbenutzer (`test`, `mitarbeiter1`) in Produktionsdatenbank
- [ ] `UPDATE_MANIFEST_URL` in Einstellungen konfiguriert (wenn Update-Server genutzt)

---

## 8. Fehlende oder beschädigte Datenbank

- `initialize_database()` wird bei jedem Start aufgerufen — legt DB und Verzeichnis an, wenn nicht vorhanden
- `is_database_ready()` prüft, ob die DB erreichbar ist
- Bei komplett beschädigter DB: Anwendung startet nicht → **Restore aus Backup nötig** (siehe Abschnitt 4)

Datenbank ohne Datenverlust neu initialisieren (ergänzt nur fehlendes Schema):

```powershell
.\.venv\Scripts\python.exe -c "from database.db import initialize_database; initialize_database(); print('OK')"
```

---

## 9. VPN-/PostgreSQL-Ausfall (Dual-Backend-Betrieb)

Gilt nur für Standorte mit aktivem `DATABASE_URL` (zentraler Raspberry-Pi-Server, siehe [TECHNICAL_DESIGN_DOCUMENT.md, Deploymentdiagramm](TECHNICAL_DESIGN_DOCUMENT.md#9-deploymentdiagramm)).

| Symptom | Prüfung | Sofortmaßnahme |
|---|---|---|
| App kann keine Verbindung zur DB herstellen | `tailscale status` auf dem betroffenen Gerät — ist der Pi sichtbar? | Lokales Netz/Internet prüfen, Tailscale-Dienst neu starten |
| Pi im Tailscale-Netz nicht erreichbar | Auf dem Pi: `systemctl status postgresql`, `systemctl status tailscaled` | Pi neu starten (Strom/SSH), Dienste prüfen |
| Dauerhafter Ausfall absehbar | — | Betroffenes Gerät vorübergehend ohne `DATABASE_URL` starten → läuft auf lokaler SQLite weiter (siehe ADR-007 im TDD) |
| Nach Wiederherstellung | Datenstand zwischen lokalem SQLite-Fallback und PostgreSQL kann auseinanderlaufen | Manueller Abgleich nötig — aktuell **kein automatischer Sync-Mechanismus**, siehe Sicherheits-/Risikohinweis im Security Guide |

---

## 10. Logs prüfen

Im installierten Modus:
```
%LOCALAPPDATA%\Anspruchssystem\logs\app.log
```

Im Entwicklungsmodus:
```
data/logs/app.log
```

```powershell
# Letzte 50 Zeilen der Logdatei:
Get-Content "$env:LOCALAPPDATA\Anspruchssystem\logs\app.log" -Tail 50

# Entwicklungsmodus:
Get-Content "data\logs\app.log" -Tail 50
```

Format: `DATUM UHRZEIT [LEVEL] Modulname: Nachricht`. Rotation: 2 MB pro Datei, 5 Backups (max. ~10 MB gesamt).

---

## 11. Sonstige Diagnose- und Troubleshooting-Fälle

### Dependency-Konflikt

```powershell
# Venv komplett neu aufsetzen:
Remove-Item -Recurse -Force .venv
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

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

### Unterschied Vereins-PC vs. funktionierendes Gerät (Kurzcheck)

| Prüfpunkt | Befehl / Ort |
|---|---|
| Richtige Datenbank? | `%LOCALAPPDATA%\Anspruchssystem\system.db` vorhanden? |
| Gleiche App-Version? | Titelleiste / `APP_VERSION` in `update_service.py` |
| Python-Version | `python --version` |
| Alle Abhängigkeiten? | `pip install -r requirements.txt` erneut ausführen |
| Benutzer gesperrt? | SQL-Abfrage in Abschnitt 2 |
| Doppelte Konten? | Mehrere Einträge für gleichen Namen in `users`? |
| `locked_until` = 2099? | Manueller DB-Eingriff — `locked_until=NULL` setzen |

---

## 12. Regelmäßige Wartung

- Audit-Log-Größe prüfen (Tabelle `audit_logs`, Cleanup nach 7 Jahren)
- Backup-Verzeichnis überwachen (max. 10 Backups, Rest wird automatisch gelöscht)
- Abhängigkeiten regelmäßig aktualisieren und Kompatibilität mit `requirements.txt` prüfen
- Bei Dual-Backend-Betrieb: Pi-Erreichbarkeit über Tailscale periodisch prüfen

---

## 13. Verweise

- Architektur und Komponenten: [TECHNICAL_DESIGN_DOCUMENT.md](TECHNICAL_DESIGN_DOCUMENT.md)
- Sicherheit, Berechtigungen, DSGVO: [SECURITY_GUIDE.md](SECURITY_GUIDE.md)
- Raspberry-Pi-Server-Setup: `docs/SERVER_SETUP_RASPBERRY_PI.md`
- Testdokumentation: `tests/` (Ausführung: `python -m pytest tests/`)
- CI/CD-Workflow: `.github/workflows/ci.yml`
- Repository: https://github.com/schienenzeit-art/minguatalada

---

*Stand: 2026-06-16 — Version 1.0*
