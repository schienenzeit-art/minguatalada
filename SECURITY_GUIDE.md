# Security Guide
## Min Guata Lada — Anspruchsverwaltung

| Feld | Wert |
|---|---|
| **Dokumentname** | Security Guide — Min Guata Lada ERP |
| **Version** | 1.0 |
| **Status** | Draft |
| **Datum** | 2026-06-16 |
| **Owner** | Dario Schaer / Projektleitung |
| **Verwandte Dokumente** | [TECHNICAL_DESIGN_DOCUMENT.md](TECHNICAL_DESIGN_DOCUMENT.md), [OPERATIONS_GUIDE.md](OPERATIONS_GUIDE.md) |

---

## 1. Zweck und Geltungsbereich

Dieses Dokument bündelt alle sicherheits- und datenschutzrelevanten Aspekte von Min Guata Lada: Authentifizierung, Berechtigungen, das Threat Model mit Reaktionsplänen, Audit-Logging und die DSGVO-relevanten Grundlagen.

**Nicht Teil dieses Dokuments**: Architektur/Code-Design (siehe [Technical Design Document](TECHNICAL_DESIGN_DOCUMENT.md)), operative Diagnose/Restore-Schritte (siehe [Operations Guide](OPERATIONS_GUIDE.md)).

**Hinweis**: Dieses Dokument ersetzt **keine** rechtliche Beratung. Mit „rechtlich zu prüfen" markierte Punkte erfordern Abstimmung mit der Vereinsführung bzw. einer datenschutzrechtlichen Beratung.

---

## 2. Authentifizierung und Autorisierung

### Login-Konzept

- bcrypt (12 Rounds) für Passwort-Hashing — kein Klartext-Passwort wird gespeichert
- Kein JWT im Desktop-Modus (Session-Objekt in Memory, pro Prozess)
- Passwort-Change-Pflicht steuerbar per `must_change_password`-Flag
- Lockout nach 5 Fehlversuchen für 15 Minuten (`AuthService`)

### Login-Prüfkette (in Reihenfolge)

