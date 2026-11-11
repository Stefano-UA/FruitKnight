"""Results screen."""

from __future__ import annotations

import pygame
import pygame_gui

from fruit_knight.modes.base import BaseGameMode
from fruit_knight.ui.screens.base import Screen
from fruit_knight.utils.constants import ModeId
from fruit_knight.utils.math_utils import format_time

TABLE_LEFT, ROW_H = 120, 74


class GameOverScreen(Screen):
    """Final standings with per-player breakdown."""

    def on_enter(self, **kwargs) -> None:
        """Receive the finished mode and build the buttons.

        :param kwargs: expects ``mode`` (the finished game mode).
        :type kwargs: typing.Any
        """
        self.mode: BaseGameMode = kwargs["mode"]
        self.standings = self.mode.standings()
        self.manager.clear_and_reset()
        w, h = self.app.size
        self.again = pygame_gui.elements.UIButton(pygame.Rect(w // 2 - 330, h - 100, 300, 58), "PLAY AGAIN", self.manager, object_id="#primary_button")
        self.menu = pygame_gui.elements.UIButton(pygame.Rect(w // 2 + 30, h - 100, 300, 58), "RETURN TO MENU", self.manager)

    def handle_event(self, event: pygame.event.Event) -> None:
        """Route button presses.

        :param event: pygame event.
        :type event: pygame.event.Event
        """
        super().handle_event(event)
        if event.type == pygame_gui.UI_BUTTON_PRESSED:
            if event.ui_element == self.again:
                self.app.start_match()
            elif event.ui_element == self.menu:
                self.app.goto("menu")

    def _columns(self) -> list[tuple[str, int]]:
        """Define table columns for the current mode.

        :return: header label and x offset pairs.
        :rtype: list[tuple[str, int]]
        """
        cols = [("RANK", 0), ("PLAYER", 90), ("FRUITS", 300), ("HOLDERS", 410), ("THROWERS", 530)]
        if self.mode.mode_id == ModeId.FOOTBALL_2P:
            cols.append(("GOALS", 660))
        cols += [("SURVIVAL", 760), ("SCORE", 900)]
        return cols

    def draw(self, surface: pygame.Surface) -> None:
        """Render standings.

        :param surface: window surface.
        :type surface: pygame.Surface
        """
        self.draw_background(surface)
        fonts = self.app.fonts
        w, h = self.app.size
        winners = [s for s in self.standings if s.winner]
        title = f"{self.app.cfg.players.names[winners[0].player.player_id - 1].upper()} WINS!" if len(winners) == 1 else "IT'S A DRAW!"
        if len(self.standings) == 1:
            title = "MATCH OVER"
        color = tuple(self.app.cfg.players.colors[winners[0].player.player_id - 1]) if len(winners) == 1 else (255, 171, 64)
        fonts.draw_centered(surface, title, 64, color, (w / 2, 80))  # type: ignore[arg-type]
        self.draw_card(surface, pygame.Rect(TABLE_LEFT - 30, 140, w - 2 * TABLE_LEFT + 60, 90 + ROW_H * len(self.standings) + 20))
        for label, dx in self._columns():
            fonts.draw_centered(surface, label, 16, (140, 150, 175), (TABLE_LEFT + dx + 40, 170), bold=True, shadow=False)
        for i, row in enumerate(self.standings):
            y = 225 + i * ROW_H
            p = row.player
            pc = tuple(self.app.cfg.players.colors[p.player_id - 1])
            pygame.draw.rect(surface, pc, pygame.Rect(TABLE_LEFT - 12, y - 28, 6, 56), border_radius=3)
            values = [f"#{row.rank}", self.app.cfg.players.names[p.player_id - 1], str(p.fruits_sliced), str(p.holders_defused), str(p.throwers_completed)]
            if self.mode.mode_id == ModeId.FOOTBALL_2P:
                values.append(str(p.goals_scored))
            values += [format_time(p.survival_time), str(row.score) + ("  *" if row.winner and len(self.standings) > 1 else "")]
            for (label, dx), text in zip(self._columns(), values):
                big = label in ("SCORE", "PLAYER")
                fonts.draw_centered(surface, text, 30 if big else 26, pc if label == "PLAYER" else (255, 255, 255), (TABLE_LEFT + dx + 40, y), bold=big, shadow=False)  # type: ignore[arg-type]
        super().draw(surface)
