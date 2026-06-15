"""Auto-updateur via GitHub Releases.

Adapté de UniversalTranscoder (core/updater.py), avec deux ajouts propres à
MarkdownAccess :
- **strings en français** (langue source du projet) ;
- **canal beta** : `include_prerelease` permet d'inclure les releases marquées
  *prerelease* (sinon seules les stables sont vues).

Sécurité : l'asset téléchargé est vérifié contre le hachage SHA-256 que GitHub
publie dans le champ ``digest`` de l'asset (``sha256:<hex>``) — pas de fichier
``.sha256`` à publier à la main.

L'installeur est lancé en mode silencieux Inno (``/SILENT`` → fenêtre de
progression sans assistant). Le redémarrage de l'app est assuré par la section
``[Run]`` du script Inno.
"""

import hashlib
import json
import os
import re
import subprocess
import sys
import webbrowser
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from urllib import error, request

from app.core.app_info import (
    APP_EXE_NAME,
    APP_GITHUB_RELEASES_API,
    APP_GITHUB_RELEASES_PAGE,
    APP_INSTALLER_FILENAME,
    APP_VERSION,
)
from app.core.i18n import _translate as _

UPDATES_DIRNAME = "updates"
UPDATER_STATE_FILENAME = "updater-state.json"
HTTP_TIMEOUT_SECONDS = 10
DOWNLOAD_CHUNK_SIZE = 1024 * 256

# Marqueurs de notes bilingues dans le corps de la release GitHub :
#   <!-- MDA-NOTES:fr:start --> … <!-- MDA-NOTES:fr:end -->
_NOTES_MARKER_RE = re.compile(
    r"<!--\s*MDA-NOTES:([a-z]{2}):start\s*-->(.+?)<!--\s*MDA-NOTES:\1:end\s*-->",
    re.DOTALL,
)


class UpdaterError(Exception):
    pass


class UpdateCheckError(UpdaterError):
    pass


class UpdateDownloadError(UpdaterError):
    pass


@dataclass(frozen=True)
class ReleaseInfo:
    tag_name: str
    version: str
    published_at: str
    html_url: str
    body: str
    asset_name: str
    asset_url: str
    asset_digest: str = ""


def is_frozen() -> bool:
    """Vrai si on tourne depuis l'exe packagé (PyInstaller). En dev, l'install
    n'a pas de sens : on ne propose pas de remplacer le code source."""
    return bool(getattr(sys, "frozen", False))


# ---- emplacements de travail ------------------------------------------------

def get_local_appdata_dir():
    localappdata = os.getenv("LOCALAPPDATA")
    if localappdata:
        return Path(localappdata)
    return Path.home() / "AppData" / "Local"


def get_update_root_dir():
    return get_local_appdata_dir() / APP_EXE_NAME


def get_updates_dir():
    return get_update_root_dir() / UPDATES_DIRNAME


def ensure_updates_dir():
    updates_dir = get_updates_dir()
    updates_dir.mkdir(parents=True, exist_ok=True)
    return updates_dir


def get_updater_state_path():
    return get_update_root_dir() / UPDATER_STATE_FILENAME


# ---- versions ---------------------------------------------------------------

def normalize_version(value):
    normalized = str(value or "").strip()
    if normalized.lower().startswith("v"):
        normalized = normalized[1:]
    return normalized


def parse_version_tuple(value):
    """(major, minor, patch) en ignorant tout suffixe (ex. ``0.4.0-beta`` →
    ``(0, 4, 0)``). Limite assumée : une beta de même base qu'un stable compare
    égal — on ne « rétrograde » donc pas un utilisateur stable vers une beta."""
    normalized = normalize_version(value)
    if not normalized:
        return tuple()

    parts = []
    for token in normalized.split("."):
        digits = []
        for char in token:
            if char.isdigit():
                digits.append(char)
            else:
                break
        parts.append(int("".join(digits)) if digits else 0)
    while len(parts) < 3:
        parts.append(0)
    return tuple(parts[:3])


def is_release_newer(remote_version, current_version=APP_VERSION):
    return parse_version_tuple(remote_version) > parse_version_tuple(current_version)


