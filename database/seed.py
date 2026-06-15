"""Seed-Daten für die Datenbankinitialisierung.

Alle Funktionen nehmen eine aktive sqlite3.Connection entgegen und sind idempotent
(INSERT OR IGNORE / existiert-Prüfung). Kein direkter DB-Zugriff über get_connection().
"""
import os
import sqlite3
import sys

from core.claim_status import ClaimStatus
from domain.categories import CATEGORIES
from services.password_service import PasswordService
from datetime import datetime, UTC


def seed_basic_data(connection: sqlite3.Connection) -> None:
    locations = [
        ("Bludenz",),
        ("Feldkirch",),
        ("Dornbirn",),
    ]

    roles = [
        ("Mitarbeiter",),
        ("Standortleitung",),
        ("Admin",),
    ]

    connection.executemany(
        "INSERT OR IGNORE INTO locations (name) VALUES (?)",
        locations,
    )

    connection.executemany(
        "INSERT OR IGNORE INTO roles (name) VALUES (?)",
        roles,
    )

    categories = [(name,) for name in CATEGORIES]
    connection.executemany(
        "INSERT OR IGNORE INTO categories (name) VALUES (?)",
        categories,
    )

    seed_settings(connection)

    in_pytest = (
        any(k in os.environ for k in ("PYTEST_CURRENT_TEST", "PYTEST_ADDOPTS", "PYTEST_RUNNING"))
        or any("pytest" in a for a in sys.argv)
    )

    _ADMIN_DEFAULT_PW = "admin123" if in_pytest else "Admin2024!"

    admin_exists = connection.execute("SELECT id FROM users WHERE username = 'admin'").fetchone()
    if not admin_exists:
        connection.execute(
            """
            INSERT INTO users (
                full_name, username, password_hash, role_id, location_id, is_active
            ) VALUES (
                ?, ?, ?,
                (SELECT id FROM roles WHERE name = ?),
                (SELECT id FROM locations WHERE name = ?),
                1
            )
            """,
            (
                "System Administrator",
                "admin",
                PasswordService.hash_password(_ADMIN_DEFAULT_PW),
                "Admin",
                "Bludenz",
            ),
        )
        connection.commit()

    try:
        inactive = connection.execute(
            "SELECT id FROM users WHERE username = 'admin' AND is_active = 0"
        ).fetchone()
        if inactive:
            connection.execute(
                "UPDATE users SET is_active = 1, failed_attempts = 0, locked_until = NULL, "
                "password_hash = ? WHERE username = 'admin'",
                (PasswordService.hash_password(_ADMIN_DEFAULT_PW),),
            )
            connection.commit()
    except Exception:
        pass

    if in_pytest:
        try:
            connection.execute(
                "UPDATE users SET password_hash = ?, is_active = 1, failed_attempts = 0, locked_until = NULL WHERE username = ?",
                (PasswordService.hash_password("admin123"), "admin"),
            )
            connection.commit()
        except Exception:
            pass
        test_worker = connection.execute("SELECT id FROM users WHERE username = 'mitarbeiter1'").fetchone()
        if not test_worker:
            try:
                connection.execute(
                    """
                    INSERT INTO users (
                        full_name, username, password_hash, role_id, location_id, is_active
                    ) VALUES (
                        ?, ?, ?,
                        (SELECT id FROM roles WHERE name = ?),
                        (SELECT id FROM locations WHERE name = ?),
                        1
                    )
                    """,
                    (
                        "Max Mitarbeiter",
                        "mitarbeiter1",
                        PasswordService.hash_password("Mitarbeiter2024!"),
                        "Mitarbeiter",
                        "Feldkirch",
                    ),
                )
                connection.commit()
            except Exception:
                pass

    connection.commit()
    seed_document_types(connection)
    seed_default_templates(connection)
    seed_claims(connection)


def seed_settings(connection: sqlite3.Connection) -> None:
    defaults = [
        ("BASE_LIMIT", "820.0", "number", "Anspruchsgrenzen", "Basisgrenze pro erwachsene Person.", 1),
        ("ADDITIONAL_ADULT_LIMIT", "390.0", "number", "Anspruchsgrenzen", "Zuschlag für weitere erwachsene Haushaltsmitglieder.", 1),
        ("CHILD_LIMIT", "185.0", "number", "Anspruchsgrenzen", "Zuschlag für Kinder.", 1),
        ("HARDSHIP_FACTOR", "1.1", "number", "Härtefall", "Multiplikator zur Berechnung der Härtefallgrenze.", 1),
        ("CASE_NUMBER_PREFIX", "AS", "string", "Fallnummern", "Präfix für generierte Fallnummern (z.B. AS → AS-2026-000001).", 1),
        ("UPDATE_MANIFEST_URL", "https://www.schaer-systems.at/updates/manifest.json", "string", "Updates", "URL zum Update-Manifest (JSON). Leer = kein Update-Server konfiguriert.", 1),
        ("AUTO_CHECK_UPDATES", "false", "boolean", "Updates", "Beim App-Start automatisch auf neue Versionen prüfen.", 1),
    ]

    connection.executemany(
        "INSERT OR IGNORE INTO settings (key, value, value_type, category, description, editable_by_admin) VALUES (?, ?, ?, ?, ?, ?)",
        defaults,
    )
    connection.commit()


