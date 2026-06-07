"""
Einstiegspunkt der Anwendung.

Beim Start wird geprüft ob die EXE als "Self-Replacement-Updater" aufgerufen wurde
(Argument --mgl-replace <zielverzeichnis>). Falls ja, kopiert sie sich selbst in das
Zielverzeichnis, startet sich von dort neu und beendet sich. Das stellt sicher, dass
nach einem .mugala-Update der Benutzer wieder aus dem ursprünglichen Installationsverzeichnis
startet und sein Desktop-Shortcut weiterhin funktioniert.
"""
from __future__ import annotations

import sys
from pathlib import Path


def _handle_self_replacement() -> None:
    """
    Selbst-Ersetzungs-Logik für .mugala-Updates auf anderem PC.

    Aufruf durch update_service.apply_update():
        MinGuataLada.exe --mgl-replace "C:\\Users\\...\\AppData\\Local\\MinGuataLada"

    Ablauf:
      1. Kurz warten (alter Prozess muss beendet sein)
      2. Eigenes Verzeichnis (UPDATES_DIR) → Zielverzeichnis kopieren
      3. Neue EXE aus Zielverzeichnis starten
      4. Diesen Prozess beenden
    """
    if "--mgl-replace" not in sys.argv:
        return

    idx = sys.argv.index("--mgl-replace")
    if idx + 1 >= len(sys.argv):
        return

    # Nur im gefrorenen (PyInstaller) Modus sinnvoll
    if not getattr(sys, "frozen", False):
        return

    import logging
    import shutil
    import subprocess
    import time

    target_dir = Path(sys.argv[idx + 1])
    source_dir = Path(sys.executable).parent

    # Gleiches Verzeichnis → kein Kopieren nötig, normal starten
    if source_dir.resolve() == target_dir.resolve():
        return

    log = logging.getLogger(__name__)
    log.info("Self-Replacement: %s → %s", source_dir, target_dir)

    # Warten bis der alte Prozess das Dateisystem freigegeben hat
    time.sleep(2)

    # Zielverzeichnis anlegen falls nötig
    target_dir.mkdir(parents=True, exist_ok=True)

    # Alle Dateien und Verzeichnisse kopieren (EXE + _internal/)
    copy_errors: list[str] = []
    for item in source_dir.iterdir():
        dest = target_dir / item.name
        try:
            if item.is_dir():
                if dest.exists():
                    shutil.rmtree(str(dest))
                shutil.copytree(str(item), str(dest))
            else:
                shutil.copy2(str(item), str(dest))
        except Exception as exc:
            copy_errors.append(f"{item.name}: {exc}")

    if copy_errors:
        # Teilweise fehlgeschlagen — aus UPDATES_DIR weiterarbeiten, nicht abstürzen
        log.warning("Self-Replacement teilweise fehlgeschlagen: %s", copy_errors)
        return

    # Neue EXE aus Zielverzeichnis starten
    new_exe = target_dir / Path(sys.executable).name
    if new_exe.exists():
        subprocess.Popen(  # noqa: S603
            [str(new_exe)],
            creationflags=subprocess.DETACHED_PROCESS,
        )
        sys.exit(0)
    else:
        log.error("Self-Replacement: Neue EXE nicht gefunden: %s", new_exe)


if __name__ == "__main__":
    _handle_self_replacement()
    from app.bootstrap import run_app
    run_app()
