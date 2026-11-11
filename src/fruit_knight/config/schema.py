"""Typed dataclasses mirroring ``config/settings.yaml``."""

from __future__ import annotations

from dataclasses import dataclass, field

Range = tuple[float, float]
Color = tuple[int, int, int]


@dataclass
class WindowConfig:
    """Window and loop settings."""

    width: int = 1280
    height: int = 720
    fps: int = 60
    title: str = "Fruit Knight"
    fullscreen: bool = False


@dataclass
class PhysicsConfig:
    """Pymunk world parameters."""

    gravity: float = 620.0
    substeps: int = 2
    damping: float = 1.0
    spawn_offset: float = 40.0
    exit_margin: float = 90.0
    max_spin: float = 4.0
    max_entity_speed: float = 3200.0


@dataclass
class SpawningConfig:
    """Fruit stream difficulty curve."""

    base_spawn_interval: float = 1.7
    spawn_acceleration_rate: float = 0.006
    jitter_range: Range = (0.75, 1.25)
    min_spawn_interval: float = 0.55
    spawn_margin_ratio: float = 0.12
    fruit_initial_delay_range: Range = (0.5, 1.2)


@dataclass
class LaunchProfile:
    """Random launch parameters shared by projectiles."""

    min_height_ratio: float = 0.55
    max_height_ratio: float = 0.88
    min_angle_deg: float = 2.0
    max_angle_deg: float = 24.0


@dataclass
class FruitSubtype:
    """One fruit variety."""

    weight: float = 1.0
    radius: float = 34.0
    points: int = 10
    color: Color = (255, 255, 255)
    spawn_weight: float = 1.0
    sprite_path: str = ""


@dataclass
class FruitConfig:
    """Fruit family settings."""

    elasticity: float = 0.35
    friction: float = 0.6
    launch: LaunchProfile = field(default_factory=LaunchProfile)
    subtypes: dict[str, FruitSubtype] = field(default_factory=dict)


@dataclass
class BombConfig:
    """Bomb settings."""

    weight: float = 1.1
    radius: float = 34.0
    color: Color = (40, 40, 48)
    elasticity: float = 0.35
    friction: float = 0.6
    initial_delay_range: Range = (8.0, 14.0)
    interval_range: Range = (4.5, 9.0)
    launch: LaunchProfile = field(default_factory=LaunchProfile)
    sprite_path: str = ""


@dataclass
class LimiterConfig:
    """Barrier limiter settings."""

    initial_delay_range: Range = (14.0, 22.0)
    interval_range: Range = (14.0, 24.0)
    min_y_ratio: float = 0.28
    max_y_ratio: float = 0.62
    max_incline_deg: float = 12.0
    advance_speed: float = 150.0
    retract_speed: float = 520.0
    lifetime_range: Range = (7.0, 12.0)
    thickness: float = 34.0
    tip_hit_radius: float = 62.0
    elasticity: float = 0.45
    friction: float = 0.7
    sprite_path: str = ""
    beam_sprite_path: str = ""


@dataclass
class HolderConfig:
    """Holder grenade settings."""

    weight: float = 1.0
    radius: float = 36.0
    initial_delay_range: Range = (16.0, 26.0)
    interval_range: Range = (16.0, 28.0)
    hold_duration_range: Range = (1.5, 3.0)
    elasticity: float = 0.3
    friction: float = 0.6
    launch: LaunchProfile = field(default_factory=LaunchProfile)
    active_sprite_path: str = ""
    defused_sprite_path: str = ""
    active_color: Color = (255, 112, 67)
    defused_color: Color = (102, 187, 106)


@dataclass
class ThrowerConfig:
    """Thrower grenade settings."""

    weight: float = 1.0
    radius: float = 36.0
    initial_delay_range: Range = (28.0, 40.0)
    interval_range: Range = (18.0, 30.0)
    expiration_range: Range = (7.0, 10.0)
    elasticity: float = 0.3
    friction: float = 0.6
    launch: LaunchProfile = field(default_factory=LaunchProfile)
    zone_thickness: float = 110.0
    zone_length_ratio: float = 0.32
    sprite_path: str = ""
    zone_sprite_path: str = ""
    color: Color = (66, 165, 245)


