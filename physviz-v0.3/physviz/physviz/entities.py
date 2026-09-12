"""Tokens, formula chips, and plain physics balls."""
from collections import deque
import pygame
from .formulas import recognize
from .fonts import math_text


TOKEN_LABELS = [
    "E", "m", "c", "v", "r", "g", "G", "F", "a", "p", "f", "μ", "N", "h", "t",
    "0", "+", "W", "s", "M", "=", "²", "/", "·", "½",
]
PALETTE_H = 74


class Token:
    radius = 22

    def __init__(self, label, pos=(0, 0), in_palette=False):
        self.label = label
        self.pos = pygame.Vector2(pos)
        self.in_palette = in_palette
        self.selected = False
        self.dragging = False

    def hit(self, point):
        return self.pos.distance_to(point) <= self.radius

    def draw(self, surface, radius=None, pos=None):
        radius = self.radius if radius is None else radius
        pos = self.pos if pos is None else pos
        color = (45, 73, 110) if not self.in_palette else (32, 50, 75)
        pygame.draw.circle(surface, color, pos, radius)
        pygame.draw.circle(surface, (105, 170, 225), pos, radius, 2)
        if self.selected:
            pygame.draw.circle(surface, (255, 210, 100), pos, radius + 4, 2)
        math_text(surface, self.label, pos, 22 if radius > 18 else 17,
                  (240, 245, 255), "center")


def chain_to_markup(tokens):
    labels = [token.label if hasattr(token, "label") else str(token) for token in tokens]
    def join(group):
        return "".join(r"\frac{1}{2}" if label == "½" else "^2" if label == "²" else label
                       for label in group)

    output = []
    group = []
    for label in labels + ["="]:
        if label in ("=", "+"):
            if "/" in group:
                slash = group.index("/")
                output.append(r"\frac{%s}{%s}" % (join(group[:slash]), join(group[slash + 1:])))
            else:
                output.append(join(group))
            output.append(label)
            group = []
        else:
            group.append(label)
    return "".join(output[:-1])


