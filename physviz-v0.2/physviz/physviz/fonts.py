"""Cross-platform Chinese UI and mathematical formula fonts."""
from functools import lru_cache
import os
from pathlib import Path
import pygame


ROOT = Path(__file__).resolve().parent.parent
_FZ_NAMES = ("fzs10", "方正s10", "fzshusong", "方正书宋", "fzssjw")
UI_PATHS = [
    "C:/Windows/Fonts/msyh.ttc", "C:/Windows/Fonts/msyhbd.ttc",
    "C:/Windows/Fonts/simhei.ttf", "C:/Windows/Fonts/simsun.ttc",
    "/System/Library/Fonts/PingFang.ttc", "/System/Library/Fonts/STHeiti Light.ttc",
    "/Library/Fonts/Arial Unicode.ttf",
    "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf",
]
MATH_PATHS = [
    "C:/Windows/Fonts/timesi.ttf", "C:/Windows/Fonts/times.ttf",
    "/System/Library/Fonts/Supplemental/Times New Roman Italic.ttf",
    "/Library/Fonts/Times New Roman Italic.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSerif-Italic.ttf",
    "/usr/share/fonts/truetype/liberation2/LiberationSerif-Italic.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Italic.ttf",
]


def _project_font():
    for suffix in ("ttf", "ttc", "otf"):
        path = ROOT / "assets" / "fonts" / f"cjk.{suffix}"
        if path.exists():
            return str(path)
    return None


def _fz_font():
    roots = [
        Path("C:/Windows/Fonts"), Path.home() / "AppData/Local/Microsoft/Windows/Fonts",
        Path("/Library/Fonts"), Path.home() / "Library/Fonts", Path("/usr/share/fonts"),
    ]
    for root in roots:
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if path.is_file() and any(name in path.name.lower() for name in _FZ_NAMES):
                return str(path)
    return None


def _resolve(paths, names, italic=False):
    for path in paths:
        if os.path.exists(path):
            return path
    return pygame.font.match_font(names, italic=italic)


@lru_cache(maxsize=1)
def resolved_roles():
    cjk = _project_font() or _fz_font() or _resolve(
        UI_PATHS, ["microsoftyahei", "msyh", "simhei", "pingfangsc",
                   "notosanscjksc", "wqyzenhei", "wenquanyizenhei",
                   "droidsansfallback"])
    math_italic = _resolve(
        MATH_PATHS, ["timesnewroman", "liberationserif", "dejavuserif", "freeserif"], True)
    return cjk, math_italic, cjk


def resolved_fonts():
    cjk, math_italic, _ = resolved_roles()
    return cjk, math_italic


@lru_cache(maxsize=32)
def ui_font(size):
    path, _, _ = resolved_roles()
    return pygame.font.Font(path, size) if path else pygame.font.Font(None, size)


@lru_cache(maxsize=32)
def math_font(size):
    _, path, _ = resolved_roles()
    font = pygame.font.Font(path, size) if path else pygame.font.Font(None, size)
    font.set_italic(True)
    return font


@lru_cache(maxsize=32)
def upright_font(size):
    path, _, fallback = resolved_roles()
    return pygame.font.Font(path or fallback, size) if path or fallback else pygame.font.Font(None, size)


def _place(surface, image, pos, anchor):
    rect = image.get_rect()
    setattr(rect, anchor, pos)
    surface.blit(image, rect)
    return rect


def text(surface, value, pos, size=18, color=(230, 235, 245), anchor="topleft"):
    image = ui_font(size).render(str(value), True, color)
    return _place(surface, image, pos, anchor)


def _group(value, start):
    if start >= len(value) or value[start] != "{":
        return value[start:start + 1], start + 1
    depth = 0
    for index in range(start, len(value)):
        if value[index] == "{":
            depth += 1
        elif value[index] == "}":
            depth -= 1
            if depth == 0:
                return value[start + 1:index], index + 1
    return value[start + 1:], len(value)


def _parse(value, upright=False):
    nodes = []
    index = 0
    plain = []
    while index < len(value):
        if value.startswith(r"\frac", index):
            if plain:
                nodes.append(("text", "".join(plain), upright))
                plain = []
            index += 5
            while index < len(value) and value[index].isspace():
                index += 1
            numerator, index = _group(value, index)
            while index < len(value) and value[index].isspace():
                index += 1
            denominator, index = _group(value, index)
            nodes.append(("frac", numerator, denominator))
        elif value.startswith(r"\u", index):
            if plain:
                nodes.append(("text", "".join(plain), upright))
                plain = []
            index += 2
            content, index = _group(value, index)
            nodes.append(("text", content, True))
        elif value[index] in "_^":
            if plain:
                nodes.append(("text", "".join(plain), upright))
                plain = []
            mode = value[index]
            content, index = _group(value, index + 1)
            nodes.append(("script", content, mode))
        else:
            plain.append(value[index])
            index += 1
    if plain:
        nodes.append(("text", "".join(plain), upright))
    return nodes


def _italic_char(char):
    return char.isascii() and char.isalpha() or char in "μθπ"


def _run_surface(value, size, color, upright=False):
    images = []
    for char in value:
        font = upright_font(size) if upright or not _italic_char(char) else math_font(size)
        images.append(font.render(char, True, color))
    width = sum(image.get_width() for image in images)
    height = max((image.get_height() for image in images), default=1)
    result = pygame.Surface((max(1, width), height), pygame.SRCALPHA)
    x = 0
    for image in images:
        result.blit(image, (x, 0))
        x += image.get_width()
    return result


def _markup_surface(value, size, color):
    items = []
    width = 0
    top = 0
    bottom = 0
    for node in _parse(str(value)):
        if node[0] == "text":
            image = _run_surface(node[1], size, color, node[2])
            y = 0
        elif node[0] == "script":
            image = _run_surface(node[1], max(8, int(size * 0.65)), color)
            y = int(size * 0.3) if node[2] == "_" else int(-size * 0.4)
        else:
            numerator = _markup_surface(node[1], max(8, int(size * 0.8)), color)
            denominator = _markup_surface(node[2], max(8, int(size * 0.8)), color)
            frac_width = max(numerator.get_width(), denominator.get_width()) + 8
            bar_y = numerator.get_height() + 1
            image = pygame.Surface((frac_width, numerator.get_height() + denominator.get_height() + 3),
                                   pygame.SRCALPHA)
            image.blit(numerator, ((frac_width - numerator.get_width()) // 2, 0))
            pygame.draw.line(image, color, (2, bar_y),
                             (frac_width - 3, bar_y), 1)
            image.blit(denominator, ((frac_width - denominator.get_width()) // 2,
                                     numerator.get_height() + 3))
            y = int(size * 0.55) - bar_y
        items.append((image, width, y))
        width += image.get_width()
        top = min(top, y)
        bottom = max(bottom, y + image.get_height())
    result = pygame.Surface((max(1, width), max(1, bottom - top)), pygame.SRCALPHA)
    for image, x, y in items:
        result.blit(image, (x, y - top))
    return result


def math_text(surface, value, pos, size=18, color=(230, 235, 245), anchor="topleft"):
    return _place(surface, _markup_surface(str(value), size, color), pos, anchor)
