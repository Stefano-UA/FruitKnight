"""Tests for game rules driven by synthetic hand samples."""

from __future__ import annotations

import random

import pytest

from fruit_knight.config import load_config
from fruit_knight.entities import BarrierLimiter, Bomb, Fruit, Holder, HolderState, Thrower
from fruit_knight.modes import MatchSetup, create_mode
from fruit_knight.modes.base import BaseGameMode
from fruit_knight.utils.constants import HandState, ModeId
from fruit_knight.vision.hands import HandSample

CFG = load_config()
SIZE = (CFG.window.width, CFG.window.height)
DT = 1 / 60


def hand(pid: int, state: HandState, palm: tuple[float, float], vel=None, label: str = "Right") -> dict[str, HandSample]:
    """Create one synthetic hand sample.

    :param pid: player id.
    :type pid: int
    :param state: posture.
    :type state: fruit_knight.utils.constants.HandState
    :param palm: palm centre in pixels.
    :type palm: tuple[float, float]
    :param vel: hand velocity; a knife hand defaults to a fast stroke, other postures to rest.
    :type vel: tuple[float, float] | None
    :param label: hand label.
    :type label: str
    :return: sample mapping.
    :rtype: dict[str, fruit_knight.vision.hands.HandSample]
    """
    key = f"p{pid}:{label}"
    if vel is None:
        vel = (900.0, 0.0) if state == HandState.KNIFE_HAND else (0.0, 0.0)
    return {key: HandSample(key, pid, state, palm, (palm[0], palm[1] - 60), (palm[0], palm[1] + 30), vel)}


def new_mode(mode: ModeId, players: int = 1, **overrides) -> BaseGameMode:
    """Create a mode with hazards disabled unless overridden.

    :param mode: mode id.
    :type mode: fruit_knight.utils.constants.ModeId
    :param players: number of players.
    :type players: int
    :param overrides: ``MatchSetup`` attribute overrides.
    :type overrides: typing.Any
    :return: mode instance.
    :rtype: fruit_knight.modes.base.BaseGameMode
    """
    setup = MatchSetup(players=players, mode=mode, lives=3, timespan=60,
                       enable_bombs=False, enable_limiters=False, enable_holders=False, enable_throwers=False)
    for k, v in overrides.items():
        setattr(setup, k, v)
    m = create_mode(CFG, setup, SIZE, random.Random(3))
    # Disable automatic fruit stream for deterministic tests.
    m.spawner._next_fruit = {lane: 1e9 for lane in m.spawner.lanes}
    return m


def place(entity, pos, vel=(0.0, 0.0)) -> None:
    """Teleport an entity.

    :param entity: projectile to move.
    :type entity: fruit_knight.entities.base.Projectile
    :param pos: position in pixels.
    :type pos: tuple[float, float]
    :param vel: velocity in pixels per second.
    :type vel: tuple[float, float]
    """
    entity.body.position = pos
    entity.body.velocity = vel


def test_knife_slices_fruit_and_scores() -> None:
    """Only a knife hand slices; open palm and fist do not."""
    m = new_mode(ModeId.ENDURANCE_1P)
    fruit = m.factory.fruit(600, 1, "apple")
    m.entities.append(fruit)
    place(fruit, (600, 300))
    m.update(DT, hand(1, HandState.OPEN_PALM, (600, 330)))
    assert fruit.alive and not fruit.sliced
    m.update(DT, hand(1, HandState.KNIFE_HAND, (600, 330)))
    assert fruit.sliced and m.players[1].fruit_points == fruit.points
    assert any(e.kind == "slice" for e in m.drain_events())


def test_missed_fruit_costs_life_and_game_over() -> None:
    """Falling fruit removes a life; zero lives ends the match."""
    m = new_mode(ModeId.ENDURANCE_1P, lives=1)
    fruit = m.factory.fruit(600, 1, "apple")
    m.entities.append(fruit)
    place(fruit, (600, SIZE[1] + 200), (0, 300))
    m.update(DT, {})
    assert m.players[1].eliminated and m.finished


