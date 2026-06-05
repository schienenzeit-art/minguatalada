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

    Args:
        installer_path:    Pfad zur EXE (MinGuataLada.exe)
        output_path:       Ziel-Pfad für das .mugala-Paket
        signing_key_path:  Optionaler Pfad zum privaten Ed25519-Schlüssel (PEM)
        version_override:  Optionale Versionsnummer (überschreibt version.json)
    """
    if not installer_path.exists():
        print(f"FEHLER: Installer nicht gefunden: {installer_path}", file=sys.stderr)
        sys.exit(1)

    ver_info = load_version()
    version = version_override or ver_info["version"]
    min_base = ver_info.get("min_base_version", "1.0.0")
    changelog = extract_changelog(version)

    manifest: dict = {
        "version":          version,
        "min_base_version": min_base,
        "max_base_version": "",
        "installer_file":   installer_path.name,
        "migrations":       [],
        "changelog":        changelog,
        "release_date":     date.today().isoformat(),
        "requires_restart": True,
    }

    # Signierung
    if signing_key_path:
        if not signing_key_path.exists():
            print(f"FEHLER: Signierschlüssel nicht gefunden: {signing_key_path}", file=sys.stderr)
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
    print(f"  Größe:    {size_mb} MB")
    print(f"  Version:  {parsed['version']}")
    print(f"  BOM:      {'JA (Problem!)' if has_bom else 'NEIN – korrekt'}")
    print(f"  Signiert: {'JA' if 'signature' in parsed else 'NEIN'}")
    print(f"  EXE:      {installer_path.name}")


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
