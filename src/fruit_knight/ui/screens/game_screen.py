"""Countdown, gameplay and pause screen."""

from __future__ import annotations

import time
from enum import Enum

import pygame

from fruit_knight.modes import create_mode
from fruit_knight.rendering.camera_view import frame_to_surface
from fruit_knight.rendering.draw_utils import alpha_rect
from fruit_knight.rendering.effects import EffectsManager
from fruit_knight.rendering.entity_renderer import EntityRenderer
from fruit_knight.rendering.overlay import draw_hands, draw_poses
from fruit_knight.ui.hud import Hud
from fruit_knight.ui.overlays import CountdownOverlay, PauseOverlay
from fruit_knight.ui.screens.base import Screen
from fruit_knight.utils.timers import Timer
from fruit_knight.vision.hands import HandSample, HandTracker
from fruit_knight.vision.simulator import MouseHandSimulator

# Seconds the final frame stays visible before showing the results.
GAME_OVER_DELAY_S = 1.8
MAX_FRAME_DT = 1 / 20


class Phase(str, Enum):
    """Sub-states of the game screen."""

    COUNTDOWN = "countdown"
    PLAYING = "playing"
    PAUSED = "paused"
    RESUMING = "resuming"
    ENDING = "ending"


class GameScreen(Screen):
    """Runs a match over the live camera feed."""

    def on_enter(self, **kwargs) -> None:
        """Create a fresh match from the current setup.

        :param kwargs: unused.
        :type kwargs: typing.Any
        """
        app = self.app
        self.size = app.size
        self.mode = create_mode(app.cfg, app.setup, self.size)
        self.hand_tracker = HandTracker(app.cfg.gestures, self.size)
        self.simulator = MouseHandSimulator(app.cfg.gestures)
        self.effects = EffectsManager(app.cfg, app.sprites, app.fonts)
        self.entity_renderer = EntityRenderer(app.sprites, app.fonts)
        self.hud = Hud(app.sprites, app.fonts)
        self.countdown_overlay = CountdownOverlay(app.fonts)
        self.pause_overlay = PauseOverlay(app.fonts)
        self.colors = [tuple(c) for c in app.cfg.players.colors]
        self.phase = Phase.COUNTDOWN
        self.timer = Timer(app.cfg.countdown_seconds)
        self.end_timer = Timer(GAME_OVER_DELAY_S)
        self.samples: dict[str, HandSample] = {}
        self.background: pygame.Surface | None = None
        self.poses: list = []
        self._last_stamp = -1.0
        self.clock_now = time.monotonic()

    def on_exit(self) -> None:
        """Stop tracking when leaving the match."""
        self.app.pipeline.stop_tracking()

    # ----------------------------------------------------------------- events
    def handle_event(self, event: pygame.event.Event) -> None:
        """Handle pause, resume and quit keys.

        :param event: pygame event.
        :type event: pygame.event.Event
        """
        if event.type != pygame.KEYDOWN:
            return
        if event.key == pygame.K_SPACE:
            if self.phase == Phase.PLAYING:
                self.phase = Phase.PAUSED
                self.mode.interaction.release_all()
            elif self.phase == Phase.PAUSED:
                self.phase = Phase.RESUMING
                self.timer = Timer(self.app.cfg.countdown_seconds)
        elif event.key == pygame.K_ESCAPE:
            if self.phase in (Phase.PAUSED, Phase.RESUMING):
                self.app.goto("menu")
            elif self.phase == Phase.PLAYING:
                self.phase = Phase.PAUSED
                self.mode.interaction.release_all()

    # ----------------------------------------------------------------- update
    def _refresh_samples(self) -> None:
        """Pull the newest vision result (or the mouse simulator) into hand samples."""
        pipeline = self.app.pipeline
        self.clock_now = time.monotonic()
        if pipeline.camera_ready:
            result = pipeline.latest()
            if result is not None and result.frame is not None and result.timestamp != self._last_stamp:
                self._last_stamp = result.timestamp
                frame_size = (result.frame.shape[1], result.frame.shape[0])
                self.samples = self.hand_tracker.update(result.hands, frame_size, result.timestamp)
                self.poses = result.poses
                self.background = frame_to_surface(result.frame, self.size)
            return
        # No camera: the mouse drives Player 1 so the game stays playable.
        self.background = None
        self.poses = []
        state = self.simulator.state_from_input(pygame.mouse.get_pressed(), pygame.key.get_pressed())
        self.samples = self.simulator.sample(pygame.mouse.get_pos(), state, self.clock_now)

    def _vision_ready(self) -> bool:
        """Report whether tracking models are loaded (or irrelevant).

        :return: True when the countdown may run.
        :rtype: bool
        """
        pipeline = self.app.pipeline
        return (not pipeline.camera_ready) or pipeline.tracker_status in ("ready", "error")

    def update(self, dt: float) -> None:
        """Advance countdowns, the match and effects.

        :param dt: time step in seconds.
        :type dt: float
        """
        dt = min(dt, MAX_FRAME_DT)
        self._refresh_samples()
        self.effects.track_hands(self.samples, self.clock_now)
        if self.phase in (Phase.COUNTDOWN, Phase.RESUMING):
            if self._vision_ready():
                self.timer.update(dt)
            if self.timer.done:
                if self.phase == Phase.RESUMING:
                    self.mode.interaction.release_all()
                self.phase = Phase.PLAYING
            self.effects.update(dt)
        elif self.phase == Phase.PLAYING:
            self.mode.update(dt, self.samples)
            self._dispatch_events()
            self.effects.update(dt)
            if self.mode.finished:
                self.phase = Phase.ENDING
        elif self.phase == Phase.ENDING:
            self.mode.update(dt, {})
            self._dispatch_events()
            self.effects.update(dt)
            self.end_timer.update(dt)
            if self.end_timer.done:
                self.app.goto("game_over", mode=self.mode)

    def _dispatch_events(self) -> None:
        """Forward mode events to visual effects and sound."""
        for event in self.mode.drain_events():
            self.effects.handle(event)
            self.app.audio.play(event.kind)

    # ------------------------------------------------------------------- draw
    def draw(self, surface: pygame.Surface) -> None:
        """Render camera feed, entities, effects, HUD and overlays.

        :param surface: window surface.
        :type surface: pygame.Surface
        """
        if self.background is not None:
            surface.blit(self.background, (0, 0))
            dim = pygame.Surface(self.size)
            dim.set_alpha(self.app.cfg.ui.camera_dim_alpha)
            surface.blit(dim, (0, 0))
        else:
            self.draw_background(surface)
        draw_poses(surface, self.poses, self.colors, self.app.fonts)  # type: ignore[arg-type]
        self.entity_renderer.draw(surface, self.mode, self.clock_now)
        draw_hands(surface, self.samples, self.colors, self.app.fonts)  # type: ignore[arg-type]
        self.effects.draw(surface, self.clock_now)
        self.hud.draw(surface, self.mode)
        self._draw_status(surface)
        self._draw_overlays(surface)

    def _draw_status(self, surface: pygame.Surface) -> None:
        """Draw vision status banners.

        :param surface: window surface.
        :type surface: pygame.Surface
        """
        pipeline = self.app.pipeline
        w, h = self.size
        fonts = self.app.fonts
        if not pipeline.camera_ready:
            fonts.draw_centered(surface, "NO CAMERA - MOUSE MODE: left = fist, right = open palm, none = knife", 18, (255, 171, 64), (w / 2, h - 24), bold=False)
        elif pipeline.tracker_status == "error":
            fonts.draw_centered(surface, f"Tracking unavailable: {pipeline.error[:90]}", 18, (255, 82, 82), (w / 2, h - 24), bold=False)
        elif pipeline.tracker_status == "loading":
            fonts.draw_centered(surface, "Loading MediaPipe models (first run downloads them)...", 22, (255, 255, 255), (w / 2, h - 24))

    def _draw_overlays(self, surface: pygame.Surface) -> None:
        """Draw countdown, pause and end banners.

        :param surface: window surface.
        :type surface: pygame.Surface
        """
        w, h = self.size
        if self.phase == Phase.COUNTDOWN:
            self.countdown_overlay.draw(surface, self.timer.remaining or 0.01, "GET READY", "Step back until your coloured skeleton and hands are visible")
        elif self.phase == Phase.RESUMING:
            alpha_rect(surface, (6, 8, 18), 120, pygame.Rect(0, 0, w, h))
            self.countdown_overlay.draw(surface, self.timer.remaining or 0.01, "RESUMING", "")
        elif self.phase == Phase.PAUSED:
            self.pause_overlay.draw(surface)
        elif self.phase == Phase.ENDING:
            self.app.fonts.draw_centered(surface, "GAME OVER", 96, (255, 82, 82), (w / 2, h / 2))
