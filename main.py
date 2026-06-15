import logging
import sys
import traceback

import wx

from app.core import logger as _logger
from app.core import settings as cfg
from app.core import i18n


def _install_excepthook(frame):
    """Sur exception non gérée : log + propose un rapport d'erreur (si l'app vit)."""
    log = logging.getLogger("markdownaccess")

    def hook(exc_type, exc, tb):
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc, tb)
            return
        message = "".join(traceback.format_exception(exc_type, exc, tb))
        log.error("Exception non gérée :\n%s", message)
        try:
            wx.CallAfter(frame.show_error_report, message)
        except Exception:
            pass

    sys.excepthook = hook


def main():
    _logger.setup()

    # Installe la traduction AVANT d'importer/instancier la fenêtre : tout module
    # qui utilise _() doit voir _ injecté dans builtins.
    settings = cfg.load()
    i18n.install_language(settings.get("language", "auto"))

    # Purge un installeur téléchargé lors d'une mise à jour précédente.
    from app.core import updater
    try:
        updater.cleanup_update_artifacts()
    except Exception:
        pass

    from app.ui.main_window import MainWindow

    app = wx.App(False)
    frame = MainWindow(None)
    _install_excepthook(frame)
    frame.Show()
    frame.run_startup_checks()
    app.MainLoop()


if __name__ == "__main__":
    main()
