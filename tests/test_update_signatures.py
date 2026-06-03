"""
Tests für Ed25519-Signaturprüfung von .mugala Update-Paketen (Priorität 1).

Testet:
  - Gültige Signatur wird akzeptiert
  - Ungültige / manipulierte Signatur wird abgelehnt
  - Fehlendes Signature-Feld → Warnung, aber akzeptiert (Transitional Mode)
  - Kein öffentlicher Schlüssel konfiguriert → alles akzeptiert (Dev-Modus)
  - validate_package() integriert die Signaturprüfung korrekt
  - Bestehende unsignierte .mugala-Pakete funktionieren weiterhin

Marker: @pytest.mark.slow (erzeugt Dateien, kryptografische Operationen)
"""
import base64
import json
import zipfile
from pathlib import Path

import pytest

pytestmark = pytest.mark.slow


# ── Test-Schlüsselpaar (in-memory, kein fester Key im Repository) ─────────────

@pytest.fixture(scope="module")
def test_keypair(tmp_path_factory):
    """
    Erzeugt ein frisches Ed25519-Schlüsselpaar für alle Tests in diesem Modul.
    scope=module → wird einmal pro Testlauf erzeugt, nicht pro Test.
    """
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    from cryptography.hazmat.primitives.serialization import (
        Encoding, NoEncryption, PrivateFormat, PublicFormat,
    )

    key_dir = tmp_path_factory.mktemp("keys")
    private_key = Ed25519PrivateKey.generate()
    public_key = private_key.public_key()

    # Privater Schlüssel als PEM-Datei (wie in der Produktion)
    pem = private_key.private_bytes(
        encoding=Encoding.PEM,
        format=PrivateFormat.PKCS8,
        encryption_algorithm=NoEncryption(),
    )
    key_path = key_dir / "test_signing.key"
    key_path.write_bytes(pem)

    # Öffentlicher Schlüssel als Base64url-String
    pub_raw = public_key.public_bytes(Encoding.Raw, PublicFormat.Raw)
    pub_b64 = base64.urlsafe_b64encode(pub_raw).decode("ascii").rstrip("=")

    return {"key_path": key_path, "pub_b64": pub_b64}


@pytest.fixture()
def sample_manifest() -> dict:
    """Minimales gültiges Manifest ohne Signatur."""
    return {
        "version": "99.9.9",
        "min_base_version": "0.0.1",
        "migrations": [],
        "changelog": "Testupdate",
        "release_date": "2026-06-01",
        "requires_restart": True,
    }


@pytest.fixture()
def signed_mugala(tmp_path, test_keypair, sample_manifest) -> Path:
    """Erstellt ein signiertes .mugala-Paket."""
    from core.update_signing import sign_manifest

    manifest = dict(sample_manifest)
    manifest["signature"] = sign_manifest(manifest, test_keypair["key_path"])
    manifest_bytes = json.dumps(manifest, ensure_ascii=False, indent=2).encode("utf-8")

    pkg = tmp_path / "update_signed.mugala"
    with zipfile.ZipFile(pkg, "w") as zf:
        zf.writestr("manifest.json", manifest_bytes)
        # Dummy-Installer (kein echtes Setup notwendig für Signaturtest)
        zf.writestr("dummy_installer.exe", b"MZ" + b"\x00" * 64)
    return pkg


@pytest.fixture()
def unsigned_mugala(tmp_path, sample_manifest) -> Path:
    """Erstellt ein unsigniertes .mugala-Paket (Altformat)."""
    manifest_bytes = json.dumps(sample_manifest, ensure_ascii=False, indent=2).encode("utf-8")
    pkg = tmp_path / "update_unsigned.mugala"
    with zipfile.ZipFile(pkg, "w") as zf:
        zf.writestr("manifest.json", manifest_bytes)
        zf.writestr("dummy_installer.exe", b"MZ" + b"\x00" * 64)
    return pkg


