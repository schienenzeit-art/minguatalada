; Inno Setup Script – Min Guata Lada Installer
; Voraussetzung: build.bat muss zuerst ausgeführt worden sein
; Build-Ausgabe erwartet unter: ..\dist\MinGuataLada\
;
; Inno Setup herunterladen: https://jrsoftware.org/isdl.php
; Dieses Skript mit dem Inno Setup Compiler kompilieren.

#define MyAppName      "Min Guata Lada"
#define MyAppVersion   "1.0.0"
#define MyAppPublisher "Tischlein Deck Dich Vorarlberg"
#define MyAppExeName   "MinGuataLada.exe"
#define MyAppID        "{A1B2C3D4-E5F6-7890-ABCD-EF1234567890}"
#define SourceDir      "..\dist\MinGuataLada"

[Setup]
AppId={{#MyAppID}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL=
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
OutputDir=.
OutputBaseFilename=MinGuataLada_Setup_{#MyAppVersion}
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
WizardImageFile=..\assets\logo.png
SetupIconFile=..\assets\logo.ico
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0

; Deinstallation
UninstallDisplayName={#MyAppName}
UninstallDisplayIcon={app}\{#MyAppExeName}

[Languages]
Name: "german"; MessagesFile: "compiler:Languages\German.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"
Name: "startmenuicon"; Description: "Startmenü-Eintrag erstellen"; GroupDescription: "{cm:AdditionalIcons}"; Flags: checkedonce

[Files]
; Alle Dateien aus dem PyInstaller-Output
Source: "{#SourceDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
; Startmenü
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"

; Desktop
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
; Anwendung nach Installation direkt starten (optional)
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#MyAppName}}"; Flags: nowait postinstall skipifsilent

[Code]
// Prüft ob .NET / VC++ Redistributable nötig – hier nicht erforderlich
// Placeholder für zukünftige Voraussetzungsprüfungen
procedure InitializeWizard();
begin
  // Nichts zu tun
end;
