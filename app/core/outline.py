"""Analyse de la structure : liste des titres Markdown pour la navigation.

Ignore les `#` à l'intérieur des blocs de code clôturés (``` ou ~~~).
"""

import re

HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)$")


def parse_headings(text: str) -> list[tuple[int, str, int]]:
    """Retourne une liste de (niveau, texte, numéro_de_ligne_0based)."""
    headings: list[tuple[int, str, int]] = []
    in_fence = False
    for i, line in enumerate((text or "").split("\n")):
        stripped = line.lstrip()
        if stripped.startswith("```") or stripped.startswith("~~~"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        m = HEADING_RE.match(line)
        if m:
            headings.append((len(m.group(1)), m.group(2).strip(), i))
    return headings


def next_heading_line(headings, current_line: int):
    """Premier titre strictement après current_line, ou None."""
    for level, text, line in headings:
        if line > current_line:
            return level, text, line
    return None


def prev_heading_line(headings, current_line: int):
    """Premier titre strictement avant current_line, ou None."""
    result = None
    for level, text, line in headings:
        if line < current_line:
            result = (level, text, line)
        else:
            break
    return result
