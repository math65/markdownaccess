"""Rapports d'erreur et contact via le backend app-backend (HTTPS).

Porté de DownAccess (app/core/error_reporter.py), simplifié pour l'éditeur.
Routes génériques `/api/feedback/report` (multipart) et `/api/feedback/contact`
(JSON), authentifiées par Bearer + champ `app`.

Note : le dépôt est public ; le Bearer est donc un identifiant d'app + garde
anti-spam (couplé au rate-limiting backend), pas un vrai secret. Le même secret
doit être présent côté serveur dans la variable d'env MARKDOWNACCESS_BEARER_SECRET.
"""
import io
import json
import platform
import sys
import threading
import urllib.error
import urllib.request
import uuid
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

import wx

from app.core import speech
from app.core import i18n
from app.core.i18n import _translate as _
from app.version import __version__

REPORT_URL = "https://mathieumartin.ovh/api/feedback/report"
CONTACT_URL = "https://mathieumartin.ovh/api/feedback/contact"
_BEARER = "0a614bd33fbc97602ebb48372cac83eac553f7fe395459ccab5237a13e2119ed"
_APP_ID = "markdownaccess"

_MAX_COMMENT = 2_000
_MAX_SUMMARY = 100_000


def collect_system_info() -> dict:
    """Infos système lisibles (libellés FR : l'email part au développeur)."""
    try:
        wx_ver = wx.version()
    except Exception:
        wx_ver = "inconnu"
    return {
        "Python": platform.python_version(),
        "wxPython": wx_ver,
        "Plateforme OS": platform.platform(),
        "Édition Windows": platform.version(),
        "Architecture": platform.machine(),
        "Langue de l'application": i18n.get_current_language_code(),
        "Lecteur d'écran": speech.active_screen_reader(),
        "Exécutable compilé": "oui" if getattr(sys, "frozen", False) else "non",
    }


def build_report(error_message: str, user_comment: str = "", email: str = "",
                 system_info: dict | None = None) -> dict:
    """Construit le payload `report`. `summary` = message d'erreur (le backend en
    fait la section rouge « Message d'erreur »)."""
    now = datetime.now(UTC)
    sections: dict = {
        "Informations techniques": {
            "Version MarkdownAccess": __version__,
            "Système": platform.version(),
            "Date": now.isoformat(),
            "Email utilisateur": email or "—",
        },
    }
    sections["Informations système"] = system_info or collect_system_info()
    return {
        "app": _APP_ID,
        "email": (email or "")[:200],
        "summary": (error_message or "")[:_MAX_SUMMARY],
        "subject_hint": f"Erreur — v{__version__} — {now.strftime('%Y-%m-%d %H:%M')}",
        "user_comment": (user_comment or "")[:_MAX_COMMENT],
        "sections": sections,
    }


def _make_multipart(fields: dict, files: dict) -> tuple[bytes, str]:
    boundary = uuid.uuid4().hex
    body = io.BytesIO()
    for name, value in fields.items():
        body.write(f"--{boundary}\r\n".encode())
        body.write(f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode())
        body.write(f"{value}\r\n".encode())
    for name, (filename, content) in files.items():
        body.write(f"--{boundary}\r\n".encode())
        body.write(
            f'Content-Disposition: form-data; name="{name}"; filename="{filename}"\r\n'
            f"Content-Type: text/plain; charset=utf-8\r\n\r\n".encode()
        )
        body.write(content if isinstance(content, bytes) else content.encode("utf-8"))
        body.write(b"\r\n")
    body.write(f"--{boundary}--\r\n".encode())
    return body.getvalue(), f"multipart/form-data; boundary={boundary}"


def _read_log_file() -> str:
    try:
        from app.core.logger import get_log_path
        log_path: Path = get_log_path()
        if log_path.exists():
            return log_path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        pass
    return ""


def send_report(report: dict, on_done: Callable[[bool, str], None]) -> None:
    """Envoie le rapport en multipart en arrière-plan. on_done(success, message)
    est appelé depuis le thread → utiliser wx.CallAfter côté UI."""
    def _run() -> None:
        try:
            fields = {"report": json.dumps(report, ensure_ascii=False)}
            files = {"log_file": ("markdownaccess.log", _read_log_file())}
            data, content_type = _make_multipart(fields, files)
            req = urllib.request.Request(REPORT_URL, data=data, method="POST")
            req.add_header("Content-Type", content_type)
            req.add_header("Authorization", f"Bearer {_BEARER}")
            with urllib.request.urlopen(req, timeout=30) as resp:
                body = json.loads(resp.read())
            if body.get("ok"):
                on_done(True, _("Rapport envoyé avec succès."))
            else:
                on_done(False, body.get("message", _("Erreur inconnue.")))
        except urllib.error.HTTPError as exc:
            try:
                body = json.loads(exc.read())
                on_done(False, body.get("message", _("Erreur HTTP {code}.").format(code=exc.code)))
            except Exception:
                on_done(False, _("Erreur HTTP {code}.").format(code=exc.code))
        except Exception as exc:
            on_done(False, str(exc))

    threading.Thread(target=_run, daemon=True).start()


def send_contact(contact_type: str, email: str, message: str,
                 on_done: Callable[[bool, str], None]) -> None:
    """Envoie un message de contact/suggestion en arrière-plan."""
    payload = {
        "app": _APP_ID,
        "app_version": __version__,
        "contact_type": contact_type,
        "email": email,
        "message": message[:_MAX_COMMENT],
    }

    def _run() -> None:
        try:
            data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            req = urllib.request.Request(CONTACT_URL, data=data, method="POST")
            req.add_header("Content-Type", "application/json; charset=utf-8")
            req.add_header("Authorization", f"Bearer {_BEARER}")
            with urllib.request.urlopen(req, timeout=15) as resp:
                body = json.loads(resp.read())
            if body.get("ok"):
                on_done(True, _("Message envoyé. Merci pour votre retour !"))
            else:
                on_done(False, body.get("message", _("Erreur inconnue.")))
        except urllib.error.HTTPError as exc:
            try:
                body = json.loads(exc.read())
                on_done(False, body.get("message", _("Erreur HTTP {code}.").format(code=exc.code)))
            except Exception:
                on_done(False, _("Erreur HTTP {code}.").format(code=exc.code))
        except Exception as exc:
            on_done(False, str(exc))

    threading.Thread(target=_run, daemon=True).start()
