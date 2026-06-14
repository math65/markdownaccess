# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Ce que c'est

MarkdownAccess — éditeur Markdown accessible aux lecteurs d'écran (NVDA, JAWS),
Python + wxPython, pour utilisateurs aveugles/malvoyants. **L'accessibilité prime
sur tout le reste.**

## Lancer / dépendances

Gestion des dépendances avec **uv** (et non pip/venv). Les dépendances sont
déclarées dans `pyproject.toml` ; `uv.lock` verrouille les versions exactes
(versionné, à committer).

```bash
uv sync          # crée .venv + installe les deps verrouillées
uv run main.py   # lance l'app dans l'environnement (pas besoin d'activer .venv)
```

Ajouter / retirer une dépendance : `uv add <pkg>` / `uv remove <pkg>`
(met à jour `pyproject.toml` et `uv.lock` automatiquement).

Pas de tests ni de linter configurés pour l'instant.

## Règles d'accessibilité (non négociables)

- Contrôles wx **natifs** uniquement, jamais de widget dessiné à la main
  (owner-drawn). `wx.stc` (Scintilla), `wx.richtext.RichTextCtrl` et
  `wx.html.HtmlWindow` sont **muets pour NVDA** — ne pas les utiliser pour du
  contenu à lire. L'éditeur est un `wx.TextCtrl`.
- Chaque champ a une `wx.StaticText` juste avant, ou un `name=` lu par le lecteur
  d'écran.
- Tout appel wx depuis un thread, et toute remise de focus, passent par
  `wx.CallAfter`.
- Erreurs via `wx.MessageDialog` (NVDA les lit).
- `speech.speak(...)` (`app/core/speech.py`) est **silencieux** si aucun lecteur
  d'écran n'est actif — c'est voulu, ne pas « corriger ».

## Aperçu HTML (décision figée, validée avec NVDA)

- L'aperçu (touche **F6**) utilise `wx.html2.WebView` (backend Edge / WebView2) :
  NVDA y entre en mode navigation. Repli `webbrowser.open` si WebView2 absent.
- Le **retour F6** depuis l'aperçu passe par un script JS injecté
  (`AddUserScript` + `AddScriptMessageHandler('wx')`) : WebView2 capte le clavier,
  donc l'accélérateur de menu ne reçoit pas la touche.
- `app/core/renderer.py` (mistune) produit du HTML **sémantique sans CSS** pour
  l'instant (la sémantique seule rend NVDA efficace ; le CSS viendra plus tard).

## i18n (piège d'ordre d'import)

- `i18n.install_language(...)` doit être appelé dans `main.py` **avant** d'importer
  `app.ui.main_window` : `_` est injecté dans `builtins`.
- Dans `app/core/`, importer la traduction par
  `from app.core.i18n import _translate as _` (jamais `_()` au niveau module).
- Le **français est la langue source** (les `msgid` sont en français) ; l'anglais
  vient de `locales/en/LC_MESSAGES/base.po`.

## Conventions

- Commits directs sur `main`, messages en français.
- Modules réutilisés de DownAccess (`../dl/`) : `speech`, `i18n`, `settings`,
  `logger`. Garder la cohérence avec ces patterns.
