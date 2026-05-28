"""SMTP-Mailversand mit HTML-Signatur und PDF-Anhang.
Konfiguration über SettingsService (SMTP_HOST, SMTP_PORT, etc.).
"""
import re
import smtplib
import ssl
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

_HTML_SIGNATURE = """\
<br><br>
<hr style="border:none;border-top:1px solid #ddd;margin:16px 0;">
<table style="font-family:Arial,sans-serif;font-size:12px;color:#444;line-height:1.6;">
<tr><td>
  <strong>Verein Tischlein Deck Dich Vorarlberg</strong><br>
  Ladritschweg 10c · 6773 Vandans<br>
  <a href="mailto:info@tischleindeckdich-vbg.at"
     style="color:#4a90d9;text-decoration:none;">info@tischleindeckdich-vbg.at</a>
</td></tr>
</table>"""


class MailService:
    """HTML-Mailversand über konfiguriertes SMTP-Konto."""

    SENDER_NAME = "Verein Tischlein Deck Dich Vorarlberg"
    SENDER_CITY = "Vandans"

    def __init__(self, settings_service=None):
        from services.settings_service import SettingsService
        self._settings = settings_service or SettingsService()

    # ── Konfiguration ─────────────────────────────────────────────────────────
    def get_config(self) -> dict:
        return {
            "host":       str(self._settings.get("SMTP_HOST", "") or ""),
            "port":       int(self._settings.get("SMTP_PORT", 587) or 587),
            "user":       str(self._settings.get("SMTP_USER", "") or ""),
            "password":   str(self._settings.get("SMTP_PASSWORD", "") or ""),
            "from_email": str(self._settings.get("SMTP_FROM_EMAIL", "") or ""),
            "from_name":  str(self._settings.get("SMTP_FROM_NAME", self.SENDER_NAME) or self.SENDER_NAME),
            "use_tls":    bool(self._settings.get("SMTP_USE_TLS", True)),
        }

    def is_configured(self) -> bool:
        cfg = self.get_config()
        return bool(cfg["host"] and cfg["from_email"])

    # ── Kernversand ───────────────────────────────────────────────────────────
    def send_html_mail(
        self,
        to_email: str,
        subject: str,
        html_body: str,
        attachments: list[str] | None = None,
        cc: str | None = None,
    ) -> None:
        """Sendet eine HTML-Mail (mit Signatur) und optionalen PDF-Anhängen."""
        cfg = self.get_config()
        if not cfg["host"]:
            raise ValueError(
                "SMTP nicht konfiguriert. "
                "Bitte SMTP-Einstellungen im Admin-Bereich → Einstellungen hinterlegen."
            )

        msg = MIMEMultipart("mixed")
        msg["From"]    = f"{cfg['from_name']} <{cfg['from_email']}>"
        msg["To"]      = to_email
        msg["Subject"] = subject
        if cc:
            msg["Cc"] = cc

        # Alt-Teil: plain-text + HTML mit Signatur
        alt = MIMEMultipart("alternative")
        plain = re.sub(r"<[^>]+>", "", html_body).strip()
        alt.attach(MIMEText(plain,                          "plain", "utf-8"))
        alt.attach(MIMEText(html_body + _HTML_SIGNATURE,   "html",  "utf-8"))
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

        all_recipients = [to_email] + ([cc] if cc else [])
        self._send(cfg, all_recipients, msg.as_string())

    def _send(self, cfg: dict, recipients: list[str], raw: str) -> None:
        ctx = ssl.create_default_context()
        if cfg["use_tls"]:
            with smtplib.SMTP(cfg["host"], cfg["port"], timeout=15) as srv:
                srv.ehlo()
                srv.starttls(context=ctx)
                if cfg["user"] and cfg["password"]:
                    srv.login(cfg["user"], cfg["password"])
                srv.sendmail(cfg["from_email"], recipients, raw)
        else:
            with smtplib.SMTP_SSL(cfg["host"], cfg["port"], context=ctx, timeout=15) as srv:
                if cfg["user"] and cfg["password"]:
                    srv.login(cfg["user"], cfg["password"])
                srv.sendmail(cfg["from_email"], recipients, raw)

    # ── Fachlicher Versand ────────────────────────────────────────────────────
    def send_letter(
        self,
        to_email: str,
        person_name: str,
        pdf_path: str | None = None,
        subject: str | None = None,
        html_body: str | None = None,
    ) -> None:
        """Versendet einen Bescheid/Brief als PDF-Anhang per E-Mail."""
        if not subject:
            subject = f"Mitteilung – {person_name}"
        if not html_body:
            html_body = (
                f"<p>Sehr geehrte/r {person_name},</p>"
                "<p>anbei finden Sie Ihre Mitteilung / Ihren Bescheid als PDF-Dokument.</p>"
                "<p>Bei Fragen stehen wir Ihnen gerne zur Verfügung.</p>"
            )
        self.send_html_mail(
            to_email=to_email,
            subject=subject,
            html_body=html_body,
            attachments=[pdf_path] if pdf_path else None,
        )

    def test_connection(self) -> tuple[bool, str]:
        """Testet die SMTP-Verbindung. Gibt (success, message) zurück."""
        try:
            cfg = self.get_config()
            if not cfg["host"]:
                return False, "Kein SMTP-Host konfiguriert."
            ctx = ssl.create_default_context()
            if cfg["use_tls"]:
                with smtplib.SMTP(cfg["host"], cfg["port"], timeout=10) as srv:
                    srv.ehlo()
                    srv.starttls(context=ctx)
                    if cfg["user"] and cfg["password"]:
                        srv.login(cfg["user"], cfg["password"])
            else:
                with smtplib.SMTP_SSL(cfg["host"], cfg["port"], context=ctx, timeout=10) as srv:
                    if cfg["user"] and cfg["password"]:
                        srv.login(cfg["user"], cfg["password"])
            return True, "Verbindung erfolgreich."
        except Exception as exc:
            return False, str(exc)