class Chain:
    def __init__(self, tokens=None, pos=None):
        self.tokens = list(tokens or [])
        self.pos = pygame.Vector2(pos if pos is not None else (0, 0))
        self.glow_time = 0.0
        self.recognized = recognize(self.text)
        self.dragging = False
        self.selected = False
        self._visuals = {}
        self._fraction_bars = []
        self._bounds = pygame.Rect(0, 0, 44, 56)
        self._layout()

    @property
    def text(self):
        return "".join(token.label for token in self.tokens)

    @property
    def width(self):
        return self._bounds.width

    @property
    def is_chip(self):
        return bool(self.recognized and self.glow_time >= 0.6)

    def _layout(self):
        self._visuals = {}
        self._fraction_bars = []
        if not self.tokens:
            return
        groups = []
        current = []
        for token in self.tokens:
            if token.label in ("=", "+"):
                if current:
                    groups.append(current)
                    current = []
                groups.append([token])
            else:
                current.append(token)
        if current:
            groups.append(current)
        widths = []
        for group in groups:
            slash = next((index for index, token in enumerate(group) if token.label == "/"), None)
            if slash is None or not group[:slash] or not group[slash + 1:]:
                widths.append(max(44, len(group) * 44))
            else:
                numerator = group[:slash]
                denominator = group[slash + 1:]
                widths.append(max(40, len(numerator) * 36, len(denominator) * 36))
        total = sum(widths) + max(0, len(widths) - 1) * 4
        cursor = self.pos.x - total / 2
        for group, group_width in zip(groups, widths):
            slash = next((index for index, token in enumerate(group) if token.label == "/"), None)
            if slash is None or not group[:slash] or not group[slash + 1:]:
                start = cursor + group_width / 2 - (len(group) - 1) * 22
                for index, token in enumerate(group):
                    radius = 16 if token.label in ("²", "½") else 22
                    y = self.pos.y - 10 if radius == 16 else self.pos.y
                    self._visuals[token] = (pygame.Vector2(start + index * 44, y), radius)
            else:
                numerator = group[:slash]
                denominator = group[slash + 1:]
                for row, row_tokens, y in (
                        (0, numerator, self.pos.y - 18),
                        (1, denominator, self.pos.y + 18)):
                    start = cursor + group_width / 2 - (len(row_tokens) - 1) * 18
                    for index, token in enumerate(row_tokens):
                        self._visuals[token] = (pygame.Vector2(start + index * 36, y), 16)
                self._visuals[group[slash]] = (pygame.Vector2(
                    cursor + group_width / 2, self.pos.y), 0)
                self._fraction_bars.append((cursor, cursor + group_width, self.pos.y))
            cursor += group_width + 4
        for token in self.tokens:
            token.in_palette = False
            if token in self._visuals:
                token.pos = self._visuals[token][0]
        left = min(pos.x - radius for pos, radius in self._visuals.values() if radius)
        right = max(pos.x + radius for pos, radius in self._visuals.values() if radius)
        top = min(pos.y - radius for pos, radius in self._visuals.values() if radius)
        bottom = max(pos.y + radius for pos, radius in self._visuals.values() if radius)
        self._bounds = pygame.Rect(left, top, max(1, right - left), max(1, bottom - top))

    def move(self, delta):
        self.pos += delta
        for token in self.tokens:
            token.pos += delta

    def hit(self, point):
        return self._bounds.collidepoint(point)

    def rect(self):
        return self._bounds.copy()

    def draw(self, surface):
        if self.is_chip:
            rect = pygame.Rect(self.pos.x - self.width / 2, self.pos.y - 25, self.width, 50)
            pygame.draw.rect(surface, (72, 57, 30), rect, border_radius=18)
            pygame.draw.rect(surface, (245, 190, 65), rect, 2, border_radius=18)
            math_text(surface, chain_to_markup(self.tokens), self.pos, 19,
                      (255, 235, 160), "center")
        else:
            if self.recognized and self.glow_time > 0:
                radius = max(self._bounds.width, self._bounds.height) / 2 + 12
                pygame.draw.ellipse(surface, (250, 180, 55),
                                    (self.pos.x - radius, self.pos.y - 31, radius * 2, 62), 3)
            for token in self.tokens:
                position, radius = self._visuals.get(token, (token.pos, token.radius))
                if radius:
                    token.draw(surface, radius, position)
            for left, right, y in self._fraction_bars:
                pygame.draw.line(surface, (225, 220, 190), (left + 3, y),
                                 (right - 3, y), 2)


