import os
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

from renderer3d import OFFICE_MAP, ROOM_CAMERA, Raycaster, Sprite3D, camera_room_world


class RaycastWorldTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.display.init()
        pygame.display.set_mode((2, 2))

    @classmethod
    def tearDownClass(cls):
        pygame.display.quit()

    def test_office_map_is_rectangular_with_two_sliding_door_cells(self):
        widths = {len(row) for row in OFFICE_MAP}
        self.assertEqual(len(widths), 1)
        center_row = OFFICE_MAP[5]
        self.assertEqual(center_row.count("D"), 2)
        self.assertEqual(center_row[12], ".")

    def test_z_buffered_billboard_renders_inside_a_camera_feed(self):
        raycaster = Raycaster((96, 54))
        world, position, angle = camera_room_world("1A")
        portrait = pygame.Surface((16, 24), pygame.SRCALPHA)
        pygame.draw.ellipse(portrait, (220, 30, 24, 255), portrait.get_rect())
        frame = raycaster.render(world, position, angle, [Sprite3D(portrait, 6.5, 4.8, "test")])
        self.assertEqual(frame.get_size(), (96, 54))
        self.assertTrue(all(distance > 0 for distance in raycaster.z_buffer))
        self.assertGreater(frame.get_at((48, 27)).r, 0)

    def test_each_camera_has_a_valid_3d_first_person_pose(self):
        for room in ROOM_CAMERA:
            with self.subTest(room=room):
                world, (x, y), angle = camera_room_world(room)
                self.assertGreater(len(world), 2)
                self.assertTrue(all(len(row) == len(world[0]) for row in world))
                self.assertEqual(world[int(y)][int(x)], ".")
                self.assertIsInstance(angle, float)


if __name__ == "__main__":
    unittest.main()