def test_bomb_penalties_respect_instant_death_flag() -> None:
    """Sliced bomb costs one life, or all lives with instant death."""
    for instant, expected in ((False, 2), (True, 0)):
        m = new_mode(ModeId.ENDURANCE_1P, instant_death_bombs=instant)
        bomb = m.factory.bomb(600, 1)
        m.entities.append(bomb)
        place(bomb, (600, 300))
        m.update(DT, hand(1, HandState.KNIFE_HAND, (600, 330)))
        assert m.players[1].lives == expected


def test_bomb_safe_with_palm_and_fist_and_throwable() -> None:
    """Palm and grabbing never detonate a bomb; it can be thrown away."""
    m = new_mode(ModeId.ENDURANCE_1P)
    bomb = m.factory.bomb(600, 1)
    m.entities.append(bomb)
    place(bomb, (600, 300))
    m.update(DT, hand(1, HandState.OPEN_PALM, (600, 300)))
    m.update(DT, hand(1, HandState.CLOSED_FIST, (600, 300)))
    assert bomb.held_by and m.players[1].lives == 3
    m.update(DT, hand(1, HandState.OPEN_PALM, (600, 300), vel=(500, -300)))
    assert bomb.held_by is None and bomb.velocity[0] > 400 and m.players[1].lives == 3


def test_grabbed_fruit_is_not_scored_but_must_be_sliced() -> None:
    """Grabbing keeps the fruit alive without points; it can still be sliced after the throw."""
    m = new_mode(ModeId.ENDURANCE_1P)
    fruit = m.factory.fruit(600, 1, "berry")
    m.entities.append(fruit)
    place(fruit, (600, 300))
    m.update(DT, hand(1, HandState.OPEN_PALM, (600, 300)))
    m.update(DT, hand(1, HandState.CLOSED_FIST, (600, 300)))
    assert fruit.held_by and m.players[1].fruit_points == 0
    m.update(DT, hand(1, HandState.OPEN_PALM, (600, 300)))
    place(fruit, (700, 300))
    m.update(DT, hand(1, HandState.KNIFE_HAND, (700, 330)))
    assert fruit.sliced


def test_occupied_hand_cannot_slice_but_second_hand_can() -> None:
    """A fist holding an item cannot slice; the other hand can."""
    m = new_mode(ModeId.ENDURANCE_1P)
    held = m.factory.holder(300, 1)
    fruit = m.factory.fruit(800, 1, "apple")
    m.entities.extend([held, fruit])
    place(held, (300, 300))
    place(fruit, (800, 300))
    m.update(DT, hand(1, HandState.OPEN_PALM, (300, 300), label="Left"))
    m.update(DT, hand(1, HandState.CLOSED_FIST, (300, 300), label="Left"))
    assert held.held_by
    both = hand(1, HandState.CLOSED_FIST, (790, 330), label="Left") | hand(1, HandState.KNIFE_HAND, (800, 330), label="Right")
    both["p1:Left"].palm = (790, 330)
    m.update(DT, both)
    assert fruit.sliced and held.held_by


def test_holder_defuse_flow_and_failure() -> None:
    """Holder awards points once held long enough; un-defused exit is penalised."""
    m = new_mode(ModeId.ENDURANCE_1P)
    holder: Holder = m.factory.holder(600, 1)
    m.entities.append(holder)
    place(holder, (600, 300))
    m.update(DT, hand(1, HandState.OPEN_PALM, (600, 300)))
    t = 0.0
    while holder.state == HolderState.ACTIVE and t < 10:
        m.update(DT, hand(1, HandState.CLOSED_FIST, (600, 300)))
        t += DT
    assert holder.state == HolderState.DEFUSED and m.players[1].holders_defused == 1
    m.update(DT, hand(1, HandState.OPEN_PALM, (600, 300)))
    place(holder, (600, SIZE[1] + 300), (0, 200))
    m.update(DT, {})
    assert m.players[1].lives == 3  # defused holder leaves safely

    bad = m.factory.holder(600, 1)
    m.entities.append(bad)
    place(bad, (600, SIZE[1] + 300), (0, 200))
    m.update(DT, {})
    assert m.players[1].lives == 2


