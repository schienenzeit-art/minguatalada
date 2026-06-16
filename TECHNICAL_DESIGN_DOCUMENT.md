# Technical Design Document
## Min Guata Lada — Anspruchsverwaltung

| Feld | Wert |
|---|---|
| **Dokumentname** | Technical Design Document — Min Guata Lada ERP |
| **Projektname** | Min Guata Lada — Tischlein Deck Dich Vorarlberg |
| **Version** | 1.2 |
| **Status** | Draft |
| **Datum** | 2026-06-16 |
| **Owner** | Dario Schaer / Projektleitung |
| **Repository** | github.com/schienenzeit-art/minguatalada |

---

## 1. Zweck des Dokuments

Dieses Dokument beschreibt den technischen Aufbau, die Architektur, die kritischen Prozesse und die bekannten Risiken der Software **Min Guata Lada — Anspruchsverwaltung**. Es dient als Referenz für:

- Entwicklung und Fehlerbehebung
- Betrieb und Wartung durch den IT-Verantwortlichen
- Onboarding neuer technischer Mitarbeitender
- Entscheidungsgrundlage für Datenbankwechsel, Cloud-Anbindung und API-Ausbau
- Nachvollziehbarkeit technischer Entscheidungen

Das Dokument ist **kein Marketingtext** und **kein akademisches Architekturpapier**. Es dokumentiert den tatsächlichen Ist-Zustand und zeigt offen auf, was stabil ist, was Risiken trägt und was noch offen ist.

---

## 2. Scope und Nicht-Ziele

### Scope
- Systemarchitektur (Schichten, Module, Datenfluss)
- Authentifizierung und Rollenmodell
- Prüfungsworkflow (Anspruchsprüfung, 4-Augen-Regel)
- Datenhaltung (SQLite, Migrationskonzept)
- Logging und Audit-Nachvollziehbarkeit
- Backup und Restore
- Deployment und CI/CD
- Fehlerbilder und Troubleshooting (insbesondere Vereins-PC)
- Datenbankentscheidung (SQLite vs. PostgreSQL)
- Vorbereitung auf Cloud-Anbindung und API-Schicht
- Teststrategie (Überblick; Details in separater Testdokumentation)

### Nicht-Ziele
- Benutzerhandbuch oder Endbenutzerdokumentation
- Vollständige API-Spezifikation (noch nicht implementiert)
- Infrastruktur-Betriebshandbuch (Cloud-Deployment noch nicht realisiert)
- Vollständige Datenschutzdokumentation (DSGVO-Analyse separat zu erstellen)

### Separat zu dokumentieren
- Datenschutz-Folgenabschätzung (DSGVO)
- Betriebshandbuch für IT-Verantwortlichen (Vereins-PC)
- API-Spezifikation bei zukünftiger Implementierung

---

## 3. Systemüberblick

### Was ist Min Guata Lada?
Min Guata Lada ist eine Desktop-Verwaltungssoftware für den Verein **Tischlein Deck Dich Vorarlberg**. Sie unterstützt die Mitarbeitenden bei der Prüfung, Verwaltung und Nachverfolgung von Anspruchsberechtigungen (z. B. für Lebensmittelunterstützung), der Erfassung von Haushalten und Personen sowie der Kartenausstellung für Anspruchsberechtigte.

### Fachlicher Zweck
- Antragserfassung und -verwaltung
- Anspruchsprüfung (Einnahmen-/Ausgaben-Berechnung)
- 4-Augen-Regelung für kritische Prüfentscheidungen
- Kartenausstellung und -verwaltung
- Dokumentenmanagement
- Standortübergreifende Verwaltung (Bludenz, Feldkirch, Dornbirn)
- Aufgabenverwaltung und Terminplanung
- Reporting und Auswertungen

### Betriebsmodus (Ist-Stand)
- **Lokal installiert**, auf mehreren Windows-Geräten im Vereinsumfeld
- **Keine zentrale Datenbank** — jedes Gerät hat seine eigene SQLite-Datei
- Produktiv im Einsatz an mindestens drei Standorten
- Bekannte Betriebsprobleme auf dem **Vereins-PC** (Details in Kapitel 18)

---

## 4. Problem- und Risikokontext

### Kritische Probleme (bekannt, teilweise behoben)

| Problem | Ursache | Status |
|---|---|---|
| Prüfungsmatrix schließt sich unerwartet | Fehlende Exception-Behandlung + kein Schließschutz | **Behoben** (v1.1) |
| Login funktioniert nur als Admin (Vereins-PC) | Per-Gerät-DB, andere User manuell gesperrt (locked_until=2099) | **Behoben** (Daten, v1.1) |
| Verlorene Eingaben bei abgebrochenem Prüfdialog | Kein Datenverlust-Schutz im Dialog | **Behoben** (v1.1) |
| `mitarbeiter1` wird bei jedem Start neu angelegt | Seed-Code ohne Prüfung auf Produktivmodus | **Behoben** (v1.1) |
| `datetime.utcnow()` deprecated in Python 3.14 | Veraltete API-Nutzung | **Behoben** (v1.1) |

### Strukturelle Risiken

1. **Per-Gerät-Datenbank**: Jeder Rechner hat seinen eigenen Datenstand. Änderungen an Benutzern, Sperren oder Konfiguration greifen nicht auf anderen Geräten. → **Hauptrisiko für Produktivbetrieb**.
2. **Keine zentrale Administration**: IT-Eingriffe (manuelles Sperren mit Ferndatum 2099) auf einem Gerät beeinflussen andere nicht — aber die lokale Datenbasis kann inkonsistent sein.
3. **Globaler Session-State**: `core.session.Session` ist ein Klassen-Variable ohne Thread-Safety. Unkritisch im Einzelplatz-Desktop-Betrieb, muss für Web/API-Betrieb ersetzt werden.
4. **Kein automatisches Monitoring**: Fehler und Exceptions landen bisher nur in `print()`-Aufrufen. Seit v1.1 gibt es `RotatingFileHandler` unter `DATA_DIR/logs/app.log`.

---

## 5. Fachliche Kernprozesse