# ── Unit-Tests: core.update_signing ──────────────────────────────────────────

class TestSignManifest:
    def test_sign_produces_base64url_string(self, test_keypair, sample_manifest):
        from core.update_signing import sign_manifest
        sig = sign_manifest(sample_manifest, test_keypair["key_path"])
        assert isinstance(sig, str)
        assert len(sig) > 0
        # Ed25519-Signatur ist 64 Byte → 86 Base64url-Zeichen ohne Padding
        assert len(sig) == 86

    def test_sign_is_deterministic_per_key_but_unique_per_content(
        self, test_keypair, sample_manifest
    ):
        from core.update_signing import sign_manifest
        sig1 = sign_manifest(sample_manifest, test_keypair["key_path"])
        sig2 = sign_manifest(sample_manifest, test_keypair["key_path"])
        # Ed25519 ist deterministisch (kein Zufallsfaktor in der Signatur selbst)
        assert sig1 == sig2

    def test_different_content_different_signature(self, test_keypair, sample_manifest):
        from core.update_signing import sign_manifest
        sig1 = sign_manifest(sample_manifest, test_keypair["key_path"])
        manifest2 = dict(sample_manifest, version="98.0.0")
        sig2 = sign_manifest(manifest2, test_keypair["key_path"])
        assert sig1 != sig2

    def test_sign_excludes_signature_field_from_canonical(self, test_keypair, sample_manifest):
        """Signatur darf nicht von sich selbst abhängen (kein Zirkelschluss)."""
        from core.update_signing import sign_manifest, _canonical_manifest_bytes
        manifest_with_sig = dict(sample_manifest, signature="alte_signatur")
        canonical = _canonical_manifest_bytes(manifest_with_sig)
        assert b"signature" not in canonical

    def test_wrong_key_type_raises(self, tmp_path, sample_manifest):
        """Nicht-Ed25519-Schlüssel muss ValueError auslösen."""
        from cryptography.hazmat.primitives.asymmetric.rsa import generate_private_key
        from cryptography.hazmat.primitives.serialization import (
            Encoding, NoEncryption, PrivateFormat,
        )
        from core.update_signing import sign_manifest

        rsa_key = generate_private_key(65537, 2048)
        pem = rsa_key.private_bytes(Encoding.PEM, PrivateFormat.PKCS8, NoEncryption())
        rsa_path = tmp_path / "rsa.key"
        rsa_path.write_bytes(pem)

        with pytest.raises(ValueError, match="Ed25519"):
            sign_manifest(sample_manifest, rsa_path)


