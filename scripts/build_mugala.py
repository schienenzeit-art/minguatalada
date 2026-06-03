"""
Erstellt ein BOM-freies .mugala Update-Paket, optional mit Ed25519-Signatur.

Aufruf (ohne Signatur, Transitional Mode):
    python scripts/build_mugala.py <version> <installer.exe> <ausgabe.mugala>

Aufruf (mit Signatur, empfohlen ab v1.2):
    python scripts/build_mugala.py <version> <installer.exe> <ausgabe.mugala> --sign <schluessel.key>

Beispiel:
    python scripts/build_mugala.py 1.2.0 dist/MinGuataLada-Setup-1.2.0.exe out/update_1.2.0.mugala --sign certs/mugala_signing.key
"""
import json
import sys
import zipfile
from datetime import date
from pathlib import Path


def build(
    version: str,
    installer_path: Path,
    output_path: Path,
    signing_key_path: Path | None = None,
) -> None:
    manifest: dict = {
        "version":          version,
        "min_base_version": "1.0.0",
        "max_base_version": "",
        "installer_file":   installer_path.name,
        "migrations":       [],
        "changelog": (
            "- Bugfix: Absturz beim Start mit Nicht-Admin-Benutzer behoben\n"
            "  (AttributeError: UpdatePage hat kein Attribut _lbl_last_update)\n"
            "- Bugfix: manifest.json mit UTF-8 BOM wird nun korrekt gelesen\n"
            "  (Fehler: Unexpected UTF-8 BOM beim Einspielen von Updates)"
        ),
        "release_date":    date.today().isoformat(),
        "requires_restart": True,
    }

    # Ed25519-Signatur anhängen (falls Schlüssel angegeben)
    if signing_key_path:
        if not signing_key_path.exists():
            print(f"FEHLER: Signierschluessel nicht gefunden: {signing_key_path}")
            sys.exit(1)
        try:
            from core.update_signing import sign_manifest
            manifest["signature"] = sign_manifest(manifest, signing_key_path)
            print(f"Signatur: erstellt mit {signing_key_path.name}")
        except ImportError:
            print("FEHLER: core.update_signing nicht gefunden — Skript vom Projektstamm ausfuehren.")
            sys.exit(1)
        except Exception as exc:
            print(f"FEHLER beim Signieren: {exc}")
            sys.exit(1)
    else:
        print("Hinweis: Paket wird OHNE Signatur erstellt (Transitional Mode).")
        print("         Empfohlen: --sign certs/mugala_signing.key")

    # Sauberes UTF-8 OHNE BOM
    manifest_bytes = json.dumps(manifest, ensure_ascii=False, indent=2).encode("utf-8")

    tmp = output_path.with_suffix(".zip")
    with zipfile.ZipFile(tmp, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("manifest.json", manifest_bytes)
        zf.write(str(installer_path), installer_path.name)

    if output_path.exists():
        output_path.unlink()
    tmp.rename(output_path)

    # Verifikation
    with zipfile.ZipFile(output_path, "r") as zf:
        raw     = zf.read("manifest.json")
        has_bom = raw[:3] == b"\xef\xbb\xbf"
        parsed  = json.loads(raw.decode("utf-8-sig"))

    size_mb = round(output_path.stat().st_size / 1024 / 1024, 1)
    print(f"Datei:     {output_path}")
    print(f"Groesse:   {size_mb} MB")
    print(f"Version:   {parsed['version']}")
    print(f"BOM:       {'JA (Problem!)' if has_bom else 'NEIN – korrekt'}")
    print(f"Signiert:  {'JA' if 'signature' in parsed else 'NEIN'}")
    print(f"Inhalt:    manifest.json + {installer_path.name}")


def _parse_args() -> tuple[str, Path, Path, Path | None]:
    """Parst Kommandozeilenargumente."""
    args = sys.argv[1:]
    signing_key: Path | None = None

    # --sign <pfad> herausfiltern
    if "--sign" in args:
        idx = args.index("--sign")
        if idx + 1 >= len(args):
            print("FEHLER: --sign braucht einen Schluessel-Pfad als Argument.")
            sys.exit(1)
        signing_key = Path(args[idx + 1])
        args = args[:idx] + args[idx + 2:]

    if len(args) != 3:
        print("Aufruf: python build_mugala.py <version> <installer.exe> <ausgabe.mugala> [--sign <schluessel.key>]")
        sys.exit(1)

    return args[0], Path(args[1]), Path(args[2]), signing_key


if __name__ == "__main__":
    version, installer_path, output_path, signing_key_path = _parse_args()
    build(version, installer_path, output_path, signing_key_path)
