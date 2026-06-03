"""
Unit-Tests für PasswordService: bcrypt-Hashing, Verifikation, Zufallspasswörter.

Reine Unit-Tests, keine DB.
"""
import pytest

from services.password_service import PasswordService

pytestmark = pytest.mark.unit


def test_hash_und_verify_konsistent():
    pw = "MeinSicheresPasswort2026!"
    hashed = PasswordService.hash_password(pw)
    assert PasswordService.verify_password(pw, hashed)


def test_falsches_passwort_schlaegt_fehl():
    hashed = PasswordService.hash_password("korrekt")
    assert not PasswordService.verify_password("falsch", hashed)


def test_leerer_hash_gibt_false():
    assert not PasswordService.verify_password("irgendwas", "")


def test_hash_ist_bcrypt_format():
    hashed = PasswordService.hash_password("test")
    assert hashed.startswith("$2b$") or hashed.startswith("$2a$")


def test_gleiche_passwoerter_erzeugen_verschiedene_hashes():
    """Bcrypt ist salted — zwei Hashes desselben PW müssen verschieden sein."""
    pw = "gleiches_passwort"
    h1 = PasswordService.hash_password(pw)
    h2 = PasswordService.hash_password(pw)
    assert h1 != h2
    # Aber beide müssen verifizieren
    assert PasswordService.verify_password(pw, h1)
    assert PasswordService.verify_password(pw, h2)


def test_zufallspasswort_hat_mindestlaenge():
    pw = PasswordService.generate_random_password()
    assert len(pw) >= 16


def test_zufallspasswort_individuell():
    """Zwei zufällige Passwörter sollen unterschiedlich sein."""
    pw1 = PasswordService.generate_random_password()
    pw2 = PasswordService.generate_random_password()
    assert pw1 != pw2


def test_zufallspasswort_laenge_konfigurierbar():
    pw = PasswordService.generate_random_password(length=24)
    assert len(pw) == 24


def test_hash_zeichenlaenge_plausibel():
    """Bcrypt-Hashes haben exakt 60 Zeichen."""
    hashed = PasswordService.hash_password("test")
    assert len(hashed) == 60


@pytest.mark.parametrize("sonderzeichen_pw", [
    "Passwort!@#$%",
    "Ümläüte&Sonderzeichen",
    "   leerzeichen   ",
    "emoji😀passwort",
])
def test_sonderzeichen_im_passwort(sonderzeichen_pw):
    hashed = PasswordService.hash_password(sonderzeichen_pw)
    assert PasswordService.verify_password(sonderzeichen_pw, hashed)