class TestVerifyPackageSignature:
    def test_valid_signature_accepted(self, test_keypair, sample_manifest, monkeypatch):
        """Gültige Signatur muss akzeptiert werden."""
        from core.update_signing import sign_manifest
        import core.update_signing as mod
        monkeypatch.setattr(mod, "EMBEDDED_PUBLIC_KEY_B64", test_keypair["pub_b64"])

        manifest = dict(sample_manifest)
        manifest["signature"] = sign_manifest(manifest, test_keypair["key_path"])

        from core.update_signing import verify_package_signature
        ok, msg = verify_package_signature(manifest)
        assert ok is True
        assert msg == ""

    def test_manipulated_manifest_rejected(self, test_keypair, sample_manifest, monkeypatch):
        """Nach Manipulation des Manifests muss die Signatur als ungültig erkannt werden."""
        from core.update_signing import sign_manifest
        import core.update_signing as mod
        monkeypatch.setattr(mod, "EMBEDDED_PUBLIC_KEY_B64", test_keypair["pub_b64"])

        manifest = dict(sample_manifest)
        manifest["signature"] = sign_manifest(manifest, test_keypair["key_path"])

        # Inhalt manipulieren (Angreifer ändert Version)
        manifest["version"] = "999.0.0"

        from core.update_signing import verify_package_signature
        ok, msg = verify_package_signature(manifest)
        assert ok is False
        assert "ungueltig" in msg.lower() or "manipuliert" in msg.lower() or "fehler" in msg.lower()

    def test_wrong_signature_rejected(self, test_keypair, sample_manifest, monkeypatch):
        """Falsche Signatur (zufällige Bytes) muss abgelehnt werden."""
        import core.update_signing as mod
        monkeypatch.setattr(mod, "EMBEDDED_PUBLIC_KEY_B64", test_keypair["pub_b64"])

        manifest = dict(sample_manifest)
        manifest["signature"] = base64.urlsafe_b64encode(b"x" * 64).decode().rstrip("=")

        from core.update_signing import verify_package_signature
        ok, msg = verify_package_signature(manifest)
        assert ok is False

    def test_no_signature_field_accepted_with_warning(self, test_keypair, sample_manifest, monkeypatch):
        """Paket ohne Signatur-Feld → akzeptiert mit Warnung (Rückwärtskompatibilität)."""
        import core.update_signing as mod
        monkeypatch.setattr(mod, "EMBEDDED_PUBLIC_KEY_B64", test_keypair["pub_b64"])

        from core.update_signing import verify_package_signature
        ok, msg = verify_package_signature(sample_manifest)  # kein 'signature'-Feld
        assert ok is True
        assert "Warnung" in msg

    def test_no_public_key_configured_accepts_everything(self, sample_manifest, monkeypatch):
        """Dev-Modus: kein öffentlicher Schlüssel → alle Pakete akzeptiert."""
        import core.update_signing as mod
        monkeypatch.setattr(mod, "EMBEDDED_PUBLIC_KEY_B64", "")

        from core.update_signing import verify_package_signature
        # Ohne Signatur
        ok, _ = verify_package_signature(sample_manifest)
        assert ok is True

        # Mit zufälliger (ungültiger) Signatur — trotzdem akzeptiert weil kein Schlüssel
        manifest_with_sig = dict(sample_manifest, signature="invalide_signatur")
        ok, _ = verify_package_signature(manifest_with_sig)
        assert ok is True

    def test_invalid_base64_signature_rejected(self, test_keypair, sample_manifest, monkeypatch):
        """Kaputte Base64-Kodierung muss abgelehnt werden."""
        import core.update_signing as mod
        monkeypatch.setattr(mod, "EMBEDDED_PUBLIC_KEY_B64", test_keypair["pub_b64"])

        manifest = dict(sample_manifest, signature="!!! kein valides base64url !!!")

        from core.update_signing import verify_package_signature
        ok, msg = verify_package_signature(manifest)
        assert ok is False

    def test_legacy_key_still_validates(self, tmp_path, sample_manifest, monkeypatch):
        """Pakete, die mit einem Legacy-Schlüssel signiert wurden, müssen weiter akzeptiert werden."""
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
        from cryptography.hazmat.primitives.serialization import (
            Encoding, NoEncryption, PrivateFormat, PublicFormat,
        )
        from core.update_signing import sign_manifest

        # Altes Schlüsselpaar (wird zu Legacy)
        old_key = Ed25519PrivateKey.generate()
        old_pub_raw = old_key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)
        old_pub_b64 = base64.urlsafe_b64encode(old_pub_raw).decode().rstrip("=")
        old_pem = old_key.private_bytes(Encoding.PEM, PrivateFormat.PKCS8, NoEncryption())
        old_key_path = tmp_path / "old.key"
        old_key_path.write_bytes(old_pem)

        # Neues Schlüsselpaar (aktuell)
        new_key = Ed25519PrivateKey.generate()
        new_pub_raw = new_key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)
        new_pub_b64 = base64.urlsafe_b64encode(new_pub_raw).decode().rstrip("=")

        # Manifest mit altem Schlüssel signieren
        manifest = dict(sample_manifest)
        manifest["signature"] = sign_manifest(manifest, old_key_path)

        import core.update_signing as mod
        monkeypatch.setattr(mod, "EMBEDDED_PUBLIC_KEY_B64", new_pub_b64)
        monkeypatch.setattr(mod, "LEGACY_PUBLIC_KEYS_B64", [old_pub_b64])

        from core.update_signing import verify_package_signature
        ok, msg = verify_package_signature(manifest)
        assert ok is True, f"Legacy-Schlüssel hätte Paket akzeptieren sollen: {msg}"


