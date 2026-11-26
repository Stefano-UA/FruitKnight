"""Dark arcade theme for pygame-gui."""

from __future__ import annotations

from typing import Any

from fruit_knight.config.schema import UiConfig

Color = tuple[int, int, int]


def hex_color(c: Color) -> str:
    """Format a colour for pygame-gui theme files.

    :param c: RGB colour.
    :type c: tuple[int, int, int]
    :return: ``#rrggbb`` string.
    :rtype: str
    """
    return "#{:02x}{:02x}{:02x}".format(*c)


def _lighten(c: Color, amount: int) -> Color:
    """Brighten a colour by an absolute amount.

    :param c: RGB colour.
    :type c: tuple[int, int, int]
    :param amount: value added to each channel.
    :type amount: int
    :return: brightened colour.
    :rtype: tuple[int, int, int]
    """
    return tuple(min(255, v + amount) for v in c)  # type: ignore[return-value]


def _button_colours(bg: Color, text: Color, border: Color) -> dict[str, str]:
    """Build the colour block of a button style.

    :param bg: normal background.
    :type bg: tuple[int, int, int]
    :param text: text colour.
    :type text: tuple[int, int, int]
    :param border: border colour.
    :type border: tuple[int, int, int]
    :return: theme colour mapping.
    :rtype: dict[str, str]
    """
    hover = _lighten(bg, 28)
    return {
        "normal_bg": hex_color(bg), "hovered_bg": hex_color(hover), "active_bg": hex_color(_lighten(bg, 50)),
        "selected_bg": hex_color(hover), "disabled_bg": hex_color((30, 33, 50)),
        "normal_text": hex_color(text), "hovered_text": "#ffffff", "active_text": "#ffffff",
        "selected_text": "#ffffff", "disabled_text": "#6b7390",
        "normal_border": hex_color(border), "hovered_border": hex_color(_lighten(border, 40)),
        "active_border": "#ffffff", "selected_border": hex_color(border), "disabled_border": "#3a3f5c",
    }


def build_theme(ui: UiConfig) -> dict[str, Any]:
    """Create the pygame-gui theme dictionary from the configured palette.

    :param ui: UI palette configuration.
    :type ui: fruit_knight.config.schema.UiConfig
    :return: theme mapping accepted by ``pygame_gui.UIManager``.
    :rtype: dict[str, typing.Any]
    """
    panel, accent, text = tuple(ui.panel_color), tuple(ui.accent_color), tuple(ui.text_color)
    button_misc = {"border_width": "2", "shadow_width": "0", "shape": "rounded_rectangle", "shape_corner_radius": "10"}
    font = {"name": "noto_sans", "size": "18", "bold": "1"}
    toggle_on = _button_colours((30, 96, 62), text, (76, 175, 120))
    toggle_off = _button_colours((58, 40, 52), (200, 190, 200), (120, 80, 100))
    return {
        "defaults": {
            "colours": {
                "dark_bg": hex_color(tuple(ui.background_color)), "normal_text": hex_color(text),
                "normal_bg": hex_color(panel), "hovered_bg": hex_color(_lighten(panel, 20)),
                "selected_bg": hex_color(_lighten(panel, 30)), "disabled_bg": "#1e2132",
                "hovered_text": "#ffffff", "selected_text": "#ffffff", "disabled_text": "#6b7390",
                "text_shadow": "#00000000", "normal_border": hex_color(_lighten(panel, 40)),
            },
            "font": font,
        },
        "button": {"colours": _button_colours(_lighten(panel, 14), text, _lighten(panel, 70)), "misc": button_misc, "font": font},
        "#primary_button": {"colours": _button_colours((200, 120, 30), (20, 12, 4), accent), "misc": button_misc, "font": font},
        "#toggle_on": {"colours": toggle_on, "misc": button_misc, "font": font},
        "#toggle_off": {"colours": toggle_off, "misc": button_misc, "font": font},
        "label": {"colours": {"normal_text": hex_color(text), "dark_bg": "#00000000"}, "font": {"name": "noto_sans", "size": "18", "bold": "0"}},
        "#heading": {"misc": {"text_horiz_alignment": "left"}, "colours": {"normal_text": hex_color(accent), "dark_bg": "#00000000"}, "font": {"name": "noto_sans", "size": "28", "bold": "1"}},
        "#muted": {"misc": {"text_horiz_alignment": "left"}, "colours": {"normal_text": hex_color(tuple(ui.muted_color)), "dark_bg": "#00000000"}, "font": {"name": "noto_sans", "size": "15", "bold": "0"}},
        "#warning": {"misc": {"text_horiz_alignment": "left"}, "colours": {"normal_text": hex_color(tuple(ui.danger_color)), "dark_bg": "#00000000"}, "font": {"name": "noto_sans", "size": "16", "bold": "1"}},
        "drop_down_menu": {
            "colours": {
                "dropdown_bg": hex_color(_lighten(panel, 14)), "normal_bg": hex_color(_lighten(panel, 14)),
                "hovered_bg": hex_color(_lighten(panel, 40)), "selected_bg": hex_color(accent),
                "normal_text": hex_color(text), "hovered_text": "#ffffff", "selected_text": "#14101c",
                "normal_border": hex_color(_lighten(panel, 70)), "disabled_bg": "#1e2132", "disabled_text": "#6b7390",
                "disabled_border": "#3a3f5c", "selected_border": hex_color(accent),
            },
            "misc": {"border_width": "2", "shape": "rounded_rectangle", "shape_corner_radius": "8"},
            "font": {"name": "noto_sans", "size": "17", "bold": "0"},
        },
    }
