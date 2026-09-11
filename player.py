import pygame
import json
import os

class Item:
    def __init__(self, name, category, buy_price, sell_price, description, icon_color=(200,200,100)):
        self.name = name
        self.category = category  # 'food', 'tool', 'information', 'medicine'
        self.buy_price = buy_price
        self.sell_price = sell_price
        self.description = description
        self.icon_color = icon_color
        self.quantity = 1

# Item catalog - items the store sells
STORE_CATALOG = [
    Item("Bread", "food", 5, 2, "Fresh-baked bread, restores energy.", (210, 180, 140)),
    Item("Apple", "food", 3, 1, "A crisp apple from the orchard.", (220, 60, 60)),
    Item("Water Flask", "food", 8, 4, "Clean water, essential for long days.", (100, 180, 255)),
    Item("Lantern", "tool", 25, 10, "Illuminates dark areas at night.", (255, 220, 100)),
    Item("Rope", "tool", 15, 7, "Sturdy rope, many uses.", (180, 140, 80)),
    Item("Town Map", "tool", 20, 5, "A hand-drawn map of Playville.", (240, 220, 180)),
    Item("Notebook", "information", 12, 6, "Record clues and observations.", (240, 240, 200)),
    Item("Rumor Sheet", "information", 10, 3, "Local gossip printed on paper.", (255, 240, 180)),
    Item("Lockpick", "tool", 40, 15, "Opens certain locked doors. Use carefully.", (160, 160, 180)),
    Item("Medicine Kit", "medicine", 30, 12, "Basic medical supplies.", (200, 240, 200)),
    Item("Whiskey", "food", 18, 8, "Strong drink. NPCs may talk more freely.", (180, 120, 60)),
    Item("Gold Nugget", "trade", 50, 45, "Pure gold. High trade value.", (255, 215, 0)),
]

class Inventory:
    def __init__(self):
        self.items = {}  # item_name -> {item: Item, quantity: int}

    def add_item(self, item, quantity=1):
        if item.name in self.items:
            self.items[item.name]['quantity'] += quantity
        else:
            self.items[item.name] = {'item': item, 'quantity': quantity}

    def remove_item(self, item_name, quantity=1):
        if item_name in self.items and self.items[item_name]['quantity'] >= quantity:
            self.items[item_name]['quantity'] -= quantity
            if self.items[item_name]['quantity'] <= 0:
                del self.items[item_name]
            return True
        return False

    def has_item(self, item_name):
        return item_name in self.items and self.items[item_name]['quantity'] > 0

    def get_item_count(self, item_name):
        return self.items.get(item_name, {}).get('quantity', 0)

    def get_all_items(self):
        return [(data['item'], data['quantity']) for data in self.items.values()]

    def total_value(self):
        return sum(data['item'].sell_price * data['quantity'] for data in self.items.values())

