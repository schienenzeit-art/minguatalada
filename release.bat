@echo off
setlocal
cd /d "%~dp0"
set "PYTHON=%~dp0.venv\Scripts\python.exe"

if not exist "%PYTHON%" (
    echo [FEHLER] Virtuelle Umgebung nicht gefunden.
    echo Bitte ausfuehren: python -m venv .venv  ^&^&  .venv\Scripts\pip install -r requirements.txt
    pause & exit /b 1
)

"%PYTHON%" scripts\release.py %*
endlocal
