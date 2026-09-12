import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
import pygame

from physviz.entities import Chain, Token, chain_to_markup
from physviz.fonts import math_text, resolved_fonts
from physviz.physics import Environment, Scene
from physviz.ui import PropertyPanel, draw_ui


def setup_module():
    pygame.init()


def teardown_module():
    pygame.quit()


def test_formula_applies_to_ball_and_gravity():
    scene = Scene()
    ball = scene.spawn_body("ball", (300, 200))
    scene.apply_formula(ball, "mg")
    assert ball.has_gravity
    start = ball.pos.y
    for _ in range(10):
        scene.step()
    assert ball.pos.y > start


def test_plain_ball_does_not_fall():
    scene = Scene()
    ball = scene.spawn_body("ball", (300, 200))
    for _ in range(10):
        scene.step()
    assert ball.pos.y == 200


def test_chip_drop_applies_formula():
    scene = Scene()
    ball = scene.spawn_body("ball", (300, 200))
    chip = scene.spawn_chain("mg", (300, 200))
    for _ in range(145):
        scene.step()
    assert chip.is_chip
    assert scene.apply_chip(chip, ball)
    assert ball.has_gravity
    assert chip not in scene.chains


def test_binary_stars_keep_separation():
    scene = Scene()
    first, second = scene.spawn_binary((640, 380))
    initial = first.pos.distance_to(second.pos)
    for _ in range(20 * 240):
        scene.step()
    assert abs(first.pos.distance_to(second.pos) - initial) / initial <= 0.05


def test_barrier_blocks_attraction():
    blocked = Scene()
    blocked.spawn_body("black_hole", (300, 300))
    ball = blocked.spawn_body("ball", (500, 300))
    blocked.spawn_barrier((400, 300), length=300, orientation=90)
    for _ in range(2 * 240):
        blocked.step()
    assert ball.pos.distance_to((500, 300)) < 1.0

    open_scene = Scene()
    open_scene.spawn_body("black_hole", (300, 300))
    open_ball = open_scene.spawn_body("ball", (500, 300))
    for _ in range(2 * 240):
        open_scene.step()
    assert open_ball.pos.distance_to((500, 300)) > 1.0


def test_air_drag_reduces_speed_monotonically():
    scene = Scene(environment=Environment(air_k=2.0))
    ball = scene.spawn_body("ball", (300, 200), (200, 0))
    speeds = []
    for _ in range(120):
        scene.step()
        speeds.append(ball.vel.length())
    assert all(next_speed <= speed + 1e-9 for speed, next_speed in zip(speeds, speeds[1:]))


def test_table_friction_stops_gravity_ball():
    scene = Scene()
    table = scene.spawn_table((500, 500))
    table.table_mu = 0.3
    ball = scene.spawn_body("ball", (500, 463), (100, 0))
    scene.apply_formula(ball, "mg")
    for _ in range(2 * 240):
        scene.step()
    assert abs(ball.vel.x) < 1e-6


def test_chip_generate_creates_black_hole_and_star():
    scene = Scene()
    hole_chip = scene.spawn_chain("E=mc²", (300, 200))
    star_chip = scene.spawn_chain("G=mv²/r", (500, 200))
    for _ in range(150):
        scene.step()
    hole = scene.generate_formula(hole_chip)
    star = scene.generate_formula(star_chip)
    assert hole.kind == "black_hole"
    assert star.kind == "star"


def test_swallowing_conserves_momentum():
    scene = Scene()
    hole = scene.spawn_body("black_hole", (400, 300), (10, 0))
    ball = scene.spawn_body("ball", (420, 300), (100, 0))
    before = hole.mass * hole.vel + ball.mass * ball.vel
    scene.step()
    assert ball not in scene.bodies
    assert (hole.mass * hole.vel - before).length() < 1e-6


def test_scenes_are_isolated():
    first = Scene()
    second = Scene()
    second.spawn_body("star", (400, 300))
    assert first.bodies == []
    assert len(second.bodies) == 1


def test_math_text_renders_on_dummy_driver():
    surface = pygame.Surface((400, 100), pygame.SRCALPHA)
    fraction = math_text(surface, r"F=\frac{mv^2}{r}=3.2\u{ N}", (20, 20), 20,
                         (255, 255, 255))
    subscript = math_text(surface, "v_0", (20, 70), 20, (255, 255, 255))
    assert fraction.width > 0 and fraction.height > 0
    assert subscript.width > 0 and subscript.height > 0
    assert resolved_fonts()[1]


def test_chain_to_markup_fractions():
    assert chain_to_markup(list("G=mv²/r")) == r"G=\frac{mv^2}{r}"
    assert chain_to_markup(list("E=½mv²")) == r"E=\frac{1}{2}mv^2"


def test_chain_rect_merge_and_incomplete_fraction_layout():
    scene = Scene()
    chain = scene.spawn_chain("=mv²/", (300, 300))
    assert not chain._fraction_bars
    left = scene.spawn_token("G", (chain.rect().left - 15, 300))
    assert scene.release_token(left) is chain
    right = scene.spawn_token("r", (chain.rect().right + 30, 300))
    assert scene.release_token(right) is chain
    assert chain.text == "G=mv²/r"
    assert chain._fraction_bars
    assert Chain([Token("/"), Token("r")], (300, 300)).rect().height == 44


def test_draw_ui_handles_token_and_chain_selection():
    scene = Scene()
    token = scene.spawn_token("m", (200, 200))
    chain = scene.spawn_chain("mg", (260, 200))
    scene.selected = token
    property_panel = PropertyPanel()
    property_panel.set_body(token)
    surface = pygame.Surface((1280, 800))
    draw_ui(surface, scene, token, property_panel)
    property_panel.set_body(chain)
    draw_ui(surface, scene, chain, property_panel)


def test_elastic_collision_conserves_ball_energy():
    scene = Scene()
    first = scene.spawn_body("ball", (400, 300), (100, 0))
    second = scene.spawn_body("ball", (452, 300), (-100, 0))
    momentum = first.mass * first.vel + second.mass * second.vel
    energy = 0.5 * first.mass * first.vel.length_squared() + 0.5 * second.mass * second.vel.length_squared()
    for _ in range(10):
        scene.step()
    assert (first.mass * first.vel + second.mass * second.vel - momentum).length() <= 1e-3
    current_energy = 0.5 * first.mass * first.vel.length_squared() + 0.5 * second.mass * second.vel.length_squared()
    assert abs(current_energy - energy) / max(energy, 1) <= 1e-3
