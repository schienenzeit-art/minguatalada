# GitHub Secrets einrichten — Einmalige Konfiguration

Diese Secrets müssen einmalig unter **Settings → Secrets and variables → Actions**
im GitHub-Repository eingerichtet werden, bevor die Release-Pipeline funktioniert.

Repository: https://github.com/schienenzeit-art/minguatalada

---

## Schritt 1 — MUGALA_SIGNING_KEY_B64

Privater Signierschlüssel als Base64-String. Wird in der Release-Pipeline verwendet,
um das `.mugala`-Paket zu signieren. Die App prüft diese Signatur beim Update.

**PowerShell (lokal ausführen):**
```powershell
$bytes = [System.IO.File]::ReadAllBytes("certs\mugala_signing.key")
$b64 = [System.Convert]::ToBase64String($bytes)
$b64 | Set-Clipboard
Write-Host "Schlüssel in Zwischenablage kopiert."
```

Diesen String unter dem Secret-Namen `MUGALA_SIGNING_KEY_B64` speichern.

> **Sicherheitshinweis:** Den privaten Schlüssel niemals in das Repository committen.
> `.gitignore` schützt `certs/*.key` — aber trotzdem prüfen.

---

## Schritt 2 — FTP_HOST

Hostname des Update-Servers.

| Secret | Wert |
|--------|------|
| `FTP_HOST` | `web15.wh20.easyname.systems` |

---

## Schritt 3 — FTP_USERNAME

FTP-Benutzername aus dem easyname-Dashboard (Hosting → FTP-Konten).

| Secret | Wert |
|--------|------|
| `FTP_USERNAME` | *(aus easyname-Dashboard)* |

---

## Schritt 4 — FTP_PASSWORD

FTP-Passwort aus dem easyname-Dashboard.

| Secret | Wert |
|--------|------|
| `FTP_PASSWORD` | *(aus easyname-Dashboard)* |

---

## Schritt 5 — FTP_SERVER_DIR

Pfad auf dem Server, wo `manifest.json` und `.mugala` landen.

| Secret | Wert |
|--------|------|
| `FTP_SERVER_DIR` | `/www/updates/` |

> Falls der Pfad auf dem Server anders ist, entsprechend anpassen.
> Das ist das Verzeichnis das unter `https://www.schaer-systems.at/updates/` erreichbar ist.

---

## Überprüfung

Nach dem Einrichten einen Test-Release auslösen:

```bash
# 1. version.json anpassen (z.B. 1.4.0-rc1 für einen Test)
# 2. CHANGELOG.md Abschnitt ergänzen
# 3. Commit + Tag
git add version.json CHANGELOG.md
git commit -m "Release: v1.4.0"
git tag v1.4.0
git push origin main --tags
```

GitHub Actions unter **Actions** → **Release** beobachten.

---

## Workflow-Übersicht

```
git push --tags
    │
    ▼
[Job 1: test]        ubuntu-latest, ~2 Min
  ├─ ruff check
  └─ pytest tests/
    │ (muss grün sein)
    ▼
[Job 2: build]       windows-latest, ~10-15 Min
  ├─ .venv + pip install
  ├─ Signierschlüssel aus Secret schreiben
  ├─ python scripts/release.py --skip-tests
  │    ├─ PyInstaller → dist/MinGuataLada/
  │    ├─ SHA-256
  │    ├─ .mugala bauen + signieren
  │    ├─ manifest.json signieren
  │    └─ releases/ + deploy/ befüllen
  ├─ Artefakte als GitHub-Artifact speichern
  └─ Signierschlüssel aus Filesystem löschen
    │
    ▼
[Job 3: publish]     ubuntu-latest, ~1 Min
  ├─ GitHub Release erstellen mit EXE + .mugala + manifest.json
  └─ FTP Upload → schaer-systems.at/updates/ (manifest.json + .mugala)
```

---

## Nach dem Release

Benutzer können über **Admin → Einstellungen → Updates → Online prüfen**
das neue Update herunterladen und einspielen.

Das `.mugala` aus dem GitHub Release kann auch manuell auf einem anderen PC
über **Admin → Einstellungen → Updates → Datei importieren** eingespielt werden.
