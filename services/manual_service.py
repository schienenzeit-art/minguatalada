"""
Benutzerhandbuch-Service

Erzeugt das vollständige deutschsprachige Benutzerhandbuch als PDF
und öffnet es mit dem Standard-PDF-Viewer des Betriebssystems.

Verwendung:
    svc = ManualService()
    svc.open_manual()          # generiert falls nicht vorhanden, dann öffnen
    svc.regenerate()           # immer neu erzeugen
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    HRFlowable, KeepTogether, PageBreak, Paragraph,
    SimpleDocTemplate, Spacer, Table, TableStyle,
)

from app.config import DATA_DIR

# ── Pfad zur PDF-Datei ────────────────────────────────────────────────────────
MANUAL_PATH: Path = Path(DATA_DIR) / "Benutzerhandbuch.pdf"

# ── Farbpalette ───────────────────────────────────────────────────────────────
_C_DARK_BLUE   = colors.HexColor("#1a3a5c")
_C_MID_BLUE    = colors.HexColor("#2c5f8a")
_C_LIGHT_BLUE  = colors.HexColor("#dceaf7")
_C_ACCENT      = colors.HexColor("#e67e22")
_C_LIGHT_GRAY  = colors.HexColor("#f5f5f5")
_C_BORDER      = colors.HexColor("#cccccc")
_C_WHITE       = colors.white
_C_BLACK       = colors.black

_PAGE_W, _PAGE_H = A4
_MARGIN = 2.5 * cm

# ── Kapitel-Inhalt (strukturiert, wartbar) ────────────────────────────────────
_CHAPTERS: list[dict] = [
    {
        "num": 1, "title": "Einführung",
        "sections": [
            ("1.1 Zweck der Software",
             "Min Guata Lada ist das Verwaltungssystem des Vereins Tischlein Deck Dich Vorarlberg. "
             "Es dient der digitalen Verwaltung von Essensansprüchen, Bezugskarten, Personen und "
             "Fällen an allen Vereinsstandorten in Vorarlberg.\n\n"
             "Die Software ermöglicht eine lückenlose, datenschutzkonforme und effiziente "
             "Bearbeitung von Anträgen auf Unterstützungsleistungen sowie die Verwaltung der "
             "damit verbundenen Bezugskarten."),
            ("1.2 Zielgruppe",
             "Die Anwendung richtet sich an folgende Personengruppen:\n\n"
             "• Mitarbeiterinnen und Mitarbeiter: Erfassen und bearbeiten Anträge sowie Karten.\n"
             "• Standortleitungen: Verwalten ihren Standort vollständig, inkl. Freigaben.\n"
             "• Administratoren: Konfigurieren das System, verwalten Benutzer und Stammdaten.\n"
             "• Supervisoren: Überwachen standortübergreifend, können Freigaben erteilen.\n"
             "• Freiwillige: Werden im System hinterlegt (Kartenübersicht), haben aber keinen Systemzugang."),
            ("1.3 Funktionsübersicht",
             "Die wichtigsten Funktionen im Überblick:\n\n"
             "• Anspruchsprüfung: Erfassung und Bewertung von Antragsstellenden.\n"
             "• Bezugskartenverwaltung: Ausstellung, Verlängerung und Sperrung von Karten.\n"
             "• Personendossier: Vollständige Akte je Person (Stammdaten, Fälle, Dokumente).\n"
             "• Benutzerverwaltung: Anlage und Verwaltung aller Systembenutzer.\n"
             "• Terminverwaltung: Planung und Nachverfolgung von Gesprächsterminen.\n"
             "• Aufgabenverwaltung: Zuweisbare Aufgaben mit Status und Priorität.\n"
             "• Dokumentenverwaltung: Hochladen, Kategorisieren und Archivieren von Unterlagen.\n"
             "• Berichte und Auswertungen: Jahresauswertungen, Zeitraumberichte, Warteliste.\n"
             "• Audit-Protokoll: Lückenloser Nachweis aller systemrelevanten Aktionen.\n"
             "• Software-Update-Center: Kontrolliertes Einspielen von Softwareupdates.\n"
             "• Freigabe-Workflow: Vier-Augen-Prinzip für kritische Statusänderungen.\n"
             "• Daten-Import: Massenimport von Personendaten via CSV oder Excel."),
        ],
    },
    {
        "num": 2, "title": "Erste Anmeldung",
        "sections": [
            ("2.1 Anmeldevorgang",
             "Starten Sie die Anwendung über das Desktop-Symbol oder das Startmenü. "
             "Es erscheint das Anmeldefenster.\n\n"
             "Geben Sie Ihren Benutzernamen und Ihr Passwort ein und klicken Sie auf 'Anmelden'. "
             "Benutzername und Passwort werden vom Systemadministrator bereitgestellt.\n\n"
             "Hinweis: Nach fünf aufeinanderfolgenden fehlgeschlagenen Anmeldeversuchen wird "
             "der Account automatisch für 15 Minuten gesperrt."),
            ("2.2 Erstanmeldung und Passwortänderung",
             "Bei der ersten Anmeldung mit einem neuen Konto wird Ihnen ein Initialpasswort "
             "mitgeteilt. Das System fordert Sie automatisch auf, dieses Passwort zu ändern.\n\n"
             "Anforderungen an das neue Passwort:\n"
             "• Mindestens 10 Zeichen\n"
             "• Bitte ein sicheres, einzigartiges Passwort wählen\n"
             "• Das Passwort wird verschlüsselt gespeichert\n\n"
             "Bewahren Sie Ihr Passwort sicher auf und teilen Sie es nicht mit anderen Personen."),
            ("2.3 Benutzerrollen und Berechtigungen",
             "Das System unterscheidet fünf Rollen:\n\n"
             "Mitarbeiter: Grundlegende Funktionen – Anträge erfassen, Karten bearbeiten, "
             "Personen anlegen, Aufgaben verwalten. Kein Zugriff auf Systemeinstellungen.\n\n"
             "Standortleitung: Alle Mitarbeiter-Funktionen plus Freigaben, Standortverwaltung, "
             "Benutzerverwaltung am eigenen Standort.\n\n"
             "Supervisor: Standortübergreifende Rechte, Freigaben, Auswertungen.\n\n"
             "Administrator: Voller Systemzugriff – Einstellungen, Benutzerverwaltung, "
             "Software-Updates, Stammdaten.\n\n"
             "Freiwillige: Keine Systemanmeldung möglich. Nur als Datensatz für die "
             "Kartenverwaltung und Übersicht hinterlegt."),
            ("2.4 Abmeldung",
             "Klicken Sie in der oberen rechten Ecke auf Ihren Benutzernamen oder das "
             "Benutzer-Symbol und wählen Sie 'Abmelden'. Die Anwendung schließt sich. "
             "Es wird empfohlen, sich am Ende jeder Sitzung abzumelden, insbesondere auf "
             "gemeinsam genutzten Arbeitsgeräten."),
        ],
    },
    {
        "num": 3, "title": "Dashboard",
        "sections": [
            ("3.1 Überblick",
             "Nach der Anmeldung öffnet sich das Dashboard automatisch. "
             "Es bietet einen sofortigen Überblick über die wichtigsten Kennzahlen und "
             "offenen Aufgaben Ihres Standorts."),
            ("3.2 Kennzahl-Kacheln",
             "Im oberen Bereich des Dashboards werden folgende Kennzahlen als Kacheln angezeigt:\n\n"
             "• Offene Fälle: Alle Anträge im Status 'In Prüfung'.\n"
             "• Anspruchsberechtigte: Personen mit aktivem, positiv beschiedenem Antrag.\n"
             "• Aktive Karten: Ausgegebene Bezugskarten im Status 'Aktiv'.\n"
             "• Ablaufende Karten: Karten, die in den nächsten 30 Tagen ablaufen.\n"
             "• Offene Aufgaben: Ihnen zugewiesene, noch nicht erledigte Aufgaben."),
            ("3.3 Schnellzugriff",
             "Das Dashboard enthält Schnellzugriffs-Schaltflächen zu den wichtigsten Bereichen:\n\n"
             "• Neuen Antrag erstellen\n"
             "• Karte ausstellen\n"
             "• Person suchen\n"
             "• Aufgaben anzeigen\n\n"
             "Diese Schaltflächen sind je nach Rolle unterschiedlich eingeblendet."),
        ],
    },
    {
        "num": 4, "title": "Benutzerverwaltung",
        "sections": [
            ("4.1 Zugriffsberechtigung",
             "Die Benutzerverwaltung ist nur für Benutzer mit den Rollen Admin, Supervisor "
             "und Standortleitung zugänglich. Sie erreichen diese über:\n"
             "Administration → Benutzerverwaltung"),
            ("4.2 Benutzer anlegen",
             "Klicken Sie auf 'Benutzer hinzufügen'. Füllen Sie das Formular aus:\n\n"
             "• Vollständiger Name: Vor- und Nachname der Person.\n"
             "• Benutzername: Eindeutiger Anmeldename (keine Leerzeichen).\n"
             "• Passwort: Initialpasswort (mind. 10 Zeichen). Entfällt bei Freiwilligen.\n"
             "• Rolle: Bestimmt die Zugriffsrechte (siehe Kapitel 2.3).\n"
             "• Standort: Zuweisung zu einem Vereinsstandort.\n"
             "• Aktiv: Aktive Benutzer können sich anmelden.\n\n"
             "Für Freiwillige wird das Passwortfeld ausgeblendet. Freiwillige erhalten "
             "keinen Systemzugang. Der Datensatz dient der Kartenverwaltung."),
            ("4.3 Benutzer bearbeiten",
             "Doppelklicken Sie auf einen Benutzer in der Tabelle, um das Bearbeitungsformular "
             "zu öffnen. Sie können alle Felder außer dem Benutzernamen der ersten Anmeldung "
             "ändern. Um ein Passwort zurückzusetzen, füllen Sie das Passwort-Feld neu aus."),
            ("4.4 Benutzer deaktivieren",
             "Statt Benutzer zu löschen, sollten Sie diese deaktivieren: "
             "Öffnen Sie den Benutzer und entfernen Sie das Häkchen bei 'Aktiv'. "
             "Deaktivierte Benutzer können sich nicht mehr anmelden, ihre Daten bleiben "
             "erhalten. Der Systemadministrator (admin) kann nicht deaktiviert werden."),
            ("4.5 Sperren und Entsperren",
             "Über die Schaltflächen 'Sperren bis…' und 'Entsperren' können Sie Konten "
             "zeitlich sperren oder manuell entsperren. "
             "Diese Funktion ist für Freiwillige deaktiviert, da diese keinen Systemzugang haben."),
        ],
    },
    {
        "num": 5, "title": "Fallverwaltung und Antragsbearbeitung",
        "sections": [
            ("5.1 Neuen Fall/Antrag erstellen",
             "Navigieren Sie zu Anspruchsprüfung → Anträge und klicken Sie auf 'Neuen Fall anlegen'. "
             "Füllen Sie folgende Pflichtfelder aus:\n\n"
             "• Person: Suchen oder anlegen der antragstellenden Person.\n"
             "• Standort: Zuständiger Vereinsstandort.\n"
             "• Kategorie: Art der Unterstützungsleistung.\n"
             "• Beschreibung: Kurze Fallbeschreibung.\n"
             "• Zeitraum: Gültigkeitszeitraum des Antrags.\n\n"
             "Haushaltsmitglieder werden im nächsten Schritt im Detaildialog erfasst."),
            ("5.2 Haushaltsmitglieder erfassen",
             "Im Falldetail (Doppelklick auf einen Fall) können Sie unter dem Tab "
             "'Haushalt' alle Haushaltsmitglieder erfassen:\n\n"
             "• Erwachsene: beeinflussen die Berechnung der Anspruchsgrenze.\n"
             "• Kinder: Zuschlag zur Anspruchsgrenze je Kind.\n"
             "• Behinderungsgrad: Kann zusätzliche Ansprüche begründen (Härtefall)."),
            ("5.3 Einkommen und Ausgaben",
             "Unter den Tabs 'Einkommen' und 'Ausgaben' erfassen Sie die wirtschaftliche "
             "Situation des Haushalts. Das System berechnet daraus automatisch:\n\n"
             "• Gesamteinkommen und Gesamtausgaben\n"
             "• Verfügbares Einkommen\n"
             "• Anspruchsgrenze (abhängig von Haushaltsgröße)\n"
             "• Härtefallgrenze (Grenze × Härtefallmultiplikator)\n\n"
             "Die Grenzwerte können in Einstellungen → Prüfungslimits konfiguriert werden."),
            ("5.4 Prüfungsergebnis und Statusänderung",
             "Nach vollständiger Erfassung können Sie die Prüfung durchführen. "
             "Folgende Status sind möglich:\n\n"
             "• In Prüfung: Antrag eingegangen, Prüfung läuft.\n"
             "• Anspruchsberechtigt: Antrag positiv beschieden.\n"
             "• Härtefall: Antrag positiv beschieden unter Härtefallregelung.\n"
             "• Abgelehnt: Antrag abgelehnt.\n"
             "• Vorläufig Abgelehnt: Unterlagen fehlen, Rückfrage erforderlich.\n"
             "• Freigabe Karte: Anspruch bestätigt, Karte kann ausgestellt werden.\n"
             "• Widerspruch: Widerspruch gegen Ablehnung eingegangen.\n"
             "• Archiviert: Fall abgeschlossen und archiviert.\n\n"
             "Kritische Statusänderungen (Härtefall, Vorläufig Abgelehnt) benötigen "
             "eine Vier-Augen-Freigabe durch Standortleitung oder Supervisor."),
            ("5.5 Bescheide erstellen",
             "Nach der Prüfung können Sie automatisch einen Bescheid als PDF generieren. "
             "Klicken Sie im Falldetail auf 'Bescheid erstellen'. "
             "Das System wählt automatisch die passende Vorlage zum aktuellen Status. "
             "Der Bescheid kann ausgedruckt oder per E-Mail versendet werden."),
            ("5.6 Fallhistorie",
             "Die vollständige Statushistorie eines Falls ist im Tab 'Historie' des Falldetails "
             "einsehbar. Alle Statusänderungen werden mit Datum, Uhrzeit und Benutzer protokolliert."),
        ],
    },
    {
        "num": 6, "title": "Bezugskartenverwaltung",
        "sections": [
            ("6.1 Bezugskarte ausstellen",
             "Bezugskarten werden ausgestellt, sobald ein Antrag den Status 'Freigabe Karte' "
             "erhalten hat. Navigieren Sie zu Anspruchsprüfung → Karten und klicken Sie auf "
             "'Karte ausstellen'.\n\n"
             "Pflichtfelder:\n"
             "• Antrag: Verknüpfung mit dem zugehörigen Fall.\n"
             "• Person: Karteninhaber/in.\n"
             "• Ausstellungsdatum und Ablaufdatum.\n"
             "• Standort der Ausstellung.\n\n"
             "Die Kartennummer wird automatisch vergeben (z. B. K-2026-000001)."),
            ("6.2 Karte sperren und entsperren",
             "Karten können im Kartendetail gesperrt werden (z. B. bei Verlust oder Missbrauch). "
             "Tragen Sie einen Sperrgrund ein und bestätigen Sie die Sperrung. "
             "Gesperrte Karten können reaktiviert werden."),
            ("6.3 Kartenübersicht",
             "Die Kartenübersicht zeigt alle ausgestellten Karten mit Status, Ablaufdatum "
             "und zugehöriger Person. Sie können nach Standort, Status und Ablaufdatum filtern. "
             "Ablaufende Karten (innerhalb 30 Tage) werden automatisch hervorgehoben."),
            ("6.4 Kartendruck",
             "Karten können als PDF erzeugt und ausgedruckt werden. "
             "Klicken Sie in der Kartenübersicht auf 'Karte drucken' (Druckersymbol). "
             "Das PDF enthält Kartennummer, Name, Ausstellungsdatum, Ablaufdatum und Standort."),
        ],
    },
    {
        "num": 7, "title": "Personendossier und Dokumentenverwaltung",
        "sections": [
            ("7.1 Personendossier aufrufen",
             "Das Personendossier ist über Anspruchsprüfung → Personendossier erreichbar. "
             "Es zeigt die vollständige Akte einer Person in fünf Tabs:\n\n"
             "• Stammdaten: Name, Adresse, Geburtsdatum, Kategorie.\n"
             "• Fälle: Alle Anträge dieser Person.\n"
             "• Dokumente: Hochgeladene Unterlagen.\n"
             "• Aktivitäten: Protokoll aller Aktionen zur Person.\n"
             "• Notizen: Interne Anmerkungen (nicht in Bescheiden sichtbar)."),
            ("7.2 Dokumente hochladen",
             "Wechseln Sie im Personendossier auf den Tab 'Dokumente' und klicken Sie auf "
             "'Dokument hochladen'. Wählen Sie die Datei aus und geben Sie folgende Informationen an:\n\n"
             "• Titel: Beschreibender Name des Dokuments.\n"
             "• Dokumenttyp: z. B. Ausweis, Einkommensnachweis, Haushaltsnachweis, Bescheid.\n"
             "• Beschreibung: Optionale Zusatzinformationen.\n"
             "• Ablaufdatum: Falls das Dokument befristet gültig ist.\n\n"
             "Unterstützte Formate: PDF, JPG, PNG, DOCX und weitere gängige Formate."),
            ("7.3 Dokumente verwalten",
             "Dokumente können heruntergeladen, angezeigt und archiviert werden. "
             "Eine physische Löschung ist nicht vorgesehen – Dokumente werden stattdessen "
             "als archiviert markiert und sind in der Hauptliste nicht mehr sichtbar."),
            ("7.4 Personen-Notizen",
             "Im Tab 'Notizen' können Sie interne Anmerkungen zur Person eintragen. "
             "Notizen sind nur für berechtigte Benutzer sichtbar und erscheinen nicht in "
             "offiziellen Dokumenten oder Bescheiden."),
        ],
    },
    {
        "num": 8, "title": "Suche und Filter",
        "sections": [
            ("8.1 Globale Suche",
             "Die Suchfunktion ist jederzeit über das Lupensymbol in der oberen Werkzeugleiste "
             "erreichbar. Sie können nach folgenden Kriterien suchen:\n\n"
             "• Personen: Name, Benutzername, E-Mail-Adresse.\n"
             "• Fälle: Fallnummer, Beschreibung.\n"
             "• Karten: Kartennummer.\n\n"
             "Die Suchergebnisse öffnen sich in einem Dialogfenster. "
             "Per Doppelklick gelangen Sie direkt zum jeweiligen Datensatz."),
            ("8.2 Listen-Filter",
             "In den Listenansichten (Anträge, Karten, Personen) können Sie die Anzeige "
             "über die Filter-Leiste einschränken:\n\n"
             "• Statusfilter: Nur Datensätze eines bestimmten Status anzeigen.\n"
             "• Standortfilter: Einschränkung auf einen Standort (für übergeordnete Rollen).\n"
             "• Datumsfilter: Zeitraum-Einschränkung nach Erstelldatum.\n"
             "• Freitextsuche: Schnellsuche innerhalb der angezeigten Liste.\n\n"
             "Filter können als Voreinstellung gespeichert werden (Filtervorlagen)."),
        ],
    },
    {
        "num": 9, "title": "Berichte und Auswertungen",
        "sections": [
            ("9.1 Aufrufen der Berichte",
             "Berichte erreichen Sie über den Menüpunkt 'Berichte' in der Navigation. "
             "Die Berichtsseite ist in vier Tabs gegliedert."),
            ("9.2 Übersicht",
             "Der Tab 'Übersicht' zeigt Kennzahlen für einen wählbaren Zeitraum:\n\n"
             "• KPI-Kacheln: Anträge gesamt, aktive Karten, Personen, offene Prüfungen.\n"
             "• Anträge nach Status: Aufschlüsselung aller Antragsstatus mit Prozentwerten.\n"
             "• Karten nach Status: Aufteilung in aktiv, abgelaufen, gesperrt.\n\n"
             "Wählen Sie 'Gesamter Zeitraum' für ungefilterte Daten oder definieren Sie "
             "einen Von-bis-Zeitraum."),
            ("9.3 Jahresauswertung",
             "Der Tab 'Jahresauswertung' erstellt eine 12-Monats-Tabelle mit folgenden Spalten:\n\n"
             "• Monat\n"
             "• Neue Anträge\n"
             "• Durchgeführte Prüfungen\n"
             "• Anspruchsberechtigte (grün)\n"
             "• Härtefälle (orange)\n"
             "• Abgelehnte Anträge (rot)\n"
             "• Neue Bezugskarten\n"
             "• Neue Personen\n\n"
             "Am Ende der Tabelle werden Summen angezeigt. "
             "Aktivieren Sie 'Vorjahresvergleich', um die Zahlen des Vorjahres "
             "und die prozentuale Veränderung zu sehen."),
            ("9.4 Zeitraum-Auswertung",
             "Im Tab 'Zeitraum' können Sie einen beliebigen Von-bis-Zeitraum auswählen. "
             "Die Ergebnisse werden monatsweise aufgeschlüsselt dargestellt. "
             "Eine Vergleichstabelle zeigt die Abweichung zum Vorjahreszeitraum."),
            ("9.5 Warteliste",
             "Der Tab 'Warteliste' listet alle offenen Fälle im Status 'In Prüfung', "
             "sortiert nach der längsten Wartezeit. "
             "Wartezeiten über 30 Tagen werden rot hervorgehoben."),
            ("9.6 Standort-Filter",
             "In allen Report-Tabs können Administratoren und Supervisoren die Auswertung "
             "auf einen bestimmten Standort einschränken. Mitarbeiter und Standortleitungen "
             "sehen automatisch nur ihren eigenen Standort."),
        ],
    },
    {
        "num": 10, "title": "Einstellungen",
        "sections": [
            ("10.1 Einstellungen öffnen",
             "Die Einstellungsseite erreichen Sie über Administration → Einstellungen. "
             "Sie ist in vier Themenbereiche gegliedert, die jeweils über eine Kachel "
             "aufgerufen werden."),
            ("10.2 Prüfungslimits",
             "Hier konfigurieren Sie die Grenzwerte für die Anspruchsprüfung:\n\n"
             "• Basisgrenze (€): Anspruchsgrenze für eine einzelne erwachsene Person.\n"
             "• Zuschlag Erwachsene (€): Zusätzlicher Betrag je weiterer erwachsener Person.\n"
             "• Zuschlag Kinder (€): Zusätzlicher Betrag je Kind im Haushalt.\n"
             "• Härtefall-Multiplikator: Die Grenze wird mit diesem Faktor multipliziert "
             "(Standard: 1,10 = 10 % Aufschlag).\n\n"
             "Eine Beispielberechnung wird live angezeigt. Nur Administratoren können "
             "diese Werte ändern."),
            ("10.3 SMTP & E-Mail",
             "Konfigurieren Sie den Mailserver für den automatischen E-Mail-Versand "
             "(Bescheide, Benachrichtigungen):\n\n"
             "• SMTP-Host und Port (Standard: 587 für STARTTLS)\n"
             "• Benutzername und Passwort\n"
             "• Absender-E-Mail und Absender-Name\n"
             "• SMTP-Aktivierung\n\n"
             "Testen Sie die Konfiguration mit der Funktion 'Testmail senden'."),
            ("10.4 Software-Update-Center",
             "Das Update-Center ermöglicht ein sicheres Einspielen von Softwareupdates:\n\n"
             "• Paket auswählen (.mugala-Datei)\n"
             "• Paket prüfen und Changelog einsehen\n"
             "• Update starten (mit automatischem Backup)\n\n"
             "Vor jedem Update wird automatisch ein Datenbank-Backup erstellt. "
             "Details zur Update-Prozedur finden Sie in Kapitel 12."),
            ("10.5 Systemparameter",
             "Technische Systemkonfiguration:\n\n"
             "• Fallnummernpräfix: Bestimmt das Präfix neuer Fallnummern (Standard: 'AS').\n"
             "• Update-Server URL: Adresse des Online-Update-Manifests.\n"
             "• Systeminfo: Anzeige der aktuellen Version und Datenbanktyp."),
            ("10.6 Benutzerhandbuch",
             "Über die Kachel 'Benutzerhandbuch' können Sie dieses Dokument jederzeit "
             "erneut öffnen oder neu generieren. "
             "Das Handbuch wird als PDF im lokalen Datenspeicher abgelegt und mit dem "
             "Standard-PDF-Viewer des Betriebssystems geöffnet."),
        ],
    },
    {
        "num": 11, "title": "Fehlerbehebung",
        "sections": [
            ("11.1 Anmeldung schlägt fehl",
             "Mögliche Ursachen und Lösungen:\n\n"
             "Falsches Passwort: Prüfen Sie Groß-/Kleinschreibung. "
             "Nach 5 Fehlversuchen wird der Account 15 Minuten gesperrt. "
             "Kontaktieren Sie den Administrator für ein Passwort-Reset.\n\n"
             "Account deaktiviert: Wenden Sie sich an den Administrator.\n\n"
             "Freiwillige können sich nicht anmelden: Das ist korrekt – "
             "Freiwillige haben keinen Systemzugang."),
            ("11.2 Daten werden nicht gespeichert",
             "Prüfen Sie:\n\n"
             "• Sind alle Pflichtfelder (mit * markiert) ausgefüllt?\n"
             "• Ist der Benutzername bei neuen Benutzern eindeutig?\n"
             "• Ist die Datenbank erreichbar? (Fehlermeldung unten im Fenster)\n\n"
             "Sollte das Problem anhalten, starten Sie die Anwendung neu."),
            ("11.3 Anwendung startet nicht",
             "Prüfen Sie:\n\n"
             "• Windows-Ereignisprotokoll auf Fehlermeldungen.\n"
             "• Ist genügend Speicherplatz vorhanden? (min. 500 MB empfohlen)\n"
             "• Ist die Datenbankdatei vorhanden? "
             "  (Pfad: %LOCALAPPDATA%\\Anspruchssystem\\system.db)\n\n"
             "Kontaktieren Sie im Zweifel den IT-Support."),
            ("11.4 PDF-Export schlägt fehl",
             "Falls beim Erstellen von Bescheiden oder beim Öffnen des Benutzerhandbuchs "
             "ein Fehler auftritt:\n\n"
             "• Ist genügend Speicherplatz vorhanden?\n"
             "• Ist ein PDF-Viewer (z. B. Adobe Acrobat, Edge) installiert?\n"
             "• Prüfen Sie den Ausgabepfad: %LOCALAPPDATA%\\Anspruchssystem\\pdfs\\"),
        ],
    },
    {
        "num": 12, "title": "Datenschutz und Sicherheit",
        "sections": [
            ("12.1 Datenhaltung",
             "Alle Daten werden lokal auf dem Serverrechner in einer SQLite-Datenbank gespeichert. "
             "Datenbankpfad: %LOCALAPPDATA%\\Anspruchssystem\\system.db\n\n"
             "Hochgeladene Dokumente werden im Verzeichnis "
             "%LOCALAPPDATA%\\Anspruchssystem\\documents\\ gespeichert. "
             "Es findet keine Übertragung an externe Server statt, sofern kein "
             "Update-Server oder SMTP-Server konfiguriert ist."),
            ("12.2 Benutzerrechte und Rollensystem",
             "Das Rollensystem stellt sicher, dass Benutzer nur auf die für ihre "
             "Funktion notwendigen Daten zugreifen können (Prinzip der minimalen Rechtevergabe).\n\n"
             "Alle sensiblen Aktionen werden im Audit-Protokoll festgehalten "
             "(Administration → Audit-Protokoll). "
             "Das Audit-Protokoll kann nicht verändert werden."),
            ("12.3 Passwortsicherheit",
             "Passwörter werden mit bcrypt (Salted Hashing) verschlüsselt gespeichert. "
             "Sie können nicht entschlüsselt werden. "
             "Bei Verlust muss ein Administrator ein neues Passwort vergeben.\n\n"
             "SMTP-Passwörter werden ebenfalls verschlüsselt in der Datenbank abgelegt."),
            ("12.4 Datensicherung",
             "Empfohlene Sicherungsmaßnahmen:\n\n"
             "• Regelmäßige Sicherung der Datenbankdatei "
             "(%LOCALAPPDATA%\\Anspruchssystem\\system.db)\n"
             "• Vor jedem Software-Update erstellt das System automatisch ein Backup "
             "unter %LOCALAPPDATA%\\Anspruchssystem\\backups\\\n"
             "• Manuelle Backups können im Software-Update-Center erstellt werden.\n"
             "• Es werden die letzten 10 Backups aufbewahrt.\n\n"
             "Bewahren Sie Sicherungskopien an einem sicheren, externen Ort auf."),
            ("12.5 Archiv- und Löschregeln",
             "Unter Administration → Archiv-Regeln können Sie konfigurieren, "
             "wann Datensätze automatisch archiviert werden:\n\n"
             "• Anträge: Standard 10 Jahre\n"
             "• Personen: Standard 10 Jahre\n"
             "• Dokumente: Standard 5 Jahre\n"
             "• Audit-Protokolle: Standard 7 Jahre (dann Löschung)\n\n"
             "Diese Regeln sind im Standardzustand deaktiviert und müssen "
             "bewusst aktiviert werden."),
        ],
    },
    {
        "num": 13, "title": "Häufig gestellte Fragen (FAQ)",
        "sections": [
            ("F: Wie lege ich einen neuen Fall an?",
             "A: Anspruchsprüfung → Anträge → 'Neuen Fall anlegen'. "
             "Füllen Sie Pflichtfelder aus (Person, Standort, Beschreibung) und bestätigen Sie. "
             "Details erfassen Sie anschließend im Falldialog."),
            ("F: Wie ändere ich den Status eines Antrags?",
             "A: Öffnen Sie den Antrag per Doppelklick. Im Detaildialog finden Sie "
             "die Schaltfläche 'Status ändern' mit den für Ihre Rolle erlaubten Folgestatus. "
             "Kritische Statusänderungen benötigen eine Freigabe."),
            ("F: Wie erstelle ich einen Bericht für das Vorjahr?",
             "A: Berichte → Tab 'Jahresauswertung' → Jahr auswählen → "
             "'Jahresauswertung starten'. Optional 'Vorjahresvergleich' aktivieren."),
            ("F: Kann ich mehrere Personen auf einmal importieren?",
             "A: Ja. Administration → Daten-Import. "
             "Laden Sie eine CSV- oder Excel-Datei hoch. "
             "Eine Vorschau zeigt die erkannten Felder vor dem endgültigen Import."),
            ("F: Wie drucke ich eine Bezugskarte?",
             "A: Anspruchsprüfung → Karten → Karte auswählen → Druckersymbol. "
             "Das PDF wird erzeugt und automatisch geöffnet."),
            ("F: Was passiert, wenn ich ein Update einspiele?",
             "A: Das System erstellt zunächst ein automatisches Datenbank-Backup. "
             "Dann werden die mitgelieferten Migrationen ausgeführt. "
             "Abschließend wird ggf. der neue Installer gestartet. "
             "Ihre Daten bleiben vollständig erhalten."),
            ("F: Wie kann ich ein Passwort zurücksetzen?",
             "A: Ein Administrator kann in der Benutzerverwaltung das Passwortfeld "
             "mit einem neuen Wert befüllen und speichern. "
             "Das neue Passwort sollte dem Benutzer persönlich mitgeteilt werden."),
            ("F: Wer hat welche Daten verändert?",
             "A: Das Audit-Protokoll (Administration → Audit-Protokoll) protokolliert "
             "alle systemrelevanten Aktionen mit Zeitstempel und Benutzerzuordnung."),
            ("F: Wie kann ich Freiwillige verwalten?",
             "A: Freiwillige werden in der Benutzerverwaltung mit der Rolle 'Freiwillige' "
             "angelegt. Sie benötigen kein Passwort und können sich nicht anmelden. "
             "Sie dienen der Übersicht und Kartenzuordnung."),
            ("F: Wie lange werden Daten aufbewahrt?",
             "A: Die Aufbewahrungsfristen können unter Administration → Archiv-Regeln "
             "konfiguriert werden. Standardmäßig werden Anträge 10 Jahre aufbewahrt."),
        ],
    },
]


class ManualService:
    """Erzeugt das Benutzerhandbuch als PDF und öffnet es."""

    def __init__(self):
        self._path = MANUAL_PATH

    def get_path(self) -> Path:
        return self._path

    def exists(self) -> bool:
        return self._path.exists()

    def open_manual(self) -> None:
        """Erzeugt die PDF falls nicht vorhanden, öffnet sie dann."""
        if not self.exists():
            self.regenerate()
        self._open_pdf()

    def regenerate(self) -> None:
        """Erzeugt die PDF neu (überschreibt vorhandene Datei)."""
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._generate()

    # ── PDF-Generierung ───────────────────────────────────────────────────────

    def _generate(self) -> None:
        styles = getSampleStyleSheet()

        style_h1 = ParagraphStyle(
            "ManualH1",
            parent=styles["Heading1"],
            fontSize=20, leading=26, spaceBefore=0, spaceAfter=10,
            textColor=_C_DARK_BLUE, fontName="Helvetica-Bold",
            borderPad=(0, 0, 4, 0),
        )
        style_h2 = ParagraphStyle(
            "ManualH2",
            parent=styles["Heading2"],
            fontSize=13, leading=18, spaceBefore=14, spaceAfter=6,
            textColor=_C_MID_BLUE, fontName="Helvetica-Bold",
        )
        style_body = ParagraphStyle(
            "ManualBody",
            parent=styles["Normal"],
            fontSize=10, leading=15, spaceAfter=8,
            fontName="Helvetica",
        )
        style_small = ParagraphStyle(
            "ManualSmall",
            parent=styles["Normal"],
            fontSize=8, leading=12, textColor=colors.gray,
        )
        style_toc_title = ParagraphStyle(
            "TocTitle",
            parent=styles["Normal"],
            fontSize=10, leading=16, fontName="Helvetica",
        )
        style_toc_entry = ParagraphStyle(
            "TocEntry",
            parent=styles["Normal"],
            fontSize=10, leading=16, fontName="Helvetica",
            leftIndent=0,
        )

        now = datetime.now()

        def _header_footer(canvas, doc):
            canvas.saveState()
            w, h = A4
            if doc.page > 1:
                canvas.setFont("Helvetica", 8)
                canvas.setFillColor(colors.gray)
                canvas.drawString(_MARGIN, h - 1.5 * cm,
                                   "Min Guata Lada — Benutzerhandbuch")
                canvas.drawRightString(w - _MARGIN, h - 1.5 * cm,
                                        f"Tischlein Deck Dich Vorarlberg")
                canvas.setStrokeColor(_C_BORDER)
                canvas.line(_MARGIN, h - 1.7 * cm, w - _MARGIN, h - 1.7 * cm)
                canvas.setFont("Helvetica", 8)
                canvas.drawCentredString(w / 2, 1.0 * cm,
                                          f"Seite {doc.page}")
                canvas.line(_MARGIN, 1.5 * cm, w - _MARGIN, 1.5 * cm)
            canvas.restoreState()

        def _title_page(canvas, doc):
            canvas.saveState()
            w, h = A4
            # Hintergrund-Balken
            canvas.setFillColor(_C_DARK_BLUE)
            canvas.rect(0, h - 8 * cm, w, 8 * cm, fill=1, stroke=0)
            # Titel
            canvas.setFillColor(_C_WHITE)
            canvas.setFont("Helvetica-Bold", 32)
            canvas.drawCentredString(w / 2, h - 3.5 * cm, "Min Guata Lada")
            canvas.setFont("Helvetica", 14)
            canvas.drawCentredString(w / 2, h - 4.5 * cm,
                                      "Tischlein Deck Dich Vorarlberg")
            canvas.setFont("Helvetica-Bold", 18)
            canvas.setFillColor(_C_ACCENT)
            canvas.drawCentredString(w / 2, h - 6.0 * cm, "Benutzerhandbuch")
            # Inhalt unten
            canvas.setFillColor(_C_BLACK)
            canvas.setFont("Helvetica", 11)
            canvas.drawCentredString(w / 2, h - 9.5 * cm, "Anspruchsverwaltung")
            canvas.setFont("Helvetica", 10)
            canvas.setFillColor(colors.gray)
            canvas.drawCentredString(w / 2, 4.0 * cm,
                                      f"Generiert am {now.strftime('%d.%m.%Y um %H:%M Uhr')}")
            canvas.drawCentredString(w / 2, 3.2 * cm, "Version 1.0")
            canvas.drawCentredString(w / 2, 2.4 * cm,
                                      "Verein Tischlein Deck Dich Vorarlberg")
            canvas.drawCentredString(w / 2, 1.8 * cm,
                                      "Ladritschweg 10c · 6773 Vandans")
            canvas.restoreState()

        doc = SimpleDocTemplate(
            str(self._path),
            pagesize=A4,
            leftMargin=_MARGIN,
            rightMargin=_MARGIN,
            topMargin=2.8 * cm,
            bottomMargin=2.5 * cm,
        )

        story = []

        # ── Titelblatt (leere Story-Seite, Inhalt via Canvas-Callback) ────────
        story.append(Spacer(1, 20 * cm))
        story.append(PageBreak())

        # ── Inhaltsverzeichnis ────────────────────────────────────────────────
        story.append(Paragraph("Inhaltsverzeichnis", style_h1))
        story.append(HRFlowable(width="100%", thickness=2, color=_C_DARK_BLUE,
                                 spaceAfter=14))

        toc_data = [[
            Paragraph("Kapitel", style_toc_entry),
            Paragraph("Seite", style_toc_entry),
        ]]
        approx_pages = {
            1: 3, 2: 4, 3: 5, 4: 6, 5: 8, 6: 10, 7: 11, 8: 12,
            9: 13, 10: 15, 11: 16, 12: 17, 13: 19,
        }
        for chap in _CHAPTERS:
            label = f"{chap['num']}.  {chap['title']}"
            toc_data.append([
                Paragraph(label, style_toc_entry),
                Paragraph(str(approx_pages.get(chap["num"], "–")), style_toc_entry),
            ])

        toc_table = Table(toc_data, colWidths=[14 * cm, 2 * cm])
        toc_table.setStyle(TableStyle([
            ("FONTNAME",     (0, 0), (-1, 0),  "Helvetica-Bold"),
            ("FONTSIZE",     (0, 0), (-1, -1), 10),
            ("BOTTOMPADDING",(0, 0), (-1, -1), 6),
            ("TOPPADDING",   (0, 0), (-1, -1), 4),
            ("LINEBELOW",    (0, 0), (-1, 0),  1, _C_BORDER),
            ("LINEBELOW",    (0, 1), (-1, -1), 0.3, _C_BORDER),
            ("ALIGN",        (1, 0), (1, -1),  "RIGHT"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [_C_WHITE, _C_LIGHT_GRAY]),
        ]))
        story.append(toc_table)
        story.append(PageBreak())

        # ── Kapitel ───────────────────────────────────────────────────────────
        for chap in _CHAPTERS:
            chap_header = f"Kapitel {chap['num']}: {chap['title']}"

            # Kapitelüberschrift (blauer Balken-Effekt via Tabelle)
            title_block = Table(
                [[Paragraph(chap_header, style_h1)]],
                colWidths=[_PAGE_W - 2 * _MARGIN],
            )
            title_block.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), _C_LIGHT_BLUE),
                ("TOPPADDING",    (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ("LEFTPADDING",   (0, 0), (-1, -1), 10),
                ("RIGHTPADDING",  (0, 0), (-1, -1), 10),
            ]))
            story.append(KeepTogether([title_block, Spacer(1, 8)]))
            story.append(HRFlowable(width="100%", thickness=1, color=_C_MID_BLUE,
                                     spaceAfter=10))

            for section_title, section_text in chap["sections"]:
                section_content = []
                section_content.append(Paragraph(section_title, style_h2))
                # Zeilenumbrüche in separate Paragraphen umwandeln
                for paragraph in section_text.split("\n\n"):
                    clean = paragraph.strip()
                    if clean:
                        section_content.append(Paragraph(clean, style_body))
                story.append(KeepTogether(section_content))
                story.append(Spacer(1, 4))

            story.append(PageBreak())

        # ── Abschlussseite ────────────────────────────────────────────────────
        story.append(Spacer(1, 6 * cm))
        story.append(Paragraph("Ende des Benutzerhandbuchs", style_h1))
        story.append(HRFlowable(width="100%", thickness=2, color=_C_DARK_BLUE,
                                 spaceAfter=20))
        footer_lines = [
            f"Generiert am {now.strftime('%d.%m.%Y um %H:%M Uhr')}",
            "Verein Tischlein Deck Dich Vorarlberg · Ladritschweg 10c · 6773 Vandans",
            "Min Guata Lada — Anspruchsverwaltung · Version 1.0",
        ]
        for line in footer_lines:
            story.append(Paragraph(line, style_small))

        # ── Dokument erzeugen ─────────────────────────────────────────────────
        doc.build(
            story,
            onFirstPage=_title_page,
            onLaterPages=_header_footer,
        )

    # ── PDF öffnen ────────────────────────────────────────────────────────────

    def _open_pdf(self) -> None:
        """Öffnet die PDF mit dem Standard-PDF-Viewer des Betriebssystems."""
        from PyQt6.QtCore import QUrl
        from PyQt6.QtGui import QDesktopServices
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(self._path)))
