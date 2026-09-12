"""Fixed-step multi-body physics and formula modifier application."""
from dataclasses import dataclass
import math
import pygame
from .entities import Body, Chain, Token, PALETTE_H
from .formulas import Formula, recognize

WORLD_W, WORLD_H = 1280, 800
PIXELS_PER_METER = 100.0
PANEL_X = 840
CANVAS_RIGHT = PANEL_X - 12


@dataclass
class Environment:
    g: float = 9.8
    global_gravity: bool = False
    air_k: float = 0.0
    ground_mu: float = 0.0
    restitution: float = 0.9
    G_sim: float = 0.02


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


def _orientation(a, b, c):
    value = (b.x - a.x) * (c.y - a.y) - (b.y - a.y) * (c.x - a.x)
    if abs(value) < 1e-9:
        return 0
    return 1 if value > 0 else 2


def _on_segment(a, b, c):
    return min(a.x, c.x) - 1e-9 <= b.x <= max(a.x, c.x) + 1e-9 and \
        min(a.y, c.y) - 1e-9 <= b.y <= max(a.y, c.y) + 1e-9


def segments_intersect(a, b, c, d):
    """Return whether closed line segments AB and CD intersect."""
    first = (_orientation(a, b, c), _orientation(a, b, d))
    second = (_orientation(c, d, a), _orientation(c, d, b))
    if first[0] != first[1] and second[0] != second[1]:
        return True
    return (first[0] == 0 and _on_segment(a, c, b)) or \
        (first[1] == 0 and _on_segment(a, d, b)) or \
        (second[0] == 0 and _on_segment(c, a, d)) or \
        (second[1] == 0 and _on_segment(c, b, d))


