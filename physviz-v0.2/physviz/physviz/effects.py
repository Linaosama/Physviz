"""Visual trails and gravitational annotations."""
import pygame
from .fonts import math_text


def dashed_line(surface, start, end, color, width=1, dash=8):
    vector = pygame.Vector2(end) - start
    if not vector.length():
        return
    direction = vector.normalize()
    for offset in range(0, int(vector.length()), dash * 2):
        pygame.draw.line(surface, color, start + direction * offset,
                         start + direction * min(offset + dash, vector.length()), width)


def draw_body_effects(surface, scene):
    for body in scene.bodies:
        if body.trail and not body.dragging:
            points = list(body.trail)
            background = (12, 17, 28)
            trail_base = (225, 175, 75) if body.kind == "star" else (210, 90, 75)
            for index in range(1, len(points)):
                amount = index / max(len(points) - 1, 1)
                color = tuple(int(background[channel] +
                                  (trail_base[channel] - background[channel]) * amount)
                              for channel in range(3))
                pygame.draw.line(surface, color, points[index - 1], points[index], 2)
        if body.kind == "black_hole":
            radius = body.radius
            pygame.draw.circle(surface, (250, 180, 75), body.pos, int(radius * 1.5), 1)
            for index in range(3):
                rect = pygame.Rect(body.pos.x - radius * (1.8 + index * 0.18),
                                   body.pos.y - radius * (0.55 + index * 0.08),
                                   radius * (3.6 + index * 0.36),
                                   radius * (1.1 + index * 0.16))
                pygame.draw.arc(surface, (220, 100 + index * 25, 45), rect,
                                scene.time + index, scene.time + 4.5 + index, 2)
        if body.kind == "star":
            for other in scene.bodies:
                if other.kind != "ball" or other.pos.distance_to(body.pos) > 600:
                    continue
                if scene._blocked(body.pos, other.pos):
                    continue
                distance_m = other.pos.distance_to(body.pos) / 100
                speed_m = other.vel.length() / 100
                force = scene.environment.G_sim * body.mass * other.mass / max(distance_m ** 2, 0.09)
                dashed_line(surface, body.pos, other.pos, (110, 100, 65), 1, 6)
                math_text(surface, "r=%.2f m" % distance_m,
                          (body.pos + other.pos) / 2, 11, (220, 200, 120), "center")
                math_text(surface, "v=%.2f m/s" % speed_m,
                          other.pos + pygame.Vector2(0, -other.radius - 12),
                          11, (160, 220, 245), "center")
                label = (r"F=\frac{mv^2}{r}=%.2f\u{ N}"
                         if other.show_orbit_force else
                         r"F=\frac{GMm}{r^2}=%.2f\u{ N}")
                math_text(surface, label % force,
                          other.pos + pygame.Vector2(0, other.radius + 12),
                          11, (245, 180, 100), "center")
