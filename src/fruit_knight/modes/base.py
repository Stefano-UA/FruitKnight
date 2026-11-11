"""Shared game-mode logic: entity lifecycle, scoring, penalties and results."""

from __future__ import annotations

import math
import random
from abc import ABC, abstractmethod

from fruit_knight.config.schema import GameConfig
from fruit_knight.entities import (
    BarrierLimiter,
    BaseEntity,
    Bomb,
    EntityFactory,
    Fruit,
    Holder,
    HolderState,
    Projectile,
    TargetZone,
    Thrower,
)
from fruit_knight.modes.events import GameEvent
from fruit_knight.modes.interaction import InteractionSystem
from fruit_knight.modes.players import PlayerState, Standing
from fruit_knight.modes.setup import MatchSetup
from fruit_knight.modes.spawner import Spawner
from fruit_knight.physics.world import PhysicsWorld
from fruit_knight.utils.constants import ModeId, PenaltyReason
from fruit_knight.vision.hands import HandSample

Vec = tuple[float, float]


class BaseGameMode(ABC):
    """Template of every game mode; subclasses customise rules through hooks."""

    mode_id: ModeId
    limiter_allowed = True

    def __init__(self, cfg: GameConfig, setup: MatchSetup, size: tuple[int, int], rng: random.Random | None = None) -> None:
        """Create match state, physics world and spawner.

        :param cfg: game configuration.
        :type cfg: fruit_knight.config.schema.GameConfig
        :param setup: match options.
        :type setup: fruit_knight.modes.setup.MatchSetup
        :param size: screen width and height in pixels.
        :type size: tuple[int, int]
        :param rng: random generator; fresh one when omitted.
        :type rng: random.Random | None
        """
        self.cfg = cfg
        self.setup = setup
        self.size = size
        self.rng = rng or random.Random()
        self.world = PhysicsWorld(cfg.physics, size)
        self.factory = EntityFactory(cfg, self.world, self.rng)
        self.players: dict[int, PlayerState] = {
            pid: PlayerState(pid, setup.lives, setup.lives) for pid in range(1, setup.players + 1)
        }
        self.entities: list[BaseEntity] = []
        self.events: list[GameEvent] = []
        self.elapsed = 0.0
        self.finished = False
        self.spawner = Spawner(cfg, setup, self.factory, self.rng, self.spawn_lanes(), self.limiter_allowed)
        self.interaction = InteractionSystem(self)

    # -------------------------------------------------------------- hooks
    def spawn_lanes(self) -> list[int | None]:
        """Define independent spawn lanes.

        :return: ``[None]`` for a shared lane; player ids for per-player lanes.
        :rtype: list[int | None]
        """
        return [None]

    @property
    def time_left(self) -> float | None:
        """Report remaining match time.

        :return: seconds left, ``None`` for untimed modes.
        :rtype: float | None
        """
        return None

    def check_finished(self) -> bool:
        """Decide whether the match is over.

        :return: True when every player is eliminated.
        :rtype: bool
        """
        return not self.alive_ids()

    @abstractmethod
    def on_tick(self, dt: float) -> None:
        """Run mode-specific per-frame logic.

        :param dt: time step in seconds.
        :type dt: float
        """

    def on_fruit_exit(self, fruit: Fruit, side: str) -> None:
        """Handle a fruit leaving the screen.

        :param fruit: exiting fruit.
        :type fruit: fruit_knight.entities.fruit.Fruit
        :param side: exit side.
        :type side: str
        """
        if not fruit.sliced and fruit.target_player is not None:
            self.penalize(fruit.target_player, PenaltyReason.MISS, self._edge_point(fruit.position))

    def apply_penalty_effect(self, player: PlayerState, reason: PenaltyReason, instant: bool) -> None:
        """Apply the cost of a penalty to a player.

        :param player: penalised player.
        :type player: fruit_knight.modes.players.PlayerState
        :param reason: penalty cause.
        :type reason: fruit_knight.utils.constants.PenaltyReason
        :param instant: True when the cause kills instantly.
        :type instant: bool
        """
        player.lives = 0 if instant else player.lives - 1
        if player.lives <= 0:
            self.eliminate(player)

    # ------------------------------------------------------------ queries
    def alive_ids(self) -> list[int]:
        """List non-eliminated players.

        :return: player ids.
        :rtype: list[int]
        """
        return [pid for pid, p in self.players.items() if not p.eliminated]

    def count_alive(self, entity_type: type) -> int:
        """Count live entities of a type.

        :param entity_type: entity class.
        :type entity_type: type
        :return: number of matching live entities.
        :rtype: int
        """
        return sum(1 for e in self.entities if e.alive and isinstance(e, entity_type))

    def score_of(self, player_id: int) -> int:
        """Compute a player's current score.

        :param player_id: player id.
        :type player_id: int
        :return: total score.
        :rtype: int
        """
        return self.players[player_id].score(self.cfg.scoring)

    def emit(self, event: GameEvent) -> None:
        """Queue an event for the presentation layer.

        :param event: event to publish.
        :type event: fruit_knight.modes.events.GameEvent
        """
        self.events.append(event)

    def drain_events(self) -> list[GameEvent]:
        """Take and clear queued events.

        :return: events since the last call.
        :rtype: list[fruit_knight.modes.events.GameEvent]
        """
        events, self.events = self.events, []
        return events

    def _edge_point(self, pos: Vec) -> Vec:
        """Clamp a position inside the visible screen for popups.

        :param pos: raw position.
        :type pos: tuple[float, float]
        :return: position inside the screen with a small margin.
        :rtype: tuple[float, float]
        """
        w, h = self.size
        return min(max(pos[0], 40.0), w - 40.0), min(max(pos[1], 40.0), h - 60.0)

    # ------------------------------------------------------------- scoring
    def penalize(self, player_id: int | None, reason: PenaltyReason, pos: Vec) -> None:
        """Penalise a player according to the cause and match options.

        :param player_id: penalised player.
        :type player_id: int | None
        :param reason: penalty cause.
        :type reason: fruit_knight.utils.constants.PenaltyReason
        :param pos: position where the popup appears.
        :type pos: tuple[float, float]
        """
        player = self.players.get(player_id) if player_id is not None else None
        if player is None or player.eliminated or self.finished:
            return
        instant = (reason == PenaltyReason.BOMB and self.setup.instant_death_bombs) or (
            reason == PenaltyReason.GRENADE and self.setup.instant_death_grenades
        )
        self.apply_penalty_effect(player, reason, instant)
        label = {"miss": "MISS", "bomb": "BOOM", "grenade": "GRENADE", "goal": "GOAL CONCEDED"}[reason.value]
        self.emit(GameEvent("popup", pos, player_id, f"{label}!" + (" DEAD" if instant else ""), {"bad": True}))

    def eliminate(self, player: PlayerState) -> None:
        """Mark a player eliminated and free their hands.

        :param player: player to eliminate.
        :type player: fruit_knight.modes.players.PlayerState
        """
        player.eliminated = True
        player.lives = max(0, player.lives)
        self.interaction.release_player(player.player_id)
        self.emit(GameEvent("eliminated", (self.size[0] / 2, self.size[1] / 2), player.player_id, "ELIMINATED"))

    def slice_fruit(self, fruit: Fruit, player_id: int, hand_velocity: Vec) -> None:
        """Resolve a fruit sliced by a knife hand.

        :param fruit: sliced fruit.
        :type fruit: fruit_knight.entities.fruit.Fruit
        :param player_id: player who sliced it.
        :type player_id: int
        :param hand_velocity: hand velocity giving the cut direction.
        :type hand_velocity: tuple[float, float]
        """
        fruit.sliced = True
        player = self.players[player_id]
        player.fruits_sliced += 1
        player.fruit_points += fruit.points
        angle = math.atan2(hand_velocity[1], hand_velocity[0]) if any(hand_velocity) else 0.0
        self.emit(GameEvent("slice", fruit.position, player_id, "", {
            "subtype": fruit.subtype, "radius": fruit.radius, "angle": angle,
            "velocity": fruit.velocity, "spin": fruit.body.angle if fruit.body else 0.0,
        }))
        self.emit(GameEvent("popup", fruit.position, player_id, f"+{fruit.points}"))
        fruit.remove()

    def explode_bomb(self, bomb: Bomb, player_id: int) -> None:
        """Resolve a bomb detonated by a knife hand.

        :param bomb: detonated bomb.
        :type bomb: fruit_knight.entities.bomb.Bomb
        :param player_id: player who sliced it.
        :type player_id: int
        """
        bomb.exploded = True
        self.players[player_id].bombs_hit += 1
        self.emit(GameEvent("explosion", bomb.position, player_id, "", {"radius": bomb.radius}))
        pos = self._edge_point(bomb.position)
        bomb.remove()
        self.penalize(player_id, PenaltyReason.BOMB, pos)

    # ------------------------------------------------------------- lifecycle
    def update(self, dt: float, samples: dict[str, HandSample]) -> None:
        """Advance the match by one frame.

        :param dt: time step in seconds.
        :type dt: float
        :param samples: current hand samples.
        :type samples: dict[str, fruit_knight.vision.hands.HandSample]
        """
        if self.finished:
            return
        self.elapsed += dt
        self.entities.extend(self.spawner.update(self.elapsed, self))
        self.interaction.process(samples, self.elapsed)
        self.world.step(dt)
        for entity in self.entities:
            if entity.alive:
                entity.update(dt)
        self._resolve_entities()
        for player in self.players.values():
            if not player.eliminated:
                player.survival_time += dt
        self.on_tick(dt)
        if self.check_finished():
            self.finish()

    def finish(self) -> None:
        """End the match and free held entities."""
        self.finished = True
        self.interaction.release_all()

    def _resolve_entities(self) -> None:
        """Resolve defusals, deliveries, exits and cleanup for every entity."""
        for entity in self.entities:
            if isinstance(entity, BarrierLimiter):
                if not entity.alive:
                    entity.remove()
                continue
            if not isinstance(entity, Projectile) or not entity.alive:
                continue
            if isinstance(entity, Holder) and entity.just_defused:
                self._defuse(entity)
            elif isinstance(entity, Thrower) and self._resolve_thrower(entity):
                continue
            if self.on_entity_checked(entity) or not entity.alive:
                continue
            side = entity.exit_side()
            if side is not None and entity.held_by is None:
                self._handle_exit(entity, side)
        for entity in self.entities:
            if isinstance(entity, TargetZone) and entity.alive and not self._zone_in_use(entity):
                entity.remove()
        self.entities = [e for e in self.entities if e.alive]

    def on_entity_checked(self, entity: Projectile) -> bool:
        """Hook run on every live projectile before exit checks.

        :param entity: projectile being checked.
        :type entity: fruit_knight.entities.base.Projectile
        :return: True when the hook consumed the entity.
        :rtype: bool
        """
        return False

    def _zone_in_use(self, zone: TargetZone) -> bool:
        """Check whether a live thrower still targets a zone.

        :param zone: target zone.
        :type zone: fruit_knight.entities.target_zone.TargetZone
        :return: True when a live thrower references it.
        :rtype: bool
        """
        return any(isinstance(e, Thrower) and e.alive and e.zone is zone for e in self.entities)

    def _defuse(self, holder: Holder) -> None:
        """Award defusal points to the holding player.

        :param holder: defused holder.
        :type holder: fruit_knight.entities.holder.Holder
        """
        pid = holder.last_holder
        if pid is None:
            return
        self.players[pid].holders_defused += 1
        self.emit(GameEvent("defuse", holder.position, pid, f"+{self.cfg.scoring.holder_points}"))

    def _resolve_thrower(self, thrower: Thrower) -> bool:
        """Resolve delivery or expiry of a thrower.

        :param thrower: thrower to check.
        :type thrower: fruit_knight.entities.thrower.Thrower
        :return: True when the thrower was resolved and removed.
        :rtype: bool
        """
        if thrower.delivered:
            pid = thrower.last_thrower if thrower.last_thrower is not None else thrower.target_player
            if pid in self.players:
                self.players[pid].throwers_completed += 1
                self.emit(GameEvent("thrower_success", thrower.position, pid, f"+{self.cfg.scoring.thrower_points}"))
            thrower.remove()
            return True
        if thrower.expiry.done and thrower.held_by is None:
            self.penalize(thrower.target_player, PenaltyReason.GRENADE, self._edge_point(thrower.position))
            self.emit(GameEvent("explosion", thrower.position, thrower.target_player, "", {"radius": thrower.radius}))
            thrower.remove()
            return True
        return False

    def _handle_exit(self, entity: Projectile, side: str) -> None:
        """Resolve an entity that left the screen.

        :param entity: exiting entity.
        :type entity: fruit_knight.entities.base.Projectile
        :param side: exit side.
        :type side: str
        """
        pos = self._edge_point(entity.position)
        if isinstance(entity, Fruit):
            self.on_fruit_exit(entity, side)
        elif isinstance(entity, (Holder, Thrower)):
            if not (isinstance(entity, Holder) and entity.state == HolderState.DEFUSED):
                self.penalize(entity.target_player, PenaltyReason.GRENADE, pos)
                self.emit(GameEvent("explosion", pos, entity.target_player, "", {"radius": entity.radius}))
        entity.remove()

    # --------------------------------------------------------------- results
    def standings(self) -> list[Standing]:
        """Rank players by final score.

        :return: standings sorted from best to worst, ties share the rank.
        :rtype: list[fruit_knight.modes.players.Standing]
        """
        scored = sorted(((self.score_of(pid), p) for pid, p in self.players.items()), key=lambda sp: -sp[0])
        top = scored[0][0] if scored else 0
        rows: list[Standing] = []
        for index, (score, player) in enumerate(scored):
            rank = rows[-1].rank if rows and rows[-1].score == score else index + 1
            rows.append(Standing(rank, player, score, score == top))
        return rows
