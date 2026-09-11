import pygame
import subprocess
import json
import os

CONFIG_FILE = "ollama_config.json"

OLLAMA_MODELS = [
    "qwen3.5:122b-a10b", "qwen3.5:35b-a3b-q8_0", "qwen3.5:35b-a3b",
    "qwen3-coder-next:latest", "qwen3.5:35b", "qwen3.5:27b",
    "qwen3-coder:30b", "qwen2.5-coder:7b", "dolphin-phi:latest",
    "mistral:7b", "llama3.1:8b", "llama3.2:3b", "mistral-small:24b",
    "gemma3:27b", "mistral-large:latest",
    "llama4:17b-scout-16e-instruct-q4_K_M", "glm-4.7-flash:latest",
    "command-r:35b", "qwen3:32b", "llama3.1:70b", "deepseek-r1:70b",
    "gpt-oss:20b", "x/flux2-klein:4b", "gemma3:12b",
    "qwen3-coder-next:80b-a3b-q5_K_M", "qwen3-coder-next:q8_0",
    "kimi-k2.5:cloud"
]

def get_available_models():
    """Run 'ollama list' and parse model names."""
    try:
        result = subprocess.run(['ollama', 'list'], capture_output=True, text=True, timeout=5)
        lines = result.stdout.strip().split('\n')
        models = []
        for line in lines[1:]:  # skip header
            parts = line.split()
            if parts:
                models.append(parts[0])
        return models if models else OLLAMA_MODELS
    except Exception:
        return OLLAMA_MODELS

def load_selected_model():
    """Load previously selected model from config file."""
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE) as f:
                data = json.load(f)
            return data.get('model', None)
        except Exception:
            pass
    return None

def save_selected_model(model_name):
    """Save selected model to config file."""
    data = {'model': model_name}
    try:
        with open(CONFIG_FILE, 'w') as f:
            json.dump(data, f)
    except Exception as e:
        print(f"[WARNING] Could not save model config: {e}")

