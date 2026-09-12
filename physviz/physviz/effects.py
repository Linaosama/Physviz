"""Decorative and explanatory physics effects."""
import math
import pygame
from .entities import Body
from .fonts import text


def dashed_line(surface, start, end, color, width=1, dash=8):
    vector = pygame.Vector2(end) - start
    length = vector.length()
    if length == 0:
        return
    direction = vector.normalize()
    for offset in range(0, int(length), dash * 2):
        a = start + direction * offset
        b = start + direction * min(offset + dash, length)
        pygame.draw.line(surface, color, a, b, width)


def draw_body_effects(surface, scene):
    for body in scene.bodies:
        if body.trail and not body.dragging and body.kind in ("mg", "force"):
            points = list(body.trail)
            background = (12, 17, 28)
            trail_base = (90, 190, 130) if body.kind == "mg" else (220, 100, 75)
            for i in range(1, len(points)):
                amount = i / max(len(points) - 1, 1)
                color = tuple(int(background[channel] +
                                  (trail_base[channel] - background[channel]) * amount)
                              for channel in range(3))
                pygame.draw.line(surface, color, points[i - 1], points[i], 2)
            end = body.pos.copy()
            v = body.vel.copy()
            acceleration = body.force / body.mass
            if body.has_gravity:
                acceleration.y += 980
            points = []
            for i in range(1, 31):
                t = i * 1.5 / 30
                points.append(end + v * t + acceleration * (0.5 * t * t))
            for i in range(1, len(points)):
                dashed_line(surface, points[i - 1], points[i], (80, 120, 90), 1, 5)
        if body.kind == "orbit_center":
            for orbiter in scene.bodies:
                if orbiter.orbiting and orbiter.orbit_center is body:
                    dashed_line(surface, body.pos, orbiter.pos, (170, 145, 75), 1, 5)
                    pygame.draw.circle(surface, (90, 90, 70), body.pos, int(orbiter.orbit_radius), 1)
                    distance_m = orbiter.orbit_radius / 100
                    speed_m = abs(orbiter.orbit_omega * orbiter.orbit_radius) / 100
                    force = orbiter.mass * (speed_m ** 2) / max(distance_m, 0.01)
                    text(surface, f"r={distance_m:.2f}m", (body.pos + orbiter.pos) / 2, 13, (220, 200, 120), "center")
                    direction = pygame.Vector2(-math.sin(orbiter.orbit_angle), math.cos(orbiter.orbit_angle))
                    Body._arrow(surface, orbiter.pos, direction * 38 * orbiter.orbit_direction, (120, 220, 255))
                    text(surface, f"v={speed_m:.1f}m/s", orbiter.pos + direction * 34, 12, (130, 220, 245), "center")
                    radial = (body.pos - orbiter.pos).normalize() * 28
                    Body._arrow(surface, orbiter.pos, radial, (245, 170, 90))
                    text(surface, f"F=mv²/r={force:.1f}N", orbiter.pos + radial * 1.3, 12, (245, 180, 100), "center")
        if body.kind == "black_hole":
            for i in range(5):
                angle = scene.time * (1.2 + i * 0.17) + i * 1.3
                radius = body.radius + 10 + (i * 7 + scene.time * 22) % 38
                p = body.pos + pygame.Vector2(math.cos(angle), math.sin(angle)) * radius
                pygame.draw.circle(surface, (240, 130 + i * 15, 45), p, 2)
