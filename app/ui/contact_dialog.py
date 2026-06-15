"""Dialogue de contact / suggestion (envoi via le backend app-backend).

Porté de DownAccess (app/ui/contact_dialog.py). Accessible : chaque champ a un
wx.StaticText / name= ; tout est parenté au dialogue (pas de panneau → pas de
piège de parent de sizer).
"""
import re

import wx

from app.core import error_reporter, speech
from app.core.i18n import _translate as _

# Clés internes des types de contact (jamais traduites).
CONTACT_TYPE_CODES = ["suggestion", "bug", "question", "other"]


def _contact_type_labels():
    return [
        _("Suggestion de fonctionnalité"),
        _("Signaler un bug"),
        _("Question générale"),
        _("Autre"),
    ]


class ContactDialog(wx.Dialog):
    def __init__(self, parent, saved_email: str = "", on_email_saved=None):
        super().__init__(
            parent,
            title=_("Contacter le support — MarkdownAccess"),
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
            size=(560, 460),
        )
        self._saved_email = saved_email
        self._on_email_saved = on_email_saved
        self._build_ui()
        self.txt_email.SetFocus()
        self.Centre()

    def _build_ui(self) -> None:
        sizer = wx.BoxSizer(wx.VERTICAL)

        sizer.Add(wx.StaticText(self, label=_("Votre adresse email (obligatoire pour recevoir une réponse) :")),
                  0, wx.LEFT | wx.RIGHT | wx.TOP, 12)
        self.txt_email = wx.TextCtrl(self, name=_("Adresse email"), value=self._saved_email)
        sizer.Add(self.txt_email, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 8)

        sizer.Add(wx.StaticText(self, label=_("Type de message :")),
                  0, wx.LEFT | wx.RIGHT | wx.TOP, 12)
        self.cho_type = wx.Choice(self, choices=_contact_type_labels(), name=_("Type de message"))
        self.cho_type.SetSelection(0)
        sizer.Add(self.cho_type, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 8)

        sizer.Add(wx.StaticText(self, label=_("Message :")),
                  0, wx.LEFT | wx.RIGHT | wx.TOP, 12)
        self.txt_message = wx.TextCtrl(self, style=wx.TE_MULTILINE, name=_("Message"))
        sizer.Add(self.txt_message, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 8)

        self.lbl_status = wx.StaticText(self, label="")
        sizer.Add(self.lbl_status, 0, wx.LEFT | wx.RIGHT | wx.TOP, 12)

        btn_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.btn_send = wx.Button(self, wx.ID_OK, label=_("Envoyer"), name=_("Envoyer le message"))
        self.btn_cancel = wx.Button(self, wx.ID_CANCEL, label=_("Annuler"), name=_("Annuler"))
        btn_sizer.AddStretchSpacer()
        btn_sizer.Add(self.btn_send, 0, wx.RIGHT, 8)
        btn_sizer.Add(self.btn_cancel, 0, wx.RIGHT, 8)
        sizer.Add(btn_sizer, 0, wx.EXPAND | wx.ALL, 10)

        self.btn_send.Bind(wx.EVT_BUTTON, self._on_send)
        self.btn_cancel.Bind(wx.EVT_BUTTON, lambda _e: self.EndModal(wx.ID_CANCEL))
        self.SetSizer(sizer)

    # ---- états ---------------------------------------------------------

    def set_sending(self) -> None:
        self.btn_send.Enable(False)
        self.btn_cancel.Enable(False)
        self.lbl_status.SetLabel(_("Envoi en cours…"))
        speech.speak(_("Envoi en cours."))
        self.Layout()

    def set_done(self, success: bool, message: str) -> None:
        self.lbl_status.SetLabel(message)
        self.btn_cancel.SetLabel(_("Fermer"))
        self.btn_cancel.Enable(True)
        self.btn_cancel.SetFocus()
        self.btn_send.Enable(not success)
        speech.speak(message)
        self.Layout()

    # ---- accesseurs ----------------------------------------------------

    def get_type_key(self) -> str:
        idx = self.cho_type.GetSelection()
        return CONTACT_TYPE_CODES[idx] if 0 <= idx < len(CONTACT_TYPE_CODES) else "other"

    def get_email(self) -> str:
        return self.txt_email.GetValue().strip()

    def get_message(self) -> str:
        return self.txt_message.GetValue().strip()

    # ---- validation + envoi -------------------------------------------

    def _on_send(self, _event) -> None:
        email = self.get_email()
        message = self.get_message()

        if not email:
            wx.MessageBox(_("Veuillez entrer votre adresse email."), _("Champ manquant"),
                          wx.OK | wx.ICON_WARNING)
            self.txt_email.SetFocus()
            return
        if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email):
            wx.MessageBox(_("L'adresse email semble invalide."), _("Email invalide"),
                          wx.OK | wx.ICON_WARNING)
            self.txt_email.SetFocus()
            return
        if not message:
            wx.MessageBox(_("Veuillez écrire un message."), _("Champ manquant"),
                          wx.OK | wx.ICON_WARNING)
            self.txt_message.SetFocus()
            return

        if self._on_email_saved:
            self._on_email_saved(email)

        self.set_sending()
        error_reporter.send_contact(
            contact_type=self.get_type_key(),
            email=email,
            message=message,
            on_done=lambda ok, msg: wx.CallAfter(self.set_done, ok, msg),
        )
