"""
Release-Pipeline fuer Min Guata Lada.

Entrypoint: release.bat  (oder direkt: python scripts/release.py)

Ablauf:
  [1] Preflight   – Versionsdatei, venv, Signierschlüssel
  [2] Tests       – pytest (273 Tests)
  [3] Build       – PyInstaller via anspruchssystem.spec
  [4] SHA-256     – Prüfsumme der EXE
  [5] .mugala     – Signiertes Update-Paket
  [6] Manifest    – Signiertes Server-Manifest (deploy/manifest.json)
  [7] Artefakte   – release/ und deploy/ befüllen

Ausgabe:
  release/
  ├── MinGuataLada.exe
  ├── update_{version}.mugala
  ├── manifest.json
  ├── CHANGELOG.txt
  └── VERSION.txt

  deploy/               ← per FTP/SSH auf web15.wh20.easyname.systems hochladen
  ├── manifest.json
  └── update_{version}.mugala

Argumente:
  --skip-tests    Tests ueberspringen (nützlich wenn CI bereits getestet hat)
  --skip-build    Bestehende EXE nutzen, kein neuer PyInstaller-Lauf
  --no-sign       Ohne Signatur (nur fuer lokale Tests, NICHT fuer Produktion)
  --dry-run       Simulieren, keine Dateien schreiben
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from datetime import date
from pathlib import Path

# ── Pfade ─────────────────────────────────────────────────────────────────────
ROOT         = Path(__file__).resolve().parent.parent
VENV_PYTHON  = ROOT / ".venv" / "Scripts" / "python.exe"
SPEC_FILE    = ROOT / "anspruchssystem.spec"
DIST_DIR     = ROOT / "dist" / "MinGuataLada"
EXE_PATH     = DIST_DIR / "MinGuataLada.exe"
VERSION_FILE = ROOT / "version.json"
CHANGELOG_MD = ROOT / "CHANGELOG.md"
RELEASE_DIR  = ROOT / "releases"
DEPLOY_DIR   = ROOT / "deploy"

MANIFEST_BASE_URL = "https://www.schaer-systems.at/updates"

# ── ANSI-Farben (funktionieren auf Windows 10+ und in modernen Terminals) ────
_G = "\033[92m"   # grün
_R = "\033[91m"   # rot
_Y = "\033[93m"   # gelb
_B = "\033[94m"   # blau
_W = "\033[1m"    # fett/weiß
_X = "\033[0m"    # reset


def _ok(msg: str) -> None:
    print(f"  {_G}[OK]{_X}  {msg}")


def _fail(msg: str) -> None:
    print(f"\n  {_R}[FEHLER]: {msg}{_X}\n", file=sys.stderr)
    sys.exit(1)


def _info(msg: str) -> None:
    print(f"  {_B}[>>]{_X}  {msg}")


def _step(n: int, label: str) -> None:
    print(f"\n{_W}[{n}/7] {label}{_X}")


# ── Hilfsfunktionen ───────────────────────────────────────────────────────────

def load_version_info() -> dict:
    if not VERSION_FILE.exists():
        _fail(f"version.json nicht gefunden: {VERSION_FILE}")
    return json.loads(VERSION_FILE.read_text(encoding="utf-8"))


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def extract_changelog(version: str) -> str:
    """Extrahiert den Changelog-Abschnitt der angegebenen Version aus CHANGELOG.md."""
    if not CHANGELOG_MD.exists():
        return f"Version {version}"
    lines = CHANGELOG_MD.read_text(encoding="utf-8").splitlines()
    in_section = False
    section: list[str] = []
    for line in lines:
        if line.startswith(f"## [{version}]"):
            in_section = True
            continue
        if in_section:
            if (line.startswith("## [") and not line.startswith(f"## [{version}]")) or line.strip() == "---":
                break
            section.append(line)
    return "\n".join(section).strip() or f"Version {version}"


def find_signing_key() -> Path | None:
    for candidate in [ROOT / "keys" / "private.pem", ROOT / "certs" / "mugala_signing.key"]:
        if candidate.exists():
            return candidate
    return None


def sign_manifest_data(manifest: dict, key_path: Path) -> str:
    sys.path.insert(0, str(ROOT))
    from core.update_signing import sign_manifest
    return sign_manifest(manifest, key_path)


# ── Pipeline-Schritte ─────────────────────────────────────────────────────────

def step_preflight(args: argparse.Namespace, ver: dict) -> Path | None:
    _step(1, "Preflight")

    version = ver["version"]
    _ok(f"Version: {_W}{version}{_X}")

    if not VENV_PYTHON.exists():
        _fail(f"Virtuelle Umgebung nicht gefunden: {VENV_PYTHON}\n"
              "       Bitte ausführen: python -m venv .venv && .venv\\Scripts\\pip install -r requirements.txt")
    _ok("Virtual environment vorhanden")

    if not SPEC_FILE.exists():
        _fail(f"anspruchssystem.spec nicht gefunden: {SPEC_FILE}")
    _ok("PyInstaller spec vorhanden")

    signing_key: Path | None = None
    if not args.no_sign:
        signing_key = find_signing_key()
        if signing_key:
            _ok(f"Signierschlüssel: {signing_key.relative_to(ROOT)}")
        else:
            _fail(
                "Kein Signierschlüssel gefunden.\n"
                "       Erwartet: keys/private.pem  oder  certs/mugala_signing.key\n"
                "       Schlüssel generieren: python scripts/generate_signing_key.py\n"
                "       Oder Release ohne Signatur: release.bat --no-sign"
            )
    else:
        print(f"  {_Y}[!]{_X}  Ohne Signatur (--no-sign) – NICHT fuer Produktion!")

    return signing_key


def step_tests(args: argparse.Namespace) -> None:
    _step(2, "Tests")
    if args.skip_tests:
        print(f"  {_Y}[!]{_X}  Tests uebersprungen (--skip-tests)")
        return

    if args.dry_run:
        _info("dry-run: pytest wuerde hier ausgefuehrt")
        return

    result = subprocess.run(
        [str(VENV_PYTHON), "-m", "pytest", "tests/", "-q", "--tb=short"],
        cwd=ROOT,
    )
    if result.returncode != 0:
        _fail("Tests fehlgeschlagen. Release abgebrochen.")
    _ok("Alle Tests grün")


def step_build(args: argparse.Namespace) -> Path:
    _step(3, "EXE bauen (PyInstaller)")
    if args.skip_build:
        if not EXE_PATH.exists():
            _fail(f"--skip-build gesetzt, aber EXE nicht gefunden: {EXE_PATH}")
        _ok(f"Bestehende EXE verwendet: {EXE_PATH.relative_to(ROOT)}")
        return EXE_PATH

    if args.dry_run:
        _info("dry-run: PyInstaller wuerde hier ausgefuehrt")
        return EXE_PATH

    # Alten Build bereinigen
    for d in [ROOT / "build", ROOT / "dist"]:
        if d.exists():
            shutil.rmtree(d)

    result = subprocess.run(
        [str(VENV_PYTHON), "-m", "PyInstaller", str(SPEC_FILE), "--noconfirm"],
        cwd=ROOT,
    )
    if result.returncode != 0:
        _fail("PyInstaller-Build fehlgeschlagen.")

    if not EXE_PATH.exists():
        _fail(f"EXE nach Build nicht gefunden: {EXE_PATH}")

    size_mb = round(EXE_PATH.stat().st_size / 1024 / 1024, 1)
    _ok(f"EXE erstellt: {EXE_PATH.relative_to(ROOT)} ({size_mb} MB)")
    return EXE_PATH


def step_sha256(exe_path: Path, dry_run: bool) -> str:
    _step(4, "SHA-256 Prüfsumme")
    if dry_run:
        checksum = "dry-run-placeholder-sha256"
        _info(f"dry-run: sha256 = {checksum}")
        return checksum
    checksum = sha256_file(exe_path)
    _ok(f"SHA-256: {checksum[:16]}…{checksum[-8:]}")
    return checksum


def step_mugala(
    exe_path: Path,
    ver: dict,
    signing_key: Path | None,
    dry_run: bool,
) -> tuple[Path, str]:
    """Erstellt das .mugala-Paket. Gibt (mugala_path, sha256_of_mugala) zurück."""
    _step(5, ".mugala-Paket")
    version = ver["version"]
    mugala_name = f"update_{version}.mugala"
    # Staging-Pfad ausserhalb von RELEASE_DIR, damit step_assemble RELEASE_DIR
    # neu aufbauen kann ohne die gerade erstellte Datei zu loeschen.
    mugala_path = ROOT / mugala_name

    if dry_run:
        _info(f"dry-run: {mugala_name} wuerde erstellt")
        return mugala_path, "dry-run-sha256"

    # Importiere build_mugala direkt
    sys.path.insert(0, str(ROOT / "scripts"))
    from build_mugala import build as build_mugala

    # Vollstaendiges dist-Verzeichnis packen (~36 MB komprimiert statt nur 7 MB EXE)
    dist_dir = ROOT / "dist" / "MinGuataLada"
    if not dist_dir.exists():
        _fail(f"dist-Verzeichnis nicht gefunden: {dist_dir}\nBitte zuerst: build.bat")
    build_mugala(dist_dir, mugala_path, signing_key)

    sha = sha256_file(mugala_path)
    size_mb = round(mugala_path.stat().st_size / 1024 / 1024, 1)
    _ok(f".mugala erstellt: {mugala_name} ({size_mb} MB)")
    _ok(f"SHA-256 (.mugala): {sha[:16]}…{sha[-8:]}")
    return mugala_path, sha


def step_server_manifest(
    ver: dict,
    mugala_sha256: str,
    changelog: str,
    signing_key: Path | None,
    dry_run: bool,
) -> dict:
    """Erstellt und signiert das Server-Manifest fuer https://www.schaer-systems.at/updates/"""
    _step(6, "Server-Manifest")
    version = ver["version"]

    manifest = {
        "version":          version,
        "release_date":     date.today().isoformat(),
        "mugala_url":       f"{MANIFEST_BASE_URL}/update_{version}.mugala",
        "sha256":           mugala_sha256,
        "min_base_version": ver.get("min_base_version", "1.0.0"),
        "changelog":        changelog,
        "requires_restart": True,
    }

    if signing_key and not dry_run:
        try:
            manifest["signature"] = sign_manifest_data(manifest, signing_key)
            _ok("Server-Manifest signiert")
        except Exception as exc:
            _fail(f"Signierung des Server-Manifests fehlgeschlagen: {exc}")
    elif dry_run:
        manifest["signature"] = "dry-run-signature"
        _info("dry-run: Server-Manifest signiert")
    else:
        print(f"  {_Y}!{_X}  Server-Manifest NICHT signiert")

    _ok(f"mugala_url: {manifest['mugala_url']}")
    return manifest


