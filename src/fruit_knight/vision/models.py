"""Download and locate MediaPipe ``.task`` model files."""

from __future__ import annotations

import logging
import urllib.request
from pathlib import Path

from fruit_knight.config.schema import TrackingConfig
from fruit_knight.utils.paths import models_dir

log = logging.getLogger(__name__)


def model_path(file_name: str) -> Path:
    """Resolve expected location of a model file.

    :param file_name: model file name.
    :type file_name: str
    :return: absolute path inside the models directory.
    :rtype: pathlib.Path
    """
    return models_dir() / file_name


def download(url: str, target: Path) -> None:
    """Download a file atomically.

    :param url: source URL.
    :type url: str
    :param target: destination path.
    :type target: pathlib.Path
    """
    tmp = target.with_suffix(target.suffix + ".part")
    log.info("Downloading %s", url)
    with urllib.request.urlopen(url, timeout=60) as response, open(tmp, "wb") as out:
        while chunk := response.read(1 << 16):
            out.write(chunk)
    tmp.replace(target)


def ensure_models(cfg: TrackingConfig, need_pose: bool = True) -> dict[str, Path]:
    """Make sure required models exist on disk, downloading missing ones.

    :param cfg: tracking configuration with file names and URLs.
    :type cfg: fruit_knight.config.schema.TrackingConfig
    :param need_pose: whether the pose model is required.
    :type need_pose: bool
    :return: mapping ``"pose"`` / ``"hand"`` to local paths.
    :rtype: dict[str, pathlib.Path]
    :raises RuntimeError: when a required model cannot be downloaded.
    """
    wanted = {"hand": (cfg.hand_model_file, cfg.hand_model_url)}
    if need_pose:
        wanted["pose"] = (cfg.pose_model_file, cfg.pose_model_url)
    paths: dict[str, Path] = {}
    for key, (file_name, url) in wanted.items():
        target = model_path(file_name)
        if not target.exists() or target.stat().st_size == 0:
            try:
                download(url, target)
            except OSError as exc:
                raise RuntimeError(f"Cannot download MediaPipe model '{file_name}' from {url}: {exc}") from exc
        paths[key] = target
    return paths


def missing_models(cfg: TrackingConfig) -> list[str]:
    """List configured model files absent from disk.

    :param cfg: tracking configuration.
    :type cfg: fruit_knight.config.schema.TrackingConfig
    :return: names of missing model files.
    :rtype: list[str]
    """
    names = (cfg.pose_model_file, cfg.hand_model_file)
    return [n for n in names if not model_path(n).exists()]


if __name__ == "__main__":
    from fruit_knight.config import load_config

    logging.basicConfig(level=logging.INFO)
    for name, path in ensure_models(load_config().tracking).items():
        print(f"{name}: {path}")
