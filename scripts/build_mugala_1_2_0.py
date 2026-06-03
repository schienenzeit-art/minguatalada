"""Einmaliges Skript: erstellt signiertes update_1.2.0.mugala (kein Installer, rein Code-Update)."""
import json
import zipfile
from datetime import date
from pathlib import Path

changelog = (
    "v1.2.0 - Sicherheits- und Qualitaetshärtung\n\n"
    "HAERTUNG:\n"
    "- WAL-Modus aktiviert (crash-sichere DB-Operationen)\n"
    "- Startup-Healthcheck beim App-Start (PRAGMA integrity_check)\n"
    "- Backup-Integritaetspruefung nach jeder Erstellung\n"
    "- Automatisches Safety-Backup vor jeder Wiederherstellung\n"
    "- Ed25519-Signaturen fuer Update-Pakete (rueckwaertskompatibel)\n\n"
    "NEUE FUNKTIONEN:\n"
    "- Autosave in Anspruchspruefung (alle 30s, Entwurf-Wiederherstellung)\n"
    "- Erfassungsmaske: responsive Fenstergroesse (85% Bildschirm)\n"
    "- Erfassungsmaske: Personenformular und Haushalt nebeneinander\n"
    "- Erfassungsmaske: E-Mail nicht mehr Pflichtfeld\n"
    "- Pensionist: optionale Erfassung von Haushaltsmitgliedern\n\n"
    "QUALITAETSSICHERUNG:\n"
    "- 58 neue Tests (215 Tests gesamt, alle gruen)"
)

manifest = {
    "version": "1.2.0",
    "min_base_version": "1.1.0",
    "max_base_version": "",
    "installer_file": "",
    "migrations": [],
    "changelog": changelog,
    "release_date": date.today().isoformat(),
    "requires_restart": True,
}

key_path = Path("certs/mugala_signing.key")
if key_path.exists():
    from core.update_signing import sign_manifest
    manifest["signature"] = sign_manifest(manifest, key_path)
    signed = True
else:
    print("WARNUNG: Kein Signierschluessel gefunden — Paket wird NICHT signiert.")
    signed = False

manifest_bytes = json.dumps(manifest, ensure_ascii=False, indent=2).encode("utf-8")

out = Path("dist/update_1.2.0.mugala")
out.parent.mkdir(parents=True, exist_ok=True)

with zipfile.ZipFile(str(out), "w", compression=zipfile.ZIP_DEFLATED) as zf:
    zf.writestr("manifest.json", manifest_bytes)

with zipfile.ZipFile(str(out), "r") as zf:
    raw = zf.read("manifest.json")
    parsed = json.loads(raw.decode("utf-8"))

print("=" * 55)
print(f"  update_1.2.0.mugala erstellt")
print("=" * 55)
print(f"  Datei:       {out.resolve()}")
print(f"  Groesse:     {round(out.stat().st_size / 1024, 1)} KB")
print(f"  Version:     {parsed['version']}")
print(f"  Signiert:    {'JA' if signed else 'NEIN'}")
print(f"  Migrationen: {parsed['migrations'] or '(keine)'}")
print(f"  Installer:   {parsed['installer_file'] or '(keiner - reines Code-Update)'}")
print("=" * 55)
print()
print("HINWEIS: Dieses Paket enthaelt keinen Installer.")
print("  Fuer ein vollstaendiges Deployment:")
print("  1. build.bat ausfuehren (EXE erstellen)")
print("  2. ISCC installer/setup.iss ausfuehren (Installer bauen)")
print("  3. python scripts/build_mugala.py 1.2.0 <installer.exe> dist/update_1.2.0_full.mugala --sign certs/mugala_signing.key")
