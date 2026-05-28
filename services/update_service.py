"""
Update-Architektur – Vorbereitung für Software-Updates via .exe Upload (Anforderung 15).

Aktueller Stand:
  - Kein externer Webserver konfiguriert
  - API-Schnittstelle noch nicht aktiv
  - Architektur ist vollständig vorbereitet

Geplante Architektur:
  1. Manifest-Datei auf externem Server (JSON):
     { "version": "1.1.0", "url": "https://...", "sha256": "...", "release_notes": "..." }
  2. Client vergleicht lokale Version gegen Manifest
  3. Bei verfügbarem Update: Download + Signaturprüfung
  4. Installation via subprocess (aktuellen Prozess ersetzen)

Settings-Key: UPDATE_MANIFEST_URL (in settings-Tabelle konfigurierbar)
"""
import hashlib
import subprocess
from pathlib import Path
from typing import Optional

from app.config import DATA_DIR

# Aktuelle Versionsnummer der Applikation
APP_VERSION = "1.0.0"


class UpdateCheckResult:
    def __init__(self, available: bool, version: str = "", url: str = "", notes: str = "", error: str = ""):
        self.available = available
        self.version = version
        self.url = url
        self.release_notes = notes
        self.error = error


class UpdateService:
    """Software-Update-Mechanismus – aktuell architektonisch vorbereitet, kein Server konfiguriert."""

    MANIFEST_URL_SETTING_KEY = "UPDATE_MANIFEST_URL"
    DOWNLOAD_DIR = Path(DATA_DIR) / "updates"

    def __init__(self, settings_service=None):
        self.settings_service = settings_service

    def get_current_version(self) -> str:
        return APP_VERSION

    def get_manifest_url(self) -> Optional[str]:
        if self.settings_service:
            try:
                return self.settings_service.get_value(self.MANIFEST_URL_SETTING_KEY)
            except Exception:
                pass
        return None

    def check_for_updates(self) -> UpdateCheckResult:
        """
        Prüft ob eine neuere Version verfügbar ist.

        Aktuell: Kein Server → gibt immer "nicht verfügbar" zurück.
        Sobald UPDATE_MANIFEST_URL in den Einstellungen gesetzt wird, ist
        diese Funktion automatisch aktiv.
        """
        manifest_url = self.get_manifest_url()
        if not manifest_url:
            return UpdateCheckResult(
                available=False,
                error="Kein Update-Server konfiguriert. Bitte UPDATE_MANIFEST_URL in den Einstellungen setzen.",
            )

        try:
            import urllib.request, json
            with urllib.request.urlopen(manifest_url, timeout=10) as resp:
                manifest = json.loads(resp.read().decode())

            remote_version = manifest.get("version", "")
            if self._is_newer(remote_version, APP_VERSION):
                return UpdateCheckResult(
                    available=True,
                    version=remote_version,
                    url=manifest.get("url", ""),
                    notes=manifest.get("release_notes", ""),
                )
            return UpdateCheckResult(available=False, version=APP_VERSION)

        except Exception as e:
            return UpdateCheckResult(available=False, error=str(e))

    def download_update(self, url: str, expected_sha256: str = "") -> Path:
        """
        Lädt Update-Paket herunter und prüft Signatur.
        Wirft Exception wenn Download fehlschlägt oder Prüfsumme falsch ist.
        """
        import urllib.request
        self.DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
        filename = url.split("/")[-1]
        dest = self.DOWNLOAD_DIR / filename

        urllib.request.urlretrieve(url, dest)

        if expected_sha256:
            actual = hashlib.sha256(dest.read_bytes()).hexdigest()
            if actual != expected_sha256:
                dest.unlink(missing_ok=True)
                raise ValueError(f"Prüfsumme falsch: erwartet {expected_sha256}, erhalten {actual}")

        return dest

    def install_update(self, exe_path: Path) -> None:
        """
        Startet den neuen Installer und beendet die aktuelle Anwendung.
        Achtung: Beendet den aktuellen Prozess!
        """
        if not exe_path.exists():
            raise FileNotFoundError(f"Installer nicht gefunden: {exe_path}")
        subprocess.Popen([str(exe_path), "/SILENT"], creationflags=subprocess.DETACHED_PROCESS)
        import sys
        sys.exit(0)

    @staticmethod
    def _is_newer(remote: str, local: str) -> bool:
        try:
            r = tuple(int(x) for x in remote.split("."))
            l = tuple(int(x) for x in local.split("."))
            return r > l
        except Exception:
            return False
