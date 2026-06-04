@echo off
setlocal enabledelayedexpansion
title Min Guata Lada – Release 1.3.0

echo ============================================================
echo  Min Guata Lada – Release Build v1.3.0
echo  Update-Pfad: 1.0.0 -> 1.3.0 (direkt, ein Paket)
echo ============================================================
echo.

set "PROJECT_DIR=%~dp0"
set "VENV=%PROJECT_DIR%.venv"
set "PYTHON=%VENV%\Scripts\python.exe"
set "VERSION=1.3.0"
set "EXE_NAME=MinGuataLada.exe"
set "DIST_DIR=%PROJECT_DIR%dist\MinGuataLada"
set "EXE=%DIST_DIR%\%EXE_NAME%"
set "OUT_DIR=%PROJECT_DIR%releases"
set "MUGALA_OUT=%OUT_DIR%\update_%VERSION%.mugala"
set "SIGN_KEY=%PROJECT_DIR%certs\mugala_signing.key"

:: ── 0. Venv prüfen ─────────────────────────────────────────────────────────
if not exist "%PYTHON%" (
    echo [FEHLER] Virtuelle Umgebung nicht gefunden: %VENV%
    echo Bitte ausfuehren: python -m venv .venv && .venv\Scripts\pip install -r requirements.txt
    pause & exit /b 1
)

:: ── 1. Tests ausführen ─────────────────────────────────────────────────────
echo [1/4] Tests ausfuehren (273 erwartet) ...
cd /d "%PROJECT_DIR%"
"%PYTHON%" -m pytest tests/ -q --tb=short
if errorlevel 1 (
    echo.
    echo [FEHLER] Tests fehlgeschlagen – Release abgebrochen.
    echo Bitte alle Tests fixen bevor ein Release erstellt wird.
    pause & exit /b 1
)
echo    OK: Alle Tests gruen.
echo.

:: ── 2. EXE bauen (PyInstaller via build.bat) ───────────────────────────────
echo [2/4] EXE bauen ...
call "%PROJECT_DIR%build.bat"
if errorlevel 1 (
    echo [FEHLER] build.bat fehlgeschlagen.
    pause & exit /b 1
)

:: EXE-Existenz prüfen
if not exist "%EXE%" (
    echo [FEHLER] EXE nicht gefunden nach Build: %EXE%
    pause & exit /b 1
)
echo    OK: EXE bereit unter dist\MinGuataLada\%EXE_NAME%
echo.

:: ── 3. .mugala-Paket erstellen ─────────────────────────────────────────────
echo [3/4] .mugala-Paket erstellen ...
if not exist "%OUT_DIR%" mkdir "%OUT_DIR%"

if exist "%SIGN_KEY%" (
    echo    Signatur: %SIGN_KEY%
    "%PYTHON%" "%PROJECT_DIR%scripts\build_mugala.py" ^
        %VERSION% "%EXE%" "%MUGALA_OUT%" ^
        --sign "%SIGN_KEY%"
) else (
    echo    [HINWEIS] Kein Signierschluessel gefunden unter certs\mugala_signing.key
    echo    Paket wird OHNE Signatur erstellt (Transitional Mode).
    "%PYTHON%" "%PROJECT_DIR%scripts\build_mugala.py" ^
        %VERSION% "%EXE%" "%MUGALA_OUT%"
)

if errorlevel 1 (
    echo [FEHLER] build_mugala.py fehlgeschlagen.
    pause & exit /b 1
)
echo.

:: ── 4. Verifikation ────────────────────────────────────────────────────────
echo [4/4] Paket verifizieren ...
if not exist "%MUGALA_OUT%" (
    echo [FEHLER] .mugala-Paket nicht gefunden: %MUGALA_OUT%
    pause & exit /b 1
)

for %%A in ("%MUGALA_OUT%") do set "SIZE=%%~zA"
set /a "SIZE_MB=%SIZE% / 1048576"
echo    Datei:   %MUGALA_OUT%
echo    Groesse: %SIZE_MB% MB
echo.

:: ── Abschluss ──────────────────────────────────────────────────────────────
echo ============================================================
echo  RELEASE ERFOLGREICH
echo ============================================================
echo.
echo  Version:     %VERSION%
echo  Update-Pfad: 1.0.0 ^-^> 1.3.0  (direkt, ein Paket)
echo  Paket:       %MUGALA_OUT%
echo.
echo  Einspielen: Admin-Bereich -> Updates -> Paket auswaehlen
echo              -> .mugala-Datei auswaehlen -> Update starten
echo.
echo ============================================================

explorer "%OUT_DIR%"
pause
endlocal
