"""Software raycaster and camera-facing photo billboards (no OpenGL required)."""
from __future__ import annotations

import math
import random
from dataclasses import dataclass

import pygame


OFFICE_MAP = (
    "##########################",
    "####..................####",
    "####..................####",
    "####..................####",
    "####..................####",
    "#..D..................D..#",
    "####..................####",
    "####..................####",
    "####..................####",
    "####..................####",
    "####..................####",
    "##########################",
)

ROOM_CAMERA = {
    "1A": ("STAGE", (6.5, 9.0), -math.pi / 2),
    "1B": ("DINING", (6.5, 9.0), -math.pi / 2),
    "1C": ("COVE", (6.5, 9.0), -math.pi / 2),
    "2A": ("HALL", (6.5, 9.0), -math.pi / 2),
    "2B": ("HALL", (6.5, 9.0), -math.pi / 2),
    "4A": ("HALL", (6.5, 9.0), -math.pi / 2),
    "4B": ("HALL", (6.5, 9.0), -math.pi / 2),
    "5": ("BACKSTAGE", (6.5, 9.0), -math.pi / 2),
    "6": ("KITCHEN", (6.5, 9.0), -math.pi / 2),
    "7": ("RESTROOM", (6.5, 9.0), -math.pi / 2),
}


@dataclass(frozen=True)
class Sprite3D:
    image: pygame.Surface
    x: float
    y: float
    name: str = ""
    lit: bool = False
    show_eyes: bool = False
    scale: float = 1.0


def prepare_photo(image: pygame.Surface, size=(160, 240)) -> pygame.Surface:
    """Downsample supplied portraits and alpha-cut their nearly-black backdrops."""
    sprite = pygame.transform.smoothscale(image, size).convert_alpha()
    transparent = sprite.map_rgb((0, 0, 0, 0))
    pixels = pygame.PixelArray(sprite)
    for x in range(sprite.get_width()):
        for y in range(sprite.get_height()):
            color = sprite.unmap_rgb(pixels[x, y])
            if max(color.r, color.g, color.b) <= 20:
                pixels[x, y] = transparent
    del pixels
    return sprite


def camera_room_world(room: str) -> tuple[tuple[str, ...], tuple[float, float], float]:
    """Return a room-specific first-person camera placement and raycast layout."""
    kind, position, angle = ROOM_CAMERA.get(room, ROOM_CAMERA["1A"])
    grid = [list("############") for _ in range(11)]
    for y in range(1, 10):
        for x in range(1, 11):
            grid[y][x] = "."

    if kind == "STAGE":
        for x in (2, 9):
            grid[3][x] = "B"
            grid[4][x] = "B"
        grid[2][4] = grid[2][7] = "B"
    elif kind == "DINING":
        for x in (3, 6, 9):
            grid[4][x] = grid[5][x] = "W"
        grid[3][2] = grid[3][10] = "B"
    elif kind == "COVE":
        for x in range(2, 10):
            grid[2][x] = "C"
        grid[3][2] = grid[3][9] = "C"
    elif kind == "HALL":
        for x in range(1, 11):
            grid[2][x] = grid[8][x] = "B"
        grid[4][2] = grid[6][9] = "B"
    elif kind == "BACKSTAGE":
        for x, y in ((3, 3), (4, 3), (8, 4), (8, 5), (2, 7), (3, 7)):
            grid[y][x] = "W"
    elif kind == "KITCHEN":
        for x in (2, 5, 8):
            for y in (3, 6):
                grid[y][x] = "M"
        grid[2][4] = grid[2][7] = "M"
    elif kind == "RESTROOM":
        for x in (3, 8):
            grid[3][x] = grid[4][x] = "W"
        grid[6][5] = grid[6][6] = "W"

    if kind == "HALL":
        position = (6.5, 7.5)
    return tuple("".join(row) for row in grid), position, angle


