"""
Erstellt ein .mugala Update-Paket (ZIP mit manifest.json + EXE).

Aufruf:
    python scripts/build_mugala.py <installer.exe> <ausgabe.mugala>
    python scripts/build_mugala.py <installer.exe> <ausgabe.mugala> --sign certs/mugala_signing.key

Version wird automatisch aus version.json gelesen.
Changelog wird automatisch aus CHANGELOG.md extrahiert.
"""
import json
import sys
import zipfile
from datetime import date
from pathlib import Path


# ── Projekt-Stamm ─────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent


def load_version() -> dict:
    """Liest version.json aus dem Projekt-Stamm."""
    path = PROJECT_ROOT / "version.json"
    if not path.exists():
        print("FEHLER: version.json nicht gefunden.", file=sys.stderr)
        sys.exit(1)
    return json.loads(path.read_text(encoding="utf-8"))


def extract_changelog(version: str) -> str:
    """Extrahiert den Changelog-Text der angegebenen Version aus CHANGELOG.md."""
    changelog_path = PROJECT_ROOT / "CHANGELOG.md"
    if not changelog_path.exists():
        return f"Version {version}"

    lines = changelog_path.read_text(encoding="utf-8").splitlines()
    in_section = False
    section_lines: list[str] = []

    for line in lines:
        if line.startswith(f"## [{version}]"):
            in_section = True
            continue
        if in_section:
            if line.startswith("## [") and not line.startswith(f"## [{version}]"):
                break
            if line.strip() == "---":
                break
            section_lines.append(line)

    text = "\n".join(section_lines).strip()
    # Markdown-Überschriften (###) entfernen, Bullet-Punkte beibehalten
    cleaned = []
    for line in text.splitlines():
        if line.startswith("###"):
            cleaned.append(line.lstrip("# ").strip() + ":")
        else:
            cleaned.append(line)
    return "\n".join(cleaned).strip() or f"Version {version}"


def build(
    installer_path: Path,
    output_path: Path,
    signing_key_path: Path | None = None,
    version_override: str | None = None,
) -> None:
    """
    Erstellt das .mugala-Paket.

    installer_path kann sein:
      - Verzeichnis (z.B. dist/MinGuataLada/) → komplettes Verzeichnis wird gepackt
      - Einzelne EXE-Datei                   → nur diese Datei wird gepackt
    """
    if not installer_path.exists():
        print(f"FEHLER: Pfad nicht gefunden: {installer_path}", file=sys.stderr)
        sys.exit(1)

    ver_info = load_version()
    version = version_override or ver_info["version"]
    min_base = ver_info.get("min_base_version", "1.0.0")
    changelog = extract_changelog(version)

    # Installer-Dateiname fuer das Manifest bestimmen
    if installer_path.is_dir():
        exe_name = "MinGuataLada.exe"
    else:
        exe_name = installer_path.name

    manifest: dict = {
        "version":          version,
        "min_base_version": min_base,
        "max_base_version": "",
        "installer_file":   exe_name,   # "" = kein Installer (nur Migrationen)
        "migrations":       [],
        "changelog":        changelog,
        "release_date":     date.today().isoformat(),
        "requires_restart": True,
    }

    # Signierung
    if signing_key_path:
        if not signing_key_path.exists():
            print(f"FEHLER: Signierschluessel nicht gefunden: {signing_key_path}", file=sys.stderr)
            sys.exit(1)
        try:
            sys.path.insert(0, str(PROJECT_ROOT))
            from core.update_signing import sign_manifest
            manifest["signature"] = sign_manifest(manifest, signing_key_path)
            print(f"  Signatur erstellt mit: {signing_key_path.name}")
        except Exception as exc:
            print(f"FEHLER beim Signieren: {exc}", file=sys.stderr)
            sys.exit(1)
    else:
        print("  Hinweis: Paket ohne Signatur (Transitional Mode).")

    # Manifest als UTF-8 ohne BOM
    manifest_bytes = json.dumps(manifest, ensure_ascii=False, indent=2).encode("utf-8")

    # ZIP → .mugala
    output_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = output_path.with_suffix(".zip")

    with zipfile.ZipFile(tmp, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("manifest.json", manifest_bytes)

        if installer_path.is_dir():
            # Vollstaendiges Verzeichnis packen: Dateipfade relativ zum Verzeichnis selbst,
            # damit sie im ZIP-Root landen (MinGuataLada.exe, _internal/...).
            all_files = [f for f in installer_path.rglob("*") if f.is_file()]
            total = len(all_files)
            for i, file in enumerate(all_files, 1):
                arc = file.relative_to(installer_path)
                zf.write(str(file), str(arc))
                if i % 50 == 0 or i == total:
                    print(f"  Packe: {i}/{total} Dateien ...", end="\r")
            print()
        else:
            zf.write(str(installer_path), installer_path.name)

    if output_path.exists():
        output_path.unlink()
    tmp.rename(output_path)

    # Verifikation
    with zipfile.ZipFile(output_path, "r") as zf:
        raw = zf.read("manifest.json")
        has_bom = raw[:3] == b"\xef\xbb\xbf"
        parsed = json.loads(raw.decode("utf-8-sig"))

    size_mb = round(output_path.stat().st_size / 1024 / 1024, 1)
    print(f"  Datei:    {output_path}")
    print(f"  Groesse:  {size_mb} MB")
    print(f"  Version:  {parsed['version']}")
    print(f"  BOM:      {'JA (Problem!)' if has_bom else 'NEIN - korrekt'}")
    print(f"  Signiert: {'JA' if 'signature' in parsed else 'NEIN'}")
    print(f"  EXE:      {exe_name}")


def _find_signing_key() -> Path | None:
    """Sucht den privaten Schlüssel in Standard-Speicherorten."""
    candidates = [
        PROJECT_ROOT / "keys" / "private.pem",
        PROJECT_ROOT / "certs" / "mugala_signing.key",
    ]
    for p in candidates:
        if p.exists():
            return p
    return None


def _parse_args() -> tuple[Path, Path, Path | None]:
    args = sys.argv[1:]
    signing_key: Path | None = None

    if "--sign" in args:
        idx = args.index("--sign")
        if idx + 1 >= len(args):
            print("FEHLER: --sign braucht einen Schlüssel-Pfad.", file=sys.stderr)
            sys.exit(1)
        signing_key = Path(args[idx + 1])
        args = args[:idx] + args[idx + 2:]

    if len(args) != 2:
        print(
            "Aufruf: python scripts/build_mugala.py <installer.exe> <ausgabe.mugala> [--sign <key>]",
            file=sys.stderr,
        )
        sys.exit(1)

    return Path(args[0]), Path(args[1]), signing_key


if __name__ == "__main__":
    installer, output, key = _parse_args()

    # Automatisch Schlüssel suchen wenn kein --sign angegeben
    if key is None:
        key = _find_signing_key()

    build(installer, output, key)
