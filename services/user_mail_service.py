"""Persönlicher Mailversand pro Benutzer.

Jeder Benutzer kann sein eigenes SMTP-Konto konfigurieren.
Fallback auf das globale System-SMTP wenn kein persönliches Konto vorhanden.
"""
import re
import smtplib
import ssl
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

from core.session import Session
from database.repositories.user_mail_config_repository import UserMailConfigRepository

_DEFAULT_SIGNATURE = """\
<br><br>
<hr style="border:none;border-top:1px solid #ddd;margin:16px 0;">
<table style="font-family:Arial,sans-serif;font-size:12px;color:#444;line-height:1.6;">
<tr><td>
  <strong>Verein Tischlein Deck Dich Vorarlberg</strong><br>
  Ladritschweg 10c · 6773 Vandans<br>
  <a href="mailto:info@tischleindeckdich-vbg.at" style="color:#4a90d9;text-decoration:none;">
    info@tischleindeckdich-vbg.at
  </a>
</td></tr>
</table>"""


class UserMailService:
    """Mailversand über das persönliche Konto des angemeldeten Benutzers."""

    def __init__(self, repo: UserMailConfigRepository | None = None):
        self.repo = repo or UserMailConfigRepository()

    def get_config(self, user_id: int | None = None) -> dict | None:
        """Gibt Mailkonfiguration des Benutzers oder None wenn keine hinterlegt."""
        uid = user_id or Session.get_user_id()
        if not uid:
            return None
        return self.repo.get_for_user(uid)

    def is_configured(self, user_id: int | None = None) -> bool:
        cfg = self.get_config(user_id)
        return bool(cfg and cfg.get("smtp_host") and cfg.get("from_email"))

    def save_config(self, data: dict, user_id: int | None = None) -> None:
        uid = user_id or Session.get_user_id()
        if not uid:
            raise ValueError("Kein Benutzer angemeldet.")
        self.repo.upsert(uid, data)

    def test_connection(self, user_id: int | None = None) -> tuple[bool, str]:
        """Testet die persönliche SMTP-Verbindung."""
        cfg = self.get_config(user_id)
        if not cfg:
            return False, "Kein persönliches Mailkonto konfiguriert."
        try:
            ctx = ssl.create_default_context()
            if cfg.get("use_tls", True):
                with smtplib.SMTP(cfg["smtp_host"], cfg.get("smtp_port", 587), timeout=10) as srv:
                    srv.ehlo()
                    srv.starttls(context=ctx)
                    if cfg.get("smtp_user") and cfg.get("smtp_password"):
                        srv.login(cfg["smtp_user"], cfg["smtp_password"])
            else:
                with smtplib.SMTP_SSL(cfg["smtp_host"], cfg.get("smtp_port", 465),
                                       context=ctx, timeout=10) as srv:
                    if cfg.get("smtp_user") and cfg.get("smtp_password"):
                        srv.login(cfg["smtp_user"], cfg["smtp_password"])
            return True, "Verbindung erfolgreich."
        except Exception as exc:
            return False, str(exc)

    def send_html_mail(
        self,
        to_email: str,
        subject: str,
        html_body: str,
        attachments: list[str] | None = None,
        user_id: int | None = None,
    ) -> None:
        """Sendet eine HTML-Mail über das persönliche Konto des Benutzers."""
        cfg = self.get_config(user_id)

        # Fallback auf globales SMTP
        if not cfg or not cfg.get("smtp_host"):
            from services.mail_service import MailService
            MailService().send_html_mail(to_email, subject, html_body, attachments)
            return

        signature = cfg.get("signature_html") or _DEFAULT_SIGNATURE
        from_addr = cfg["from_email"]
        from_name = cfg.get("from_name", "") or ""

        msg = MIMEMultipart("mixed")
        msg["From"]    = f"{from_name} <{from_addr}>" if from_name else from_addr
        msg["To"]      = to_email
        msg["Subject"] = subject

        alt = MIMEMultipart("alternative")
        plain = re.sub(r"<[^>]+>", "", html_body).strip()
        alt.attach(MIMEText(plain,                     "plain", "utf-8"))
        alt.attach(MIMEText(html_body + signature,     "html",  "utf-8"))
        msg.attach(alt)

        for path_str in (attachments or []):
            p = Path(path_str)
            if p.exists():
                with open(p, "rb") as fh:
                    part = MIMEBase("application", "octet-stream")
                    part.set_payload(fh.read())
                encoders.encode_base64(part)
                part.add_header("Content-Disposition", f'attachment; filename="{p.name}"')
                msg.attach(part)

        ctx = ssl.create_default_context()
        if cfg.get("use_tls", True):
            with smtplib.SMTP(cfg["smtp_host"], cfg.get("smtp_port", 587), timeout=15) as srv:
                srv.ehlo()
                srv.starttls(context=ctx)
                if cfg.get("smtp_user") and cfg.get("smtp_password"):
                    srv.login(cfg["smtp_user"], cfg["smtp_password"])
                srv.sendmail(from_addr, [to_email], msg.as_string())
        else:
            with smtplib.SMTP_SSL(cfg["smtp_host"], cfg.get("smtp_port", 465),
                                   context=ctx, timeout=15) as srv:
                if cfg.get("smtp_user") and cfg.get("smtp_password"):
                    srv.login(cfg["smtp_user"], cfg["smtp_password"])
                srv.sendmail(from_addr, [to_email], msg.as_string())

    def send_document_mail(
        self,
        to_email: str,
        person_name: str,
        subject: str | None,
        html_body: str | None,
        pdf_paths: list[str],
        user_id: int | None = None,
    ) -> None:
        """Versendet einen Bescheid/Brief als PDF-Anhang."""
        if not subject:
            subject = f"Bescheid / Mitteilung – {person_name}"
        if not html_body:
            html_body = (
                f"<p>Sehr geehrte/r {person_name},</p>"
                "<p>anbei finden Sie Ihren Bescheid / Ihre Mitteilung als PDF-Dokument.</p>"
                "<p>Bei Fragen stehen wir Ihnen gerne zur Verfügung.</p>"
            )
        self.send_html_mail(
            to_email=to_email,
            subject=subject,
            html_body=html_body,
            attachments=pdf_paths,
            user_id=user_id,
        )
