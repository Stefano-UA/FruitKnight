"""Mouse-driven hand used for development and when no webcam is available."""

from __future__ import annotations

from fruit_knight.config.schema import GestureConfig
from fruit_knight.utils.constants import HandState
from fruit_knight.vision.hands import HandSample
from fruit_knight.vision.motion import VelocityEstimator

# Distance in pixels between simulated palm and fingertip.
KNIFE_LENGTH_PX = 70.0


class MouseHandSimulator:
    """Produces a single synthetic hand for player 1 following the mouse cursor."""

    def __init__(self, cfg: GestureConfig, player_id: int = 1) -> None:
        """Create simulator.

        :param cfg: gesture configuration (velocity filtering).
        :type cfg: fruit_knight.config.schema.GestureConfig
        :param player_id: player controlled by the mouse.
        :type player_id: int
        """
        self._player = player_id
        self._velocity = VelocityEstimator(cfg.velocity_window_s, cfg.velocity_smoothing)

    @staticmethod
    def state_from_input(buttons: tuple[bool, bool, bool], keys_pressed) -> HandState:
        """Map mouse buttons and keys to a posture.

        Hold left button for a fist, right button for an open palm; otherwise knife hand.
        Keys ``2`` and ``3`` force open palm and fist.

        :param buttons: pressed state of left, middle and right buttons.
        :type buttons: tuple[bool, bool, bool]
        :param keys_pressed: pygame key state sequence.
        :type keys_pressed: typing.Sequence[bool]
        :return: simulated posture.
        :rtype: fruit_knight.utils.constants.HandState
        """
        import pygame

        if buttons[0] or keys_pressed[pygame.K_3]:
            return HandState.CLOSED_FIST
        if buttons[2] or keys_pressed[pygame.K_2]:
            return HandState.OPEN_PALM
        return HandState.KNIFE_HAND

    def sample(self, position: tuple[float, float], state: HandState, now: float) -> dict[str, HandSample]:
        """Create the simulated sample for this frame.

        :param position: mouse position in viewport pixels.
        :type position: tuple[float, float]
        :param state: simulated posture.
        :type state: fruit_knight.utils.constants.HandState
        :param now: current time in seconds.
        :type now: float
        :return: single-entry sample mapping.
        :rtype: dict[str, fruit_knight.vision.hands.HandSample]
        """
        velocity = self._velocity.push(now, position)
        tip = (position[0], position[1] - KNIFE_LENGTH_PX)
        key = f"p{self._player}:Right"
        return {
            key: HandSample(
                key=key, player_id=self._player, state=state, palm=position, tip=tip,
                wrist=(position[0], position[1] + KNIFE_LENGTH_PX * 0.5), velocity=velocity, synthetic=True,
            )
        }
