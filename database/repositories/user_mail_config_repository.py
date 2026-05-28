"""Repository für persönliche Mail-Konto-Konfigurationen pro Benutzer."""
import base64

from database.db import get_connection


def _enc(s: str) -> str:
    return base64.b64encode(s.encode()).decode() if s else ""


def _dec(s: str) -> str:
    try:
        return base64.b64decode(s.encode()).decode() if s else ""
    except Exception:
        return ""


class UserMailConfigRepository:

    def upsert(self, user_id: int, data: dict) -> None:
        with get_connection() as conn:
            conn.execute(
                """INSERT INTO user_mail_configs
                   (user_id, smtp_host, smtp_port, smtp_user, smtp_password_enc,
                    from_email, from_name, use_tls, signature_html, is_active)
                   VALUES (?,?,?,?,?,?,?,?,?,1)
                   ON CONFLICT(user_id) DO UPDATE SET
                     smtp_host       = excluded.smtp_host,
                     smtp_port       = excluded.smtp_port,
                     smtp_user       = excluded.smtp_user,
                     smtp_password_enc = excluded.smtp_password_enc,
                     from_email      = excluded.from_email,
                     from_name       = excluded.from_name,
                     use_tls         = excluded.use_tls,
                     signature_html  = excluded.signature_html,
                     is_active       = 1,
                     updated_at      = CURRENT_TIMESTAMP""",
                (
                    user_id,
                    data.get("smtp_host", ""),
                    int(data.get("smtp_port", 587)),
                    data.get("smtp_user", ""),
                    _enc(data.get("smtp_password", "")),
                    data.get("from_email", ""),
                    data.get("from_name", ""),
                    1 if data.get("use_tls", True) else 0,
                    data.get("signature_html", ""),
                ),
            )
            conn.commit()

    def get_for_user(self, user_id: int) -> dict | None:
        with get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM user_mail_configs WHERE user_id=? AND is_active=1",
                (user_id,),
            ).fetchone()
        if not row:
            return None
        d = dict(row)
        d["smtp_password"] = _dec(d.get("smtp_password_enc", ""))
        return d

    def delete(self, user_id: int) -> None:
        with get_connection() as conn:
            conn.execute(
                "UPDATE user_mail_configs SET is_active=0 WHERE user_id=?", (user_id,)
            )
            conn.commit()