class Raycaster:
    """Low-resolution textured DDA raycaster with z-buffered Sprite3D billboards."""

    def __init__(self, size=(400, 225), fov=0.72):
        self.width, self.height = size
        self.fov = fov
        self.surface = pygame.Surface(size).convert()
        self.z_buffer = [float("inf")] * self.width
        self.textures = self._make_textures()
        self._background = self._make_background()

    def _make_textures(self) -> dict[str, pygame.Surface]:
        rng = random.Random(813)
        textures: dict[str, pygame.Surface] = {}
        palettes = {
            "#": ((56, 53, 48), (27, 30, 32), "plaster"),
            "D": ((71, 74, 72), (24, 27, 28), "metal"),
            "B": ((84, 63, 48), (39, 34, 30), "brick"),
            "C": ((88, 27, 36), (34, 12, 18), "curtain"),
            "M": ((73, 77, 72), (29, 33, 32), "metal"),
            "W": ((104, 89, 69), (49, 43, 35), "wood"),
        }
        for kind, (base, seam, pattern) in palettes.items():
            texture = pygame.Surface((64, 64)).convert()
            for y in range(64):
                for x in range(64):
                    grit = rng.randint(-9, 9)
                    color = [max(0, min(255, channel + grit)) for channel in base]
                    if pattern == "brick" and (y % 16 in (0, 1) or (x + (32 if (y // 16) % 2 else 0)) % 32 in (0, 1)):
                        color = list(seam)
                    elif pattern == "metal" and y % 12 in (0, 1):
                        color = list(seam)
                    elif pattern == "wood" and (y % 18 in (0, 1) or x % 21 == 0):
                        color = list(seam)
                    elif pattern == "curtain" and x % 13 in (0, 1, 2):
                        color = [min(255, channel + 18) for channel in color]
                    texture.set_at((x, y), color)
            textures[kind] = texture
        return textures

    def _make_background(self) -> pygame.Surface:
        background = pygame.Surface((self.width, self.height)).convert()
        horizon = self.height // 2
        for y in range(self.height):
            if y < horizon:
                shade = max(3, 20 - int(y / max(1, horizon) * 15))
                color = (shade, shade, shade + 2)
            else:
                t = (y - horizon) / max(1, self.height - horizon)
                shade = int(22 - 17 * t)
                color = (shade, max(5, shade - 2), max(4, shade - 4))
            pygame.draw.line(background, color, (0, y), (self.width - 1, y))
        # Perspective floor seams recede toward the vanishing point.
        for x in range(-self.width, self.width * 2, max(12, self.width // 13)):
            pygame.draw.line(background, (33, 29, 25), (self.width // 2, horizon), (x, self.height), 1)
        for offset in (8, 18, 35, 66):
            y = min(self.height - 1, horizon + offset)
            pygame.draw.line(background, (34, 29, 25), (0, y), (self.width - 1, y), 1)
        return background

    def render(
        self,
        world: tuple[str, ...],
        position: tuple[float, float],
        angle: float,
        sprites: list[Sprite3D] | None = None,
        door_open: dict[str, float] | None = None,
        light_sources: list[tuple[float, float]] | None = None,
    ) -> pygame.Surface:
        surface = self.surface
        surface.blit(self._background, (0, 0))
        door_open = door_open or {}
        pos_x, pos_y = position
        dir_x, dir_y = math.cos(angle), math.sin(angle)
        plane_x, plane_y = -dir_y * self.fov, dir_x * self.fov
        world_h, world_w = len(world), len(world[0])

        for column in range(self.width):
            camera_x = 2.0 * column / self.width - 1.0
            ray_x = dir_x + plane_x * camera_x
            ray_y = dir_y + plane_y * camera_x
            map_x, map_y = int(pos_x), int(pos_y)
            delta_x = abs(1.0 / ray_x) if ray_x else 1e30
            delta_y = abs(1.0 / ray_y) if ray_y else 1e30
            step_x = -1 if ray_x < 0 else 1
            step_y = -1 if ray_y < 0 else 1
            side_x = (pos_x - map_x) * delta_x if ray_x < 0 else (map_x + 1.0 - pos_x) * delta_x
            side_y = (pos_y - map_y) * delta_y if ray_y < 0 else (map_y + 1.0 - pos_y) * delta_y
            side = 0
            tile = "#"
            perp = 1.0
            hit = False
            for _ in range(48):
                if side_x < side_y:
                    side_x += delta_x
                    map_x += step_x
                    side = 0
                else:
                    side_y += delta_y
                    map_y += step_y
                    side = 1
                tile = world[map_y][map_x] if 0 <= map_y < world_h and 0 <= map_x < world_w else "#"
                if tile == ".":
                    continue
                perp = max(0.08, (side_x - delta_x) if side == 0 else (side_y - delta_y))
                if tile == "D":
                    hit_y = pos_y + perp * ray_y
                    hit_x = pos_x + perp * ray_x
                    texture_pos = hit_y - math.floor(hit_y) if side == 0 else hit_x - math.floor(hit_x)
                    side_name = "left" if map_x < world_w // 2 else "right"
                    if texture_pos < door_open.get(side_name, 0.0):
                        tile = "."
                        continue
                hit = True
                break
            if not hit:
                perp = 14.0
                tile = "#"
            self.z_buffer[column] = perp
            line_height = min(self.height * 5, int(self.height / max(0.08, perp)))
            draw_start = max(0, self.height // 2 - line_height // 2)
            draw_end = min(self.height - 1, self.height // 2 + line_height // 2)
            if tile == "D":
                texture = self.textures["D"]
            else:
                texture = self.textures.get(tile, self.textures["#"])
            hit_coord = pos_y + perp * ray_y if side == 0 else pos_x + perp * ray_x
            texture_x = int((hit_coord - math.floor(hit_coord)) * 64) % 64
            if (side == 0 and ray_x > 0) or (side == 1 and ray_y < 0):
                texture_x = 63 - texture_x
            stripe = texture.subsurface((texture_x, 0, 1, 64))
            strip = pygame.transform.scale(stripe, (1, max(1, line_height)))
            distance_light = max(0.10, min(0.72, 0.82 - perp * 0.065))
            hit_x, hit_y = pos_x + perp * ray_x, pos_y + perp * ray_y
            light_boost = max((max(0.0, 1.0 - math.hypot(hit_x-lx, hit_y-ly) / 5.0) for lx, ly in (light_sources or [])), default=0.0)
            distance_light = min(1.0, distance_light + light_boost * 0.48)
            side_light = 0.70 if side else 0.92
            tint = int(255 * distance_light * side_light)
            strip.fill((tint, tint, tint), special_flags=pygame.BLEND_RGB_MULT)
            surface.blit(strip, (column, draw_start))
            if 0 <= draw_end < self.height:
                surface.set_at((column, draw_end), (13, 12, 11))

        self._draw_billboards(surface, position, dir_x, dir_y, plane_x, plane_y, sprites or [])
        return surface

    def _draw_billboards(self, surface, position, dir_x, dir_y, plane_x, plane_y, sprites: list[Sprite3D]) -> None:
        determinant = plane_x * dir_y - dir_x * plane_y
        if abs(determinant) < 1e-7:
            return
        inv_det = 1.0 / determinant
        pos_x, pos_y = position
        ordered = sorted(sprites, key=lambda sprite: (sprite.x-pos_x)**2 + (sprite.y-pos_y)**2, reverse=True)
        for sprite in ordered:
            rel_x, rel_y = sprite.x - pos_x, sprite.y - pos_y
            trans_x = inv_det * (dir_y * rel_x - dir_x * rel_y)
            trans_y = inv_det * (-plane_y * rel_x + plane_x * rel_y)
            if trans_y <= 0.12:
                continue
            screen_x = int(self.width * 0.5 * (1.0 + trans_x / trans_y))
            height = max(2, min(self.height * 4, int(self.height / trans_y * sprite.scale)))
            width = max(2, int(height * sprite.image.get_width() / sprite.image.get_height()))
            top = self.height // 2 - height // 2
            left = screen_x - width // 2
            first, last = max(0, left), min(self.width - 1, left + width)
            for stripe_x in range(first, last + 1):
                if trans_y >= self.z_buffer[stripe_x]:
                    continue
                tex_x = min(sprite.image.get_width()-1, max(0, int((stripe_x - left) * sprite.image.get_width() / width)))
                column = sprite.image.subsurface((tex_x, 0, 1, sprite.image.get_height()))
                column = pygame.transform.scale(column, (1, height))
                if not sprite.lit:
                    column.fill((24, 24, 30), special_flags=pygame.BLEND_RGB_MULT)
                surface.blit(column, (stripe_x, top))
            if sprite.show_eyes and not sprite.lit and 0 <= screen_x < self.width and trans_y < self.z_buffer[screen_x]:
                eye_y = top + int(height * 0.28)
                spread = max(2, int(width * 0.105))
                radius = max(1, int(height / self.height * 2.0))
                for eye_x in (screen_x - spread, screen_x + spread):
                    pygame.draw.circle(surface, (105, 4, 5), (eye_x, eye_y), radius + 2)
                    pygame.draw.circle(surface, (255, 28, 18), (eye_x, eye_y), radius)
