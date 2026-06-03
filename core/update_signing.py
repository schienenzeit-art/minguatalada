"""
Kryptografische Signaturprüfung für .mugala Update-Pakete.

Signaturverfahren : Ed25519 (modernes, schnelles Signaturverfahren)
Schlüsselformat   : Öffentlicher Schlüssel als Raw-Bytes, Base64url-kodiert (32 Byte)
Signiertes Objekt : Kanonisches JSON des Manifests (sortierte Keys, ohne 'signature'-Feld)

Schlüsselverwaltung:
  - Schlüsselpaar einmalig erzeugen:  python scripts/generate_signing_key.py
  - Öffentlichen Schlüssel in EMBEDDED_PUBLIC_KEY_B64 eintragen (dieses Modul)
  - Privaten Schlüssel NIEMALS committen (liegt in certs/ → .gitignore)
  - Bei Schlüsselrotation: alten Schlüssel nach LEGACY_PUBLIC_KEYS_B64 verschieben

Rückwärtskompatibilität:
  - Pakete ohne 'signature'-Feld → Warnung, aber akzeptiert (Transitional Mode)
  - Pakete mit ungültiger Signatur → strikt abgelehnt
  - Kein öffentlicher Schlüssel konfiguriert → alle Pakete akzeptiert (Dev-Modus)
"""

import base64
import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# ── Öffentliche Schlüssel ─────────────────────────────────────────────────────

# Aktueller öffentlicher Schlüssel (Base64url-kodiert, 32 Byte Ed25519 Raw).
# Leer = kein Schlüssel konfiguriert (Dev-Modus / vor erster Schlüsselgenerierung).
# Eintragen nach: python scripts/generate_signing_key.py
EMBEDDED_PUBLIC_KEY_B64: str = ""

# Frühere öffentliche Schlüssel — signierte Pakete dieser Schlüssel werden weiterhin akzeptiert.
# Hierher verschieben bei Schlüsselrotation.
LEGACY_PUBLIC_KEYS_B64: list[str] = []


# ── Interne Hilfsfunktionen ───────────────────────────────────────────────────

def _b64url_decode(s: str) -> bytes:
    """Base64url-Dekodierung mit automatischer Padding-Ergänzung."""
    padding = (4 - len(s) % 4) % 4
    return base64.urlsafe_b64decode(s + "=" * padding)


def _canonical_manifest_bytes(manifest_data: dict) -> bytes:
    """
    Kanonische JSON-Repräsentation des Manifests zum Signieren/Prüfen.
    Schlüssel werden alphabetisch sortiert; das 'signature'-Feld wird ausgeschlossen.
    """
    data = {k: v for k, v in manifest_data.items() if k != "signature"}
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


# ── Öffentliche API ───────────────────────────────────────────────────────────

def sign_manifest(manifest_data: dict, private_key_path: Path) -> str:
    """
    Signiert das Manifest mit dem angegebenen privaten Ed25519-Schlüssel (PEM).
    Gibt die Base64url-kodierte Signatur zurück (ohne Padding-Zeichen).
    """
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    from cryptography.hazmat.primitives.serialization import load_pem_private_key

    pem = private_key_path.read_bytes()
    private_key = load_pem_private_key(pem, password=None)
    if not isinstance(private_key, Ed25519PrivateKey):
        raise ValueError(
            f"'{private_key_path}' enthält keinen Ed25519-Schlüssel "
            f"(gefunden: {type(private_key).__name__})."
        )

    canonical = _canonical_manifest_bytes(manifest_data)
    sig_bytes = private_key.sign(canonical)
    return base64.urlsafe_b64encode(sig_bytes).decode("ascii").rstrip("=")


def verify_package_signature(manifest_data: dict) -> tuple[bool, str]:
    """
    Prüft die Signatur eines .mugala-Manifests.

    Rückgabe (ok: bool, meldung: str):
      (True,  "")                – Signatur gültig
      (True,  "Warnung: …")     – Kein Schlüssel / Signatur fehlt (Transitional Mode)
      (False, "Fehler: …")      – Signatur ungültig oder Paket manipuliert
    """
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
    from cryptography.exceptions import InvalidSignature

    signature_b64 = manifest_data.get("signature", "")

    # Fall 1: Kein öffentlicher Schlüssel konfiguriert → Dev-Modus
    if not EMBEDDED_PUBLIC_KEY_B64:
        if signature_b64:
            logger.warning(
                "Signatur im Paket vorhanden, aber kein oeffentlicher Schluessel "
                "konfiguriert (EMBEDDED_PUBLIC_KEY_B64 leer) — Signatur uebersprungen."
            )
        else:
            logger.debug("Kein Schluessel konfiguriert, kein Signature-Feld — Transitional Mode.")
        return True, "Kein Signaturschluessel konfiguriert (Transitional Mode)."

    # Fall 2: Schlüssel konfiguriert, aber Paket nicht signiert → Warnung, aber akzeptiert
    if not signature_b64:
        msg = (
            "Paket ist nicht signiert. Bitte ein aktuell mit "
            "scripts/build_mugala.py --sign erstelltes Paket verwenden."
        )
        logger.warning("Signaturpruefung: %s", msg)
        return True, f"Warnung: {msg}"

    # Fall 3: Signatur prüfen — aktueller + alle Legacy-Schlüssel
    canonical = _canonical_manifest_bytes(manifest_data)
    try:
        sig_bytes = _b64url_decode(signature_b64)
    except Exception as exc:
        return False, f"Fehler: Signatur-Feld ist kein gueltiges Base64url ({exc})."

    all_keys = [EMBEDDED_PUBLIC_KEY_B64] + LEGACY_PUBLIC_KEYS_B64
    for pub_key_b64 in all_keys:
        try:
            pub_raw = _b64url_decode(pub_key_b64)
            pub_key = Ed25519PublicKey.from_public_bytes(pub_raw)
            pub_key.verify(sig_bytes, canonical)
            logger.info("Signaturpruefung: Signatur gueltig.")
            return True, ""
        except InvalidSignature:
            continue
        except Exception as exc:
            logger.debug("Schluessel '%s...' ungueltig: %s", pub_key_b64[:8], exc)
            continue

    msg = (
        "Signatur ungueltig — das Paket wurde moeglicherweise manipuliert "
        "oder mit einem unbekannten Schluessel signiert."
    )
    logger.error("Signaturpruefung: %s", msg)
    return False, f"Fehler: {msg}"
