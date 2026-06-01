"""
Standalone-Skript: Benutzerhandbuch als PDF erzeugen.

Wird von build.bat aufgerufen:
    python scripts/generate_manual.py [Zielpfad.pdf]
"""
import sys
from pathlib import Path

# Projektstamm zum sys.path hinzufügen
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

def main():
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else PROJECT_ROOT / "Benutzerhandbuch.pdf"
    target.parent.mkdir(parents=True, exist_ok=True)

    # Temporär DATA_DIR auf Projektstamm zeigen lassen,
    # damit manual_service ohne laufende App funktioniert
    import app.config as cfg
    cfg.DATA_DIR = PROJECT_ROOT / "data"
    cfg.DATA_DIR.mkdir(parents=True, exist_ok=True)

    from services.manual_service import ManualService, MANUAL_PATH
    svc = ManualService()

    # Pfad überschreiben, damit die PDF am gewünschten Zielort landet
    svc._path = target
    svc.regenerate()
    print(f"Benutzerhandbuch erstellt: {target}")

if __name__ == "__main__":
    main()
