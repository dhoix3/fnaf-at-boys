"""Atmospheric game rendering: menu, office, CRT camera tablet and scare effects."""
from __future__ import annotations

import math
import os
import random
import sys
import time
from pathlib import Path

import pygame

from office_render import prepare_photo
from office_render import render_office, render_camera


WIDTH, HEIGHT = 1280, 720
CAM_MAP_SIZE = (492, 400)
CAM_MAP_RECT = pygame.Rect(900, 142, 282, 230)
CAM_NODES = {
    "1A": (201, 6, 78, 48), "1B": (201, 78, 78, 48),
    "1C": (108, 93, 78, 48), "5": (18, 52, 78, 48), "7": (394, 93, 78, 48),
    "3": (31, 282, 78, 48), "2A": (118, 280, 78, 48), "2B": (118, 338, 78, 48),
    "6": (359, 243, 78, 48), "4A": (296, 280, 78, 48), "4B": (296, 338, 78, 48),
    "YOU": (201, 372, 78, 29),
}
CAM_CONNECTIONS = (
    ((240,47),(240,78)),                         # stage to dining
    ((190,112),(198,112),(198,98),(207,98)),    # cove to dining
    ((145,93),(88,93),(88,73)),                 # backstage to cove
    ((273,98),(398,98)),                         # dining to restrooms
    ((124,304),(103,304)),                       # storage to west hall
    ((240,117),(240,220),(157,220),(157,284)),  # dining to west hall
    ((240,220),(335,220),(335,284)),            # dining to east hall
    ((157,323),(157,340)),                       # west hall to corner
    ((335,323),(335,340)),                       # east hall to corner
    ((368,304),(390,304),(390,285),(398,285)),  # east hall to kitchen
    ((190,359),(207,359)), ((302,359),(273,359)),
    ((240,397),(240,400)),                       # office below map
)


def asset_path(relative: str) -> str:
    root = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return str(Path(root) / relative)


