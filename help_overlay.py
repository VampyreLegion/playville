import pygame

HELP_SECTIONS = [
    ("MOVEMENT & INTERACTION", [
        ("Click NPC", "Select NPC to view details in bottom pane"),
        ("Click Courthouse", "Open evidence journal"),
        ("F1", "Toggle this help screen"),
        ("ESC", "Close overlays / Deselect"),
    ]),
    ("OVERLAY TOGGLES", [
        ("C", "Toggle NPC deep thoughts window"),
        ("N", "Toggle The Playville Chronicle newspaper"),
        ("G", "Toggle social network relationship graph"),
        ("T", "Seed a story into the next newspaper"),
        ("B", "Urgent bulletin - publish seeded stories now"),
        ("J", "File court case (select NPC first)"),
        ("F1", "Toggle help screen (this page)"),
    ]),
    ("NEWSPAPER NAVIGATION", [
        ("N", "Open/close the newspaper overlay"),
        ("UP Arrow", "Scroll newspaper up"),
        ("DOWN Arrow", "Scroll newspaper down"),
    ]),
    ("NEWSPAPER REPORTER", [
        ("Fletcher Haze", "AI reporter who files articles automatically"),
        ("T key", "Open story seeder - inject your own headline + body"),
        ("Shift+Enter", "Submit seeded story to next newspaper edition"),
        ("N key", "Read the latest Chronicle (includes reporter articles)"),
    ]),
    ("SOCIAL GRAPH", [
        ("G", "Open/close the relationship graph"),
        ("Click node", "Inspect NPC relationships"),
        ("Hover", "Highlight connected nodes"),
    ]),
    ("NPC STATUS DOTS", [
        ("Green dot", "NPC is calm / normal"),
        ("Red dot", "NPC is suspicious / guilty"),
        ("Blue dot", "NPC is investigating something"),
    ]),
    ("AI MODEL", [
        ("Startup screen", "Select Ollama LLM for NPC thoughts"),
        ("Restart game", "Change the AI model"),
    ]),
    ("TIPS", [
        ("Town Chronicle", "Published every 5 in-game minutes"),
        ("Factions", "Form when 2+ NPCs share strong opinions"),
        ("Town Whispers", "Appear when 5+ NPCs share the same wish"),
        ("Story Seeder", "Inject custom headlines into the next newspaper edition"),
        ("Reputation", "Future: affects how NPCs respond to you"),
    ]),
]

class HelpOverlay:
    def __init__(self):
        self.visible = False
        self.scroll = 0

    def toggle(self):
        self.visible = not self.visible
        self.scroll = 0

    def handle_event(self, event):
        if not self.visible:
            return
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_F1 or event.key == pygame.K_ESCAPE:
                self.visible = False
            elif event.key == pygame.K_UP:
                self.scroll = max(0, self.scroll - 20)
            elif event.key == pygame.K_DOWN:
                self.scroll += 20

    def draw(self, screen, font_s, font_m):
        if not self.visible:
            return
        W, H = screen.get_size()
        overlay_rect = pygame.Rect(100, 40, W - 600, H - 80)  # leave sidebar visible

        bg = pygame.Surface((overlay_rect.width, overlay_rect.height))
        bg.set_alpha(250)
        bg.fill((18, 20, 35))
        screen.blit(bg, overlay_rect.topleft)
        pygame.draw.rect(screen, (80, 100, 180), overlay_rect, 3)

        title = font_m.render("F1 - PLAYVILLE HELP & KEYBOARD REFERENCE", True, (200, 220, 255))
        screen.blit(title, (overlay_rect.x + 20, overlay_rect.y + 12))

        pygame.draw.line(screen, (80, 100, 180),
                         (overlay_rect.x + 10, overlay_rect.y + 34),
                         (overlay_rect.right - 10, overlay_rect.y + 34), 1)

        y = overlay_rect.y + 45 - self.scroll
        col_w = overlay_rect.width // 2 - 20

        left_sections = HELP_SECTIONS[:4]
        right_sections = HELP_SECTIONS[4:]

        def draw_section(section_list, start_x, start_y):
            y = start_y
            for section_title, entries in section_list:
                if y < overlay_rect.bottom - 10 and y > overlay_rect.y + 30:
                    header = font_m.render(section_title, True, (255, 220, 100))
                    screen.blit(header, (start_x, y))
                y += 20
                for key, desc in entries:
                    if y < overlay_rect.bottom - 10 and y > overlay_rect.y + 30:
                        key_surf = font_s.render(f"  {key:<22}", True, (140, 200, 255))
                        desc_surf = font_s.render(desc, True, (200, 200, 200))
                        screen.blit(key_surf, (start_x, y))
                        screen.blit(desc_surf, (start_x + 160, y))
                    y += 15
                y += 8
            return y

        left_x = overlay_rect.x + 20
        right_x = overlay_rect.x + col_w + 30

        draw_section(left_sections, left_x, y)
        draw_section(right_sections, right_x, y)

        footer = font_s.render("F1 or ESC to close | UP/DOWN to scroll", True, (120, 130, 160))
        screen.blit(footer, (overlay_rect.x + 20, overlay_rect.bottom - 20))