### 5.1 Benutzeranmeldung
1. Loginmaske zeigt Benutzername + Passwort-Felder
2. `AuthService.login()` prüft in dieser Reihenfolge:
   - Felder nicht leer
   - Benutzer in DB vorhanden
   - `is_active == 1`
   - Rolle nicht in `NON_LOGIN_ROLES` (z. B. „Freiwillige")
   - `locked_until` nicht in der Zukunft
   - bcrypt-Passwortabgleich
3. Bei Erfolg: Session setzen, ggf. Passwort-Change-Dialog
4. Bei Fehlschlag: Fehlversuch zählen; nach 5 Fehlversuchen: `locked_until = jetzt + 15 Min`
5. Alle Login-Events (Erfolg, Fehlschlag, Sperre) in `audit_logs` protokollieren

### 5.2 Rollen und Berechtigungen

| Rolle | Prüfen | Archivieren | Administration | Freigaben genehmigen |
|---|---|---|---|---|
| Mitarbeiter | Erstprüfung | Nein | Nein | Nein |
| Standortleitung | Ja (immer) | Ja | Nein | Ja |
| Supervisor | Ja (immer) | Ja | Ja | Ja |
| Admin | Ja (immer) | Ja | Ja | Ja |
| Freiwillige | — (kein Login) | — | — | — |

### 5.3 Haushaltsverwaltung
- Einem Antrag (`claim`) sind beliebig viele Haushaltsmitglieder zugeordnet
- Mitglieder haben: Vorname, Nachname, Geburtsdatum, Beziehungstyp, optional `category_id`
- Erwachsene (Beziehungen ≠ Kind/Stiefkind/Pflegekind) können eine Kategorie erhalten
- Kategorien: Pensionist, Alleinerziehend, Menschen mit Beeinträchtigung, Familie, Sozialhilfebezieher, Freiwillige Mitarbeiter
- 20-Jahre-Alters-Alert: Kinder die das 20. Lebensjahr erreichen, lösen eine automatische Warnung aus

### 5.4 Anspruchsprüfung (Prüfungsworkflow)
1. Mitarbeiter öffnet `ClaimEvaluationDialog` für einen Antrag
2. Eingabe von Einnahmen (13 Kategorien) und Ausgaben (17 Kategorien) inkl. Nachweis-Checkboxen
3. Wohnbeihilfe-Status obligatorisch angeben (Checkbox)
4. Klick „Prüfung starten": `PruefungService.evaluate_claim()` berechnet:
   - Summen, freies Einkommen
   - Anspruchsgrenze (`BASE_LIMIT` + Zuschläge aus DB-Settings)
   - Härtefallgrenze (`Anspruchsgrenze × HARDSHIP_FACTOR`)
   - Status: ANSPRUCHSBERECHTIGT / HAERTEFALL / ABGELEHNT / VORLAEFIG_ABGELEHNT
5. Klick „Prüfung abschließen": `ClaimService.persist_evaluation()` speichert alles, erzeugt PDF-Protokoll
6. **4-Augen-Regel**: Zweite Prüfung durch Mitarbeiter nur mit Supervisor-Freigabe
7. Nach Abschluss: `PostEvaluationPanel` für Brief, Wiedervorlage, etc.

**Datenverlust-Schutz (seit v1.1)**:
- Sobald Daten eingegeben oder Prüfung gestartet: `reject()` und `closeEvent()` fragen nach Bestätigung
- Exception in `evaluate_claim()` schließt den Dialog nicht mehr
- Nach erfolgreichem Speichern: Dialog schließt ohne Nachfrage

### 5.5 Backup und Restore
1. Backup: WAL-Checkpoint → `shutil.copy2(DB_PATH, BACKUPS_DIR/backup_DATUM_vVERSION.db)`
2. Max. 10 Backups, älteste werden automatisch gelöscht
3. Restore: Sicherheits-Backup des aktuellen Stands → Backup-Datei überschreibt `DB_PATH` → Neustart erforderlich
4. Backup wird automatisch vor jedem Update erstellt

---

## 6. Architekturüberblick

```
┌─────────────────────────────────────────────────────────────┐
│                         UI (PyQt6)                          │
│  LoginWindow │ MainWindow │ Pages │ Dialoge │ Komponenten   │
└───────────────────────────┬─────────────────────────────────┘
                            │ ruft auf
┌───────────────────────────▼─────────────────────────────────┐
│                   Services (Fachlogik)                      │
│  AuthService │ ClaimService │ PruefungService │ UserService  │
│  UpdateService │ HouseholdService │ AuditService │ ...       │
└───────────────────────────┬─────────────────────────────────┘
                            │ ruft auf
┌───────────────────────────▼─────────────────────────────────┐
│           Repositories (Datenzugriff)                       │
│  ClaimRepository │ UserRepository │ AuditRepository │ ...   │
└───────────────────────────┬─────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────┐
│              database/db.py (SQLite)                        │
│  get_connection() │ initialize_database() │ Migrationen     │
└─────────────────────────────────────────────────────────────┘
```

### Schichten im Überblick

| Schicht | Verzeichnis | Verantwortung |
|---|---|---|
| UI | `ui/` | Darstellung, Interaktion, Event-Handling |
| App-Bootstrap | `app/` | Startup, DI-Container, Konfiguration, Session |
| Core | `core/` | Enums, Konstanten, Session, domänenübergreifende Typen |
| Domain | `domain/` | Domänenobjekte, reine Fachlogik (PruefungService) |
| Services | `services/` | Fachlogik mit Datenbankzugriff, Orchestrierung |
| Database | `database/` | Repositories, Schema, Migrationen, Seed |

### Externe Abhängigkeiten

| Paket | Version | Zweck |
|---|---|---|
| PyQt6 | 6.11.0 | Desktop-GUI |
| bcrypt | 5.0.0 | Passwort-Hashing |
| reportlab | 4.5.1 | PDF-Erzeugung |
| openpyxl | 3.1.5 | Excel-Export |
| fastapi | 0.136.3 | (vorbereitet, noch nicht produktiv genutzt) |
| uvicorn | 0.48.0 | (vorbereitet, noch nicht produktiv genutzt) |
| PyJWT | 2.13.0 | (vorbereitet für API-Auth) |

---

## 7. Modul- und Komponentenbeschreibung

### 7.1 `app/` — Application Bootstrap

**Zweck**: Startpunkt und Dependency Injection.

| Datei | Verantwortung |
|---|---|
| `bootstrap.py` | `run_app()`: Logging, DB-Init, Qt-App, Login, MainWindow |
| `config.py` | Pfade (`DB_PATH`, `DATA_DIR`, `RESOURCE_DIR`), Secret-Key, JWT-Config |
| `container.py` | `ServiceContainer`: alle Services als Dataclass gebündelt |
| `app_registry.py` | Welche Apps für welche Rollen sichtbar sind |
| `session.py` | `Session`: Klassen-Variable, hält eingeloggten User |
| `ports.py` | Interface-Definitionen (Abstract Base Classes) für Repositories |

**Risiken**:
- `Session` ist globaler State — nicht thread-safe, nicht request-fähig. Kein Problem im Desktop-Modus. Muss für API-Betrieb ersetzt werden.
- `config.py` unterscheidet frozen/unfrozen; im Dev-Modus liegt die DB im Projektverzeichnis, im installierten Modus in `%LOCALAPPDATA%`. Das ist die Hauptursache für das Vereins-PC-Problem (s. Kapitel 18).

### 7.2 `services/auth_service.py` — Authentifizierung

**Zweck**: Login, Lockout-Verwaltung, Audit-Logging aller Auth-Events.

**Login-Prüfkette** (in Reihenfolge):
1. Felder nicht leer
2. Benutzer existiert
3. `is_active == 1`
4. Rolle nicht in `NON_LOGIN_ROLES`
5. `locked_until` nicht in der Zukunft
6. bcrypt-Verifikation

**Lockout-Logik**: Nach `MAX_FAILED_ATTEMPTS` (5) → `locked_until = jetzt + 15 Min`. Admin kann manuell entsperren.

**Audit**: Jeder Login-Vorgang → `audit_logs` mit Action (`LOGIN_SUCCESS`, `LOGIN_FAILED`, `ACCOUNT_LOCKED`). Kein Passwort, kein Hash im Log.

### 7.3 `services/claim_service.py` — Antragsverwaltung

**Zweck**: Orchestrierung des gesamten Antrags-Workflows.

Wichtige Methoden:
- `evaluate_claim()`: delegiert an `PruefungService`, gibt `dict` zurück (ohne Persistenz)
- `persist_evaluation()`: speichert Ergebnis, zählt Prüfungen, prüft 4-Augen-Sperre, benachrichtigt Supervisor nach Erstprüfung
- `update_claim_status()`: nur valide Statuses, schreibt `claim_history`
- `get_allowed_transitions()`: delegiert an `ClaimStatus.get_allowed_transitions()`

**Risiko**: Methode ist komplex (~200 Zeilen für `persist_evaluation`). Noch keine vollständigen Integrationstests für den persist-Pfad.

### 7.4 `domain/services/pruefung_service.py` — Berechnungslogik

**Zweck**: Reine, zustandslose Prüfungsberechnung ohne DB-Zugriff.

Berechnung:
```
Anspruchsgrenze = BASE_LIMIT + ADDITIONAL_ADULT_LIMIT × (Erwachsene - 1) + CHILD_LIMIT × Kinder
Härtefallgrenze = Anspruchsgrenze × HARDSHIP_FACTOR

freies_Einkommen = Summe(Einnahmen) - Summe(Ausgaben)

Status:
  freies_Einkommen ≤ Anspruchsgrenze  → ANSPRUCHSBERECHTIGT
  freies_Einkommen ≤ Härtefallgrenze  → HAERTEFALL
  sonst                               → ABGELEHNT
  Wohnbeihilfe nicht angegeben oder False → VORLAEFIG_ABGELEHNT
                                           (wenn sonst berechtigt/Härtefall)
```

Alle Grenzwerte kommen aus DB-Settings und sind über `SettingsService` änderbar.

### 7.5 `services/re_evaluation_service.py` — 4-Augen-Regel

**Zweck**: Steuert, wer wann erneut prüfen darf.

**Kernregel**: Mitarbeiter darf Antrag genau einmal eigenständig prüfen. Jede weitere Prüfung erfordert Supervisor-Freigabe. Supervisor, Admin und Standortleitung sind ausgenommen.

**Zustände**: `PENDING` → `APPROVED` / `REJECTED`. Genehmigte Freigabe wird nach der Prüfung verbraucht (`consumed_at`).

### 7.6 `services/update_service.py` — Update-System

**Zweck**: Sicheres Einspielen von Software-Updates als `.mugala`-Paket (ZIP).

**Ablauf**:
1. Validierung (Manifest, Version, Migration-Dateien vorhanden)
2. Backup vor Änderungen
3. Migration ausführen (idempotent via `update_migrations`-Tabelle)
4. Erfolg/Fehler in `update_history` protokollieren
5. Installer starten und Anwendung beenden

**Sicherheitsfeature**: Destruktive SQL-Anweisungen (`DROP TABLE`, `TRUNCATE`, `DELETE` ohne `WHERE`, `UPDATE` ohne `WHERE`) in Migrationen werden erkannt und blockiert.

### 7.7 `database/db.py` — Schema und Migration

**Zweck**: Einmaliger Aufruf `initialize_database()` beim Start — idempotent.

**Besonderheiten**:
- `CREATE TABLE IF NOT EXISTS` für alle Tabellen
- Nachträgliche Spalten via `ALTER TABLE ... ADD COLUMN` mit `try/except` (SQLite-kompatibel)
- Seed-Daten: Admin-User (immer reaktiviert), Standorte, Rollen, Kategorien, Einstellungen, Dokumenttypen, Vorlagen
- `CATEGORY_RENAMES`-Migration: veraltete Bezeichnungen werden automatisch umbenannt
- Supervisor-Rolle und Freiwillige-Rolle werden idempotent eingefügt

**Risiko**: Die Migrations-Logik ist monolithisch in einer 1.500-Zeilen-Datei. Bei weiterem Wachstum empfiehlt sich eine Auslagerung in nummerierte SQL-Dateien (via `apply_update` bereits möglich).

### 7.8 Logging

**Seit v1.1**: `RotatingFileHandler` in `bootstrap.py` → `DATA_DIR/logs/app.log`
- Max. 2 MB pro Datei, 5 Backups (max. ~10 MB)
- Alle `logger.info/warning/error`-Aufrufe landen hier
- Datenschutz: keine Passwörter, keine Hashes im Log
- Benutzername wird bei Auth-Events protokolliert

**Audit-Log**: Separate Tabelle `audit_logs` in der DB. Enthält User-ID, Action, Object-Type, Object-ID, Details, Timestamp. Sichtbar über `ui/pages/audit_log_page.py`.

---

## 8. Zustands- und Fehlerverhalten

### 8.1 Prüfungsmatrix-Schutz (seit v1.1)

`ClaimEvaluationDialog` hat folgende Schutzebenen:

| Auslöser | Verhalten |
|---|---|
| Escape-Taste / „Schließen"-Button | `reject()` → `_confirm_discard()` → Rückfrage wenn Daten vorhanden |
| Fenster-X (closeEvent) | `closeEvent()` → `_confirm_discard()` → Rückfrage |
| Exception in `evaluate_claim()` | try/except → Fehlermeldung, Dialog bleibt offen, Eingaben erhalten |
| Erfolgreiches Speichern | `_saved = True` → Schließen ohne Nachfrage |

### 8.2 Login-Fehlerverhalten

| Situation | Meldung | Audit |
|---|---|---|
| Benutzer nicht gefunden | „Benutzer nicht gefunden." | LOGIN_FAILED |
| Deaktiviert | „Benutzer ist deaktiviert. Bitte wenden Sie sich an einen Administrator." | LOGIN_FAILED |
| Gesperrt (locked_until) | „Account ist gesperrt. Bitte wenden Sie sich an einen Administrator." | ACCOUNT_LOCKED |
| Falsches Passwort | „Passwort ist falsch." | LOGIN_FAILED |
| 5. Fehlversuch | Passwortmeldung + `locked_until` wird gesetzt | ACCOUNT_LOCKED |

### 8.3 Fehlende/beschädigte Datenbank
- `initialize_database()` wird bei jedem Start aufgerufen — legt DB und Verzeichnis an wenn nicht vorhanden
- `is_database_ready()` prüft ob DB erreichbar ist
- Bei komplett beschädigter DB: Anwendung startet nicht → Restore aus Backup nötig

---

## 9. Datenmodell und Datenhaltung

### Zentrale Entitäten

| Tabelle | Beschreibung | Schlüsselfelder |
|---|---|---|
| `users` | Systembenutzer | `username`, `password_hash`, `role_id`, `is_active`, `locked_until`, `failed_attempts` |
| `roles` | Rollendefinitionen | `name` (Mitarbeiter, Standortleitung, Supervisor, Admin, Freiwillige) |
| `locations` | Standorte | `name` (Bludenz, Feldkirch, Dornbirn) |
| `categories` | Anspruchskategorien | `name` (Pensionist, Alleinerziehend, ...) |
| `persons` | Antragstellende Personen | `first_name`, `last_name`, `birth_date`, `category_id` |
| `claims` | Anträge | `case_number`, `person_id`, `status`, `evaluation_count`, `examiner_id` |
| `incomes` | Einnahmen pro Antrag | `claim_id`, `type`, `amount` |
| `expenses` | Ausgaben pro Antrag | `claim_id`, `type`, `amount`, `has_proof`, `note` |
| `household_members` | Haushaltsmitglieder | `claim_id`, `relationship`, `birth_date`, `category_id` (neu v1.1) |
| `cards` | Kundenkarten | `card_number`, `claim_id`, `status`, `expiry_date` |
| `documents` | Hochgeladene Dokumente | `claim_id`, `person_id`, `storage_path`, `status` |
| `audit_logs` | Protokollereignisse | `user_id`, `action`, `object_type`, `timestamp` |
| `claim_history` | Statusänderungshistorie | `claim_id`, `old_status`, `new_status`, `changed_by` |
| `re_evaluation_requests` | 4-Augen-Freigaben | `claim_id`, `requested_by`, `status` (`PENDING`/`APPROVED`/`REJECTED`/`CONSUMED`) |
| `update_history` | Update-Protokoll | `version`, `status`, `backup_path`, `applied_migrations` |
| `settings` | Systemparameter | `key`, `value`, `value_type` (BASE_LIMIT, CHILD_LIMIT, etc.) |

### Antragsstatus-Zustandsmaschine

```
IN_PRUEFUNG
    ├──→ ANSPRUCHSBERECHTIGT ──→ FREIGABE_KARTE
    ├──→ HAERTEFALL
    ├──→ ABGELEHNT ──→ WIDERSPRUCH ──→ IN_PRUEFUNG (Neuprüfung)
    └──→ VORLAEFIG_ABGELEHNT ──→ IN_PRUEFUNG (nach Klärung)
                                 └──→ ABGELEHNT

Alle Statuses → ARCHIVIERT (nur privilegierte Rollen)
```

### Datenkonsistenz
- Foreign Keys sind aktiviert (`PRAGMA foreign_keys = ON`)
- Alle referenziellen Integritätsfehler lösen Exceptions aus
- Migrationen sind idempotent (via `IF NOT EXISTS` oder Try/Except)
- Keine Cascading-Deletes außer bei natürlichem Eltern-Kind-Verhältnis (z. B. `claim_id → incomes`)

---

## 10. Datenbankentscheidung

### Aktuell: SQLite

**Vorteile**:
- Kein Datenbankserver, keine Konfiguration
- Datei-Backup trivial
- Ausreichend für Einzelplatz-Desktop-Betrieb

**Grenzen**:
- **Kein Mehrbenutzer-Echtzeit-Betrieb**: SQLite serialisiert Schreibzugriffe. Bei mehreren gleichzeitigen Schreibern (verschiedene Geräte) → Datenkonflikte
- **Kein zentraler Stand**: Jedes Gerät hat seine eigene Kopie → Inkonsistenz ist strukturell unvermeidbar
- **Kein WAL-Modus** aktiv (nur Checkpoint im Backup-Pfad)

### Status: PostgreSQL-Dual-Backend implementiert (seit v1.6.0)

Die ursprünglich geplante Migration ist umgesetzt — `database/db.py` unterstützt SQLite (Standard) und PostgreSQL parallel, gesteuert über `DATABASE_URL`. Repository-Klassen, Services und UI bleiben unverändert; die Umschaltung erfolgt vollständig in der Datenzugriffsschicht.

| Zeithorizont | Stand | Begründung |
|---|---|---|
| **Kurzfristig (erledigt)** | Dual-Backend implementiert | SQLite bleibt Default für Entwicklung/Tests, PostgreSQL für Produktion aktivierbar |
| **Mittelfristig (in Umsetzung)** | Zentraler PostgreSQL-Server auf Raspberry Pi, erreichbar via Tailscale-VPN | Eigene Infrastruktur statt Cloud-Anbieter — Daten bleiben selbst gehostet, kein monatliches Hosting-Budget nötig |
| **Langfristig** | PostgreSQL + API-Schicht | Skalierbar, auditfähig, mehrere Clients möglich |

### PostgreSQL-Architektur (`database/connection_adapter.py`)

`PgConnectionAdapter` bildet ein sqlite3.Connection-kompatibles Interface auf psycopg3 ab, damit alle Repositories `with get_connection() as conn:` unverändert nutzen können:

- **Platzhalter-Übersetzung**: `?` → `%s`
- **`INSERT OR IGNORE INTO` → `INSERT INTO … ON CONFLICT DO NOTHING`**, RETURNING wird syntaktisch korrekt *nach* ON CONFLICT angehängt
- **`RETURNING id` nur bei Tabellen mit `id`-Spalte**: Eine Whitelist (`_TABLES_WITHOUT_ID`, aktuell `schema_migrations`) schließt bekannte id-lose Tabellen aus. Für unbekannte Fälle läuft das INSERT in einem SQL-Savepoint; wirft PostgreSQL `undefined_column` (pgcode `42703`), wird zur Savepoint-Grenze zurückgerollt und ohne RETURNING erneut ausgeführt — ohne die umgebende Transaktion abzubrechen
- **`executescript()`** nutzt einen Mini-Parser (`_split_sql`), der Semikolons in `--`-Kommentaren und `'...'`-Stringliteralen (inkl. `''`-Escape) korrekt ignoriert, statt naiv auf `;` zu splitten
- **Row-Normalisierung**: `Decimal` → `float`, `datetime`/`date` → sqlite3-kompatible Strings

Weitere Bausteine:
- `database/schema_postgres.sql` — vollständiges Schema, alle 26 SQLite-Migrationen eingebettet (idempotent)
- `scripts/migrate_sqlite_to_postgres.py` — einmalige Datenübernahme, öffnet die SQLite-Quelle read-only
- `docs/SERVER_SETUP_RASPBERRY_PI.md` — Pi-Setup inkl. Tailscale/pg_hba.conf-Härtung
- **Kein Redis**: Kein Caching-/Queue-Bedarf erkennbar. Hinzufügen nur wenn konkrete Anforderung entsteht.

### Tests gegen beide Backends
- Alle 279 SQLite-Tests laufen weiterhin isoliert über `tmp_path`-Fixtures (kein PostgreSQL-Server nötig, auch nicht in CI)
- `tests/test_pg_adapter_integration.py` (3 Tests) läuft zusätzlich gegen eine echte PostgreSQL-Instanz, sobald `TEST_DATABASE_URL` gesetzt ist — deckt die drei kritischen Adapter-Fälle ab: INSERT mit id-Spalte, INSERT ohne id-Spalte, INSERT-OR-IGNORE-Konflikt
- Verbleibendes SQLite-spezifisches Risiko bei künftigen Schemaänderungen: neue id-lose Tabellen müssen zur `_TABLES_WITHOUT_ID`-Whitelist hinzugefügt werden (der Savepoint-Fallback fängt den Fall zwar ab, kostet aber einen Roundtrip)

---

## 11. API- und Integrationsdesign

### Ist-Stand
FastAPI, uvicorn und PyJWT sind installiert. `app/web_api.py` existiert als Platzhalter. Die API ist **nicht produktiv aktiv**.

### Vorbereitung (was bereits cloudfähig ist)
- Repository-Interface-Pattern (`app/ports.py`) entkoppelt Services von Datenbankdetails
- `ServiceContainer` (`app/container.py`) zentralisiert DI
- Services sind (fast) zustandslos — mit Ausnahme von `Session`

### Was für API-Betrieb noch angepasst werden muss
1. **`Session` ersetzen**: Globaler Klassen-State durch Request-Kontext (FastAPI Dependency Injection)
2. **Repository-Direktzugriffe eliminieren**: Einzelne Services nutzen `get_connection()` direkt statt Repository — muss hinter Interface
3. **Auth via JWT**: `PyJWT` ist bereit, `AuthService` braucht Token-Rückgabe

### Sinnvolle API-Endpunkte (Priorität)

| Bereich | Endpunkte | Priorität |
|---|---|---|
| Auth | `POST /auth/login`, `POST /auth/logout` | 1 |
| Benutzer | `GET/POST/PUT /users`, `PUT /users/{id}/active` | 2 |
| Anträge | `GET/POST /claims`, `GET /claims/{id}`, `PUT /claims/{id}/status` | 2 |
| Prüfung | `POST /claims/{id}/evaluate`, `POST /claims/{id}/persist-evaluation` | 3 |
| Haushalte | `GET/POST/PUT/DELETE /claims/{id}/household-members` | 3 |
| Personen | `GET/POST/PUT /persons` | 3 |
| Logs | `GET /audit-logs` | 4 |
| Backups | `POST /backups`, `GET /backups`, `POST /backups/{id}/restore` | 4 |

---

## 12. Authentifizierung und Autorisierung

### Login-Konzept
- bcrypt (12 Rounds) für Passwort-Hashing
- Kein JWT im Desktop-Modus (Session-Objekt in Memory)
- Passwort-Change-Pflicht steuerbar per `must_change_password`-Flag
- Lockout nach 5 Fehlversuchen für 15 Minuten

### Rollenhierarchie

```
Admin
  └── Supervisor (Freigaben erteilen, alle Transitions)
        └── Standortleitung (archivieren, Widersprüche bearbeiten)
              └── Mitarbeiter (Erstprüfung, Kartenfreigabe)
Freiwillige (kein Systemzugang, nur Datenverwaltung)
```

### Tatjana Stüttler — Erklärung des Problems (Vereins-PC)
In der Datenbank des Vereins-PCs existierten zwei Konten für Tatjana Stüttler:
- `TaStue` (Admin, `is_active=0`, `locked_until=2099`) — manuell gesperrt
- `tatjana.stuettler` (Supervisor, aktiv)

Beide wurden behoben (v1.1). Ursache: manuelle Eingriffe mit fehlerhafter `locked_until`-Setzung auf das Jahr 2099. Der Code erzeugt max. `jetzt + 15 Minuten` — das Ferndatum stammt aus einem manuellen Datenbankeingriff.

### Umgebungsprüfpunkte bei Login-Problemen
1. Welche DB liegt unter `%LOCALAPPDATA%\Anspruchssystem\system.db`?
2. `SELECT username, is_active, locked_until, r.name FROM users u JOIN roles r ON u.role_id=r.id`
3. Gibt es Konten mit `locked_until` weit in der Zukunft?
4. Gibt es doppelte Einträge für denselben Benutzer?
5. Ist der User einer `NON_LOGIN_ROLES` (z. B. Freiwillige)?

---

## 13. Logging, Monitoring und Auditierbarkeit

### Logdatei (`DATA_DIR/logs/app.log`)
- `RotatingFileHandler`: 2 MB pro Datei, 5 Backups
- Level: INFO und höher (WARNING, ERROR, CRITICAL)
- Format: `DATUM UHRZEIT [LEVEL] Modulname: Nachricht`
- Zugriff: Datei-Explorer oder Admin-Ansicht (zu implementieren)

### Audit-Log (Tabelle `audit_logs`)
Folgende Events werden protokolliert:

| Event | Kategorie | Details |
|---|---|---|
| `LOGIN_SUCCESS` | auth | Benutzername, Rolle |
| `LOGIN_FAILED` | auth | Benutzername, Grund (ohne Passwort) |
| `ACCOUNT_LOCKED` | auth | Benutzername, Sperrdauer |
| `first_evaluation_completed` | claim | Prüfer-ID, Status |
| `re_evaluation_completed` | claim | Prüfer-ID, Status |
| `evaluation_blocked` | claim | Prüfer-ID, Grund |
| `re_evaluation_requested` | claim | Anfragesteller |
| `re_evaluation_approved` | claim | Supervisor-ID |
| `re_evaluation_rejected` | claim | Supervisor-ID, Grund |
| `UPDATE_APPLIED` | system | Version, Migrationen |
| `UPDATE_FAILED` | system | Fehlermeldung |
| `BACKUP_RESTORED` | system | Backup-Pfad |
| `HAUSHALT_MITGLIED_HINZUGEFUEGT` | household_member | Antrag-ID, Name |
| `set_active` | user | User-ID, Aktivstatus |

### Datenschutz-Grenzen
- **Keine Passwörter** im Log
- **Keine bcrypt-Hashes** im Log
- Benutzernamen sind zulässig (für Nachvollziehbarkeit)
- Inhaltliche Details (z. B. Einnahmen/Ausgaben) **nicht** im Audit-Log — nur in `claims`/`incomes`/`expenses`
- Log-Cleanup: `AuditRepository.delete_old(days=2555)` — 7 Jahre Aufbewahrung gemäß Archivierungsregeln

---

## 14. Sicherheitskonzept

| Bereich | Maßnahme |
|---|---|
| Passwörter | bcrypt, 12 Rounds, kein Klartext gespeichert |
| Login | Lockout nach 5 Fehlversuchen, Fehlermeldungen ohne Info-Leak |
| Rollentrennung | Übergangsrechte strikt nach Rolle definiert |
| Prüfschutz | 4-Augen-Regel via `ReEvaluationService` |
| Updates | Destructive-SQL-Block in Migrations |
| Backups | Vor jedem Update, max. 10 automatische Backups |
| Konfiguration | `SECRET_KEY` via Umgebungsvariable `APP_SECRET_KEY` (Fallback: Warnung) |
| Audit-Logs | Alle kritischen Aktionen protokolliert |
| Sensitive Daten | Passwörter/Hashes nie im Log, durch Tests verifiziert |

**Mindestanforderungen sicherer Betrieb**:
- `APP_SECRET_KEY` in Produktionsumgebung setzen (nicht Default!)
- Datenbankdatei (`system.db`) darf nur für Anwendungsbenutzer lesbar sein
- Backup-Verzeichnis vor unbefugtem Zugriff schützen
- Updates nur aus vertrauenswürdiger Quelle und mit SHA-256-Prüfsumme

---

## 15. Teststrategie

Vollständige Testdokumentation: in `tests/` und im Commit-Log.

### Testpyramide

```
         ▲  [UI/Workflow]    — nicht automatisiert (PyQt-Tests aufwändig)
        ▲▲▲ [Integration]    — 108 Tests (DB-basiert, isolierte tmp-DB)
      ▲▲▲▲▲ [Service-Unit]   — mit Mocks (bestehende Tests)
    ▲▲▲▲▲▲▲ [Pure Unit]      — 48 Tests (ClaimStatus, PruefungService, Password)
```

### Testinfrastruktur
- **`conftest.py`**: Isolierte `tmp_path`-SQLite-DB per Test, Session-Fixtures für alle Rollen
- **`pytest.ini`**: Marker `unit`, `integration`, `slow`
- **282 Tests** (279 SQLite-Tests grün ohne weitere Voraussetzungen, 3 PostgreSQL-Adapter-Tests zusätzlich grün mit `TEST_DATABASE_URL`) — Stand 2026-06-16

### Kritisch abgedeckte Bereiche

| Bereich | Tests | Datei |
|---|---|---|
| Auth (alle Szenarien) | 10 | `test_auth_service.py` |
| Status-Übergänge (alle Rollen) | 34 | `test_claim_status.py` |
| 4-Augen-Regel | 19 | `test_re_evaluation_service.py` |
| Update/Backup/Restore | 25 | `test_update_service.py` |
| Audit-Logging / kein Passwort im Log | 12 | `test_logging_audit.py` |
| Passwort-Hashing | 13 | `test_password_service.py` |
| Haushalt-Kategorien | 12 | `test_household_service.py` |
| PostgreSQL-Adapter (optional, `TEST_DATABASE_URL`) | 3 | `test_pg_adapter_integration.py` |

### CI-Integration
- GitHub Actions (`.github/workflows/ci.yml`): Tests bei jedem Push auf `main`
- Schnelle Tests (`unit`): bei jedem Commit/PR
- Slow-Tests (`slow`): im Build-Job auf `main`

---

## 16. Deployment, Backup und Betrieb

### Aktueller Deploy-Modus
1. Entwickler baut Installer mit PyInstaller + Inno Setup
2. Installer wird als `.mugala`-Paket verpackt
3. Admin spielt Update über die Anwendungsoberfläche ein
4. Anwendung erstellt automatisch Backup → wendet Migrationen an → startet Installer → beendet sich

### CI/CD-Ablauf (empfohlen)

```
git push → GitHub Actions
  ├── Tests (python -m pytest tests/)
  ├── Linting (optional: ruff)
  └── [main] PyInstaller Build → Artifact → manuell zu .mugala signieren → veröffentlichen
```

### Backup-Strategie
- Automatisches Backup: vor jedem Update
- Manuelles Backup: über Einstellungen-Seite jederzeit möglich
- Aufbewahrung: max. 10 Backups (älteste werden gelöscht)
- Restore: über Einstellungen-Seite, erfordert Neustart

### Rollback
- Backup aus `BACKUPS_DIR` wählen → Restore → Neustart
- Altes Installationspaket erneut ausführen (Inno Setup überschreibt)

### Betriebscheckliste vor Produktiveinsatz
- [ ] Admin-Passwort geändert (`Admin2024!` ist Default → sofort ändern)
- [ ] `APP_SECRET_KEY` Umgebungsvariable gesetzt
- [ ] Backup-Verzeichnis gesichert (Dateisystem-Berechtigungen)
- [ ] Log-Verzeichnis zugänglich für Admin-Review
- [ ] Keine Testbenutzer (`test`, `mitarbeiter1`) in Produktionsdatenbank
- [ ] `UPDATE_MANIFEST_URL` in Einstellungen konfiguriert (wenn Update-Server genutzt)

---

## 17. Troubleshooting und Umgebungsanalyse

### Vereins-PC: Diagnose-Checkliste

**Schritt 1: Richtige Datenbank lokalisieren**
```
%LOCALAPPDATA%\Anspruchssystem\system.db  (installierte Version)
<Projektverzeichnis>\data\system.db        (Entwickler-Version)
```

**Schritt 2: Benutzerstatus prüfen (SQL direkt)**
```sql
SELECT u.id, u.username, u.full_name, u.is_active,
       u.failed_attempts, u.locked_until, r.name AS rolle
FROM users u
LEFT JOIN roles r ON u.role_id = r.id
ORDER BY u.id;
```
Verdächtig: `is_active = 0`, `locked_until` in der Zukunft (besonders Jahr 2099)

**Schritt 3: Umgebungsvergleich**

| Prüfpunkt | Funktionierendes Gerät | Vereins-PC |
|---|---|---|
| Python-Version | `python --version` | |
| Installierter Pfad | `%LOCALAPPDATA%\Anspruchssystem` | |
| DB-Größe | `system.db` in KB | |
| App-Version | Titelleiste / Info | |
| Benutzerkonten | s. SQL oben | |

**Schritt 4: Typische Fehlerbilder**

| Symptom | Wahrscheinliche Ursache | Lösung |
|---|---|---|
| Login schlägt für bestimmten User fehl | `is_active=0` oder `locked_until` in Zukunft | DB: User reaktivieren |
| Login funktioniert nur als Admin | Admin-Auto-Reaktivierung in `seed_basic_data()` | Andere User manuell reaktivieren |
| Prüfungsmatrix schließt sich | Exception in Service-Layer (alt: v1.0) | Update auf v1.1 |
| Keine Daten nach Gerätewechsel | Per-Gerät-SQLite, kein gemeinsamer Stand | DB-Export/Import oder `DATABASE_URL` auf zentralen PostgreSQL-Server umstellen |
| Manuelle Sperren mit Datum 2099 | Direkter DB-Eingriff durch IT | `UPDATE users SET locked_until=NULL WHERE ...` |

---

## 18. Architekturentscheidungen

### ADR-001: SQLite als Datenbank (Default, weiterhin gültig für Einzelplatz)
**Entscheidung**: SQLite bleibt Default-Backend für Entwicklung, Tests und Einzelplatzbetrieb.
**Begründung**: Keine Serverinfrastruktur nötig, triviales Backup, ausreichend wenn Geräte isoliert bleiben.
**Konsequenz**: Kein gemeinsamer Datenstand zwischen Geräten — gilt nur noch für Installationen ohne `DATABASE_URL`.
**Revisionsauslöser**: Erledigt durch ADR-007 (Dual-Backend) für Mehrgeräte-Standorte.

### ADR-002: Pro-Gerät-Datenbank (überholt durch zentrale PostgreSQL-Option)
**Entscheidung**: Jedes Gerät hat `%LOCALAPPDATA%\Anspruchssystem\system.db`.
**Begründung**: Vereinfacht Installation, keine Netzwerkabhängigkeit.
**Konsequenz**: War die Hauptursache aller Synchronisationsprobleme und Umgebungsunterschiede.
**Revisionsauslöser**: Durch ADR-007 abgelöst — Standorte mit Mehrgeräte-Bedarf nutzen `DATABASE_URL` gegen einen zentralen Raspberry-Pi-Server.

### ADR-003: Logging im Admin-Bereich sichtbar
**Entscheidung**: `audit_logs` in DB, sichtbar über `audit_log_page`.
**Begründung**: Nachvollziehbarkeit von Login-Fehlern, Prüfungsentscheidungen, Updates. Wichtig für Datenschutz und Fehlerbehebung.

### ADR-004: Prüfungsmatrix darf nicht unbeabsichtigt schließen
**Entscheidung**: `reject()` und `closeEvent()` prüfen unsaved state.
**Begründung**: Bekannter Bug: Eingaben gingen bei Ausnahmen verloren. Datenverlust in Produktivbetrieb ist inakzeptabel.

### ADR-005: API erst modular vorbereiten, nicht sofort auslagern
**Entscheidung**: Repository-Pattern und DI-Container vorhanden, aber keine aktive API.
**Begründung**: Für Desktop-Einzelplatz unnötig. Erste Priorität: stabile, korrekte Datenhaltung. API erst wenn Cloud-Anbindung konkret wird.

### ADR-006: Kein Redis
**Entscheidung**: Redis wird nicht eingesetzt.
**Begründung**: Kein Caching-, Queue- oder PubSub-Bedarf erkennbar. Würde nur Betriebskomplexität hinzufügen.

### ADR-007: PostgreSQL-Dual-Backend statt Hard-Cutover
**Entscheidung**: `database/db.py` unterstützt SQLite und PostgreSQL gleichzeitig über `DATABASE_URL`; `PgConnectionAdapter` bildet die sqlite3-Schnittstelle nach, statt Repositories für PostgreSQL neu zu schreiben.
**Begründung**: Repository-Pattern war bereits vorhanden — ein kompatibler Adapter erlaubt produktiven Einsatz ohne jede Repository-Klasse anzufassen, und Tests/CI bleiben ohne PostgreSQL-Server lauffähig.
**Konsequenz**: Der Adapter muss SQLite-Eigenheiten aktiv nachbilden (z. B. `lastrowid`), was Sonderfälle wie id-lose Tabellen (`schema_migrations`) erfordert. Gelöst über Whitelist + Savepoint-Fallback bei `undefined_column` (pgcode 42703), siehe Abschnitt 10.
**Revisionsauslöser**: Wenn der Adapter-Overhead (zusätzlicher Savepoint-Roundtrip je INSERT in unbekannte Tabellen) messbar zum Performance-Problem wird.

### ADR-008: Eigener Raspberry-Pi-Server statt Supabase/Cloud
**Entscheidung**: Zentraler PostgreSQL-Server läuft auf einem Raspberry Pi (24/7), Zugriff ausschließlich über Tailscale-VPN (100.64.0.0/10), kein öffentliches Port-Forwarding.
**Begründung**: Daten bleiben selbst gehostet (Datenschutz, kein laufendes Cloud-Budget), Tailscale erspart komplexe Firewall-/VPN-Konfiguration.
**Konsequenz**: Verfügbarkeit hängt an Heimnetz/Pi-Stabilität statt an einem SLA-gestützten Cloud-Anbieter; Monitoring der VPN-Verbindung ist Eigenverantwortung.
**Revisionsauslöser**: Wenn Standortzahl oder Lastanforderungen einen Managed-Service rechtfertigen.

---

## 19. Offene Punkte und Roadmap

### Kritische offene Punkte

| Punkt | Priorität | Status |
|---|---|---|
| Zentrale Datenbank (PostgreSQL, Raspberry Pi) | Hoch | **In Umsetzung** — Dual-Backend implementiert, Produktiv-Pi noch nicht aktiviert |
| Admin-UI für Log-Ansicht mit Filter | Mittel | Basis vorhanden, Filter fehlen |
| `persist_evaluation()` Integrationstests | Mittel | ✓ Abgeschlossen (v1.3.0) |
| `UserService` Tests | Mittel | Offen |
| `Session` durch Request-Kontext ersetzen | Mittel | Für API-Betrieb nötig |
| Direkte `get_connection()`-Aufrufe in Services | Niedrig | Refactor für API |
| pytest in CI-Workflow vollständig aktiv | Hoch | Workflow vorhanden |

### Geplante Erweiterungen

1. **PostgreSQL-Produktivaktivierung** (kurzfristig): Code ist fertig (`connection_adapter.py`, `schema_postgres.sql`, Migrationsskript). Noch offen: Raspberry-Pi-Hardware aufsetzen, `DATABASE_URL` auf Produktivgeräten aktivieren, Migration laufen lassen.
2. **API-Schicht** (nach Pi-Aktivierung): FastAPI/uvicorn bereit, Session durch Request-Kontext ersetzen.
3. **Admin-Log-Filter**: Audit-Log-Seite um Filter (Aktion, Benutzer, Zeitraum) und Export erweitern.
4. **Monitoring**: Strukturiertes Logging mit Alerting (z. B. bei wiederholten Login-Fehlschlägen).
5. **Automatisches Backup-Monitoring**: Warnung wenn letztes Backup zu alt.

---

## 20. Anhänge

### Glossar

| Begriff | Erklärung |
|---|---|
| Antrag / Claim | Antrag einer Person auf Anspruchsberechtigung |
| Anspruchsgrenze | Maximal zulässiges freies Einkommen für volle Berechtigung |
| Härtefallgrenze | Anspruchsgrenze × Härtefallfaktor (Standard: 1.1) |
| Prüfungsmatrix | Dialog mit Einnahmen-/Ausgaben-Tabellen zur Anspruchsberechnung |
| 4-Augen-Regel | Mitarbeiter darf nur einmal eigenständig prüfen; weitere Prüfung via Supervisor |
| Seed-Daten | Basisdaten (Rollen, Standorte, Kategorien, Admin-User), die bei jedem Start idempotent eingespielt werden |
| NON_LOGIN_ROLES | Rollen ohne Systemzugang (aktuell: „Freiwillige") |
| locked_until | Zeitstempel bis wann ein Account gesperrt ist (Lockout oder manuell) |
| .mugala | Dateiformat für Update-Pakete (ZIP mit manifest.json) |
| WAL | Write-Ahead Log — SQLite-Mechanismus für Datenkonsistenz beim Backup |

### Wichtige Konfigurationsparameter

| Key | Beschreibung | Default |
|---|---|---|
| `BASE_LIMIT` | Anspruchsgrenze für erste erwachsene Person (€) | 820.00 |
| `ADDITIONAL_ADULT_LIMIT` | Zuschlag pro weiterer erwachsener Person (€) | 390.00 |
| `CHILD_LIMIT` | Zuschlag pro Kind (€) | 185.00 |
| `HARDSHIP_FACTOR` | Multiplikator für Härtefallgrenze | 1.1 |
| `CASE_NUMBER_PREFIX` | Präfix für Fallnummern | AS |
| `UPDATE_MANIFEST_URL` | URL zum Update-Manifest | (leer) |
| `APP_SECRET_KEY` | Umgebungsvariable für JWT-Secret | Pflicht in Produktion |

### Verweise

- Testdokumentation: `tests/` (282 Tests, Ausführung: `python -m pytest tests/`)
- CI/CD-Workflow: `.github/workflows/ci.yml`
- Benutzerhandbuch: `Benutzerhandbuch.pdf`
- Diagnosescript für Vereins-PC: s. Kapitel 17
- Repository: https://github.com/schienenzeit-art/minguatalada

### Zu validieren / offene Platzhalter

- [ ] Genaue Pfade auf Vereins-PC verifizieren (Windows-Benutzerprofil)
- [ ] IT-Verantwortlicher Verein: Welche manuellen Eingriffe wurden vorgenommen?
- [ ] Supabase-Projekt einrichten und Verbindungstest durchführen
- [ ] DSGVO-Analyse: Welche personenbezogenen Daten werden gespeichert, wie lange?
- [ ] Backup-Aufbewahrungspflichten mit Vereinsführung abstimmen
- [ ] Produktionsinstallation auf Vereins-PC nach v1.1 validieren
