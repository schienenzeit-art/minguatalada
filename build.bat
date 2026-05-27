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
set "EXE=%PROJECT_DIR%dist\MinGuataLada\MinGuataLada.exe"

:: ── 0. Virtuelle Umgebung prüfen ─────────────────────────────────────────────
if not exist "%PYTHON%" (
    echo [FEHLER] Virtuelle Umgebung nicht gefunden: %VENV%
    echo Bitte zuerst ausfuehren:  python -m venv .venv
    pause & exit /b 1
)

:: ── 1. Abhängigkeiten installieren ───────────────────────────────────────────
echo [1/5] Abhaengigkeiten installieren ...
"%PIP%" install -r "%PROJECT_DIR%requirements.txt" --quiet
if errorlevel 1 ( echo [FEHLER] pip install fehlgeschlagen & pause & exit /b 1 )

"%PIP%" install pyinstaller pillow --quiet
if errorlevel 1 ( echo [FEHLER] PyInstaller/Pillow-Installation fehlgeschlagen & pause & exit /b 1 )

:: ── 2. Logo-Assets erstellen ─────────────────────────────────────────────────
echo [2/5] Logo-Assets erstellen ...
"%PYTHON%" "%PROJECT_DIR%scripts\create_icon.py"
if errorlevel 1 ( echo [WARNUNG] Logo-Erstellung fehlgeschlagen – Build wird fortgesetzt. )

:: ── 3. Alte Build-Artefakte bereinigen ───────────────────────────────────────
echo [3/5] Alte Build-Artefakte bereinigen ...
if exist "%PROJECT_DIR%build" rmdir /s /q "%PROJECT_DIR%build"
if exist "%PROJECT_DIR%dist"  rmdir /s /q "%PROJECT_DIR%dist"

:: ── 4. PyInstaller ausführen ─────────────────────────────────────────────────
echo [4/5] PyInstaller ausfuehren ...
cd /d "%PROJECT_DIR%"
"%PYINST%" anspruchssystem.spec --noconfirm
if errorlevel 1 ( echo [FEHLER] PyInstaller-Build fehlgeschlagen & pause & exit /b 1 )

:: ── 5. Ergebnis prüfen ───────────────────────────────────────────────────────
echo [5/5] Ergebnis pruefen ...
echo.
echo ============================================================
if exist "%EXE%" (
    echo  BUILD ERFOLGREICH
    echo  Ausgabe: dist\MinGuataLada\MinGuataLada.exe
) else (
    echo  [WARNUNG] EXE nicht gefunden – bitte Build-Log pruefen.
)
echo ============================================================
echo.
echo Druecken Sie eine Taste um das Ausgabeverzeichnis zu oeffnen ...
pause > nul
if exist "%PROJECT_DIR%dist\MinGuataLada" (
    explorer "%PROJECT_DIR%dist\MinGuataLada"
)
endlocal
