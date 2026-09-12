"""Interactive entities used by the simulation."""
from collections import deque
import pygame
from .formulas import recognize


TOKEN_LABELS = ["E", "m", "c", "²", "=", "v", "r", "g", "G", "F", "a", "p", "/", "·", "½"]
PALETTE_H = 74


class Token:
    radius = 22

    def __init__(self, label, pos=(0, 0), in_palette=False):
        self.label = label
        self.pos = pygame.Vector2(pos)
        self.in_palette = in_palette
        self.selected = False
        self.dragging = False

    def draw(self, surface, font_size=22):
        color = (45, 73, 110) if not self.in_palette else (32, 50, 75)
        pygame.draw.circle(surface, color, self.pos, self.radius)
        pygame.draw.circle(surface, (105, 170, 225), self.pos, self.radius, 2)
        if self.selected:
            pygame.draw.circle(surface, (255, 210, 100), self.pos, self.radius + 4, 2)
        from .fonts import text
        text(surface, self.label, self.pos, font_size, (240, 245, 255), "center")

    def hit(self, point):
        return self.pos.distance_to(point) <= self.radius


class Chain:
    def __init__(self, tokens=None, pos=None):
        self.tokens = list(tokens or [])
        self.pos = pygame.Vector2(pos if pos is not None else (0, 0))
        self.glow_time = 0.0
        self.recognized = recognize(self.text)
        self.dragging = False
        self.selected = False
        self._layout()

    @property
    def text(self):
        return "".join(t.label for t in self.tokens)

    @property
    def width(self):
        return max(44, len(self.tokens) * 44)

    def _layout(self):
        if not self.tokens:
            return
        start = self.pos.x - (len(self.tokens) - 1) * 22
        for i, token in enumerate(self.tokens):
            token.pos = pygame.Vector2(start + i * 44, self.pos.y)
            token.in_palette = False

    def move(self, delta):
        self.pos += delta
        for token in self.tokens:
            token.pos += delta

    def hit(self, point):
        return pygame.Rect(self.pos.x - self.width / 2, self.pos.y - 28,
                           self.width, 56).collidepoint(point)

    def draw(self, surface):
        if self.recognized and self.glow_time > 0:
            radius = self.width / 2 + 12
            pygame.draw.ellipse(surface, (250, 180, 55), (self.pos.x - radius, self.pos.y - 31,
                              radius * 2, 62), 3)
        for token in self.tokens:
            token.draw(surface)


