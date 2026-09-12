"""Font loading with a Chinese-capable preference order."""
from functools import lru_cache
import os
import pygame

FONT_PATH = "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc"


@lru_cache(maxsize=32)
def get_font(size: int) -> pygame.font.Font:
    if os.path.exists(FONT_PATH):
        return pygame.font.Font(FONT_PATH, size)
    for name in ("notosanscjksc", "wqyzenhei", "microsoftyahei"):
        font = pygame.font.SysFont(name, size)
        if font:
            return font
    return pygame.font.Font(None, size)


def text(surface, value, pos, size=18, color=(230, 235, 245), anchor="topleft"):
    image = get_font(size).render(str(value), True, color)
    rect = image.get_rect()
    setattr(rect, anchor, pos)
    surface.blit(image, rect)
    return rect