def test_thrower_delivery_awards_points() -> None:
    """Throwing into the target zone scores and removes both entities."""
    m = new_mode(ModeId.ENDURANCE_1P)
    zone = m.factory.target_zone("left")
    thrower: Thrower = m.factory.thrower(600, 1, zone)
    m.entities.extend([zone, thrower])
    x, y, w, h = zone.rect
    place(thrower, (x + w + 200, y + h / 2))
    m.update(DT, hand(1, HandState.OPEN_PALM, thrower.position))
    m.update(DT, hand(1, HandState.CLOSED_FIST, thrower.position))
    thrower.move_to((x + w / 2, y + h / 2))
    m.world.step(DT)
    m.update(DT, hand(1, HandState.OPEN_PALM, (x + w / 2, y + h / 2)))
    assert m.players[1].throwers_completed == 1
    assert not thrower.alive and not zone.alive


def test_limiter_stopped_by_open_palm_on_tip() -> None:
    """Open palm over the leading tip freezes the limiter."""
    m = new_mode(ModeId.ENDURANCE_1P)
    limiter = BarrierLimiter(m.world, CFG.limiter, "left", 300.0, 0.0, 30.0)
    m.entities.append(limiter)
    m.update(DT, {})
    tip = limiter.tip
    length = limiter.length
    for _ in range(20):
        m.update(DT, hand(1, HandState.OPEN_PALM, limiter.tip))
    assert limiter.stopped and abs(limiter.length - length) < 1.5
    assert limiter.tip[0] >= tip[0] - 1
    for _ in range(20):
        m.update(DT, {})
    assert limiter.length > length + 20


def test_multi_endurance_independent_lives_and_winner_by_score() -> None:
    """Eliminated players keep score; winner is highest score."""
    m = new_mode(ModeId.ENDURANCE_NP, players=2, lives=1)
    m.players[1].fruit_points = 500
    fruit = m.factory.fruit(900, 2, "apple")
    m.entities.append(fruit)
    place(fruit, (900, SIZE[1] + 200), (0, 300))
    m.update(DT, {})
    assert m.players[2].eliminated and not m.players[1].eliminated and not m.finished
    place_fruit = m.factory.fruit(300, 1, "apple")
    m.entities.append(place_fruit)
    place(place_fruit, (300, SIZE[1] + 200), (0, 300))
    m.update(DT, {})
    assert m.finished
    standings = m.standings()
    assert standings[0].player.player_id == 1 and standings[0].winner


def test_eliminated_player_hands_ignored() -> None:
    """Eliminated players cannot slice anymore."""
    m = new_mode(ModeId.ENDURANCE_NP, players=2)
    m.players[2].eliminated = True
    fruit = m.factory.fruit(600, 1, "apple")
    m.entities.append(fruit)
    place(fruit, (600, 300))
    m.update(DT, hand(2, HandState.KNIFE_HAND, (600, 330)))
    assert not fruit.sliced


def test_competition_clock_and_point_penalties() -> None:
    """Competition ends on time; point penalties never remove lives."""
    m = new_mode(ModeId.COMPETITION_NP, players=2, competition_penalty="points", timespan=1)
    fruit = m.factory.fruit(600, 1, "apple")
    m.entities.append(fruit)
    place(fruit, (600, SIZE[1] + 200), (0, 300))
    m.update(DT, {})
    assert m.players[1].lives == 3 and m.players[1].penalty_points == CFG.scoring.penalty_points_loss
    for _ in range(70):
        m.update(DT, {})
    assert m.finished