def step_assemble(
    ver: dict,
    exe_path: Path,
    mugala_path: Path,
    server_manifest: dict,
    changelog: str,
    dry_run: bool,
) -> None:
    """Befüllt release/ und deploy/ mit allen Artefakten."""
    _step(7, "Artefakte zusammenstellen")
    version = ver["version"]
    mugala_name = mugala_path.name

    if dry_run:
        _info("dry-run: release/ und deploy/ wuerden befüllt")
        return

    # ── release/ ──────────────────────────────────────────────────────────────
    if RELEASE_DIR.exists():
        shutil.rmtree(RELEASE_DIR)
    RELEASE_DIR.mkdir(parents=True)

    # EXE
    shutil.copy2(exe_path, RELEASE_DIR / exe_path.name)
    # .mugala
    shutil.copy2(mugala_path, RELEASE_DIR / mugala_name)
    # Server-Manifest
    manifest_bytes = json.dumps(server_manifest, ensure_ascii=False, indent=2).encode("utf-8")
    (RELEASE_DIR / "manifest.json").write_bytes(manifest_bytes)
    # VERSION.txt
    (RELEASE_DIR / "VERSION.txt").write_text(version, encoding="utf-8")
    # CHANGELOG.txt
    (RELEASE_DIR / "CHANGELOG.txt").write_text(changelog, encoding="utf-8")

    _ok(f"release/  [>>] {len(list(RELEASE_DIR.iterdir()))} Dateien")

    # ── deploy/ ───────────────────────────────────────────────────────────────
    if DEPLOY_DIR.exists():
        shutil.rmtree(DEPLOY_DIR)
    DEPLOY_DIR.mkdir(parents=True)

    shutil.copy2(RELEASE_DIR / "manifest.json", DEPLOY_DIR / "manifest.json")
    shutil.copy2(RELEASE_DIR / mugala_name, DEPLOY_DIR / mugala_name)

    _ok(f"deploy/   [>>] manifest.json + {mugala_name}")
    _info(f"Upload: SCP deploy/ [>>] web15.wh20.easyname.systems:/www/updates/")


