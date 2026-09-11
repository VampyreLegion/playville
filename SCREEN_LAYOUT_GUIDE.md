# Screen Layout Guide

## Screen Dimensions

Defined in `config.py`:

```python
SCREEN_WIDTH = 2300
SCREEN_HEIGHT = 1024
SIDEBAR_WIDTH = 500
```

`GAME_WIDTH = SCREEN_WIDTH - SIDEBAR_WIDTH = 1800`

In `main.py`:
```python
GAME_WIDTH = SCREEN_WIDTH - SIDEBAR_WIDTH  # 1800
WIDTH, HEIGHT = SCREEN_WIDTH, SCREEN_HEIGHT
```

---

## Layout Regions

```
┌─────────────────────────────────────────────────────────┬─────────────┐
│                                                         │             │
│                  GAME AREA (1800 x 1024)                │  SIDEBAR    │
│                                                         │  (500 x     │
│  - Procedurally generated town map (map_generator.py)  │   1024)     │
│  - NPCs moving around                                   │             │
│  - Player character (blue sprite, WASD movement)        │ • Keys hint │
│  - Clickable locations                                  │ • AI model  │
│                                                         │ • Gold      │
│                                                         │ • Chronicle  │
│                                                         │ • Legend    │
│                                                         │ • Whispers  │
│                                                         │ • Stories   │
│                                                         │ • Town Mood │
│                                                         │ • Social Log│
│                                                         │             │
├─────────────────────────────────────────────────────────┤             │
│  DETAIL PANE (1700 x 320) - 4 columns                  │             │
│  [Bio/Goal/Wish] [Thoughts/Relationships] [Secrets/Trust] [Themes]   │
└─────────────────────────────────────────────────────────┴─────────────┘
```

Coordinates: Game area `0→1800 (x)`, Sidebar `1800→2300 (x)`, Full height `0→1024 (y)`.

---

## Procedural Town Map (`map_generator.py`)

The map is generated at startup by `generate_town_map(width=1800, height=1024)` and replaces
the static `map.png`. Features:

- **Background**: medium green grass
- **Roads**: tan/dirt colored paths connecting all buildings
- **Buildings**: filled rectangles with darker roof strip, border, door, and windows
- **Labels**: white text below each building
- **Trees**: dark green circles scattered across the map
- **Graveyard**: enclosed with fence and gravestones

---

## Location Coordinates

```python
LOCATIONS = {
    "store":        (220,  820),
    "courthouse":   (900,  280),
    "jail":         (1520, 200),
    "library":      (1520, 420),
    "factory":      (480,  820),
    "graveyard":    (120,  150),
    "doctor":       (350,  400),
    "town_square":  (900,  600),
    "player_house": (700,  750),
}
```

Courthouse clickable area: `pygame.Rect(800, 100, 250, 250)`

---

## Player Character

The player is a blue-outfit sprite (`player.py`) starting at `(700, 750)` (Player House).

- **Sprite**: 40x40 pixel hand-drawn character with blue body and visible eyes
- **Label**: "YOU" in yellow, displayed above the sprite
- **Gold display**: current gold shown in gold color below the sprite
- **Store prompt**: "[E] Enter Store" shown above when within 80px of the General Store
- **Movement**: WASD or Arrow keys; constrained to game area bounds

---

## Keybindings

| Key | Action |
|-----|--------|
| **WASD / Arrow Keys** | Move player character |
| **E** (near store) | Open the General Store |
| **ESC** | Close overlays (store, newspaper, graph, help) |
| **C** | Toggle NPC thought/conversation window |
| **N** | Toggle newspaper overlay (generates one if needed) |
| **G** | Toggle social network graph overlay |
| **F1** | Toggle help screen |
| **UP arrow** | Scroll newspaper up / help overlay up |
| **DOWN arrow** | Scroll newspaper down / help overlay down |
| **TAB** (in store) | Switch between Buy and Sell tabs |
| **UP/DOWN** (in store) | Navigate item list |
| **ENTER / E** (in store) | Confirm buy or sell |
| Click NPC sprite | Select NPC, show detail pane |
| Click courthouse | Open memory journal popup |
| Click anywhere else | Deselect NPC, close journal |

---

## Startup: Ollama Model Selector

Before the game starts, a full-screen model selection screen appears (`ollama_selector.py`):

- Queries `ollama list` to get installed models
- Displays a scrollable list of models
- Shows previously selected model highlighted in green
- Type to search/filter models
- UP/DOWN to navigate, ENTER to confirm, ESC to use previous/default
- Selected model is saved to `ollama_config.json` and passed to `PlayvilleGame.selected_model`

---

## Overlays

### General Store (E key near store)