@dataclass
class ScoringConfig:
    """Score weights."""

    holder_points: int = 50
    thrower_points: int = 75
    time_multiplier: float = 0.5
    penalty_points_loss: int = 25
    football_goal_points: int = 100


@dataclass
class FootballConfig:
    """Versus mode rules."""

    goal_bottom_edge_ratio: float = 0.15


@dataclass
class GestureConfig:
    """Gesture thresholds and interaction radii."""

    extended_ratio: float = 1.12
    fist_curl_ratio: float = 1.0
    min_curled_fingers: int = 3
    knife_finger_spread_max_ratio: float = 0.42
    throw_inertia_multiplier: float = 1.15
    debounce_frames: int = 2
    velocity_window_s: float = 0.12
    velocity_smoothing: float = 0.5
    knife_thickness: float = 22.0
    grab_radius: float = 46.0
    grab_grace_s: float = 0.35
    hand_lost_grace_s: float = 0.30
    hand_hit_radius: float = 54.0


@dataclass
class CameraConfig:
    """Webcam capture request."""

    default_index: int = 0
    request_width: int = 1280
    request_height: int = 720
    request_fps: int = 30
    index_options: list[int] = field(default_factory=lambda: [0, 1, 2, 3, 4])


@dataclass
class TrackingConfig:
    """Computer vision settings."""

    default_mode: str = "pose_hands"
    pose_model_file: str = "pose_landmarker_lite.task"
    hand_model_file: str = "hand_landmarker.task"
    pose_model_url: str = ""
    hand_model_url: str = ""
    min_detection_confidence: float = 0.5
    min_tracking_confidence: float = 0.5
    assign_max_distance: float = 0.45
    max_inference_side: int = 640
    camera: CameraConfig = field(default_factory=CameraConfig)


@dataclass
class PlayersConfig:
    """Player identity styling."""

    colors: list[Color] = field(default_factory=list)
    names: list[str] = field(default_factory=list)


@dataclass
class UiConfig:
    """Look and feel."""

    background_color: Color = (14, 16, 28)
    panel_color: Color = (24, 28, 48)
    accent_color: Color = (255, 171, 64)
    text_color: Color = (236, 239, 244)
    muted_color: Color = (140, 150, 175)
    danger_color: Color = (255, 82, 82)
    camera_dim_alpha: int = 70
    trail_length: int = 14
    trail_lifetime_s: float = 0.25
    popup_lifetime_s: float = 1.0
    icon_path: str = "assets/icon.ico"
    heart_sprite_path: str = ""
    background_sprite_path: str = ""
    logo_sprite_path: str = ""


@dataclass
class DefaultsConfig:
    """Initial values of the match setup screen."""

    players: int = 1
    mode: str = "1p_endurance"
    lives: int = 3
    timespan: int = 120
    instant_death_bombs: bool = False
    instant_death_grenades: bool = False
    enable_bombs: bool = True
    enable_limiters: bool = True
    enable_holders: bool = True
    enable_throwers: bool = True
    competition_penalty: str = "lives"
    tracking_mode: str = "pose_hands"
    life_options: list[int] = field(default_factory=lambda: [1, 2, 3, 5, 7, 10])
    timespan_options: list[int] = field(default_factory=lambda: [30, 60, 120, 180, 300])


@dataclass
class GameConfig:
    """Root configuration object."""

    window: WindowConfig = field(default_factory=WindowConfig)
    countdown_seconds: float = 5.0
    physics: PhysicsConfig = field(default_factory=PhysicsConfig)
    spawning: SpawningConfig = field(default_factory=SpawningConfig)
    fruits: FruitConfig = field(default_factory=FruitConfig)
    bomb: BombConfig = field(default_factory=BombConfig)
    limiter: LimiterConfig = field(default_factory=LimiterConfig)
    holder: HolderConfig = field(default_factory=HolderConfig)
    thrower: ThrowerConfig = field(default_factory=ThrowerConfig)
    scoring: ScoringConfig = field(default_factory=ScoringConfig)
    football: FootballConfig = field(default_factory=FootballConfig)
    gestures: GestureConfig = field(default_factory=GestureConfig)
    tracking: TrackingConfig = field(default_factory=TrackingConfig)
    players: PlayersConfig = field(default_factory=PlayersConfig)
    ui: UiConfig = field(default_factory=UiConfig)
    defaults: DefaultsConfig = field(default_factory=DefaultsConfig)
