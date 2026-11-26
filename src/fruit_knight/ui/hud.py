"""In-game heads-up display: lives, scores, clock, football goals and centre line."""

from __future__ import annotations

import pygame

from fruit_knight.modes.base import BaseGameMode
from fruit_knight.modes.football import FootballMode
from fruit_knight.rendering.draw_utils import alpha_rect
from fruit_knight.rendering.fonts import FontCache
from fruit_knight.rendering.sprites import SpriteProvider
from fruit_knight.utils.math_utils import format_time

Color = tuple[int, int, int]
# Layout constants in pixels.
PANEL_W, PANEL_H = 250, 86
HEART_SIZE = 26
MAX_HEARTS_SHOWN = 6
GOAL_STRIP = 14


class Hud:
    """Draws match information on top of the game view."""

    def __init__(self, sprites: SpriteProvider, fonts: FontCache) -> None:
        """Create HUD.

        :param sprites: sprite provider (heart icons).
        :type sprites: fruit_knight.rendering.sprites.SpriteProvider
        :param fonts: font cache.
        :type fonts: fruit_knight.rendering.fonts.FontCache
        """
        self.sprites = sprites
        self.fonts = fonts
        self.cfg = sprites.cfg

    def color(self, player_id: int) -> Color:
        """Resolve a player's colour.

        :param player_id: player id (1-based).
        :type player_id: int
        :return: RGB colour.
        :rtype: tuple[int, int, int]
        """
        colors = self.cfg.players.colors
        return tuple(colors[(player_id - 1) % len(colors)])  # type: ignore[return-value]

    def draw(self, surface: pygame.Surface, mode: BaseGameMode) -> None:
        """Draw the full HUD.

        :param surface: target surface.
        :type surface: pygame.Surface
        :param mode: running mode providing state.
        :type mode: fruit_knight.modes.base.BaseGameMode
        """
        if isinstance(mode, FootballMode):
            self._draw_football_field(surface, mode)
        w, _ = surface.get_size()
        n = len(mode.players)
        for index, (pid, player) in enumerate(mode.players.items()):
            # Panels spread evenly; versus mode pins them to the left and right.
            x = 16 if n == 1 else int(16 + index * (w - 32 - PANEL_W) / (n - 1))
            self._draw_player_panel(surface, mode, pid, pygame.Rect(x, 12, PANEL_W, PANEL_H))
        clock = mode.time_left if mode.time_left is not None else mode.elapsed
        label = format_time(clock)
        urgent = mode.time_left is not None and mode.time_left <= 10
        self.fonts.draw_centered(surface, label, 46, (255, 82, 82) if urgent else (255, 255, 255), (w / 2, 38))
        caption = "TIME LEFT" if mode.time_left is not None else "SURVIVED"
        self.fonts.draw_centered(surface, caption, 14, tuple(self.cfg.ui.muted_color), (w / 2, 66), bold=False)  # type: ignore[arg-type]

    def _draw_player_panel(self, surface: pygame.Surface, mode: BaseGameMode, pid: int, rect: pygame.Rect) -> None:
        """Draw one player's card.

        :param surface: target surface.
        :type surface: pygame.Surface
        :param mode: running mode.
        :type mode: fruit_knight.modes.base.BaseGameMode
        :param pid: player id.
        :type pid: int
        :param rect: card rectangle.
        :type rect: pygame.Rect
        """
        player = mode.players[pid]
        color = self.color(pid)
        alpha_rect(surface, (14, 16, 28), 175, rect, 12)
        pygame.draw.rect(surface, color if not player.eliminated else (90, 90, 100), rect, 3, border_radius=12)
        name = self.cfg.players.names[(pid - 1) % len(self.cfg.players.names)]
        surface.blit(self.fonts.text(name, 18, color, True), (rect.x + 12, rect.y + 6))
        score = self.fonts.text(f"{mode.score_of(pid)}", 30, (255, 255, 255), True)
        surface.blit(score, (rect.right - score.get_width() - 12, rect.y + 4))
        if player.eliminated:
            surface.blit(self.fonts.text("ELIMINATED", 18, (255, 82, 82), True), (rect.x + 12, rect.y + 48))
            return
        self._draw_lives(surface, player.lives, player.max_lives, (rect.x + 12, rect.y + 46))
        if mode.setup.competition_penalty == "points" and mode.mode_id.value == "np_competition":
            surface.blit(self.fonts.text(f"-{player.penalty_points} pts", 14, (255, 130, 130), True), (rect.x + 12, rect.y + 46))

    def _draw_lives(self, surface: pygame.Surface, lives: int, max_lives: int, origin: tuple[int, int]) -> None:
        """Draw heart icons, collapsing large life counts to ``heart x N``.

        :param surface: target surface.
        :type surface: pygame.Surface
        :param lives: remaining lives.
        :type lives: int
        :param max_lives: initial lives.
        :type max_lives: int
        :param origin: top-left of the row.
        :type origin: tuple[int, int]
        """
        x, y = origin
        if max_lives > MAX_HEARTS_SHOWN:
            surface.blit(self.sprites.heart(True, HEART_SIZE), (x, y))
            surface.blit(self.fonts.text(f"x {lives}", 22, (255, 255, 255), True), (x + HEART_SIZE + 6, y + 2))
            return
        for i in range(max_lives):
            surface.blit(self.sprites.heart(i < lives, HEART_SIZE), (x + i * (HEART_SIZE + 3), y))

    def _draw_football_field(self, surface: pygame.Surface, mode: FootballMode) -> None:
        """Draw centre line and highlighted goal edges.

        :param surface: target surface.
        :type surface: pygame.Surface
        :param mode: football mode providing goal geometry.
        :type mode: fruit_knight.modes.football.FootballMode
        """
        w, h = surface.get_size()
        ratio = mode.cfg.football.goal_bottom_edge_ratio
        for y in range(96, h, 30):
            pygame.draw.line(surface, (255, 255, 255), (w // 2, y), (w // 2, y + 16), 3)
        # Each defended goal: the whole outer vertical edge plus a bottom segment near that corner.
        left, right = self.color(1), self.color(2)
        alpha_rect(surface, left, 190, pygame.Rect(0, 0, GOAL_STRIP, h))
        alpha_rect(surface, left, 190, pygame.Rect(0, h - GOAL_STRIP, int(w * ratio), GOAL_STRIP))
        alpha_rect(surface, right, 190, pygame.Rect(w - GOAL_STRIP, 0, GOAL_STRIP, h))
        alpha_rect(surface, right, 190, pygame.Rect(int(w * (1 - ratio)), h - GOAL_STRIP, int(w * ratio), GOAL_STRIP))
        self.fonts.draw_centered(surface, "P1 GOAL", 16, left, (60, h - 34))
        self.fonts.draw_centered(surface, "P2 GOAL", 16, right, (w - 60, h - 34))