# ---- interrogation GitHub ---------------------------------------------------

def fetch_latest_release(timeout=HTTP_TIMEOUT_SECONDS, lang=None, include_prerelease=False):
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": f"{APP_EXE_NAME}/{APP_VERSION}",
    }
    api_request = request.Request(APP_GITHUB_RELEASES_API, headers=headers)

    try:
        with request.urlopen(api_request, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except error.HTTPError as exc:
        raise UpdateCheckError(
            _("La vérification des mises à jour a échoué (statut HTTP {code}).").format(code=exc.code)
        ) from exc
    except error.URLError as exc:
        raise UpdateCheckError(_("Impossible de contacter GitHub pour vérifier les mises à jour.")) from exc
    except TimeoutError as exc:
        raise UpdateCheckError(_("La vérification des mises à jour a expiré.")) from exc
    except json.JSONDecodeError as exc:
        raise UpdateCheckError(_("GitHub a renvoyé une réponse de mise à jour invalide.")) from exc

    return parse_release_info(payload, lang=lang, include_prerelease=include_prerelease)


def parse_release_info(payload, lang=None, include_prerelease=False):
    releases = _extract_releases(payload, include_prerelease)
    if not releases:
        raise UpdateCheckError(_("GitHub a renvoyé une réponse de mise à jour invalide."))

    latest_release = releases[0]
    tag_name = str(latest_release.get("tag_name") or "").strip()
    version = normalize_version(tag_name)
    html_url = str(latest_release.get("html_url") or APP_GITHUB_RELEASES_PAGE).strip() or APP_GITHUB_RELEASES_PAGE
    body = build_combined_release_notes(releases, lang=lang)
    published_at = str(latest_release.get("published_at") or "").strip()
    asset_name, asset_url, asset_digest = find_setup_asset(latest_release.get("assets"))

    if not version:
        raise UpdateCheckError(_("La release GitHub ne définit pas de version valide."))

    return ReleaseInfo(
        tag_name=tag_name,
        version=version,
        published_at=published_at,
        html_url=html_url,
        body=body,
        asset_name=asset_name,
        asset_url=asset_url,
        asset_digest=asset_digest,
    )


def _extract_releases(payload, include_prerelease):
    """Releases candidates, la plus récente d'abord (ordre GitHub).

    On exclut toujours les brouillons (``draft``). On exclut les préversions
    (``prerelease``) **sauf** si ``include_prerelease`` est vrai (canal beta).
    """
    if not isinstance(payload, list):
        return []

    releases = []
    for item in payload:
        if not isinstance(item, dict):
            continue
        if item.get("draft"):
            continue
        if item.get("prerelease") and not include_prerelease:
            continue
        releases.append(item)
    return releases


# ---- notes de version -------------------------------------------------------

def build_combined_release_notes(releases, current_version=APP_VERSION, lang=None):
    sections = []
    for release in releases:
        version = normalize_version(release.get("tag_name"))
        if not version or not is_release_newer(version, current_version):
            continue

        published_at = format_release_date(str(release.get("published_at") or "").strip())
        body = normalize_release_notes(release.get("body"), lang=lang)
        sections.append(
            "\n".join(
                [
                    f"# {_('Version')} {version}",
                    f"{_('Publiée le :')} {published_at}",
                    "",
                    body,
                ]
            ).strip()
        )

    if sections:
        return "\n\n".join(sections)

    latest_release = releases[0] if releases else {}
    return normalize_release_notes(latest_release.get("body"), lang=lang)


def extract_language_notes(body, lang):
    """Extrait les notes d'une langue depuis un corps bilingue à marqueurs.

    Repli : langue demandée → ``en`` → ``fr`` → corps complet si aucun marqueur.
    """
    normalized = str(body or "").replace("\r\n", "\n")
    matches = {m.group(1): m.group(2).strip() for m in _NOTES_MARKER_RE.finditer(normalized)}

    if not matches:
        return normalized.strip()

    for candidate in [lang, "en", "fr"]:
        if candidate and candidate in matches:
            return matches[candidate]

    return normalized.strip()


def normalize_release_notes(value, lang=None):
    normalized = str(value or "").replace("\r\n", "\n").strip()
    if not normalized:
        return _("Aucune note de version fournie.")
    if lang:
        normalized = extract_language_notes(normalized, lang)
    return normalized or _("Aucune note de version fournie.")


def format_release_date(value):
    if not value:
        return _("Inconnue")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed.strftime("%Y-%m-%d %H:%M UTC")
    except ValueError:
        return value


# ---- asset + intégrité ------------------------------------------------------

def find_setup_asset(assets):
    if not isinstance(assets, list):
        raise UpdateCheckError(_("Aucun installeur n'a été trouvé dans la release GitHub."))

    exact_name = APP_INSTALLER_FILENAME.lower()
    for asset in assets:
        if not isinstance(asset, dict):
            continue
        name = str(asset.get("name") or "").strip()
        if name.lower() == exact_name:
            download_url = str(asset.get("browser_download_url") or "").strip()
            if download_url:
                digest = str(asset.get("digest") or "").strip()
                return name, download_url, digest

    raise UpdateCheckError(_("Aucun installeur n'a été trouvé dans la release GitHub."))


def parse_expected_sha256(digest):
    """Hex SHA-256 minuscule depuis le champ ``digest`` GitHub (``sha256:<hex>``).

    Retourne None si absent ou si l'algorithme n'est pas géré (forward-compatible :
    on ne fait jamais échouer une mise à jour juste parce que GitHub a introduit
    un nouveau format de digest).
    """
    normalized = str(digest or "").strip().lower()
    if not normalized.startswith("sha256:"):
        return None
    hex_digest = normalized[len("sha256:"):].strip()
    if len(hex_digest) != 64 or any(char not in "0123456789abcdef" for char in hex_digest):
        return None
    return hex_digest


def download_release_installer(release_info, progress_callback=None, timeout=HTTP_TIMEOUT_SECONDS):
    if not isinstance(release_info, ReleaseInfo):
        raise UpdateDownloadError(_("Informations de mise à jour invalides."))

    updates_dir = ensure_updates_dir()
    final_path = updates_dir / release_info.asset_name
    partial_path = updates_dir / f"{release_info.asset_name}.part"

    if partial_path.exists():
        partial_path.unlink(missing_ok=True)

    headers = {"User-Agent": f"{APP_EXE_NAME}/{APP_VERSION}"}
    asset_request = request.Request(release_info.asset_url, headers=headers)

    expected_sha256 = parse_expected_sha256(release_info.asset_digest)

    try:
        with request.urlopen(asset_request, timeout=timeout) as response:
            total_size = int(response.headers.get("Content-Length", "0") or "0")
            downloaded = 0
            hasher = hashlib.sha256()
            with open(partial_path, "wb") as handle:
                while True:
                    chunk = response.read(DOWNLOAD_CHUNK_SIZE)
                    if not chunk:
                        break
                    handle.write(chunk)
                    hasher.update(chunk)
                    downloaded += len(chunk)
                    if progress_callback is not None:
                        progress_callback(downloaded, total_size)

        # Refuse un téléchargement tronqué (connexion coupée sans exception).
        if total_size and downloaded != total_size:
            raise UpdateDownloadError(_("Le téléchargement de l'installeur est incomplet. Réessayez."))

        # Vérifie l'intégrité contre le SHA-256 publié par GitHub pour l'asset.
        if expected_sha256 and hasher.hexdigest() != expected_sha256:
            raise UpdateDownloadError(
                _("L'installeur a échoué la vérification d'intégrité et n'a pas été installé.")
            )

        if final_path.exists():
            final_path.unlink()
        partial_path.replace(final_path)
        return final_path
    except error.HTTPError as exc:
        raise UpdateDownloadError(
            _("Le téléchargement de l'installeur a échoué (statut HTTP {code}).").format(code=exc.code)
        ) from exc
    except error.URLError as exc:
        raise UpdateDownloadError(_("Impossible de télécharger l'installeur depuis GitHub.")) from exc
    except TimeoutError as exc:
        raise UpdateDownloadError(_("Le téléchargement de l'installeur a expiré.")) from exc
    except OSError as exc:
        raise UpdateDownloadError(_("Impossible d'enregistrer l'installeur téléchargé.")) from exc
    finally:
        if partial_path.exists():
            partial_path.unlink(missing_ok=True)


# ---- état + nettoyage des artefacts ----------------------------------------

def load_updater_state():
    state_path = get_updater_state_path()
    if not state_path.exists():
        return {}
    try:
        with open(state_path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
        if isinstance(data, dict):
            return data
    except Exception:
        return {}
    return {}


def save_updater_state(installer_path, version, cleanup_pending=True):
    state_path = get_updater_state_path()
    state_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "downloaded_installer_path": str(Path(installer_path)),
        "downloaded_version": normalize_version(version),
        "cleanup_pending": bool(cleanup_pending),
    }
    with open(state_path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=4)
    return payload


def clear_updater_state():
    state_path = get_updater_state_path()
    if state_path.exists():
        state_path.unlink(missing_ok=True)


def cleanup_update_artifacts():
    """Supprime l'installeur téléchargé d'une mise à jour passée (appelé au boot)."""
    updates_dir = get_updates_dir()
    state = load_updater_state()
    removed_paths = []
    keep_pending = False
    pending_installer = str(state.get("downloaded_installer_path") or "").strip()
    cleanup_pending = bool(state.get("cleanup_pending", False))

    if cleanup_pending and pending_installer:
        pending_path = Path(pending_installer)
        if pending_path.exists():
            try:
                pending_path.unlink()
                removed_paths.append(str(pending_path))
            except OSError:
                keep_pending = True
        else:
            removed_paths.append(str(pending_path))

    if updates_dir.exists():
        normalized_pending = os.path.normcase(pending_installer) if pending_installer else ""
        exact_installer_path = updates_dir / APP_INSTALLER_FILENAME
        if exact_installer_path.exists():
            if not (normalized_pending and os.path.normcase(str(exact_installer_path)) == normalized_pending):
                try:
                    exact_installer_path.unlink()
                    removed_paths.append(str(exact_installer_path))
                except OSError:
                    pass

        for partial_path in updates_dir.glob("*.part"):
            try:
                partial_path.unlink()
                removed_paths.append(str(partial_path))
            except OSError:
                continue

    if keep_pending:
        save_updater_state(pending_installer, state.get("downloaded_version", ""), cleanup_pending=True)
    else:
        clear_updater_state()

    return removed_paths


# ---- lancement installeur / page de release --------------------------------

def open_release_page(url):
    target = str(url or APP_GITHUB_RELEASES_PAGE).strip() or APP_GITHUB_RELEASES_PAGE
    if os.name == "nt":
        try:
            os.startfile(target)
            return target
        except OSError:
            pass
    if webbrowser.open(target, new=0):
        return target
    raise RuntimeError("Unable to open the release page.")


def launch_installer_after_exit(installer_path):
    """Lance l'installeur Inno en silencieux après un court délai (le temps que
    l'app se ferme et libère ses fichiers). ``/SILENT`` affiche la fenêtre de
    progression d'Inno sans assistant à cliquer."""
    resolved_path = str(Path(installer_path).resolve())
    if os.name != "nt":
        subprocess.Popen([resolved_path], close_fds=True)
        return resolved_path

    escaped_path = resolved_path.replace("'", "''")
    command = (
        f"Start-Sleep -Milliseconds 800; "
        f"Start-Process -FilePath '{escaped_path}' "
        f"-ArgumentList '/SILENT','/SUPPRESSMSGBOXES','/NORESTART'"
    )
    kwargs = {"close_fds": True}
    if hasattr(subprocess, "CREATE_NO_WINDOW"):
        kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW

    subprocess.Popen(
        [
            "powershell.exe",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-WindowStyle",
            "Hidden",
            "-Command",
            command,
        ],
        **kwargs,
    )
    return resolved_path
