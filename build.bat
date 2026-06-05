@echo off
setlocal enabledelayedexpansion
title Min Guata Lada – Build (CORE ONLY)

echo ============================================================
echo  Min Guata Lada – Core Build (no release packaging)
echo ============================================================
echo.

set "PROJECT_DIR=%~dp0"
set "VENV=%PROJECT_DIR%.venv"
set "PYTHON=%VENV%\Scripts\python.exe"
set "PIP=%VENV%\Scripts\pip.exe"
set "PYINST=%VENV%\Scripts\pyinstaller.exe"

set "DIST_DIR=%PROJECT_DIR%dist\MinGuataLada"
set "EXE=%DIST_DIR%\MinGuataLada.exe"

:: 0. venv check
if not exist "%PYTHON%" (
    echo [FEHLER] venv fehlt
    pause & exit /b 1
)

:: 1. deps
echo [1/4] dependencies...
"%PIP%" install -r "%PROJECT_DIR%requirements.txt" --quiet
"%PIP%" install pyinstaller pillow --quiet

:: 2. icon
echo [2/4] icon...
"%PYTHON%" "%PROJECT_DIR%scripts\create_icon.py"

:: 3. clean
echo [3/4] clean...
if exist "%PROJECT_DIR%build" rmdir /s /q "%PROJECT_DIR%build"
if exist "%PROJECT_DIR%dist" rmdir /s /q "%PROJECT_DIR%dist"

:: 4. build
echo [4/4] pyinstaller...
cd /d "%PROJECT_DIR%"
"%PYINST%" anspruchssystem.spec --noconfirm

if errorlevel 1 (
    echo BUILD FAILED
    pause & exit /b 1
)

if not exist "%EXE%" (
    echo EXE NOT FOUND
    pause & exit /b 1
)

echo.
echo BUILD OK: %EXE%
endlocal
exit /b 0