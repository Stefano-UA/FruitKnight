"""Headless smoke test of the whole screen flow and the procedural renderer."""

from __future__ import annotations

import random

import pygame

from fruit_knight.config import load_config
from fruit_knight.modes import MatchSetup, create_mode
from fruit_knight.rendering import AssetManager, EffectsManager, EntityRenderer, FontCache, SpriteProvider
from fruit_knight.rendering.icon import ensure_icon
from fruit_knight.ui.app import App
from fruit_knight.utils.constants import ModeId


def pump(app: App, frames: int, dt: float = 1 / 60) -> None:
    """Run UI frames.

    :param app: application under test.
    :type app: fruit_knight.ui.app.App
    :param frames: number of frames.
    :type frames: int
    :param dt: frame time in seconds.
    :type dt: float
    """
    for _ in range(frames):
        for event in pygame.event.get():
            app.current.handle_event(event)
        app.current.update(dt)
        app.current.draw(app.window)


def test_full_screen_flow_without_camera() -> None:
    """Menu -> setup -> camera -> countdown -> play -> pause -> resume -> results."""
    app = App(load_config(), use_camera=False)
    try:
        pump(app, 3)
        for name in ("setup", "camera"):
            app.goto(name)
            pump(app, 3)
        app.start_match()
        game = app.current
        pump(app, 5)
        assert game.phase.value == "countdown"
        game.timer.update(10)
        pump(app, 120)
        assert game.phase.value == "playing"
        game.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_SPACE))
        before = game.mode.elapsed
        pump(app, 30)
        assert game.phase.value == "paused" and game.mode.elapsed == before  # everything frozen
        game.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_SPACE))
        pump(app, 10)
        assert game.phase.value == "resuming" and game.mode.elapsed == before
        game.timer.update(10)
        pump(app, 5)
        assert game.phase.value == "playing"
        game.mode.finish()
        game.phase = type(game.phase)("ending")
        pump(app, 150)
        assert type(app.current).__name__ == "GameOverScreen"
        pump(app, 3)
    finally:
        pygame.quit()


def test_procedural_fallback_renders_every_entity(tmp_path) -> None:
    """Missing sprite files never crash; every entity type draws."""
    pygame.init()
    pygame.display.set_mode((1280, 720))
    cfg = load_config()
    mode = create_mode(cfg, MatchSetup(players=2, mode=ModeId.ENDURANCE_NP), (1280, 720), random.Random(2))
    f = mode.factory
    zone = f.target_zone("top")
    mode.entities += [f.fruit(300, 1, s) for s in cfg.fruits.subtypes] + [f.bomb(500, 2), f.holder(600, 1), zone, f.thrower(700, 2, zone), f.limiter()]
    assets = AssetManager(tmp_path)  # empty root: every sprite is missing
    sprites = SpriteProvider(cfg, assets)
    fonts = FontCache()
    surface = pygame.Surface((1280, 720))
    EntityRenderer(sprites, fonts).draw(surface, mode, 0.0)
    effects = EffectsManager(cfg, sprites, fonts)
    from fruit_knight.modes.events import GameEvent

    effects.handle(GameEvent("slice", (100, 100), 1, "", {"subtype": "apple", "radius": 34, "angle": 1.0, "velocity": (0, 0)}))
    effects.update(0.05)
    effects.draw(surface, 0.0)
    assert set(sprites.all_configured_paths()) <= assets.missing or assets.missing
    pygame.quit()


def test_icon_is_a_valid_ico(tmp_path) -> None:
    """Generated icon has a valid ICO header with several sizes."""
    pygame.init()
    path = ensure_icon(tmp_path / "icon.ico")
    data = path.read_bytes()
    assert data[:4] == b"\x00\x00\x01\x00" and data[4] == 4
    pygame.quit()


def test_game_window_follows_roi_aspect_ratio() -> None:
    """The match window takes the aspect ratio of the selected camera area."""
    import numpy as np

    from fruit_knight.vision.roi import RoiRect

    app = App(load_config(), use_camera=True)
    try:
        app.pipeline.camera._frame, app.pipeline.camera._counter = np.zeros((480, 640, 3), np.uint8), 1
        app.setup.roi = RoiRect(0.0, 0.0, 0.5, 1.0)  # 320x480 px: portrait, aspect 2:3
        w, h = app.compute_game_size()
        assert abs(w / h - 320 / 480) < 0.02
        app.setup.roi = RoiRect.full()
        w, h = app.compute_game_size()
        assert abs(w / h - 640 / 480) < 0.02
        app.set_window_size((w, h))
        assert app.window.get_size() == (w, h)
    finally:
        pygame.quit()
