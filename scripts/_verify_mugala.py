"""Verifikationsskript fuer .mugala-Pakete."""
import json
import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

pkg_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("dist/update_1.1.0.mugala")

from core.update_signing import verify_package_signature

with zipfile.ZipFile(str(pkg_path)) as zf:
    raw = zf.read("manifest.json").decode("utf-8")
    manifest = json.loads(raw)
    contents = zf.namelist()

ok, msg = verify_package_signature(manifest)
print(f"Datei:        {pkg_path}")
print(f"Signatur:     {'GUELTIG' if ok else 'UNGUELTIG'}")
if msg:
    print(f"Hinweis:      {msg}")
print(f"Version:      {manifest['version']}")
print(f"Min-Base:     {manifest['min_base_version']}")
print(f"Max-Base:     {manifest['max_base_version'] or '(kein Limit)'}")
print(f"Migrationen:  {manifest['migrations'] or '(keine)'}")
print(f"Inhalt:       {contents}")
