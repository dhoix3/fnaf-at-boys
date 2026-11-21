"""Game orchestration, state transitions, input, and frame loop."""
from __future__ import annotations

import time

import pygame

from audio_manager import AudioManager
from entities import Animatronic, CameraSystem, Foxy, Player
from ui import HEIGHT, WIDTH, UI


class Game:
    NIGHT_SECONDS = 240.0
    room_names = {
        "1A": "MAIN STAGE", "1B": "DINING ROOM", "1C": "PIRATE COVE",
        "2A": "WEST HALL", "2B": "WEST CORNER", "4A": "EAST HALL",
        "4B": "EAST CORNER", "5": "BACKSTAGE", "6": "KITCHEN", "7": "RESTROOMS",
    }

    def __init__(self) -> None:
        pygame.display.set_caption("Five Nights at the Boys' — Night Shift")
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        self.clock = pygame.time.Clock()
        self.ui = UI(self.screen)
        self.audio = AudioManager()
        self.player = Player()
        self.cameras = CameraSystem()
        self.enemies = [
            Animatronic("Freddy", 1, ("1A", "1B", "4A", "4B", "LDoor"), (8.5, 15.0)),
            Animatronic("Bonnie", 2, ("1A", "1B", "2A", "2B", "LDoor"), (5.5, 10.0)),
            Animatronic("Chica", 3, ("1A", "1B", "4A", "4B", "RDoor"), (6.0, 11.0)),
            Foxy(),
        ]
        self.mode = "menu"
        self.night_elapsed = 0.0
        self.power_out_at: float | None = None
        self.scare_started = 0.0
        self.scare_photo = 1
        self.running = True

    @property
    def clock_label(self) -> str:
        hour = min(6, int(self.night_elapsed / (self.NIGHT_SECONDS / 6)))
        return f"{12 if hour == 0 else hour}:00 AM"

    def start_night(self) -> None:
        self.mode = "playing"
        self.night_elapsed = 0.0
        self.power_out_at = None
        self.player.reset()
        self.cameras.reset()
        for enemy in self.enemies:
            enemy.reset()
        self.audio.play("ambient")

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.QUIT:
            self.running = False
            return
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.mode == "playing" and self.power_out_at is not None:
                return
            if self.mode in ("menu", "dead", "won"):
                self.start_night()
                return
            self.ui.hit_test(event.pos, self)
            return
        if event.type != pygame.KEYDOWN:
            return
        if self.mode == "menu":
            if event.key != pygame.K_ESCAPE:
                self.start_night()
            return
        if self.mode in ("dead", "won"):
            self.start_night()
            return
        if self.mode != "playing" or self.power_out_at is not None:
            return
        if event.key == pygame.K_ESCAPE:
            self.cameras.open = False
        elif event.key == pygame.K_SPACE:
            self.cameras.open = not self.cameras.open
        elif event.key in (pygame.K_a, pygame.K_d, pygame.K_q, pygame.K_e) and not self.cameras.open:
            if event.key == pygame.K_a:
                self.toggle_door("left")
            elif event.key == pygame.K_d:
                self.toggle_door("right")
            elif event.key == pygame.K_q:
                self.toggle_light("left")
            elif event.key == pygame.K_e:
                self.toggle_light("right")
        else:
            key_rooms = {
                pygame.K_1: "1A", pygame.K_2: "1B", pygame.K_3: "1C",
                pygame.K_4: "2A", pygame.K_5: "2B", pygame.K_6: "4A",
                pygame.K_7: "4B", pygame.K_8: "5", pygame.K_9: "6", pygame.K_0: "7",
            }
            if self.cameras.open and event.key in key_rooms:
                self.cameras.select(key_rooms[event.key])
                self.audio.play("camera")

    def toggle_door(self, side: str) -> None:
        self.player.doors[side] = not self.player.doors[side]
        self.ui.press(f"{side}_door")
        self.audio.play("door")

    def toggle_light(self, side: str) -> None:
        self.player.lights[side] = not self.player.lights[side]
        self.ui.press(f"{side}_light")

    def enemy_at_door(self, side: str):
        room = "LDoor" if side == "left" else "RDoor"
        return next((enemy for enemy in self.enemies if enemy.room == room), None)

    def enemies_in_room(self, room: str):
        return [enemy for enemy in self.enemies if enemy.room == room]

    def trigger_jumpscare(self, enemy_name: str) -> None:
        if self.mode != "playing":
            return
        enemy = next((item for item in self.enemies if item.name == enemy_name), None)
        self.scare_photo = enemy.photo if enemy else 1
        self.scare_started = time.monotonic()
        self.mode = "scare"
        self.audio.stop_ambient()
        self.audio.play("jumpscare")

    def update(self, dt: float) -> None:
        if self.mode == "scare":
            return
        if self.mode != "playing":
            return
        if self.power_out_at is not None:
            if time.monotonic() - self.power_out_at >= 5.0:
                self.trigger_jumpscare("Freddy")
            return

        self.night_elapsed += dt
        if self.night_elapsed >= self.NIGHT_SECONDS:
            self.night_elapsed = self.NIGHT_SECONDS
            self.mode = "won"
            self.audio.stop_ambient()
            return

        for enemy in self.enemies:
            enemy.update(dt, self)
            if self.mode != "playing":
                return
        if self.player.drain(dt, self.cameras.open):
            self.player.doors = {"left": False, "right": False}
            self.player.lights = {"left": False, "right": False}
            self.cameras.open = False
            self.power_out_at = time.monotonic()

    def run(self) -> None:
        while self.running:
            dt = min(self.clock.tick(60) / 1000.0, 0.05)
            for event in pygame.event.get():
                self.handle_event(event)
            self.update(dt)
            self.ui.draw(self)
        self.audio.close()
