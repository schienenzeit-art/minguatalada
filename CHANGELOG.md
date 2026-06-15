# Changelog

Alle wesentlichen Änderungen werden in dieser Datei dokumentiert.
Format basiert auf [Keep a Changelog](https://keepachangelog.com/de/1.0.0/).
Versionierung nach [Semantic Versioning](https://semver.org/lang/de/).

---

## [1.6.0] – 2026-06-15

### Added
- **Online-Update-Center**: Automatischer Update-Check beim App-Start (Einstellung
  `AUTO_CHECK_UPDATES`). Bei verfügbarem Update erscheint ein blauer Banner zwischen
  Topbar und Inhalt — Klick führt direkt zum Update-Center.
- **Direkter .exe-Installer-Download**: Update-Center lädt den Windows-Installer
  automatisch herunter und startet ihn (kein manueller Datei-Import mehr nötig).
  Fortschrittsanzeige mit MB-Anzeige während des Downloads.
- **PostgreSQL-Backend**: Dual-Backend via `DATABASE_URL`-Umgebungsvariable.
  Raspberry Pi als zentraler Datenbankserver via Tailscale VPN (100.64.0.0/10).
  Bestehende SQLite-Installationen laufen unverändert weiter.

### Changed
- **Update-Center UI**: Tab „Online-Update" ist jetzt primärer Tab mit
  Versions-Status-Karte und direktem „Jetzt installieren"-Button.
  Tab „Manuell einspielen" bleibt als Fallback für Offline-Szenarien.
- **Update-Manifest**: Server-Manifest enthält neu `installer_url` (direkter
  Link zur Setup-EXE). `mugala_url` bleibt für Abwärtskompatibilität erhalten.

### Fixed
- Update-Check lieferte HTTP 400 bei easyname-Hosting — User-Agent-Header
  `MinGuataLada/{version}` wird jetzt bei allen HTTP-Anfragen gesetzt.

---

## [1.5.0] – 2026-06-07

Architektur-Refactoring Sprint 2–3: Code-Qualitätsgates und Schuldenabbau.
Keine Änderungen an der Benutzeroberfläche oder den Geschäftsregeln.

### Changed
- **Migration-Framework**: `database/migrations.py` mit 26 nummerierten, idempotenten
  Migrationen. `database/db.py` von 1106 auf 385 Zeilen reduziert. Jede neue Spalte
  oder Tabelle wird ab sofort in einer nummerierten Migration erfasst statt als
  try/except ALTER TABLE-Block.
- **`schema_migrations`-Tabelle**: Trackt angewandte Migrationen mit Versionsnummer
  und Zeitstempel. Migrationen laufen automatisch beim nächsten App-Start.
- **DI-Propagation**: `TasksPage` und `DashboardPage` leiten `claim_service` und
  `case_service` jetzt vollständig an untergeordnete Dialoge weiter.
- **`service_factory.py` entfernt**: Fallback-Anti-Pattern aus allen UI-Dialogen
  (`ClaimDetailPage`, `ClaimEvaluationDialog`, `CaseCreateDialog`) entfernt.
  Services werden direkt instanziiert wenn kein Container verfügbar ist.
- **`ManualService`**: In `ServiceContainer` aufgenommen und per DI übergeben.
  Kein direktes `ManualService()` mehr in `main_window.py`.

### Added
- **Inno Setup Installer**: Release enthält jetzt `MinGuataLada_Setup_<version>.exe` –
  ein vollständiger Windows-Installer mit Deinstallations-Support, Desktop-Verknüpfung
  und automatischem Upgrade bestehender Installationen.

### Fixed
- Doppelte `AuditService`- und `NotificationService`-Instanzen im Container
  (Sprint 2) behoben.
- Legacy-Seiten (`claims_page.py`, `dashboard.py`, `location_page.py`) und
  `refactor.md` aus dem Repository entfernt.
- F401-Lint-Fehler in allen Services und Repositories bereinigt.

---

## [1.3.0] – 2026-06-04

Architektur-Refactoring (Sprint 1–4): Stabilitäts- und Wartbarkeitsverbesserungen ohne
Änderungen an der Benutzeroberfläche oder den Geschäftsregeln.

### Changed
- **Dependency Injection**: `ClaimService`, `ReEvaluationService`, `TaskService`,
  `DashboardService`, `PDFService` und `DocumentPackageService` erhalten alle
  Abhängigkeiten explizit über den `ServiceContainer`. Keine Lazy-DI-Fallbacks mehr
  in kritischen Services.
- **`service_factory.py`** (neu): Zentraler Fallback für UI-Komponenten die ohne
  vollständigen DI-Container instanziiert werden.
- **`EvaluationResult.logic_version`**: Alle gespeicherten Prüfergebnisse tragen
  jetzt eine Versionsnummer (`"1.0"`) damit historische Auswertungen nach
  Regeländerungen korrekt interpretiert werden können.
- **`database/db.py`**: 510 Zeilen extrahiert – Seed-Funktionen in `database/seed.py`
  ausgelagert. `db.py` orchestriert nur noch Schema, Migrationen und Healthcheck.
- **`DocumentService`**: Audit-Logging über `AuditService` statt direktem SQL.
  `update_document_title` ist jetzt auditiert. Vollständiger Compliance-Trail für
  Upload, Archivierung, Löschung und Titeländerung.
- **`ReEvaluationService`**: `notify_re_evaluation_requested()` wird jetzt im
  Service-Layer ausgelöst (statt in der UI). `notification_service` wird injiziert.
- **`ClaimEvaluationDialog`**: Doppeltes `AuditService().log()` und
  `NotificationService()` Inline-Aufruf aus der UI entfernt.
- **`app/web_api.py`**: Als inaktiver Architektur-Placeholder markiert.
  `datetime.utcnow()` auf `timezone.utc` migriert.
- **Tests**: `conftest.py` mit `make_claim_service()` / `make_re_eval_service()`
  Factories – vollständig verdrahtete Services in Integrationstests.
  `autouse`-Fixture verhindert Session-Ghoststate zwischen Tests.

### Added
- **`domain/types.py`**: `ClaimSnapshot` Dataclass als typsicherer Ersatz für
  rohe `dict`-Rückgaben aus `ClaimService`. `get_claim_snapshot()` als neue
  Methode auf `ClaimService` (additiv, bestehende `get_claim_by_id()` unverändert).
- **`UserRepository.username_exists()`**: Explizite Existenzprüfung vor Create-
  Operationen (verhindert Constraint-Exceptions als Kontrollfluss).
- **graphify Knowledge Graph**: Codebase-Navigation via `graphify-out/graph.json`
  (3155 Nodes, 8906 Edges). `CLAUDE.md` und PreToolUse-Hook integriert.

### Fixed
- **Startup-Crash**: `notification_service_early` wurde im Container nach
  `re_evaluation_service` initialisiert → `UnboundLocalError` beim Start. Behoben.
- **UI-Crash** bei `ClaimEvaluationDialog(claim_service=None)`: Lazy-Fallback
  `or ClaimService()` schlug fehl da `ClaimService` jetzt Required-Deps hat.
  Behoben via `service_factory.default_claim_service()`.

---

## [1.2.0] – 2026-06-04

### Added
- **Mehrpersonen-Erfassung**: Responsive Erfassungsmaske für mehrere Personen
  in einem Durchgang.
- **Ed25519-Signaturen**: `.mugala`-Update-Pakete werden mit Ed25519 signiert
  und beim Einspielen verifiziert.
- **WAL-Modus**: SQLite WAL-Journaling und Startup-Healthcheck (FK, Integrität,
  Journal-Modus) aktiv.
- **Backup-Integritätsprüfung**: Backups werden vor Restore auf Vollständigkeit
  geprüft. Destruktive SQL-Befehle in Migrationsskripten blockiert.
- **Erweiterte Test-Suite**: Hardening-Tests für Edge Cases, Backup-Restore,
  Randfälle und Autosave-Verhalten.

### Changed
- **Autosave im Prüfdialog**: Zwischenspeicherung bei längeren Prüfvorgängen.

---

## [1.1.0] – 2026-06-03

### Added
- **Datenverlust-Schutz im Prüfdialog**: Rückfrage beim Schließen des Prüfungsdialogs,
  wenn bereits Daten eingegeben oder eine Prüfung gestartet wurde (`closeEvent`, `reject`).
  Nach erfolgreichem Speichern schließt der Dialog ohne Nachfrage.
- **Exception-Schutz in der Prüfungsmatrix**: Auswertungsfehler in `evaluate_claim()`
  schließen den Dialog nicht mehr; Eingaben bleiben erhalten.
- **Zentrales Logging**: `RotatingFileHandler` bei App-Start eingerichtet
  (`DATA_DIR/logs/app.log`, 2 MB × 5 Backups).
- **Auth-Audit-Logging**: Login-Erfolg, -Fehlschlag, Lockout und Kontosperrung werden
  in `audit_logs` protokolliert (ohne Passwort oder Hash).
- **Haushaltskategorien**: Erwachsene Haushaltsmitglieder können jetzt eine Kategorie
  erhalten (Pensionist, Sozialhilfebezieher etc.). Migration `household_members.category_id`,
  Repository, Service und UI-Dialog aktualisiert.
- **Test-Infrastruktur**: `conftest.py` mit isolierter `tmp_path`-SQLite-DB-Fixture,
  Session-Fixtures für alle Rollen (Admin, Mitarbeiter, Supervisor).
- **pytest**: `pytest==8.3.5` in `requirements.txt` aufgenommen.
- **pytest.ini**: Marker (`unit`, `integration`, `slow`), `filterwarnings`, `testpaths`.
- **Neue Testmodule**:
  - `test_claim_status.py` – 34 Unit-Tests für rollenbasierte Statusübergänge
  - `test_re_evaluation_service.py` – 19 Integrationstests für 4-Augen-Regel
  - `test_update_service.py` – 25 Tests für Backup, Paketvalidierung, destruktive-SQL-Block
  - `test_logging_audit.py` – 12 Tests: Audit-Events, kein Passwort im Log
  - `test_password_service.py` – 13 Unit-Tests: bcrypt, Sonderzeichen
  - `test_household_service.py` – 12 Tests: Kategorie-Feature
- **GitHub Actions CI/CD**: Workflow `.github/workflows/ci.yml` mit Test-Job
  (Windows, Python 3.12+3.13) und Build-Job (PyInstaller-Artifact auf `main`).
- **Technical Design Document**: `TECHNICAL_DESIGN_DOCUMENT.md` mit vollständiger
  Architektur-, Risiko-, DB- und API-Dokumentation.
- **README.md**: Vollständig überarbeitet mit Setup, Rollen, Tests, Logging,
  Troubleshooting, Backup und Roadmap.
- **CHANGELOG.md**: Diese Datei.

### Changed
- **Login-Fehlermeldungen**: Klarere Rückmeldung bei deaktiviertem/gesperrtem Account
  mit explizitem Hinweis auf Administrator-Kontakt.
- **Seed-Code**: `mitarbeiter1` wird in Produktion nicht mehr automatisch angelegt
  (nur noch für pytest-Lauf). Verhindert unbeabsichtigte Testkonten auf Produktivgeräten.
- **`seed_claims()`**: Verwendet jetzt `admin` statt `mitarbeiter1` als Beispiel-User,
  damit Beispiel-Antrag auch ohne Testbenutzer angelegt werden kann.
- **`datetime.utcnow()`** in allen Services und DB-Dateien auf `datetime.now(UTC)`
  umgestellt (deprecated in Python 3.14).
- **`requirements.txt`**: Abhängigkeiten vollständig gepinnt.
- **`.gitignore`**: Erweitert um explizite Pfade für Laufzeitdaten und Build-Artefakte.
  Verhindert versehentliches Einchecken von Datenbankdateien, PDFs und Binaries.

### Fixed
- **Login „nur als Admin"** (Vereins-PC): Ursache analysiert — per-Gerät-SQLite,
  andere Benutzer mit `locked_until=2099` (manueller Eingriff). Bereinigt.
  `seed_basic_data()` reaktiviert nur noch den `admin`-Account — nie andere Benutzer.
- **Tatjana Stüttler**: Doppeltes Konto (`TaStue` Admin deaktiviert,
  `tatjana.stuettler` Supervisor aktiv) bereinigt.
- **Test-Isolation**: `test_auth_service.py` nutzt isolierte temporäre DB statt
  Produktions-`system.db`. Produktionsdaten unberührt.
- **Test-Korrektheit**: `test_app_registry.py` mockt jetzt korrekt `Session.get_user()`
  statt des nicht genutzten `Session.is_admin`.
- `test_pruefung_service.py`: Tests an aktuelle Business-Logik angepasst
  (Wohnbeihilfe-Pflichtprüfung, kein Disability-Reject mehr).

### Security
- **Personenbezogene Dateien aus Git-History entfernt**: Prüfprotokolle, Dossiers,
  Briefe, Excel-Reports und Antragsdokumente wurden aus dem Git-Index entfernt.
  Betrifft 44 Dateien in `data/documents/`, `data/pdfs/`, `data/excel/`.
  → Für vollständige History-Bereinigung: `git filter-repo` oder BFG Repo Cleaner
  (gesonderte Aktion erforderlich, siehe Troubleshooting im README).
- **Build-Artefakte entfernt**: `build/`, `dist/`, Installer-Binaries (`.exe`)
  aus Git-Index entfernt — 233 Dateien. Keine Binaries im Quell-Repository.
- **Passwörter / Hashes nie im Log**: Durch `test_logging_audit.py` automatisch
  als Regression abgesichert.
- Admin-Default-Passwort dokumentiert: `Admin2024!` — sofort nach erstem Login ändern.

### Known Issues
- Die alte Git-History enthält weiterhin die personenbezogenen Dateien.
  Vollständige Bereinigung via `git filter-repo` steht aus (erfordert Force-Push
  und muss mit allen Repository-Beteiligten koordiniert werden).
- SQLite ist pro Gerät — kein gemeinsamer Datenstand zwischen Geräten.
  PostgreSQL/Supabase-Migration geplant (mittelfristig).
- `ClaimService.persist_evaluation()` noch ohne vollständige Integrationstests.

---

## [1.0.3] – 2026-05-31

Produktiv eingesetzter Versionsstand vor den Stabilitätsverbesserungen.
Keine strukturierten Release Notes vorhanden (Backup-Commits).

---

## [1.0.0] – 2026-05-15

Initiales Grundgerüst: PyQt6-Desktop-App, SQLite-Datenhaltung, Login,
Anspruchsprüfung, Kartenverwaltung.

---

*Ältere Versionen: Keine strukturierten Changelogs vorhanden.*
