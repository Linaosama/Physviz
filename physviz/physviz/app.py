"""Main pygame application."""
import pygame
from .entities import PALETTE_H, TOKEN_LABELS
from .physics import Scene
from .effects import draw_body_effects
from .ui import draw_ui


WIDTH, HEIGHT = 1280, 800


def run(max_seconds=None):
    pygame.init()
    pygame.display.set_caption("PhysViz · 物理公式实验台")
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    clock = pygame.time.Clock()
    scene = Scene(WIDTH, HEIGHT)
    paused = False
    selected = None
    drag_offset = pygame.Vector2()
    drag_points = []
    right_dragging = False
    right_start = pygame.Vector2()
    running = True
    elapsed = 0.0
    while running:
        frame_dt = min(clock.tick(60) / 1000.0, 0.05)
        elapsed += frame_dt
        if max_seconds is not None and elapsed >= max_seconds:
            break
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    paused = not paused
                elif event.key == pygame.K_r:
                    scene.reset()
                    selected = None
                elif event.key == pygame.K_DELETE and selected is not None:
                    _remove_selected(scene, selected)
                    selected = None
            elif event.type == pygame.MOUSEBUTTONDOWN:
                point = pygame.Vector2(event.pos)
                if event.button == 1:
                    picked = _pick(scene, point)
                    if picked is None and point.y >= HEIGHT - PALETTE_H:
                        idx = int(point.x // 77)
                        if 0 <= idx < len(TOKEN_LABELS):
                            picked = scene.spawn_token(TOKEN_LABELS[idx], (point.x, HEIGHT - PALETTE_H - 35))
                    if picked is not None:
                        selected = picked
                        scene.selected = picked
                        picked.selected = True
                        if picked in scene.bodies:
                            picked.orbiting = False
                            picked.orbit_center = None
                        picked.dragging = True
                        drag_offset = picked.pos - point
                        drag_points = [(pygame.time.get_ticks(), point.copy())]
                elif event.button == 3:
                    picked = _pick(scene, point)
                    if picked is not None:
                        selected = picked
                        scene.selected = picked
                        picked.selected = True
                        if getattr(picked, "kind", None) == "force":
                            picked.right_drag_start = point.copy()
                            right_start = point.copy()
                            right_dragging = True
                        elif hasattr(picked, "label"):
                            _remove_selected(scene, picked)
                            selected = None
            elif event.type == pygame.MOUSEMOTION:
                point = pygame.Vector2(event.pos)
                if selected is not None and getattr(selected, "dragging", False):
                    if hasattr(selected, "move") and selected in scene.chains:
                        selected.move(point + drag_offset - selected.pos)
                    else:
                        selected.pos = point + drag_offset
                    drag_points.append((pygame.time.get_ticks(), point.copy()))
                    drag_points = drag_points[-10:]
                    if selected in scene.chains:
                        selected._layout()
                    if selected in scene.tokens:
                        selected.in_palette = False
                if right_dragging and selected is not None and getattr(selected, "kind", None) == "force":
                    selected.force = point - right_start
            elif event.type == pygame.MOUSEBUTTONUP:
                point = pygame.Vector2(event.pos)
                if event.button == 1 and selected is not None:
                    selected.dragging = False
                    if selected in scene.tokens:
                        scene.release_token(selected)
                    elif selected in scene.bodies:
                        _throw_velocity(selected, drag_points)
                        scene.capture_orbit(selected)
                    selected.selected = False
                    selected = None
                    scene.selected = None
                elif event.button == 3 and right_dragging:
                    if selected is not None and getattr(selected, "kind", None) == "force":
                        if point.distance_to(right_start) < 8:
                            selected.force.update(0, 0)
                    right_dragging = False
                    if selected is not None:
                        selected.selected = False
                        selected = None
                        scene.selected = None
        if not paused:
            for _ in range(2):
                scene.step(1 / 120)
        draw_ui(screen, scene, paused, clock.get_fps())
        draw_body_effects(screen, scene)
        for chain in scene.chains:
            chain.draw(screen)
        for token in scene.tokens:
            token.draw(screen)
        for body in scene.bodies:
            body.draw(screen, scene.time)
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


def _remove_selected(scene, selected):
    for collection in (scene.tokens, scene.chains, scene.bodies):
        if selected in collection:
            collection.remove(selected)
            return


def _throw_velocity(body, points):
    now = pygame.time.get_ticks()
    recent = [(timestamp, position) for timestamp, position in points if now - timestamp <= 120]
    if len(recent) < 2 or now - recent[-1][0] > 150:
        body.vel.update(0, 0)
        return
    first_t, first = recent[0]
    last_t, last = recent[-1]
    seconds = max((last_t - first_t) / 1000.0, 1 / 120)
    velocity = (last - first) / seconds
    if velocity.length() > 1500:
        velocity.scale_to_length(1500)
    body.vel = velocity


if __name__ == "__main__":
    run()
