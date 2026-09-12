"""Panels, palette, scene tabs, and editable properties."""
import math
import pygame
from .entities import Body
from .fonts import math_text, text, ui_font
from .physics import CANVAS_RIGHT

PALETTE_W, PALETTE_H = 420, 240
PANEL_X = 840
COLLISION_RECT = pygame.Rect(PANEL_X, 265, PALETTE_W, 120)
PROPERTY_RECT = pygame.Rect(PANEL_X, 395, PALETTE_W, 180)
ENVIRONMENT_RECT = pygame.Rect(PANEL_X, 585, PALETTE_W, 200)
PALETTE_LETTERS = ["E", "m", "c", "v", "r", "g", "G", "F", "a", "p",
                   "f", "μ", "N", "h", "t", "W", "s", "M"]
PALETTE_SYMBOLS = ["0", "=", "²", "+", "/", "·", "½"]


class TextField:
    def __init__(self, label, key, value=""):
        self.label, self.key, self.value = label, key, str(value)
        self.active = False
        self.pristine = False

    def draw(self, surface, rect, enabled=True):
        fill = (38, 48, 65) if self.active and enabled else (25, 34, 49)
        border = (245, 190, 70) if self.active and enabled else (75, 95, 120)
        if not enabled:
            fill, border = (22, 28, 39), (55, 65, 80)
        pygame.draw.rect(surface, fill, rect, border_radius=4)
        pygame.draw.rect(surface, border, rect, 2, border_radius=4)
        if self.active and self.pristine and enabled:
            selected = pygame.Rect(rect.centerx, rect.y + 3,
                                   rect.right - rect.centerx - 4, rect.height - 6)
            pygame.draw.rect(surface, (70, 92, 125), selected, border_radius=2)
        label_color = (125, 135, 150) if not enabled else (200, 215, 230)
        value_color = (115, 125, 140) if not enabled else (245, 245, 250)
        text(surface, self.label, (rect.x + 7, rect.centery), 11, label_color, "midleft")
        text(surface, self.value, (rect.right - 7, rect.centery), 12, value_color, "midright")

    def handle_key(self, event):
        if not self.active or event.type != pygame.KEYDOWN:
            return False
        if event.key == pygame.K_BACKSPACE:
            self.value = "" if self.pristine else self.value[:-1]
            self.pristine = False
        elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
            return "apply"
        elif event.key == pygame.K_ESCAPE:
            return "cancel"
        elif event.unicode and event.unicode in "0123456789.-":
            self.value = event.unicode if self.pristine else self.value + event.unicode
            self.pristine = False
        return True


def _panel(surface, rect, title):
    pygame.draw.rect(surface, (20, 29, 44), rect, border_radius=8)
    pygame.draw.rect(surface, (75, 95, 120), rect, 1, border_radius=8)
    text(surface, title, (rect.x + 14, rect.y + 10), 16, (240, 215, 140))


