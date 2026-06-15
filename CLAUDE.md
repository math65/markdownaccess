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

## Packaging .exe + installeur (recette figée, pas encore buildé)

Cible : **PyInstaller onedir** + **installeur Inno Setup** (et non `--onefile`).
Ce choix est imposé par l'auto-updateur (voir plus bas) : l'asset GitHub est un
`MarkdownAccess-Setup.exe` lancé en `/SILENT`, cohérent avec
DownAccess/UniversalTranscoder.

```bash
uv add --dev pyinstaller
uv run pyinstaller markdownaccess.spec          # -> dist/MarkdownAccess/ (dossier)
ISCC.exe installer\markdownaccess.iss           # -> dist/MarkdownAccess-Setup.exe
```

- `markdownaccess.spec` : recette onedir reproductible (datas + hidden imports).
- `installer/markdownaccess.iss` : install **par-utilisateur** (`PrivilegesRequired=
  lowest`, pas d'UAC → silencieux possible), `AppId` GUID **fixe** (identité pour
  les MAJ, ne jamais changer), section `[Run]` **sans `skipifsilent`** pour que
  l'app **redémarre** après une install silencieuse.

Pièges spécifiques à anticiper (vérifiés sur la doc officielle des deps), déjà
encodés dans le `.spec` :
- **`locales/`** : fichiers de données, non vus par PyInstaller → les ajouter
  (`--add-data "locales;locales"`) sinon l'anglais disparaît dans l'exe. Ce sont
  les `.mo` compilés qui comptent (cf. `polib` ci-dessous).
- **`accessible_output2`** : ses DLL `nvdaControllerClient32/64.dll` sont des
  *données* non vues par l'analyse → dans le `.spec`,
  `datas = collect_data_files('accessible_output2')`. Embarquer aussi **pywin32**
  (le backend JAWS passe par un COM). Sans ça, l'app est **muette dans l'exe** (le
  `try/except` de `speech.py` masque l'erreur). Tester la synthèse sur l'exe final.
- **`mdit_py_plugins`** (footnotes/tasklists de l'aperçu) : sous-modules chargés
  dynamiquement → `--hidden-import mdit_py_plugins.footnote --hidden-import
  mdit_py_plugins.tasklists` (ou `collect_submodules`), sinon l'aperçu plante.
- **WebView2** (aperçu F6) : `WebView2Loader.dll` n'est pas détectée
  automatiquement → le `.spec` la cherche dans wxPython et la place à la racine.
  Le backend Edge dépend aussi du runtime WebView2 (présent sur la plupart des
  Win11) ; le repli `webbrowser.open` couvre l'absence. À tester sur une machine
  « propre ».

`polib` n'est utile **qu'au build** (compilation `.po` → `.mo`), pas au runtime
(c'est `gettext` qui lit le `.mo`) → le passer en `uv add --dev polib`, il n'a pas
à être embarqué dans l'exe.

Détails par dépendance dans la mémoire (`ref-*` : accessible-output2,
mdit-py-plugins, etc.).

## Auto-updateur (GitHub Releases)

`app/core/updater.py` + `app/ui/update_dialog.py` + `app/core/app_info.py`
(adaptés de UniversalTranscoder). Vérif **au démarrage** (notif seulement, pas
d'install auto — protège le travail) et via **Aide → Vérifier les mises à jour**.
- **Canal beta** opt-in (`settings.update_channel`) : inclut les releases
  `prerelease`. Stable les ignore.
- **Sécurité** : SHA-256 vérifié contre le champ `digest` de l'asset GitHub
  (rien à publier à la main).
- **Install** : `MarkdownAccess-Setup.exe` lancé en `/SILENT` après fermeture de
  l'app ; redémarrage via `[Run]` Inno.
- **Garde dev** : `updater.is_frozen()` → en `uv run`, l'install est désactivée.

**Process de release :** bump `app/version.py` → build (ci-dessus) → créer la
release GitHub (tag `vX.Y.Z`, cocher *prerelease* pour une beta) → **uploader**
`MarkdownAccess-Setup.exe`. Notes bilingues dans le corps via marqueurs :
`<!-- MDA-NOTES:fr:start -->…<!-- MDA-NOTES:fr:end -->` (et `:en:`). La langue
affichée suit `i18n.get_current_language_code()`.

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
- `app/core/renderer.py` (markdown-it-py, conforme CommonMark) produit du HTML
  **sémantique sans CSS** pour l'instant (la sémantique seule rend NVDA efficace ;
  le CSS viendra plus tard). Les `id` d'ancre des titres sont posés par une règle
  core native (pas de post-traitement HTML).

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
