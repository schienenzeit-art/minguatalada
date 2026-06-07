; =============================================================================
; Inno Setup Script -- Min Guata Lada
; Tischlein Deck Dich Vorarlberg -- Anspruchsverwaltung
; Voraussetzung: build.bat muss zuerst ausgefuehrt worden sein
; Erstellt mit Inno Setup 6
; =============================================================================

; Version kann per Kommandozeile ueberschrieben werden:
;   ISCC.exe setup.iss /DMyAppVersion=1.5.0
#ifndef MyAppVersion
  #define MyAppVersion "1.5.0"
#endif

#define MyAppName        "Min Guata Lada"
#define MyAppPublisher   "Nexaris Software Engineering"
#define MyAppCopyright   "Copyright (C) 2026 Nexaris Software Engineering"
#define MyAppExeName     "MinGuataLada.exe"
#define MyAppID          "{A1B2C3D4-E5F6-7890-ABCD-EF1234567890}"
#define SourceDir        "..\dist\MinGuataLada"
#define ManualPath       "..\dist\MinGuataLada\..\..\..\MinGuataLada-Release\Benutzerhandbuch.pdf"

[Setup]
; Eindeutige App-ID -- NICHT aendern (Deinstallation + Upgrades)
AppId={{#MyAppID}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppCopyright={#MyAppCopyright}
AppPublisherURL=
AppSupportURL=
AppUpdatesURL=

; ── Installationsverzeichnis ────────────────────────────────────────────────
; Program Files -- schreibgeschuetzt fuer Standardbenutzer (Sicherheit)
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
AllowNoIcons=yes

; ── Sicherheit: Admin-Rechte erforderlich ───────────────────────────────────
; Installiert nach Program Files -- Standardbenutzer koennen Dateien
; dort NICHT veraendern. Nutzerdaten liegen separat in %LOCALAPPDATA%.
PrivilegesRequired=admin

; ── Ausgabe ─────────────────────────────────────────────────────────────────
OutputDir=.
OutputBaseFilename=MinGuataLada_Setup_{#MyAppVersion}

; ── Kompression ─────────────────────────────────────────────────────────────
Compression=lzma2/ultra64
SolidCompression=yes

; ── Erscheinungsbild ────────────────────────────────────────────────────────
WizardStyle=modern
SetupIconFile=..\assets\logo.ico

; ── Lizenz ──────────────────────────────────────────────────────────────────
LicenseFile=license.rtf

; ── Windows-Anforderungen ───────────────────────────────────────────────────
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0

; ── Versionsinformationen ───────────────────────────────────────────────────
VersionInfoVersion={#MyAppVersion}.0
VersionInfoCompany={#MyAppPublisher}
VersionInfoDescription={#MyAppName} Setup
VersionInfoCopyright={#MyAppCopyright}
VersionInfoProductName={#MyAppName}
VersionInfoProductVersion={#MyAppVersion}.0

; ── Deinstallation ──────────────────────────────────────────────────────────
UninstallDisplayName={#MyAppName}
UninstallDisplayIcon={app}\{#MyAppExeName}
UninstallFilesDir={app}

; Beim Upgrade bestehende Version automatisch ersetzen
CloseApplications=yes
CloseApplicationsFilter=*MinGuataLada*
RestartApplications=no

[Languages]
Name: "german"; MessagesFile: "compiler:Languages\German.isl"

[Tasks]
Name: "desktopicon";   Description: "Desktop-Verknuepfung erstellen"; GroupDescription: "Zusaetzliche Optionen:"; Flags: checkedonce
Name: "startmenuicon"; Description: "Startmenue-Eintrag erstellen";   GroupDescription: "Zusaetzliche Optionen:"; Flags: checkedonce

[Files]
; ── Anwendungsdateien (PyInstaller One-Folder) ──────────────────────────────
; Flags: ignoreversion = existierende Dateien immer ersetzen (fuer Upgrades)
Source: "{#SourceDir}\*";                  DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

; ── Benutzerhandbuch ────────────────────────────────────────────────────────
; Wird im App-Verzeichnis abgelegt (schreibgeschuetzt, aber lesbar)
Source: "..\Benutzerhandbuch.pdf";         DestDir: "{app}"; Flags: ignoreversion skipifsourcedoesntexist

[Dirs]
; ── Nutzerdaten-Ordner in %LOCALAPPDATA% ────────────────────────────────────
; WICHTIG: Diese Verzeichnisse werden NIEMALS geloescht oder ueberschrieben.
; Hier liegen Datenbank, PDFs, Backups und hochgeladene Dokumente.
Name: "{localappdata}\Anspruchssystem";                  Flags: uninsneveruninstall
Name: "{localappdata}\Anspruchssystem\pdfs";             Flags: uninsneveruninstall
Name: "{localappdata}\Anspruchssystem\documents";        Flags: uninsneveruninstall
Name: "{localappdata}\Anspruchssystem\backups";          Flags: uninsneveruninstall
Name: "{localappdata}\Anspruchssystem\updates";          Flags: uninsneveruninstall

[Icons]
; Startmenue
Name: "{group}\{#MyAppName}";                    Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\{#MyAppExeName}"; Tasks: startmenuicon
Name: "{group}\Benutzerhandbuch";                Filename: "{app}\Benutzerhandbuch.pdf"; Tasks: startmenuicon
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
; Desktop
Name: "{autodesktop}\{#MyAppName}";              Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
; Anwendung nach Installation starten (optional)
Filename: "{app}\{#MyAppExeName}"; Description: "{#MyAppName} jetzt starten"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; Beim Deinstallieren: nur Build-Caches entfernen, KEINE Nutzerdaten
Type: filesandordirs; Name: "{app}\__pycache__"
Type: filesandordirs; Name: "{app}\build"

[Code]
// ── Upgrade-Erkennung ────────────────────────────────────────────────────────
// Wenn dieselbe AppId bereits installiert ist, wird automatisch upgradet
// ohne separate Deinstallation -- Nutzerdaten bleiben erhalten.

function InitializeSetup(): Boolean;
begin
  Result := True;
end;

function NextButtonClick(CurPageID: Integer): Boolean;
begin
  Result := True;
end;

// ── Hinweis nach Deinstallation ──────────────────────────────────────────────
procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
begin
  if CurUninstallStep = usPostUninstall then
  begin
    MsgBox(
      '{#MyAppName} wurde deinstalliert.' + #13#10 + #13#10 +
      'Ihre Daten (Datenbank, Dokumente, Backups) wurden NICHT geloescht.' + #13#10 +
      'Sie befinden sich unter:' + #13#10 +
      '%LOCALAPPDATA%\Anspruchssystem\' + #13#10 + #13#10 +
      'Sie koennen diesen Ordner manuell loeschen, wenn er nicht mehr benoetigt wird.',
      mbInformation, MB_OK
    );
  end;
end;
