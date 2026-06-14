"""Moteur de formatage assisté Markdown, opérant sur un wx.TextCtrl.

Chaque méthode publique modifie le texte (sélection / ligne courante) et **retourne
la chaîne d'annonce** (FR source). L'UI se charge de l'annoncer via speech.speak.

Aucune dépendance wx ici hormis le contrôle passé : la classe ne fait qu'appeler
GetSelection / GetStringSelection / Replace / SetSelection / SetInsertionPoint.
"""

import re

from app.core.i18n import _translate as _


class MarkdownActions:
    def __init__(self, text_ctrl):
        self.tc = text_ctrl

    # ---- helpers -------------------------------------------------------

    def _xy(self, pos):
        """Retourne (col, row) pour une position, robuste cross-version."""
        res = self.tc.PositionToXY(pos)
        if isinstance(res, (tuple, list)) and len(res) == 3:
            _ok, col, row = res
        else:
            col, row = res
        return col, row

    def _current_line(self):
        """(line_start_pos, line_text) de la ligne contenant le curseur."""
        pos = self.tc.GetInsertionPoint()
        _col, row = self._xy(pos)
        line_start = self.tc.XYToPosition(0, row)
        line_text = self.tc.GetLineText(row)
        return line_start, line_text

    def _block(self):
        """(start, end, block_text) couvrant toutes les lignes de la sélection."""
        s, e = self.tc.GetSelection()
        text = self.tc.GetValue()
        bs = text.rfind("\n", 0, s) + 1
        be = text.find("\n", e)
        if be == -1:
            be = len(text)
        return bs, be, text[bs:be]

    # ---- inline (wrap / unwrap) ---------------------------------------

    def _toggle_wrap(self, marker, name_on, name_off):
        tc = self.tc
        start, end = tc.GetSelection()
        sel = tc.GetStringSelection()
        m = len(marker)
        if sel and sel.startswith(marker) and sel.endswith(marker) and len(sel) >= 2 * m:
            inner = sel[m:-m]
            tc.Replace(start, end, inner)
            tc.SetSelection(start, start + len(inner))
            return name_off
        if sel:
            tc.Replace(start, end, f"{marker}{sel}{marker}")
            tc.SetSelection(start + m, start + m + len(sel))
            return name_on
        pos = tc.GetInsertionPoint()
        tc.Replace(pos, pos, f"{marker}{marker}")
        tc.SetInsertionPoint(pos + m)
        return name_on

    def bold(self):
        return self._toggle_wrap("**", _("Gras"), _("Gras désactivé"))

    def italic(self):
        return self._toggle_wrap("*", _("Italique"), _("Italique désactivé"))

    def inline_code(self):
        return self._toggle_wrap("`", _("Code"), _("Code désactivé"))

    # ---- titres --------------------------------------------------------

    def heading(self, level: int):
        line_start, line_text = self._current_line()
        line_end = line_start + len(line_text)
        m = re.match(r"^(#{1,6})\s+", line_text)
        existing = len(m.group(1)) if m else 0
        stripped = re.sub(r"^#{1,6}\s+", "", line_text)
        if existing == level:
            self.tc.Replace(line_start, line_end, stripped)
            return _("Titre supprimé")
        self.tc.Replace(line_start, line_end, "#" * level + " " + stripped)
        return _("Titre niveau {n}").format(n=level)

    # ---- préfixes de ligne (listes, citation) --------------------------

    def bullet_list(self):
        bs, be, block = self._block()
        lines = block.split("\n")
        has = any(line.startswith("- ") for line in lines)
        if has:
            new = [line[2:] if line.startswith("- ") else line for line in lines]
            name = _("Liste à puces désactivée")
        else:
            new = [("- " + line) if line.strip() else line for line in lines]
            name = _("Liste à puces")
        self.tc.Replace(bs, be, "\n".join(new))
        return name

    def numbered_list(self):
        bs, be, block = self._block()
        lines = block.split("\n")
        has = any(re.match(r"^\d+\.\s", line) for line in lines)
        if has:
            new = [re.sub(r"^\d+\.\s", "", line) for line in lines]
            name = _("Liste numérotée désactivée")
        else:
            new = []
            n = 1
            for line in lines:
                if line.strip():
                    new.append(f"{n}. {line}")
                    n += 1
                else:
                    new.append(line)
            name = _("Liste numérotée")
        self.tc.Replace(bs, be, "\n".join(new))
        return name

    def blockquote(self):
        bs, be, block = self._block()
        lines = block.split("\n")
        has = any(line.startswith("> ") for line in lines)
        if has:
            new = [line[2:] if line.startswith("> ") else line for line in lines]
            name = _("Citation désactivée")
        else:
            new = [("> " + line) if line.strip() else line for line in lines]
            name = _("Citation")
        self.tc.Replace(bs, be, "\n".join(new))
        return name

    # ---- bloc de code / lien ------------------------------------------

    def code_block(self):
        tc = self.tc
        s, e = tc.GetSelection()
        sel = tc.GetStringSelection()
        if sel:
            tc.Replace(s, e, f"```\n{sel}\n```")
        else:
            pos = tc.GetInsertionPoint()
            tc.Replace(pos, pos, "```\n\n```")
            tc.SetInsertionPoint(pos + 4)
        return _("Bloc de code")

    def insert_link(self, text: str, url: str):
        tc = self.tc
        s, e = tc.GetSelection()
        md = f"[{text}]({url})"
        tc.Replace(s, e, md)
        tc.SetInsertionPoint(s + len(md))
        return _("Lien inséré")
