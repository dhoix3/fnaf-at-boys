"""Painterly 2.5D office and camera-room scenes built from native Pygame shapes."""
import math
import pygame

W, H = 1280, 720

def prepare_photo(image, size=(160, 240)):
    """Downsample supplied portraits and make near-black backgrounds transparent."""
    sprite = pygame.transform.smoothscale(image, size).convert_alpha()
    key = sprite.map_rgb((0, 0, 0, 0))
    pixels = pygame.PixelArray(sprite)
    for x in range(sprite.get_width()):
        for y in range(sprite.get_height()):
            c = sprite.unmap_rgb(pixels[x, y])
            if max(c.r, c.g, c.b) <= 38:
                pixels[x, y] = key
    del pixels
    # A tiny dropped silhouette masks JPEG edge chatter against dark scenes.
    mask = pygame.mask.from_surface(sprite)
    shadow = mask.to_surface(setcolor=(0, 0, 0, 165), unsetcolor=(0, 0, 0, 0))
    shadow.set_colorkey((0, 0, 0))
    composed = pygame.Surface(sprite.get_size(), pygame.SRCALPHA)
    composed.blit(shadow, (2, 2))
    composed.blit(sprite, (0, 0))
    return composed

def _poly(dst, color, pts): pygame.draw.polygon(dst, color, pts)

def render_office(dst, offset=0.0, doors=None, lights=None, intruders=None, fan_phase=0.0, images=None):
    """Draw a fixed-width office panorama; offset pans between left, center and right."""
    offset = max(-330, min(330, int(offset)))
    s = pygame.Surface((W, H))
    s.fill((16, 17, 18))
    pygame.draw.rect(s, (38, 39, 37), (0, 0, W, 488))
    # wall panels and dim overhead pool
    pygame.draw.rect(s, (47, 47, 43), (0, 80, W, 356))
    for x in range(30, W, 140):
        pygame.draw.line(s, (39, 40, 37), (x, 80), (x, 436), 3)
    pygame.draw.polygon(s, (57, 55, 46), [(500,0),(780,0),(940,480),(340,480)])
    # hallway doors and deep black openings
    for side, x in (("left", 55), ("right", 1035)):
        pygame.draw.rect(s, (20, 20, 19), (x, 145, 190, 330))
        pygame.draw.rect(s, (92, 82, 65), (x-10, 135, 210, 24))
        pygame.draw.rect(s, (80, 72, 59), (x-10, 455, 210, 20))
        if lights and lights.get(side):
            glow = pygame.Surface((190, 320), pygame.SRCALPHA); glow.fill((230, 179, 78, 72)); s.blit(glow,(x,150))
            pygame.draw.polygon(s,(115,96,62),[(x+30,150),(x+160,150),(x+185,460),(x+5,460)])
        if doors and doors.get(side):
            pygame.draw.rect(s,(63,66,64),(x-4,145,198,320)); pygame.draw.line(s,(113,112,99),(x+20,155),(x+20,460),3)
        enemy_photo = (intruders or {}).get(side)
        if enemy_photo and not (doors and doors.get(side)):
            opening = pygame.Rect(x, 145, 190, 330)
            if lights and lights.get(side):
                photo = (images or {}).get(enemy_photo)
                if photo:
                    # Crop the portrait to the doorway; retain its natural colors.
                    portrait = pygame.transform.smoothscale(photo, (opening.w, opening.h))
                    s.set_clip(opening)
                    s.blit(portrait, opening.topleft)
                    s.set_clip(None)
            else:
                # Unlit doorway: absolute silhouette black with only visible eye-shine.
                pygame.draw.rect(s, (0, 0, 0), opening)
                eye_y = 262
                for eye_x in (x + 70, x + 120):
                    pygame.draw.circle(s, (110, 0, 0), (eye_x, eye_y), 11)
                    pygame.draw.circle(s, (255, 18, 12), (eye_x, eye_y), 6)
    # posters, drawings and vent grilles
    for x, c in ((342,(100,76,55)),(770,(75,72,61))):
        pygame.draw.rect(s,(83,77,64),(x,118,110,142)); pygame.draw.rect(s,c,(x+8,126,94,126))
        pygame.draw.circle(s,(192,171,115),(x+55,169),25); pygame.draw.circle(s,(25,24,22),(x+46,164),4); pygame.draw.circle(s,(25,24,22),(x+64,164),4)
    for x in (500, 735):
        pygame.draw.rect(s,(26,28,28),(x,92,74,36));
        for xx in range(x+6,x+70,9): pygame.draw.line(s,(93,97,91),(xx,97),(xx,123),2)
    pygame.draw.rect(s,(28,24,21),(0,0,W,76))
    pygame.draw.polygon(s,(39,37,33),[(0,488),(W,488),(W,H),(0,H)])
    pygame.draw.line(s,(83,68,49),(0,490),(W,490),5)
    # Desk and CRT
    pygame.draw.polygon(s,(48,40,33),[(350,493),(930,493),(1045,680),(240,680)])
    pygame.draw.polygon(s,(75,63,49),[(350,493),(930,493),(900,526),(380,526)])
    pygame.draw.rect(s,(39,42,40),(526,350,230,151),border_radius=12); pygame.draw.rect(s,(7,18,14),(544,367,194,112),border_radius=8)
    pygame.draw.rect(s,(22,54,35),(553,376,176,94));
    for y in range(380,468,5): pygame.draw.line(s,(13,37,24),(558,y),(724,y),1)
    # fan with rotating blades
    cx,cy=850,466; pygame.draw.circle(s,(37,38,35),(cx,cy),42); pygame.draw.circle(s,(97,94,79),(cx,cy),8)
    for i in range(3):
        a=fan_phase+i*math.tau/3; ex=cx+math.cos(a)*35; ey=cy+math.sin(a)*35
        pygame.draw.line(s,(122,116,96),(cx,cy),(int(ex),int(ey)),7)
    # Circular wire guard and radial spokes sit in front of the rotating blades.
    for radius in (20, 30, 40):
        pygame.draw.circle(s, (126, 124, 110), (cx, cy), radius, 2)
    for angle in range(0, 180, 30):
        a = math.radians(angle)
        pygame.draw.line(s, (104, 104, 94),
                         (int(cx-math.cos(a)*40), int(cy-math.sin(a)*40)),
                         (int(cx+math.cos(a)*40), int(cy+math.sin(a)*40)), 1)
    pygame.draw.circle(s, (157, 149, 126), (cx, cy), 7, 2)
    # papers and mug
    _poly(s,(182,174,150),[(405,563),(515,548),(530,600),(418,614)])
    for y in (566,576,586): pygame.draw.line(s,(111,104,88),(426,y),(505,y-8),1)
    pygame.draw.rect(s,(121,105,80),(590,540,32,41),border_radius=5); pygame.draw.ellipse(s,(45,39,31),(590,536,32,10)); pygame.draw.arc(s,(143,126,96),(615,546,22,27),-1.5,1.5,3)
    # side controls mounted on wall
    for x in (18,1190):
        pygame.draw.rect(s,(36,37,34),(x,300,72,150),border_radius=5)
        for j,col in enumerate(((140,42,33),(147,127,70))): pygame.draw.rect(s,col,(x+12,316+j*58,48,40),border_radius=4)
    dst.fill((0, 0, 0))
    dst.blit(s,(offset,0))