class Body:
    COLORS = {
        "ball": (205, 215, 225), "black_hole": (20, 20, 28),
        "star": (235, 180, 65), "table": (125, 78, 42), "barrier": (180, 190, 200),
    }

    def __init__(self, kind="ball", pos=(0, 0), mass=None, velocity=(0, 0)):
        self.kind = kind
        self.pos = pygame.Vector2(pos)
        self.vel = pygame.Vector2(velocity)
        defaults = {"ball": 1.0, "star": 1000.0, "black_hole": 5000.0}
        self.mass = float(defaults.get(kind, 1.0) if mass is None else mass)
        self.radius = 22.0 if kind == "star" else max(18.0, 0.006 * self.mass) \
            if kind == "black_hole" else 26.0
        self.attracts = kind in ("star", "black_hole")
        self.has_gravity = False
        self.can_force = False
        self.show_momentum = False
        self.show_energy = False
        self.show_friction = False
        self.show_potential = False
        self.show_velocity_time = False
        self.show_gravity_force = False
        self.show_orbit_force = False
        self.show_work = False
        self.force = pygame.Vector2()
        self.selected = False
        self.dragging = False
        self.trail = deque(maxlen=240 if kind == "star" else 60)
        self.on_surface = None
        self.release_speed = 0.0
        self.width = 300.0 if kind == "table" else 8.0 if kind == "barrier" else 0.0
        self.height = 20.0 if kind == "table" else 8.0 if kind == "barrier" else 0.0
        self.table_mu = 0.3 if kind == "table" else 0.0
        self.table_restitution = 0.5 if kind == "table" else 0.0
        self.length = 240.0 if kind == "barrier" else 0.0
        self.orientation = 0.0
        self.swallowed = False

    def hit(self, point):
        if self.kind == "table":
            return pygame.Rect(self.pos.x - self.width / 2, self.pos.y - self.height / 2,
                               self.width, self.height).collidepoint(point)
        if self.kind == "barrier":
            rect = self.barrier_rect()
            return rect.collidepoint(point)
        return self.pos.distance_to(point) <= self.radius

    def barrier_endpoints(self):
        direction = pygame.Vector2(1, 0).rotate(self.orientation)
        half = direction * self.length / 2
        return self.pos - half, self.pos + half

    def barrier_rect(self):
        start, end = self.barrier_endpoints()
        if abs(self.orientation % 180) < 45:
            return pygame.Rect(self.pos.x - self.length / 2, self.pos.y - self.height / 2,
                               self.length, self.height)
        return pygame.Rect(self.pos.x - self.height / 2, self.pos.y - self.length / 2,
                           self.height, self.length)

    def tag_text(self):
        tags = []
        if self.has_gravity:
            tags.append("mg")
        if self.can_force:
            tags.append("F=ma")
        if self.show_friction:
            tags.append("f=μN")
        return " · ".join(tags)

    def draw(self, surface, now=0.0, gravity=9.8):
        if self.kind == "black_hole":
            pygame.draw.circle(surface, (5, 5, 9), self.pos, int(self.radius))
            for i in range(3):
                radius = self.radius + 7 + i * 4
                rect = pygame.Rect(self.pos.x - radius, self.pos.y - radius, radius * 2, radius * 2)
                pygame.draw.arc(surface, (230, 130 + i * 30, 40), rect, now + i, now + 4.2 + i, 2)
        elif self.kind == "star":
            pygame.draw.circle(surface, (255, 210, 70), self.pos, int(self.radius))
            for radius in (34, 43, 52):
                pygame.draw.circle(surface, (130, 105, 55), self.pos, radius, 1)
        elif self.kind == "table":
            rect = pygame.Rect(self.pos.x - self.width / 2, self.pos.y - self.height / 2,
                               self.width, self.height)
            pygame.draw.rect(surface, self.COLORS["table"], rect, border_radius=5)
            pygame.draw.line(surface, self.COLORS["table"], (rect.x + 30, rect.bottom),
                             (rect.x + 20, rect.bottom + 60), 4)
            pygame.draw.line(surface, self.COLORS["table"], (rect.right - 30, rect.bottom),
                             (rect.right - 20, rect.bottom + 60), 4)
        elif self.kind == "barrier":
            rect = self.barrier_rect()
            pygame.draw.rect(surface, self.COLORS["barrier"], rect)
            start, end = self.barrier_endpoints()
            direction = (end - start).normalize()
            for offset in range(0, int(self.length), 18):
                point = start + direction * offset
                pygame.draw.line(surface, (120, 130, 140), point - direction * 3,
                                 point + direction * 3, 2)
        else:
            pygame.draw.circle(surface, self.COLORS["ball"], self.pos, int(self.radius))
            pygame.draw.circle(surface, (245, 250, 255), self.pos, int(self.radius), 2)
            if self.has_gravity:
                pygame.draw.circle(surface, (75, 210, 125), self.pos, int(self.radius + 4), 2)
            if self.can_force:
                pygame.draw.circle(surface, (230, 80, 70), self.pos, int(self.radius + 7), 2)
        if self.selected:
            pygame.draw.circle(surface, (255, 220, 90), self.pos, int(self.radius + 10), 2)
        if self.kind == "ball":
            palette_y = surface.get_height() - PALETTE_H
            labels_above = self.pos.y + self.radius + 56 > palette_y
            speed = self.vel.length() / 100
            has_velocity_visuals = (self.has_gravity or self.force.length() > 0) and speed >= 0.1
            label_lines = [("m=%.1f kg" % self.mass, 14, (185, 200, 215))]
            if has_velocity_visuals:
                label_lines.append(("v=%.1f m/s" % speed, 16, (240, 245, 250)))
            status = []
            if self.show_momentum:
                status.append("p=%.2f kg·m/s" % (self.mass * speed))
            if self.show_energy:
                status.append("E_k=%.2f J" % (0.5 * self.mass * speed ** 2))
            if status:
                label_lines.append((" · ".join(status), 12, (215, 225, 245)))
            label_anchor = "midbottom" if labels_above else "midtop"
            first_y = self.pos.y - self.radius - 12 if labels_above else self.pos.y + self.radius + 13
            direction = -16 if labels_above else 16
            for index, (label, size, color) in enumerate(label_lines):
                math_text(surface, label, (self.pos.x, first_y + index * direction),
                          size, color, label_anchor)
            if self.tag_text():
                math_text(surface, self.tag_text(), (self.pos.x, self.pos.y - self.radius - 8),
                          12, (220, 220, 180), "midbottom")
        elif self.kind == "black_hole":
            math_text(surface, "M=%.1f kg" % self.mass,
                      (self.pos.x, self.pos.y + self.radius + 10), 14, (255, 180, 90), "midtop")
            math_text(surface, "r_h=%.2f m" % (self.radius / 100),
                      (self.pos.x, self.pos.y + self.radius + 27), 11, (240, 190, 120), "midtop")
        if self.kind == "ball" and has_velocity_visuals:
            self._draw_velocity(surface)
        elif self.kind == "ball" and self.vel.length() >= 10:
            self._arrow(surface, self.pos, self._clamped(self.vel * 0.22), (120, 220, 255))
        if self.can_force and self.force.length() > 0:
            self._arrow(surface, self.pos, self._clamped(self.force * 0.1), (245, 75, 65))
            math_text(surface, "F=%.1f N" % (self.force.length() / 100),
                      self.pos + self._clamped(self.force * 0.1), 12, (255, 150, 130), "midbottom")
        if self.show_friction and self.on_surface is not None:
            mu = 0.0 if self.on_surface == "floor" else self.on_surface.table_mu
            normal = self.mass * gravity
            math_text(surface, "f=μN=%.2f N" % (mu * normal),
                      (self.pos.x, self.pos.y - self.radius - 8), 11,
                      (180, 220, 180), "midbottom")

    def _draw_velocity(self, surface):
        raw = self.vel * 0.22
        scale = min(1.0, 120 / raw.length()) if raw.length() else 1.0
        vx = pygame.Vector2(self.vel.x * 0.22, 0) * scale
        vy = pygame.Vector2(0, -self.vel.y * 0.22) * scale
        result = raw * scale
        self._arrow(surface, self.pos, vx, (245, 170, 90))
        self._arrow(surface, self.pos, vy, (120, 220, 255))
        self._arrow(surface, self.pos, result, (235, 240, 245))
        if vx.length() >= 2:
            vx_tip = self.pos + vx
            vx_offset = pygame.Vector2(7 if vx.x >= 0 else -7, -4)
            math_text(surface, "v_x=%.1f" % (self.vel.x / 100),
                      vx_tip + vx_offset, 13, (245, 180, 100),
                      "midleft" if vx.x >= 0 else "midright")
        if vy.length() >= 2:
            vy_tip = self.pos + vy
            vy_offset = pygame.Vector2(0, -7 if vy.y < 0 else 7)
            math_text(surface, "v_y=%.1f" % (-self.vel.y / 100),
                      vy_tip + vy_offset, 13, (130, 225, 245),
                      "midbottom" if vy.y < 0 else "midtop")

    @staticmethod
    def _clamped(delta):
        if delta.length() > 120:
            delta.scale_to_length(120)
        return delta

    @staticmethod
    def _arrow(surface, start, delta, color):
        if delta.length() < 2:
            return
        end = start + delta
        direction = delta.normalize()
        pygame.draw.line(surface, color, start, end, 2)
        pygame.draw.line(surface, color, end, end - direction.rotate(145) * 7, 2)
        pygame.draw.line(surface, color, end, end - direction.rotate(-145) * 7, 2)
