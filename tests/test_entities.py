import unittest
from unittest.mock import patch

from entities import Animatronic, CameraSystem, Player


class EntityTests(unittest.TestCase):
    def test_power_base_and_active_loads(self):
        player = Player()
        player.drain(10.0, camera_open=False)
        self.assertAlmostEqual(player.power, 97.5)

        player = Player()
        player.doors["left"] = True
        player.lights["right"] = True
        player.drain(2.0, camera_open=True)
        self.assertAlmostEqual(player.power, 95.7)

    def test_camera_selection_triggers_short_glitch_and_foxy_check(self):
        camera = CameraSystem()
        before = camera.foxy_last_check
        camera.select("2A")
        self.assertGreater(camera.glitch_until, 0)
        self.assertEqual(camera.current, "2A")
        self.assertEqual(camera.foxy_last_check, before)
        camera.select("1C")
        self.assertGreaterEqual(camera.foxy_last_check, before)

    def test_freddy_only_moves_while_player_watches_another_camera(self):
        enemy = Animatronic("Freddy", 1, ("1A", "1B", "4A", "LDoor"), (8, 10))

        class FakeGame:
            player = Player()
            cameras = type("Cameras", (), {"open": False, "current": "1B"})()

        enemy.next_move = 0
        enemy.update(0, FakeGame())
        self.assertEqual(enemy.room, "1A")

        FakeGame.cameras.open = True
        FakeGame.cameras.current = "1B"
        enemy.next_move = 0
        with patch("entities.random.random", return_value=0.0), patch("entities.random.uniform", return_value=9.0):
            enemy.update(0, FakeGame())
        self.assertEqual(enemy.room, "1B")


if __name__ == "__main__":
    unittest.main()
