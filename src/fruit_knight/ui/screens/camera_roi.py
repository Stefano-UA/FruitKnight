"""Camera selection and play-area (ROI) calibration screen."""

from __future__ import annotations

import pygame
import pygame_gui

from fruit_knight.rendering.camera_view import fit_rect, frame_to_surface
from fruit_knight.rendering.draw_utils import alpha_rect
from fruit_knight.ui.screens.base import Screen
from fruit_knight.vision.camera import STATUS_CLOSED, STATUS_FAILED, STATUS_OPENING
from fruit_knight.vision.roi import RoiRect

PREVIEW_AREA = pygame.Rect(40, 100, 880, 540)
PANEL_X, PANEL_W = 950, 290


class CameraROIScreen(Screen):
    """Live mirrored preview where the user drags the active play area."""

    def on_enter(self, **kwargs) -> None:
        """Open the camera and build widgets.

        :param kwargs: unused.
        :type kwargs: typing.Any
        """
        self.manager.clear_and_reset()
        ui = pygame_gui.elements
        cfg = self.app.cfg
        self.drag_start: tuple[float, float] | None = None
        self.drag_now: tuple[float, float] | None = None
        self.preview_surface: pygame.Surface | None = None
        self.frame_size = (16, 9)
        self.app.ensure_camera(self.app.setup.camera_index)
        options = [str(i) for i in cfg.tracking.camera.index_options]
        current = str(self.app.setup.camera_index)
        if current not in options:
            options.append(current)
        ui.UILabel(pygame.Rect(PANEL_X, 100, PANEL_W, 30), "Camera input index", self.manager)
        self.camera_drop = ui.UIDropDownMenu(options, current, pygame.Rect(PANEL_X, 136, PANEL_W, 42), self.manager)
        self.reset_btn = ui.UIButton(pygame.Rect(PANEL_X, 330, PANEL_W, 50), "RESET TO FULL FRAME", self.manager)
        self.back = ui.UIButton(pygame.Rect(PANEL_X, 530, PANEL_W, 50), "BACK", self.manager)
        self.start = ui.UIButton(pygame.Rect(PANEL_X, 590, PANEL_W, 56), "START MATCH", self.manager, object_id="#primary_button")

    # ------------------------------------------------------------ geometry
    def video_rect(self) -> pygame.Rect:
        """Compute the letterboxed rectangle where the preview is drawn.

        :return: preview rectangle in window coordinates.
        :rtype: pygame.Rect
        """
        return fit_rect(self.frame_size, PREVIEW_AREA)

    def to_norm(self, pos: tuple[int, int]) -> tuple[float, float]:
        """Convert a window position to normalised preview coordinates.

        :param pos: mouse position in pixels.
        :type pos: tuple[int, int]
        :return: coordinates clamped to ``[0, 1]``.
        :rtype: tuple[float, float]
        """
        r = self.video_rect()
        return (min(1.0, max(0.0, (pos[0] - r.x) / r.w)), min(1.0, max(0.0, (pos[1] - r.y) / r.h)))

    # --------------------------------------------------------------- events
    def handle_event(self, event: pygame.event.Event) -> None:
        """Handle widgets and mouse dragging.

        :param event: pygame event.
        :type event: pygame.event.Event
        """
        super().handle_event(event)
        setup = self.app.setup
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and self.video_rect().collidepoint(event.pos):
            self.drag_start = self.drag_now = self.to_norm(event.pos)
        elif event.type == pygame.MOUSEMOTION and self.drag_start is not None:
            self.drag_now = self.to_norm(event.pos)
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1 and self.drag_start is not None:
            end = self.to_norm(event.pos)
            setup.roi = RoiRect.from_corners(*self.drag_start, *end)
            self.drag_start = self.drag_now = None
        elif event.type == pygame_gui.UI_DROP_DOWN_MENU_CHANGED and event.ui_element == self.camera_drop:
            setup.camera_index = int(event.text)
            setup.roi = RoiRect.full()
            self.app.ensure_camera(setup.camera_index, restart=True)
        elif event.type == pygame_gui.UI_BUTTON_PRESSED:
            if event.ui_element == self.reset_btn:
                setup.roi = RoiRect.full()
            elif event.ui_element == self.back:
                self.app.goto("setup")
            elif event.ui_element == self.start:
                self.app.start_match()

    def update(self, dt: float) -> None:
        """Refresh the preview frame.

        :param dt: time step in seconds.
        :type dt: float
        """
        super().update(dt)
        frame = self.app.pipeline.preview_frame()
        if frame is not None:
            self.frame_size = (frame.shape[1], frame.shape[0])
            self.preview_surface = frame_to_surface(frame, self.video_rect().size)

    # ----------------------------------------------------------------- draw
    def _current_roi_rect(self) -> pygame.Rect:
        """Compute the on-screen rectangle of the selected play area.

        :return: ROI rectangle in window coordinates.
        :rtype: pygame.Rect
        """
        v = self.video_rect()
        if self.drag_start is not None and self.drag_now is not None:
            # Raw rectangle while dragging; the minimum size is enforced on release.
            (x0, y0), (x1, y1) = self.drag_start, self.drag_now
            roi = RoiRect(min(x0, x1), min(y0, y1), abs(x1 - x0), abs(y1 - y0))
        else:
            roi = self.app.setup.roi
        return pygame.Rect(v.x + roi.x * v.w, v.y + roi.y * v.h, roi.w * v.w, roi.h * v.h)

    def draw(self, surface: pygame.Surface) -> None:
        """Render the preview, ROI overlay and widgets.

        :param surface: window surface.
        :type surface: pygame.Surface
        """
        self.draw_background(surface)
        fonts = self.app.fonts
        fonts.draw_centered(surface, "CAMERA & PLAY AREA", 34, (255, 171, 64), (PREVIEW_AREA.centerx, 52))
        v = self.video_rect()
        status = self.app.pipeline.camera.status
        if self.preview_surface is not None and self.app.pipeline.camera_ready:
            surface.blit(self.preview_surface, v.topleft)
            roi = self._current_roi_rect()
            for r in (
                pygame.Rect(v.x, v.y, v.w, roi.y - v.y), pygame.Rect(v.x, roi.bottom, v.w, v.bottom - roi.bottom),
                pygame.Rect(v.x, roi.y, roi.x - v.x, roi.h), pygame.Rect(roi.right, roi.y, v.right - roi.right, roi.h),
            ):
                if r.w > 0 and r.h > 0:
                    alpha_rect(surface, (0, 0, 0), 150, r)
            pygame.draw.rect(surface, (255, 171, 64), roi, 3)
            fonts.draw_centered(surface, "ACTIVE PLAY AREA", 18, (255, 171, 64), (roi.centerx, roi.y + 16))
        else:
            self.draw_card(surface, PREVIEW_AREA)
            if status == STATUS_FAILED:
                msg = ["No camera available on this index.", "You can still start: Player 1 will be controlled with the mouse", "(left button = fist, right button = open palm, none = knife)."]
            elif status == STATUS_OPENING:
                msg = ["Opening camera..."]
            elif status == STATUS_CLOSED:
                msg = ["Camera disabled (--no-camera): Player 1 will use the mouse."]
            else:
                msg = ["Waiting for camera frames..."]
            for i, line in enumerate(msg):
                fonts.draw_centered(surface, line, 24 if i == 0 else 18, (236, 239, 244), (PREVIEW_AREA.centerx, PREVIEW_AREA.centery - 30 + i * 32), bold=i == 0)
        roi = self.app.setup.roi
        info = "Full frame" if roi.is_full else f"x {roi.x:.2f}  y {roi.y:.2f}  w {roi.w:.2f}  h {roi.h:.2f}"
        for i, line in enumerate(("Drag with the mouse over", "the preview to crop the play", "area (preview is mirrored)")):
            fonts.draw_centered(surface, line, 17, (140, 150, 175), (PANEL_X + PANEL_W / 2, 206 + i * 24), bold=False, shadow=False)
        fonts.draw_centered(surface, f"ROI: {info}", 16, (236, 239, 244), (PANEL_X + PANEL_W / 2, 300), bold=False, shadow=False)
        super().draw(surface)
