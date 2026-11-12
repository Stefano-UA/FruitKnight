"""Hand-to-world interaction: slicing, grabbing, throwing and stopping limiters."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import TYPE_CHECKING

from fruit_knight.entities import BarrierLimiter, Bomb, Fruit, Projectile
from fruit_knight.modes.events import GameEvent
from fruit_knight.utils.constants import HandState
from fruit_knight.utils.math_utils import distance, norm, point_segment_distance
from fruit_knight.vision.hands import HandSample

if TYPE_CHECKING:  # pragma: no cover
    from fruit_knight.modes.base import BaseGameMode

Vec = tuple[float, float]
OPEN_STATES = (HandState.OPEN_PALM, HandState.KNIFE_HAND)


@dataclass
class HandController:
    """Interaction memory of one tracked hand."""

    key: str
    player_id: int
    prev_state: HandState = HandState.UNKNOWN
    last_open_time: float = -1e9
    last_seen: float = 0.0
    last_velocity: Vec = (0.0, 0.0)
    last_palm: Vec = (0.0, 0.0)
    prev_tip: Vec | None = None
    held: Projectile | None = None


class InteractionSystem:
    """Applies the rules of the four hand states to the entities of a mode."""

    def __init__(self, mode: "BaseGameMode") -> None:
        """Create system bound to a mode.

        :param mode: mode owning entities, players and scoring callbacks.
        :type mode: fruit_knight.modes.base.BaseGameMode
        """
        self.mode = mode
        self.cfg = mode.cfg.gestures
        self.controllers: dict[str, HandController] = {}

    # ------------------------------------------------------------------ public
    def process(self, samples: dict[str, HandSample], now: float) -> None:
        """Handle every hand for one tick.

        :param samples: current hand samples keyed by hand id.
        :type samples: dict[str, fruit_knight.vision.hands.HandSample]
        :param now: match time in seconds.
        :type now: float
        """
        for key, sample in samples.items():
            ctrl = self.controllers.setdefault(key, HandController(key, sample.player_id))
            ctrl.player_id = sample.player_id
            ctrl.last_seen, ctrl.last_velocity, ctrl.last_palm = now, sample.velocity, sample.palm
            player = self.mode.players.get(sample.player_id)
            if player is None or player.eliminated:
                self._release(ctrl, (0.0, 0.0))
            else:
                self._step_hand(ctrl, sample, now)
            ctrl.prev_state, ctrl.prev_tip = sample.state, sample.tip
        for key in [k for k in self.controllers if k not in samples]:
            ctrl = self.controllers[key]
            if now - ctrl.last_seen > self.cfg.hand_lost_grace_s:
                # Hand vanished (often mid-throw): release with its last velocity.
                self._release(ctrl, self._throw_velocity(ctrl.last_velocity))
                del self.controllers[key]

    def release_player(self, player_id: int) -> None:
        """Drop everything held by a player's hands.

        :param player_id: player whose hands are freed.
        :type player_id: int
        """
        for ctrl in self.controllers.values():
            if ctrl.player_id == player_id:
                self._release(ctrl, (0.0, 0.0))

    def release_all(self, with_inertia: bool = False) -> None:
        """Release every held entity (pause resume, end of match).

        :param with_inertia: keep last hand velocity when True, drop in place otherwise.
        :type with_inertia: bool
        """
        for ctrl in self.controllers.values():
            velocity = self._throw_velocity(ctrl.last_velocity) if with_inertia else (0.0, 0.0)
            self._release(ctrl, velocity)
            ctrl.prev_state = HandState.UNKNOWN

    # ---------------------------------------------------------------- per hand
    def _step_hand(self, ctrl: HandController, s: HandSample, now: float) -> None:
        """Apply posture rules to one hand.

        :param ctrl: hand memory.
        :type ctrl: HandController
        :param s: current hand sample.
        :type s: fruit_knight.vision.hands.HandSample
        :param now: match time in seconds.
        :type now: float
        """
        if s.state in OPEN_STATES:
            ctrl.last_open_time = now
        if ctrl.held is not None and not ctrl.held.alive:
            ctrl.held = None
        if ctrl.held is not None:
            if s.state in OPEN_STATES:
                self._release(ctrl, self._throw_velocity(s.velocity))
            else:
                ctrl.held.move_to(s.palm)  # occupied hand: entity locked to palm centre
            return
        if s.state == HandState.CLOSED_FIST:
            if ctrl.prev_state != HandState.CLOSED_FIST and now - ctrl.last_open_time <= self.cfg.grab_grace_s:
                self._try_grab(ctrl, s)
        elif s.state == HandState.KNIFE_HAND:
            self._try_slice(ctrl, s)
        elif s.state == HandState.OPEN_PALM:
            self._try_stop_limiter(s)

    def _throw_velocity(self, velocity: Vec) -> Vec:
        """Scale hand velocity by the inertia multiplier.

        :param velocity: smoothed hand velocity in pixels per second.
        :type velocity: tuple[float, float]
        :return: launch velocity of the released entity.
        :rtype: tuple[float, float]
        """
        m = self.cfg.throw_inertia_multiplier
        return velocity[0] * m, velocity[1] * m

    def _release(self, ctrl: HandController, velocity: Vec) -> None:
        """Detach the held entity, if any.

        :param ctrl: hand memory.
        :type ctrl: HandController
        :param velocity: velocity given to the entity.
        :type velocity: tuple[float, float]
        """
        entity = ctrl.held
        if entity is None:
            return
        ctrl.held = None
        if entity.alive:
            entity.release(velocity, ctrl.player_id)
            self.mode.emit(GameEvent("release", entity.position, ctrl.player_id))

    # ----------------------------------------------------------------- actions
    def _try_grab(self, ctrl: HandController, s: HandSample) -> None:
        """Grab nearest graspable entity inside reach.

        :param ctrl: hand memory.
        :type ctrl: HandController
        :param s: current hand sample.
        :type s: fruit_knight.vision.hands.HandSample
        """
        best: Projectile | None = None
        best_dist = math.inf
        for entity in self.mode.entities:
            if not isinstance(entity, Projectile) or not entity.alive or entity.held_by is not None:
                continue
            if isinstance(entity, Fruit) and entity.sliced:
                continue
            d = distance(s.palm, entity.position)
            if d <= entity.radius + self.cfg.grab_radius and d < best_dist:
                best, best_dist = entity, d
        if best is not None:
            best.grab(ctrl.key, ctrl.player_id)
            best.move_to(s.palm)
            ctrl.held = best
            self.mode.emit(GameEvent("grab", best.position, ctrl.player_id))

    def _knife_hits(self, ctrl: HandController, s: HandSample, entity: Projectile) -> bool:
        """Test contact between the knife hand and an entity, including swept tip motion.

        :param ctrl: hand memory (previous tip position).
        :type ctrl: HandController
        :param s: current hand sample.
        :type s: fruit_knight.vision.hands.HandSample
        :param entity: candidate entity.
        :type entity: fruit_knight.entities.base.Projectile
        :return: True when the knife touches the entity.
        :rtype: bool
        """
        reach = entity.radius + self.cfg.knife_thickness
        centre = entity.position
        if point_segment_distance(centre, s.palm, s.tip) <= reach:
            return True
        # Sweep the fingertip path to avoid tunnelling during fast strokes.
        return ctrl.prev_tip is not None and point_segment_distance(centre, ctrl.prev_tip, s.tip) <= reach

    def _try_slice(self, ctrl: HandController, s: HandSample) -> None:
        """Slice fruits and detonate bombs touched by a knife hand.

        :param ctrl: hand memory.
        :type ctrl: HandController
        :param s: current hand sample.
        :type s: fruit_knight.vision.hands.HandSample
        """
        # A knife hand only cuts while it moves: a still hand never slices or detonates anything.
        if norm(s.velocity) < self.cfg.knife_min_speed:
            return
        for entity in list(self.mode.entities):
            if not isinstance(entity, Projectile) or not entity.alive or entity.held_by is not None:
                continue
            if isinstance(entity, Fruit) and not entity.sliced and self._knife_hits(ctrl, s, entity):
                self.mode.slice_fruit(entity, ctrl.player_id, s.velocity)
            elif isinstance(entity, Bomb) and not entity.exploded and self._knife_hits(ctrl, s, entity):
                self.mode.explode_bomb(entity, ctrl.player_id)

    def _try_stop_limiter(self, s: HandSample) -> None:
        """Halt a limiter whose leading tip is covered by an open palm.

        :param s: current hand sample.
        :type s: fruit_knight.vision.hands.HandSample
        """
        for entity in self.mode.entities:
            if isinstance(entity, BarrierLimiter) and entity.alive and not entity.retracting:
                if distance(s.palm, entity.tip) <= entity.cfg.tip_hit_radius:
                    entity.stop_requested = True
