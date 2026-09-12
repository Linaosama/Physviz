"""Pygame user interface rendering."""
import pygame
from .entities import PALETTE_H, TOKEN_LABELS, Token
from .fonts import text


HELP = "左键拖动对象 · 右键删除 token/清除力 · 空格暂停 · R 重置 · Delete 删除选中"


def draw_ui(surface, scene, paused=False, fps=60):
    width, height = surface.get_size()
    surface.fill((12, 17, 28))
    pygame.draw.rect(surface, (18, 25, 40), (0, height - PALETTE_H, width, PALETTE_H))
    pygame.draw.line(surface, (65, 85, 110), (0, height - PALETTE_H), (width, height - PALETTE_H), 2)
    text(surface, "PhysViz · 物理公式实验台", (18, 14), 22, (220, 235, 250))
    text(surface, HELP, (18, 44), 15, (160, 180, 205))
    text(surface, f"FPS {fps:.0f}" + (" · 已暂停" if paused else ""), (width - 18, 18), 16,
         (180, 205, 225), "topright")
    for i, label in enumerate(TOKEN_LABELS):
        token = Token(label, (34 + i * 77, height - 37), True)
        token.draw(surface, 20)
    text(surface, "拖到上方画布组合公式", (width - 18, height - 17), 14, (145, 165, 190), "bottomright")
    panel = pygame.Rect(width - 425, 78, 405, 154)
    pygame.draw.rect(surface, (22, 30, 45), panel, border_radius=8)
    pygame.draw.rect(surface, (62, 83, 110), panel, 1, border_radius=8)
    text(surface, "碰撞信息", (panel.x + 14, panel.y + 10), 17, (240, 210, 130))
    if scene.reports:
        report = scene.reports[0]
        v1, v1a = report.v1.length() / 100, report.v1_after.length() / 100
        v2, v2a = report.v2.length() / 100, report.v2_after.length() / 100
        lines = [
            f"m1={report.m1:.1f}, v1={v1:.2f} → v1'={v1a:.2f} m/s",
            f"m2={report.m2:.1f}, v2={v2:.2f} → v2'={v2a:.2f} m/s",
            f"总动量 p: {report.momentum_before:.2f} → {report.momentum_after:.2f} kg·m/s",
            f"总动能 E: {report.kinetic_before:.2f} → {report.kinetic_after:.2f} J",
        ]
        for i, line in enumerate(lines):
            text(surface, line, (panel.x + 14, panel.y + 39 + i * 24), 13, (205, 220, 235))
    else:
        text(surface, "暂无碰撞（报告保留 4 秒）", (panel.x + 14, panel.y + 50), 14, (135, 155, 180))
    legend = pygame.Rect(18, 86, 210, 112)
    pygame.draw.rect(surface, (20, 28, 42), legend, border_radius=6)
    text(surface, "图例", (30, 94), 16, (220, 220, 190))
    text(surface, "青色箭头：速度", (30, 121), 13, (130, 220, 235))
    text(surface, "橙色：轨道/向心力", (30, 145), 13, (240, 175, 90))
    text(surface, "红色：外力 F", (30, 169), 13, (245, 120, 100))
