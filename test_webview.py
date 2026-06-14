"""Spike accessibilite NVDA : wx.html2.WebView (moteur Edge WebView2 de Windows).

But : verifier si NVDA lit le rendu HTML d'une WebView2 INTEGREE (mode navigation,
sauts H / K / T). Le bug qui l'empechait est cense etre corrige dans NVDA 2026.1.

Lancer (venv du projet) :
    venv\\Scripts\\python.exe test_webview.py

Protocole (NVDA actif) :
  - Le focus demarre dans la WebView. Fleches haut/bas pour lire.
  - Touche H -> NVDA saute-t-il les titres ("Titre niveau 1/2") ?
  - Touche K -> annonce-t-il le lien ?
  - Touche T -> trouve-t-il le tableau ?
  - Regarde aussi le bandeau du haut : indique quel backend est utilise (Edge ou
    repli IE). Si ce n'est pas Edge, NVDA sera moins fiable.

Note ta version de NVDA (menu NVDA > Aide > A propos) pour interpreter le resultat.
"""

import wx
import wx.html2

HTML = """<!DOCTYPE html>
<html lang="fr">
<head><meta charset="utf-8"><title>Apercu</title></head>
<body>
<h1>Titre niveau 1</h1>
<h2>Titre niveau 2</h2>
<p>Un paragraphe avec du <b>gras</b> et un
<a href="https://example.com">lien vers example</a>.</p>
<ul><li>Premier element</li><li>Deuxieme element</li></ul>
<table border="1">
<tr><th>Nom</th><th>Valeur</th></tr>
<tr><td>Alpha</td><td>1</td></tr>
</table>
</body>
</html>"""


class Frame(wx.Frame):
    def __init__(self):
        super().__init__(None, title="Test NVDA : wx.html2.WebView (Edge WebView2)",
                         size=(960, 640))

        # Choix du backend : Edge (WebView2) si dispo, sinon repli par defaut.
        backend = wx.html2.WebViewBackendDefault
        label = "Backend : defaut (IE/MSHTML) - Edge WebView2 non disponible"
        if wx.html2.WebView.IsBackendAvailable(wx.html2.WebViewBackendEdge):
            backend = wx.html2.WebViewBackendEdge
            label = "Backend : Edge (WebView2) - moteur HTML integre a Windows"

        panel = wx.Panel(self)
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(wx.StaticText(panel, label=label), 0, wx.ALL, 6)

        self.wv = wx.html2.WebView.New(panel, backend=backend, name="Apercu HTML")
        self.wv.SetPage(HTML, "")
        sizer.Add(self.wv, 1, wx.EXPAND | wx.ALL, 4)

        panel.SetSizer(sizer)
        wx.CallAfter(self.wv.SetFocus)


if __name__ == "__main__":
    app = wx.App(False)
    Frame().Show()
    app.MainLoop()