- Position: `(150, 80)`, Size: `1400 x 860`
- Parchment-colored semi-transparent background
- **Left panel**: scrollable item list (Buy or Sell tab)
  - Color dot, item name, price, quantity owned
  - Selected item highlighted in light green
- **Right panel**: selected item details
  - Icon, name, category, buy/sell price, description
  - Recent transaction log (last 8)
  - Inventory summary (up to 6 items + total value)
- **Bottom**: feedback message (green=success, red=error) or "Press E to close store"
- TAB switches Buy/Sell; UP/DOWN navigate; ENTER/E confirms; ESC closes

### Help Overlay (F1 key)

- Position: `(100, 40)`, Size: `SCREEN_WIDTH-600 x SCREEN_HEIGHT-80` (leaves sidebar visible)
- Dark navy semi-transparent background (alpha 250)
- Blue border
- Two-column layout with 8 sections:
  - Movement & Interaction, Overlay Toggles, Newspaper Navigation, Store Navigation
  - Social Graph, NPC Status Dots, AI Model, Tips
- F1 or ESC to close; UP/DOWN to scroll

### Conversation Window (C key)

- Position: `(50, 50)`, Size: `1100 x 900`
- Semi-transparent dark background (alpha 240)
- Shows last 10 NPC thought entries with full components:
  - Observation (blue-white)
  - Interpretation with "↳" prefix (warm orange)
  - Decision with "→" prefix (light green)
  - Goal, internal reflection, opinion expression if present
- Hidden automatically when newspaper, social graph, or store is open

### Newspaper Overlay (N key)

- Position: `(100, 50)`, Size: `GAME_WIDTH-200 x HEIGHT-100` (1600 x 924)
- Semi-transparent parchment background (alpha 245)
- Scrollable with UP/DOWN arrow keys
- Format: `format_newspaper_for_display()` from `newspaper.py`
- Header shows: "THE PLAYVILLE CHRONICLE - Press N to close"
- Footer shows: "Scroll: UP/DOWN arrows"

### Social Graph Overlay (G key)

- Covers full game area `(0, 0)` to `(GAME_WIDTH, HEIGHT)`
- Dark overlay (alpha 230) behind the graph
- Physics simulation runs every frame (2 iterations)
- Network stats shown at bottom: total links, friendships, rivalries, density
- Click to select nodes; hover to highlight
- Closed automatically when newspaper opens; newspaper closes when graph opens

### Journal Popup (click courthouse)

- Position: `(300, 150)`, Size: `1200 x 500`
- Parchment background, dark red border
- Shows last 18 ChromaDB memory entries
- Hidden when newspaper or social graph is open

---

## Sidebar Layout (top to bottom)

1. **Keybinding hint** - "C=Thoughts N=Paper G=Graph E=Store F1=Help"
2. **AI model** - "AI: <selected_model_name>" in green
3. **Player gold** - "Your Gold: Ng" in gold color
4. **Chronicle indicator** - "Chronicle Edition #N available" (when published)
5. **Status Legend** - Green/Red/Blue dots with labels
6. **Town Whispers** - Up to 2 consensus wishes in gold text
7. **Emerging Stories** - Up to 2 keyword-based story threads
8. **Town Mood** - Top 3 opinion categories with +/- scores and icons
9. **Global Social Log** - Up to 22 entries, word-wrapped at 75 chars, emotion-colored

---

## Detail Pane (bottom, when NPC selected)

Position: `(50, 650)`, Size: `1700 x 320`

### Column Layout

**Left column (x offset ~20):**
- Name, age, occupation, emotional state
- Short bio
- Personality traits (up to 3)
- Core values (up to 4)
- Current goal
- Dominant opinion (color-coded)
- Most recent wish
- Background text (3 word-wrapped lines, 75 chars each)

**Middle-left column (x offset ~650):**
- Recent thoughts (up to 4, color-coded green/red)
- Relationships (up to 5, with score and depth indicator)

**Middle-right column (x offset ~1050):**
- Secrets (up to 4, truncated at 43 chars)
- Trust network (up to 5 entries, green=trusted/red=distrusted)

**Right column (x offset ~1450):**
- Memory themes (active themes with memory counts)

---

## NPC Visual Indicators

Each NPC sprite has:
- **Status dot** (above sprite): Green=cleared, Red=suspicious/guilty, Blue=investigating
- **White outer ring** on dot for visibility
- **Selection ring** (when selected): Color depends on emotional state
  - calm=blue, happy=green, anxious=orange, angry=red
- **Name label** (below sprite): white text on black background

---

## Fonts

```python
font_s = pygame.font.SysFont("Arial", 12)         # Body text
font_m = pygame.font.SysFont("Arial", 16, bold=True)  # Headers
```

---

## Recommended Display

- Minimum: 2300 x 1024
- Recommended: 2560 x 1440
- The window is not resizable at runtime; dimensions are set at launch.
