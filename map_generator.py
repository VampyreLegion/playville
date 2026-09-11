import pygame
import random


def generate_town_map(width=1800, height=1024):
    """Generate and return a pygame.Surface with the town map drawn."""
    surface = pygame.Surface((width, height))

    # --- Background: grass ---
    surface.fill((72, 120, 60))

    # --- Road network (tan/dirt paths connecting buildings) ---
    road_color = (180, 155, 110)
    road_width = 28

    # Define road segments as (start, end) pairs (pixel coords)
    road_segments = [
        # Main horizontal spine
        ((0, 600), (width, 600)),
        # Vertical connector: graveyard area to town square
        ((120, 0), (120, 600)),
        # Vertical spine: courthouse to town square
        ((900, 0), (900, 820)),
        # Right side: jail and library column
        ((1520, 0), (1520, 600)),
        # Connect library/jail column to town square spine
        ((900, 430), (1520, 430)),
        # Doctor's office horizontal
        ((120, 400), (500, 400)),
        # General store / factory row
        ((0, 820), (700, 820)),
        # House D spur (formerly player house)
        ((700, 750), (900, 750)),
        # Press office spur
        ((680, 400), (680, 600)),
        # House A road spur
        ((1100, 600), (1100, 750)),
        # House B road spur
        ((350, 600), (350, 700)),
        # House C road spur
        ((1300, 600), (1300, 650)),
        # Town square horizontal
        ((700, 600), (1100, 600)),
        # Connect factory row up to doctor row
        ((480, 400), (480, 820)),
    ]

    for (x1, y1), (x2, y2) in road_segments:
        pygame.draw.line(surface, road_color, (x1, y1), (x2, y2), road_width)

    # Road edges (slightly darker)
    road_edge_color = (150, 125, 85)
    edge_w = 2
    for (x1, y1), (x2, y2) in road_segments:
        pygame.draw.line(surface, road_edge_color, (x1, y1), (x2, y2), road_width + edge_w * 2)
        pygame.draw.line(surface, road_color, (x1, y1), (x2, y2), road_width)

    # --- Helper: draw a building ---
    def draw_building(cx, cy, bw, bh, body_color, roof_color, border_color, label, font):
        rect = pygame.Rect(cx - bw // 2, cy - bh // 2, bw, bh)
        # Shadow
        shadow = rect.move(4, 4)
        pygame.draw.rect(surface, (40, 40, 40), shadow)
        # Body
        pygame.draw.rect(surface, body_color, rect)
        # Border
        pygame.draw.rect(surface, border_color, rect, 3)
        # Roof (darker top strip / triangle suggestion)
        roof_rect = pygame.Rect(rect.x, rect.y, bw, bh // 5)
        pygame.draw.rect(surface, roof_color, roof_rect)
        # Door (dark brown rectangle at bottom center)
        door_w, door_h = max(12, bw // 6), max(14, bh // 4)
        door_rect = pygame.Rect(rect.centerx - door_w // 2, rect.bottom - door_h, door_w, door_h)
        pygame.draw.rect(surface, (80, 50, 20), door_rect)
        # Windows (two small squares)
        win_y = rect.y + bh // 3
        win_size = max(8, bw // 8)
        for wx_offset in [-bw // 4, bw // 4]:
            win_rect = pygame.Rect(rect.centerx + wx_offset - win_size // 2, win_y, win_size, win_size)
            pygame.draw.rect(surface, (200, 230, 255), win_rect)
            pygame.draw.rect(surface, (100, 100, 120), win_rect, 1)
        # Label
        label_surf = font.render(label, True, (255, 255, 255))
        label_shadow = font.render(label, True, (0, 0, 0))
        lx = cx - label_surf.get_width() // 2
        ly = cy + bh // 2 + 5
        surface.blit(label_shadow, (lx + 1, ly + 1))
        surface.blit(label_surf, (lx, ly))

    # Initialize font for labels (requires pygame.font.init() to have been called)
    try:
        font = pygame.font.SysFont("Arial", 11, bold=True)
    except Exception:
        font = pygame.font.Font(None, 14)

    # --- Buildings ---

    # General Store (220, 820) - wooden, tan/brown
    draw_building(220, 820, 90, 70, (180, 140, 90), (130, 90, 50), (90, 60, 20),
                  "General Store", font)
    # Sign
    sign = font.render("STORE", True, (255, 220, 100))
    surface.blit(sign, (220 - sign.get_width() // 2, 820 - 35 - 14))

    # Courthouse (900, 280) - grand stone, grey/white
    draw_building(900, 280, 130, 110, (210, 210, 205), (160, 160, 155), (80, 80, 90),
                  "Courthouse", font)
    # Columns suggestion (vertical lines)
    for col_x in [840, 860, 930, 950]:
        pygame.draw.line(surface, (240, 240, 235), (col_x, 235), (col_x, 330), 4)

    # Jail (1520, 200) - dark stone, grey
    draw_building(1520, 200, 100, 80, (100, 100, 105), (60, 60, 65), (30, 30, 35),
                  "Jail", font)
    # Bars on windows
    for bx in [1500, 1520, 1540]:
        pygame.draw.line(surface, (50, 50, 55), (bx, 175), (bx, 205), 2)

    # Library (1520, 420) - brick, dark red
    draw_building(1520, 420, 100, 80, (160, 70, 60), (110, 45, 35), (70, 25, 20),
                  "Library", font)

    # Factory (480, 820) - industrial, dark grey
    draw_building(480, 820, 110, 80, (80, 80, 85), (50, 50, 55), (30, 30, 35),
                  "Factory", font)
    # Smokestacks
    for sx in [455, 490, 525]:
        pygame.draw.rect(surface, (60, 60, 65), pygame.Rect(sx - 7, 750, 14, 50))
        pygame.draw.rect(surface, (40, 40, 45), pygame.Rect(sx - 9, 748, 18, 6))
        # Smoke puff
        for i in range(3):
            pygame.draw.circle(surface, (180, 180, 180),
                               (sx + random.randint(-4, 4), 742 - i * 10),
                               5 + i * 2)

    # Graveyard (120, 150) - enclosed area, dark green
    grave_rect = pygame.Rect(60, 90, 130, 130)
    pygame.draw.rect(surface, (30, 55, 30), grave_rect)
    pygame.draw.rect(surface, (20, 35, 20), grave_rect, 3)
    # Fence
    for fx in range(60, 190, 12):
        pygame.draw.line(surface, (80, 80, 80), (fx, 90), (fx, 220), 2)
    pygame.draw.line(surface, (80, 80, 80), (60, 90), (190, 90), 2)
    pygame.draw.line(surface, (80, 80, 80), (60, 220), (190, 220), 2)
    # Gravestones
    for gx, gy in [(90, 130), (120, 150), (150, 125), (100, 175), (140, 170)]:
        pygame.draw.rect(surface, (160, 160, 160), pygame.Rect(gx - 6, gy - 12, 12, 18))
        pygame.draw.rect(surface, (100, 100, 100), pygame.Rect(gx - 6, gy - 12, 12, 18), 1)
    gyard_label = font.render("Graveyard", True, (180, 220, 180))
    surface.blit(gyard_label, (120 - gyard_label.get_width() // 2, 225))

    # Doctor's Office (350, 400) - white/clean
    draw_building(350, 400, 90, 70, (240, 240, 235), (200, 200, 195), (100, 120, 100),
                  "Doctor", font)
    # Red cross sign
    pygame.draw.rect(surface, (220, 40, 40), pygame.Rect(345, 360, 10, 25))
    pygame.draw.rect(surface, (220, 40, 40), pygame.Rect(338, 367, 24, 10))

    # Town Square (900, 600) - open plaza with fountain
    plaza_rect = pygame.Rect(820, 530, 160, 140)
    pygame.draw.rect(surface, (190, 175, 145), plaza_rect)
    pygame.draw.rect(surface, (150, 135, 105), plaza_rect, 2)
    # Fountain
    pygame.draw.circle(surface, (100, 160, 210), (900, 600), 32)
    pygame.draw.circle(surface, (140, 200, 240), (900, 600), 20)
    pygame.draw.circle(surface, (80, 130, 180), (900, 600), 32, 3)
    # Fountain center
    pygame.draw.circle(surface, (180, 180, 190), (900, 600), 6)
    ts_label = font.render("Town Square", True, (60, 40, 10))
    surface.blit(ts_label, (900 - ts_label.get_width() // 2, 640))

    # House (700, 750) - small warm house (formerly player house)
    draw_building(700, 750, 70, 60, (190, 170, 140), (140, 120, 95), (100, 85, 60),
                  "House", font)
    # Chimney
    pygame.draw.rect(surface, (130, 90, 60), pygame.Rect(718, 710, 12, 20))

    # Press Office / Gazette (680, 400) - newspaper office
    draw_building(680, 400, 80, 65, (160, 140, 110), (110, 90, 70), (70, 60, 40),
                  "Gazette", font)
    # Printing press symbol (small rectangle grid)
    for px in [660, 675, 690]:
        pygame.draw.rect(surface, (80, 70, 50), pygame.Rect(px, 370, 8, 10))

    # Empty House A (1100, 750)
    draw_building(1100, 750, 65, 55, (190, 170, 140), (140, 120, 95), (100, 85, 60),
                  "House", font)

    # Empty House B (350, 700)
    draw_building(350, 700, 65, 55, (175, 165, 145), (130, 120, 100), (95, 85, 65),
                  "House", font)

    # Empty House C (1300, 650)
    draw_building(1300, 650, 65, 55, (185, 160, 130), (135, 110, 85), (100, 80, 55),
                  "House", font)

    # Bank (1200, 300) - stone, gold-trimmed
    draw_building(1200, 300, 100, 80, (200, 195, 175), (150, 145, 120), (100, 90, 60),
                  "Bank", font)
    # Vault door symbol (concentric circles)
    pygame.draw.circle(surface, (140, 130, 100), (1200, 295), 18)
    pygame.draw.circle(surface, (180, 170, 130), (1200, 295), 13)
    pygame.draw.circle(surface, (140, 130, 100), (1200, 295), 8)
    pygame.draw.circle(surface, (200, 190, 150), (1200, 295), 3)

    # Church (1600, 700) - white/stone with cross
    draw_building(1600, 700, 90, 80, (230, 228, 220), (180, 175, 165), (120, 115, 100),
                  "Church", font)
    # Cross on roof
    cross_cx = 1600
    cross_top = 700 - 40 - 20  # above roof strip
    pygame.draw.rect(surface, (180, 160, 120), pygame.Rect(cross_cx - 3, cross_top - 22, 6, 28))
    pygame.draw.rect(surface, (180, 160, 120), pygame.Rect(cross_cx - 10, cross_top - 14, 20, 6))

    # Road spurs for bank and church
    # Bank spur: connect to main horizontal spine at y=600
    bank_road_segments = [
        ((1200, 300), (1200, 430)),   # bank south to cross-road
        ((1100, 430), (1300, 430)),   # horizontal at y=430 (bank area)
    ]
    for (x1, y1), (x2, y2) in bank_road_segments:
        pygame.draw.line(surface, road_edge_color, (x1, y1), (x2, y2), road_width + edge_w * 2)
        pygame.draw.line(surface, road_color, (x1, y1), (x2, y2), road_width)

    # Church spur: connect to main horizontal spine at y=600
    church_road_segments = [
        ((1600, 700), (1600, 600)),   # church north to main road
    ]
    for (x1, y1), (x2, y2) in church_road_segments:
        pygame.draw.line(surface, road_edge_color, (x1, y1), (x2, y2), road_width + edge_w * 2)
        pygame.draw.line(surface, road_color, (x1, y1), (x2, y2), road_width)

    # Redraw bank and church on top of road spurs
    draw_building(1200, 300, 100, 80, (200, 195, 175), (150, 145, 120), (100, 90, 60),
                  "Bank", font)
    pygame.draw.circle(surface, (140, 130, 100), (1200, 295), 18)
    pygame.draw.circle(surface, (180, 170, 130), (1200, 295), 13)
    pygame.draw.circle(surface, (140, 130, 100), (1200, 295), 8)
    pygame.draw.circle(surface, (200, 190, 150), (1200, 295), 3)

    draw_building(1600, 700, 90, 80, (230, 228, 220), (180, 175, 165), (120, 115, 100),
                  "Church", font)
    pygame.draw.rect(surface, (180, 160, 120), pygame.Rect(cross_cx - 3, cross_top - 22, 6, 28))
    pygame.draw.rect(surface, (180, 160, 120), pygame.Rect(cross_cx - 10, cross_top - 14, 20, 6))

    # --- Trees scattered around ---
    tree_positions = [
        (50, 320), (200, 480), (300, 700), (400, 200), (600, 150),
        (750, 300), (1050, 200), (1100, 500), (1200, 700), (1300, 150),
        (1350, 550), (1400, 800), (1600, 600), (1650, 350), (1700, 750),
        (50, 700), (250, 900), (600, 950), (1000, 900), (1400, 950),
        (800, 100), (1000, 450), (570, 600), (320, 550),
    ]
    for tx, ty in tree_positions:
        # Trunk
        pygame.draw.rect(surface, (100, 70, 40), pygame.Rect(tx - 4, ty, 8, 18))
        # Canopy
        pygame.draw.circle(surface, (40, 90, 40), (tx, ty), 18)
        pygame.draw.circle(surface, (55, 110, 55), (tx - 5, ty - 5), 12)
        pygame.draw.circle(surface, (35, 80, 35), (tx + 5, ty - 3), 10)

    return surface
