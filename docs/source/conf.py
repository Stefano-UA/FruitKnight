"""Sphinx configuration for the Fruit Knight documentation."""

import os
import sys
from pathlib import Path

# Make the package importable and keep pygame headless while autodoc imports modules.
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

project = "Fruit Knight"
author = "Fruit Knight team"
copyright = "2026, Fruit Knight team"
release = "1.0.0"

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.viewcode",
]

autodoc_member_order = "bysource"
autodoc_default_options = {"members": True, "undoc-members": False, "show-inheritance": True}
autodoc_typehints = "none"  # types are documented through :type: fields

templates_path = ["_templates"]
exclude_patterns = ["_build"]

html_theme = "furo"
html_title = "Fruit Knight"
html_static_path = ["_static"]
html_css_files = ["custom.css"]

# Palette of the dark theme, also applied to the "light" variables so the page stays dark
# even if the visitor toggles the theme switch.
_DARK = {
    "color-background-primary": "#131416",
    "color-background-secondary": "#1a1c1e",
    "color-background-hover": "#1e2124",
    "color-background-border": "#303335",
    "color-foreground-primary": "#cfd0d0",
    "color-foreground-secondary": "#9ca0a5",
    "color-brand-primary": "#ffab40",
    "color-brand-content": "#ffab40",
    "color-code-background": "#1a1c1e",
    "color-code-foreground": "#d0d0d0",
}
html_theme_options = {
    "light_css_variables": _DARK,
    "dark_css_variables": _DARK,
    "sidebar_hide_name": False,
}