def test_score_formula() -> None:
    """Score follows the configured formula."""
    m = new_mode(ModeId.ENDURANCE_1P)
    p = m.players[1]
    p.fruit_points, p.holders_defused, p.throwers_completed, p.survival_time = 100, 2, 1, 10.0
    s = CFG.scoring
    assert m.score_of(1) == 100 + 2 * s.holder_points + s.thrower_points + int(10 * s.time_multiplier)


def test_football_goal_rules() -> None:
    """Goals count only for fruits thrown by the opponent into the defended zone."""
    m = new_mode(ModeId.FOOTBALL_2P, players=2)
    w, h = SIZE
    own = m.factory.fruit(300, 1, "apple")
    m.entities.append(own)
    place(own, (-5.0, 300.0), (-10, 0))
    m.update(DT, {})
    assert m.players[1].lives == 3  # never thrown by player 2: no goal

    shot = m.factory.fruit(300, 1, "apple")
    shot.last_thrower = 2
    m.entities.append(shot)
    place(shot, (-5.0, 300.0), (-10, 0))
    m.update(DT, {})
    assert m.players[1].lives == 2 and m.players[2].goals_scored == 1

    bottom = m.factory.fruit(300, 1, "apple")
    bottom.last_thrower = 1
    m.entities.append(bottom)
    place(bottom, (w * 0.9, h + 5.0), (0, 100))
    m.update(DT, {})
    assert m.players[2].lives == 2 and m.players[1].goals_scored == 1
    assert m.goal_owner((w * 0.5, h + 5)) is None


def test_football_spawns_paired_grenades_and_no_limiter() -> None:
    """Each lane receives its own grenade and limiters never spawn."""
    m = new_mode(ModeId.FOOTBALL_2P, players=2, enable_holders=True, enable_throwers=True, enable_limiters=True)
    m.spawner._holder.next_time = 0.0
    m.spawner._thrower.next_time = 0.0
    m.spawner._limiter.next_time = 0.0
    m.update(DT, {})
    holders = [e for e in m.entities if isinstance(e, Holder)]
    throwers = [e for e in m.entities if isinstance(e, Thrower)]
    assert sorted(h.target_player for h in holders) == [1, 2]
    assert sorted(t.target_player for t in throwers) == [1, 2]
    assert not any(isinstance(e, BarrierLimiter) for e in m.entities)


def test_single_limiter_at_a_time() -> None:
    """The spawner never creates a second limiter while one exists."""
    m = new_mode(ModeId.ENDURANCE_1P, enable_limiters=True)
    for _ in range(3):
        m.spawner._limiter.next_time = 0.0
        m.update(DT, {})
    assert m.count_alive(BarrierLimiter) == 1


def test_setup_auto_validation() -> None:
    """Player count and mode stay compatible."""
    s = MatchSetup.from_config(CFG)
    s.set_players(3)
    assert s.mode == ModeId.ENDURANCE_NP
    s.set_mode(ModeId.FOOTBALL_2P)
    assert s.players == 2
    s.set_players(1)
    assert s.mode == ModeId.ENDURANCE_1P
    s.set_mode(ModeId.COMPETITION_NP)
    assert s.players == 2


@pytest.mark.parametrize("mode,players", [(ModeId.ENDURANCE_1P, 1), (ModeId.ENDURANCE_NP, 3), (ModeId.COMPETITION_NP, 4), (ModeId.FOOTBALL_2P, 2)])
def test_long_random_simulation_is_stable(mode: ModeId, players: int) -> None:
    """Five simulated minutes with every hazard enabled run without errors."""
    setup = MatchSetup(players=players, mode=mode, lives=50, timespan=300)
    m = create_mode(CFG, setup, SIZE, random.Random(11))
    rng = random.Random(5)
    for i in range(60 * 120):
        samples = {}
        for pid in range(1, players + 1):
            state = rng.choice(list(HandState)[:3])
            samples.update(hand(pid, state, (rng.uniform(0, SIZE[0]), rng.uniform(0, SIZE[1])), (rng.uniform(-900, 900), rng.uniform(-900, 900))))
        m.update(DT, samples)
        if m.finished:
            break
    assert m.elapsed > 10
    assert len(m.entities) < 200


