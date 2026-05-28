; =============================================================================
; Inno Setup Script – Min Guata Lada
; Herausgeber: Nexaris Software Engineering
; Voraussetzung: build.bat muss zuerst ausgef�hrt worden sein
; =============================================================================

#define MyAppName        "Min Guata Lada"
#define MyAppVersion     "1.0.0"
#define MyAppPublisher   "Nexaris Software Engineering"
#define MyAppCopyright   "Copyright � 2025 Nexaris Software Engineering"
#define MyAppExeName     "MinGuataLada.exe"
#define MyAppID          "{A1B2C3D4-E5F6-7890-ABCD-EF1234567890}"
#define SourceDir        "..\dist\MinGuataLada"

[Setup]
; Eindeutige App-ID (GUID – nicht �ndern, sonst Deinstallation bricht)
AppId={{#MyAppID}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppCopyright={#MyAppCopyright}
AppPublisherURL=
AppSupportURL=
AppUpdatesURL=

; Installer-Verzeichnis
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
AllowNoIcons=yes

; Ausgabe
OutputDir=.
OutputBaseFilename=MinGuataLada_Setup_{#MyAppVersion}

; Kompression
Compression=lzma2/ultra64
SolidCompression=yes

; Erscheinungsbild
WizardStyle=modern
WizardImageFile=..\assets\logo.png
SetupIconFile=..\assets\logo.ico

; Lizenzvereinbarung (muss aktiv best�tigt werden)
LicenseFile=license.rtf

; Berechtigungen – ohne Admin installierbar, Admin-Modus auf Nachfrage
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog

; Windows-Mindestversion und Architektur
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0

; Versionsinformationen des Installers (sichtbar in Dateieigenschaften)
VersionInfoVersion={#MyAppVersion}.0
VersionInfoCompany={#MyAppPublisher}
VersionInfoDescription={#MyAppName} Installer
VersionInfoCopyright={#MyAppCopyright}
VersionInfoProductName={#MyAppName}
VersionInfoProductVersion={#MyAppVersion}.0

; Deinstallation
UninstallDisplayName={#MyAppName}
UninstallDisplayIcon={app}\{#MyAppExeName}
UninstallFilesDir={app}

; Signierung: nach dem Build mit signtool.exe signieren (siehe sign_build.bat)
; SignTool=nexaris sign /fd SHA256 /tr http://timestamp.digicert.com /td SHA256 $f

[Languages]
Name: "german"; MessagesFile: "compiler:Languages\German.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: checkedonce
Name: "startmenuicon"; Description: "Startmen�-Eintrag erstellen"; GroupDescription: "{cm:AdditionalIcons}"; Flags: checkedonce

[Files]
; PyInstaller-Output
Source: "{#SourceDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
; Datenschutz-RTF tempor�r f�r Installer-Seite
Source: "privacy.rtf"; DestDir: "{tmp}"; Flags: dontcopy deleteafterinstall

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\{#MyAppExeName}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#MyAppName}}"; Flags: nowait postinstall skipifsilent

[Code]

var
  PrivacyPage:     TWizardPage;
  PrivacyMemo:     TRichEditViewer;
  PrivacyCheckBox: TCheckBox;

procedure InitializeWizard();
begin
  // ── Datenschutz-Seite (nach der Lizenzseite) ──────────────────────────────
  PrivacyPage := CreateCustomPage(
    wpLicense,
    'Datenschutzerkl�rung',
    'Bitte lesen Sie die Datenschutzerkl�rung und best�tigen Sie Ihre Zustimmung.'
  );

  PrivacyMemo := TRichEditViewer.Create(WizardForm);
  PrivacyMemo.ScrollBars   := ssVertical;
  PrivacyMemo.Parent       := PrivacyPage.Surface;
  PrivacyMemo.Left         := 0;
  PrivacyMemo.Top          := 0;
  PrivacyMemo.Width        := PrivacyPage.SurfaceWidth;
  PrivacyMemo.Height       := PrivacyPage.SurfaceHeight - 32;
  PrivacyMemo.ReadOnly     := True;
  ExtractTemporaryFile('privacy.rtf');
  PrivacyMemo.Lines.LoadFromFile(ExpandConstant('{tmp}\privacy.rtf'));

  PrivacyCheckBox := TCheckBox.Create(WizardForm);
  PrivacyCheckBox.Parent   := PrivacyPage.Surface;
  PrivacyCheckBox.Left     := 0;
  PrivacyCheckBox.Top      := PrivacyPage.SurfaceHeight - 26;
  PrivacyCheckBox.Width    := PrivacyPage.SurfaceWidth;
  PrivacyCheckBox.Height   := 22;
  PrivacyCheckBox.Caption  := 'Ich habe die Datenschutzerkl�rung gelesen und akzeptiere diese.';
end;

function NextButtonClick(CurPageID: Integer): Boolean;
begin
  Result := True;
  if CurPageID = PrivacyPage.ID then
  begin
    if not PrivacyCheckBox.Checked then
    begin
      MsgBox(
        'Bitte best�tigen Sie die Datenschutzerkl�rung, um die Installation fortzusetzen.',
        mbError, MB_OK
      );
      Result := False;
    end;
  end;
end;