class PropertyPanel:
    def __init__(self):
        self.body = None
        self.fields = []
        self.delete_requested = False

    def _specs(self, body):
        if body.kind == "ball":
            return [("质量 m (kg)", "mass"), ("速度 v (m/s)", "speed"),
                    ("方向 θ (°)", "angle"), ("力 F (N)", "force"),
                    ("力方向 (°)", "force_angle")]
        if body.kind in ("star", "black_hole"):
            return [("质量 m (kg)", "mass"), ("速度 v (m/s)", "speed"),
                    ("方向 θ (°)", "angle")]
        if body.kind == "table":
            return [("宽度 (px)", "width"), ("高度 (px)", "height"),
                    ("摩擦 μ", "mu"), ("反弹 e", "restitution")]
        if body.kind == "barrier":
            return [("长度 (px)", "length"), ("方向 (°)", "orientation")]
        return []

    def set_body(self, body):
        if not isinstance(body, Body):
            body = None
        if body is self.body:
            return
        self.body = body
        self.fields = [TextField(label, key) for label, key in self._specs(body)] if body else []
        self._sync_values()

    def _values(self):
        body = self.body
        speed = body.vel.length() / 100
        angle = math.degrees(math.atan2(-body.vel.y, body.vel.x)) % 360
        return {
            "mass": body.mass, "speed": speed, "angle": angle,
            "force": body.force.length() / 100,
            "force_angle": math.degrees(math.atan2(-body.force.y, body.force.x)) % 360,
            "width": body.width, "height": body.height, "mu": body.table_mu,
            "restitution": body.table_restitution, "length": body.length,
            "orientation": body.orientation,
        }

    def _sync_values(self):
        if not self.body:
            return
        values = self._values()
        for field in self.fields:
            field.value = "%.2f" % values[field.key]
            field.active = False
            field.pristine = False

    def _rects(self, panel):
        return [pygame.Rect(panel.x + 12 + (index % 2) * 195,
                            panel.y + 38 + (index // 2) * 29, 180, 24)
                for index in range(len(self.fields))]

    def handle_event(self, event, body):
        self.set_body(body)
        self.delete_requested = False
        if not self.body:
            return False
        panel = PROPERTY_RECT
        rects = self._rects(panel)
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for field, rect in zip(self.fields, rects):
                if rect.collidepoint(event.pos):
                    for other in self.fields:
                        other.active = other is field
                    field.pristine = True
                    return True
            for field in self.fields:
                field.active = False
            apply_rect = pygame.Rect(panel.x + 12, panel.bottom - 32, 75, 25)
            still_rect = pygame.Rect(panel.x + 95, panel.bottom - 32, 75, 25)
            delete_rect = pygame.Rect(panel.right - 95, panel.bottom - 32, 82, 25)
            if apply_rect.collidepoint(event.pos):
                self.apply()
                return True
            if still_rect.collidepoint(event.pos) and self.body.kind == "ball":
                self.body.vel.update(0, 0)
                self._sync_values()
                return True
            if delete_rect.collidepoint(event.pos):
                self.delete_requested = True
                return True
        if event.type == pygame.KEYDOWN:
            for field in self.fields:
                result = field.handle_key(event)
                if result == "apply":
                    self.apply()
                    return True
                if result == "cancel":
                    self._sync_values()
                    return True
                if result:
                    return True
        return False

    def apply(self):
        if not self.body:
            return
        try:
            values = {field.key: float(field.value) for field in self.fields}
        except ValueError:
            return
        body = self.body
        if body.kind in ("ball", "star", "black_hole"):
            body.mass = max(0.01, values["mass"])
            speed = values["speed"] * 100
            angle = math.radians(values["angle"])
            body.vel = pygame.Vector2(speed * math.cos(angle), -speed * math.sin(angle))
            if body.kind == "black_hole":
                body.radius = max(18.0, 0.006 * body.mass)
            if body.kind == "ball" and body.can_force and "force" in values:
                force = values["force"] * 100
                force_angle = math.radians(values["force_angle"])
                body.force = pygame.Vector2(force * math.cos(force_angle),
                                            -force * math.sin(force_angle))
        elif body.kind == "table":
            body.width, body.height = max(20, values["width"]), max(8, values["height"])
            body.table_mu = max(0, values["mu"])
            body.table_restitution = max(0, min(1, values["restitution"]))
        elif body.kind == "barrier":
            body.length = max(20, values["length"])
            body.orientation = values["orientation"] % 180
        self._sync_values()

    def draw(self, surface, body):
        self.set_body(body)
        if not self.body:
            return
        _panel(surface, PROPERTY_RECT, "属性")
        force_enabled = self.body.kind == "ball" and self.body.can_force
        for field, rect in zip(self.fields, self._rects(PROPERTY_RECT)):
            field.draw(surface, rect, force_enabled or field.key not in ("force", "force_angle"))
        if self.body.kind == "ball" and not force_enabled:
            text(surface, "应用力字段在 F=ma 后启用",
                 (PROPERTY_RECT.x + 14, PROPERTY_RECT.bottom - 57), 11, (145, 165, 190))
        for rect, label, color in [
            (pygame.Rect(PROPERTY_RECT.x + 12, PROPERTY_RECT.bottom - 32, 75, 25), "应用", (55, 100, 80)),
            (pygame.Rect(PROPERTY_RECT.x + 95, PROPERTY_RECT.bottom - 32, 75, 25), "静止", (80, 75, 55)),
            (pygame.Rect(PROPERTY_RECT.right - 95, PROPERTY_RECT.bottom - 32, 82, 25), "删除", (110, 55, 55)),
        ]:
            pygame.draw.rect(surface, color, rect, border_radius=5)
            text(surface, label, rect.center, 12, (245, 245, 245), "center")


class EnvironmentPanel:
    def __init__(self):
        self.fields = [TextField("g (m/s²)", "g"), TextField("空气 k", "air_k"),
                       TextField("地面 μ", "ground_mu"), TextField("反弹 e", "restitution"),
                       TextField("G_sim", "G_sim")]

    def sync(self, environment):
        values = vars(environment)
        for field in self.fields:
            field.value = "%.3f" % values[field.key]
            field.active = False
            field.pristine = False

    def handle_event(self, event, environment):
        rects = [pygame.Rect(ENVIRONMENT_RECT.x + 12 + (i % 2) * 195,
                             ENVIRONMENT_RECT.y + 35 + (i // 2) * 28, 180, 23)
                 for i in range(len(self.fields))]
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for field, rect in zip(self.fields, rects):
                if rect.collidepoint(event.pos):
                    for other in self.fields:
                        other.active = other is field
                    field.pristine = True
                    return True
            for field in self.fields:
                field.active = False
            toggle = pygame.Rect(ENVIRONMENT_RECT.x + 12, ENVIRONMENT_RECT.bottom - 31, 150, 24)
            if toggle.collidepoint(event.pos):
                environment.global_gravity = not environment.global_gravity
                return True
        if event.type == pygame.KEYDOWN:
            for field in self.fields:
                result = field.handle_key(event)
                if result == "apply":
                    self.apply(environment)
                    return True
                if result == "cancel":
                    self.sync(environment)
                    return True
                if result:
                    return True
        return False

    def apply(self, environment):
        try:
            values = {field.key: float(field.value) for field in self.fields}
        except ValueError:
            return
        for key, value in values.items():
            setattr(environment, key, max(0, value))
        self.sync(environment)

    def draw(self, surface, environment):
        _panel(surface, ENVIRONMENT_RECT, "环境")
        rects = [pygame.Rect(ENVIRONMENT_RECT.x + 12 + (i % 2) * 195,
                             ENVIRONMENT_RECT.y + 35 + (i // 2) * 28, 180, 23)
                 for i in range(len(self.fields))]
        for field, rect in zip(self.fields, rects):
            field.draw(surface, rect)
        toggle = pygame.Rect(ENVIRONMENT_RECT.x + 12, ENVIRONMENT_RECT.bottom - 31, 150, 24)
        pygame.draw.rect(surface, (55, 100, 80) if environment.global_gravity else (55, 65, 85),
                         toggle, border_radius=5)
        text(surface, "全局重力: 开" if environment.global_gravity else "全局重力: 关",
             toggle.center, 11, (245, 245, 245), "center")


def palette_layout(width):
    panel = pygame.Rect(width - PALETTE_W - 20, 14, PALETTE_W, PALETTE_H)
    rects = []
    cell_w = 36
    for index, label in enumerate(PALETTE_LETTERS):
        row, column = divmod(index, 10)
        rects.append((label, pygame.Rect(panel.x + 12 + column * 40,
                                         panel.y + 45 + row * 28, cell_w, 24), "token"))
    symbols_y = panel.y + 115
    for index, label in enumerate(PALETTE_SYMBOLS):
        rects.append((label, pygame.Rect(panel.x + 12 + index * 40,
                                         symbols_y, cell_w, 24), "token"))
    button_y = panel.y + 164
    for index, label in enumerate(("小球", "桌子", "隔板", "双星", "三星")):
        rects.append((label, pygame.Rect(panel.x + 12 + index * 78, button_y, 70, 28), label))
    return panel, rects


def palette_hit(width, point):
    _, rects = palette_layout(width)
    for label, rect, action in rects:
        if rect.collidepoint(point):
            return label, action
    return None


def tabs_layout(width, count):
    rects = []
    for index in range(count):
        rects.append((index, pygame.Rect(18 + index * 78, 95, 72, 25)))
    rects.append(("add", pygame.Rect(18 + count * 78, 95, 30, 25)))
    return rects


def tabs_hit(width, count, point):
    for index, rect in tabs_layout(width, count):
        if rect.collidepoint(point):
            return index
    return None


def draw_ui(surface, scene, selected=None, property_panel=None, paused=False, fps=60,
            mouse_pos=(0, 0), scenes=None, active_index=0, environment_panel=None):
    width, height = surface.get_size()
    surface.fill((12, 17, 28))
    text(surface, "PhysViz · 物理公式实验台", (18, 14), 22, (220, 235, 250))
    text(surface, "左键拖动 · 右键删除 token/chip · 空格暂停 · R 重置 · Delete 删除",
         (18, 44), 14, (160, 180, 205))
    text(surface, "小球 + 公式 chip = 物理实验", (18, 68), 14, (175, 195, 215))
    text(surface, "FPS %.0f%s" % (fps, " · 已暂停" if paused else ""),
         (width - 18, 18), 15, (180, 205, 225), "topright")
    if scenes is not None:
        for index, rect in tabs_layout(width, len(scenes)):
            if index == "add":
                text(surface, "+", rect.center, 18, (230, 230, 230), "center")
            else:
                fill = (65, 82, 105) if index == active_index else (28, 40, 58)
                pygame.draw.rect(surface, fill, rect, border_radius=5)
                text(surface, "模拟%d" % (index + 1), rect.center, 12, (235, 240, 250), "center")
                if len(scenes) > 1:
                    text(surface, "×", (rect.right - 8, rect.y + 4), 11, (240, 150, 150), "topright")
    panel, rects = palette_layout(width)
    _panel(surface, panel, "素材与公式")
    text(surface, "字母", (panel.x + 12, panel.y + 30), 10, (150, 175, 200))
    text(surface, "数字/符号", (panel.x + 12, panel.y + 100), 10, (150, 175, 200))
    text(surface, "物体", (panel.x + 12, panel.y + 147), 10, (150, 175, 200))
    for label, rect, action in rects:
        hover = rect.collidepoint(mouse_pos)
        is_button = action != "token"
        fill = (65, 82, 105) if hover else ((60, 75, 94) if is_button else (32, 45, 65))
        pygame.draw.rect(surface, fill, rect, border_radius=6)
        pygame.draw.rect(surface, (180, 155, 80) if is_button else (75, 105, 140), rect, 1, border_radius=6)
        (text if is_button else math_text)(surface, label, rect.center, 14 if is_button else 17,
                                           (245, 245, 235), "center")
    _panel(surface, COLLISION_RECT, "碰撞")
    if scene.reports:
        report = scene.reports[0]
        lines = [
            "m_1=%.1f kg, m_2=%.1f kg" % (report.m1, report.m2),
            "v_1: %.2f → %.2f \\u{m/s}" %
            (report.v1.length() / 100, report.v1_after.length() / 100),
            "v_2: %.2f → %.2f \\u{m/s}" %
            (report.v2.length() / 100, report.v2_after.length() / 100),
            "Σp = %.2f → %.2f \\u{kg·m/s}" %
            (report.momentum_before, report.momentum_after),
            "E_k = %.2f → %.2f \\u{J}" %
            (report.kinetic_before, report.kinetic_after),
        ]
        for index, line in enumerate(lines):
            math_text(surface, line, (COLLISION_RECT.x + 14, COLLISION_RECT.y + 35 + index * 19),
                      11, (250, 210, 100) if index > 2 else (200, 215, 230))
    else:
        text(surface, "暂无碰撞（报告保留 4 秒）",
             (COLLISION_RECT.x + 14, COLLISION_RECT.y + 42), 13, (135, 155, 180))
    if property_panel:
        property_panel.draw(surface, selected)
    if environment_panel:
        environment_panel.draw(surface, scene.environment)
    legend = "图例：青色速度 · 橙色 vx · 蓝色 vy · 红色外力"
    legend_width = max(285, ui_font(13).size(legend)[0] + 24)
    pygame.draw.rect(surface, (20, 29, 44), (18, 125, legend_width, 48), border_radius=7)
    text(surface, legend, (30, 138), 13, (180, 205, 225))
    pygame.draw.line(surface, (45, 58, 78), (CANVAS_RIGHT, 0), (CANVAS_RIGHT, height), 1)
