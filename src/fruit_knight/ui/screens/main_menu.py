"""Main menu screen."""

from __future__ import annotations

import pygame
import pygame_gui

from fruit_knight.ui.screens.base import Screen

# Description lines shown under the title (serious-game rationale).
RATIONALE = (
    "Serious game for upper-limb rehabilitation and frailty assessment",
    "Slice fruits with a knife hand  -  stop limiters with an open palm  -  defuse and throw grenades with your fist",
)


class MainMenuScreen(Screen):
    """Title screen with Play and Quit buttons."""

    def on_enter(self, **kwargs) -> None:
        """Build the buttons.

        :param kwargs: unused.
        :type kwargs: typing.Any
        """
        self.manager.clear_and_reset()
        w, h = self.app.size
        self.play = pygame_gui.elements.UIButton(pygame.Rect(w // 2 - 160, 360, 320, 64), "PLAY", self.manager, object_id="#primary_button")
        self.quit = pygame_gui.elements.UIButton(pygame.Rect(w // 2 - 160, 440, 320, 54), "QUIT", self.manager)

    def handle_event(self, event: pygame.event.Event) -> None:
        """Route button presses.

        :param event: pygame event.
        :type event: pygame.event.Event
        """
        super().handle_event(event)
        if event.type == pygame_gui.UI_BUTTON_PRESSED:
            if event.ui_element == self.play:
                self.app.goto("setup")
            elif event.ui_element == self.quit:
                self.app.running = False
        elif event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN:
            self.app.goto("setup")

    def draw(self, surface: pygame.Surface) -> None:
        """Render title and widgets.

        :param surface: window surface.
        :type surface: pygame.Surface
        """
        self.draw_background(surface)
        w, _ = self.app.size
        surface.blit(self.app.sprites.logo((760, 130)), (w // 2 - 380, 90))
        for i, line in enumerate(RATIONALE):
            self.app.fonts.draw_centered(surface, line, 20 if i == 0 else 17, (236, 239, 244) if i == 0 else (140, 150, 175), (w // 2, 245 + i * 30), bold=i == 0, shadow=False)
        self.app.fonts.draw_centered(surface, "Camera + MediaPipe  |  Pymunk physics  |  Pygame CE", 15, (110, 118, 150), (w // 2, self.app.size[1] - 30), bold=False, shadow=False)
        super().draw(surface)
