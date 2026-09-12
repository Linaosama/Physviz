"""Pygame application, multiple simulations, and interactions."""
import random
from pathlib import Path
import pygame
from .effects import draw_body_effects
from .entities import Body
from .physics import CANVAS_RIGHT, Scene
from .ui import (EnvironmentPanel, PropertyPanel, draw_ui, palette_hit, tabs_hit,
                 tabs_layout)

WIDTH, HEIGHT = 1280, 800


class App:
    def __init__(self, width=WIDTH, height=HEIGHT):
        self.width, self.height = width, height
        self.scenes = [Scene(width, height)]
        self.active = 0

    @property
    def scene(self):
        return self.scenes[self.active]

    def add_scene(self):
        self.scenes.append(Scene(self.width, self.height))
        self.active = len(self.scenes) - 1

    def close_scene(self, index):
        if len(self.scenes) == 1:
            return
        self.scenes.pop(index)
        self.active = min(self.active, len(self.scenes) - 1)


def run(max_seconds=None):
    pygame.init()
    pygame.display.set_caption("PhysViz · 物理公式实验台")
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    clock = pygame.time.Clock()
    app = App()
    property_panel = PropertyPanel()
    environment_panel = EnvironmentPanel()
    environment_panel.sync(app.scene.environment)
    paused = False
    drag_offset = pygame.Vector2()
    drag_points = []
    right_dragging = False
    right_start = pygame.Vector2()
    last_click = (None, 0)
    spawned_from_palette = False
    drag_moved = False
    elapsed = 0.0
    running = True
    while running:
        frame_dt = min(clock.tick(60) / 1000, 0.05)
        elapsed += frame_dt
        if max_seconds is not None and elapsed >= max_seconds:
            break
        scene = app.scene
        selected = scene.selected
        for event in pygame.event.get():
            scene = app.scene
            selected = scene.selected
            if event.type == pygame.QUIT:
                running = False
                continue
            if property_panel.handle_event(event, selected):
                if property_panel.delete_requested:
                    _remove_selected(scene, selected)
                continue
            if environment_panel.handle_event(event, scene.environment):
                continue
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_F12:
                    _save_screenshot(screen)
                elif event.key == pygame.K_SPACE:
                    paused = not paused
                elif event.key == pygame.K_r:
                    scene.reset()
                    property_panel.set_body(None)
                elif event.key == pygame.K_DELETE and selected:
                    _remove_selected(scene, selected)
                continue
            if event.type == pygame.MOUSEBUTTONDOWN:
                point = pygame.Vector2(event.pos)
                tab = tabs_hit(WIDTH, len(app.scenes), point)
                if tab is not None:
                    if tab == "add":
                        app.add_scene()
                        environment_panel.sync(app.scene.environment)
                    else:
                        rect = next(rect for index, rect in tabs_layout(WIDTH, len(app.scenes))
                                    if index == tab)
                        if len(app.scenes) > 1 and point.x >= rect.right - 18:
                            app.close_scene(tab)
                        else:
                            app.active = tab
                        environment_panel.sync(app.scene.environment)
                    continue
                if event.button == 1:
                    spawned_from_palette = False
                    drag_moved = False
                    picked = _pick(scene, point)
                    if picked is None:
                        material = palette_hit(WIDTH, point)
                        if material:
                            label, action = material
                            spawn_point = _canvas_spawn_point()
                            if action == "token":
                                picked = scene.spawn_token(label, spawn_point)
                            elif label == "小球":
                                picked = scene.spawn_body("ball", spawn_point)
                            elif label == "桌子":
                                picked = scene.spawn_table(spawn_point)
                            elif label == "隔板":
                                picked = scene.spawn_barrier(spawn_point)
                            elif label == "双星":
                                picked = scene.spawn_binary(spawn_point)[0]
                            elif label == "三星":
                                picked = scene.spawn_trinary(spawn_point)[0]
                            spawned_from_palette = picked is not None
                    if picked:
                        now = pygame.time.get_ticks()
                        if picked is last_click[0] and now - last_click[1] < 450:
                            if picked in scene.chains and picked.is_chip:
                                picked = scene.generate_formula(picked)
                        last_click = (picked, now)
                        if selected and selected is not picked:
                            selected.selected = False
                        scene.selected = picked
                        if picked:
                            picked.selected = True
                            picked.dragging = True
                            drag_offset = pygame.Vector2() if spawned_from_palette else picked.pos - point
                            drag_points = [(now, picked.pos.copy())]
                            if isinstance(picked, Body):
                                picked.on_surface = None
                    continue
                if event.button == 3:
                    picked = _pick(scene, point)
                    if isinstance(picked, Body) and picked.kind == "ball" and picked.can_force:
                        scene.selected = picked
                        picked.selected = True
                        right_dragging = True
                        right_start = point.copy()
                    elif picked and (picked in scene.tokens or picked in scene.chains):
                        _remove_selected(scene, picked)
                continue
            if event.type == pygame.MOUSEMOTION:
                point = pygame.Vector2(event.pos)
                selected = scene.selected
                if selected and selected.dragging:
                    if spawned_from_palette and point.distance_to(drag_points[0][1]) > 8:
                        drag_moved = True
                    if selected in scene.chains:
                        selected.move(point + drag_offset - selected.pos)
                        selected._layout()
                    else:
                        selected.pos = point + drag_offset
                    _clamp_dragged(scene, selected)
                    drag_points.append((pygame.time.get_ticks(), point.copy()))
                    drag_points = drag_points[-10:]
                    if hasattr(selected, "in_palette"):
                        selected.in_palette = False
                if right_dragging and isinstance(selected, Body) and selected.kind == "ball":
                    selected.force = point - right_start
                continue
            if event.type == pygame.MOUSEBUTTONUP:
                point = pygame.Vector2(event.pos)
                selected = scene.selected
                if event.button == 1 and selected:
                    selected.dragging = False
                    if spawned_from_palette and not drag_moved and point.x >= CANVAS_RIGHT:
                        center = _canvas_spawn_point()
                        if isinstance(selected, Body):
                            selected.pos = center
                            scene.clamp_body_position(selected)
                        else:
                            selected.pos = center
                            if selected in scene.chains:
                                selected._layout()
                    elif isinstance(selected, Body):
                        scene.clamp_body_position(selected)
                    if selected in scene.tokens:
                        merged = scene.release_token(selected)
                        if merged:
                            scene.selected = merged
                            merged.selected = True
                    elif selected in scene.chains:
                        target = next((body for body in scene.bodies
                                       if body.kind == "ball" and body.hit(point)), None)
                        if selected.is_chip and target and scene.apply_chip(selected, target):
                            scene.selected = target
                            target.selected = True
                    elif selected in scene.bodies:
                        if not (spawned_from_palette and not drag_moved):
                            _throw_velocity(selected, drag_points)
                        scene.release_body(selected)
                    spawned_from_palette = False
                    continue
                if event.button == 3:
                    if isinstance(selected, Body) and point.distance_to(right_start) < 8:
                        selected.force.update(0, 0)
                    right_dragging = False
        if not paused:
            for _ in range(4):
                app.scene.step(1 / 240)
        draw_ui(screen, app.scene, app.scene.selected, property_panel, paused,
                clock.get_fps(), pygame.mouse.get_pos(), app.scenes, app.active,
                environment_panel)
        draw_body_effects(screen, app.scene)
        for chain in app.scene.chains:
            chain.draw(screen)
        for token in app.scene.tokens:
            token.draw(screen)
        for body in app.scene.bodies:
            body.draw(screen, app.scene.time, app.scene.environment.g)
        pygame.display.flip()
    pygame.quit()


