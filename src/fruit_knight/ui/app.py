"""Application shell: window, screen state machine and shared services."""

from __future__ import annotations

import logging

import pygame

from fruit_knight.config.schema import GameConfig
from fruit_knight.modes.setup import MatchSetup
from fruit_knight.rendering.assets import AssetManager
from fruit_knight.rendering.fonts import FontCache
from fruit_knight.rendering.icon import build_icon_surface, ensure_icon
from fruit_knight.rendering.sprites import SpriteProvider
from fruit_knight.ui.screens import CameraROIScreen, GameOverScreen, GameScreen, MainMenuScreen, ModeSetupScreen
from fruit_knight.ui.screens.base import Screen
from fruit_knight.utils.paths import resource_path
from fruit_knight.vision.camera import STATUS_CLOSED, STATUS_FAILED
from fruit_knight.vision.pipeline import VisionPipeline

log = logging.getLogger(__name__)
ICON_PREVIEW_SIZE = 64


class App:
    """Owns the pygame window and switches between screens."""

    def __init__(self, cfg: GameConfig, use_camera: bool = True) -> None:
        """Initialise pygame and every shared service.

        :param cfg: game configuration.
        :type cfg: fruit_knight.config.schema.GameConfig
        :param use_camera: disable to force mouse mode even when a camera exists.
        :type use_camera: bool
        """
        pygame.init()
        self.cfg = cfg
        self.use_camera = use_camera
        self.size = (cfg.window.width, cfg.window.height)
        flags = pygame.FULLSCREEN | pygame.SCALED if cfg.window.fullscreen else 0
        self.window = pygame.display.set_mode(self.size, flags)
        pygame.display.set_caption(cfg.window.title)
        try:
            ensure_icon(resource_path(cfg.ui.icon_path))
        except OSError:
            log.warning("Could not create %s", cfg.ui.icon_path)
        pygame.display.set_icon(build_icon_surface(ICON_PREVIEW_SIZE))
        self.clock = pygame.time.Clock()
        self.assets = AssetManager()
        self.sprites = SpriteProvider(cfg, self.assets)
        self.fonts = FontCache()
        self.pipeline = VisionPipeline(cfg.tracking)
        self.setup = MatchSetup.from_config(cfg)
        self.running = True
        self.screens: dict[str, Screen] = {
            "menu": MainMenuScreen(self), "setup": ModeSetupScreen(self), "camera": CameraROIScreen(self),
            "game": GameScreen(self), "game_over": GameOverScreen(self),
        }
        self.current: Screen = self.screens["menu"]
        self.current.on_enter()

    # ------------------------------------------------------------- services
    def goto(self, name: str, **kwargs) -> None:
        """Switch to another screen.

        :param name: screen key (``menu``, ``setup``, ``camera``, ``game``, ``game_over``).
        :type name: str
        :param kwargs: parameters forwarded to ``on_enter``.
        :type kwargs: typing.Any
        """
        self.current.on_exit()
        self.current = self.screens[name]
        self.current.on_enter(**kwargs)

    def ensure_camera(self, index: int, restart: bool = False) -> None:
        """Make sure the camera of a given index is streaming or being opened.

        :param index: camera device index.
        :type index: int
        :param restart: reopen even if the same device is active.
        :type restart: bool
        """
        if not self.use_camera:
            return
        cam = self.pipeline.camera
        same = cam.index == index and cam.status not in (STATUS_CLOSED, STATUS_FAILED)
        if restart or not same:
            self.pipeline.start_camera(index)

    def start_match(self) -> None:
        """Start (or restart) a match with the current setup and calibration."""
        self.pipeline.set_roi(self.setup.roi)
        self.pipeline.stop_tracking()
        self.ensure_camera(self.setup.camera_index)
        if self.use_camera:
            self.pipeline.start_tracking(self.setup.tracking_mode, self.setup.players)
        self.goto("game")

    # ----------------------------------------------------------------- loop
    def run(self) -> None:
        """Run the main loop until the window closes."""
        try:
            while self.running:
                dt = self.clock.tick(self.cfg.window.fps) / 1000.0
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        self.running = False
                    else:
                        self.current.handle_event(event)
                self.current.update(dt)
                self.current.draw(self.window)
                pygame.display.flip()
        finally:
            self.pipeline.shutdown()
            pygame.quit()
