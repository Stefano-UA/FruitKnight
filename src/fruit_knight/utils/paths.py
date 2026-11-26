"""Filesystem path resolution compatible with PyInstaller bundles."""

from __future__ import annotations

import sys
from pathlib import Path


def is_frozen() -> bool:
    """Detect whether code runs inside a PyInstaller bundle.

    :return: True when ``sys._MEIPASS`` is defined.
    :rtype: bool
    """
    return getattr(sys, "_MEIPASS", None) is not None


def repo_root() -> Path:
    """Resolve root directory holding ``assets/`` and ``config/``.

    :return: PyInstaller extraction directory when frozen, repository root otherwise.
    :rtype: pathlib.Path
    """
    bundle = getattr(sys, "_MEIPASS", None)
    if bundle is not None:
        return Path(bundle)
    # utils/paths.py -> utils -> fruit_knight -> src -> repository root
    return Path(__file__).resolve().parents[3]


def resource_path(*parts: str) -> Path:
    """Build absolute path of a bundled read-only resource.

    :param parts: path components relative to repository root.
    :type parts: str
    :return: absolute resource path.
    :rtype: pathlib.Path
    """
    return repo_root().joinpath(*parts)


def models_dir() -> Path:
    """Resolve writable directory that stores downloaded MediaPipe models.

    Frozen builds extract to a temporary folder, so models go to the user home instead.

    :return: existing directory for ``.task`` model files.
    :rtype: pathlib.Path
    """
    target = Path.home() / ".fruit_knight" / "models" if is_frozen() else resource_path("assets", "models")
    target.mkdir(parents=True, exist_ok=True)
    return target