def _pick(scene, point):
    for body in reversed(scene.bodies):
        if body.hit(point):
            return body
    for chain in reversed(scene.chains):
        if chain.hit(point):
            return chain
    for token in reversed(scene.tokens):
        if token.hit(point):
            return token
    return None


def _canvas_spawn_point():
    return pygame.Vector2(
        CANVAS_RIGHT / 2 + random.uniform(-40, 40),
        400 + random.uniform(-40, 40),
    )


def _save_screenshot(screen):
    directory = Path("/home/ubuntu/screenshots")
    directory.mkdir(parents=True, exist_ok=True)
    index = 1
    while (directory / ("physviz-%d.png" % index)).exists():
        index += 1
    path = directory / ("physviz-%d.png" % index)
    pygame.image.save(screen, path)
    return path


def _clamp_dragged(scene, selected):
    if isinstance(selected, Body):
        scene.clamp_body_position(selected)
        return
    radius = getattr(selected, "radius", 22)
    half_width = getattr(selected, "width", 0) / 2 if selected in scene.chains else radius
    selected.pos.x = max(half_width, min(CANVAS_RIGHT - half_width, selected.pos.x))
    selected.pos.y = max(radius, min(scene.palette_y - radius, selected.pos.y))
    if selected in scene.chains:
        selected._layout()


def _remove_selected(scene, selected):
    for collection in (scene.tokens, scene.chains, scene.bodies):
        if selected in collection:
            collection.remove(selected)
            if scene.selected is selected:
                scene.selected = None
            return


def _throw_velocity(body, points):
    now = pygame.time.get_ticks()
    recent = [(stamp, pos) for stamp, pos in points if now - stamp <= 120]
    if len(recent) < 2 or now - recent[-1][0] > 150:
        body.vel.update(0, 0)
        return
    first_t, first = recent[0]
    last_t, last = recent[-1]
    velocity = (last - first) / max((last_t - first_t) / 1000, 1 / 120)
    maximum = 300 if body.attracts else 1500
    if velocity.length() > maximum:
        velocity.scale_to_length(maximum)
    body.vel = velocity


if __name__ == "__main__":
    run()