class Player:
    SAVE_FILE = "player_save.json"

    def __init__(self, start_pos=(700, 750)):
        self.pos = pygame.Vector2(start_pos)
        self.speed = 3.5
        self.gold = 100  # starting gold
        self.inventory = Inventory()
        self.name = "You"
        self.reputation = 50  # 0-100, affects NPC interactions
        self.transactions = []  # transaction log
        self.image = self._create_player_sprite()
        self.rect = self.image.get_rect(center=(int(self.pos.x), int(self.pos.y)))
        self.near_store = False
        self.load()

    def _create_player_sprite(self):
        """Draw the player as a distinct character (blue outfit)."""
        surf = pygame.Surface((40, 40), pygame.SRCALPHA)
        # Body
        pygame.draw.circle(surf, (70, 130, 200), (20, 14), 10)  # head
        pygame.draw.rect(surf, (50, 100, 180), (12, 24, 16, 14))  # body
        pygame.draw.rect(surf, (70, 130, 200), (8, 24, 8, 12))  # left arm
        pygame.draw.rect(surf, (70, 130, 200), (24, 24, 8, 12))  # right arm
        # Eyes
        pygame.draw.circle(surf, (255, 255, 255), (17, 13), 3)
        pygame.draw.circle(surf, (255, 255, 255), (23, 13), 3)
        pygame.draw.circle(surf, (0, 0, 0), (17, 13), 1)
        pygame.draw.circle(surf, (0, 0, 0), (23, 13), 1)
        return surf

    def update(self, keys, game_width, height, store_pos, store_radius=80):
        """Handle WASD movement and store proximity detection."""
        dx, dy = 0, 0
        if keys[pygame.K_w] or keys[pygame.K_UP]: dy -= self.speed
        if keys[pygame.K_s] or keys[pygame.K_DOWN]: dy += self.speed
        if keys[pygame.K_a] or keys[pygame.K_LEFT]: dx -= self.speed
        if keys[pygame.K_d] or keys[pygame.K_RIGHT]: dx += self.speed

        self.pos.x = max(20, min(game_width - 20, self.pos.x + dx))
        self.pos.y = max(20, min(height - 20, self.pos.y + dy))
        self.rect.center = (int(self.pos.x), int(self.pos.y))

        # Check proximity to store
        store_vec = pygame.Vector2(store_pos)
        self.near_store = self.pos.distance_to(store_vec) < store_radius

    def draw(self, surf, font):
        surf.blit(self.image, self.rect)
        # Label
        label = font.render("YOU", True, (255, 255, 100))
        label_rect = label.get_rect(center=(self.rect.centerx, self.rect.top - 8))
        surf.blit(label, label_rect)
        # Gold display near player
        gold_txt = font.render(f"${self.gold}g", True, (255, 215, 0))
        surf.blit(gold_txt, (self.rect.centerx - 15, self.rect.bottom + 2))
        # Store prompt
        if self.near_store:
            prompt = font.render("[E] Enter Store", True, (255, 255, 100))
            surf.blit(prompt, (self.rect.centerx - 50, self.rect.top - 22))

    def buy_item(self, item):
        if self.gold >= item.buy_price:
            self.gold -= item.buy_price
            self.inventory.add_item(item)
            self.transactions.append(f"Bought {item.name} for {item.buy_price}g")
            if len(self.transactions) > 20:
                self.transactions.pop(0)
            return True, f"Bought {item.name} for {item.buy_price}g"
        return False, f"Not enough gold! Need {item.buy_price}g, have {self.gold}g"

    def sell_item(self, item_name):
        if self.inventory.has_item(item_name):
            item_data = self.inventory.items[item_name]
            item = item_data['item']
            sell_price = item.sell_price
            self.inventory.remove_item(item_name)
            self.gold += sell_price
            self.transactions.append(f"Sold {item_name} for {sell_price}g")
            if len(self.transactions) > 20:
                self.transactions.pop(0)
            return True, f"Sold {item_name} for {sell_price}g"
        return False, "Item not in inventory"

    def save(self):
        data = {
            'gold': self.gold,
            'reputation': self.reputation,
            'inventory': {name: d['quantity'] for name, d in self.inventory.items.items()},
            'transactions': self.transactions[-10:]
        }
        with open(self.SAVE_FILE, 'w') as f:
            json.dump(data, f)

    def load(self):
        if os.path.exists(self.SAVE_FILE):
            try:
                with open(self.SAVE_FILE) as f:
                    data = json.load(f)
                self.gold = data.get('gold', 100)
                self.reputation = data.get('reputation', 50)
                self.transactions = data.get('transactions', [])
                # Restore inventory
                catalog_by_name = {item.name: item for item in STORE_CATALOG}
                for item_name, qty in data.get('inventory', {}).items():
                    if item_name in catalog_by_name:
                        self.inventory.add_item(catalog_by_name[item_name], qty)
            except Exception as e:
                print(f"[WARNING] Could not load player save: {e}")
