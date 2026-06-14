"""Fenêtre principale de MarkdownAccess.

Éditeur Markdown en wx.TextCtrl natif (lu par NVDA), menus + accélérateurs,
formatage assisté avec annonces vocales, navigation par titres, et aperçu HTML
bascule (F6) via wx.html2.WebView (WebView2) avec repli navigateur.
"""

import os
import tempfile
import webbrowser

import wx

try:
    import wx.html2
    _HAS_HTML2 = True
except Exception:
    _HAS_HTML2 = False

from app.core import renderer, settings as cfg, speech
from app.core import outline as outline_mod
from app.core import search as search_mod
from app.core.document import Document
from app.core.i18n import _translate as _
from app.core.markdown_actions import MarkdownActions
from app.ui.find_dialog import FindDialog
from app.ui.link_dialog import LinkDialog
from app.version import APP_NAME, __version__

# IDs personnalisés (non traduits, usage interne).
ID_EXPORT_HTML = wx.NewIdRef()
ID_BOLD = wx.NewIdRef()
ID_ITALIC = wx.NewIdRef()
ID_CODE = wx.NewIdRef()
ID_H1 = wx.NewIdRef()
ID_H2 = wx.NewIdRef()
ID_H3 = wx.NewIdRef()
ID_UL = wx.NewIdRef()
ID_OL = wx.NewIdRef()
ID_QUOTE = wx.NewIdRef()
ID_CODEBLOCK = wx.NewIdRef()
ID_LINK = wx.NewIdRef()
ID_FIND = wx.NewIdRef()
ID_FIND_NEXT = wx.NewIdRef()
ID_FIND_PREV = wx.NewIdRef()
ID_TOGGLE_PREVIEW = wx.NewIdRef()
ID_OUTLINE = wx.NewIdRef()
ID_NEXT_HEADING = wx.NewIdRef()
ID_PREV_HEADING = wx.NewIdRef()
ID_SHORTCUTS = wx.NewIdRef()


