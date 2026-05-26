@echo off
setlocal enabledelayedexpansion
title Anspruchssystem – Build

echo ============================================================
echo  Anspruchssystem – Windows Build
echo ============================================================
echo.

:: Projektstamm
set "PROJECT_DIR=%~dp0"
set "VENV=%PROJECT_DIR%.venv"
set "PYTHON=%VENV%\Scripts\python.exe"
set "PIP=%VENV%\Scripts\pip.exe"
set "PYINST=%VENV%\Scripts\pyinstaller.exe"

:: Python-Umgebung prüfen
if not exist "%PYTHON%" (
    echo [FEHLER] Virtuelle Umgebung nicht gefunden: %VENV%
    echo Bitte zuerst: python -m venv .venv
    pause & exit /b 1
)

echo [1/4] Abhängigkeiten installieren ...
"%PIP%" install -r "%PROJECT_DIR%requirements.txt" --quiet
if errorlevel 1 ( echo [FEHLER] pip install fehlgeschlagen & pause & exit /b 1 )

echo [2/4] PyInstaller sicherstellen ...
"%PIP%" install pyinstaller --quiet
if errorlevel 1 ( echo [FEHLER] PyInstaller-Installation fehlgeschlagen & pause & exit /b 1 )

echo [3/4] Alte Build-Artefakte bereinigen ...
if exist "%PROJECT_DIR%build" rmdir /s /q "%PROJECT_DIR%build"
if exist "%PROJECT_DIR%dist"  rmdir /s /q "%PROJECT_DIR%dist"

echo [4/4] PyInstaller ausführen ...
cd /d "%PROJECT_DIR%"
"%PYINST%" anspruchssystem.spec --noconfirm
if errorlevel 1 ( echo [FEHLER] PyInstaller-Build fehlgeschlagen & pause & exit /b 1 )

echo.
echo ============================================================
echo  Build erfolgreich abgeschlossen!
echo  Ausgabe: dist\Anspruchssystem\Anspruchssystem.exe
echo ============================================================
echo.

:: Kurz-Test: EXE existiert?
if exist "%PROJECT_DIR%dist\Anspruchssystem\Anspruchssystem.exe" (
    echo [OK] Anspruchssystem.exe wurde erstellt.
) else (
    echo [WARNUNG] EXE nicht gefunden – bitte Build-Log prüfen.
)

echo.
echo Drücken Sie eine Taste um das Ausgabeverzeichnis zu öffnen ...
pause > nul
explorer "%PROJECT_DIR%dist\Anspruchssystem"
endlocal
