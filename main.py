import pygame
import random
import os
import sys

# Initialize pygame
pygame.init()
pygame.mixer.init(frequency=22050, size=-16, channels=2, buffer=512)

# Constants
WIDTH, HEIGHT = 1280, 720
FPS = 60

# Colors
BLACK = (0, 0, 0)
DARK_GRAY = (30, 30, 30)
GRAY = (50, 50, 50)
METAL = (60, 60, 60)
DARK_RED = (80, 0, 0)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
YELLOW = (255, 255, 0)
WHITE = (255, 255, 255)
DARK_GREEN = (0, 100, 0)
NEON_GREEN = (0, 255, 100)

# Screen setup
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Five Nights at the Boys' — FNaF Parody")
clock = pygame.time.Clock()

# Font
font = pygame.font.SysFont("Courier New", 28, bold=True)
small_font = pygame.font.SysFont("Courier New", 20, bold=True)
tiny_font = pygame.font.SysFont("Courier New", 14, bold=True)

# ------------------------------------------------------------------
# Resource Path (for EXE bundling)
# ------------------------------------------------------------------
def resource_path(relative):
    base_path = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_path, relative)

def load_image(path, size=None, fallback_color=(40, 40, 40), fallback_text="PHOTO"):
    try:
        img = pygame.image.load(resource_path(path)).convert()
        if size:
            img = pygame.transform.scale(img, size)
        return img
    except Exception:
        surf = pygame.Surface(size if size else (200, 200))
        surf.fill(fallback_color)
        text = small_font.render(fallback_text, True, WHITE)
        text_rect = text.get_rect(center=(surf.get_width() // 2, surf.get_height() // 2))
        surf.blit(text, text_rect)
        return surf

# Preload enemy images (small silhouettes 120x250)
ENEMY_IMAGES = {}
for i in range(1, 6):
    ENEMY_IMAGES[i] = load_image(f"assets/photo{i}.jpg", (120, 250), fallback_text=f"PHOTO {i}")

# Jumpscare images (full screen)
JUMPSCARE_IMAGES = {}
for i in range(1, 6):
    JUMPSCARE_IMAGES[i] = load_image(f"assets/photo{i}.jpg", (WIDTH, HEIGHT), fallback_text=f"PHOTO {i}")

office_bg = pygame.Surface((WIDTH, HEIGHT))
for y in range(HEIGHT):
    color_val = max(0, 30 - int(y / HEIGHT * 30))
    pygame.draw.line(office_bg, (color_val, color_val, color_val + 10), (0, y), (WIDTH, y))

# ------------------------------------------------------------------
# Procedural Sound System
# ------------------------------------------------------------------
def generate_tone(freq, duration, volume=0.3, wave_type="square"):
    sample_rate = 22050
    n_samples = int(sample_rate * duration)
    buf = pygame.sndarray.make_surface(None) if False else None
    import array
    samples = array.array('h')
    for i in range(n_samples):
        t = i / sample_rate
        if wave_type == "square":
            val = 1.0 if (t * freq) % 1 < 0.5 else -1.0
        elif wave_type == "sawtooth":
            val = 2.0 * ((t * freq) % 1) - 1.0
        else:
            val = 0.0
        samples.append(int(val * volume * 32767))
    sound = pygame.sndarray.make_sound(samples.reshape(-1, 1) if len(samples) % 2 == 0 else samples)
    return sound

# Simple beep sounds
door_sound = None
light_sound = None
jumpscare_sound = None
powerout_sound = None
foxy_step_sound = None

def init_sounds():
    global door_sound, light_sound, jumpscare_sound, powerout_sound, foxy_step_sound
    try:
        door_sound = generate_tone(80, 0.2, 0.4, "sawtooth")
        light_sound = generate_tone(900, 0.08, 0.15, "square")
        powerout_sound = generate_tone(60, 3.0, 0.3, "sawtooth")
        foxy_step_sound = generate_tone(100, 0.1, 0.25, "square")
    except Exception:
        pass

def play_sound(sound):
    if sound:
        try:
            sound.play()
        except Exception:
            pass

# ------------------------------------------------------------------
# Game State
# ------------------------------------------------------------------
class GameState:
    def __init__(self):
        self.running = True
        self.game_over = False
        self.won = False
        self.jumpscare_active = False
        self.jumpscare_timer = 0
        self.jumpscare_enemy = 1
        self.jumpscare_phase = 0  # 0 = black screen, 1 = show image
        self.power_out = False
        self.power_out_timer = 0

        self.hour = 12
        self.minute = 0

        self.power = 100.0
        self.base_drain = 1.0 / 9.6

        self.door_left = False
        self.door_right = False
        self.light_left = False
        self.light_right = False

        self.camera_open = False
        self.current_cam = "1A"

        self.freddy_pos = "1A"
        self.bonnie_pos = "1A"
        self.chica_pos = "1A"
        self.foxy_pos = "1C"
        self.secret_active = False
        self.secret_timer = 0

        self.foxy_running = False
        self.foxy_last_check = pygame.time.get_ticks()
        self.foxy_run_deadline = 0

        self.bonnie_at_left_door = None
        self.chica_at_right_door = None
        self.freddy_at_left_door = None

        self.ai_timer = 0
        self.ai_interval = 2000

        self.eye_blink_timer = 0
        self.eye_blink_state = False

    def reset(self):
        self.__init__()

# ------------------------------------------------------------------
# Drawing Helpers
# ------------------------------------------------------------------
def draw_glow_text(surface, text, x, y, font_obj, color, glow_color, center=False):
    for offset in range(3, 0, -1):
        glow_surf = font_obj.render(text, True, glow_color)
        rect = glow_surf.get_rect()
        if center:
            rect.center = (x + offset, y + offset)
        else:
            rect.topleft = (x + offset, y + offset)
        surface.blit(glow_surf, rect)
    main_surf = font_obj.render(text, True, color)
    rect = main_surf.get_rect()
    if center:
        rect.center = (x, y)
    else:
        rect.topleft = (x, y)
    surface.blit(main_surf, rect)

def draw_button_panel(surface, rect, text, active=False, font_obj=small_font):
    shadow = pygame.Rect(rect.x + 4, rect.y + 4, rect.w, rect.h)
    pygame.draw.rect(surface, BLACK, shadow, border_radius=6)
    body_color = DARK_RED if active else DARK_GRAY
    pygame.draw.rect(surface, body_color, rect, border_radius=6)
    border_color = RED if active else GRAY
    pygame.draw.rect(surface, border_color, rect, width=3, border_radius=6)
    if active:
        glow = pygame.Rect(rect.x - 2, rect.y - 2, rect.w + 4, rect.h + 4)
        pygame.draw.rect(surface, RED, glow, width=2, border_radius=8)
    lines = text.split("\n")
    total_h = len(lines) * font_obj.get_height()
    start_y = rect.y + (rect.h - total_h) // 2
    for i, line in enumerate(lines):
        t_surf = font_obj.render(line, True, WHITE)
        t_rect = t_surf.get_rect(centerx=rect.centerx, y=start_y + i * font_obj.get_height())
        surface.blit(t_surf, t_rect)

def draw_metal_flap(surface, rect, closed=True):
    pygame.draw.rect(surface, GRAY, rect, width=3, border_radius=2)
    if closed:
        flap = pygame.Rect(rect.x + 3, rect.y + 3, rect.w - 6, rect.h - 6)
        pygame.draw.rect(surface, METAL, flap, border_radius=2)
        for i in range(1, 4):
            lx = rect.x + 3 + i * (rect.w - 6) // 4
            pygame.draw.line(surface, DARK_GRAY, (lx, rect.y + 3), (lx, rect.y + rect.h - 3), 2)
        pygame.draw.line(surface, DARK_GRAY, (rect.x + 5, rect.y + rect.h - 8), (rect.x + rect.w - 5, rect.y + rect.h - 8), 2)

def draw_gradient_rect(surface, rect, color_top, color_bottom, vertical=True):
    if vertical:
        for y in range(rect.height):
            ratio = y / rect.height if rect.height > 0 else 0
            r = int(color_top[0] * (1 - ratio) + color_bottom[0] * ratio)
            g = int(color_top[1] * (1 - ratio) + color_bottom[1] * ratio)
            b = int(color_top[2] * (1 - ratio) + color_bottom[2] * ratio)
            pygame.draw.line(surface, (r, g, b), (rect.x, rect.y + y), (rect.x + rect.width, rect.y + y))

def draw_enemy_silhouette(surface, rect, enemy_id, glow=False, light_level=0.0):
    """Draw enemy as small silhouette with red glowing eyes in darkness"""
    img = ENEMY_IMAGES.get(enemy_id)
    if img:
        # Apply dark filter if light is off
        if light_level < 0.3:
            dark_surf = img.copy()
            dark_surf.fill((10, 10, 10), special_flags=pygame.BLEND_RGB_MULT)
            surface.blit(dark_surf, (rect.x, rect.y))
        else:
            surface.blit(img, (rect.x, rect.y))
    else:
        color = (200, 50, 50) if enemy_id == 1 else (100, 100, 255) if enemy_id == 2 else (255, 200, 50)
        pygame.draw.ellipse(surface, color, (rect.x, rect.y, rect.w // 2, rect.h // 3))
        pygame.draw.rect(surface, color, (rect.x + rect.w // 6, rect.y + rect.h // 3, rect.w * 2 // 3, rect.h - rect.h // 3), border_radius=8)

    # Draw glowing red eyes in darkness
    if light_level < 0.3:
        eye_y = rect.y + rect.h // 4
        eye1_x = rect.x + rect.w // 3
        eye2_x = rect.x + rect.w * 2 // 3
        eye_size = 6 if glow else 4
        # Eye glow
        for r in range(eye_size + 4, eye_size, -1):
            alpha_surf = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
            pygame.draw.circle(alpha_surf, (255, 0, 0, 60 // r), (r, r), r)
            surface.blit(alpha_surf, (eye1_x - r, eye_y - r), special_flags=pygame.BLEND_RGBA_ADD)
            surface.blit(alpha_surf, (eye2_x - r, eye_y - r), special_flags=pygame.BLEND_RGBA_ADD)
        pygame.draw.circle(surface, RED, (eye1_x, eye_y), eye_size)
        pygame.draw.circle(surface, RED, (eye2_x, eye_y), eye_size)

# ------------------------------------------------------------------
# Camera Map Rooms
# ------------------------------------------------------------------
CAM_ROOMS = {
    "1A": {"label": "1A\nSTAGE", "pos": (0, 0)},
    "1B": {"label": "1B\nDINING", "pos": (1, 0)},
    "1C": {"label": "1C\nCOVE", "pos": (2, 0)},
    "2A": {"label": "2A\nWEST", "pos": (0, 1)},
    "2B": {"label": "2B\nCORNER", "pos": (1, 1)},
    "4A": {"label": "4A\nEAST", "pos": (2, 1)},
    "4B": {"label": "4B\nCORNER", "pos": (2, 2)},
    "5":  {"label": "5\nBACK", "pos": (0, 2)},
    "6":  {"label": "6\nKITCHEN", "pos": (1, 2)},
    "7":  {"label": "7\nREST", "pos": (0, 3)},
}

# ------------------------------------------------------------------
# Main Game
# ------------------------------------------------------------------
def main():
    init_sounds()
    state = GameState()

    # Button rects
    btn_w, btn_h = 180, 70
    gap = 20
    left_x = 30
    right_x = WIDTH - btn_w - 30
    door_y = HEIGHT // 2 - btn_h - gap // 2
    light_y = HEIGHT // 2 + gap // 2

    door_left_rect = pygame.Rect(left_x, door_y, btn_w, btn_h)
    light_left_rect = pygame.Rect(left_x, light_y, btn_w, btn_h)
    door_right_rect = pygame.Rect(right_x, door_y, btn_w, btn_h)
    light_right_rect = pygame.Rect(right_x, light_y, btn_w, btn_h)

    cam_btn_w, cam_btn_h = 220, 50
    cam_btn_rect = pygame.Rect((WIDTH - cam_btn_w) // 2, HEIGHT - cam_btn_h - 30, cam_btn_w, cam_btn_h)

    # Door frames
    door_frame_w = 130
    door_frame_h = 220
    left_door_frame = pygame.Rect(WIDTH // 4 - door_frame_w // 2, HEIGHT // 3 - 20, door_frame_w, door_frame_h)
    right_door_frame = pygame.Rect(WIDTH * 3 // 4 - door_frame_w // 2, HEIGHT // 3 - 20, door_frame_w, door_frame_h)

    # Camera map buttons
    cam_map_x = WIDTH - 320
    cam_map_y = HEIGHT - 380
    btn_size = 75
    cam_buttons = {}
    cols = 3
    for i, (cam, info) in enumerate(CAM_ROOMS.items()):
        col = i % cols
        row = i // cols
        bx = cam_map_x + col * (btn_size + 8)
        by = cam_map_y + row * (btn_size + 8)
        cam_buttons[cam] = (pygame.Rect(bx, by, btn_size, btn_size), info["label"])

    secret_next = pygame.time.get_ticks() + random.randint(5000, 15000)

    running = True
    while running:
        clock.tick(FPS)
        now = pygame.time.get_ticks()
        dt = clock.get_time() / 1000.0

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
                break
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                    break
            if event.type == pygame.MOUSEBUTTONDOWN:
                mx, my = pygame.mouse.get_pos()

                if state.jumpscare_active:
                    state.game_over = True
                    state.jumpscare_active = False
                    continue
                if state.game_over or state.won:
                    state.reset()
                    secret_next = now + random.randint(5000, 15000)
                    continue
                if state.power_out:
                    continue

                if door_left_rect.collidepoint(mx, my):
                    state.door_left = not state.door_left
                    play_sound(door_sound)
                if door_right_rect.collidepoint(mx, my):
                    state.door_right = not state.door_right
                    play_sound(door_sound)
                if light_left_rect.collidepoint(mx, my):
                    state.light_left = not state.light_left
                    play_sound(light_sound)
                if light_right_rect.collidepoint(mx, my):
                    state.light_right = not state.light_right
                    play_sound(light_sound)

                if cam_btn_rect.collidepoint(mx, my):
                    state.camera_open = not state.camera_open
                    if state.camera_open:
                        state.current_cam = "1A"
                        if state.foxy_pos == "1C" and state.current_cam == "1C":
                            state.foxy_last_check = now
                            state.foxy_running = False
                            state.foxy_run_deadline = 0

                if state.camera_open:
                    for cam, (rect, label) in cam_buttons.items():
                        if rect.collidepoint(mx, my):
                            state.current_cam = cam
                            if cam == "1C":
                                state.foxy_last_check = now
                                state.foxy_running = False
                                state.foxy_run_deadline = 0
                            if state.secret_active and now - state.secret_timer <= 2000:
                                state.secret_active = False
                            break

        if not running:
            break

        # Game logic updates
        if state.running and not state.power_out and not state.camera_open:
            state.minute += dt * (60.0 / 45.0)
            while state.minute >= 60:
                state.minute -= 60
                state.hour += 1
                if state.hour > 6:
                    state.hour = 6
                    state.won = True
                    state.running = False

            drain = state.base_drain * dt
            if state.door_left:
                drain += 1.0 * dt
            if state.door_right:
                drain += 1.0 * dt
            if state.light_left:
                drain += 1.0 * dt
            if state.light_right:
                drain += 1.0 * dt
            state.power -= drain
            if state.power <= 0:
                state.power = 0
                state.power_out = True
                state.power_out_timer = now
                play_sound(powerout_sound)

            update_ai(state)
            check_threats(state)

            if not state.secret_active and now > secret_next:
                state.secret_active = True
                state.secret_timer = now
                secret_next = now + random.randint(8000, 20000)

            if state.secret_active:
                if now - state.secret_timer > 2000:
                    state.secret_active = False
                    state.jumpscare_active = True
                    state.jumpscare_enemy = 5
                    state.jumpscare_timer = now
                    state.jumpscare_phase = 0
                    state.running = False
                elif state.camera_open:
                    state.secret_active = False

        elif state.power_out:
            if now - state.power_out_timer > 5000:
                state.jumpscare_active = True
                state.jumpscare_enemy = 1
                state.jumpscare_timer = now
                state.jumpscare_phase = 0
                state.running = False

        # Jumpscare phase timing
        if state.jumpscare_active:
            elapsed = now - state.jumpscare_timer
            if elapsed >= 500 and state.jumpscare_phase == 0:
                state.jumpscare_phase = 1

        # Draw office background
        screen.fill(DARK_GRAY)

        # Back wall with gradient
        back_wall_rect = pygame.Rect(int(WIDTH * 0.42), int(HEIGHT * 0.25), int(WIDTH * 0.16), int(HEIGHT * 0.37))
        draw_gradient_rect(screen, back_wall_rect, (20, 20, 25), (10, 10, 10))

        # Left wall with perspective
        left_wall = [
            (0, int(HEIGHT * 0.25)),
            (0, HEIGHT),
            (int(WIDTH * 0.42), int(HEIGHT * 0.62)),
            (int(WIDTH * 0.42), int(HEIGHT * 0.25)),
        ]
        pygame.draw.polygon(screen, (25, 25, 30), left_wall)

        # Right wall with perspective
        right_wall = [
            (WIDTH, int(HEIGHT * 0.25)),
            (WIDTH, HEIGHT),
            (int(WIDTH * 0.58), int(HEIGHT * 0.62)),
            (int(WIDTH * 0.58), int(HEIGHT * 0.25)),
        ]
        pygame.draw.polygon(screen, (25, 25, 30), right_wall)

        # Floor
        floor = [
            (0, HEIGHT),
            (WIDTH, HEIGHT),
            (int(WIDTH * 0.58), int(HEIGHT * 0.62)),
            (int(WIDTH * 0.42), int(HEIGHT * 0.62)),
        ]
        pygame.draw.polygon(screen, (15, 15, 15), floor)

        # Guard desk
        desk_top_w = WIDTH * 0.7
        desk_top_h = HEIGHT * 0.22
        desk_top_y = HEIGHT - desk_top_h
        desk = [
            (int(WIDTH * 0.15 - desk_top_w * 0.1), desk_top_y),
            (int(WIDTH * 0.85 + desk_top_w * 0.1), desk_top_y),
            (int(WIDTH * 0.85), HEIGHT),
            (int(WIDTH * 0.15), HEIGHT),
        ]
        pygame.draw.polygon(screen, (35, 35, 35), desk)
        pygame.draw.polygon(screen, (55, 55, 55), desk, width=3)

        # Door frames
        pygame.draw.rect(screen, GRAY, left_door_frame, width=3, border_radius=2)
        pygame.draw.rect(screen, BLACK, (left_door_frame.x + 3, left_door_frame.y + 3, left_door_frame.w - 6, left_door_frame.h - 6))
        pygame.draw.rect(screen, GRAY, right_door_frame, width=3, border_radius=2)
        pygame.draw.rect(screen, BLACK, (right_door_frame.x + 3, right_door_frame.y + 3, right_door_frame.w - 6, right_door_frame.h - 6))

        # Light rendering (bright yellowish-white cones)
        if state.light_left:
            light_rect = pygame.Rect(0, int(HEIGHT * 0.25), int(WIDTH * 0.4), int(HEIGHT * 0.5))
            light_surf = pygame.Surface((light_rect.w, light_rect.h), pygame.SRCALPHA)
            light_surf.fill((255, 255, 200, 60))
            screen.blit(light_surf, (light_rect.x, light_rect.y))
        if state.light_right:
            light_rect = pygame.Rect(int(WIDTH * 0.6), int(HEIGHT * 0.25), int(WIDTH * 0.4), int(HEIGHT * 0.5))
            light_surf = pygame.Surface((light_rect.w, light_rect.h), pygame.SRCALPHA)
            light_surf.fill((255, 255, 200, 60))
            screen.blit(light_surf, (light_rect.x, light_rect.y))

        # Enemies in doorways
        left_light_level = 1.0 if state.light_left else 0.1
        right_light_level = 1.0 if state.light_right else 0.1

        if not state.door_left:
            if state.bonnie_pos == "LDoor":
                draw_enemy_silhouette(screen, left_door_frame, 2, glow=True, light_level=left_light_level)
            elif state.freddy_pos == "LDoor":
                draw_enemy_silhouette(screen, left_door_frame, 1, glow=True, light_level=left_light_level)
        else:
            draw_metal_flap(screen, left_door_frame, closed=True)

        if not state.door_right:
            if state.chica_pos == "RDoor":
                draw_enemy_silhouette(screen, right_door_frame, 3, glow=True, light_level=right_light_level)
        else:
            draw_metal_flap(screen, right_door_frame, closed=True)

        if state.secret_active:
            sec_rect = pygame.Rect(WIDTH // 2 - 100, HEIGHT // 2 - 120, 200, 240)
            draw_enemy_silhouette(screen, sec_rect, 5, glow=True, light_level=0.1)

        # Power meter
        draw_glow_text(screen, "POWER", 25, 15, small_font, RED, DARK_RED)
        pb_x, pb_y = 25, 50
        pb_w, pb_h = 220, 20
        pygame.draw.rect(screen, BLACK, (pb_x, pb_y, pb_w, pb_h))
        pygame.draw.rect(screen, WHITE, (pb_x, pb_y, pb_w, pb_h), width=2)
        fill_w = int((state.power / 100.0) * (pb_w - 4))
        if fill_w > 0:
            pcolor = YELLOW if state.power < 30 else RED
            pygame.draw.rect(screen, pcolor, (pb_x + 2, pb_y + 2, fill_w, pb_h - 4))
        draw_glow_text(screen, f"{int(state.power)}%", pb_x + pb_w + 8, pb_y - 2, small_font, WHITE, BLACK)

        # Time
        time_str = f"{state.hour}:{int(state.minute):02d} AM"
        draw_glow_text(screen, time_str, WIDTH // 2, 25, font, GREEN, DARK_GREEN, center=True)

        # Buttons
        draw_button_panel(screen, door_left_rect, f"L DOOR\n{'CLOSED' if state.door_left else 'OPEN'}", active=state.door_left)
        draw_button_panel(screen, light_left_rect, f"L LIGHT\n{'ON' if state.light_left else 'OFF'}", active=state.light_left)
        draw_button_panel(screen, door_right_rect, f"R DOOR\n{'CLOSED' if state.door_right else 'OPEN'}", active=state.door_right)
        draw_button_panel(screen, light_right_rect, f"R LIGHT\n{'ON' if state.light_right else 'OFF'}", active=state.light_right)
        draw_button_panel(screen, cam_btn_rect, f"CAMERA\n{'ON' if state.camera_open else 'OFF'}", active=state.camera_open, font_obj=font)

        if state.power < 20:
            draw_glow_text(screen, "LOW POWER", WIDTH // 2, HEIGHT - 90, font, RED, DARK_RED, center=True)

        if state.power_out:
            overlay = pygame.Surface((WIDTH, HEIGHT))
            overlay.fill(BLACK)
            overlay.set_alpha(200)
            screen.blit(overlay, (0, 0))
            draw_glow_text(screen, "POWER OUT", WIDTH // 2, HEIGHT // 2, font, RED, DARK_RED, center=True)

        if state.camera_open:
            tablet_w, tablet_h = 950, 700
            tablet_x = (WIDTH - tablet_w) // 2
            tablet_y = (HEIGHT - tablet_h) // 2
            tablet_rect = pygame.Rect(tablet_x, tablet_y, tablet_w, tablet_h)
            pygame.draw.rect(screen, GRAY, tablet_rect, border_radius=18)
            pygame.draw.rect(screen, WHITE, tablet_rect, width=4, border_radius=18)

            screen_pad = 20
            feed_rect = pygame.Rect(tablet_x + screen_pad, tablet_y + screen_pad, tablet_w - 2 * screen_pad, tablet_h - 2 * screen_pad - 100)
            pygame.draw.rect(screen, BLACK, feed_rect)
            pygame.draw.rect(screen, GREEN, feed_rect, width=3)

            feed_inner = pygame.Rect(feed_rect.x + 5, feed_rect.y + 5, feed_rect.w - 10, feed_rect.h - 10)
            cam_label = ""
            enemy_in_cam = None

            if state.current_cam == "1A":
                cam_label = "CAM 1A - STAGE"
                if state.freddy_pos == "1A":
                    enemy_in_cam = 1
                elif state.bonnie_pos == "1A":
                    enemy_in_cam = 2
            elif state.current_cam == "1B":
                cam_label = "CAM 1B - DINING"
                if state.freddy_pos == "1B":
                    enemy_in_cam = 1
                elif state.bonnie_pos == "1B":
                    enemy_in_cam = 2
            elif state.current_cam == "1C":
                cam_label = "CAM 1C - PIRATE COVE"
                if state.foxy_pos == "1C":
                    enemy_in_cam = 4
            elif state.current_cam == "2A":
                cam_label = "CAM 2A - WEST HALL"
                if state.bonnie_pos == "2A":
                    enemy_in_cam = 2
                elif state.freddy_pos == "2A":
                    enemy_in_cam = 1
                elif state.foxy_running and state.foxy_pos == "2A":
                    enemy_in_cam = 4
            elif state.current_cam == "2B":
                cam_label = "CAM 2B - W. HALL CORNER"
                if state.bonnie_pos == "2B":
                    enemy_in_cam = 2
                elif state.freddy_pos == "2B":
                    enemy_in_cam = 1
                elif state.foxy_running and state.foxy_pos == "2B":
                    enemy_in_cam = 4
            elif state.current_cam == "4A":
                cam_label = "CAM 4A - EAST HALL"
                if state.chica_pos == "4A":
                    enemy_in_cam = 3
                elif state.freddy_pos == "4A":
                    enemy_in_cam = 1
            elif state.current_cam == "4B":
                cam_label = "CAM 4B - E. HALL CORNER"
                if state.chica_pos == "4B":
                    enemy_in_cam = 3
                elif state.freddy_pos == "4B":
                    enemy_in_cam = 1
            elif state.current_cam == "5":
                cam_label = "CAM 5 - BACKSTAGE"
                if state.bonnie_pos == "5":
                    enemy_in_cam = 2
            elif state.current_cam == "6":
                cam_label = "CAM 6 - KITCHEN"
                if state.chica_pos == "6":
                    enemy_in_cam = 3
                elif state.freddy_pos == "6":
                    enemy_in_cam = 1
            elif state.current_cam == "7":
                cam_label = "CAM 7 - RESTROOMS"
                if state.freddy_pos == "7":
                    enemy_in_cam = 1

            draw_glow_text(screen, cam_label, feed_inner.x + 10, feed_inner.y + 10, small_font, GREEN, DARK_GREEN)

            if enemy_in_cam:
                enemy_rect = pygame.Rect(feed_inner.centerx - 60, feed_inner.centery - 125, 120, 250)
                draw_enemy_silhouette(screen, enemy_rect, enemy_in_cam, glow=True, light_level=0.3)
                # VHS noise overlay on enemy
                noise = pygame.Surface((120, 250), pygame.SRCALPHA)
                for _ in range(200):
                    nx = random.randint(0, 119)
                    ny = random.randint(0, 249)
                    pygame.draw.rect(noise, (255, 0, 0, 50), (nx, ny, 1, 1))
                screen.blit(noise, (enemy_rect.x, enemy_rect.y), special_flags=pygame.BLEND_RGBA_ADD)
            else:
                noise = pygame.Surface((feed_inner.w, feed_inner.h), pygame.SRCALPHA)
                for _ in range(800):
                    nx = random.randint(0, feed_inner.w - 1)
                    ny = random.randint(0, feed_inner.h - 1)
                    c = random.randint(0, 60)
                    pygame.draw.rect(noise, (c, c, c, 60), (nx, ny, 1, 1))
                screen.blit(noise, (feed_inner.x, feed_inner.y), special_flags=pygame.BLEND_RGBA_ADD)

            # Camera map grid
            map_rect = pygame.Rect(tablet_x + tablet_w - 310, tablet_y + tablet_h - 120, 290, 100)
            pygame.draw.rect(screen, DARK_GRAY, map_rect, border_radius=6)
            pygame.draw.rect(screen, GRAY, map_rect, width=2, border_radius=6)

            map_origin_x = map_rect.x + 10
            map_origin_y = map_rect.y + 10
            cell_w = 24
            cell_h = 20

            connections = [
                ("1A", "1B"), ("1B", "1C"),
                ("1A", "2A"), ("1B", "2B"), ("1C", "4A"),
                ("2A", "2B"), ("2B", "4B"), ("4A", "4B"),
                ("5", "6"), ("6", "7"),
            ]
            for c1, c2 in connections:
                if c1 in CAM_ROOMS and c2 in CAM_ROOMS:
                    r1 = CAM_ROOMS[c1]["pos"]
                    r2 = CAM_ROOMS[c2]["pos"]
                    x1 = map_origin_x + r1[0] * (cell_w + 4) + cell_w // 2
                    y1 = map_origin_y + r1[1] * (cell_h + 4) + cell_h // 2
                    x2 = map_origin_x + r2[0] * (cell_w + 4) + cell_w // 2
                    y2 = map_origin_y + r2[1] * (cell_h + 4) + cell_h // 2
                    pygame.draw.line(screen, GRAY, (x1, y1), (x2, y2), 2)

            for cam, (rect, label) in cam_buttons.items():
                active = (state.current_cam == cam)
                room_color = RED if active else GRAY
                has_enemy = False
                if cam == "1A" and (state.freddy_pos == "1A" or state.bonnie_pos == "1A"):
                    has_enemy = True
                elif cam == "1B" and (state.freddy_pos == "1B" or state.bonnie_pos == "1B"):
                    has_enemy = True
                elif cam == "1C" and state.foxy_pos == "1C":
                    has_enemy = True
                elif cam == "2A" and (state.bonnie_pos == "2A" or state.freddy_pos == "2A" or (state.foxy_running and state.foxy_pos == "2A")):
                    has_enemy = True
                elif cam == "2B" and (state.bonnie_pos == "2B" or state.freddy_pos == "2B" or (state.foxy_running and state.foxy_pos == "2B")):
                    has_enemy = True
                elif cam == "4A" and (state.chica_pos == "4A" or state.freddy_pos == "4A"):
                    has_enemy = True
                elif cam == "4B" and (state.chica_pos == "4B" or state.freddy_pos == "4B"):
                    has_enemy = True
                elif cam == "5" and state.bonnie_pos == "5":
                    has_enemy = True
                elif cam == "6" and (state.chica_pos == "6" or state.freddy_pos == "6"):
                    has_enemy = True
                elif cam == "7" and state.freddy_pos == "7":
                    has_enemy = True

                if has_enemy:
                    room_color = (255, 50, 50)
                pygame.draw.rect(screen, room_color, rect, border_radius=4)
                pygame.draw.rect(screen, WHITE if active else DARK_GRAY, rect, width=2, border_radius=4)
                lines = label.split("\n")
                for i, line in enumerate(lines):
                    t_surf = tiny_font.render(line, True, WHITE)
                    t_rect = t_surf.get_rect(center=rect.center, y=rect.y + 4 + i * tiny_font.get_height())
                    screen.blit(t_surf, t_rect)

        # Jumpscare
        if state.jumpscare_active:
            js_overlay = pygame.Surface((WIDTH, HEIGHT))
            js_overlay.fill(BLACK)
            screen.blit(js_overlay, (0, 0))

            elapsed = now - state.jumpscare_timer

            if state.jumpscare_phase == 0 and elapsed < 500:
                # Phase 1: Black screen, silence
                pass
            else:
                # Phase 2: Show jumpscare with zoom and shake
                enemy_id = state.jumpscare_enemy
                size = int(400 + (elapsed - 500) * 0.5)
                if size > WIDTH:
                    size = WIDTH
                center_x, center_y = WIDTH // 2, HEIGHT // 2
                js_rect = pygame.Rect(center_x - size // 2, center_y - size // 2, size, size)
                draw_enemy_silhouette(screen, js_rect, enemy_id, glow=True, light_level=1.0)

                # Red flash
                if (elapsed // 80) % 2 == 0:
                    flash = pygame.Surface((WIDTH, HEIGHT))
                    flash.fill(RED)
                    flash.set_alpha(120)
                    screen.blit(flash, (0, 0))

                draw_glow_text(screen, "HE'S HERE", center_x, center_y + size // 2 + 40, font, RED, DARK_RED, center=True)

        # Game Over / Win
        if state.game_over or state.won:
            overlay = pygame.Surface((WIDTH, HEIGHT))
            overlay.fill(BLACK)
            overlay.set_alpha(210)
            screen.blit(overlay, (0, 0))

            if state.won:
                draw_glow_text(screen, "6:00 AM", WIDTH // 2, HEIGHT // 2 - 50, font, GREEN, DARK_GREEN, center=True)
                draw_glow_text(screen, "YOU SURVIVED THE NIGHT", WIDTH // 2, HEIGHT // 2 + 20, font, WHITE, BLACK, center=True)
            else:
                draw_glow_text(screen, "GAME OVER", WIDTH // 2, HEIGHT // 2 - 50, font, RED, DARK_RED, center=True)
                draw_glow_text(screen, "HE GOT YOU", WIDTH // 2, HEIGHT // 2 + 20, font, WHITE, BLACK, center=True)

            draw_glow_text(screen, "Click to restart", WIDTH // 2, HEIGHT // 2 + 90, small_font, WHITE, BLACK, center=True)

        pygame.display.flip()

    pygame.quit()
    sys.exit()

def update_ai(state):
    now = pygame.time.get_ticks()
    if now - state.ai_timer < state.ai_interval:
        return
    state.ai_timer = now

    roll = random.random()

    # Freddy: Moves ONLY when camera is open OR closed (freezes when watching him on cam)
    if state.freddy_pos != "LDoor" and state.freddy_pos != "office":
        watching_freddy = state.camera_open and state.current_cam == state.freddy_pos
        if not watching_freddy:
            if state.freddy_pos == "1A" and roll < 0.25:
                state.freddy_pos = "1B"
            elif state.freddy_pos == "1B" and roll < 0.25:
                state.freddy_pos = random.choice(["2A", "4A"])
            elif (state.freddy_pos in ("2A", "4A")) and roll < 0.2:
                state.freddy_pos = "LDoor"
                state.freddy_at_left_door = now

    # Bonnie
    if state.bonnie_pos != "LDoor":
        if state.bonnie_pos == "1A" and roll < 0.35:
            state.bonnie_pos = "2A"
        elif state.bonnie_pos == "2A" and roll < 0.35:
            state.bonnie_pos = "LDoor"
            state.bonnie_at_left_door = now

    # Chica
    if state.chica_pos != "RDoor":
        if state.chica_pos == "4A" and roll < 0.35:
            state.chica_pos = "RDoor"
            state.chica_at_right_door = now

    # Foxy
    if state.foxy_pos == "1C" and not state.foxy_running and not state.foxy_run_deadline:
        if now - state.foxy_last_check > 15000:
            state.foxy_running = True
            state.foxy_run_deadline = now + 1500
            play_sound(foxy_step_sound)
    elif state.foxy_running and state.foxy_pos == "1C":
        state.foxy_pos = "2A"
    elif state.foxy_running and state.foxy_pos == "2A":
        state.foxy_pos = "2B"
    elif state.foxy_running and state.foxy_pos == "2B":
        state.foxy_pos = "LDoor"

def check_threats(state):
    now = pygame.time.get_ticks()

    if state.bonnie_pos == "LDoor" and not state.door_left:
        if state.bonnie_at_left_door is None:
            state.bonnie_at_left_door = now
        threat_time = 3000 + random.randint(0, 2000)
        if now - state.bonnie_at_left_door >= threat_time:
            trigger_jumpscare(state, 2)
    else:
        state.bonnie_at_left_door = None

    if state.chica_pos == "RDoor" and not state.door_right:
        if state.chica_at_right_door is None:
            state.chica_at_right_door = now
        threat_time = 3000 + random.randint(0, 2000)
        if now - state.chica_at_right_door >= threat_time:
            trigger_jumpscare(state, 3)
    else:
        state.chica_at_right_door = None

    if state.freddy_pos == "LDoor" and not state.door_left:
        if state.freddy_at_left_door is None:
            state.freddy_at_left_door = now
        if now - state.freddy_at_left_door >= 5000:
            trigger_jumpscare(state, 1)
    else:
        state.freddy_at_left_door = None

    if state.foxy_running and state.foxy_run_deadline > 0:
        if state.door_left:
            state.foxy_running = False
            state.foxy_run_deadline = 0
            state.foxy_pos = "1C"
            state.foxy_last_check = now
            state.power = max(0, state.power - 5)
        elif now >= state.foxy_run_deadline:
            state.foxy_running = False
            state.foxy_run_deadline = 0
            trigger_jumpscare(state, 4)

def trigger_jumpscare(state, enemy_id):
    state.jumpscare_active = True
    state.jumpscare_enemy = enemy_id
    state.jumpscare_timer = pygame.time.get_ticks()
    state.jumpscare_phase = 0
    state.running = False

if __name__ == "__main__":
    main()
