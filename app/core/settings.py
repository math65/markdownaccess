"""Réglages persistés MarkdownAccess (JSON dans %APPDATA%/MarkdownAccess).

Adapté de DownAccess (app/core/settings.py) : même mécanique load()/save() qui
filtre les clés inconnues, DEFAULTS propres à l'éditeur.
"""
import json
import os
from pathlib import Path

from app.version import APP_NAME

DEFAULTS: dict = {
    "language": "auto",                 # auto | fr | en
    "recent_files": [],                 # MRU de chemins absolus (cap 10)
    "last_folder": str(Path.home() / "Documents"),
    "default_export_format": "html",    # html | pdf
    "word_wrap": True,                  # retour à la ligne dans l'éditeur
    "window_maximized": True,
    "window_size": [1000, 700],
    "window_pos": None,                 # None -> centré
    "install_id": "",
}

MAX_RECENT_FILES = 10


def _config_dir() -> Path:
    appdata = os.environ.get("APPDATA", str(Path.home()))
    path = Path(appdata) / APP_NAME
    path.mkdir(parents=True, exist_ok=True)
    return path


def _config_file() -> Path:
    return _config_dir() / "settings.json"


def load() -> dict:
    cfg = dict(DEFAULTS)
    try:
        with open(_config_file(), encoding="utf-8") as f:
            saved = json.load(f)
        cfg.update({k: v for k, v in saved.items() if k in DEFAULTS})
    except FileNotFoundError:
        pass
    # Purge les fichiers récents qui n'existent plus.
    cfg["recent_files"] = [p for p in cfg.get("recent_files", []) if os.path.exists(p)]
    return cfg


def save(settings: dict) -> None:
    with open(_config_file(), "w", encoding="utf-8") as f:
        json.dump(settings, f, indent=2, ensure_ascii=False)


def push_recent_file(settings: dict, path: str) -> None:
    """Place ``path`` en tête de la liste des fichiers récents (sans doublon)."""
    path = os.path.abspath(path)
    recent = [p for p in settings.get("recent_files", []) if os.path.abspath(p) != path]
    recent.insert(0, path)
    settings["recent_files"] = recent[:MAX_RECENT_FILES]
