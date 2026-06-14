"""Modèle de document : chemin, état modifié (dirty), lecture/écriture UTF-8.

Le texte lui-même vit dans le wx.TextCtrl (source unique de vérité) ; ce modèle
ne gère que le fichier et les métadonnées.
"""

from pathlib import Path


class Document:
    def __init__(self):
        self.path: str | None = None
        self.dirty: bool = False

    @property
    def filename(self) -> str | None:
        return Path(self.path).name if self.path else None

    def load(self, path: str) -> str:
        """Lit le fichier en UTF-8 (replis utf-8-sig puis cp1252)."""
        p = Path(path)
        for enc in ("utf-8", "utf-8-sig", "cp1252"):
            try:
                text = p.read_text(encoding=enc)
                break
            except UnicodeDecodeError:
                continue
        else:
            text = p.read_text(encoding="utf-8", errors="replace")
        self.path = str(p)
        self.dirty = False
        return text

    def save(self, text: str, path: str | None = None) -> None:
        """Écrit en UTF-8, fins de ligne normalisées en \\n."""
        if path:
            self.path = str(Path(path))
        if not self.path:
            raise ValueError("Aucun chemin de fichier défini")
        normalized = text.replace("\r\n", "\n").replace("\r", "\n")
        Path(self.path).write_text(normalized, encoding="utf-8", newline="")
        self.dirty = False
