"""
Generiert ein Ed25519-Schlüsselpaar für die Signierung von .mugala Update-Paketen.

Aufruf:
    python scripts/generate_signing_key.py [ausgabe-verzeichnis]
    python scripts/generate_signing_key.py certs/

Erzeugte Dateien:
    certs/mugala_signing.key   – Privater Schlüssel (PEM, NIEMALS committen!)
    certs/mugala_signing.pub   – Öffentlicher Schlüssel (Base64url, zum Einbetten)

Nach der Generierung:
    1. Öffentlichen Schlüssel in core/update_signing.py eintragen:
           EMBEDDED_PUBLIC_KEY_B64 = "<ausgabe>"
    2. certs/mugala_signing.key in .gitignore aufnehmen (oder sicher aufbewahren)
    3. Pakete mit build_mugala.py --sign certs/mugala_signing.key signieren
"""

import base64
import sys
from pathlib import Path


def main() -> None:
    try:
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
        from cryptography.hazmat.primitives.serialization import (
            Encoding,
            NoEncryption,
            PrivateFormat,
            PublicFormat,
        )
    except ImportError:
        print("FEHLER: 'cryptography' nicht installiert.")
        print("Bitte ausfuehren: pip install cryptography")
        sys.exit(1)

    output_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("certs")
    output_dir.mkdir(parents=True, exist_ok=True)

    key_path = output_dir / "mugala_signing.key"
    pub_path = output_dir / "mugala_signing.pub"

    if key_path.exists():
        print(f"WARNUNG: {key_path} existiert bereits.")
        print("Loeschen Sie die Datei manuell, wenn ein neuer Schluessel benoetigt wird.")
        print("ACHTUNG: Damit verlieren bereits signierte Pakete ihre Gueltigkeit,")
        print("         sofern der alte Schluessel nicht in LEGACY_PUBLIC_KEYS_B64 eingetragen wird.")
        sys.exit(1)

    # Ed25519-Schlüsselpaar generieren
    private_key = Ed25519PrivateKey.generate()
    public_key = private_key.public_key()

    # Privaten Schlüssel als PKCS8-PEM speichern
    pem = private_key.private_bytes(
        encoding=Encoding.PEM,
        format=PrivateFormat.PKCS8,
        encryption_algorithm=NoEncryption(),
    )
    key_path.write_bytes(pem)
    try:
        key_path.chmod(0o600)
    except Exception:
        pass  # chmod nicht auf Windows verfügbar

    # Öffentlichen Schlüssel als Base64url speichern (ohne Padding)
    pub_raw = public_key.public_bytes(Encoding.Raw, PublicFormat.Raw)
    pub_b64 = base64.urlsafe_b64encode(pub_raw).decode("ascii").rstrip("=")
    pub_path.write_text(pub_b64 + "\n", encoding="utf-8")

    print("=" * 60)
    print("  Ed25519-Schluessel generiert")
    print("=" * 60)
    print(f"  Privater Schluessel : {key_path}")
    print(f"  Oeffentlicher Schluessel : {pub_path}")
    print()
    print("  Oeffentlicher Schluessel (Base64url):")
    print(f"  {pub_b64}")
    print()
    print("  Naechste Schritte:")
    print("  1. Oeffentlichen Schluessel in core/update_signing.py eintragen:")
    print(f'     EMBEDDED_PUBLIC_KEY_B64 = "{pub_b64}"')
    print()
    print("  2. certs/mugala_signing.key NIEMALS committen!")
    print("     Sichern Sie den privaten Schluessel an einem sicheren Ort.")
    print()
    print("  3. Pakete mit Signatur erstellen:")
    print("     python scripts/build_mugala.py <version> <installer.exe> <ausgabe.mugala> --sign certs/mugala_signing.key")
    print("=" * 60)


if __name__ == "__main__":
    main()
