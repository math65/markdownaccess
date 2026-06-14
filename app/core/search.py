"""Recherche de texte (logique pure, testable sans wx).

Renvoie des indices caractère dans la chaîne fournie. La fenêtre fait le lien
avec le `wx.TextCtrl` (sélection, défilement, annonce vocale).
"""


def find(text, term, start, forward=True, case_sensitive=False):
    """Cherche `term` dans `text` à partir de l'indice `start`.

    Recherche **circulaire** : si rien n'est trouvé jusqu'au bord, on reprend de
    l'autre extrémité. Renvoie le couple (début, fin) de l'occurrence, ou
    ``None`` si `term` est vide ou absent.
    """
    if not term:
        return None

    haystack = text if case_sensitive else text.lower()
    needle = term if case_sensitive else term.lower()

    if forward:
        idx = haystack.find(needle, start)
        if idx == -1:                       # repli : on repart du début
            idx = haystack.find(needle, 0)
    else:
        idx = haystack.rfind(needle, 0, start)
        if idx == -1:                       # repli : on repart de la fin
            idx = haystack.rfind(needle)

    if idx == -1:
        return None
    return idx, idx + len(needle)