def test_still_knife_hand_does_not_cut() -> None:
    """A knife hand must move to cut: resting on fruits and bombs does nothing."""
    m = new_mode(ModeId.ENDURANCE_1P)
    fruit = m.factory.fruit(600, 1, "apple")
    bomb = m.factory.bomb(700, 1)
    m.entities.extend([fruit, bomb])
    place(fruit, (600, 300))
    place(bomb, (700, 300))
    still = CFG.gestures.knife_min_speed * 0.5
    m.update(DT, hand(1, HandState.KNIFE_HAND, (600, 330), vel=(still, 0.0)))
    m.update(DT, hand(1, HandState.KNIFE_HAND, (700, 330), vel=(0.0, 0.0)))
    assert not fruit.sliced and not bomb.exploded and m.players[1].lives == 3
    m.update(DT, hand(1, HandState.KNIFE_HAND, (600, 330), vel=(CFG.gestures.knife_min_speed * 2, 0.0)))
    assert fruit.sliced


def test_difficulty_overrides_merge_over_base() -> None:
    """Each level changes only what it lists; normal equals the base values."""
    from fruit_knight.config import apply_difficulty

    base = CFG
    normal = apply_difficulty(base, "normal")
    easy, hard = apply_difficulty(base, "very_easy"), apply_difficulty(base, "hard")
    assert normal.physics.gravity == base.physics.gravity
    assert easy.physics.gravity < base.physics.gravity < hard.physics.gravity
    assert easy.spawning.base_spawn_interval > hard.spawning.base_spawn_interval
    assert easy.fruits.subtypes["apple"].points == base.fruits.subtypes["apple"].points  # untouched keys survive
    assert easy.fruits.launch.max_angle_deg < hard.fruits.launch.max_angle_deg
    assert [d.label for d in base.difficulties.values()] == ["Very Easy", "Easy", "Normal", "Hard"]


def test_difficulty_config_drives_the_mode() -> None:
    """A mode built from a harder config launches faster and falls harder."""
    from fruit_knight.config import apply_difficulty

    speeds = {}
    for name in ("very_easy", "hard"):
        cfg = apply_difficulty(CFG, name)
        m = create_mode(cfg, MatchSetup(players=1, mode=ModeId.ENDURANCE_1P), SIZE, random.Random(1))
        speeds[name] = m.factory.fruit(600, 1, "apple").g_eff
    assert speeds["hard"] > speeds["very_easy"]


def test_sliced_halves_inherit_inertia() -> None:
    """Halves keep the fruit velocity, rotation speed and gravity instead of spinning wildly."""
    import pygame

    from fruit_knight.modes.events import GameEvent
    from fruit_knight.rendering import AssetManager, EffectsManager, FontCache, SpriteProvider

    pygame.init()
    pygame.display.set_mode((100, 100))
    fx = EffectsManager(CFG, SpriteProvider(CFG, AssetManager()), FontCache())
    fx.handle(GameEvent("slice", (300.0, 300.0), 1, "", {
        "subtype": "apple", "radius": 34, "angle": 0.7, "velocity": (120.0, -400.0),
        "body_angle": 0.5, "angular_velocity": 2.0, "g_eff": 620.0,
    }))
    assert len(fx._halves) == 2
    for half in fx._halves:
        assert abs(half.spin - 2.0) <= 1.0  # same rotation speed as the fruit, small split
        assert abs(half.vel[0] - 120.0) < 120 and abs(half.vel[1] + 400.0) < 120
        assert half.gravity == 620.0
    pygame.quit()