class OllamaModelSelector:
    """Startup screen for selecting an Ollama LLM model."""

    def __init__(self, screen, font_s, font_m):
        self.screen = screen
        self.font_s = font_s
        self.font_m = font_m
        self.models = get_available_models()
        self.selected_index = 0
        self.scroll_offset = 0
        self.visible_count = 18
        self.selected_model = load_selected_model()

        # Pre-select previously used model
        if self.selected_model and self.selected_model in self.models:
            self.selected_index = self.models.index(self.selected_model)
            self.scroll_offset = max(0, self.selected_index - self.visible_count // 2)

        self.done = False
        self.search_text = ""
        self.filtered_models = self.models[:]

    def _apply_filter(self):
        if self.search_text:
            self.filtered_models = [m for m in self.models if self.search_text.lower() in m.lower()]
        else:
            self.filtered_models = self.models[:]
        self.selected_index = min(self.selected_index, max(0, len(self.filtered_models) - 1))

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_UP:
                self.selected_index = max(0, self.selected_index - 1)
                if self.selected_index < self.scroll_offset:
                    self.scroll_offset = self.selected_index
            elif event.key == pygame.K_DOWN:
                self.selected_index = min(len(self.filtered_models) - 1, self.selected_index + 1)
                if self.selected_index >= self.scroll_offset + self.visible_count:
                    self.scroll_offset = self.selected_index - self.visible_count + 1
            elif event.key == pygame.K_RETURN:
                if self.filtered_models:
                    self.selected_model = self.filtered_models[self.selected_index]
                    save_selected_model(self.selected_model)
                    self.done = True
            elif event.key == pygame.K_ESCAPE:
                # Use default or previously selected
                if not self.selected_model:
                    self.selected_model = self.models[0] if self.models else "llama3.1:8b"
                save_selected_model(self.selected_model)
                self.done = True
            elif event.key == pygame.K_BACKSPACE:
                self.search_text = self.search_text[:-1]
                self._apply_filter()
            elif event.unicode and event.unicode.isprintable() and len(event.unicode) == 1:
                self.search_text += event.unicode
                self._apply_filter()

    def draw(self):
        W, H = self.screen.get_size()
        self.screen.fill((15, 15, 25))

        # Title
        title = self.font_m.render("PLAYVILLE - SELECT OLLAMA MODEL FOR NPC AI", True, (200, 220, 255))
        self.screen.blit(title, (W // 2 - title.get_width() // 2, 30))

        subtitle = self.font_s.render("NPCs will use this LLM to generate thoughts. Choose based on your hardware.", True, (150, 160, 180))
        self.screen.blit(subtitle, (W // 2 - subtitle.get_width() // 2, 58))

        # Search box
        search_label = self.font_s.render("Search: ", True, (180, 180, 200))
        self.screen.blit(search_label, (W // 2 - 300, 85))
        search_box = pygame.Rect(W // 2 - 220, 82, 440, 22)
        pygame.draw.rect(self.screen, (30, 30, 50), search_box)
        pygame.draw.rect(self.screen, (100, 120, 180), search_box, 1)
        search_txt = self.font_s.render(self.search_text + "|", True, (220, 220, 255))
        self.screen.blit(search_txt, (search_box.x + 5, search_box.y + 3))

        # Model list panel
        panel = pygame.Rect(W // 2 - 500, 115, 1000, self.visible_count * 32 + 20)
        pygame.draw.rect(self.screen, (20, 20, 35), panel)
        pygame.draw.rect(self.screen, (80, 100, 150), panel, 2)

        col_headers_y = panel.y + 5
        self.screen.blit(self.font_s.render("Model Name", True, (150, 160, 200)), (panel.x + 20, col_headers_y))
        self.screen.blit(self.font_s.render("(Use UP/DOWN + ENTER to select)", True, (120, 130, 160)), (panel.x + 300, col_headers_y))

        for i in range(self.visible_count):
            model_idx = self.scroll_offset + i
            if model_idx >= len(self.filtered_models):
                break
            model = self.filtered_models[model_idx]
            item_y = panel.y + 20 + i * 32
            item_rect = pygame.Rect(panel.x + 5, item_y, panel.width - 10, 30)

            is_selected = model_idx == self.selected_index
            is_previous = model == self.selected_model

            if is_selected:
                pygame.draw.rect(self.screen, (50, 80, 130), item_rect)
                pygame.draw.rect(self.screen, (100, 150, 255), item_rect, 1)
            elif is_previous:
                pygame.draw.rect(self.screen, (30, 60, 30), item_rect)

            label_color = (255, 255, 100) if is_selected else (200, 220, 200) if is_previous else (180, 180, 200)
            model_txt = self.font_s.render(model, True, label_color)
            self.screen.blit(model_txt, (item_rect.x + 15, item_rect.y + 8))

            if is_previous:
                prev_marker = self.font_s.render("<- PREVIOUSLY USED", True, (100, 200, 100))
                self.screen.blit(prev_marker, (item_rect.x + 400, item_rect.y + 8))

        # Scrollbar
        if len(self.filtered_models) > self.visible_count:
            sb_x = panel.right - 12
            sb_h = panel.height - 25
            sb_ratio = self.visible_count / len(self.filtered_models)
            thumb_h = max(20, int(sb_h * sb_ratio))
            thumb_y = panel.y + 20 + int(sb_h * self.scroll_offset / len(self.filtered_models))
            pygame.draw.rect(self.screen, (50, 50, 80), pygame.Rect(sb_x, panel.y + 20, 8, sb_h))
            pygame.draw.rect(self.screen, (100, 130, 200), pygame.Rect(sb_x, thumb_y, 8, thumb_h))

        # Instructions
        instr_y = panel.bottom + 15
        instructions = [
            "UP/DOWN: navigate  |  Type to search  |  ENTER: confirm  |  ESC: use previous/default",
            f"Currently selected: {self.filtered_models[self.selected_index] if self.filtered_models else 'none'}",
        ]
        for line in instructions:
            txt = self.font_s.render(line, True, (160, 170, 190))
            self.screen.blit(txt, (W // 2 - txt.get_width() // 2, instr_y))
            instr_y += 20

        pygame.display.flip()

    def run(self, clock):
        """Run the selector screen until a model is chosen. Returns selected model name."""
        while not self.done:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    import sys; sys.exit()
                self.handle_event(event)
            self.draw()
            clock.tick(60)
        return self.selected_model