# ── Integrationstests: validate_package() mit Signaturprüfung ────────────────

class TestValidatePackageWithSignature:
    @pytest.fixture()
    def update_svc(self, db, tmp_path, monkeypatch):
        """UpdateService mit isolierten Verzeichnissen."""
        import services.update_service as usmod
        monkeypatch.setattr(usmod, "BACKUPS_DIR", tmp_path / "backups")
        monkeypatch.setattr(usmod, "UPDATES_DIR", tmp_path / "updates")
        from services.update_service import UpdateService
        return UpdateService()

    def test_signed_package_passes_validation(
        self, update_svc, signed_mugala, test_keypair, monkeypatch
    ):
        """validate_package() akzeptiert ein korrekt signiertes Paket."""
        import core.update_signing as mod
        monkeypatch.setattr(mod, "EMBEDDED_PUBLIC_KEY_B64", test_keypair["pub_b64"])

        ok, msg, manifest = update_svc.validate_package(signed_mugala)
        assert ok is True, f"Gültiges Paket wurde abgelehnt: {msg}"
        assert manifest is not None

    def test_unsigned_package_accepted_with_transitional_mode(
        self, update_svc, unsigned_mugala, test_keypair, monkeypatch
    ):
        """Unsigniertes Paket → Warnung, aber validate_package() gibt ok=True zurück."""
        import core.update_signing as mod
        monkeypatch.setattr(mod, "EMBEDDED_PUBLIC_KEY_B64", test_keypair["pub_b64"])

        ok, msg, manifest = update_svc.validate_package(unsigned_mugala)
        # Rückwärtskompatibilität: unsignierte Pakete laufen durch (Transitional Mode)
        assert ok is True, f"Unsigniertes Paket wurde abgelehnt (Transitional Mode verletzt): {msg}"

    def test_manipulated_package_rejected_by_validate(
        self, tmp_path, update_svc, test_keypair, sample_manifest, monkeypatch
    ):
        """Manipuliertes Paket muss von validate_package() abgelehnt werden."""
        from core.update_signing import sign_manifest
        import core.update_signing as mod
        monkeypatch.setattr(mod, "EMBEDDED_PUBLIC_KEY_B64", test_keypair["pub_b64"])

        # Paket signieren
        manifest = dict(sample_manifest)
        manifest["signature"] = sign_manifest(manifest, test_keypair["key_path"])

        # Manifest manipulieren (nach dem Signieren)
        manifest["version"] = "999.0.0"
        manifest_bytes = json.dumps(manifest, ensure_ascii=False, indent=2).encode("utf-8")

        pkg = tmp_path / "tampered.mugala"
        with zipfile.ZipFile(pkg, "w") as zf:
            zf.writestr("manifest.json", manifest_bytes)
            zf.writestr("dummy_installer.exe", b"MZ" + b"\x00" * 64)

        ok, msg, _ = update_svc.validate_package(pkg)
        assert ok is False, "Manipuliertes Paket hätte abgelehnt werden müssen."

    def test_no_public_key_unsigned_package_passes(
        self, update_svc, unsigned_mugala, monkeypatch
    ):
        """Dev-Modus: kein Schlüssel konfiguriert → unsigniertes Paket wird akzeptiert."""
        import core.update_signing as mod
        monkeypatch.setattr(mod, "EMBEDDED_PUBLIC_KEY_B64", "")

        ok, msg, manifest = update_svc.validate_package(unsigned_mugala)
        assert ok is True, f"Paket im Dev-Modus abgelehnt: {msg}"
