"""Dialogue de recherche : un champ étiqueté + option de casse.

Champ précédé d'un wx.StaticText (règle d'accessibilité maison). Le focus part
sur le champ de saisie ; OK reste le bouton « par défaut » (Entrée lance la
recherche) sans pour autant capter le focus à l'ouverture.
"""

import wx

from app.core.i18n import _translate as _


class FindDialog(wx.Dialog):
    def __init__(self, parent, default_term="", case_sensitive=False):
        super().__init__(parent, title=_("Rechercher"))
        panel = wx.Panel(self)
        sizer = wx.BoxSizer(wx.VERTICAL)

        sizer.Add(wx.StaticText(panel, label=_("Rechercher :")), 0, wx.ALL, 4)
        self.txt_term = wx.TextCtrl(panel, value=default_term, name=_("Texte à rechercher"))
        sizer.Add(self.txt_term, 0, wx.EXPAND | wx.ALL, 4)

        self.chk_case = wx.CheckBox(panel, label=_("Respecter la &casse"))
        self.chk_case.SetValue(case_sensitive)
        sizer.Add(self.chk_case, 0, wx.ALL, 4)

        # Boutons construits à la main : ID_OK / ID_CANCEL clôturent le modal
        # automatiquement. OK est « par défaut » (Entrée), mais on ne lui donne
        # pas le focus.
        ok = wx.Button(panel, wx.ID_OK)
        cancel = wx.Button(panel, wx.ID_CANCEL)
        ok.SetDefault()
        btns = wx.StdDialogButtonSizer()
        btns.AddButton(ok)
        btns.AddButton(cancel)
        btns.Realize()
        sizer.Add(btns, 0, wx.EXPAND | wx.ALL, 8)

        panel.SetSizer(sizer)
        sizer.Fit(panel)
        self.Fit()

        # Focus sur le champ ; sélection du terme pour qu'une frappe le remplace.
        self.txt_term.SetFocus()
        self.txt_term.SelectAll()

    def get_values(self):
        return self.txt_term.GetValue(), self.chk_case.GetValue()