1. Felder nicht leer
2. Benutzer in DB vorhanden
3. `is_active == 1`
4. Rolle nicht in `NON_LOGIN_ROLES` (z. B. „Freiwillige")
5. `locked_until` nicht in der Zukunft
6. bcrypt-Passwortabgleich

### Rollenhierarchie

```
Admin
  └── Supervisor (Freigaben erteilen, alle Transitions)
        └── Standortleitung (archivieren, Widersprüche bearbeiten)
              └── Mitarbeiter (Erstprüfung, Kartenfreigabe)
Freiwillige (kein Systemzugang, nur Datenverwaltung)
```

---

## 3. Berechtigungskonzept

| Rolle | Erstprüfung | Erneute Prüfung | Archivieren | Freigaben genehmigen | Administration |
|---|---|---|---|---|---|
| **Mitarbeiter** | Ja (1×) | Nur mit Freigabe | Nein | Nein | Nein |
| **Standortleitung** | Ja | Ja | Ja | Ja | Nein |
| **Supervisor** | Ja | Ja | Ja | Ja | Ja |
| **Admin** | Ja | Ja | Ja | Ja | Ja |
| **Freiwillige** | — | — | — | — | — (kein Login) |

**4-Augen-Regel**: Ein Mitarbeiter darf einen Antrag genau einmal eigenständig prüfen. Jede weitere Prüfung erfordert eine explizite Supervisor-Freigabe (`ReEvaluationService`, Zustände `PENDING → APPROVED/REJECTED`, einmal verbrauchbar via `consumed_at`). Supervisor, Admin und Standortleitung sind von dieser Einschränkung ausgenommen.

**Prinzip**: Berechtigungen werden serverseitig (Service-Layer) durchgesetzt, nicht nur in der UI verborgen — UI-Elemente sind ausgeblendet, die zugrunde liegende Service-Methode prüft die Rolle zusätzlich.

---

## 4. Security Threat Model

Konkrete Risiken für eine Desktop-Anwendung mit lokal/zentral gespeicherten personenbezogenen und finanziellen Daten, mit bestehenden Gegenmaßnahmen und Reaktionsplan bei Eintritt.

| Risiko | Eintrittswahrscheinlichkeit | Auswirkung | Bestehende Mitigation | Reaktion bei Eintritt |
|---|---|---|---|---|
| **Gestohlener Laptop/PC** | Mittel | Hoch — lokale SQLite-Datei enthält Klartextdaten zu Personen/Anträgen | Login-Pflicht; keine automatische Anmeldung; Betriebssystem-Login als zusätzliche Hürde (außerhalb der App-Kontrolle, **mit Vereinsführung zu verifizieren** ob Festplattenverschlüsselung/BitLocker aktiv ist) | 1. Gerät umgehend aus dem Tailscale-VPN entfernen (Key-Revoke, falls Dual-Backend aktiv).<br>2. Passwörter aller Benutzer, die auf diesem Gerät aktiv waren, zurücksetzen.<br>3. Prüfen, ob lokale DB durch BitLocker/Diskverschlüsselung geschützt war.<br>4. Vorfall im Audit-Log/Vorfallsprotokoll dokumentieren, Vereinsführung informieren.<br>5. DSGVO-Meldepflicht prüfen (Art. 33/34 — **rechtlich zu prüfen**) |
| **Datenbankkopie (Datei oder Dump entwendet)** | Niedrig–Mittel | Hoch — vollständiger Datenbestand exponiert (Personen, Anträge, Einnahmen/Ausgaben, Benutzerkonten) | Passwort-Hashes statt Klartext (bcrypt); zentraler PostgreSQL-Server nur über Tailscale-VPN erreichbar, kein öffentliches Port-Forwarding (ADR-008) | 1. Umfang feststellen: welche Kopie, welcher Zeitstand, welcher Weg (USB, Netzwerk, Backup-Ordner)?<br>2. Betroffene Personen/Datensätze identifizieren.<br>3. Alle Benutzer-Passwörter zurücksetzen (Vorsichtsmaßnahme, falls Hashes mit entwendet wurden).<br>4. DSGVO-Meldepflicht prüfen (**rechtlich zu prüfen**), ggf. Betroffene informieren.<br>5. Backup-Verzeichnis-Zugriffsrechte nachträglich härten |
| **SQL Injection** | Niedrig | Hoch (potenziell vollständiger DB-Zugriff) | Durchgängig parametrisierte Queries (`?` bei SQLite, `%s` bei PostgreSQL über `PgConnectionAdapter`); kein dynamisches String-Concat von Benutzereingaben in SQL irgendwo im Code | 1. Verdächtige Eingabe/Stelle isolieren (z. B. über Audit-Log oder Fehlermeldung).<br>2. Code-Review/Grep nach String-Concatenation in SQL-Aufrufen (`f"...{user_input}..."`, `% input`, `.format(`) im betroffenen Modul.<br>3. Fix auf parametrisierte Query umstellen, Regressionstest ergänzen.<br>4. Betroffene Daten auf Integrität prüfen |
| **Passwort-Leak** (Phishing, schwaches Passwort, Wiederverwendung, Brute-Force) | Mittel | Mittel–Hoch, abhängig von der Rolle des betroffenen Kontos | bcrypt-Hashing; Lockout nach 5 Fehlversuchen (15 Min); keine Mindestkomplexitätsprüfung aktuell implementiert (**Lücke, siehe Mindestanforderungen unten**) | 1. Betroffenes Konto sofort deaktivieren (`is_active=0`) oder Passwort zurücksetzen.<br>2. Audit-Log auf ungewöhnliche Logins/Aktionen im fraglichen Zeitraum prüfen.<br>3. Betroffenen Benutzer informieren, neues Passwort vergeben lassen.<br>4. Bei Admin-/Supervisor-Konten: alle von diesem Konto vorgenommenen Aktionen im Audit-Log gegenprüfen |
| **VPN-Ausfall** (Tailscale/Raspberry-Pi nicht erreichbar) | Mittel | Mittel — kein zentraler Datenzugriff, aber kein Datenverlust dank Dual-Backend (ADR-007) | Dual-Backend-Architektur: Geräte ohne `DATABASE_URL`-Erreichbarkeit können (bei entsprechender Konfiguration) auf lokale SQLite ausweichen | 1. Diagnose gemäß [Operations Guide, Abschnitt 9](OPERATIONS_GUIDE.md#9-vpn-postgresql-ausfall-dual-backend-betrieb).<br>2. Bei längerem Ausfall: betroffene Geräte temporär auf lokalen SQLite-Modus umstellen.<br>3. Nach Wiederherstellung: Datenstand manuell abgleichen (aktuell kein automatischer Sync — **bekannte Lücke**, siehe Abschnitt 9).<br>4. Pi-Verfügbarkeit überwachen (kein automatisiertes Monitoring aktuell vorhanden) |

### Bekannte Lücken (aus diesem Threat Model abgeleitet)

- Keine erzwungene Passwort-Mindestkomplexität beim Anlegen/Ändern von Konten
- Kein automatischer Datenabgleich nach VPN-Wiederherstellung zwischen lokalem SQLite-Fallback und zentralem PostgreSQL
- Festplattenverschlüsselung auf Vereins-PCs nicht zentral verifiziert/erzwungen
- Kein automatisiertes Monitoring/Alerting bei Pi-/VPN-Ausfall

---

## 5. Sicherheitsmaßnahmen im Überblick

| Bereich | Maßnahme |
|---|---|
| Passwörter | bcrypt, 12 Rounds, kein Klartext gespeichert |
| Login | Lockout nach 5 Fehlversuchen, Fehlermeldungen ohne Info-Leak |
| Rollentrennung | Übergangsrechte strikt nach Rolle definiert, serverseitig durchgesetzt |
| Prüfschutz | 4-Augen-Regel via `ReEvaluationService` |
| Updates | Destructive-SQL-Block in Migrationen (`DROP TABLE`, `TRUNCATE`, `DELETE`/`UPDATE` ohne `WHERE`) |
| Backups | Vor jedem Update, max. 10 automatische Backups |
| Konfiguration | `SECRET_KEY` via Umgebungsvariable `APP_SECRET_KEY` (Fallback: Warnung) |
| Netzwerkzugriff (PostgreSQL) | Ausschließlich über Tailscale-VPN, kein öffentliches Port-Forwarding |
| Audit-Logs | Alle kritischen Aktionen protokolliert |
| Sensitive Daten | Passwörter/Hashes nie im Log, durch Tests verifiziert (`test_logging_audit.py`) |

### Mindestanforderungen sicherer Betrieb

- `APP_SECRET_KEY` in Produktionsumgebung setzen (nicht Default!)
- Datenbankdatei (`system.db`) darf nur für Anwendungsbenutzer lesbar sein
- Backup-Verzeichnis vor unbefugtem Zugriff schützen
- Updates nur aus vertrauenswürdiger Quelle und mit Signaturprüfung (Ed25519, seit v1.2.0)

---

## 6. Logging, Monitoring und Auditierbarkeit

### Audit-Log (Tabelle `audit_logs`)

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

### Datenschutz-Grenzen im Logging

- **Keine Passwörter** im Log (weder Logdatei noch Audit-Log)
- **Keine bcrypt-Hashes** im Log
- Benutzernamen sind zulässig (für Nachvollziehbarkeit erforderlich)
- Inhaltliche Details (z. B. Einnahmen/Ausgaben) **nicht** im Audit-Log — nur in den Fachtabellen (`claims`/`incomes`/`expenses`)
- Aufbewahrung: `AuditRepository.delete_old(days=2555)` — 7 Jahre, gemäß Archivierungsregeln

Praktische Schritte zum Lesen der Logdatei: siehe [Operations Guide, Abschnitt 10](OPERATIONS_GUIDE.md#10-logs-prüfen).

---

## 7. DSGVO / Datenschutz

> **Hinweis**: Dies ist eine technische Bestandsaufnahme, **keine** Datenschutz-Folgenabschätzung (DPIA) im rechtlichen Sinn. Eine vollständige DSGVO-Analyse mit der Vereinsführung steht aus.

### Verarbeitete personenbezogene Daten (Ist-Stand aus dem Datenmodell)

| Tabelle | Personenbezogene Felder | Sensitivität |
|---|---|---|
| `persons` | Vorname, Nachname, Geburtsdatum | Normal |
| `household_members` | Vorname, Nachname, Geburtsdatum, Beziehung | Normal |
| `claims`/`incomes`/`expenses` | Einnahmen, Ausgaben, Wohnsituation | **Erhöht** — finanzielle Verhältnisse |
| `users` | Benutzername, Klarname, Passwort-Hash | Normal (Hash, kein Klartext) |
| `documents` | Hochgeladene Belege (können Ausweise, Einkommensnachweise enthalten) | **Erhöht** |
| `audit_logs` | Benutzername, Aktion, Zeitstempel | Normal (keine Inhalte) |

### Offene Punkte (rechtlich zu prüfen)

- [ ] Rechtsgrundlage der Verarbeitung dokumentieren (vermutlich berechtigtes Interesse / Vertragserfüllung im Rahmen der Vereinsleistung)
- [ ] Aufbewahrungsfristen pro Datenkategorie festlegen (aktuell nur für Audit-Logs definiert: 7 Jahre)
- [ ] Löschkonzept für `claims`/`documents` nach Ablauf der Aufbewahrungsfrist (aktuell keine automatische Löschung)
- [ ] Betroffenenrechte (Auskunft, Löschung, Berichtigung) — Prozess für Anfragen Betroffener definieren
- [ ] Auftragsverarbeitungsvertrag (AVV) falls der Raspberry-Pi-Betrieb oder Hosting durch Dritte erfolgt — aktuell **selbst betrieben**, daher vermutlich kein AVV nötig, aber zu bestätigen
- [ ] Datenschutzerklärung für Antragstellende (Information nach Art. 13/14 DSGVO) — Status unbekannt, mit Vereinsführung klären

### Bereits umgesetzte technische Schutzmaßnahmen (datenschutzrelevant)

- Passwörter ausschließlich gehasht (bcrypt) gespeichert
- Zugriff auf den zentralen PostgreSQL-Server ausschließlich über VPN (keine öffentliche Erreichbarkeit)
- Rollenbasierte Zugriffskontrolle begrenzt, wer welche Daten einsehen/bearbeiten kann
- Audit-Log dokumentiert Zugriffe und Änderungen ohne sensible Inhalte zu protokollieren

---

## 8. Vorfall-Fallstudie: Tatjana Stüttler (Vereins-PC)

In der Datenbank des Vereins-PCs existierten zwei Konten für dieselbe Person:
- `TaStue` (Admin, `is_active=0`, `locked_until=2099`) — manuell gesperrt
- `tatjana.stuettler` (Supervisor, aktiv)

**Ursache**: Manuelle Datenbankeingriffe mit fehlerhafter `locked_until`-Setzung auf das Jahr 2099. Der reguläre Code erzeugt maximal `jetzt + 15 Minuten` — das Ferndatum 2099 stammt zweifelsfrei aus einem direkten, undokumentierten Datenbankeingriff, nicht aus regulärem Anwendungsverhalten.

**Behoben**: v1.1.0 — Duplikat bereinigt, Konten konsolidiert.

**Lehre für künftige manuelle DB-Eingriffe**:
- Manuelle `UPDATE`/`DELETE`-Eingriffe an `users` nur über dokumentierte, nachvollziehbare Kommandos (siehe [Operations Guide](OPERATIONS_GUIDE.md))
- Vor jedem manuellen Eingriff: Backup erstellen
- Eingriffe im Audit-Log oder zumindest in einer Übergabe-Notiz dokumentieren — aktuell gibt es **keine automatische Protokollierung manueller SQL-Eingriffe außerhalb der Anwendung**

---

## 9. Verweise

- Architektur, Komponenten, ADRs: [TECHNICAL_DESIGN_DOCUMENT.md](TECHNICAL_DESIGN_DOCUMENT.md)
- Operative Diagnose, Backup/Restore, VPN-Troubleshooting: [OPERATIONS_GUIDE.md](OPERATIONS_GUIDE.md)
- Raspberry-Pi-Server-Härtung (Tailscale, `pg_hba.conf`): `docs/SERVER_SETUP_RASPBERRY_PI.md`
- Tests zu Sicherheitseigenschaften: `tests/test_logging_audit.py`, `tests/test_password_service.py`, `tests/test_auth_service.py`

---

*Stand: 2026-06-16 — Version 1.0*
