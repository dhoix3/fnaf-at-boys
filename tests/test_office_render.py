import pygame
from office_render import render_camera, render_office

pygame.init()

def test_office_panorama_and_camera_rooms_draw():
    screen = pygame.Surface((1280, 720))
    render_office(screen, -250, {"left": False, "right": True}, {"left": True, "right": False}, {"left": True}, 1.2)
    assert screen.get_at((640, 400)).a == 255
    feed = pygame.Surface((850, 518))
    for room in ("1A", "1B", "1C", "2A", "2B", "3", "4A", "4B", "5", "6", "7"):
        render_camera(feed, room)
        assert feed.get_at((10, 10)).a == 255
