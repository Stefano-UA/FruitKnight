"""Optional sound effects that never block or crash the game."""

from __future__ import annotations

import logging

import pygame

from fruit_knight.config.schema import AudioConfig
from fruit_knight.utils.paths import resource_path

log = logging.getLogger(__name__)


class AudioManager:
    """Plays configured sound files; silent when files or an audio device are missing."""

    def __init__(self, cfg: AudioConfig) -> None:
        """Initialise the mixer if possible.

        :param cfg: audio configuration.
        :type cfg: fruit_knight.config.schema.AudioConfig
        """
        self._cfg = cfg
        self._sounds: dict[str, pygame.mixer.Sound | None] = {}
        self.available = False
        if not cfg.enabled:
            return
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init()
            self.available = True
        except pygame.error:
            log.info("No audio device: sound effects disabled")

    def _load(self, name: str) -> pygame.mixer.Sound | None:
        """Load a sound once.

        :param name: sound key from the configuration.
        :type name: str
        :return: loaded sound or ``None`` when unavailable.
        :rtype: pygame.mixer.Sound | None
        """
        if name not in self._sounds:
            sound = None
            rel = self._cfg.sounds.get(name, "")
            path = resource_path(rel) if rel else None
            if path is not None and path.is_file():
                try:
                    sound = pygame.mixer.Sound(str(path))
                    sound.set_volume(self._cfg.volume)
                except pygame.error:
                    log.warning("Cannot decode sound '%s'", rel)
            self._sounds[name] = sound
        return self._sounds[name]

    def play(self, name: str) -> None:
        """Play a sound effect if it exists.

        :param name: sound key (game event kind).
        :type name: str
        """
        if not self.available:
            return
        sound = self._load(name)
        if sound is not None:
            sound.play()
