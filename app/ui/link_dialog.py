"""Dialogue d'insertion de lien : deux champs étiquetés (Texte / URL).

Chaque wx.TextCtrl est précédé d'un wx.StaticText (règle d'accessibilité maison).
"""

import wx

from app.core.i18n import _translate as _


class LinkDialog(wx.Dialog):
    def __init__(self, parent, default_text=""):
        super().__init__(parent, title=_("Insérer un lien"))
        panel = wx.Panel(self)
        sizer = wx.BoxSizer(wx.VERTICAL)

        sizer.Add(wx.StaticText(panel, label=_("Texte du lien :")), 0, wx.ALL, 4)
        self.txt_text = wx.TextCtrl(panel, value=default_text, name=_("Texte du lien"))
        sizer.Add(self.txt_text, 0, wx.EXPAND | wx.ALL, 4)

        sizer.Add(wx.StaticText(panel, label=_("Adresse (URL) :")), 0, wx.ALL, 4)
        self.txt_url = wx.TextCtrl(panel, value="https://", name=_("Adresse URL"))
        sizer.Add(self.txt_url, 0, wx.EXPAND | wx.ALL, 4)

        btns = self.CreateButtonSizer(wx.OK | wx.CANCEL)
        sizer.Add(btns, 0, wx.EXPAND | wx.ALL, 8)

        panel.SetSizer(sizer)
        sizer.Fit(panel)
        self.Fit()

        # Focus initial sur le contenu, pas sur un bouton.
        if default_text:
            wx.CallAfter(self.txt_url.SetFocus)
        else:
            wx.CallAfter(self.txt_text.SetFocus)

    def get_values(self):
        return self.txt_text.GetValue().strip(), self.txt_url.GetValue().strip()
