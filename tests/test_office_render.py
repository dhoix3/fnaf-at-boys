import pygame
from office_render import prepare_photo, render_camera, render_office

pygame.init()
pygame.display.set_mode((1, 1))

def test_office_panorama_and_camera_rooms_draw():
    screen = pygame.Surface((1280, 720))
    render_office(screen, -250, {"left": False, "right": True}, {"left": True, "right": False}, {"left": True}, 1.2)
    assert screen.get_at((640, 400)).a == 255
    # Panning can expose only clean black at the viewport edge, never stale pixels.
    render_office(screen, 330)
    assert screen.get_at((0, 0)) == pygame.Color(0, 0, 0, 255)
    # JPEG-dark pixels are cut out, with a drop shadow behind the remaining sprite.
    source = pygame.Surface((20, 20))
    source.fill((38, 38, 38))
    source.set_at((10, 10), (180, 120, 80))
    prepared = prepare_photo(source, (20, 20))
    assert prepared.get_at((0, 0)).a == 0
    assert prepared.get_at((10, 10)).a == 255
    feed = pygame.Surface((850, 518))
    for room in ("1A", "1B", "1C", "2A", "2B", "3", "4A", "4B", "5", "6", "7"):
        render_camera(feed, room)
        assert feed.get_at((10, 10)).a == 255
