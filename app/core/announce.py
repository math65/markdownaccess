"""Annonces au lancement (backend app-backend, route /api/announce/check).

Porté de DownAccess (app/core/announce.py). Si une annonce active existe, elle est
remontée à l'UI pour affichage ; l'affichage est confirmé via /api/announce/ack.
Vérification silencieuse : toute erreur réseau est ignorée (log DEBUG).
"""
import json
import logging
import threading
import urllib.error
import urllib.request
from collections.abc import Callable

from app.core import i18n
from app.core.error_reporter import _APP_ID, _BEARER

log = logging.getLogger("markdownaccess.announce")

CHECK_URL = "https://mathieumartin.ovh/api/announce/check"
ACK_URL = "https://mathieumartin.ovh/api/announce/ack"
CLICK_URL = "https://mathieumartin.ovh/api/announce/click"


def _post(url: str, payload: dict, timeout: int) -> dict:
    """POST JSON avec auth Bearer, retourne le corps décodé."""
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Content-Type", "application/json; charset=utf-8")
    req.add_header("Authorization", f"Bearer {_BEARER}")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read())


def check_announcement(install_id: str, on_done: Callable[[dict | None], None]) -> None:
    """Récupère l'annonce active en arrière-plan. on_done(announcement | None) est
    appelé depuis le thread → utiliser wx.CallAfter côté UI. None = aucune annonce
    ou erreur (silencieux)."""
    def _run() -> None:
        try:
            lang = i18n.get_current_language_code()
            payload = {"app": _APP_ID, "install_id": install_id, "lang": lang}
            body = _post(CHECK_URL, payload, timeout=8)
            ann = body.get("announcement")
            on_done(ann if isinstance(ann, dict) else None)
        except (urllib.error.URLError, OSError, ValueError) as exc:
            log.debug("Vérification annonce impossible : %s", exc)
            on_done(None)
        except Exception as exc:
            log.debug("Vérification annonce : erreur inattendue : %s", exc)
            on_done(None)

    threading.Thread(target=_run, daemon=True).start()


def ack_announcement(install_id: str, ann_id: str) -> None:
    """Confirme l'affichage d'une annonce (fire-and-forget, erreurs ignorées)."""
    def _run() -> None:
        try:
            _post(ACK_URL, {"app": _APP_ID, "install_id": install_id, "id": ann_id}, timeout=8)
        except Exception as exc:
            log.debug("Accusé annonce impossible : %s", exc)

    threading.Thread(target=_run, daemon=True).start()


def click_announcement(install_id: str, ann_id: str) -> None:
    """Enregistre un clic sur le bouton lien de l'annonce (fire-and-forget)."""
    def _run() -> None:
        try:
            _post(CLICK_URL, {"app": _APP_ID, "install_id": install_id, "id": ann_id}, timeout=8)
        except Exception as exc:
            log.debug("Clic annonce impossible : %s", exc)

    threading.Thread(target=_run, daemon=True).start()