class Scene:
    def __init__(self, width=WORLD_W, height=WORLD_H, environment=None):
        self.width, self.height = width, height
        self.palette_y = height - PALETTE_H
        self.environment = environment or Environment()
        self.tokens, self.chains, self.bodies = [], [], []
        self.reports = []
        self.selected = None
        self.time = 0.0

    def reset(self):
        self.tokens.clear()
        self.chains.clear()
        self.bodies.clear()
        self.reports.clear()
        self.selected = None
        self.time = 0.0

    def spawn_token(self, label, pos):
        token = Token(label, pos)
        self.tokens.append(token)
        return token

    def spawn_chain(self, labels, pos=(400, 260)):
        chain = Chain([Token(label, pos) for label in labels], pos)
        self.chains.append(chain)
        return chain

    def spawn_body(self, kind="ball", pos=(400, 300), velocity=(0, 0), mass=None, **kwargs):
        body = Body(kind, pos, mass, velocity)
        for key, value in kwargs.items():
            if hasattr(body, key):
                setattr(body, key, value)
        self.bodies.append(body)
        return body

    def spawn_table(self, pos=(500, 500), width=300, height=20):
        table = self.spawn_body("table", pos)
        table.width, table.height = float(width), float(height)
        return table

    def spawn_barrier(self, pos=(600, 400), length=240, orientation=90):
        barrier = self.spawn_body("barrier", pos)
        barrier.length, barrier.orientation = float(length), float(orientation)
        return barrier

    def clamp_body_position(self, body):
        if body.kind == "table":
            half_x, half_y = body.width / 2, body.height / 2
        elif body.kind == "barrier":
            horizontal = abs(body.orientation % 180) < 45
            half_x = body.length / 2 if horizontal else body.height / 2
            half_y = body.height / 2 if horizontal else body.length / 2
        else:
            half_x = half_y = body.radius
        body.pos.x = max(half_x, min(CANVAS_RIGHT - half_x, body.pos.x))
        body.pos.y = max(half_y, min(self.palette_y - half_y, body.pos.y))

    def spawn_binary(self, pos):
        distance = 120.0
        center = pygame.Vector2(pos)
        radius_m = distance / 100
        softening = 0.3
        speed = math.sqrt(self.environment.G_sim * 1000 * radius_m /
                          (4 * radius_m ** 2 + softening ** 2))
        first = self.spawn_body("star", center + (-distance, 0), velocity=(0, -speed * 100))
        second = self.spawn_body("star", center + (distance, 0), velocity=(0, speed * 100))
        return first, second

    def spawn_trinary(self, pos):
        center = pygame.Vector2(pos)
        side = 240.0
        radius = side / math.sqrt(3)
        speed = math.sqrt(3 * self.environment.G_sim * 1000 / (side / 100))
        bodies = []
        for index in range(3):
            angle = math.radians(90 + index * 120)
            radial = pygame.Vector2(math.cos(angle), math.sin(angle)) * radius
            tangent = pygame.Vector2(-radial.y, radial.x).normalize()
            bodies.append(self.spawn_body("star", center + radial, velocity=tangent * speed * 100))
        return bodies

    def apply_formula(self, body, formula):
        if not isinstance(body, Body) or body.kind != "ball":
            return body
        formula = formula if isinstance(formula, Formula) else recognize(formula)
        if not formula:
            return body
        if formula.kind == "mg":
            body.has_gravity = True
        elif formula.kind == "force":
            body.can_force = True
            body.force = pygame.Vector2(100, 0)
        elif formula.kind == "momentum":
            body.show_momentum = True
            if not body.vel.length():
                body.vel.x = 200
        elif formula.kind == "energy":
            body.show_energy = True
            if not body.vel.length():
                body.vel.x = 200
        elif formula.kind == "black_hole":
            body.kind = "black_hole"
            body.attracts = True
            body.radius = max(18.0, 0.006 * body.mass)
        elif formula.kind == "star":
            body.kind = "star"
            body.attracts = True
            body.show_orbit_force = True
            body.radius = 22.0
            if body.mass <= 1:
                body.mass = 1000.0
            body.trail = type(body.trail)(maxlen=240)
        elif formula.kind == "friction":
            body.show_friction = True
        elif formula.kind == "potential":
            body.show_potential = True
        elif formula.kind == "velocity_time":
            body.show_velocity_time = True
        elif formula.kind == "gravity_force":
            body.show_gravity_force = True
        elif formula.kind == "work":
            body.show_work = True
        return body

    def apply_chip(self, chip, body):
        if chip in self.chains and chip.is_chip and body in self.bodies and body.kind == "ball":
            self.apply_formula(body, chip.recognized)
            self.chains.remove(chip)
            return True
        return False

    def generate_formula(self, chip):
        if chip not in self.chains or not chip.is_chip:
            return None
        formula = chip.recognized
        initial = (200, 0) if formula.kind in ("momentum", "energy") else (0, 0)
        kind = {"black_hole": "black_hole", "star": "star"}.get(formula.kind, "ball")
        body = self.spawn_body(kind, chip.pos, velocity=initial)
        self.apply_formula(body, formula)
        self.chains.remove(chip)
        return body

    def _merge_token(self, token):
        nearby = [chain for chain in self.chains
                  if not chain.is_chip and self._token_in_rect(token, chain.rect().inflate(60, 40))]
        if nearby:
            chain = min(nearby, key=lambda candidate: abs(candidate.pos.x - token.pos.x))
            ordered = sorted(chain.tokens, key=lambda item: item.pos.x)
            if not ordered or token.pos.x < ordered[0].pos.x:
                insert_at = 0
            elif token.pos.x > ordered[-1].pos.x:
                insert_at = len(chain.tokens)
            else:
                gaps = [
                    (abs(token.pos.x - (ordered[index].pos.x + ordered[index + 1].pos.x) / 2),
                     ordered[index + 1])
                    for index in range(len(ordered) - 1)
                ]
                insert_before = min(gaps, key=lambda item: item[0])[1]
                insert_at = chain.tokens.index(insert_before)
            chain.tokens.insert(insert_at, token)
            if token in self.tokens:
                self.tokens.remove(token)
            chain.pos = pygame.Vector2(sum(item.pos.x for item in chain.tokens) / len(chain.tokens), token.pos.y)
            chain._layout()
            chain.recognized = recognize(chain.text)
            chain.glow_time = 0
            return chain
        others = [item for item in self.tokens if item is not token and not item.in_palette
                  and abs(token.pos.y - item.pos.y) < 48
                  and token.pos.distance_to(item.pos) <= 50]
        if others:
            other = min(others, key=lambda item: token.pos.distance_to(item.pos))
            tokens = [token, other] if token.pos.x < other.pos.x else [other, token]
            self.tokens.remove(token)
            self.tokens.remove(other)
            chain = Chain(tokens, ((token.pos.x + other.pos.x) / 2, token.pos.y))
            self.chains.append(chain)
            return chain
        return None

    @staticmethod
    def _token_in_rect(token, rect):
        return rect.left <= token.pos.x <= rect.right and \
            rect.top <= token.pos.y <= rect.bottom

    def release_token(self, token):
        token.dragging = False
        return self._merge_token(token)

    def _blocked(self, first, second):
        for barrier in self.bodies:
            if barrier.kind != "barrier":
                continue
            start, end = barrier.barrier_endpoints()
            if segments_intersect(first, second, start, end):
                return True
        return False

    def _gravity_acceleration(self, body):
        acceleration = pygame.Vector2()
        for attractor in self.bodies:
            if attractor is body or not attractor.attracts or attractor.swallowed:
                continue
            if self._blocked(attractor.pos, body.pos):
                continue
            delta = attractor.pos - body.pos
            distance_m = delta.length() / PIXELS_PER_METER
            if distance_m <= 0:
                continue
            magnitude_m = self.environment.G_sim * attractor.mass / (distance_m ** 2 + 0.3 ** 2)
            acceleration += delta.normalize() * (magnitude_m * PIXELS_PER_METER)
        return acceleration

    def _assist_orbit(self, body):
        if body.kind != "ball" or body.dragging or body.vel.length() >= 30:
            return
        stars = [star for star in self.bodies
                 if star.kind == "star" and body.pos.distance_to(star.pos) <= 400
                 and not self._blocked(star.pos, body.pos)]
        if len(stars) != 1:
            return
        star = stars[0]
        distance_m = body.pos.distance_to(star.pos) / PIXELS_PER_METER
        if distance_m <= 0:
            return
        speed = math.sqrt(self.environment.G_sim * star.mass / distance_m) * PIXELS_PER_METER
        radial = body.pos - star.pos
        body.vel = pygame.Vector2(-radial.y, radial.x).normalize() * speed

    def release_body(self, body):
        body.dragging = False
        body.release_speed = body.vel.length()
        self._assist_orbit(body)

    def step(self, dt=1 / 240):
        self.time += dt
        for chain in self.chains:
            if chain.recognized:
                chain.glow_time += dt
        for report in self.reports:
            report.age += dt
        self.reports[:] = [report for report in self.reports if report.age < 4]
        self._swallow()
        accelerations = {}
        for body in self.bodies:
            if body.kind in ("table", "barrier") or body.dragging or body.swallowed:
                continue
            body.on_surface = None
            acceleration = pygame.Vector2()
            if body.kind == "ball" and (body.has_gravity or self.environment.global_gravity):
                acceleration.y += self.environment.g * PIXELS_PER_METER
            if body.kind == "ball" and body.can_force:
                acceleration += body.force / body.mass
            if body.kind == "ball" and self.environment.air_k:
                acceleration -= body.vel * self.environment.air_k / body.mass
            acceleration += self._gravity_acceleration(body)
            if body.kind == "black_hole":
                for other in self.bodies:
                    if other is not body and body.pos.distance_to(other.pos) < 3 * body.radius:
                        body.vel *= max(0.0, 1.0 - 0.5 * dt)
                        break
            accelerations[body] = acceleration
        for body, acceleration in accelerations.items():
            body.vel += acceleration * dt
            body.pos += body.vel * dt
            if body.kind in ("star", "black_hole") or (body.kind == "ball" and
                    (body.has_gravity or body.force.length() > 0)):
                body.trail.append(body.pos.copy())
            self._walls(body)
            self._tables(body)
            self._barriers(body)
            self._friction(body)
        self._swallow()
        self._collisions()

    def _walls(self, body):
        max_y = self.palette_y - body.radius
        e = self.environment.restitution
        if body.pos.x < body.radius:
            body.pos.x, body.vel.x = body.radius, abs(body.vel.x) * e
        elif body.pos.x > CANVAS_RIGHT - body.radius:
            body.pos.x, body.vel.x = CANVAS_RIGHT - body.radius, -abs(body.vel.x) * e
        if body.pos.y < body.radius:
            body.pos.y, body.vel.y = body.radius, abs(body.vel.y) * e
        elif body.pos.y >= max_y:
            body.pos.y = max_y
            if body.vel.y > 0:
                body.vel.y = -body.vel.y * e
            if abs(body.vel.y) < 12:
                body.vel.y = 0
                body.on_surface = "floor"

    def _tables(self, body):
        if body.kind not in ("ball", "star", "black_hole"):
            return
        for table in self.bodies:
            if table.kind != "table":
                continue
            rect = pygame.Rect(table.pos.x - table.width / 2, table.pos.y - table.height / 2,
                               table.width, table.height)
            closest = pygame.Vector2(max(rect.left, min(body.pos.x, rect.right)),
                                      max(rect.top, min(body.pos.y, rect.bottom)))
            delta = body.pos - closest
            distance = delta.length()
            if distance >= body.radius:
                continue
            if distance == 0:
                candidates = [
                    (abs(body.pos.y - rect.top), pygame.Vector2(0, -1)),
                    (abs(body.pos.y - rect.bottom), pygame.Vector2(0, 1)),
                    (abs(body.pos.x - rect.left), pygame.Vector2(-1, 0)),
                    (abs(body.pos.x - rect.right), pygame.Vector2(1, 0)),
                ]
                _, normal = min(candidates, key=lambda item: item[0])
                penetration = body.radius
            else:
                normal = delta.normalize()
                penetration = body.radius - distance
            body.pos += normal * penetration
            if body.vel.dot(normal) < 0:
                body.vel -= (1 + table.table_restitution) * body.vel.dot(normal) * normal
            if normal.y < -0.5 and abs(body.vel.y) < 12:
                body.vel.y = 0
                body.on_surface = table

    def _barriers(self, body):
        if body.kind not in ("ball", "star", "black_hole"):
            return
        for barrier in self.bodies:
            if barrier.kind != "barrier":
                continue
            rect = barrier.barrier_rect()
            closest = pygame.Vector2(max(rect.left, min(body.pos.x, rect.right)),
                                      max(rect.top, min(body.pos.y, rect.bottom)))
            delta = body.pos - closest
            distance = delta.length()
            if distance >= body.radius:
                continue
            normal = delta.normalize() if distance else pygame.Vector2(0, -1)
            body.pos += normal * (body.radius - distance if distance else body.radius)
            if body.vel.dot(normal) < 0:
                body.vel -= (1 + self.environment.restitution) * body.vel.dot(normal) * normal

    def _friction(self, body):
        if body.kind != "ball" or not body.has_gravity or body.on_surface is None:
            return
        mu = self.environment.ground_mu if body.on_surface == "floor" else body.on_surface.table_mu
        deceleration = mu * self.environment.g * PIXELS_PER_METER
        if abs(body.vel.x) <= deceleration / 240:
            body.vel.x = 0
        else:
            body.vel.x -= math.copysign(deceleration / 240, body.vel.x)

    def _merge_stars(self):
        for index, first in enumerate(list(self.bodies)):
            if first.kind != "star" or first.swallowed:
                continue
            for second in list(self.bodies[index + 1:]):
                if second.kind != "star" or second.swallowed:
                    continue
                if first.pos.distance_to(second.pos) > first.radius + second.radius:
                    continue
                total = first.mass + second.mass
                first.vel = (first.vel * first.mass + second.vel * second.mass) / total
                first.pos = (first.pos * first.mass + second.pos * second.mass) / total
                first.mass = total
                second.swallowed = True
                self.bodies.remove(second)
                break

    def _collisions(self):
        self._merge_stars()
        dynamic = [body for body in self.bodies if body.kind not in ("table", "barrier") and not body.swallowed]
        for index, first in enumerate(dynamic):
            for second in dynamic[index + 1:]:
                if first.kind == "black_hole" or second.kind == "black_hole":
                    continue
                if first.kind == "star" and second.kind == "star":
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
                impulse = 2 * relative.dot(normal) / (first.mass + second.mass)
                first.vel += impulse * second.mass * normal
                second.vel -= impulse * first.mass * normal
                overlap = minimum - distance
                first.pos -= normal * overlap * second.mass / (first.mass + second.mass)
                second.pos += normal * overlap * first.mass / (first.mass + second.mass)
                momentum_before = (first.mass * before1 + second.mass * before2).length() / 100
                momentum_after = (first.mass * first.vel + second.mass * second.vel).length() / 100
                kinetic_before = (0.5 * first.mass * before1.length_squared() +
                                  0.5 * second.mass * before2.length_squared()) / 10000
                kinetic_after = (0.5 * first.mass * first.vel.length_squared() +
                                 0.5 * second.mass * second.vel.length_squared()) / 10000
                self.reports.insert(0, CollisionReport(
                    first.mass, before1, first.vel.copy(), second.mass, before2,
                    second.vel.copy(), momentum_before, momentum_after,
                    kinetic_before, kinetic_after))

    def _swallow(self):
        holes = [body for body in self.bodies if body.kind == "black_hole"]
        for hole in holes:
            hole.radius = max(18.0, 0.006 * hole.mass)
            for body in list(self.bodies):
                if body is hole or body.swallowed or body.kind in ("table", "barrier"):
                    continue
                if self._blocked(hole.pos, body.pos):
                    continue
                if hole.pos.distance_to(body.pos) < hole.radius:
                    total = hole.mass + body.mass
                    hole.vel = (hole.vel * hole.mass + body.vel * body.mass) / total
                    hole.mass = total
                    hole.radius = max(18.0, 0.006 * hole.mass)
                    body.swallowed = True
                    self.bodies.remove(body)
