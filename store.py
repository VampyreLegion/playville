import pygame
from player import STORE_CATALOG, Item

class GeneralStore:
    """The Playville General Store - buy and sell items."""

    def __init__(self):
        self.catalog = STORE_CATALOG[:]
        self.selected_buy_index = 0
        self.selected_sell_index = 0
        self.tab = 'buy'  # 'buy' or 'sell'
        self.message = ""
        self.message_timer = 0
        self.store_npc_name = "Bea Miller"
        self.greetings = [
            "Welcome! Looking to buy something?",
            "Good to see you! Browse around.",
            "Fresh stock just arrived!",
            "Best prices in Playville, guaranteed.",
            "Need anything? I've got it all.",
        ]
        self.greeting = self.greetings[0]
        import random
        self.greeting = random.choice(self.greetings)

    def handle_event(self, event, player):
        """Handle keyboard events for store navigation."""
        result_msg = None
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_TAB:
                self.tab = 'sell' if self.tab == 'buy' else 'buy'
                self.selected_buy_index = 0
                self.selected_sell_index = 0
            elif event.key == pygame.K_UP:
                if self.tab == 'buy':
                    self.selected_buy_index = max(0, self.selected_buy_index - 1)
                else:
                    sell_items = player.inventory.get_all_items()
                    self.selected_sell_index = max(0, self.selected_sell_index - 1)
            elif event.key == pygame.K_DOWN:
                if self.tab == 'buy':
                    self.selected_buy_index = min(len(self.catalog) - 1, self.selected_buy_index + 1)
                else:
                    sell_items = player.inventory.get_all_items()
                    self.selected_sell_index = min(len(sell_items) - 1, self.selected_sell_index + 1)
            elif event.key == pygame.K_RETURN or event.key == pygame.K_e:
                if self.tab == 'buy':
                    if 0 <= self.selected_buy_index < len(self.catalog):
                        item = self.catalog[self.selected_buy_index]
                        success, msg = player.buy_item(item)
                        self.message = msg
                        self.message_timer = 120
                else:
                    sell_items = player.inventory.get_all_items()
                    if 0 <= self.selected_sell_index < len(sell_items):
                        item, qty = sell_items[self.selected_sell_index]
                        success, msg = player.sell_item(item.name)
                        self.message = msg
                        self.message_timer = 120
                        if self.selected_sell_index >= len(player.inventory.get_all_items()):
                            self.selected_sell_index = max(0, self.selected_sell_index - 1)
        return result_msg

    def draw(self, screen, font_s, font_m, player):
        """Draw the full store UI overlay."""
        # Background panel
        panel = pygame.Rect(150, 80, 1400, 860)
        bg = pygame.Surface((panel.width, panel.height))
        bg.set_alpha(248)
        bg.fill((245, 230, 200))
        screen.blit(bg, panel.topleft)
        pygame.draw.rect(screen, (120, 80, 40), panel, 4)

        # Title
        title = font_m.render("PLAYVILLE GENERAL STORE", True, (80, 40, 0))
        screen.blit(title, (panel.x + 20, panel.y + 12))

        # NPC greeting
        npc_txt = font_s.render(f'{self.store_npc_name}: "{self.greeting}"', True, (100, 60, 20))
        screen.blit(npc_txt, (panel.x + 20, panel.y + 38))

        # Player gold
        gold_txt = font_m.render(f"Your Gold: {player.gold}g", True, (180, 140, 0))
        screen.blit(gold_txt, (panel.x + panel.width - 200, panel.y + 12))

        # Tabs
        buy_color = (80, 140, 80) if self.tab == 'buy' else (120, 120, 120)
        sell_color = (140, 80, 80) if self.tab == 'sell' else (120, 120, 120)
        buy_tab = font_m.render("[BUY]", True, buy_color)
        sell_tab = font_m.render("[SELL]", True, sell_color)
        screen.blit(buy_tab, (panel.x + 20, panel.y + 60))
        screen.blit(sell_tab, (panel.x + 110, panel.y + 60))
        tab_hint = font_s.render("TAB to switch | UP/DOWN select | ENTER to confirm | E to close", True, (100, 80, 40))
        screen.blit(tab_hint, (panel.x + 200, panel.y + 64))

        pygame.draw.line(screen, (120, 80, 40), (panel.x + 10, panel.y + 82), (panel.x + panel.width - 10, panel.y + 82), 2)

        # Left: item list
        list_x = panel.x + 20
        list_y = panel.y + 95

        if self.tab == 'buy':
            items_to_show = [(item, None) for item in self.catalog]
            selected_idx = self.selected_buy_index
            header = "ITEMS FOR SALE"
        else:
            items_to_show = player.inventory.get_all_items()
            selected_idx = self.selected_sell_index
            header = "YOUR INVENTORY (sell)"

        screen.blit(font_m.render(header, True, (60, 40, 20)), (list_x, list_y))
        list_y += 22

        # Column headers
        screen.blit(font_s.render("Item", True, (80, 60, 40)), (list_x, list_y))
        price_label = "Price" if self.tab == 'buy' else "Sell Value"
        screen.blit(font_s.render(price_label, True, (80, 60, 40)), (list_x + 250, list_y))
        screen.blit(font_s.render("Qty", True, (80, 60, 40)), (list_x + 340, list_y))
        list_y += 16

        for i, item_data in enumerate(items_to_show):
            if list_y > panel.y + panel.height - 100:
                break
            if self.tab == 'buy':
                item = item_data[0]
                qty_display = ""
                price_display = f"{item.buy_price}g"
                inv_qty = player.inventory.get_item_count(item.name)
                qty_display = f"(own:{inv_qty})" if inv_qty > 0 else ""
            else:
                item, qty = item_data
                price_display = f"{item.sell_price}g"
                qty_display = f"x{qty}"

            # Highlight selected
            if i == selected_idx:
                highlight = pygame.Rect(list_x - 5, list_y - 2, 500, 18)
                pygame.draw.rect(screen, (200, 220, 180), highlight)
                pygame.draw.rect(screen, (80, 140, 80), highlight, 1)

            # Item color dot
            pygame.draw.circle(screen, item.icon_color, (list_x + 8, list_y + 7), 6)

            name_color = (30, 30, 30) if i == selected_idx else (60, 60, 60)
            screen.blit(font_s.render(item.name, True, name_color), (list_x + 18, list_y))

            price_color = (0, 100, 0) if self.tab == 'buy' else (150, 60, 0)
            screen.blit(font_s.render(price_display, True, price_color), (list_x + 250, list_y))
            screen.blit(font_s.render(qty_display, True, (100, 100, 100)), (list_x + 340, list_y))
            list_y += 20

        # Right: selected item detail
        detail_x = panel.x + 600
        detail_y = panel.y + 95
        pygame.draw.line(screen, (120, 80, 40), (detail_x - 10, panel.y + 90), (detail_x - 10, panel.y + panel.height - 10), 1)

        screen.blit(font_m.render("ITEM DETAILS", True, (60, 40, 20)), (detail_x, detail_y))
        detail_y += 25

        selected_item = None
        if self.tab == 'buy' and 0 <= self.selected_buy_index < len(items_to_show):
            selected_item = items_to_show[self.selected_buy_index][0]
        elif self.tab == 'sell' and 0 <= self.selected_sell_index < len(items_to_show):
            selected_item = items_to_show[self.selected_sell_index][0]

        if selected_item:
            pygame.draw.circle(screen, selected_item.icon_color, (detail_x + 25, detail_y + 20), 20)
            screen.blit(font_m.render(selected_item.name, True, (30, 30, 30)), (detail_x + 55, detail_y + 10))
            detail_y += 50

            cat_txt = font_s.render(f"Category: {selected_item.category.title()}", True, (100, 80, 50))
            screen.blit(cat_txt, (detail_x, detail_y)); detail_y += 18

            buy_txt = font_s.render(f"Buy Price: {selected_item.buy_price}g", True, (0, 120, 0))
            screen.blit(buy_txt, (detail_x, detail_y)); detail_y += 18

            sell_txt = font_s.render(f"Sell Value: {selected_item.sell_price}g", True, (160, 80, 0))
            screen.blit(sell_txt, (detail_x, detail_y)); detail_y += 25

            # Description word-wrapped
            words = selected_item.description.split()
            line = ""
            for word in words:
                if len(line) + len(word) + 1 > 45:
                    screen.blit(font_s.render(line, True, (60, 60, 60)), (detail_x, detail_y))
                    detail_y += 16
                    line = word + " "
                else:
                    line += word + " "
            if line:
                screen.blit(font_s.render(line, True, (60, 60, 60)), (detail_x, detail_y))
                detail_y += 20

        # Transaction log
        trans_y = panel.y + 500
        screen.blit(font_m.render("RECENT TRANSACTIONS", True, (60, 40, 20)), (detail_x, trans_y))
        trans_y += 20
        for tx in reversed(player.transactions[-8:]):
            screen.blit(font_s.render(tx, True, (80, 80, 80)), (detail_x, trans_y))
            trans_y += 16

        # Inventory summary (right panel bottom)
        inv_y = panel.y + panel.height - 160
        screen.blit(font_m.render("YOUR INVENTORY SUMMARY", True, (60, 40, 20)), (detail_x, inv_y))
        inv_y += 20
        all_items = player.inventory.get_all_items()
        if all_items:
            for item, qty in all_items[:6]:
                screen.blit(font_s.render(f"• {item.name} x{qty}", True, (60, 60, 60)), (detail_x, inv_y))
                inv_y += 14
            total_val = player.inventory.total_value()
            screen.blit(font_s.render(f"Inventory value: {total_val}g", True, (140, 100, 0)), (detail_x, inv_y))
        else:
            screen.blit(font_s.render("(empty)", True, (120, 120, 120)), (detail_x, inv_y))

        # Message area
        if self.message_timer > 0:
            self.message_timer -= 1
            msg_color = (0, 120, 0) if "Bought" in self.message or "Sold" in self.message else (180, 0, 0)
            msg_txt = font_m.render(self.message, True, msg_color)
            msg_rect = msg_txt.get_rect(center=(panel.centerx, panel.y + panel.height - 30))
            pygame.draw.rect(screen, (255, 255, 220), msg_rect.inflate(20, 8))
            screen.blit(msg_txt, msg_rect)
        else:
            hint = font_s.render("Press E to close store", True, (120, 80, 40))
            screen.blit(hint, (panel.x + 20, panel.y + panel.height - 22))
