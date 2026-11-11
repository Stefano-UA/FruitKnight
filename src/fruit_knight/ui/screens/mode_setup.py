"""Match configuration screen."""

from __future__ import annotations

import pygame
import pygame_gui

from fruit_knight.modes.setup import MODE_LABELS, PLAYER_RANGE, MatchSetup
from fruit_knight.utils.constants import ModeId, TrackingMode
from fruit_knight.ui.screens.base import Screen

TRACKING_LABELS = {
    TrackingMode.POSE_HANDS: "Full Pose + Hands (Mannequins)",
    TrackingMode.HANDS_ONLY: "Lightweight Hands-Only (Zones)",
}
PENALTY_LABELS = {"lives": "Lose lives", "points": "Lose points"}
ROW_H = 56
LEFT_X, RIGHT_X = 90, 740
LABEL_W, CONTROL_W = 230, 280
TOGGLE_W = 450
TOP = 175


class ModeSetupScreen(Screen):
    """Lets the user choose players, mode, lives, hazards and tracking."""

    def on_enter(self, **kwargs) -> None:
        """Rebuild widgets from the current setup.

        :param kwargs: unused.
        :type kwargs: typing.Any
        """
        self.notice = ""
        self._build()

    # ------------------------------------------------------------------ build
    def _dropdown(self, options: list[str], current: str, rect: pygame.Rect) -> pygame_gui.elements.UIDropDownMenu:
        """Create a drop-down menu.

        :param options: option labels.
        :type options: list[str]
        :param current: initially selected label.
        :type current: str
        :param rect: widget rectangle.
        :type rect: pygame.Rect
        :return: drop-down element.
        :rtype: pygame_gui.elements.UIDropDownMenu
        """
        return pygame_gui.elements.UIDropDownMenu(options, current, rect, self.manager)

    def _build(self) -> None:
        """Create all widgets for the current setup."""
        s: MatchSetup = self.app.setup
        cfg = self.app.cfg
        self.manager.clear_and_reset()
        self.drops: dict[str, pygame_gui.elements.UIDropDownMenu] = {}
        self.options: dict[str, dict[str, object]] = {}
        self.toggles: dict[pygame_gui.elements.UIButton, str] = {}
        ui = pygame_gui.elements

        def label(text: str, x: int, y: int, oid: str | None = None, w: int = LABEL_W) -> None:
            """Add a text label.

            :param text: label text.
            :type text: str
            :param x: left coordinate.
            :type x: int
            :param y: top coordinate.
            :type y: int
            :param oid: optional theme object id.
            :type oid: str | None
            :param w: label width.
            :type w: int
            """
            ui.UILabel(pygame.Rect(x, y, w, 44 if oid == "#heading" else 34), text, self.manager, object_id=oid)

        label("MATCH SETUP", 90, 36, "#heading", 500)
        label("Choose the game rules, then calibrate the camera", 90, 84, "#muted", 600)

        # ---- left column: choices
        rows = [
            ("players", "Number of players", [str(n) for n in range(1, 5)], str(s.players), {str(n): n for n in range(1, 5)}),
            ("mode", "Game mode", [MODE_LABELS[m] for m in ModeId], MODE_LABELS[s.mode], {MODE_LABELS[m]: m for m in ModeId}),
            ("lives", "Initial lives", [str(v) for v in cfg.defaults.life_options], str(s.lives), {str(v): v for v in cfg.defaults.life_options}),
            ("timespan", "Timespan (seconds)", [str(v) for v in cfg.defaults.timespan_options], str(s.timespan), {str(v): v for v in cfg.defaults.timespan_options}),
            ("penalty", "Competition penalty", list(PENALTY_LABELS.values()), PENALTY_LABELS[s.competition_penalty], {v: k for k, v in PENALTY_LABELS.items()}),
            ("tracking", "Tracking mode", list(TRACKING_LABELS.values()), TRACKING_LABELS[s.tracking_mode], {v: k for k, v in TRACKING_LABELS.items()}),
        ]
        if str(s.lives) not in rows[2][2]:
            rows[2][2].append(str(s.lives))
            rows[2][4][str(s.lives)] = s.lives
        if str(s.timespan) not in rows[3][2]:
            rows[3][2].append(str(s.timespan))
            rows[3][4][str(s.timespan)] = s.timespan
        for i, (key, text, opts, current, mapping) in enumerate(rows):
            y = TOP + i * ROW_H
            label(text, LEFT_X, y + 4)
            drop = self._dropdown(opts, current, pygame.Rect(LEFT_X + LABEL_W, y, CONTROL_W + (60 if key == "tracking" else 0), 42))
            self.drops[key] = drop
            self.options[key] = mapping
        if not s.is_timed:
            self.drops["timespan"].disable()
        if s.mode != ModeId.COMPETITION_NP:
            self.drops["penalty"].disable()

        # ---- right column: toggles
        label("Rules and hazards", RIGHT_X, TOP - 50, "#heading", 400)
        toggle_rows = [
            ("instant_death_bombs", "Instant death on bombs"),
            ("instant_death_grenades", "Instant death on grenades"),
            ("enable_bombs", "Bombs"),
            ("enable_limiters", "Limiters (barrier trunks)"),
            ("enable_holders", "Holders (Grenade v1: grab & hold)"),
            ("enable_throwers", "Throwers (Grenade v2: grab & throw)"),
        ]
        for i, (attr, text) in enumerate(toggle_rows):
            value = getattr(s, attr)
            btn = ui.UIButton(
                pygame.Rect(RIGHT_X, TOP + i * ROW_H, TOGGLE_W, 44), f"{text}:  {'ON' if value else 'OFF'}",
                self.manager, object_id="#toggle_on" if value else "#toggle_off",
            )
            self.toggles[btn] = attr
        if s.mode == ModeId.FOOTBALL_2P:
            self.toggles_note = "Limiters are disabled in Football mode"
        else:
            self.toggles_note = ""

        # ---- navigation
        self.back = ui.UIButton(pygame.Rect(90, 630, 200, 56), "BACK", self.manager)
        self.next = ui.UIButton(pygame.Rect(self.app.size[0] - 90 - 360, 630, 360, 56), "NEXT: CAMERA & PLAY AREA", self.manager, object_id="#primary_button")
        self.notice_label = ui.UILabel(pygame.Rect(320, 638, 560, 40), self.notice or self.toggles_note, self.manager, object_id="#warning")

    # ----------------------------------------------------------------- events
    def handle_event(self, event: pygame.event.Event) -> None:
        """Apply changes and navigate.

        :param event: pygame event.
        :type event: pygame.event.Event
        """
        super().handle_event(event)
        s: MatchSetup = self.app.setup
        if event.type == pygame_gui.UI_DROP_DOWN_MENU_CHANGED:
            for key, drop in self.drops.items():
                if event.ui_element == drop:
                    self._apply_choice(key, self.options[key][event.text])
                    return
        elif event.type == pygame_gui.UI_BUTTON_PRESSED:
            if event.ui_element in self.toggles:
                attr = self.toggles[event.ui_element]
                setattr(s, attr, not getattr(s, attr))
                self._build()
            elif event.ui_element == self.back:
                self.app.goto("menu")
            elif event.ui_element == self.next:
                self.app.goto("camera")

    def _apply_choice(self, key: str, value: object) -> None:
        """Store a drop-down selection and re-validate player count versus mode.

        :param key: setting identifier.
        :type key: str
        :param value: selected value.
        :type value: object
        """
        s: MatchSetup = self.app.setup
        before_mode, before_players = s.mode, s.players
        self.notice = ""
        if key == "players":
            s.set_players(int(value))  # type: ignore[arg-type]
            if s.players != value:
                self.notice = "Player count adjusted to the selected mode"
            elif s.mode != before_mode:
                self.notice = f"Mode switched to {MODE_LABELS[s.mode]} for {s.players} players"
        elif key == "mode":
            s.set_mode(value)  # type: ignore[arg-type]
            if s.players != before_players:
                low, high = PLAYER_RANGE[s.mode]
                self.notice = f"{MODE_LABELS[s.mode]} needs {low if low == high else f'{low}-{high}'} players: set to {s.players}"
        elif key == "lives":
            s.lives = int(value)  # type: ignore[arg-type]
        elif key == "timespan":
            s.timespan = int(value)  # type: ignore[arg-type]
        elif key == "penalty":
            s.competition_penalty = str(value)
        elif key == "tracking":
            s.tracking_mode = value  # type: ignore[assignment]
        self._build()

    # ------------------------------------------------------------------- draw
    def draw(self, surface: pygame.Surface) -> None:
        """Render cards and widgets.

        :param surface: window surface.
        :type surface: pygame.Surface
        """
        self.draw_background(surface)
        self.draw_card(surface, pygame.Rect(LEFT_X - 24, TOP - 30, LABEL_W + CONTROL_W + 108, 6 * ROW_H + 40))
        self.draw_card(surface, pygame.Rect(RIGHT_X - 24, TOP - 58, TOGGLE_W + 48, 6 * ROW_H + 68))
        super().draw(surface)
