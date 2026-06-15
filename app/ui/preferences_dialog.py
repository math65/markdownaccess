"""Dialogue Préférences : langue et retour à la ligne.

Chaque contrôle est précédé d'un wx.StaticText (règle d'accessibilité maison).
Les choix sont appliqués au prochain démarrage (la langue est installée dans
main.py et le style de retour à la ligne est posé à la création de l'éditeur) ;
l'appelant en informe l'utilisateur.
"""

import wx

from app.core.i18n import _translate as _

# (valeur stockée, msgid du libellé). msgid brut : traduit dans __init__ pour
# respecter le pattern paresseux i18n (jamais de _() figé au niveau module).
# L'ordre fixe l'index du wx.Choice.
_LANGUAGES = [
    ("auto", "Automatique (langue du système)"),
    ("fr", "Français"),
    ("en", "English"),
]


class PreferencesDialog(wx.Dialog):
    def __init__(self, parent, language="auto", word_wrap=True):
        super().__init__(parent, title=_("Préférences"))
        panel = wx.Panel(self)
        sizer = wx.BoxSizer(wx.VERTICAL)

        sizer.Add(wx.StaticText(panel, label=_("Langue de l'interface :")),
                  0, wx.ALL, 4)
        self.choice_lang = wx.Choice(
            panel, choices=[_(msgid) for _val, msgid in _LANGUAGES],
            name=_("Langue de l'interface"))
        values = [val for val, _label in _LANGUAGES]
        self.choice_lang.SetSelection(values.index(language)
                                      if language in values else 0)
        sizer.Add(self.choice_lang, 0, wx.EXPAND | wx.ALL, 4)

        self.chk_wrap = wx.CheckBox(
            panel, label=_("Retour à la ligne automatique"),
            name=_("Retour à la ligne automatique"))
        self.chk_wrap.SetValue(bool(word_wrap))
        sizer.Add(self.chk_wrap, 0, wx.ALL, 8)

        # Boutons parentés au panneau (et non au dialogue) : un sizer ne peut
        # positionner que des contrôles enfants de sa fenêtre. CreateButtonSizer
        # les parenterait au dialogue → assertion wx. Voir find_dialog.py.
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

        wx.CallAfter(self.choice_lang.SetFocus)

    def get_values(self):
        lang = _LANGUAGES[self.choice_lang.GetSelection()][0]
        return {"language": lang, "word_wrap": self.chk_wrap.GetValue()}
