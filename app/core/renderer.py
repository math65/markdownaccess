"""Rendu Markdown -> HTML sémantique, via mistune.

Lifté de DownAccess (scripts/build_docs.py) : on garde le slug d'ancre sur les
titres pour la navigation, mais **sans CSS pour l'instant** (décision produit :
HTML classique d'abord, présentation plus tard). La sémantique (vrais h1-h6,
ul/ol, a, table+th) est ce qui rend NVDA efficace en mode navigation.
"""

import re

import mistune

_TAG_RE = re.compile(r"<[^>]+>")


def slug(text: str) -> str:
    s = _TAG_RE.sub("", text).lower()
    s = re.sub(r"[^\w\s-]", "", s, flags=re.UNICODE)
    return re.sub(r"\s+", "-", s.strip())


class AccessibleRenderer(mistune.HTMLRenderer):
    """Ajoute un id (ancre) sur chaque titre -> navigation par titres."""

    def heading(self, text, level, **attrs):
        return f'<h{level} id="{slug(text)}">{text}</h{level}>\n'


_markdown = mistune.create_markdown(
    renderer=AccessibleRenderer(escape=False),
    plugins=["table", "strikethrough", "url"],
)

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
    return _markdown(md_text or "")


def render_document(md_text: str, title: str = "Aperçu", lang: str = "fr") -> str:
    """Document HTML autonome (doctype + lang + charset), sans CSS pour l'instant.

    Utilisé pour l'aperçu WebView2, l'export HTML et le repli navigateur.
    """
    return _TEMPLATE.format(lang=lang, title=title, body=render_body(md_text))
