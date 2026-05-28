@echo off
setlocal enabledelayedexpansion
title Nexaris Software Engineering – Code Signing

echo ============================================================
echo  Min Guata Lada – Code Signing
echo  Nexaris Software Engineering
echo ============================================================
echo.

:: ── Konfiguration ────────────────────────────────────────────────────────────
set "PROJECT_DIR=%~dp0"
set "EXE=%PROJECT_DIR%dist\MinGuataLada\MinGuataLada.exe"
set "INSTALLER=%PROJECT_DIR%installer\MinGuataLada_Setup_1.0.0.exe"

:: Zertifikat-Pfad (PFX-Datei) – hier anpassen:
set "CERT_FILE=%PROJECT_DIR%certs\nexaris_codesign.pfx"

:: Timestamp-Server (DigiCert – kostenlos nutzbar)
set "TIMESTAMP_URL=http://timestamp.digicert.com"

:: Signatur-Algorithmus
set "DIGEST=SHA256"

:: ── signtool.exe suchen ──────────────────────────────────────────────────────
set "SIGNTOOL="
for %%v in (10.0.22621.0 10.0.20348.0 10.0.19041.0 10.0.18362.0 10.0.17763.0) do (
    if exist "%ProgramFiles(x86)%\Windows Kits\10\bin\%%v\x64\signtool.exe" (
        set "SIGNTOOL=%ProgramFiles(x86)%\Windows Kits\10\bin\%%v\x64\signtool.exe"
    )
)
if not defined SIGNTOOL (
    for /f "delims=" %%i in ('where signtool 2^>nul') do set "SIGNTOOL=%%i"
)
if not defined SIGNTOOL (
    echo [FEHLER] signtool.exe nicht gefunden.
    echo.
    echo Bitte installieren:
    echo   Windows SDK: https://developer.microsoft.com/windows/downloads/windows-sdk/
    echo   Oder: Visual Studio mit Workload "Desktop-Entwicklung mit C++"
    echo.
    goto :INSTRUCTIONS
)
echo [OK] signtool.exe: %SIGNTOOL%

:: ── Zertifikat pruefen ────────────────────────────────────────────────────────
if not exist "%CERT_FILE%" (
    echo [WARNUNG] Zertifikat nicht gefunden: %CERT_FILE%
    echo.
    goto :INSTRUCTIONS
)

:: ── Passwort abfragen ─────────────────────────────────────────────────────────
set /p "CERT_PASSWORD=PFX-Passwort fuer %CERT_FILE%: "
if "%CERT_PASSWORD%"=="" (
    echo [FEHLER] Kein Passwort eingegeben.
    pause & exit /b 1
)

:: ── EXE signieren ─────────────────────────────────────────────────────────────
echo.
echo [1/2] Signiere EXE ...
if not exist "%EXE%" (
    echo [FEHLER] EXE nicht gefunden: %EXE%
    echo Bitte zuerst build.bat ausfuehren.
    pause & exit /b 1
)
"%SIGNTOOL%" sign ^
    /fd %DIGEST% ^
    /tr %TIMESTAMP_URL% /td %DIGEST% ^
    /f "%CERT_FILE%" /p "%CERT_PASSWORD%" ^
    /d "Min Guata Lada" ^
    /du "https://nexaris.at" ^
    "%EXE%"
if errorlevel 1 ( echo [FEHLER] EXE-Signierung fehlgeschlagen & pause & exit /b 1 )
echo [OK] EXE signiert.

:: ── Installer signieren ───────────────────────────────────────────────────────
echo [2/2] Signiere Installer ...
if not exist "%INSTALLER%" (
    echo [WARNUNG] Installer nicht gefunden: %INSTALLER%
    echo Bitte zuerst ISCC.exe ausfuehren oder build.bat mit Installer-Schritt.
    goto :DONE
)
"%SIGNTOOL%" sign ^
    /fd %DIGEST% ^
    /tr %TIMESTAMP_URL% /td %DIGEST% ^
    /f "%CERT_FILE%" /p "%CERT_PASSWORD%" ^
    /d "Min Guata Lada Installer" ^
    /du "https://nexaris.at" ^
    "%INSTALLER%"
if errorlevel 1 ( echo [FEHLER] Installer-Signierung fehlgeschlagen & pause & exit /b 1 )
echo [OK] Installer signiert.

:DONE
echo.
echo ============================================================
echo  Signierung abgeschlossen.
echo ============================================================
echo.
pause
endlocal
exit /b 0

:: ── Anleitung (wenn Zertifikat fehlt) ────────────────────────────────────────
:INSTRUCTIONS
echo ============================================================
echo  CODE SIGNING VORBEREITUNG – ANLEITUNG
echo ============================================================
echo.
echo  Um die Software zu signieren, benoetigen Sie ein Code-Signing-
echo  Zertifikat von einer vertrauenswuerdigen Zertifizierungsstelle.
echo.
echo  EMPFOHLENE ANBIETER (OV oder EV Code Signing):
echo    - DigiCert:     https://www.digicert.com/signing/code-signing-certificates
echo    - Sectigo:      https://sectigo.com/ssl-certificates-tls/code-signing
echo    - GlobalSign:   https://www.globalsign.com/de/code-signing-certificate
echo    - SignPath:     https://signpath.io  (fuer Open-Source kostenlos)
echo.
echo  SCHRITTE:
echo    1. OV (Organization Validation) Code-Signing-Zertifikat kaufen
echo    2. Zertifikat als PFX-Datei exportieren
echo    3. PFX-Datei ablegen unter:
echo       %CERT_FILE%
echo    4. Dieses Skript erneut ausfuehren
echo.
echo  WICHTIG: Ohne gueltiges Zertifikat zeigt Windows SmartScreen
echo  beim ersten Ausfuehren einer neuen .exe eine Warnung.
echo  Diese Warnung verschwindet nach einer ausreichenden Download-
echo  Reputationsphase automatisch (typisch: einige Wochen/Monate).
echo  Mit OV-Zertifikat: sofort vertrauenswuerdig.
echo  Mit EV-Zertifikat: hoechste Vertrauensstufe, keine SmartScreen-Warnung.
echo.
echo ============================================================
echo.
pause
endlocal
