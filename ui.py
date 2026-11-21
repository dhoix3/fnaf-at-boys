"""Atmospheric game rendering: menu, office, CRT camera tablet and scare effects."""
from __future__ import annotations

import math
import os
import random
import sys
import time
from pathlib import Path

import pygame


WIDTH, HEIGHT = 1280, 720
ROOM_POS = {
    "1A": (0, 0), "1B": (1, 0), "1C": (2, 0),
    "2A": (0, 1), "2B": (1, 1), "4A": (2, 1),
    "5": (0, 2), "6": (1, 2), "4B": (2, 2), "7": (0, 3),
}


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
                self.images[number] = pygame.image.load(path).convert()
            except (pygame.error, OSError) as exc:
                print(f"[assets] Missing image {path}: {exc}")
                fallback = pygame.Surface((320, 480))
                fallback.fill((25, 20, 22))
                pygame.draw.circle(fallback, (145, 24, 24), (160, 170), 54, 5)
                self.images[number] = fallback
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

    def hit_test(self, pos: tuple[int, int], game) -> bool:
        x, y = pos
        if game.mode == "menu":
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
                    game.cameras.open = not game.cameras.open
                return True
        return False

    def _camera_click(self, pos: tuple[int, int], game) -> bool:
        x, y = pos
        if 990 <= x <= 1205 and 125 <= y <= 395:
            col = min(2, max(0, (x - 994) // 68))
            row = min(3, max(0, (y - 130) // 64))
            for room, (cx, cy) in ROOM_POS.items():
                if (cx, cy) == (col, row):
                    game.cameras.select(room)
                    game.audio.play("camera")
                    return True
        if (x > 1120 and y < 100) or pygame.Rect(990, 522, 180, 44).collidepoint(pos):
            game.cameras.open = False
            return True
        return False

    def draw(self, game) -> None:
        if game.mode == "menu":
            self._draw_menu(game)
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
        self._draw_wall_and_floor()
        shade = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        shade.fill((0, 0, 0, 105))
        self.screen.blit(shade, (0, 0))
        self._text("FIVE NIGHTS", self.title, (184, 183, 171), (WIDTH//2, 190), True)
        self._text("AT THE BOYS'", self.title, (159, 34, 34), (WIDTH//2, 255), True)
        pygame.draw.line(self.screen, (92, 73, 54), (430, 298), (850, 298), 2)
        self._text("SECURITY LOG  /  NIGHT 01", self.small, (139, 144, 137), (WIDTH//2, 330), True)
        now = time.monotonic()
        pulse = 0.5 + 0.5 * math.sin(now * 4.0)
        box = pygame.Rect(485, 405, 310, 72)
        self._button(box, "START NIGHT", True, "start")
        if pulse > 0.35:
            self._text("PRESS ANY KEY", self.small, (180, 31, 31), (WIDTH//2, 520), True)
        self._text("A / D DOORS    Q / E LIGHTS    SPACE CAMERAS", self.tiny, (108, 111, 108), (WIDTH//2, 590), True)
        self.screen.blit(self.vhs, (0, 0))

    def _draw_wall_and_floor(self) -> None:
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
        for rect, color, word in ((pygame.Rect(318, 166, 105, 143), (74, 54, 40), "PARTY!"),
                                  (pygame.Rect(858, 166, 105, 143), (57, 48, 45), "SMILE")):
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
        self._draw_wall_and_floor()
        # Door alcoves, layered frames and deep black hallways.
        frames = {"left": pygame.Rect(224, 202, 150, 283), "right": pygame.Rect(906, 202, 150, 283)}
        for side, frame in frames.items():
            pygame.draw.rect(self.screen, (7, 8, 9), frame.inflate(18, 16))
            pygame.draw.rect(self.screen, (68, 68, 64), frame, 7)
            opening = frame.inflate(-18, -18)
            pygame.draw.rect(self.screen, (1, 2, 3), opening)
            pygame.draw.line(self.screen, (105, 100, 88), (frame.x+4, frame.y+4), (frame.x+4, frame.bottom-5), 3)
            enemy = game.enemy_at_door(side)
            if enemy and not game.player.doors[side]:
                if game.player.lights[side]:
                    self._door_light(opening)
                    self._draw_enemy(enemy, opening, lit=True)
                else:
                    self._draw_enemy_eyes(opening)
            if game.player.doors[side]:
                self._metal_door(frame)

        # Desk foreground with a CRT, mug, papers and wood-highlight edge.
        desk = [(190, 581), (1090, 581), (1178, 720), (102, 720)]
        pygame.draw.polygon(self.screen, (27, 23, 20), desk)
        pygame.draw.line(self.screen, (104, 79, 54), desk[0], desk[1], 7)
        pygame.draw.line(self.screen, (9, 8, 7), (102,720), (1178,720), 4)
        self._draw_desk()

        # Buttons, HUD and crosshair status.
        self._button(pygame.Rect(24,380,188,72), f"LEFT DOOR\n{'SEALED' if game.player.doors['left'] else 'OPEN'}", game.player.doors['left'], "left_door")
        self._button(pygame.Rect(24,463,188,72), f"LEFT LIGHT\n{'ON' if game.player.lights['left'] else 'OFF'}", game.player.lights['left'], "left_light")
        self._button(pygame.Rect(1068,380,188,72), f"RIGHT DOOR\n{'SEALED' if game.player.doors['right'] else 'OPEN'}", game.player.doors['right'], "right_door")
        self._button(pygame.Rect(1068,463,188,72), f"RIGHT LIGHT\n{'ON' if game.player.lights['right'] else 'OFF'}", game.player.lights['right'], "right_light")
        self._button(pygame.Rect(522,638,236,58), "CAMERAS  [SPACE]", game.cameras.open, "camera")
        self._text(f"{game.clock_label}", self.font, (160, 225, 164), (640, 31), True)
        self._text(f"POWER  {int(game.player.power):02d}%", self.small, (222, 61, 50) if game.player.power < 25 else (207, 207, 193), (25, 24))
        bar = pygame.Rect(25, 52, 210, 12)
        pygame.draw.rect(self.screen, (5, 6, 6), bar)
        pygame.draw.rect(self.screen, (139, 40, 35) if game.player.power < 25 else (111, 163, 102), (bar.x, bar.y, int(bar.w*game.player.power/100), bar.h))
        pygame.draw.rect(self.screen, (135, 136, 128), bar, 1)
        usage = 1 + int(game.cameras.open) + sum(game.player.doors.values()) + sum(game.player.lights.values())
        self._text("USAGE  " + "▮"*usage, self.tiny, (197, 204, 181), (25, 73))
        if game.player.power < 18 and int(time.monotonic()*3) % 2:
            self._text("LOW POWER", self.small, (235, 40, 34), (640, 568), True)

    def _door_light(self, rect: pygame.Rect) -> None:
        # A feathered alpha ellipse softly illuminates only the doorway opening.
        glow = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
        center = (rect.w//2, int(rect.h*.58))
        for radius in range(145, 5, -8):
            alpha = max(1, int(42 * (1 - radius/155)))
            pygame.draw.ellipse(glow, (255, 218, 144, alpha),
                                (center[0]-radius, center[1]-radius*1.15, radius*2, radius*2.3))
        self.screen.blit(glow, rect.topleft)

    def _draw_enemy(self, enemy, rect: pygame.Rect, lit=False) -> None:
        image = self.images.get(enemy.photo)
        if image:
            height = int(rect.h * 1.12)
            width = max(1, int(image.get_width()*height/image.get_height()))
            sprite = pygame.transform.smoothscale(image, (width, height))
            if not lit:
                sprite.fill((20, 20, 22), special_flags=pygame.BLEND_RGB_MULT)
            self.screen.set_clip(rect)
            self.screen.blit(sprite, (rect.centerx-width//2, rect.bottom-height))
            self.screen.set_clip(None)

    def _draw_enemy_eyes(self, rect: pygame.Rect) -> None:
        y = rect.y + rect.h//3
        for x in (rect.centerx-19, rect.centerx+19):
            pygame.draw.circle(self.screen, (83, 0, 0), (x,y), 13)
            pygame.draw.circle(self.screen, (255, 26, 20), (x,y), 4)

    def _metal_door(self, frame: pygame.Rect) -> None:
        pygame.draw.rect(self.screen, (56, 59, 58), frame.inflate(-10,-10))
        for y in range(frame.y+20, frame.bottom-15, 23):
            pygame.draw.line(self.screen, (37, 40, 40), (frame.x+9,y), (frame.right-9,y), 2)
        pygame.draw.line(self.screen, (116, 116, 108), (frame.x+8,frame.y+8), (frame.x+8,frame.bottom-10), 3)
        pygame.draw.circle(self.screen, (145, 119, 73), (frame.centerx, frame.bottom-25), 5)

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
        pygame.draw.rect(self.screen,(59,87,66),feed,2)
        room = game.cameras.current
        self._text(f"CAM {room}  //  {game.room_names.get(room,'UNKNOWN')}", self.small, (138,221,152), (feed.x+20,feed.y+14))
        foxy = next((enemy for enemy in game.enemies if enemy.name == "Foxy"), None)
        if foxy and foxy.running:
            pygame.draw.rect(self.screen, (72, 8, 12), (feed.x+16, feed.bottom-58, feed.w-32, 32))
            self._text("MOTION ALERT  /  DROP TABLET — CLOSE LEFT DOOR", self.tiny, (255,125,103), (feed.centerx,feed.bottom-42), True, False)
        occupants = game.enemies_in_room(room)
        if occupants:
            enemy = occupants[0]
            rect = pygame.Rect(feed.centerx-130,feed.y+120,260,340)
            self._draw_enemy(enemy, rect, lit=True)
            # Dirty chromatic fringe and occasional horizontal tearing.
            pygame.draw.line(self.screen,(100,28,37),(rect.x-8,rect.centery),(rect.right+10,rect.centery),2)
        else:
            self._draw_empty_feed(feed, room)
        if time.monotonic() < game.cameras.glitch_until:
            for _ in range(20):
                gy = random.randrange(feed.y+34,feed.bottom-8)
                gx = random.randrange(feed.x,feed.right-100)
                pygame.draw.rect(self.screen,random.choice(((172,45,49),(48,175,90),(110,125,150))), (gx,gy,random.randrange(25,220),random.randrange(1,5)))
            flash = pygame.Surface((feed.w,feed.h),pygame.SRCALPHA)
            flash.fill((110,144,122,30))
            self.screen.blit(flash,feed.topleft)
        # Right-side room map, with tactile key buttons and enemy indicators.
        self._text("FACILITY MAP",self.tiny,(149,154,142),(990,100))
        for room,(col,row) in ROOM_POS.items():
            rect=pygame.Rect(994+col*68,130+row*64,59,52)
            active=room==game.cameras.current
            pygame.draw.rect(self.screen,(62,35,34) if active else (26,30,28),rect,border_radius=4)
            pygame.draw.rect(self.screen,(171,79,62) if active else (85,96,83),rect,2,border_radius=4)
            self._text(room,self.tiny,(225,225,207) if active else (157,168,151),rect.center,True,False)
            if game.enemies_in_room(room):
                pygame.draw.circle(self.screen,(220,37,31),(rect.right-5,rect.y+5),4)
        self._text("CLICK ROOM TO SWITCH",self.tiny,(128,138,127),(990,424))
        pygame.draw.rect(self.screen,(32,33,31),(990,466,180,42),border_radius=3)
        pygame.draw.rect(self.screen,(120,125,116),(990,466,180,42),1,border_radius=3)
        self._text("SIGNAL  ▮▮▮▮",self.tiny,(143,207,145),(1080,487),True,False)
        pygame.draw.rect(self.screen,(45,32,31),(990,522,180,44),border_radius=3)
        pygame.draw.rect(self.screen,(136,76,60),(990,522,180,44),1,border_radius=3)
        self._text("LOWER TABLET",self.tiny,(210,179,159),(1080,544),True,False)
        self._text("CAMERA SYSTEM  •  LIVE",self.tiny,(122,133,122),(110,615))

    def _draw_empty_feed(self, feed: pygame.Rect, room: str) -> None:
        pygame.draw.rect(self.screen,(16,19,17),feed.inflate(-24,-70))
        # Room dressing varies by feed: party tables, hallway vanishing point, cove curtain.
        inner=feed.inflate(-35,-95)
        if room in ("2A","2B","4A","4B"):
            pygame.draw.polygon(self.screen,(31,32,30),[(inner.x,inner.y),(inner.right,inner.y),(inner.centerx+55,inner.bottom),(inner.centerx-55,inner.bottom)])
            pygame.draw.line(self.screen,(65,67,61),(inner.centerx,inner.y),(inner.centerx,inner.bottom),3)
        elif room == "1C":
            pygame.draw.rect(self.screen,(77,13,24),inner)
            for x in range(inner.x,inner.right,24): pygame.draw.line(self.screen,(101,28,36),(x,inner.y),(x-28,inner.bottom),3)
        else:
            for x in range(inner.x+35,inner.right-25,100):
                pygame.draw.line(self.screen,(63,59,49),(x,inner.y+80),(x,inner.bottom-10),4)
                pygame.draw.circle(self.screen,(108,91,62),(x,inner.y+75),10,2)
        self._text("NO MOTION DETECTED",self.tiny,(104,120,106),(feed.centerx,feed.bottom-30),True)

    def _draw_scare(self, game) -> None:
        elapsed = time.monotonic() - game.scare_started
        if elapsed < 1.45:
            self.screen.fill((3,2,3))
            shake = int(10 + elapsed*15)
            dx,dy=random.randint(-shake,shake),random.randint(-shake,shake)
            size = min(1.45, 0.70 + elapsed*1.1)
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
        self.screen.fill((4,4,5))
        self._draw_wall_and_floor()
        veil=pygame.Surface((WIDTH,HEIGHT),pygame.SRCALPHA)
        veil.fill((0,0,0,220))
        self.screen.blit(veil,(0,0))
        won=game.mode=="won"
        self._text("6:00 AM" if won else "SHIFT TERMINATED",self.title,(195,207,186) if won else (175,33,37),(640,270),True)
        self._text("YOU SURVIVED THE NIGHT" if won else "THEY FOUND YOU",self.font,(198,195,177),(640,342),True)
        rect=pygame.Rect(472,420,336,66)
        self._button(rect,"RESTART NIGHT",False,"restart")
        if int(time.monotonic()*2)%2:
            self._text("CLICK OR PRESS ANY KEY",self.tiny,(123,124,116),(640,528),True)
