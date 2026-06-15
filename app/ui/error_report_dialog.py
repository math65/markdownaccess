"""Dialogue de rapport d'erreur (déclenché sur exception non gérée).

Montre le message d'erreur (lecture seule), un email (pré-rempli) et un
commentaire, puis envoie un rapport au backend (log + infos système joints).
Accessible : champs étiquetés, focus sur le commentaire.
"""
import re

import wx

from app.core import error_reporter, speech
from app.core.i18n import _translate as _


class ErrorReportDialog(wx.Dialog):
    def __init__(self, parent, error_message: str, saved_email: str = "",
                 on_email_saved=None):
        super().__init__(
            parent,
            title=_("Une erreur est survenue — MarkdownAccess"),
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
            size=(600, 500),
        )
        self._error_message = error_message
        self._saved_email = saved_email
        self._on_email_saved = on_email_saved
        self._build_ui()
        self.Centre()

    def _build_ui(self) -> None:
        sizer = wx.BoxSizer(wx.VERTICAL)

        sizer.Add(wx.StaticText(self, label=_(
            "Une erreur inattendue est survenue. Vous pouvez envoyer un rapport "
            "au développeur pour aider à la corriger.")),
            0, wx.LEFT | wx.RIGHT | wx.TOP, 12)

        sizer.Add(wx.StaticText(self, label=_("Détail de l'erreur :")),
                  0, wx.LEFT | wx.RIGHT | wx.TOP, 12)
        self.txt_error = wx.TextCtrl(
            self, style=wx.TE_MULTILINE | wx.TE_READONLY,
            value=self._error_message, name=_("Détail de l'erreur"))
        self.txt_error.SetMinSize((-1, 140))
        sizer.Add(self.txt_error, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 8)

        sizer.Add(wx.StaticText(self, label=_("Votre adresse email (pour une réponse) :")),
                  0, wx.LEFT | wx.RIGHT | wx.TOP, 12)
        self.txt_email = wx.TextCtrl(self, value=self._saved_email, name=_("Adresse email"))
        sizer.Add(self.txt_email, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 8)

        sizer.Add(wx.StaticText(self, label=_("Que faisiez-vous ? (optionnel) :")),
                  0, wx.LEFT | wx.RIGHT | wx.TOP, 12)
        self.txt_comment = wx.TextCtrl(self, style=wx.TE_MULTILINE, name=_("Commentaire"))
        sizer.Add(self.txt_comment, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 8)

        self.lbl_status = wx.StaticText(self, label="")
        sizer.Add(self.lbl_status, 0, wx.LEFT | wx.RIGHT | wx.TOP, 12)

        btn_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.btn_send = wx.Button(self, wx.ID_OK, label=_("Envoyer le rapport"),
                                  name=_("Envoyer le rapport"))
        self.btn_close = wx.Button(self, wx.ID_CANCEL, label=_("Fermer"), name=_("Fermer"))
        btn_sizer.AddStretchSpacer()
        btn_sizer.Add(self.btn_send, 0, wx.RIGHT, 8)
        btn_sizer.Add(self.btn_close, 0, wx.RIGHT, 8)
        sizer.Add(btn_sizer, 0, wx.EXPAND | wx.ALL, 10)

        self.btn_send.Bind(wx.EVT_BUTTON, self._on_send)
        self.btn_close.Bind(wx.EVT_BUTTON, lambda _e: self.EndModal(wx.ID_CANCEL))
        self.SetSizer(sizer)
        wx.CallAfter(self.txt_comment.SetFocus)

    def set_sending(self) -> None:
        self.btn_send.Enable(False)
        self.btn_close.Enable(False)
        self.lbl_status.SetLabel(_("Envoi en cours…"))
        speech.speak(_("Envoi en cours."))
        self.Layout()

    def set_done(self, success: bool, message: str) -> None:
        self.lbl_status.SetLabel(message)
        self.btn_close.Enable(True)
        self.btn_close.SetFocus()
        self.btn_send.Enable(not success)
        speech.speak(message)
        self.Layout()

    def _on_send(self, _event) -> None:
        email = self.txt_email.GetValue().strip()
        # Email facultatif ici, mais s'il est fourni on le valide.
        if email and not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email):
            wx.MessageBox(_("L'adresse email semble invalide."), _("Email invalide"),
                          wx.OK | wx.ICON_WARNING)
            self.txt_email.SetFocus()
            return
        if email and self._on_email_saved:
            self._on_email_saved(email)

        report = error_reporter.build_report(
            error_message=self._error_message,
            user_comment=self.txt_comment.GetValue().strip(),
            email=email,
        )
        self.set_sending()
        error_reporter.send_report(
            report, on_done=lambda ok, msg: wx.CallAfter(self.set_done, ok, msg))
