"""Night mechanics: office controls, camera system, and autonomous enemies."""
from __future__ import annotations

import random
import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from game import Game


@dataclass
class Player:
    doors: dict[str, bool] = field(default_factory=lambda: {"left": False, "right": False})
    lights: dict[str, bool] = field(default_factory=lambda: {"left": False, "right": False})
    power: float = 100.0

    def reset(self) -> None:
        self.doors = {"left": False, "right": False}
        self.lights = {"left": False, "right": False}
        self.power = 100.0

    def drain(self, dt: float, camera_open: bool) -> bool:
        # A full night lasts about four minutes with careful energy use.
        rate = 0.25 + (0.20 if camera_open else 0.0)
        rate += sum(0.95 for closed in self.doors.values() if closed)
        rate += sum(0.75 for on in self.lights.values() if on)
        self.power = max(0.0, self.power - rate * dt)
        return self.power <= 0.0


class CameraSystem:
    ROOMS = ("1A", "1B", "1C", "2A", "2B", "4A", "4B", "5", "6", "7")

    def __init__(self) -> None:
        self.open = False
        self.current = "1A"
        self.glitch_until = 0.0
        self.foxy_last_check = time.monotonic()

    def select(self, room: str) -> None:
        if room not in self.ROOMS:
            return
        if room != self.current:
            self.current = room
            self.glitch_until = time.monotonic() + 0.2
        if room == "1C":
            self.foxy_last_check = time.monotonic()

    def reset(self) -> None:
        self.open = False
        self.current = "1A"
        self.glitch_until = 0.0
        self.foxy_last_check = time.monotonic()


class Animatronic:
    """A route-driven threat with per-enemy pacing and door behavior."""

    ROUTES = {
        "Bonnie": ("1A", "1B", "2A", "2B", "LDoor"),
        "Chica": ("1A", "1B", "4A", "4B", "RDoor"),
        "Freddy": ("1A", "1B", "4A", "4B", "LDoor"),
    }

    def __init__(self, name: str, photo: int, route: tuple[str, ...], interval: tuple[float, float]):
        self.name = name
        self.photo = photo
        self.route = route
        self.interval = interval
        self.room = route[0]
        self.next_move = random.uniform(*interval)
        self.at_door_since: float | None = None
        self.retreat_at = 0.0

    def reset(self) -> None:
        self.room = self.route[0]
        self.next_move = random.uniform(*self.interval)
        self.at_door_since = None
        self.retreat_at = 0.0

    def update(self, dt: float, game: "Game") -> None:
        self.next_move -= dt
        if self.room in ("LDoor", "RDoor"):
            self._handle_door(game)
            return
        if self.next_move > 0:
            return

        if self.name == "Freddy":
            # Freddy advances only while the player watches a different feed.
            distracted = game.cameras.open and game.cameras.current != self.room
            if distracted and random.random() < 0.62:
                self._advance()
        else:
            # Bonnie and Chica use irregular teleports between route nodes.
            if random.random() < (0.68 if self.name == "Bonnie" else 0.60):
                jump = random.choice((1, 2))
                self._advance(jump)
        self.next_move = random.uniform(*self.interval)

    def _advance(self, jump: int = 1) -> None:
        try:
            index = self.route.index(self.room)
        except ValueError:
            index = 0
        self.room = self.route[min(index + jump, len(self.route) - 1)]
        if self.room.endswith("Door"):
            self.at_door_since = time.monotonic()

    def _handle_door(self, game: "Game") -> None:
        side = "left" if self.room == "LDoor" else "right"
        now = time.monotonic()
        if game.player.doors[side]:
            if not self.retreat_at:
                self.retreat_at = now + random.uniform(1.1, 2.4)
            if now >= self.retreat_at:
                self.room = self.route[max(0, len(self.route) - 3)]
                self.at_door_since = None
                self.retreat_at = 0.0
                self.next_move = random.uniform(*self.interval)
            return
        self.retreat_at = 0.0
        if self.at_door_since is None:
            self.at_door_since = now
        reaction = 4.2 if self.name == "Freddy" else 3.4
        if now - self.at_door_since >= reaction:
            game.trigger_jumpscare(self.name)


class Foxy(Animatronic):
    def __init__(self) -> None:
        super().__init__("Foxy", 4, ("1C", "2A", "2B", "LDoor"), (99, 99))
        self.running = False
        self.deadline = 0.0

    def reset(self) -> None:
        super().reset()
        self.room = "1C"
        self.running = False
        self.deadline = 0.0

    def update(self, dt: float, game: "Game") -> None:
        now = time.monotonic()
        if not self.running and self.room == "1C" and now - game.cameras.foxy_last_check > 14.0:
            self.running = True
            self.deadline = now + 2.0
            game.audio.play("foxy_steps")
        if not self.running:
            return
        if game.player.doors["left"]:
            self.running = False
            self.room = "1C"
            self.deadline = 0.0
            game.cameras.foxy_last_check = now
            game.player.power = max(0.0, game.player.power - 5.0)
        elif now >= self.deadline:
            game.trigger_jumpscare("Foxy")

    def _advance(self, jump: int = 1) -> None:
        return