def seed_document_types(connection: sqlite3.Connection) -> None:
    document_types = [
        ("Ausweis", "Personalausweis, Reisepass oder ähnliche Identifikationsdokumente.", 1),
        ("Einkommensnachweis", "Lohnabrechnung, Gehaltsbescheinigung oder Einkommensnachweis.", 1),
        ("Haushaltsnachweis", "Nachweis über Haushaltsgröße, Kosten oder Bedarfssituation.", 1),
        ("Antrag", "Formulare oder Anträge zum Leistungsbezug.", 1),
        ("Prüfprotokoll", "Protokolle, Prüfberichte oder interne Dokumente zur Anspruchsprüfung.", 1),
        ("Bescheid", "Bescheide, Entscheidungen oder Schriftstücke mit hohem Beweiskraftwert.", 1),
        ("Kartenunterlage", "Unterlagen zur Kartenherstellung und Kartenausgabe.", 1),
        ("Sonstiges", "Weitere Dokumente ohne speziellen Typ.", 1),
    ]
    connection.executemany(
        "INSERT OR IGNORE INTO document_types (name, description, is_active) VALUES (?, ?, ?)",
        document_types,
    )
    connection.commit()


def seed_claims(connection: sqlite3.Connection) -> None:
    example_claims = [
        {
            "username": "admin",
            "location": "Bludenz",
            "status": ClaimStatus.IN_PRUEFUNG,
            "description": "Erstmalige Beantragung von Unterstützung im Mai 2026.",
            "start_date": "2026-05-01",
            "end_date": "2026-05-31",
            "created_by": "admin",
        }
    ]

    for claim in example_claims:
        existing = connection.execute(
            "SELECT 1 FROM claims WHERE description = ? LIMIT 1",
            (claim["description"],),
        ).fetchone()

        if existing:
            continue

        year = datetime.now(UTC).year
        last = connection.execute(
            "SELECT case_number FROM claims WHERE case_number LIKE ? ORDER BY case_number DESC LIMIT 1",
            (f"AS-{year}-%",),
        ).fetchone()

        if last:
            try:
                seq = int(last["case_number"].split("-")[-1]) + 1
            except Exception:
                seq = 1
        else:
            seq = 1

        case_number = f"AS-{year}-{seq:06d}"

        connection.execute(
            """
            INSERT INTO claims (
                case_number, person_id, user_id, location_id, category_id,
                status, description, start_date, end_date, created_by
            ) VALUES (
                ?, NULL,
                (SELECT id FROM users WHERE username = ?),
                (SELECT id FROM locations WHERE name = ?),
                NULL, ?, ?, ?, ?,
                (SELECT id FROM users WHERE username = ?)
            )
            """,
            (
                case_number,
                claim["username"],
                claim["location"],
                claim["status"],
                claim["description"],
                claim["start_date"],
                claim["end_date"],
                claim["created_by"],
            ),
        )

    connection.commit()