# ── Einstiegspunkt ────────────────────────────────────────────────────────────

def main() -> None:
    # Windows ANSI aktivieren
    if sys.platform == "win32":
        import os
        os.system("")

    parser = argparse.ArgumentParser(
        description="Min Guata Lada Release-Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--skip-tests", action="store_true", help="Tests ueberspringen")
    parser.add_argument("--skip-build", action="store_true", help="Bestehende EXE verwenden")
    parser.add_argument("--no-sign",    action="store_true", help="Ohne Signatur (nicht fuer Produktion)")
    parser.add_argument("--dry-run",    action="store_true", help="Simulieren, keine Dateien schreiben")
    args = parser.parse_args()

    print(f"\n{_W}{'='*60}")
    print("  Min Guata Lada – Release-Pipeline")
    print(f"{'='*60}{_X}")

    ver = load_version_info()
    version = ver["version"]

    # Pipeline
    signing_key    = step_preflight(args, ver)
    step_tests(args)
    exe_path       = step_build(args)
    exe_sha256     = step_sha256(exe_path, args.dry_run)
    mugala_path, mugala_sha256 = step_mugala(exe_path, ver, signing_key, args.dry_run)
    changelog      = extract_changelog(version)
    server_manifest = step_server_manifest(ver, mugala_sha256, changelog, signing_key, args.dry_run)
    step_assemble(ver, exe_path, mugala_path, server_manifest, changelog, args.dry_run)

    # Zusammenfassung
    print(f"\n{_W}{'='*60}")
    print(f"  {_G}RELEASE ERFOLGREICH – v{version}{_X}{_W}")
    print(f"{'='*60}{_X}")
    print(f"  EXE:       {_W}releases/MinGuataLada.exe{_X}")
    print(f"  .mugala:   {_W}releases/update_{version}.mugala{_X}")
    print(f"  Manifest:  {_W}releases/manifest.json{_X}")
    print(f"\n  Deploy-Artefakte in: {_W}deploy/{_X}")
    print(f"  Server:  {_B}https://www.schaer-systems.at/updates/{_X}")
    print(f"\n  Nächste Schritte:")
    print(f"    1. deploy/ per FTP/SCP auf web15.wh20.easyname.systems hochladen")
    print(f"    2. In der App: Admin [>>] Updates [>>] Online prüfen")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
