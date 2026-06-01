@echo off
setlocal enabledelayedexpansion
title Min Guata Lada – Build

echo ============================================================
echo  Min Guata Lada – Windows Build
echo ============================================================
echo.

:: Projektstamm (Verzeichnis dieses Skripts)
set "PROJECT_DIR=%~dp0"
set "VENV=%PROJECT_DIR%.venv"
set "PYTHON=%VENV%\Scripts\python.exe"
set "PIP=%VENV%\Scripts\pip.exe"
set "PYINST=%VENV%\Scripts\pyinstaller.exe"
set "DIST_DIR=%PROJECT_DIR%dist\MinGuataLada"
set "EXE=%DIST_DIR%\MinGuataLada.exe"

:: Release-Ziel auf dem Desktop
set "DESKTOP=%USERPROFILE%\Desktop"
set "RELEASE_DIR=%DESKTOP%\MinGuataLada-Release"

:: ── 0. Virtuelle Umgebung prüfen ──────────────────────────────────────────────
if not exist "%PYTHON%" (
    echo [FEHLER] Virtuelle Umgebung nicht gefunden: %VENV%
    echo Bitte zuerst ausfuehren:  python -m venv .venv
    pause & exit /b 1
)

:: ── 1. Abhängigkeiten installieren ────────────────────────────────────────────
echo [1/7] Abhaengigkeiten installieren ...
"%PIP%" install -r "%PROJECT_DIR%requirements.txt" --quiet
if errorlevel 1 ( echo [FEHLER] pip install fehlgeschlagen & pause & exit /b 1 )

"%PIP%" install pyinstaller pillow --quiet
if errorlevel 1 ( echo [FEHLER] PyInstaller/Pillow-Installation fehlgeschlagen & pause & exit /b 1 )

:: ── 2. Logo-Assets erstellen ──────────────────────────────────────────────────
echo [2/7] Logo-Assets erstellen ...
"%PYTHON%" "%PROJECT_DIR%scripts\create_icon.py"
if errorlevel 1 ( echo [WARNUNG] Logo-Erstellung fehlgeschlagen – Build wird fortgesetzt. )

:: ── 3. Alte Build-Artefakte bereinigen ────────────────────────────────────────
echo [3/7] Alte Build-Artefakte bereinigen ...
if exist "%PROJECT_DIR%build" rmdir /s /q "%PROJECT_DIR%build"
if exist "%PROJECT_DIR%dist"  rmdir /s /q "%PROJECT_DIR%dist"

:: ── 4. PyInstaller ausführen ──────────────────────────────────────────────────
echo [4/7] PyInstaller ausfuehren ...
cd /d "%PROJECT_DIR%"
"%PYINST%" anspruchssystem.spec --noconfirm
if errorlevel 1 ( echo [FEHLER] PyInstaller-Build fehlgeschlagen & pause & exit /b 1 )

:: ── 5. Build-Ergebnis prüfen ──────────────────────────────────────────────────
echo [5/7] Build-Ergebnis pruefen ...
if not exist "%EXE%" (
    echo [FEHLER] EXE nicht gefunden: %EXE%
    pause & exit /b 1
)
echo    OK: EXE gefunden unter dist\MinGuataLada\MinGuataLada.exe

:: ── 6. Release-Ordner auf Desktop erstellen ───────────────────────────────────
echo [6/7] Release-Ordner auf Desktop erstellen ...

:: Alten Release-Ordner entfernen
if exist "%RELEASE_DIR%" (
    echo    Entferne alten Release-Ordner ...
    rmdir /s /q "%RELEASE_DIR%"
)

:: Neuen Release-Ordner anlegen
mkdir "%RELEASE_DIR%"
mkdir "%RELEASE_DIR%\data"
mkdir "%RELEASE_DIR%\data\pdfs"
mkdir "%RELEASE_DIR%\data\backups"
mkdir "%RELEASE_DIR%\data\updates"
mkdir "%RELEASE_DIR%\logs"

:: Komplettes Build-Verzeichnis kopieren
echo    Kopiere Build-Artefakte ...
xcopy /s /e /q "%DIST_DIR%\*" "%RELEASE_DIR%\" >nul
if errorlevel 1 ( echo [FEHLER] Kopieren fehlgeschlagen & pause & exit /b 1 )

:: Benutzerhandbuch generieren und ablegen
echo    Benutzerhandbuch generieren ...
"%PYTHON%" "%PROJECT_DIR%scripts\generate_manual.py" "%RELEASE_DIR%\Benutzerhandbuch.pdf"
if errorlevel 1 (
    echo    [HINWEIS] Handbuch-Generierung uebersprungen – wird beim ersten Start automatisch erstellt.
)

:: README ablegen
echo Min Guata Lada - Anspruchsverwaltung > "%RELEASE_DIR%\README.txt"
echo Tischlein Deck Dich Vorarlberg >> "%RELEASE_DIR%\README.txt"
echo. >> "%RELEASE_DIR%\README.txt"
echo Starten: MinGuataLada.exe >> "%RELEASE_DIR%\README.txt"
echo Erstanmeldung: admin / Admin2024! >> "%RELEASE_DIR%\README.txt"
echo. >> "%RELEASE_DIR%\README.txt"
echo Datenspeicherort: %%LOCALAPPDATA%%\Anspruchssystem\ >> "%RELEASE_DIR%\README.txt"
echo Handbuch: Benutzerhandbuch.pdf (im selben Ordner) >> "%RELEASE_DIR%\README.txt"

:: ── 7. Abschluss ──────────────────────────────────────────────────────────────
echo [7/7] Abschluss ...
echo.
echo ============================================================
echo  BUILD ERFOLGREICH
echo ============================================================
echo  EXE:     %RELEASE_DIR%\MinGuataLada.exe
echo  Release: %RELEASE_DIR%
echo ============================================================
echo.

:: Release-Ordner im Explorer oeffnen
explorer "%RELEASE_DIR%"

endlocal
