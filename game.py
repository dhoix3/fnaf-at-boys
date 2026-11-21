"""Game orchestration, state transitions, input, and frame loop."""
from __future__ import annotations

import math
import time

import pygame

from audio_manager import AudioManager
from entities import Animatronic, CameraSystem, Foxy, Player
from localization import LocalizationManager
from settings import SettingsStore
from ui import HEIGHT, WIDTH, UI


class Game:
    NIGHT_SECONDS = 240.0
    def __init__(self) -> None:
        self.settings_store = SettingsStore()
        self.settings = self.settings_store.values
        self.localization = LocalizationManager(self.settings["language"])
        pygame.display.set_caption(self.localization.get("window_title"))
        flags = pygame.FULLSCREEN if self.settings["fullscreen"] else 0
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT), flags)
        self.clock = pygame.time.Clock()
        self.ui = UI(self.screen)
        self.audio = AudioManager()
        self.audio.set_volume(self.settings["volume"])
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
        self.look_angle = 0.0
        self._mouse_warp_pending = False
        self.door_open_amount = {"left": 0.0, "right": 0.0}
        self.scare_started = 0.0
        self.scare_photo = 1
        self.running = True

    @property
    def clock_label(self) -> str:
        hour = min(6, int(self.night_elapsed / (self.NIGHT_SECONDS / 6)))
        return f"{12 if hour == 0 else hour}:00 {self.localization.get('period_am')}"

    def set_language(self, language: str) -> None:
        self.settings_store.set("language", language)
        self.localization.set_language(self.settings["language"])
        pygame.display.set_caption(self.localization.get("window_title"))

    def set_volume(self, volume: float) -> None:
        self.settings_store.set("volume", volume)
        self.audio.set_volume(self.settings["volume"])

    def set_fullscreen(self, enabled: bool) -> None:
        self.settings_store.set("fullscreen", enabled)
        flags = pygame.FULLSCREEN if self.settings["fullscreen"] else 0
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT), flags)
        self.ui.screen = self.screen

    def save_settings(self) -> None:
        self.settings_store.save()

    def leave_settings(self) -> None:
        self.save_settings()
        self.mode = "menu"
        pygame.event.set_grab(False)
        pygame.mouse.set_visible(True)

    def set_camera_open(self, opened: bool) -> None:
        self.cameras.open = opened
        pygame.event.set_grab(not opened)
        pygame.mouse.set_visible(True)
        if not opened:
            pygame.mouse.set_pos((WIDTH // 2, HEIGHT // 2))
            self._mouse_warp_pending = True
        else:
            self._mouse_warp_pending = False

    def start_night(self) -> None:
        self.mode = "playing"
        pygame.mouse.set_visible(True)
        pygame.event.set_grab(True)
        pygame.mouse.set_pos((WIDTH // 2, HEIGHT // 2))
        self._mouse_warp_pending = True
        self.night_elapsed = 0.0
        self.power_out_at = None
        self.look_angle = 0.0
        self.door_open_amount = {"left": 1.0, "right": 1.0}
        self.player.reset()
        self.cameras.reset()
        for enemy in self.enemies:
            enemy.reset()
        self.audio.play("ambient")

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.QUIT:
            self.running = False
            return
        if event.type == pygame.MOUSEMOTION and self.mode == "playing" and not self.cameras.open:
            if self._mouse_warp_pending and abs(event.pos[0] - WIDTH // 2) <= 3:
                self._mouse_warp_pending = False
                return
            self._mouse_warp_pending = False
            self.look_angle = max(-1.5, min(1.5, self.look_angle + event.rel[0] * 0.0038))
            if event.pos[0] <= 2 or event.pos[0] >= WIDTH - 3:
                pygame.mouse.set_pos((WIDTH // 2, event.pos[1]))
                self._mouse_warp_pending = True
            return
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.mode == "playing" and self.power_out_at is not None:
                return
            if self.mode in ("menu", "settings"):
                self.ui.hit_test(event.pos, self)
                return
            if self.mode in ("dead", "won"):
                self.start_night()
                return
            self.ui.hit_test(event.pos, self)
            return
        if event.type != pygame.KEYDOWN:
            return
        if self.mode == "menu":
            if event.key in (pygame.K_s, pygame.K_F1):
                self.mode = "settings"
            elif event.key == pygame.K_ESCAPE:
                self.running = False
            else:
                self.start_night()
            return
        if self.mode == "settings":
            if event.key == pygame.K_ESCAPE:
                self.leave_settings()
            elif event.key == pygame.K_l:
                self.set_language("ru" if self.localization.language == "en" else "en")
            elif event.key in (pygame.K_LEFT, pygame.K_MINUS):
                self.set_volume(self.settings["volume"] - 0.1)
            elif event.key in (pygame.K_RIGHT, pygame.K_PLUS, pygame.K_EQUALS):
                self.set_volume(self.settings["volume"] + 0.1)
            elif event.key == pygame.K_f:
                self.set_fullscreen(not self.settings["fullscreen"])
            return
        if self.mode in ("dead", "won"):
            self.start_night()
            return
        if self.mode != "playing" or self.power_out_at is not None:
            return
        if event.key == pygame.K_ESCAPE:
            self.set_camera_open(False)
        elif event.key == pygame.K_LEFT:
            self.look_angle = max(-1.5, self.look_angle - 0.08)
        elif event.key == pygame.K_RIGHT:
            self.look_angle = min(1.5, self.look_angle + 0.08)
        elif event.key == pygame.K_SPACE:
            self.set_camera_open(not self.cameras.open)
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
        pygame.event.set_grab(False)
        pygame.mouse.set_visible(True)
        self.audio.stop_ambient()
        self.audio.play("jumpscare")

    def update(self, dt: float) -> None:
        if self.mode == "scare":
            return
        if self.mode != "playing":
            return
        for side in ("left", "right"):
            target = 0.0 if self.player.doors[side] else 1.0
            current = self.door_open_amount[side]
            step = min(1.0, dt / 0.42)
            self.door_open_amount[side] = min(target, current + step) if target > current else max(target, current - step)
        if self.power_out_at is not None:
            if time.monotonic() - self.power_out_at >= 5.0:
                self.trigger_jumpscare("Freddy")
            return

        self.night_elapsed += dt
        if self.night_elapsed >= self.NIGHT_SECONDS:
            self.night_elapsed = self.NIGHT_SECONDS
            self.mode = "won"
            pygame.event.set_grab(False)
            pygame.mouse.set_visible(True)
            self.audio.stop_ambient()
            return

        for enemy in self.enemies:
            enemy.update(dt, self)
            if self.mode != "playing":
                return
        if self.player.drain(dt, self.cameras.open):
            self.player.doors = {"left": False, "right": False}
            self.player.lights = {"left": False, "right": False}
            self.set_camera_open(False)
            self.power_out_at = time.monotonic()

    def run(self) -> None:
        while self.running:
            dt = min(self.clock.tick(60) / 1000.0, 0.05)
            for event in pygame.event.get():
                self.handle_event(event)
            self.update(dt)
            self.ui.draw(self)
        self.save_settings()
        self.audio.close()
