"""Rendu Markdown -> HTML sémantique, via markdown-it-py.

On utilise markdown-it-py (conforme CommonMark) pour un rendu **prévisible** : ce
que l'utilisateur tape se comporte comme le standard, sans surprises sur l'inline
imbriqué. On ajoute un id (ancre) sur chaque titre pour la navigation, et on reste
**sans CSS pour l'instant** (décision produit). La sémantique seule (vrais h1-h6,
ul/ol, a, table+th) est ce qui rend NVDA efficace en mode navigation.
"""

import re

from markdown_it import MarkdownIt

_TAG_RE = re.compile(r"<[^>]+>")


def slug(text: str) -> str:
    s = _TAG_RE.sub("", text).lower()
    s = re.sub(r"[^\w\s-]", "", s, flags=re.UNICODE)
    return re.sub(r"\s+", "-", s.strip())


def _add_heading_ids(state):
    """Règle core : pose un id=slug sur chaque titre, lu après l'étape inline.

    Le token 'heading_open' est suivi du token 'inline' qui porte le texte brut
    du titre (.content). On en dérive l'ancre, ce qui évite tout post-traitement
    HTML (pas de dépendance d'analyse HTML).
    """
    tokens = state.tokens
    for i, tok in enumerate(tokens):
        if tok.type == "heading_open" and i + 1 < len(tokens):
            text = tokens[i + 1].content
            if text:
                tok.attrSet("id", slug(text))


def _build_markdown() -> MarkdownIt:
    # "commonmark" = base stricte ; html=True laisse passer le HTML inline tapé
    # par l'utilisateur (éditeur local, contenu de confiance). linkify off : on
    # n'auto-lie pas les URL nues (les liens [texte](url) et <url> marchent).
    md = MarkdownIt("commonmark", {"html": True})
    md.enable("table")
    md.enable("strikethrough")
    md.core.ruler.push("heading_ids", _add_heading_ids)
    return md


_markdown = _build_markdown()

_TEMPLATE = """<!DOCTYPE html>
<html lang="{lang}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
</head>
<body>
<main>
{body}
</main>
</body>
</html>
"""


def render_body(md_text: str) -> str:
    """Corps HTML sémantique seul (sans <html>/<head>)."""
    return _markdown.render(md_text or "")


def render_document(md_text: str, title: str = "Aperçu", lang: str = "fr") -> str:
    """Document HTML autonome (doctype + lang + charset), sans CSS pour l'instant.

    Utilisé pour l'aperçu WebView2, l'export HTML et le repli navigateur.
    """
    return _TEMPLATE.format(lang=lang, title=title, body=render_body(md_text))
