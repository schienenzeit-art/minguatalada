"""
Erstellt ein BOM-freies .mugala Update-Paket.
Aufruf: python scripts/build_mugala.py <version> <installer.exe> <ausgabe.mugala>
"""
import json
import sys
import zipfile
from datetime import date
from pathlib import Path


def build(version: str, installer_path: Path, output_path: Path) -> None:
    manifest = {
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

    # Sauberes UTF-8 OHNE BOM – json.dumps + encode("utf-8") schreibt nie BOM
    manifest_bytes = json.dumps(manifest, ensure_ascii=False, indent=2).encode("utf-8")

    tmp = output_path.with_suffix(".zip")
    with zipfile.ZipFile(tmp, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("manifest.json", manifest_bytes)
        zf.write(str(installer_path), installer_path.name)

    if output_path.exists():
        output_path.unlink()
    tmp.rename(output_path)

    # Prüfung
    with zipfile.ZipFile(output_path, "r") as zf:
        raw     = zf.read("manifest.json")
        has_bom = raw[:3] == b"\xef\xbb\xbf"
        parsed  = json.loads(raw.decode("utf-8-sig"))

    size_mb = round(output_path.stat().st_size / 1024 / 1024, 1)
    print(f"Datei:   {output_path}")
    print(f"Groesse: {size_mb} MB")
    print(f"Version: {parsed['version']}")
    print(f"BOM:     {'JA (Problem!)' if has_bom else 'NEIN – korrekt'}")
    print(f"Inhalt:  manifest.json + {installer_path.name}")


if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Aufruf: python build_mugala.py <version> <installer.exe> <ausgabe.mugala>")
        sys.exit(1)
    build(
        version       = sys.argv[1],
        installer_path= Path(sys.argv[2]),
        output_path   = Path(sys.argv[3]),
    )