def render_camera(dst, room, occupants=(), images=None, tick=0):
    """Draw a room-specific static 2D surveillance still and photo billboards."""
    dst.fill((12,15,14)); pygame.draw.rect(dst,(31,35,32),(0,0,dst.get_width(),dst.get_height()))
    w,h=dst.get_size(); floor=int(h*.68)
    pygame.draw.polygon(dst,(22,23,21),[(0,floor),(w*.36,h*.42),(w*.64,h*.42),(w,floor),(w,h),(0,h)])
    pygame.draw.line(dst,(67,70,63),(0,floor),(w,floor),3)
    if room=="1A":
        pygame.draw.rect(dst,(77,29,35),(int(w*.12),int(h*.12),int(w*.76),int(h*.45)))
        for x in range(int(w*.15),int(w*.88),28): pygame.draw.line(dst,(130,48,48),(x,int(h*.12)),(x-10,int(h*.57)),5)
        pygame.draw.rect(dst,(73,64,50),(int(w*.22),int(h*.55),int(w*.56),int(h*.12)))
    elif room in ("1B","7","6"):
        for x in (0.24,.52,.78):
            xx=int(w*x); pygame.draw.ellipse(dst,(74,65,51),(xx-48,int(h*.52),96,28)); pygame.draw.line(dst,(84,75,62),(xx,int(h*.55)),(xx,int(h*.76)),4)
    elif room=="1C":
        pygame.draw.rect(dst,(68,25,30),(int(w*.20),int(h*.13),int(w*.60),int(h*.48)))
        for x in range(int(w*.2),int(w*.8),20): pygame.draw.line(dst,(110,34,40),(x,int(h*.13)),(x,int(h*.60)),3)
    else:
        pygame.draw.polygon(dst,(45,47,42),[(0,int(h*.23)),(w,int(h*.12)),(w,int(h*.39)),(0,int(h*.48))])
        for x in range(24,w,55): pygame.draw.line(dst,(87,88,79),(x,int(h*.24)),(x,int(h*.38)),2)
        if room=="3": pygame.draw.rect(dst,(75,65,52),(int(w*.2),int(h*.5),int(w*.6),int(h*.18)))
    # Faint phosphor haze belongs to the room only; photo sprites stay true-color.
    haze = pygame.Surface((w, h), pygame.SRCALPHA)
    haze.fill((46, 74, 50, 30))
    dst.blit(haze, (0, 0))
    for photo in list(occupants)[:1]:
        if images and photo in images:
            img=pygame.transform.smoothscale(images[photo],(int(w*.25),int(h*.7)))
            dst.blit(img, (int(w*.375), int(h*.25)))