class MainWindow(wx.Frame):
    def __init__(self, parent):
        super().__init__(parent, title=APP_NAME, size=(1000, 700))
        self.settings = cfg.load()
        self.document = Document()

        # Dernière recherche (réutilisée par F3 / Maj+F3).
        self._find_term = ""
        self._find_case = False

        self.panel = wx.Panel(self)
        self.sizer = wx.BoxSizer(wx.VERTICAL)

        wrap = wx.TE_DONTWRAP if not self.settings.get("word_wrap", True) else 0
        self.editor = wx.TextCtrl(
            self.panel,
            style=wx.TE_MULTILINE | wx.TE_RICH2 | wrap,
            name=_("Éditeur Markdown"),
        )
        self.sizer.Add(self.editor, 1, wx.EXPAND)

        # WebView2 pour l'aperçu (créée si le backend Edge est dispo).
        self.webview = None
        self.preview_visible = False
        self._init_webview()

        self.panel.SetSizer(self.sizer)
        self.actions = MarkdownActions(self.editor)

        self._build_menu_bar()
        self._build_statusbar()
        self._bind_events()

        self._update_title()
        self._update_cursor()

        if self.settings.get("window_maximized", True):
            self.Maximize()
        wx.CallAfter(self.editor.SetFocus)

    # ---- construction UI ----------------------------------------------

    # Écouteur clavier injecté dans la page d'aperçu : F6 / Échap renvoient à
    # l'éditeur via le canal postMessage (sinon WebView2 capture la touche et
    # l'accélérateur de menu ne la voit jamais).
    _PREVIEW_KEY_SCRIPT = (
        "document.addEventListener('keydown', function(e){"
        "if(e.key==='F6'){e.preventDefault();"
        "if(window.wx&&window.wx.postMessage)window.wx.postMessage('back');}});"
    )

    def _init_webview(self):
        if not _HAS_HTML2:
            return
        try:
            backend = wx.html2.WebViewBackendDefault
            if wx.html2.WebView.IsBackendAvailable(wx.html2.WebViewBackendEdge):
                backend = wx.html2.WebViewBackendEdge
            self.webview = wx.html2.WebView.New(
                self.panel, backend=backend, name=_("Aperçu HTML")
            )
            self.webview.Hide()
            self.sizer.Add(self.webview, 1, wx.EXPAND)
            # Canal de retour page -> app pour la touche F6/Échap.
            try:
                self.webview.AddScriptMessageHandler("wx")
                self.webview.AddUserScript(self._PREVIEW_KEY_SCRIPT)
                self.webview.Bind(
                    wx.html2.EVT_WEBVIEW_SCRIPT_MESSAGE_RECEIVED,
                    self._on_webview_message,
                )
            except Exception:
                pass
            # Filet de sécurité : si jamais wx reçoit la touche depuis la WebView.
            self.webview.Bind(wx.EVT_KEY_DOWN, self._on_webview_key)
        except Exception:
            self.webview = None

    def _on_webview_message(self, evt):
        if evt.GetString() == "back":
            wx.CallAfter(self._show_editor)

    def _on_webview_key(self, evt):
        if evt.GetKeyCode() == wx.WXK_F6:
            wx.CallAfter(self._show_editor)
        else:
            evt.Skip()

    def _build_menu_bar(self):
        mb = wx.MenuBar()

        # Fichier
        m_file = wx.Menu()
        m_file.Append(wx.ID_NEW, _("&Nouveau\tCtrl+N"))
        m_file.Append(wx.ID_OPEN, _("&Ouvrir...\tCtrl+O"))
        m_file.Append(wx.ID_SAVE, _("&Enregistrer\tCtrl+S"))
        m_file.Append(wx.ID_SAVEAS, _("Enregistrer &sous...\tCtrl+Shift+S"))
        m_file.AppendSeparator()
        m_file.Append(ID_EXPORT_HTML, _("Exporter en &HTML..."))
        m_file.AppendSeparator()
        m_file.Append(wx.ID_EXIT, _("&Quitter\tAlt+F4"))
        mb.Append(m_file, _("&Fichier"))

        # Édition (géré nativement par wx.TextCtrl)
        m_edit = wx.Menu()
        m_edit.Append(wx.ID_UNDO, _("&Annuler\tCtrl+Z"))
        m_edit.Append(wx.ID_REDO, _("&Rétablir\tCtrl+Y"))
        m_edit.AppendSeparator()
        m_edit.Append(wx.ID_CUT, _("Co&uper\tCtrl+X"))
        m_edit.Append(wx.ID_COPY, _("&Copier\tCtrl+C"))
        m_edit.Append(wx.ID_PASTE, _("C&oller\tCtrl+V"))
        m_edit.Append(wx.ID_SELECTALL, _("&Tout sélectionner\tCtrl+A"))
        m_edit.AppendSeparator()
        m_edit.Append(ID_FIND, _("&Rechercher...\tCtrl+F"))
        m_edit.Append(ID_FIND_NEXT, _("Rechercher le &suivant\tF3"))
        m_edit.Append(ID_FIND_PREV, _("Rechercher le &précédent\tShift+F3"))
        mb.Append(m_edit, _("&Édition"))

        # Format
        m_fmt = wx.Menu()
        m_fmt.Append(ID_BOLD, _("&Gras\tCtrl+B"))
        m_fmt.Append(ID_ITALIC, _("&Italique\tCtrl+I"))
        m_fmt.Append(ID_CODE, _("Code &inline\tCtrl+`"))
        m_fmt.AppendSeparator()
        m_fmt.Append(ID_H1, _("Titre niveau &1\tCtrl+1"))
        m_fmt.Append(ID_H2, _("Titre niveau &2\tCtrl+2"))
        m_fmt.Append(ID_H3, _("Titre niveau &3\tCtrl+3"))
        m_fmt.AppendSeparator()
        m_fmt.Append(ID_UL, _("Liste à &puces\tCtrl+Shift+U"))
        m_fmt.Append(ID_OL, _("Liste &numérotée\tCtrl+Shift+L"))
        m_fmt.Append(ID_QUOTE, _("&Citation\tCtrl+Q"))
        m_fmt.Append(ID_CODEBLOCK, _("&Bloc de code\tCtrl+Shift+K"))
        m_fmt.AppendSeparator()
        m_fmt.Append(ID_LINK, _("&Lien...\tCtrl+K"))
        mb.Append(m_fmt, _("&Format"))

        # Affichage
        m_view = wx.Menu()
        m_view.Append(ID_TOGGLE_PREVIEW, _("Basculer texte / aperçu &HTML\tF6"))
        m_view.AppendSeparator()
        m_view.Append(ID_OUTLINE, _("&Plan du document...\tCtrl+Shift+O"))
        m_view.Append(ID_NEXT_HEADING, _("Titre &suivant\tAlt+Down"))
        m_view.Append(ID_PREV_HEADING, _("Titre &précédent\tAlt+Up"))
        mb.Append(m_view, _("&Affichage"))

        # Aide
        m_help = wx.Menu()
        m_help.Append(ID_SHORTCUTS, _("&Raccourcis clavier"))
        m_help.Append(wx.ID_ABOUT, _("À &propos de MarkdownAccess"))
        mb.Append(m_help, _("&Aide"))

        self.SetMenuBar(mb)

    def _build_statusbar(self):
        self.statusbar = self.CreateStatusBar(2)
        self.statusbar.SetStatusWidths([-1, 200])
        self.statusbar.SetStatusText(_("Prêt"), 0)

    def _bind_events(self):
        self.editor.Bind(wx.EVT_TEXT, self._on_text)
        self.editor.Bind(wx.EVT_KEY_UP, self._update_cursor)
        self.editor.Bind(wx.EVT_LEFT_UP, self._update_cursor)
        self.Bind(wx.EVT_CLOSE, self._on_close)
        self.Bind(wx.EVT_ACTIVATE, self._on_activate)

        b = lambda func, ident: self.Bind(wx.EVT_MENU, func, id=ident)
        b(self._on_new, wx.ID_NEW)
        b(self._on_open, wx.ID_OPEN)
        b(self._on_save, wx.ID_SAVE)
        b(self._on_save_as, wx.ID_SAVEAS)
        b(self._on_export_html, ID_EXPORT_HTML)
        b(lambda e: self.Close(), wx.ID_EXIT)

        b(lambda e: self.editor.Undo(), wx.ID_UNDO)
        b(lambda e: self.editor.Redo(), wx.ID_REDO)
        b(lambda e: self.editor.Cut(), wx.ID_CUT)
        b(lambda e: self.editor.Copy(), wx.ID_COPY)
        b(lambda e: self.editor.Paste(), wx.ID_PASTE)
        b(lambda e: self.editor.SelectAll(), wx.ID_SELECTALL)

        b(self._on_find, ID_FIND)
        b(lambda e: self._do_find(forward=True), ID_FIND_NEXT)
        b(lambda e: self._do_find(forward=False), ID_FIND_PREV)

        b(lambda e: self._do(self.actions.bold), ID_BOLD)
        b(lambda e: self._do(self.actions.italic), ID_ITALIC)
        b(lambda e: self._do(self.actions.inline_code), ID_CODE)
        b(lambda e: self._do(lambda: self.actions.heading(1)), ID_H1)
        b(lambda e: self._do(lambda: self.actions.heading(2)), ID_H2)
        b(lambda e: self._do(lambda: self.actions.heading(3)), ID_H3)
        b(lambda e: self._do(self.actions.bullet_list), ID_UL)
        b(lambda e: self._do(self.actions.numbered_list), ID_OL)
        b(lambda e: self._do(self.actions.blockquote), ID_QUOTE)
        b(lambda e: self._do(self.actions.code_block), ID_CODEBLOCK)
        b(self._on_link, ID_LINK)

        b(self._on_toggle_preview, ID_TOGGLE_PREVIEW)
        b(self._on_outline, ID_OUTLINE)
        b(lambda e: self._jump_heading(forward=True), ID_NEXT_HEADING)
        b(lambda e: self._jump_heading(forward=False), ID_PREV_HEADING)

        b(self._on_shortcuts, ID_SHORTCUTS)
        b(self._on_about, wx.ID_ABOUT)

    # ---- helpers -------------------------------------------------------

    def _do(self, action):
        """Exécute une action de formatage et annonce le résultat."""
        msg = action()
        if msg:
            speech.speak(msg, interrupt=True)

    def _on_activate(self, evt):
        # Au retour d'Alt+Tab, Windows ne restaure pas toujours le focus sur le
        # bon enfant (NVDA annonce alors le panneau). On force le focus sur le
        # contrôle actif : aperçu si visible, sinon l'éditeur.
        if evt.GetActive():
            target = self.webview if (self.preview_visible and self.webview) else self.editor
            if target:
                wx.CallAfter(target.SetFocus)
        evt.Skip()

    def _update_title(self):
        name = self.document.filename or _("Sans titre")
        star = "* " if self.document.dirty else ""
        self.SetTitle(f"{star}{name} — {APP_NAME}")

    def _update_cursor(self, evt=None):
        pos = self.editor.GetInsertionPoint()
        res = self.editor.PositionToXY(pos)
        if isinstance(res, (tuple, list)) and len(res) == 3:
            _ok, col, row = res
        else:
            col, row = res
        self.statusbar.SetStatusText(
            _("Ligne {l}, Colonne {c}").format(l=row + 1, c=col + 1), 1
        )
        if evt:
            evt.Skip()

    def _current_row(self):
        pos = self.editor.GetInsertionPoint()
        res = self.editor.PositionToXY(pos)
        if isinstance(res, (tuple, list)) and len(res) == 3:
            return res[2]
        return res[1]

    # ---- modifié / fichiers -------------------------------------------

    def _on_text(self, evt):
        if not self.document.dirty:
            self.document.dirty = True
            self._update_title()
        evt.Skip()

    def _confirm_discard(self) -> bool:
        """True si on peut continuer (pas modifié, ou l'utilisateur a tranché)."""
        if not self.document.dirty:
            return True
        dlg = wx.MessageDialog(
            self,
            _("Le document a été modifié. Enregistrer les modifications ?"),
            APP_NAME,
            wx.YES_NO | wx.CANCEL | wx.ICON_QUESTION,
        )
        res = dlg.ShowModal()
        dlg.Destroy()
        if res == wx.ID_CANCEL:
            return False
        if res == wx.ID_YES:
            return self._on_save(None)
        return True

    def _on_new(self, evt):
        if not self._confirm_discard():
            return
        self.editor.SetValue("")
        self.document = Document()
        self.actions = MarkdownActions(self.editor)
        self._update_title()
        speech.speak(_("Nouveau document"))

    def _on_open(self, evt):
        if not self._confirm_discard():
            return
        with wx.FileDialog(
            self, _("Ouvrir un fichier Markdown"),
            defaultDir=self.settings.get("last_folder", ""),
            wildcard=_("Fichiers Markdown (*.md;*.markdown;*.txt)|*.md;*.markdown;*.txt|Tous les fichiers (*.*)|*.*"),
            style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST,
        ) as dlg:
            if dlg.ShowModal() != wx.ID_OK:
                return
            path = dlg.GetPath()
        try:
            text = self.document.load(path)
        except Exception as exc:
            wx.MessageBox(_("Impossible d'ouvrir le fichier : {err}").format(err=exc),
                          APP_NAME, wx.OK | wx.ICON_ERROR)
            return
        self.editor.SetValue(text)
        self.document.dirty = False
        self.settings["last_folder"] = os.path.dirname(path)
        cfg.push_recent_file(self.settings, path)
        cfg.save(self.settings)
        self._update_title()
        speech.speak(_("Document ouvert : {name}").format(name=self.document.filename))

    def _on_save(self, evt) -> bool:
        if not self.document.path:
            return self._on_save_as(evt)
        try:
            self.document.save(self.editor.GetValue())
        except Exception as exc:
            wx.MessageBox(_("Impossible d'enregistrer : {err}").format(err=exc),
                          APP_NAME, wx.OK | wx.ICON_ERROR)
            return False
        self._update_title()
        speech.speak(_("Enregistré"))
        return True

    def _on_save_as(self, evt) -> bool:
        with wx.FileDialog(
            self, _("Enregistrer sous"),
            defaultDir=self.settings.get("last_folder", ""),
            wildcard=_("Fichiers Markdown (*.md)|*.md|Tous les fichiers (*.*)|*.*"),
            style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT,
        ) as dlg:
            if dlg.ShowModal() != wx.ID_OK:
                return False
            path = dlg.GetPath()
        try:
            self.document.save(self.editor.GetValue(), path)
        except Exception as exc:
            wx.MessageBox(_("Impossible d'enregistrer : {err}").format(err=exc),
                          APP_NAME, wx.OK | wx.ICON_ERROR)
            return False
        self.settings["last_folder"] = os.path.dirname(path)
        cfg.push_recent_file(self.settings, path)
        cfg.save(self.settings)
        self._update_title()
        speech.speak(_("Enregistré"))
        return True

    def _on_export_html(self, evt):
        with wx.FileDialog(
            self, _("Exporter en HTML"),
            defaultDir=self.settings.get("last_folder", ""),
            wildcard=_("Fichiers HTML (*.html)|*.html"),
            style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT,
        ) as dlg:
            if dlg.ShowModal() != wx.ID_OK:
                return
            path = dlg.GetPath()
        title = self.document.filename or _("Document")
        html = renderer.render_document(self.editor.GetValue(), title=title)
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(html)
        except Exception as exc:
            wx.MessageBox(_("Impossible d'exporter : {err}").format(err=exc),
                          APP_NAME, wx.OK | wx.ICON_ERROR)
            return
        speech.speak(_("Exporté en HTML"))

    # ---- format / lien -------------------------------------------------

    def _on_link(self, evt):
        sel = self.editor.GetStringSelection()
        dlg = LinkDialog(self, default_text=sel)
        if dlg.ShowModal() == wx.ID_OK:
            text, url = dlg.get_values()
            if url:
                self._do(lambda: self.actions.insert_link(text or url, url))
        dlg.Destroy()

    # ---- recherche -----------------------------------------------------

    def _on_find(self, evt):
        # Pré-remplit avec la sélection courante, sinon le dernier terme.
        sel = self.editor.GetStringSelection()
        default = sel if sel else self._find_term
        dlg = FindDialog(self, default_term=default, case_sensitive=self._find_case)
        if dlg.ShowModal() == wx.ID_OK:
            term, case = dlg.get_values()
            self._find_term = term
            self._find_case = case
            self._do_find(forward=True)
        dlg.Destroy()

    def _do_find(self, forward=True):
        if not self._find_term:
            self._on_find(None)
            return
        text = self.editor.GetValue()
        # On repart de la fin de la sélection (avant, en arrière) pour avancer.
        sel_start, sel_end = self.editor.GetSelection()
        start = sel_end if forward else sel_start
        res = search_mod.find(text, self._find_term, start, forward, self._find_case)
        if res is None:
            speech.speak(_("Texte introuvable"), interrupt=True)
            self.statusbar.SetStatusText(_("Texte introuvable"), 0)
            return
        a, b = res
        self.editor.SetSelection(a, b)
        self.editor.ShowPosition(a)
        self.editor.SetFocus()
        # NVDA n'annonce pas une sélection posée par programme : on lit la ligne.
        res_xy = self.editor.PositionToXY(a)
        row = res_xy[2] if len(res_xy) == 3 else res_xy[1]
        speech.speak(self.editor.GetLineText(row), interrupt=True)
        self._update_cursor()

    # ---- aperçu --------------------------------------------------------

    def _on_toggle_preview(self, evt=None):
        if self.preview_visible:
            self._show_editor()
            return
        html = renderer.render_document(self.editor.GetValue())
        if self.webview is not None:
            self.webview.SetPage(html, "")
            self.editor.Hide()
            self.webview.Show()
            self.panel.Layout()
            self.preview_visible = True
            wx.CallAfter(self.webview.SetFocus)
            speech.speak(_("Aperçu HTML"))
        else:
            self._open_in_browser(html)
            speech.speak(_("Aperçu ouvert dans le navigateur"))

    def _show_editor(self):
        if self.webview is not None:
            self.webview.Hide()
        self.editor.Show()
        self.panel.Layout()
        self.preview_visible = False
        wx.CallAfter(self.editor.SetFocus)
        speech.speak(_("Édition"))

    def _open_in_browser(self, html: str):
        fd, path = tempfile.mkstemp(suffix=".html", prefix="markdownaccess_")
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(html)
        webbrowser.open(f"file://{path}")

    # ---- navigation par titres ----------------------------------------

    def _on_outline(self, evt):
        headings = outline_mod.parse_headings(self.editor.GetValue())
        if not headings:
            speech.speak(_("Aucun titre dans le document"))
            wx.MessageBox(_("Aucun titre dans le document."), APP_NAME,
                          wx.OK | wx.ICON_INFORMATION)
            return
        labels = ["  " * (lvl - 1) + text for lvl, text, _line in headings]
        dlg = wx.SingleChoiceDialog(self, _("Aller au titre :"),
                                    _("Plan du document"), labels)
        if dlg.ShowModal() == wx.ID_OK:
            idx = dlg.GetSelection()
            self._goto_line(headings[idx][2])
        dlg.Destroy()

    def _jump_heading(self, forward: bool):
        headings = outline_mod.parse_headings(self.editor.GetValue())
        if not headings:
            speech.speak(_("Aucun titre"))
            return
        row = self._current_row()
        target = (outline_mod.next_heading_line(headings, row) if forward
                  else outline_mod.prev_heading_line(headings, row))
        if not target:
            speech.speak(_("Aucun titre") if forward else _("Aucun titre"))
            return
        level, text, line = target
        self._goto_line(line)
        speech.speak(_("Titre niveau {n} : {t}").format(n=level, t=text))

    def _goto_line(self, row: int):
        pos = self.editor.XYToPosition(0, row)
        self.editor.SetInsertionPoint(pos)
        self.editor.ShowPosition(pos)
        if not self.preview_visible:
            self.editor.SetFocus()
        self._update_cursor()

    # ---- aide ----------------------------------------------------------

    def _on_shortcuts(self, evt):
        text = _(
            "Raccourcis clavier :\n\n"
            "Ctrl+N Nouveau, Ctrl+O Ouvrir, Ctrl+S Enregistrer\n"
            "Ctrl+F Rechercher, F3 / Maj+F3 Suivant / Précédent\n"
            "Ctrl+B Gras, Ctrl+I Italique, Ctrl+` Code\n"
            "Ctrl+1/2/3 Titres, Ctrl+K Lien\n"
            "Ctrl+Maj+U Liste à puces, Ctrl+Maj+L Liste numérotée\n"
            "Ctrl+Q Citation, Ctrl+Maj+K Bloc de code\n"
            "F6 Aperçu HTML, Ctrl+Maj+O Plan\n"
            "Alt+Bas / Alt+Haut Titre suivant / précédent"
        )
        wx.MessageBox(text, _("Raccourcis clavier"), wx.OK | wx.ICON_INFORMATION)

    def _on_about(self, evt):
        wx.MessageBox(
            f"{APP_NAME} {__version__}\n\n" +
            _("Éditeur Markdown accessible pour NVDA."),
            _("À propos de MarkdownAccess"), wx.OK | wx.ICON_INFORMATION)

    # ---- fermeture -----------------------------------------------------

    def _on_close(self, evt):
        if not self._confirm_discard():
            if evt.CanVeto():
                evt.Veto()
            return
        self.settings["window_maximized"] = self.IsMaximized()
        cfg.save(self.settings)
        self.Destroy()
