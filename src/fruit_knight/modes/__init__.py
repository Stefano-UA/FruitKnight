"""Game modes and match rules."""

from __future__ import annotations

import random

from fruit_knight.config.schema import GameConfig
from fruit_knight.modes.base import BaseGameMode
from fruit_knight.modes.competition import CompetitionMode
from fruit_knight.modes.endurance import MultiEnduranceMode, SoloEnduranceMode
from fruit_knight.modes.football import FootballMode
from fruit_knight.modes.setup import MatchSetup
from fruit_knight.utils.constants import ModeId

MODE_CLASSES: dict[ModeId, type[BaseGameMode]] = {
    ModeId.ENDURANCE_1P: SoloEnduranceMode,
    ModeId.ENDURANCE_NP: MultiEnduranceMode,
    ModeId.COMPETITION_NP: CompetitionMode,
    ModeId.FOOTBALL_2P: FootballMode,
}


def create_mode(cfg: GameConfig, setup: MatchSetup, size: tuple[int, int], rng: random.Random | None = None) -> BaseGameMode:
    """Instantiate the mode selected in a setup.

    :param cfg: game configuration.
    :type cfg: fruit_knight.config.schema.GameConfig
    :param setup: match options.
    :type setup: fruit_knight.modes.setup.MatchSetup
    :param size: screen width and height in pixels.
    :type size: tuple[int, int]
    :param rng: random generator.
    :type rng: random.Random | None
    :return: ready-to-run mode.
    :rtype: fruit_knight.modes.base.BaseGameMode
    """
    return MODE_CLASSES[setup.mode](cfg, setup, size, rng)


__all__ = [
    "BaseGameMode", "CompetitionMode", "FootballMode", "MODE_CLASSES", "MatchSetup",
    "MultiEnduranceMode", "SoloEnduranceMode", "create_mode",
]
