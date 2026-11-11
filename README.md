# Fruit Knight

**Fruit Knight** is a webcam-controlled **Serious Game for Upper-Limb Physical Rehabilitation and Frailty
Assessment**, developed for the course *Interacción Persona-Máquina (IPM) mediante visión por computador*
(reference concept: <https://github.com/CarloHSUA/IPM/>).

Players stand in front of a webcam. **MediaPipe** tracks their bodies and hands, **Pymunk** simulates the
fruits and hazards as 2D rigid bodies, and **Pygame CE** renders everything on top of the live camera feed.

## Serious-game rationale

| Mechanic | Exercise | Rehabilitation target |
|---|---|---|
| **Slicing fruits** (knife hand) | Reaching across the frame with extended hand and adducted fingers | Dynamic range of motion (shoulder abduction/flexion, elbow extension) and visuomotor reaction speed |
| **Stopping limiters** (open palm on the tip) | Holding a palm steadily against an advancing barrier | Isometric upper-limb endurance, shoulder/arm stability, proprioceptive control |
| **Holders** (Grenade v1) | Open palm → closed fist, sustained for *X* seconds | Palmar grasp rehabilitation, palmar flexion/extension, grip endurance, fine motor control |
| **Throwers** (Grenade v2) and **Football** | Grab, accelerate with a fist, release with an open hand | Ballistic coordination, kinetic-chain transfer, timing and directional release |

## Quick start

Requirements: Python 3.10+ and a webcam (the game also works with the mouse when no camera is found).

```bash
./scripts/run.sh                # creates .venv, installs dependencies, downloads MediaPipe models, launches
./scripts/run.sh --reinstall    # force dependency reinstall
./scripts/run.sh --no-camera    # play with the mouse (left = fist, right = open palm, none = knife)
```

On Windows run the scripts from Git Bash (or WSL). Manual launch:

```bash
python -m venv .venv && source .venv/bin/activate      # .venv\Scripts\activate on Windows
pip install -r requirements.txt
PYTHONPATH=src python -m fruit_knight.main
```

The MediaPipe models (`pose_landmarker_lite.task`, `hand_landmarker.task`) are downloaded from Google's
official storage into `assets/models/` on first use.

## Screen flow

1. **Main menu** → **Match setup**: players (1-4), game mode (incompatible choices are corrected
   automatically), initial lives, timespan, instant death on bombs / grenades, toggles for bombs, limiters,
   holders and throwers, and the tracking mode (*Full Pose + Hands* with coloured mannequins, or
   *Lightweight Hands-Only* with screen zones).
2. **Camera & play area**: camera index selector with a mirrored live preview; drag a rectangle with the
   mouse to crop the active play area (**Reset to Full Frame** restores the whole image).
3. **Countdown (5 s)** over the live feed with each player's coloured skeleton/hands visible, then the match.
   **SPACE** pauses (physics, timers and spawners freeze); **SPACE** again runs the same 5-second countdown
   before resuming. **ESC** from the pause screen returns to the menu.
4. **Results**: standings and per-player breakdown, **Play Again** or **Return to Menu**.

## Hand states

| State | How to do it | What it does |
|---|---|---|
| `KNIFE_HAND` | Four fingers extended **and together** | The **only** state that slices fruits and detonates bombs |
| `OPEN_PALM` | Four fingers extended and **spread** | Stops a limiter placed on its leading tip; ready state before grabbing; never cuts |
| `CLOSED_FIST` | Fingers curled | Open → fist near an object grabs it (it follows the palm and the hand is occupied) |
| `RELEASE_WITH_INERTIA` | Fist → open hand while holding | Object is thrown with the smoothed hand velocity × `throw_inertia_multiplier` |

Each player can use both hands. Players get a fixed colour: P1 cyan, P2 coral red, P3 lime green, P4 gold.

## Game entities

- **Fruit** (watermelon, coconut, apple, banana, berry): slice for points; missing one costs its target player a life.
  It can be grabbed and thrown, but it still has to be sliced.
- **Bomb**: slicing it costs a life (or all lives with *instant death*). Palms and fists are safe, so bombs can be thrown away.
- **Barrier limiter**: a trunk/beam entering from a side edge that advances until it reaches the opposite edge. An open palm on its
  tip stops it. At most one at a time. Fruits bounce off its underside and roll on top of it (Pymunk).
- **Holder** (Grenade v1): grab it and keep the fist closed; the radial timer only advances while held. Defused holders can be dropped
  safely; an un-defused one leaving the screen costs a life (or instant death).
- **Thrower** (Grenade v2): grab it and throw it into the **target zone** shown at a screen margin before its expiry timer ends.

### Physics

Effective gravity is `g_eff = g0 · weight`. Each launch picks a random apex height `H` (ratio of the screen height) and angle `θ`:
`v_y0 = √(2·g_eff·H)`, `v_x0 = v_y0·tan θ`, so heavier objects move faster both ways. Gravity is applied in a custom Pymunk
`velocity_func` per body.

## Game modes and scoring

| Mode | Rules |
|---|---|
| `1p_endurance` | One player, *N* lives; survive and score as much as possible |
| `np_endurance` | 2-4 players with independent lives and scores; eliminated players keep their score; the winner has the highest score |
| `np_competition` | Fixed timespan (60/120/180 s...). Penalties cost lives or points (`penalty_points_loss`) depending on the *Competition penalty* option; highest score at 00:00 wins |
| `2p_football` | P1 (left) vs P2 (right). Throw fruits into the opponent's goal (whole outer vertical edge plus `goal_bottom_edge_ratio` of the bottom edge next to that corner). Only fruits last thrown by the attacker score; limiters are disabled; holders/throwers spawn as a pair, one per side |

```
Score_i = Σ fruit points + holders·holder_points + throwers·thrower_points + floor(t_survived · time_multiplier)
          (+ goals · football_goal_points − penalty points in competition/point mode)
```

Spawn pressure grows with match time: `interval(t) = max(min_spawn_interval, base · exp(−rate · t))` with random jitter.
In multi-player modes spawned fruits and hazards are assigned to a target player (coloured halo, spawn inside that player's sector);
anyone can slice or interact to earn points, but the penalty goes to the assigned player (the bomb penalty goes to whoever slices it).

## Configuration

Everything tunable lives in [`config/settings.yaml`](config/settings.yaml) (resolution, FPS, countdown, gravity, spawn curve, per-entity
weights/radii/heights/angles/delays, scoring weights, gesture thresholds, football goal ratio, player colours, UI palette, setup defaults)
and is loaded into typed dataclasses (`src/fruit_knight/config`).

## Assets and procedural fallback

All sprite paths are configured in `settings.yaml` (e.g. `assets/sprites/fruits/watermelon.png`). If a file is missing, `AssetManager`
generates and caches an anti-aliased procedural sprite, so the game is fully playable without any image. Drop real `.png` files at the
configured paths to replace them (see [`TODO_REPORT.md`](TODO_REPORT.md)).

## Project layout

```
src/fruit_knight/
  config/     YAML loader, dataclasses, validation
  vision/     camera capture, ROI, MediaPipe trackers, gesture classifier, hand velocity
  physics/    Pymunk world + collision handlers, launch kinematics, coordinate conversion
  entities/   BaseEntity, Fruit, Bomb, BarrierLimiter, Holder, Thrower, TargetZone, factory
  modes/      BaseGameMode, Solo/Multi endurance, Competition, Football, spawner, interaction rules
  ui/         pygame-gui screens (menu, setup, camera ROI, game, results), HUD, overlays
  rendering/  AssetManager + procedural painters, skeleton overlay, slice trails, effects
  utils/      math helpers, timers, constants, PyInstaller-aware path resolver
scripts/      run.sh · docs.sh · package.sh
tests/        pytest suite (rules, physics, vision, UI smoke, docstring policy)
```

## Documentation

```bash
./scripts/docs.sh          # Sphinx + furo (dark mode) → docs/html/index.html
```

The API reference is generated from Sphinx-style docstrings; the compiled site is published to GitHub Pages by
`.github/workflows/docs.yaml` once the branch reaches `main`.

## Tests

```bash
pip install -r requirements.txt
python -m pytest tests
```

## Packaging

```bash
./scripts/package.sh [output.zip]    # builds the docs first; default: fruit_knight_submission.zip
```

The archive contains `src/`, `assets/`, `config/`, `scripts/`, `requirements.txt`, `README.md` and `docs/html/` (no `.venv`, `.git` or caches).
`.github/workflows/build.yaml` builds Windows and Linux executables with PyInstaller on pushes to `main`.

## Technical notes

- The UI uses **pygame-gui** (natively inside the single pygame-ce window). `pygame-menu` was not used because it pulls in the
  non-CE `pygame` package, which conflicts with `pygame-ce`.
- Vision runs in a worker thread (capture → mirror → ROI crop → MediaPipe) and the game consumes the latest result, so the render loop
  keeps its target FPS even on slow CPUs. Use *Lightweight Hands-Only* mode on low-end laptops.
- If no pose is visible in *Full Pose + Hands* mode, hands are assigned to screen zones so the game stays playable.