class UI:
    def __init__(self, screen: pygame.Surface):
        self.screen = screen
        self.font = pygame.font.SysFont("couriernew", 22, bold=True)
        self.small = pygame.font.SysFont("couriernew", 16, bold=True)
        self.tiny = pygame.font.SysFont("couriernew", 12, bold=True)
        self.title = pygame.font.SysFont("couriernew", 56, bold=True)
        self.images: dict[int, pygame.Surface] = {}
        for number in range(1, 6):
            path = asset_path(f"assets/images/photo{number}.jpg")
            try:
                self.images[number] = prepare_photo(pygame.image.load(path).convert())
            except (pygame.error, OSError) as exc:
                print(f"[assets] Missing image {path}: {exc}")
                fallback = pygame.Surface((320, 480))
                fallback.fill((25, 20, 22))
                pygame.draw.circle(fallback, (145, 24, 24), (160, 170), 54, 5)
                self.images[number] = fallback
        self.fan_phase = 0.0
        self.camera_feed = pygame.Surface((850, 518))
        self.pressed: dict[str, float] = {}
        self.vhs = self._make_vhs_overlay()
        self.glitch_rng = random.Random()

    def _make_vhs_overlay(self) -> pygame.Surface:
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        for y in range(0, HEIGHT, 3):
            pygame.draw.line(overlay, (0, 0, 0, 40 if y % 9 else 62), (0, y), (WIDTH, y))
        # Soft, layered edge falloff. Constructed once, so it is cheap per frame.
        for i in range(18):
            alpha = 7 + i * 2
            pygame.draw.rect(overlay, (0, 0, 0, alpha), (i * 10, i * 7, WIDTH - 2*i*10, HEIGHT - 2*i*7), 10)
        return overlay

    def press(self, name: str) -> None:
        self.pressed[name] = time.monotonic() + 0.13

    def _l(self, game, key: str, **values) -> str:
        return game.localization.get(key, **values)

    def hit_test(self, pos: tuple[int, int], game) -> bool:
        x, y = pos
        if game.mode == "menu":
            if pygame.Rect(485, 452, 310, 62).collidepoint(pos):
                game.mode = "settings"
            else:
                game.start_night()
            return True
        if game.mode == "settings":
            if pygame.Rect(485, 500, 310, 62).collidepoint(pos):
                game.leave_settings()
            elif pygame.Rect(450, 205, 430, 64).collidepoint(pos):
                game.set_language("ru" if game.localization.language == "en" else "en")
            elif pygame.Rect(630, 305, 60, 56).collidepoint(pos):
                game.set_volume(game.settings["volume"] - 0.1)
            elif pygame.Rect(880, 305, 60, 56).collidepoint(pos):
                game.set_volume(game.settings["volume"] + 0.1)
            elif pygame.Rect(710, 305, 150, 56).collidepoint(pos):
                game.set_volume((x - 710) / 150)
            elif pygame.Rect(450, 390, 450, 64).collidepoint(pos):
                game.set_fullscreen(not game.settings["fullscreen"])
            return True
        if game.mode in ("dead", "won"):
            return True
        if game.mode != "playing" or game.cameras.open:
            if game.mode == "playing" and game.cameras.open:
                return self._camera_click(pos, game)
            return False
        controls = {
            "left_door": pygame.Rect(24, 380, 188, 72),
            "left_light": pygame.Rect(24, 463, 188, 72),
            "right_door": pygame.Rect(1068, 380, 188, 72),
            "right_light": pygame.Rect(1068, 463, 188, 72),
            "camera": pygame.Rect(522, 638, 236, 58),
        }
        for name, rect in controls.items():
            if rect.collidepoint(pos):
                self.press(name)
                if name.endswith("door"):
                    side = name.split("_")[0]
                    game.toggle_door(side)
                elif name.endswith("light"):
                    side = name.split("_")[0]
                    game.toggle_light(side)
                else:
                    game.set_camera_open(not game.cameras.open)
                return True
        return False

    def _camera_click(self, pos: tuple[int, int], game) -> bool:
        x, y = pos
        for room, (nx, ny, nw, nh) in CAM_NODES.items():
            rect = pygame.Rect(CAM_MAP_RECT.x + nx * CAM_MAP_RECT.w // 492,
                               CAM_MAP_RECT.y + ny * CAM_MAP_RECT.h // 400,
                               max(1, nw * CAM_MAP_RECT.w // 492), max(1, nh * CAM_MAP_RECT.h // 400))
            if rect.collidepoint(pos):
                game.cameras.select(room)
                game.audio.play("camera")
                return True
        if (x > 1120 and y < 100) or pygame.Rect(990, 522, 180, 44).collidepoint(pos):
            game.set_camera_open(False)
            return True
        return False

    def draw(self, game) -> None:
        if game.mode == "menu":
            self._draw_menu(game)
        elif game.mode == "settings":
            self._draw_settings(game)
        elif game.mode == "playing":
            self._draw_office(game)
            if game.cameras.open:
                self._draw_tablet(game)
        elif game.mode == "scare":
            self._draw_scare(game)
        else:
            self._draw_end(game)
        if game.mode != "menu":
            self.screen.blit(self.vhs, (0, 0))
            if random.random() < 0.018:
                y = random.randrange(HEIGHT)
                pygame.draw.rect(self.screen, (200, 220, 200, 50), (0, y, WIDTH, random.randrange(1, 5)))
        pygame.display.flip()

    def _text(self, text: str, font: pygame.font.Font, color, pos, center=False, shadow=True):
        image = font.render(text, True, color)
        rect = image.get_rect(center=pos) if center else image.get_rect(topleft=pos)
        if shadow:
            shade = font.render(text, True, (0, 0, 0))
            self.screen.blit(shade, rect.move(2, 3))
        self.screen.blit(image, rect)
        return rect

    def _draw_menu(self, game) -> None:
        self.screen.fill((5, 6, 8))
        self._draw_wall_and_floor(game)
        shade = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        shade.fill((0, 0, 0, 105))
        self.screen.blit(shade, (0, 0))
        self._text(self._l(game, "title_top"), self.title, (184, 183, 171), (WIDTH//2, 175), True)
        self._text(self._l(game, "title_bottom"), self.title, (159, 34, 34), (WIDTH//2, 237), True)
        pygame.draw.line(self.screen, (92, 73, 54), (430, 280), (850, 280), 2)
        self._text(self._l(game, "menu_subtitle"), self.small, (139, 144, 137), (WIDTH//2, 308), True)
        pulse = 0.5 + 0.5 * math.sin(time.monotonic() * 4.0)
        self._button(pygame.Rect(485, 365, 310, 62), self._l(game, "menu_start"), True, "start")
        self._button(pygame.Rect(485, 452, 310, 62), self._l(game, "menu_settings"), False, "settings")
        if pulse > 0.35:
            self._text(self._l(game, "menu_press_any_key"), self.small, (180, 31, 31), (WIDTH//2, 552), True)
        self._text(self._l(game, "controls_hint"), self.tiny, (108, 111, 108), (WIDTH//2, 610), True)

    def _draw_settings(self, game) -> None:
        self.screen.fill((5, 6, 8))
        self._draw_wall_and_floor(game)
        veil = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        veil.fill((0, 0, 0, 166))
        self.screen.blit(veil, (0, 0))
        panel = pygame.Rect(330, 110, 620, 500)
        pygame.draw.rect(self.screen, (11, 13, 13), panel.move(0, 8), border_radius=8)
        pygame.draw.rect(self.screen, (27, 30, 29), panel, border_radius=8)
        pygame.draw.rect(self.screen, (103, 107, 98), panel, 2, border_radius=8)
        self._text(self._l(game, "settings_title"), self.title, (184, 183, 171), (640, 156), True)

        self._text(self._l(game, "settings_language"), self.small, (193, 194, 180), (420, 237), True)
        self._button(pygame.Rect(700, 205, 180, 64), game.localization.language.upper(), True, "language")

        self._text(self._l(game, "settings_volume"), self.small, (193, 194, 180), (460, 333), True)
        self._button(pygame.Rect(630, 305, 60, 56), "−", False, "volume_down")
        bar = pygame.Rect(710, 325, 150, 18)
        pygame.draw.rect(self.screen, (4, 6, 6), bar, border_radius=4)
        fill = bar.copy()
        fill.width = int(bar.width * game.settings["volume"])
        pygame.draw.rect(self.screen, (127, 163, 112), fill, border_radius=4)
        pygame.draw.rect(self.screen, (105, 110, 103), bar, 1, border_radius=4)
        self._button(pygame.Rect(880, 305, 60, 56), "+", False, "volume_up")
        self._text(f"{int(game.settings['volume']*100)}%", self.tiny, (210, 215, 199), (805, 360), True, False)

        self._text(self._l(game, "settings_fullscreen"), self.small, (193, 194, 180), (460, 423), True)
        flag = game.settings["fullscreen"]
        self._button(pygame.Rect(700, 395, 180, 64), self._l(game, "settings_on" if flag else "settings_off"), flag, "fullscreen")
        self._button(pygame.Rect(485, 500, 310, 62), self._l(game, "settings_back"), False, "back")
        self._text(self._l(game, "settings_shortcuts"), self.tiny, (107, 112, 105), (640, 578), True)

    def _draw_wall_and_floor(self, game) -> None:
        self.screen.fill((13, 14, 16))
        # Converging wall planes give the room a clear vanishing point.
        pygame.draw.polygon(self.screen, (23, 24, 26), [(0, 0), (WIDTH, 0), (WIDTH, 440), (850, 453), (430, 453), (0, 440)])
        pygame.draw.polygon(self.screen, (28, 28, 29), [(0, 0), (438, 80), (438, 452), (0, 720)])
        pygame.draw.polygon(self.screen, (25, 25, 26), [(WIDTH, 0), (842, 80), (842, 452), (WIDTH, 720)])
        pygame.draw.polygon(self.screen, (19, 18, 17), [(0, 720), (430, 453), (850, 453), (WIDTH, 720)])
        # Wall panel seams and rubbed highlights.
        for x in (214, 422, 640, 858, 1066):
            pygame.draw.line(self.screen, (38, 38, 38), (x, 95), (x, 444), 2)
            pygame.draw.line(self.screen, (9, 10, 10), (x+4, 95), (x+4, 444), 2)
        for y in (173, 273, 370):
            pygame.draw.line(self.screen, (37, 36, 34), (220, y), (1060, y), 2)
            pygame.draw.line(self.screen, (10, 11, 11), (220, y+3), (1060, y+3), 2)
        # Floor tiles converge towards the corridor.
        horizon = (640, 453)
        for x in range(-200, WIDTH+200, 170):
            pygame.draw.line(self.screen, (35, 32, 29), horizon, (x, HEIGHT), 2)
        for y, spread in ((510, 90), (575, 185), (650, 310)):
            pygame.draw.line(self.screen, (32, 30, 28), (640-spread, y), (640+spread, y), 2)
        # Framed posters and crude mascot art.
        for rect, color, word in ((pygame.Rect(318, 166, 105, 143), (74, 54, 40), game.localization.get("poster_party")),
                                  (pygame.Rect(858, 166, 105, 143), (57, 48, 45), game.localization.get("poster_smile"))):
            pygame.draw.rect(self.screen, (7, 7, 7), rect.move(6, 7))
            pygame.draw.rect(self.screen, (116, 86, 56), rect)
            inner = rect.inflate(-10, -10)
            pygame.draw.rect(self.screen, color, inner)
            pygame.draw.circle(self.screen, (185, 147, 87), (rect.centerx, rect.y+59), 22, 2)
            pygame.draw.circle(self.screen, (15, 13, 11), (rect.centerx-7, rect.y+55), 3)
            pygame.draw.circle(self.screen, (15, 13, 11), (rect.centerx+7, rect.y+55), 3)
            self._text(word, self.tiny, (222, 195, 153), (rect.centerx, rect.bottom-21), True, False)
        # Ceiling cable and a dirty fluorescent fixture.
        pygame.draw.line(self.screen, (6, 7, 8), (640, 0), (640, 112), 4)
        pygame.draw.polygon(self.screen, (66, 65, 58), [(576,110),(704,110),(724,135),(556,135)])
        pygame.draw.polygon(self.screen, (142, 133, 104), [(590,115),(690,115),(700,128),(580,128)])
        lamp_glow = pygame.Surface((360, 230), pygame.SRCALPHA)
        pygame.draw.ellipse(lamp_glow, (210, 185, 115, 16), lamp_glow.get_rect())
        self.screen.blit(lamp_glow, (460, 120))

    def _draw_office(self, game) -> None:
        self.fan_phase += 0.09
        offset = max(-330, min(330, int(game.look_angle * 220)))
        intruders = {
            "left": next((enemy.photo for enemy in game.enemies if enemy.room == "LDoor"), None),
            "right": next((enemy.photo for enemy in game.enemies if enemy.room == "RDoor"), None),
        }
        render_office(self.screen, offset, game.player.doors, game.player.lights,
                      intruders, self.fan_phase, self.images)

        self._button(pygame.Rect(24,380,188,72), self._l(game, "door_left", status=self._l(game, "state_sealed" if game.player.doors['left'] else "state_open")), game.player.doors['left'], "left_door")
        self._button(pygame.Rect(24,463,188,72), self._l(game, "light_left", status=self._l(game, "state_on" if game.player.lights['left'] else "state_off")), game.player.lights['left'], "left_light")
        self._button(pygame.Rect(1068,380,188,72), self._l(game, "door_right", status=self._l(game, "state_sealed" if game.player.doors['right'] else "state_open")), game.player.doors['right'], "right_door")
        self._button(pygame.Rect(1068,463,188,72), self._l(game, "light_right", status=self._l(game, "state_on" if game.player.lights['right'] else "state_off")), game.player.lights['right'], "right_light")
        self._button(pygame.Rect(522,638,236,58), self._l(game, "camera_button"), game.cameras.open, "camera")
        self._text(f"{game.clock_label}", self.font, (160, 225, 164), (640, 31), True)
        self._text(self._l(game, "power", value=int(game.player.power)), self.small, (222, 61, 50) if game.player.power < 25 else (207, 207, 193), (25, 24))
        bar = pygame.Rect(25, 52, 210, 12)
        pygame.draw.rect(self.screen, (5, 6, 6), bar)
        pygame.draw.rect(self.screen, (139, 40, 35) if game.player.power < 25 else (111, 163, 102), (bar.x, bar.y, int(bar.w*game.player.power/100), bar.h))
        pygame.draw.rect(self.screen, (135, 136, 128), bar, 1)
        usage = 1 + int(game.cameras.open) + sum(game.player.doors.values()) + sum(game.player.lights.values())
        self._text(self._l(game, "usage", bars="▮"*usage), self.tiny, (197, 204, 181), (25, 73))
        if game.player.power < 18 and int(time.monotonic()*3) % 2:
            self._text(self._l(game, "low_power"), self.small, (235, 40, 34), (640, 568), True)

    def _draw_desk(self) -> None:
        x, y = 562, 500
        pygame.draw.polygon(self.screen, (7, 9, 9), [(x+8,y+9),(x+147,y+9),(x+140,y+91),(x,y+91)])
        pygame.draw.rect(self.screen, (51,52,48), (x,y,146,86), border_radius=8)
        pygame.draw.rect(self.screen, (5,12,9), (x+12,y+10,122,60), border_radius=7)
        pygame.draw.rect(self.screen, (29,62,41), (x+18,y+16,110,49), border_radius=5)
        for yy in range(y+20,y+65,5):
            pygame.draw.line(self.screen, (18,39,26), (x+23,yy),(x+124,yy),1)
        pygame.draw.circle(self.screen, (72,231,119), (x+125,y+76), 3)
        pygame.draw.polygon(self.screen, (34,34,31), [(x+56,y+86),(x+92,y+86),(x+101,y+108),(x+47,y+108)])
        pygame.draw.rect(self.screen, (100,89,70), (390,590,32,42), border_radius=5)
        pygame.draw.ellipse(self.screen, (31,28,23), (393,589,26,9))
        pygame.draw.arc(self.screen, (141,128,102), (415,599,18,23), -1.4, 1.4, 3)
        pygame.draw.polygon(self.screen,(177,169,150),[(836,600),(905,592),(912,612),(842,620)])

    def _button(self, rect, text, active=False, name="") -> None:
        pressed = self.pressed.get(name, 0) > time.monotonic()
        offset = 3 if pressed else 0
        shadow = rect.move(0, 7-offset)
        pygame.draw.rect(self.screen, (2,3,3), shadow, border_radius=5)
        body = rect.move(0, offset)
        pygame.draw.rect(self.screen, (45,30,27) if active else (28,30,31), body, border_radius=4)
        pygame.draw.rect(self.screen, (147,54,43) if active else (91,94,91), body, 2, border_radius=4)
        pygame.draw.line(self.screen, (137,137,127), (body.x+7,body.y+4),(body.right-7,body.y+4),1)
        lines = text.split("\n")
        for i, line in enumerate(lines):
            font = self.small if "\n" not in text or i == 0 else self.tiny
            color = (239,185,143) if active else (192,197,187)
            self._text(line, font, color, (body.centerx,body.centery+(i-(len(lines)-1)/2)*22), True, False)

    def _draw_tablet(self, game) -> None:
        veil = pygame.Surface((WIDTH,HEIGHT),pygame.SRCALPHA)
        veil.fill((0,0,0,154))
        self.screen.blit(veil,(0,0))
        tablet = pygame.Rect(82,62,1116,590)
        pygame.draw.rect(self.screen,(3,4,4),tablet.move(0,10),border_radius=20)
        pygame.draw.rect(self.screen,(74,76,72),tablet,border_radius=18)
        pygame.draw.rect(self.screen,(26,29,28),tablet.inflate(-12,-12),border_radius=13)
        pygame.draw.rect(self.screen,(105,107,98),tablet,3,border_radius=18)
        feed = pygame.Rect(108,87,850,518)
        pygame.draw.rect(self.screen,(5,9,7),feed)
        room = game.cameras.current
        occupants = game.enemies_in_room(room)
        render_camera(self.camera_feed, room, [enemy.photo for enemy in occupants], self.images, time.monotonic())
        # Scene already has a faint green room-only haze; photo overlays remain natural.
        self.screen.blit(self.camera_feed, feed.topleft)
        pygame.draw.rect(self.screen,(59,87,66),feed,2)
        self._text(self._l(game, "cam_feed", room=room, name=self._l(game, f"room_{room}")), self.small, (138,221,152), (feed.x+20,feed.y+14))
        foxy = next((enemy for enemy in game.enemies if enemy.name == "Foxy"), None)
        if foxy and foxy.running:
            pygame.draw.rect(self.screen, (72, 8, 12), (feed.x+16, feed.bottom-58, feed.w-32, 32))
            self._text(self._l(game, "motion_alert"), self.tiny, (255,125,103), (feed.centerx,feed.bottom-42), True, False)
        if time.monotonic() < game.cameras.glitch_until:
            for _ in range(20):
                gy = random.randrange(feed.y+34,feed.bottom-8)
                gx = random.randrange(feed.x,feed.right-100)
                pygame.draw.rect(self.screen,random.choice(((172,45,49),(48,175,90),(110,125,150))), (gx,gy,random.randrange(25,220),random.randrange(1,5)))
            flash = pygame.Surface((feed.w,feed.h),pygame.SRCALPHA)
            flash.fill((110,144,122,30))
            self.screen.blit(flash,feed.topleft)
        # VHS interference: scan bands, rolling tear, chroma noise and small jitter.
        tear_y = feed.y + int((time.monotonic() * 145) % feed.h)
        pygame.draw.line(self.screen, (185,205,185), (feed.x, tear_y), (feed.right, tear_y), 2)
        for _ in range(650):
            nx=random.randrange(feed.x,feed.right); ny=random.randrange(feed.y,feed.bottom)
            shade=random.choice(((175,190,175),(35,48,40),(110,125,115)))
            self.screen.set_at((nx,ny),shade)
        for sy in range(feed.y,feed.bottom,4):
            pygame.draw.line(self.screen,(0,0,0),(feed.x,sy),(feed.right,sy),1)
        # Connected room map, scaled from the FNAF-style floor plan.
        self._text(self._l(game, "cam_map"), self.tiny, (149,154,142), (990,100))
        for points in CAM_CONNECTIONS:
            scaled = [(CAM_MAP_RECT.x + px * CAM_MAP_RECT.w // 492,
                       CAM_MAP_RECT.y + py * CAM_MAP_RECT.h // 400) for px, py in points]
            pygame.draw.lines(self.screen, (91,101,86), False, scaled, 2)
        for room, (nx, ny, nw, nh) in CAM_NODES.items():
            rect = pygame.Rect(CAM_MAP_RECT.x + nx * CAM_MAP_RECT.w // 492,
                               CAM_MAP_RECT.y + ny * CAM_MAP_RECT.h // 400,
                               max(1, nw * CAM_MAP_RECT.w // 492), max(1, nh * CAM_MAP_RECT.h // 400))
            active = room == game.cameras.current
            if room == "YOU":
                pygame.draw.rect(self.screen, (21,26,23), rect, border_radius=3)
                pygame.draw.rect(self.screen, (114,130,108), rect, 2, border_radius=3)
                self._text("YOU", self.tiny, (184,194,175), rect.center, True, False)
                continue
            pygame.draw.rect(self.screen, (112,25,27) if active else (26,30,28), rect, border_radius=3)
            pygame.draw.rect(self.screen, (230,48,43) if active else (114,130,108), rect, 2, border_radius=3)
            self._text(room, self.tiny, (255,225,213) if active else (184,194,175), rect.center, True, False)
            if game.enemies_in_room(room):
                pygame.draw.circle(self.screen, (235,37,31), (rect.right-3,rect.y+3), 3)
        self._text(self._l(game, "cam_switch_hint"),self.tiny,(128,138,127),(990,424))
        pygame.draw.rect(self.screen,(32,33,31),(990,466,180,42),border_radius=3)
        pygame.draw.rect(self.screen,(120,125,116),(990,466,180,42),1,border_radius=3)
        self._text(self._l(game, "cam_signal"),self.tiny,(143,207,145),(1080,487),True,False)
        pygame.draw.rect(self.screen,(45,32,31),(990,522,180,44),border_radius=3)
        pygame.draw.rect(self.screen,(136,76,60),(990,522,180,44),1,border_radius=3)
        self._text(self._l(game, "cam_lower"),self.tiny,(210,179,159),(1080,544),True,False)
        self._text(self._l(game, "cam_live"),self.tiny,(122,133,122),(110,615))

    def _draw_scare(self, game) -> None:
        elapsed = time.monotonic() - game.scare_started
        if elapsed < 1.0:
            self.screen.fill((0, 0, 0))
            return
        if elapsed < 2.45:
            self.screen.fill((24, 1, 4))
            shake = int(10 + elapsed*22)
            dx,dy=random.randint(-shake,shake),random.randint(-shake,shake)
            size = min(3.2, 0.42 + (elapsed-1.0)*2.25)
            img=self.images[game.scare_photo]
            w,h=int(WIDTH*size),int(HEIGHT*size)
            sprite=pygame.transform.smoothscale(img,(w,h))
            self.screen.blit(sprite,(WIDTH//2-w//2+dx,HEIGHT//2-h//2+dy))
            if int(elapsed*12)%2==0:
                flash=pygame.Surface((WIDTH,HEIGHT),pygame.SRCALPHA)
                flash.fill((150,0,0,70))
                self.screen.blit(flash,(0,0))
            if elapsed > .7:
                for y in range(random.randrange(40,HEIGHT),HEIGHT,6):
                    pygame.draw.line(self.screen,(80,10,18),(0,y),(WIDTH,y),1)
        else:
            game.mode="dead"
            self._draw_end(game)

    def _draw_end(self, game) -> None:
        render_office(self.screen, max(-330, min(330, int(game.look_angle * 220))), game.player.doors, game.player.lights)
        veil=pygame.Surface((WIDTH,HEIGHT),pygame.SRCALPHA)
        veil.fill((0,0,0,220))
        self.screen.blit(veil,(0,0))
        won=game.mode=="won"
        self._text("6:00 " + self._l(game, "period_am") if won else self._l(game, "game_over"),self.title,(195,207,186) if won else (175,33,37),(640,270),True)
        self._text(self._l(game, "game_survived" if won else "game_found"),self.font,(198,195,177),(640,342),True)
        rect=pygame.Rect(472,420,336,66)
        self._button(rect,self._l(game,"game_restart"),False,"restart")
        if int(time.monotonic()*2)%2:
            self._text(self._l(game,"game_restart_hint"),self.tiny,(123,124,116),(640,528),True)
