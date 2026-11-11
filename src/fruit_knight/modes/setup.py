"""Match setup chosen in the pre-match screens."""

from __future__ import annotations

from dataclasses import dataclass, field

from fruit_knight.config.schema import GameConfig
from fruit_knight.utils.constants import ModeId, TrackingMode
from fruit_knight.vision.roi import RoiRect

# Allowed player counts per mode (inclusive).
PLAYER_RANGE: dict[ModeId, tuple[int, int]] = {
    ModeId.ENDURANCE_1P: (1, 1),
    ModeId.ENDURANCE_NP: (2, 4),
    ModeId.COMPETITION_NP: (2, 4),
    ModeId.FOOTBALL_2P: (2, 2),
}
MODE_LABELS: dict[ModeId, str] = {
    ModeId.ENDURANCE_1P: "1P Endurance",
    ModeId.ENDURANCE_NP: "NP Endurance",
    ModeId.COMPETITION_NP: "NP Competition",
    ModeId.FOOTBALL_2P: "2P Football",
}
TIMED_MODES = (ModeId.COMPETITION_NP, ModeId.FOOTBALL_2P)


@dataclass
class MatchSetup:
    """All user-selectable options of a match."""

    players: int = 1
    mode: ModeId = ModeId.ENDURANCE_1P
    lives: int = 3
    timespan: int = 120
    instant_death_bombs: bool = False
    instant_death_grenades: bool = False
    enable_bombs: bool = True
    enable_limiters: bool = True
    enable_holders: bool = True
    enable_throwers: bool = True
    competition_penalty: str = "lives"
    tracking_mode: TrackingMode = TrackingMode.POSE_HANDS
    camera_index: int = 0
    roi: RoiRect = field(default_factory=RoiRect.full)

    @staticmethod
    def from_config(cfg: GameConfig) -> "MatchSetup":
        """Build setup from ``defaults`` in the YAML file.

        :param cfg: game configuration.
        :type cfg: fruit_knight.config.schema.GameConfig
        :return: validated setup.
        :rtype: MatchSetup
        """
        d = cfg.defaults
        setup = MatchSetup(
            players=d.players, mode=ModeId(d.mode), lives=d.lives, timespan=d.timespan,
            instant_death_bombs=d.instant_death_bombs, instant_death_grenades=d.instant_death_grenades,
            enable_bombs=d.enable_bombs, enable_limiters=d.enable_limiters,
            enable_holders=d.enable_holders, enable_throwers=d.enable_throwers,
            competition_penalty=d.competition_penalty, tracking_mode=TrackingMode(d.tracking_mode),
            camera_index=cfg.tracking.camera.default_index,
        )
        setup.set_mode(setup.mode)
        return setup

    def set_mode(self, mode: ModeId) -> None:
        """Select a mode and fix the player count if incompatible.

        :param mode: requested mode.
        :type mode: fruit_knight.utils.constants.ModeId
        """
        self.mode = mode
        low, high = PLAYER_RANGE[mode]
        self.players = max(low, min(high, self.players))

    def set_players(self, players: int) -> None:
        """Select a player count and switch to a compatible mode if needed.

        :param players: requested number of players (1-4).
        :type players: int
        """
        self.players = max(1, min(4, players))
        low, high = PLAYER_RANGE[self.mode]
        if not low <= self.players <= high:
            if self.players == 1:
                self.mode = ModeId.ENDURANCE_1P
            elif self.mode in (ModeId.ENDURANCE_1P, ModeId.FOOTBALL_2P):
                self.mode = ModeId.ENDURANCE_NP
            if self.mode == ModeId.FOOTBALL_2P and self.players != 2:
                self.mode = ModeId.ENDURANCE_NP

    @property
    def is_timed(self) -> bool:
        """Report whether the mode uses a countdown clock.

        :return: True for competition and football.
        :rtype: bool
        """
        return self.mode in TIMED_MODES
