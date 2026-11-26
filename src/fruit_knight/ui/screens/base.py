"""Base class of UI screens."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pygame
import pygame_gui

from fruit_knight.ui.theme import build_theme

if TYPE_CHECKING:  # pragma: no cover
    from fruit_knight.ui.app import App


class Screen:
    """A state of the application state machine with its own pygame-gui manager."""

    def __init__(self, app: "App") -> None:
        """Create screen and its UI manager.

        :param app: owning application.
        :type app: fruit_knight.ui.app.App
        """
        self.app = app
        self.manager = pygame_gui.UIManager(app.size, theme_path=build_theme(app.cfg.ui))

    def on_enter(self, **kwargs) -> None:
        """Prepare the screen when it becomes active.

        :param kwargs: screen-specific parameters.
        :type kwargs: typing.Any
        """

    def on_exit(self) -> None:
        """Release resources when leaving the screen."""

    def handle_event(self, event: pygame.event.Event) -> None:
        """Process an input event.

        :param event: pygame event.
        :type event: pygame.event.Event
        """
        self.manager.process_events(event)

    def update(self, dt: float) -> None:
        """Advance screen logic.

        :param dt: time step in seconds.
        :type dt: float
        """
        self.manager.update(dt)

    def draw(self, surface: pygame.Surface) -> None:
        """Render the screen.

        :param surface: window surface.
        :type surface: pygame.Surface
        """
        self.manager.draw_ui(surface)

    def draw_background(self, surface: pygame.Surface) -> None:
        """Paint the shared arcade backdrop.

        :param surface: window surface.
        :type surface: pygame.Surface
        """
        surface.blit(self.app.sprites.background(self.app.size), (0, 0))

    def draw_card(self, surface: pygame.Surface, rect: pygame.Rect) -> None:
        """Paint a translucent panel behind a group of widgets.

        :param surface: window surface.
        :type surface: pygame.Surface
        :param rect: card rectangle.
        :type rect: pygame.Rect
        """
        from fruit_knight.rendering.draw_utils import alpha_rect

        alpha_rect(surface, tuple(self.app.cfg.ui.panel_color), 215, rect, 18)  # type: ignore[arg-type]
        pygame.draw.rect(surface, (70, 78, 120), rect, 2, border_radius=18)
