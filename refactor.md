# Refactor Plan

## 1. Analyse
- [x] Relevante Dateien und Module identifiziert
  - `ui/pages/dashboard/dashboard_page.py`
  - `services/dashboard_service.py`
  - `ui/pages/claims/claims_page.py`
  - `ui/pages/cards_page.py`
  - `ui/pages/tasks/tasks_page.py`
  - `ui/components/topbar.py`
  - `ui/shell/main_window.py`
  - `ui/pages/documents/documents_page.py`
  - `ui/pages/person_dossier_dialog.py`
  - `database/db.py`
  - `domain/categories.py`
  - `core/claim_status.py`
- [ ] Bestehende Datenflüsse, Filterübergaben und Persistenzabhängigkeiten prüfen
- [ ] Fachlogik vs. UI-Verdrahtung klar trennen

## 2. Dashboard / KPI-Drilldowns
- [x] `DashboardService.get_kpi_items()` prüfen und KPI-Filter dokumentieren
- [x] `DashboardPage.build_kpi_card()` muss `navigate_callback(page, filters)` sauber auslösen
- [x] Zielseiten müssen Filter akzeptieren und anwenden
  - `ClaimsPage.apply_filters()` / `load_claims()`
  - `CardsPage.apply_filters()` / `on_filter_changed()`
  - `TasksPage.apply_filters()` / `refresh_tasks()`
- [x] `DashboardPage._refresh_table_rows()` darf nur offene Anträge (`IN_PRUEFUNG`) zeigen
- Risiko: falsche Filterübergabe erzeugt unpassende Listen
- Prüfschritt: Klick auf KPI öffnet korrekte Ansicht, Status wird gefiltert

## 3. Statusdarstellung
- [ ] `core/claim_status.py` einheitliche Display-Namen sicherstellen
- [ ] UI muss technische Rohwerte vermeiden
- [ ] Status-Indikatoren in Tabellen einheitlich machen
- Risiko: inkonsistente Anzeigen in Dashboard / Claim-Listen
- Prüfschritt: Statuslabels in allen Views vergleichen

## 4. Anspruchsberechtigte Personen / Kategorien
- [ ] `domain/categories.py` um `Familie` und `Sozialhilfebezüger` erweitern
- [ ] Nutzung der Kategorien in Persistenz/Claims prüfen
- [ ] Separate Ansicht für anspruchsberechtigte Personen definieren
- Risiko: fehlende Kategorie-Seedwerte oder falsch verknüpfte Filter
- Prüfschritt: Kategorieauswahl im Backend und Datenbank-Seed testen

## 5. Anträge / Fälle
- [ ] `ClaimsPage` muss Checkboxen für Mehrfachauswahl erhalten
- [ ] Rechtsklick-Menü und 3-Punkte-Menü planen
- [ ] Delete-Taste + Bestätigungsdialog für Löschung einbauen
- [ ] `Neuer Antrag` im Dashboard muss bereits funktionieren
- Risiko: Änderung der Claim-Löschlogik darf Fachlogik nicht brechen
- Prüfschritt: Auswahl/Doppelklick/Entfernen funktionieren auf Claims-Seite

## 6. Fensterverhalten
- [ ] Dialoge dürfen minimierbar/maximierbar sein
- [ ] Formulare scrollbar machen (`QScrollArea`) wo nötig
- [ ] Hauptfenster beim Start maximiert öffnen
- Risiko: UX-Probleme bei kleinen Bildschirmen
- Prüfschritt: Fensterverhalten bei Dialogen und Hauptfenster validieren

## 7. Dokumente / Archiv
- [ ] `DocumentsPage` und `DocumentsWebPage` klar trennen
- [ ] Automatische Archivierung verhindern
- [ ] In `DocumentsPage` expliziter Archiv-Button einbauen
- [ ] Dokumente personenzentriert ausrichten
  - Name
  - Fall-ID
  - Filter nach Name
  - aufklappbares Dossier pro Person
  - einzelstehende Dokumente anklickbar
  - Dokumentnamen änderbar
- Risiko: Doppelung von Archiv- und Dokument-Views
- Prüfschritt: Dokumente lassen sich archivieren, nicht automatisch verschieben

## 8. Personen-Dossier
- [ ] `PersonDossierDialog` als eigene Page/Area umwandeln
- [ ] Filter nach Name/Vorname/Standort anbieten
- [ ] Status je Person anzeigen: Anspruchsberechtigt, Abgelehnt, Härtefall, in Prüfung
- [ ] UI-Sprache an Dashboard angleichen
- Risiko: Dialog bleibt isoliert, App-Rechte unklar
- Prüfschritt: Personen-Dossier direkt aus Navigation öffnen und filtern

## 9. Globalsuche
- [ ] TopBar-Suche implementieren auf Suchbegriffe und Teilbegriffe
- [ ] Autosuggest / Vorschläge anzeigen
- [ ] Treffer navigierbar machen
- Risiko: ungenaue Suche, zu viele Treffer
- Prüfschritt: Suche im TopBar führt zu passenden Anträgen/Personen

## 10. Reports / Zeitraumreport
- [ ] Report-Buttons klickbar machen
- [ ] Parameterauswahl (Zeitraum) ins UI einbauen
- [ ] Ausgabe sichtbar machen / PDF- oder Excel-Öffnung verlässlich machen
- Risiko: Report-IO kann Plattformunterschiede aufwerfen
- Prüfschritt: PDF/Excel öffnen oder Download-Link sichtbar

## 11. Standorte / Referenzdaten
- [ ] Demo-/Mock-Standorte entfernen
- [ ] zentrale Standorte verwenden: Bludenz, Feldkirch, Dornbirn
- [ ] `location_service` als Quelle verwenden
- Risiko: verkopfte Hardcoded-Standorte in mehreren Views
- Prüfschritt: Standorte in Filterlisten korrespondieren mit DB

## 12. Benutzer / Sicherheit
- [ ] Wechsel von Benutzer / Mandant oben rechts realisieren
- [ ] Benutzerverwaltung prüfen (anlegen, ändern, deaktivieren, löschen)
- [ ] Passwortspeicherung ist bereits bcrypt-basiert
- [ ] Webserver-Vorbereitung möglich belassen
- Risiko: Session- und Nutzerwechsel nicht konsistent
- Prüfschritt: Benutzerwechsel zieht die aktuelle Session/TopBar nach

## 13. Architektur / Cleanup
- [ ] UI / Fachlogik / Persistenz sauber trennen
- [ ] zentrale Status- / Lookup-Logik prüfen
- [ ] Redundanzen vermeiden, nur bei Bedarf refactoren
- Risiko: große Refactors statt punktueller Reparatur
- Prüfschritt: bestehende DB-Schemata bleiben erhalten, keine stillen Behavior-Changes
