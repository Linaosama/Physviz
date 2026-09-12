import math
import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
import pygame

from physviz.physics import Scene


def setup_module():
    pygame.init()


def teardown_module():
    pygame.quit()


def test_formula_chain_collapses():
    scene = Scene()
    scene.spawn_chain("mg", (300, 240))
    for _ in range(73):
        scene.step()
    assert len(scene.bodies) == 1
    assert scene.bodies[0].kind == "mg"


def test_dropped_tokens_merge_at_their_shared_y():
    scene = Scene()
    first = scene.spawn_token("m", (300, 260))
    scene.spawn_token("g", (340, 260))
    scene.release_token(first)
    assert len(scene.chains) == 1
    assert scene.chains[0].pos.y == 260


def test_elastic_collision_conserves_momentum_and_energy():
    scene = Scene()
    first = scene.spawn_body("momentum", (400, 300), (100, 0))
    second = scene.spawn_body("momentum", (452, 300), (-100, 0))
    p_before = first.mass * first.vel + second.mass * second.vel
    e_before = 0.5 * first.mass * first.vel.length_squared() + 0.5 * second.mass * second.vel.length_squared()
    for _ in range(10):
        scene.step()
    p_after = first.mass * first.vel + second.mass * second.vel
    e_after = 0.5 * first.mass * first.vel.length_squared() + 0.5 * second.mass * second.vel.length_squared()
    assert (p_after - p_before).length() <= 1e-3
    assert abs(e_after - e_before) / max(e_before, 1) <= 1e-3


def test_orbit_capture_keeps_radius():
    scene = Scene()
    center = scene.spawn_body("orbit_center", (500, 400))
    body = scene.spawn_body("momentum", (700, 400), (0, 150))
    for _ in range(200):
        scene.step()
    assert body.orbiting
    radius = body.orbit_radius
    assert radius > 0
    assert math.isclose(body.pos.distance_to(center.pos), radius, rel_tol=1e-6, abs_tol=1e-6)
    for _ in range(200):
        scene.step()
    assert math.isclose(body.pos.distance_to(center.pos), radius, rel_tol=1e-6, abs_tol=1e-6)
