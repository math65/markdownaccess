"""Constantes d'identité applicative pour l'auto-updateur.

Réutilise la version et le nom déclarés dans app/version.py (source unique de
vérité) et les complète avec les coordonnées GitHub + le nom de l'asset
installeur attendu dans les releases.
"""

from app.version import APP_NAME, __version__ as APP_VERSION

APP_EXE_NAME = "MarkdownAccess"
# Nom exact de l'asset à publier dans chaque release GitHub.
APP_INSTALLER_FILENAME = "MarkdownAccess-Setup.exe"

APP_GITHUB_OWNER = "math65"
APP_GITHUB_REPOSITORY = "markdownaccess"

APP_GITHUB_RELEASES_API = (
    f"https://api.github.com/repos/{APP_GITHUB_OWNER}/{APP_GITHUB_REPOSITORY}/releases"
)
APP_GITHUB_RELEASES_PAGE = (
    f"https://github.com/{APP_GITHUB_OWNER}/{APP_GITHUB_REPOSITORY}/releases"
)