class Body:
    COLORS = {
        "mg": (75, 175, 115), "momentum": (75, 135, 220),
        "kinetic_energy": (190, 105, 220), "force": (220, 100, 75),
        "black_hole": (20, 20, 28), "orbit_center": (235, 180, 65),
    }

    def __init__(self, kind, pos=(0, 0), mass=1.0, velocity=(0, 0), label=None):
        self.kind = kind
        self.pos = pygame.Vector2(pos)
        self.vel = pygame.Vector2(velocity)
        self.mass = float(mass)
        self.radius = 26.0
        self.label = label or {"mg": "mg", "black_hole": "E=mc²",
            "orbit_center": "G=mv²/r", "force": "F=ma",
            "momentum": "p=mv", "kinetic_energy": "E=½mv²"}.get(kind, kind)
        self.dragging = False
        self.selected = False
        self.has_gravity = kind == "mg"
        self.force = pygame.Vector2()
        self.trail = deque(maxlen=60)
        self.collision_flash = 0.0
        self.orbiting = False
        self.orbit_center = None
        self.orbit_radius = 0.0
        self.orbit_angle = 0.0
        self.orbit_omega = 0.0
        self.orbit_direction = 1.0
        self.drag_history = deque(maxlen=5)
        self.right_drag_start = None
        self.swallowed = False

    def hit(self, point):
        return self.pos.distance_to(point) <= self.radius

    def draw(self, surface, now=0.0):
        if self.kind == "black_hole":
            pygame.draw.circle(surface, (5, 5, 9), self.pos, int(self.radius))
            for i in range(3):
                radius = self.radius + 7 + i * 4
                rect = pygame.Rect(self.pos.x - radius, self.pos.y - radius, radius * 2, radius * 2)
                pygame.draw.arc(surface, (230, 130 + i * 30, 40), rect, now + i, now + 4.2 + i, 2)
        elif self.kind == "orbit_center":
            pygame.draw.circle(surface, (255, 210, 70), self.pos, int(self.radius))
            for r in (34, 43, 52):
                pygame.draw.circle(surface, (130, 105, 55), self.pos, r, 1)
        else:
            pygame.draw.circle(surface, self.COLORS.get(self.kind, (90, 140, 180)), self.pos, int(self.radius))
            pygame.draw.circle(surface, (220, 235, 255), self.pos, int(self.radius), 2)
        if self.selected:
            pygame.draw.circle(surface, (255, 220, 90), self.pos, int(self.radius + 4), 2)
        from .fonts import text
        text(surface, self.label, self.pos, 15, (245, 245, 250), "center")
        speed = self.vel.length() / 100.0
        palette_y = surface.get_height() - PALETTE_H
        labels_above = self.pos.y + self.radius + 40 > palette_y
        label_pos = self.pos.y - self.radius - 14 if labels_above else self.pos.y + self.radius + 14
        label_anchor = "midbottom" if labels_above else "midtop"
        if self.kind in ("mg", "force"):
            v = self.vel / 100.0
            vy = -v.y
            raw_resultant = self.vel * 0.22
            arrow_scale = min(1.0, 120.0 / raw_resultant.length()) if raw_resultant.length() else 1.0
            vx_delta = pygame.Vector2(self.vel.x * 0.22, 0) * arrow_scale
            vy_delta = pygame.Vector2(0, -self.vel.y * 0.22) * arrow_scale
            resultant = raw_resultant * arrow_scale
            self._arrow(surface, self.pos, vx_delta, (245, 170, 90))
            self._arrow(surface, self.pos, vy_delta, (120, 220, 255))
            self._arrow(surface, self.pos, resultant, (235, 240, 245))
            if vx_delta.length() >= 2:
                vx_label_pos = self.pos + vx_delta
                if labels_above:
                    vx_label_pos.y -= 12
                text(surface, f"vx={v.x:.1f}m/s", vx_label_pos, 12, (245, 180, 100), "midbottom")
            if vy_delta.length() >= 2:
                vy_label_pos = self.pos + vy_delta
                if labels_above:
                    vy_label_pos.y -= 12
                text(surface, f"vy={vy:.1f}m/s", vy_label_pos, 12, (130, 225, 245), "midbottom")
            text(surface, f"vx={v.x:.1f}m/s vy={vy:.1f}m/s v={speed:.1f}m/s",
                 (self.pos.x, label_pos), 13, (180, 220, 235), label_anchor)
        else:
            if speed > 0.05:
                velocity_arrow = self.vel * 0.22
                if velocity_arrow.length() > 120:
                    velocity_arrow.scale_to_length(120)
                self._arrow(surface, self.pos, velocity_arrow, (120, 220, 255))
        if self.kind == "momentum":
            text(surface, f"p={self.mass * self.vel.length() / 100:.1f} kg·m/s",
                 (self.pos.x, label_pos), 13, (220, 230, 250), label_anchor)
        elif self.kind == "kinetic_energy":
            text(surface, f"E={0.5 * self.mass * (self.vel.length() / 100) ** 2:.1f} J",
                 (self.pos.x, label_pos), 13, (230, 210, 250), label_anchor)
        if self.kind == "force" and self.force.length() > 0:
            self._arrow(surface, self.pos, self.force * 0.1, (245, 75, 65))
            text(surface, f"F={self.force.length() / 100:.1f}N a={self.force.length() / 100 / self.mass:.1f}m/s²",
                 (self.pos.x, self.pos.y - self.radius - 18), 13, (255, 150, 130), "midbottom")
        if self.kind == "black_hole":
            mass_label_y = self.pos.y - self.radius - 10 if labels_above else self.pos.y + self.radius + 10
            text(surface, f"M={self.mass:.1f}", (self.pos.x, mass_label_y), 14,
                 (255, 180, 90),
                 "midbottom" if labels_above else "midtop")

    @staticmethod
    def _arrow(surface, start, delta, color):
        if delta.length() < 2:
            return
        end = start + delta
        pygame.draw.line(surface, color, start, end, 2)
        direction = delta.normalize()
        left = end - direction.rotate(145) * 7
        right = end - direction.rotate(-145) * 7
        pygame.draw.line(surface, color, end, left, 2)
        pygame.draw.line(surface, color, end, right, 2)
