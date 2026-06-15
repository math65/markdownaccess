"""Dialogue Assistant Tableau : nombre de lignes, de colonnes, en-tête.

Chaque wx.SpinCtrl est précédé d'un wx.StaticText (règle d'accessibilité maison).
Génère un squelette de tableau Markdown (GFM) inséré au curseur par l'appelant.
"""

import wx

from app.core.i18n import _translate as _


class TableDialog(wx.Dialog):
    def __init__(self, parent):
        super().__init__(parent, title=_("Insérer un tableau"))
        panel = wx.Panel(self)
        sizer = wx.BoxSizer(wx.VERTICAL)

        sizer.Add(wx.StaticText(panel, label=_("Nombre de lignes :")),
                  0, wx.ALL, 4)
        self.spin_rows = wx.SpinCtrl(panel, min=1, max=100, initial=2,
                                     name=_("Nombre de lignes"))
        sizer.Add(self.spin_rows, 0, wx.EXPAND | wx.ALL, 4)

        sizer.Add(wx.StaticText(panel, label=_("Nombre de colonnes :")),
                  0, wx.ALL, 4)
        self.spin_cols = wx.SpinCtrl(panel, min=1, max=20, initial=2,
                                     name=_("Nombre de colonnes"))
        sizer.Add(self.spin_cols, 0, wx.EXPAND | wx.ALL, 4)

        self.chk_header = wx.CheckBox(
            panel, label=_("Première ligne d'en-tête"),
            name=_("Première ligne d'en-tête"))
        self.chk_header.SetValue(True)
        sizer.Add(self.chk_header, 0, wx.ALL, 8)

        btns = self.CreateButtonSizer(wx.OK | wx.CANCEL)
        sizer.Add(btns, 0, wx.EXPAND | wx.ALL, 8)

        panel.SetSizer(sizer)
        sizer.Fit(panel)
        self.Fit()

        wx.CallAfter(self.spin_rows.SetFocus)

    def get_values(self):
        return (self.spin_rows.GetValue(), self.spin_cols.GetValue(),
                self.chk_header.GetValue())