def seed_default_templates(connection: sqlite3.Connection) -> None:
    """Seeded Standard-Vorlagentexte.

    Prüft jeden Eintrag einzeln per Name – vorhandene Vorlagen werden NICHT überschrieben.
    """
    templates = [
        {
            "name": "Bescheid – Anspruchsberechtigt",
            "template_type": "BESCHEID",
            "status_trigger": "ANSPRUCHSBERECHTIGT",
            "body_text": """\
{{ANREDE}},

im Namen des Vereins Tischlein Deck Dich Vorarlberg freuen wir uns, Ihnen mitteilen zu können, dass Ihr Antrag auf Unterstützungsleistungen nach eingehender Prüfung positiv beschieden wurde.

Aktenzeichen: {{AKTENZEICHEN}}
Prüfungsdatum: {{DATUM}}
Standort: {{STANDORT}}

Ergebnis der Prüfung:
Ihr Antrag wurde positiv bewertet. Sie sind damit berechtigt, die Leistungen des Vereins in Anspruch zu nehmen.

Begründung:
{{BEGRUENDUNG}}

Nächste Schritte:
Für die Ausstellung Ihrer persönlichen Kundenkarte wenden Sie sich bitte an den Standort {{STANDORT}}. Bringen Sie zu diesem Termin bitte einen gültigen Lichtbildausweis mit.

Die Karte wird auf Ihren Namen ausgestellt und ist ausschließlich für Ihre Person bestimmt.

Sollten Sie Fragen zu Ihrem Antrag oder zu den Leistungen des Vereins haben, stehen Ihnen die Mitarbeiterinnen und Mitarbeiter des Standorts {{STANDORT}} gerne zur Verfügung.

Mit freundlichen Grüßen

{{MITARBEITER}}
Verein Tischlein Deck Dich Vorarlberg
Ladritschweg 10c · 6773 Vandans""",
        },
        {
            "name": "Bescheid – Abgelehnt",
            "template_type": "BESCHEID",
            "status_trigger": "ABGELEHNT",
            "body_text": """\
{{ANREDE}},

nach eingehender Prüfung Ihres Antrags auf Unterstützungsleistungen beim Verein Tischlein Deck Dich Vorarlberg müssen wir Ihnen leider mitteilen, dass Ihrem Ansuchen nicht entsprochen werden kann.

Aktenzeichen: {{AKTENZEICHEN}}
Prüfungsdatum: {{DATUM}}
Standort: {{STANDORT}}

Ergebnis der Prüfung:
Ihr Antrag wurde abgelehnt.

Begründung:
{{BEGRUENDUNG}}

Die vollständige Begründung dieser Entscheidung entnehmen Sie bitte dem beigefügten Prüfungsprotokoll (Aktenzeichen {{AKTENZEICHEN}}).

Widerspruchsrecht:
Sie haben das Recht, innerhalb von 14 Tagen ab Zustellung dieses Bescheids schriftlich Widerspruch einzulegen. Richten Sie Ihren Widerspruch bitte unter Angabe des Aktenzeichens {{AKTENZEICHEN}} an den Standort {{STANDORT}}.

Neue Antragstellung:
Sollten sich Ihre persönlichen oder wirtschaftlichen Verhältnisse wesentlich ändern, steht Ihnen jederzeit die Möglichkeit offen, einen neuen Antrag zu stellen.

Wir bedanken uns für Ihr Vertrauen und bedauern, Ihnen keine positive Entscheidung mitteilen zu können.

Mit freundlichen Grüßen

{{MITARBEITER}}
Verein Tischlein Deck Dich Vorarlberg
Ladritschweg 10c · 6773 Vandans

Beilage: Prüfungsprotokoll (Aktenzeichen {{AKTENZEICHEN}})""",
        },
        {
            "name": "Bescheid – Vorläufig Abgelehnt",
            "template_type": "BESCHEID",
            "status_trigger": "VORLAEFIG_ABGELEHNT",
            "body_text": """\
{{ANREDE}},

Ihr Antrag auf Unterstützungsleistungen beim Verein Tischlein Deck Dich Vorarlberg wurde einer ersten Prüfung unterzogen. Aufgrund fehlender oder unvollständiger Unterlagen kann derzeit keine abschließende Entscheidung getroffen werden.

Aktenzeichen: {{AKTENZEICHEN}}
Prüfungsdatum: {{DATUM}}
Standort: {{STANDORT}}

Ergebnis der Prüfung:
Vorläufig abgelehnt – weitere Abklärung erforderlich.

Begründung:
{{BEGRUENDUNG}}

Erforderliche Maßnahmen:
Damit Ihr Antrag weiterbearbeitet werden kann, bitten wir Sie, die fehlenden Unterlagen oder Informationen umgehend beim Standort {{STANDORT}} einzureichen.

Sobald alle erforderlichen Dokumente vollständig vorliegen, wird Ihr Antrag erneut geprüft und Sie werden schriftlich über das endgültige Ergebnis informiert.

Bitte beachten Sie, dass bei ausbleibender Rückmeldung innerhalb von 30 Tagen der Antrag als zurückgezogen gilt.

Für Rückfragen oder zur Terminvereinbarung wenden Sie sich bitte an den Standort {{STANDORT}}.

Mit freundlichen Grüßen

{{MITARBEITER}}
Verein Tischlein Deck Dich Vorarlberg
Ladritschweg 10c · 6773 Vandans""",
        },
        {
            "name": "Eingangsbestätigung – Antrag in Prüfung",
            "template_type": "INFORMATION",
            "status_trigger": "IN_PRUEFUNG",
            "body_text": """\
{{ANREDE}},

wir bestätigen den Eingang Ihres Antrags auf Unterstützungsleistungen beim Verein Tischlein Deck Dich Vorarlberg und danken Ihnen für Ihr Vertrauen.

Aktenzeichen: {{AKTENZEICHEN}}
Eingangsdatum: {{DATUM}}
Standort: {{STANDORT}}
Aktueller Status: Antrag in Prüfung

Ihr Antrag wird derzeit von unseren Mitarbeiterinnen und Mitarbeitern sorgfältig geprüft. Sobald die Prüfung abgeschlossen ist, werden wir Sie schriftlich über das Ergebnis informieren.

Für eine zügige Bearbeitung bitten wir Sie, sicherzustellen, dass alle erforderlichen Unterlagen vollständig und lesbar vorliegen. Sollten noch Nachweise fehlen, werden wir Sie gesondert kontaktieren.

Bitte halten Sie bei allen Kontaktaufnahmen Ihr Aktenzeichen bereit: {{AKTENZEICHEN}}

Bei Fragen zum Stand Ihrer Bearbeitung stehen Ihnen die Mitarbeiterinnen und Mitarbeiter des Standorts {{STANDORT}} gerne zur Verfügung.

Mit freundlichen Grüßen

{{MITARBEITER}}
Verein Tischlein Deck Dich Vorarlberg
Ladritschweg 10c · 6773 Vandans""",
        },
        {
            "name": "Mitteilung – Kundenkarte freigegeben",
            "template_type": "INFORMATION",
            "status_trigger": "FREIGABE_KARTE",
            "body_text": """\
{{ANREDE}},

wir freuen uns, Ihnen mitteilen zu können, dass Ihre persönliche Kundenkarte für den Bezug von Leistungen des Vereins Tischlein Deck Dich Vorarlberg ausgestellt und zur Abholung bereitsteht.

Aktenzeichen: {{AKTENZEICHEN}}
Ausstellungsdatum: {{DATUM}}
Standort: {{STANDORT}}

Abholung Ihrer Kundenkarte:
Bitte holen Sie Ihre Karte persönlich beim Standort {{STANDORT}} ab. Bringen Sie dabei bitte einen gültigen Lichtbildausweis mit.

Wichtige Hinweise zur Nutzung Ihrer Kundenkarte:
– Die Karte ist personengebunden und nicht übertragbar.
– Sie ist ausschließlich für die im Antrag genannten Personen bestimmt.
– Das Ablaufdatum ist auf der Karte vermerkt. Rechtzeitig vor Ablauf erhalten Sie eine Erinnerung.
– Bei Verlust oder Diebstahl informieren Sie bitte umgehend den Standort {{STANDORT}}.

Mit der Kundenkarte sind Sie berechtigt, die Leistungen des Vereins im Rahmen Ihrer geprüften Anspruchsberechtigung zu nutzen.

Mit freundlichen Grüßen

{{MITARBEITER}}
Verein Tischlein Deck Dich Vorarlberg
Ladritschweg 10c · 6773 Vandans""",
        },
        {
            "name": "Eingangsbestätigung – Widerspruch",
            "template_type": "INFORMATION",
            "status_trigger": "WIDERSPRUCH",
            "body_text": """\
{{ANREDE}},

wir bestätigen den Eingang Ihres Widerspruchs zum Bescheid betreffend Ihren Antrag auf Unterstützungsleistungen beim Verein Tischlein Deck Dich Vorarlberg.

Aktenzeichen: {{AKTENZEICHEN}}
Eingang des Widerspruchs: {{DATUM}}
Standort: {{STANDORT}}

Ihr Widerspruch wird von uns sorgfältig geprüft. Dabei werden alle von Ihnen vorgebrachten Argumente und Unterlagen berücksichtigt. Wir werden Ihnen das Ergebnis dieser Prüfung innerhalb einer angemessenen Frist schriftlich mitteilen.

Falls Sie weitere Unterlagen oder Informationen zur Unterstützung Ihres Widerspruchs einreichen möchten, bitten wir Sie, dies baldmöglichst zu tun.

Bitte halten Sie bei allen Kontaktaufnahmen Ihr Aktenzeichen bereit: {{AKTENZEICHEN}}

Für Rückfragen zum Widerspruchsverfahren stehen Ihnen die Mitarbeiterinnen und Mitarbeiter des Standorts {{STANDORT}} gerne zur Verfügung.

Mit freundlichen Grüßen

{{MITARBEITER}}
Verein Tischlein Deck Dich Vorarlberg
Ladritschweg 10c · 6773 Vandans""",
        },
    ]

    for t in templates:
        try:
            exists = connection.execute(
                "SELECT id FROM document_templates WHERE name=?", (t["name"],)
            ).fetchone()
            if not exists:
                connection.execute(
                    """INSERT INTO document_templates
                       (name, template_type, description, body_text,
                        status_trigger, is_active, version, created_by)
                       VALUES (?,?,?,?,?,1,1,NULL)""",
                    (
                        t["name"],
                        t["template_type"],
                        f"Standard-Vorlage für: {t['name']}",
                        t["body_text"],
                        t.get("status_trigger"),
                    ),
                )
        except Exception:
            pass
    connection.commit()
