"""Application shell: window, screen state machine and shared services."""

from __future__ import annotations

import ctypes
import logging
import sys

import pygame

from fruit_knight.config.schema import GameConfig
from fruit_knight.modes.setup import MatchSetup
from fruit_knight.rendering.assets import AssetManager
from fruit_knight.rendering.audio import AudioManager
from fruit_knight.rendering.fonts import FontCache
from fruit_knight.rendering.icon import build_icon_surface, ensure_icon
from fruit_knight.rendering.sprites import SpriteProvider
from fruit_knight.ui.screens import CameraROIScreen, GameOverScreen, GameScreen, MainMenuScreen, ModeSetupScreen
from fruit_knight.ui.screens.base import Screen
from fruit_knight.utils.paths import resource_path
from fruit_knight.vision.camera import STATUS_CLOSED, STATUS_FAILED
from fruit_knight.vision.pipeline import VisionPipeline

log = logging.getLogger(__name__)
ICON_PREVIEW_SIZE = 128
APP_USER_MODEL_ID = "fruitknight.rehabilitation.game"
# Limits of the match window relative to the desktop, and smallest accepted width in pixels.
MAX_DESKTOP_WIDTH_RATIO, MAX_DESKTOP_HEIGHT_RATIO = 0.96, 0.88
MIN_GAME_WIDTH = 480


def set_windows_dpi_aware() -> None:
    """Declare the process DPI-aware so Windows does not bitmap-scale the window (blurry and slower)."""
    if sys.platform.startswith("win"):
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(2)  # type: ignore[attr-defined]
        except (AttributeError, OSError):
            try:
                ctypes.windll.user32.SetProcessDPIAware()  # type: ignore[attr-defined]
            except (AttributeError, OSError):
                log.debug("Could not set DPI awareness")


def set_windows_app_id() -> None:
    """Give the process its own Windows taskbar identity so the window icon replaces Python's."""
    if sys.platform.startswith("win"):
        try:
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(APP_USER_MODEL_ID)  # type: ignore[attr-defined]
        except (AttributeError, OSError):
            log.debug("Could not set the Windows AppUserModelID")


class App:
    """Owns the pygame window and switches between screens."""

    def __init__(self, cfg: GameConfig, use_camera: bool = True) -> None:
        """Initialise pygame and every shared service.

        :param cfg: game configuration.
        :type cfg: fruit_knight.config.schema.GameConfig
        :param use_camera: disable to force mouse mode even when a camera exists.
        :type use_camera: bool
        """
        set_windows_dpi_aware()  # both calls must precede window creation
        set_windows_app_id()  # for the taskbar icon
        pygame.init()
        self.cfg = cfg
        self.use_camera = use_camera
        self.menu_size = (cfg.window.width, cfg.window.height)
        self.game_size = self.menu_size
        self.size = self.menu_size
        self._flags = pygame.FULLSCREEN | pygame.SCALED if cfg.window.fullscreen else 0
        try:
            ensure_icon(resource_path(cfg.ui.icon_path))
        except OSError:
            log.warning("Could not create %s", cfg.ui.icon_path)
        # The icon is set before the window exists so the OS uses it for the taskbar entry too.
        pygame.display.set_icon(build_icon_surface(ICON_PREVIEW_SIZE))
        self.window = pygame.display.set_mode(self.size, self._flags)
        pygame.display.set_caption(cfg.window.title)
        self.clock = pygame.time.Clock()
        self.assets = AssetManager()
        self.sprites = SpriteProvider(cfg, self.assets)
        self.fonts = FontCache()
        self.audio = AudioManager(cfg.audio)
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
        if name in ("menu", "setup"):
            self.pipeline.stop_tracking()  # models stay loaded only between the camera screen and the match
        self.set_window_size(self.game_size if name == "game" else self.menu_size)
        self.current = self.screens[name]
        self.current.on_enter(**kwargs)

    def set_window_size(self, size: tuple[int, int]) -> None:
        """Resize the window (no-op when it already has that size or runs fullscreen).

        :param size: new window width and height in pixels.
        :type size: tuple[int, int]
        """
        if size == self.size or self._flags:
            return
        self.size = size
        self.window = pygame.display.set_mode(size, self._flags)

    def compute_game_size(self) -> tuple[int, int]:
        """Derive the match window size so it has the aspect ratio of the selected camera area.

        :return: width and height in pixels; the menu size when no camera frame is available.
        :rtype: tuple[int, int]
        """
        frame, _ = self.pipeline.camera.read_latest()
        if not self.use_camera or frame is None or self._flags:
            return self.menu_size
        frame_h, frame_w = frame.shape[:2]
        roi = self.setup.roi
        aspect = (roi.w * frame_w) / (roi.h * frame_h)
        height = float(self.menu_size[1])
        width = height * aspect
        desktop_w, desktop_h = pygame.display.get_desktop_sizes()[0]
        max_w, max_h = desktop_w * MAX_DESKTOP_WIDTH_RATIO, desktop_h * MAX_DESKTOP_HEIGHT_RATIO
        scale = min(1.0, max_w / width, max_h / height)
        width, height = width * scale, height * scale
        if width < MIN_GAME_WIDTH:  # very narrow areas: grow, then re-fit the height
            height, width = height * MIN_GAME_WIDTH / width, float(MIN_GAME_WIDTH)
            if height > max_h:
                width, height = width * max_h / height, max_h
        return int(width) // 2 * 2, int(height) // 2 * 2

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
        self.ensure_camera(self.setup.camera_index)
        if self.use_camera:
            self.pipeline.ensure_tracking(self.setup.tracking_mode, self.setup.players)
        self.game_size = self.compute_game_size()
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
