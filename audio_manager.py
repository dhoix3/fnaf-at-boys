"""Optional, file-backed sound system with silent, non-fatal fallbacks."""
from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

import pygame


log = logging.getLogger("boys.audio")


def asset_path(relative: str) -> str:
    root = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return str(Path(root) / relative)


class AudioManager:
    FILES = {
        "ambient": ("assets/audio/ventilation.ogg", "assets/audio/ventilation.wav"),
        "door": ("assets/audio/door.wav", "assets/audio/door.ogg"),
        "foxy_steps": ("assets/audio/foxy_steps.ogg", "assets/audio/foxy_steps.wav"),
        "jumpscare": ("assets/audio/jumpscare.ogg", "assets/audio/jumpscare.wav"),
        "camera": ("assets/audio/camera.ogg", "assets/audio/camera.wav"),
    }

    def __init__(self) -> None:
        self.sounds: dict[str, pygame.mixer.Sound] = {}
        self.ready = False
        try:
            if pygame.mixer.get_init() is None:
                pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
            pygame.mixer.set_num_channels(12)
            self.ready = True
        except pygame.error as exc:
            log.warning("Audio disabled; mixer could not initialize: %s", exc)
        if self.ready:
            for name, candidates in self.FILES.items():
                for relative in candidates:
                    path = asset_path(relative)
                    if os.path.isfile(path):
                        try:
                            self.sounds[name] = pygame.mixer.Sound(path)
                            break
                        except (pygame.error, OSError) as exc:
                            log.warning("Could not load audio %s: %s", path, exc)
                if name not in self.sounds:
                    log.warning("Optional audio missing: %s (silent fallback)", candidates[0])
        self.ambient_channel: pygame.mixer.Channel | None = None
        self.active_channels: list[pygame.mixer.Channel] = []
        self.volume = 0.75
        self.set_volume(self.volume)

    def set_volume(self, volume: float) -> None:
        self.volume = max(0.0, min(1.0, float(volume)))
        try:
            pygame.mixer.music.set_volume(self.volume)
            for channel in self.active_channels:
                channel.set_volume(self.volume)
            if self.ambient_channel is not None:
                self.ambient_channel.set_volume(self.volume)
        except pygame.error as exc:
            log.debug("Could not apply master volume: %s", exc)

    def play(self, name: str, loops: int = 0) -> None:
        sound = self.sounds.get(name)
        if sound is None:
            return
        try:
            if name == "ambient":
                if self.ambient_channel is None or not self.ambient_channel.get_busy():
                    self.ambient_channel = sound.play(loops=-1)
                    if self.ambient_channel is not None:
                        self.ambient_channel.set_volume(self.volume)
            else:
                channel = sound.play(loops=loops)
                if channel is not None:
                    channel.set_volume(self.volume)
                    if len(self.active_channels) >= 24:
                        self.active_channels.pop(0)
                    self.active_channels.append(channel)
        except pygame.error as exc:
            log.debug("Audio playback failed (%s): %s", name, exc)

    def stop_ambient(self) -> None:
        if self.ambient_channel is not None:
            self.ambient_channel.fadeout(500)
            self.ambient_channel = None

    def close(self) -> None:
        self.stop_ambient()
