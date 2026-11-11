# TODO Report - Fruit Knight

Everything below is **not** blocking: the game is fully playable today because missing images fall back to procedural sprites
and missing sounds are skipped silently.

## 1. Assets currently using the procedural fallback

Replace any of these files with real art (same path, any size; it is scaled automatically). Paths are configured in `config/settings.yaml`.

### Sprites (`.png`)

- [ ] `assets/sprites/fruits/watermelon.png`
- [ ] `assets/sprites/fruits/coconut.png`
- [ ] `assets/sprites/fruits/apple.png`
- [ ] `assets/sprites/fruits/banana.png`
- [ ] `assets/sprites/fruits/berry.png`
- [ ] `assets/sprites/bombs/bomb.png`
- [ ] `assets/sprites/limiters/trunk.png` (horizontal texture, **tip on the right end**)
- [ ] `assets/sprites/limiters/beam.png` (horizontal texture, **tip on the right end**)
- [ ] `assets/sprites/holders/holder_active.png`
- [ ] `assets/sprites/holders/holder_defused.png`
- [ ] `assets/sprites/throwers/thrower.png`
- [ ] `assets/sprites/throwers/target_portal.png` (stretched to the target zone rectangle)
- [ ] `assets/sprites/ui/heart.png` (lost lives are greyed automatically)
- [ ] `assets/sprites/ui/background.png` (menu / no-camera backdrop)
- [ ] `assets/sprites/ui/logo.png` (title logo)

### Sound effects (`.wav`, optional - no sound is bundled)

- [ ] `assets/audio/slice.wav`
- [ ] `assets/audio/explosion.wav`
- [ ] `assets/audio/grab.wav`
- [ ] `assets/audio/throw.wav`
- [ ] `assets/audio/defuse.wav`
- [ ] `assets/audio/success.wav`
- [ ] `assets/audio/goal.wav`
- [ ] `assets/audio/eliminated.wav`

### Other

- [ ] `assets/icon.ico` is a generated placeholder (apple on a dark tile); replace it with the final icon if desired.

## 2. Manual steps before the academic submission

- [ ] **Test with a real webcam.** The development machine had no camera, so live gesture recognition was validated only with synthetic
  landmarks and blank frames. Check `knife_finger_spread_max_ratio`, `extended_ratio`, `fist_curl_ratio`, `min_curled_fingers` and
  `throw_inertia_multiplier` in `config/settings.yaml` with real hands and adjust if postures are misclassified.
- [ ] Verify multi-player play (2-4 people) in both tracking modes; use *Lightweight Hands-Only* on slow laptops.
- [ ] Rename the archive with the **exact student names**: `./scripts/package.sh "Name1_Name2.zip"`.
- [ ] Record the **10-minute demo video** (menus, calibration/ROI, every mode, each hand state, limiter, holder, thrower, football).
- [ ] Run `./scripts/docs.sh` once more right before packaging (`package.sh` already does it) and review `docs/html/index.html`.
- [ ] Merge `agi/code` into `main` so the GitHub Actions run, then in the repository settings enable **Pages -> Source: GitHub Actions**.
- [ ] Check the first `Build Executables` run: the PyInstaller command is unchanged from the specification and has not been executed locally.
  If a binary misses data files (pygame-gui themes) or MediaPipe libraries, add `--collect-data pygame_gui --collect-all mediapipe` to the workflow.
- [ ] Models are not stored in git: the first launch downloads `pose_landmarker_lite.task` and `hand_landmarker.task` (internet needed once).
  The `.zip` produced on a machine that already ran the game contains them, so the submission works offline.
