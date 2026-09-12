"""Fixed-step simulation and interaction model."""
from dataclasses import dataclass
import math
import pygame
from .entities import Body, Chain, Token, PALETTE_H
from .formulas import recognize

G = 980.0
WORLD_W, WORLD_H = 1280, 800


@dataclass
class CollisionReport:
    m1: float
    v1: pygame.Vector2
    v1_after: pygame.Vector2
    m2: float
    v2: pygame.Vector2
    v2_after: pygame.Vector2
    momentum_before: float
    momentum_after: float
    kinetic_before: float
    kinetic_after: float
    age: float = 0.0


class Scene:
    def __init__(self, width=WORLD_W, height=WORLD_H):
        self.width, self.height = width, height
        self.palette_y = height - PALETTE_H
        self.tokens = []
        self.chains = []
        self.bodies = []
        self.reports = []
        self.selected = None
        self.time = 0.0
        self._orbit_distances = {}

    def reset(self):
        self.tokens.clear()
        self.chains.clear()
        self.bodies.clear()
        self.reports.clear()
        self.selected = None
        self.time = 0.0
        self._orbit_distances.clear()

    def spawn_token(self, label, pos):
        token = Token(label, pos)
        self.tokens.append(token)
        return token

    def spawn_chain(self, labels, pos=(400, 260)):
        tokens = [Token(label, pos) for label in labels]
        chain = Chain(tokens, pos)
        self.chains.append(chain)
        return chain

    def spawn_body(self, kind, pos=(400, 300), velocity=(0, 0), mass=1.0):
        body = Body(kind, pos, mass, velocity)
        self.bodies.append(body)
        return body

    def add_palette_token(self, label, point):
        if point[1] < self.palette_y:
            return None
        return self.spawn_token(label, point)

    def _collapse_chains(self, dt):
        for chain in list(self.chains):
            chain.glow_time += dt
            if chain.recognized and chain.glow_time >= 0.6:
                self.spawn_body(chain.recognized.kind, chain.pos)
                self.chains.remove(chain)
                for token in chain.tokens:
                    if token in self.tokens:
                        self.tokens.remove(token)

    def _merge_token(self, token):
        nearby = []
        for chain in self.chains:
            if abs(token.pos.y - chain.pos.y) < 48 and abs(token.pos.x - chain.pos.x) <= chain.width / 2 + 50:
                nearby.append(chain)
        if nearby:
            chain = min(nearby, key=lambda c: abs(c.pos.x - token.pos.x))
            insert_left = token.pos.x < chain.pos.x
            if insert_left:
                chain.tokens.insert(0, token)
            else:
                chain.tokens.append(token)
            if token in self.tokens:
                self.tokens.remove(token)
            chain.pos = pygame.Vector2(sum(t.pos.x for t in chain.tokens) / len(chain.tokens), token.pos.y)
            chain._layout()
            chain.recognized = recognize(chain.text)
            chain.glow_time = 0
            return chain
        others = [t for t in self.tokens if t is not token and not t.in_palette
                   and abs(token.pos.y - t.pos.y) < 48 and token.pos.distance_to(t.pos) <= 50]
        if others:
            other = min(others, key=lambda t: token.pos.distance_to(t.pos))
            tokens = [token, other] if token.pos.x < other.pos.x else [other, token]
            self.tokens.remove(token)
            self.tokens.remove(other)
            chain = Chain(tokens, ((token.pos.x + other.pos.x) / 2, token.pos.y))
            self.chains.append(chain)
            return chain
        return None

    def release_token(self, token):
        token.dragging = False
        self._merge_token(token)

    def capture_orbit(self, body, capture_on_step=False):
        if body.orbiting or body.dragging or body.kind in ("black_hole", "orbit_center"):
            return
        for center in self.bodies:
            if center.kind != "orbit_center" or center is body:
                continue
            delta = body.pos - center.pos
            distance = delta.length()
            if capture_on_step and self._orbit_distances.get((id(body), id(center)), float("inf")) <= 300:
                continue
            if capture_on_step and body.vel.length() >= 400:
                continue
            if distance <= 300 and distance > center.radius + body.radius:
                speed = max(body.vel.length(), 150.0)
                tangent = pygame.Vector2(-delta.y, delta.x)
                sign = 1.0 if tangent.dot(body.vel) >= 0 else -1.0
                body.orbiting = True
                body.orbit_center = center
                body.orbit_radius = distance
                body.orbit_angle = math.atan2(delta.y, delta.x)
                body.orbit_direction = sign
                body.orbit_omega = sign * speed / distance
                body.vel = tangent.normalize() * speed * sign
                return

    def _update_orbit(self, body, dt):
        center = body.orbit_center
        if not center or center not in self.bodies:
            body.orbiting = False
            return
        body.orbit_angle += body.orbit_omega * dt
        body.pos = center.pos + pygame.Vector2(math.cos(body.orbit_angle), math.sin(body.orbit_angle)) * body.orbit_radius
        tangent = pygame.Vector2(-math.sin(body.orbit_angle), math.cos(body.orbit_angle))
        body.vel = tangent * (body.orbit_omega * body.orbit_radius)

    def step(self, dt=1 / 120):
        self.time += dt
        self._collapse_chains(dt)
        for report in self.reports:
            report.age += dt
        self.reports[:] = [r for r in self.reports if r.age < 4.0]
        for body in self.bodies:
            if body.kind == "orbit_center":
                continue
            if body.dragging:
                continue
            if body.orbiting:
                self._update_orbit(body, dt)
                continue
            acceleration = pygame.Vector2()
            if body.has_gravity:
                acceleration.y += G
            if body.kind == "force":
                acceleration += body.force / body.mass
            for black_hole in self.bodies:
                if black_hole.kind != "black_hole" or black_hole is body:
                    continue
                delta = black_hole.pos - body.pos
                dist_sq = max(delta.length_squared(), 1000.0)
                if delta.length() > 0:
                    acceleration += delta.normalize() * min(1800.0, 180000.0 * black_hole.mass / dist_sq)
            body.vel += acceleration * dt
            body.pos += body.vel * dt
            if body.vel.length() > 5:
                body.trail.append(body.pos.copy())
            self._walls(body)
            self.capture_orbit(body, capture_on_step=True)
        self._token_gravity()
        self._swallow()
        self._collisions()
        self._orbit_distances = {
            (id(body), id(center)): body.pos.distance_to(center.pos)
            for body in self.bodies
            if body.kind not in ("black_hole", "orbit_center")
            for center in self.bodies
            if center.kind == "orbit_center" and center is not body
        }

    def _token_gravity(self):
        holes = [body for body in self.bodies if body.kind == "black_hole"]
        if not holes:
            return
        for token in list(self.tokens):
            if token.dragging or token.in_palette:
                continue
            acceleration = pygame.Vector2()
            for hole in holes:
                delta = hole.pos - token.pos
                if delta.length() > 0:
                    acceleration += delta.normalize() * min(1800.0, 180000.0 * hole.mass /
                                                           max(delta.length_squared(), 1000.0))
                if delta.length() < hole.radius:
                    self.tokens.remove(token)
                    break
            else:
                token.pos += acceleration * (1 / 120)

    def _walls(self, body):
        max_y = self.palette_y - body.radius
        if body.pos.x < body.radius:
            body.pos.x, body.vel.x = body.radius, abs(body.vel.x) * 0.9
        elif body.pos.x > self.width - body.radius:
            body.pos.x, body.vel.x = self.width - body.radius, -abs(body.vel.x) * 0.9
        if body.pos.y < body.radius:
            body.pos.y, body.vel.y = body.radius, abs(body.vel.y) * 0.9
        elif body.pos.y > max_y:
            body.pos.y, body.vel.y = max_y, -abs(body.vel.y) * 0.9

    def _swallow(self):
        holes = [b for b in self.bodies if b.kind == "black_hole"]
        for hole in holes:
            for body in list(self.bodies):
                if body is hole or body.swallowed or body.kind == "black_hole":
                    continue
                if body.pos.distance_to(hole.pos) < hole.radius:
                    hole.mass += body.mass
                    hole.radius = min(100, 26 * math.sqrt(hole.mass))
                    body.swallowed = True
                    self.bodies.remove(body)

    def _collisions(self):
        for i, first in enumerate(self.bodies):
            if first.kind == "orbit_center" or first.swallowed:
                continue
            for second in self.bodies[i + 1:]:
                if second.kind == "orbit_center" or second.swallowed:
                    continue
                delta = second.pos - first.pos
                distance = delta.length()
                minimum = first.radius + second.radius
                if distance >= minimum or distance == 0:
                    continue
                normal = delta / distance
                relative = second.vel - first.vel
                if relative.dot(normal) > 0:
                    continue
                before1, before2 = first.vel.copy(), second.vel.copy()
                impulse = (2 * relative.dot(normal)) / (first.mass + second.mass)
                first.vel += impulse * second.mass * normal
                second.vel -= impulse * first.mass * normal
                overlap = minimum - distance
                first.pos -= normal * (overlap * second.mass / (first.mass + second.mass))
                second.pos += normal * (overlap * first.mass / (first.mass + second.mass))
                momentum_before = (first.mass * before1 + second.mass * before2).length() / 100
                momentum_after = (first.mass * first.vel + second.mass * second.vel).length() / 100
                kinetic_before = (0.5 * first.mass * before1.length_squared() +
                                  0.5 * second.mass * before2.length_squared()) / 10000
                kinetic_after = (0.5 * first.mass * first.vel.length_squared() +
                                 0.5 * second.mass * second.vel.length_squared()) / 10000
                self.reports.insert(0, CollisionReport(first.mass, before1, first.vel.copy(),
                    second.mass, before2, second.vel.copy(), momentum_before, momentum_after,
                    kinetic_before, kinetic_after))
                first.collision_flash = second.collision_flash = 0.25
