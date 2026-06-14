"""Spike accessibilite NVDA : wx.html.HtmlWindow vs wx.TextCtrl lecture seule.

But : verifier EMPIRIQUEMENT, avec NVDA actif, si le rendu HTML d'un HtmlWindow
est lu par NVDA (titres, liens, sauts H/K du mode navigation), ou s'il est muet.

Lancer (venv du projet) :
    venv\\Scripts\\python.exe test_nvda.py

Protocole :
  1. Le focus demarre dans le volet GAUCHE (HtmlWindow). Fleches haut/bas, puis
     touches H (titres) et K (liens) du mode navigation NVDA. NVDA lit-il quelque
     chose ?
  2. Tab vers le volet DROITE (TextCtrl) : fleche ligne par ligne -> NVDA doit
     lire chaque ligne proprement.
  3. Comparer.
"""

import wx
import wx.html

HTML = """<h1>Titre niveau 1</h1>
<h2>Titre niveau 2</h2>
<p>Un paragraphe avec du <b>gras</b> et un
<a href="https://example.com">lien vers example</a>.</p>
<ul><li>Premier element</li><li>Deuxieme element</li></ul>
<table border="1">
<tr><th>Nom</th><th>Valeur</th></tr>
<tr><td>Alpha</td><td>1</td></tr>
</table>"""

TEXTE = (
    "Titre niveau 1\n"
    "Titre niveau 2\n"
    "Un paragraphe avec du gras et un lien : example (https://example.com).\n"
    "Element de liste : Premier element\n"
    "Element de liste : Deuxieme element\n"
    "Tableau, ligne d'entete : Nom, Valeur\n"
    "Ligne : Alpha, 1"
)


class Frame(wx.Frame):
    def __init__(self):
        super().__init__(None, title="Test NVDA : HtmlWindow vs TextCtrl",
                         size=(960, 600))
        panel = wx.Panel(self)
        row = wx.BoxSizer(wx.HORIZONTAL)

        left = wx.BoxSizer(wx.VERTICAL)
        left.Add(wx.StaticText(panel, label="GAUCHE - Apercu HtmlWindow (rendu HTML) :"),
                 0, wx.ALL, 4)
        self.html = wx.html.HtmlWindow(panel, name="Apercu HTML rendu")
        self.html.SetPage(HTML)
        left.Add(self.html, 1, wx.EXPAND | wx.ALL, 4)

        right = wx.BoxSizer(wx.VERTICAL)
        right.Add(wx.StaticText(panel, label="DROITE - Apercu TextCtrl lecture seule (texte) :"),
                  0, wx.ALL, 4)
        self.txt = wx.TextCtrl(panel, style=wx.TE_MULTILINE | wx.TE_READONLY,
                               name="Apercu texte")
        self.txt.SetValue(TEXTE)
        right.Add(self.txt, 1, wx.EXPAND | wx.ALL, 4)

        row.Add(left, 1, wx.EXPAND)
        row.Add(right, 1, wx.EXPAND)
        panel.SetSizer(row)
        self.html.SetFocus()


if __name__ == "__main__":
    app = wx.App(False)
    Frame().Show()
    app.MainLoop()
