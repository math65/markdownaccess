# MarkdownAccess

Éditeur Markdown **accessible**, pensé d'abord pour les utilisateurs aveugles et
malvoyants sous lecteur d'écran (NVDA, JAWS). Écrit en Python + wxPython.

L'intérêt du Markdown pour ce public : c'est du **texte pur**, dont la structure
(titres, listes, gras, liens) est lisible et dictée en clair par le lecteur
d'écran — contrairement à un traitement de texte où la mise en forme est invisible
au clavier.

## Fonctionnalités

- **Édition** dans un `wx.TextCtrl` natif, lu correctement par NVDA (écho, suivi du
  curseur, sélection).
- **Formatage assisté** avec annonces vocales : gras (Ctrl+B), italique (Ctrl+I),
  titres (Ctrl+1/2/3), listes, citation, code, lien (Ctrl+K).
- **Aperçu HTML intégré** via `wx.html2.WebView` (WebView2), bascule avec **F6** —
  NVDA y entre en mode navigation (sauts par titre / lien / tableau). Repli
  automatique sur le navigateur par défaut si WebView2 est absent.
- **Navigation par structure** : titre suivant/précédent (Alt+Bas/Haut), plan du
  document (Ctrl+Maj+O).
- **Fichiers** : ouvrir / enregistrer en UTF-8, fichiers récents, export HTML.
- Interface **bilingue FR/EN**, réglages persistés.

## Lancer depuis les sources

Dépendances gérées avec [uv](https://docs.astral.sh/uv/) :

```bash
uv sync          # crée l'environnement et installe les dépendances
uv run main.py   # lance l'application
```

## Architecture

```
main.py                 # point d'entrée
app/
  core/                 # logique : speech, i18n, settings, renderer, document…
  ui/                   # fenêtre principale et dialogues wxPython
```

L'accessibilité repose sur des contrôles wx natifs uniquement (jamais de widgets
dessinés à la main), chaque champ ayant une étiquette ou un nom lu par le lecteur
d'écran.
