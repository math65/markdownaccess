"""Dialogue de mise à jour : notes de version + téléchargement avec jauge.

Adapté de UniversalTranscoder (ui/update_dialog.py), en français. Accessible :
contrôles wx natifs, `name=` sur chaque élément lu par NVDA, focus initial sur
les notes, notes dans un `wx.TextCtrl` lecture seule (jamais HtmlWindow).

La jauge `wx.Gauge` montre la progression du **téléchargement**. L'installation
elle-même se fait après fermeture de l'app, via la fenêtre de progression d'Inno
(`/SILENT`) — pas dans ce dialogue.
"""

import logging
import re
import threading

import wx

from app.core.app_info import APP_NAME, APP_VERSION
from app.core.i18n import _translate as _
from app.core.updater import (
    UpdateDownloadError,
    download_release_installer,
    format_release_date,
    open_release_page,
)


class UpdateDialog(wx.Dialog):
    def __init__(self, parent, release_info):
        super().__init__(parent, title=_("Mise à jour disponible"), size=(760, 620))
        self.SetName(_("Mise à jour disponible"))

        self.parent_window = parent
        self.release_info = release_info
        self._download_in_progress = False

        self._init_ui()
        self.Centre()

    def _init_ui(self):
        panel = wx.Panel(self)
        root = wx.BoxSizer(wx.VERTICAL)

        intro = wx.StaticText(
            panel,
            label=_("Une nouvelle version de {app_name} est disponible.").format(app_name=APP_NAME),
        )
        intro.Wrap(680)
        root.Add(intro, 0, wx.EXPAND | wx.ALL, 12)

        info_grid = wx.FlexGridSizer(cols=2, vgap=8, hgap=10)
        info_grid.AddGrowableCol(1, 1)

        info_grid.Add(wx.StaticText(panel, label=_("Version actuelle :")), 0, wx.ALIGN_CENTER_VERTICAL)
        info_grid.Add(wx.StaticText(panel, label=APP_VERSION), 0, wx.ALIGN_CENTER_VERTICAL)
        info_grid.Add(wx.StaticText(panel, label=_("Version disponible :")), 0, wx.ALIGN_CENTER_VERTICAL)
        info_grid.Add(wx.StaticText(panel, label=self.release_info.version), 0, wx.ALIGN_CENTER_VERTICAL)
        info_grid.Add(wx.StaticText(panel, label=_("Publiée le :")), 0, wx.ALIGN_CENTER_VERTICAL)
        info_grid.Add(
            wx.StaticText(panel, label=format_release_date(self.release_info.published_at)),
            0, wx.ALIGN_CENTER_VERTICAL,
        )
        root.Add(info_grid, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 12)

        notes_box = wx.StaticBoxSizer(wx.VERTICAL, panel, _("Notes de version"))
        self.txt_release_notes = wx.TextCtrl(
            panel,
            style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_RICH2 | wx.VSCROLL | wx.HSCROLL,
            name=_("Notes de version"),
        )
        self.txt_release_notes.SetMinSize((-1, 320))
        notes_box.Add(self.txt_release_notes, 1, wx.EXPAND | wx.ALL, 8)
        root.Add(notes_box, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 12)

        self.lbl_feedback = wx.StaticText(panel, label="")
        self.lbl_feedback.Wrap(680)
        self.lbl_feedback.Hide()
        root.Add(self.lbl_feedback, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        self.gauge_download = wx.Gauge(panel, range=100, name=_("Progression du téléchargement"))
        self.gauge_download.Hide()
        root.Add(self.gauge_download, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        self.lbl_download_status = wx.StaticText(panel, label="")
        self.lbl_download_status.Hide()
        root.Add(self.lbl_download_status, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 12)

        actions = wx.BoxSizer(wx.HORIZONTAL)
        self.btn_download_install = wx.Button(panel, label=_("Télécharger et installer"))
        self.btn_download_install.SetName(_("Télécharger et installer"))
        self.btn_download_install.SetDefault()

        self.btn_release_page = wx.Button(panel, label=_("Ouvrir la page de la release"))
        self.btn_release_page.SetName(_("Ouvrir la page de la release"))

        self.btn_close = wx.Button(panel, wx.ID_CLOSE, label=_("Fermer"))
        self.btn_close.SetName(_("Fermer"))

        actions.Add(self.btn_download_install, 0, wx.RIGHT, 8)
        actions.Add(self.btn_release_page, 0, wx.RIGHT, 8)
        actions.AddStretchSpacer()
        actions.Add(self.btn_close, 0)
        root.Add(actions, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 12)

        panel.SetSizer(root)
        self.SetEscapeId(self.btn_close.GetId())
        self.SetAffirmativeId(self.btn_download_install.GetId())

        self.Bind(wx.EVT_BUTTON, self.on_download_install, self.btn_download_install)
        self.Bind(wx.EVT_BUTTON, self.on_open_release_page, self.btn_release_page)
        self.Bind(wx.EVT_BUTTON, self.on_close_button, self.btn_close)
        self.Bind(wx.EVT_CLOSE, self.on_close_window)
        self.txt_release_notes.Bind(wx.EVT_KEY_DOWN, self.on_release_notes_key_down)
        self._render_release_notes()
        wx.CallAfter(self.txt_release_notes.SetFocus)

    # ---- notes ---------------------------------------------------------

    def _render_release_notes(self):
        try:
            self.txt_release_notes.SetValue(self._to_plain_release_notes(self.release_info.body))
            self.txt_release_notes.SetInsertionPoint(0)
            self.txt_release_notes.ShowPosition(0)
        except Exception:
            logging.getLogger("markdownaccess").exception("Rendu des notes de version impossible.")

    def _to_plain_release_notes(self, body):
        lines = str(body or "").replace("\r\n", "\n").split("\n")
        out = []
        for line in lines:
            stripped = line.strip()
            if stripped.startswith("## "):
                out.append(self._normalize_inline(stripped[3:]))
            elif stripped.startswith("# "):
                out.append(self._normalize_inline(stripped[2:]))
            elif stripped.startswith("- ") or stripped.startswith("* "):
                out.append(f"• {self._normalize_inline(stripped[2:])}")
            else:
                out.append(self._normalize_inline(line))
        return "\n".join(out).strip()

    def _normalize_inline(self, text):
        normalized = str(text or "")
        normalized = re.sub(r"\*\*(.*?)\*\*", r"\1", normalized)
        normalized = re.sub(r"`(.*?)`", r"\1", normalized)
        normalized = re.sub(r"\[(.*?)\]\((.*?)\)", r"\1 (\2)", normalized)
        return normalized

    # ---- feedback / progression ----------------------------------------

    def _set_feedback(self, message, is_error=False):
        self.lbl_feedback.SetLabel(message)
        self.lbl_feedback.SetForegroundColour(
            wx.Colour(180, 0, 0) if is_error else wx.Colour(0, 120, 0)
        )
        self.lbl_feedback.Show()
        self.Layout()
        wx.CallAfter(self.lbl_feedback.SetFocus)

    def _set_download_state(self, downloading):
        self._download_in_progress = downloading
        self.btn_download_install.Enable(not downloading)
        self.btn_release_page.Enable(not downloading)
        self.btn_close.Enable(not downloading)
        if downloading:
            self.gauge_download.SetValue(0)
            self.gauge_download.Show()
            self.lbl_download_status.SetLabel(_("Téléchargement de la mise à jour..."))
            self.lbl_download_status.Show()
        self.Layout()

    def _update_download_progress(self, downloaded, total):
        if not self._download_in_progress:
            return
        if total > 0:
            percent = min(100, int((downloaded / total) * 100))
            self.gauge_download.SetValue(percent)
            status = _("Téléchargement... {percent} %").format(percent=percent)
        else:
            self.gauge_download.Pulse()
            status = _("Téléchargement...")
        self.lbl_download_status.SetLabel(status)
        self.lbl_download_status.SetName(status)
        self.Layout()

    # ---- téléchargement (thread) ---------------------------------------

    def _download_worker(self):
        try:
            installer_path = download_release_installer(
                self.release_info,
                progress_callback=lambda d, t: wx.CallAfter(self._update_download_progress, d, t),
            )
        except UpdateDownloadError as exc:
            wx.CallAfter(self._on_download_failure, str(exc))
            return
        except Exception:
            logging.getLogger("markdownaccess").exception("Erreur inattendue pendant le téléchargement.")
            wx.CallAfter(self._on_download_failure, _("Erreur inattendue pendant le téléchargement."))
            return
        wx.CallAfter(self._on_download_success, installer_path)

    def _on_download_success(self, installer_path):
        self._set_download_state(False)
        self.gauge_download.SetValue(100)
        self._set_feedback(_("Mise à jour téléchargée."))

        message = _(
            "La version {version} a été téléchargée.\n\nL'application va se fermer "
            "et l'installation va démarrer (l'app redémarrera ensuite).\nContinuer ?"
        ).format(version=self.release_info.version)
        confirm = wx.MessageDialog(
            self, message, _("Installer la mise à jour"),
            wx.YES_NO | wx.NO_DEFAULT | wx.ICON_QUESTION,
        )
        try:
            if confirm.ShowModal() == wx.ID_YES:
                if self.parent_window.begin_install_update(installer_path, self.release_info.version):
                    self.EndModal(wx.ID_OK)
                    return
        finally:
            confirm.Destroy()

        try:
            installer_path.unlink(missing_ok=True)
        except OSError:
            logging.getLogger("markdownaccess").exception("Suppression de l'installeur annulé impossible.")
        self._set_feedback(_("Installation annulée."))

    def _on_download_failure(self, message):
        self._set_download_state(False)
        self.gauge_download.Hide()
        self.lbl_download_status.Hide()
        self._set_feedback(message, is_error=True)
        self.Layout()

    # ---- handlers ------------------------------------------------------

    def on_download_install(self, event):
        if self._download_in_progress:
            return
        self._set_feedback(_("Téléchargement de l'installeur..."))
        self._set_download_state(True)
        threading.Thread(target=self._download_worker, daemon=True).start()

    def on_open_release_page(self, event):
        try:
            open_release_page(self.release_info.html_url)
        except Exception:
            logging.getLogger("markdownaccess").exception("Ouverture de la page de release impossible.")
            self._set_feedback(_("Impossible d'ouvrir la page de la release."), is_error=True)

    def on_release_notes_key_down(self, event):
        if event.GetKeyCode() == wx.WXK_TAB:
            target = self.btn_close if event.ShiftDown() else self.btn_download_install
            target.SetFocus()
            return
        event.Skip()

    def on_close_button(self, event):
        self.EndModal(wx.ID_CLOSE)

    def on_close_window(self, event):
        if self._download_in_progress:
            self._set_feedback(_("Veuillez attendre la fin du téléchargement."), is_error=True)
            event.Veto()
            return
        event.Skip()
