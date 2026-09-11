# Playville Enhanced AI NPC System

## Overview

Playville is a Pygame-based social simulation where NPCs with deep character backgrounds
think autonomously, form opinions, express wishes, build or break relationships, and
generate emergent narratives. The player can walk around town, interact with the General
Store economy, and observe NPC AI powered by a locally-running Ollama LLM.

---

## NEW: Startup — Ollama Model Selection

At launch, before the game starts, a full-screen model selector appears (`ollama_selector.py`):

- Runs `ollama list` to detect installed models on the machine
- Displays all available models in a scrollable list
- Type to search/filter by model name
- Previously used model is highlighted and pre-selected
- UP/DOWN arrow keys to navigate; ENTER to confirm; ESC to use previous/default
- Selection is saved to `ollama_config.json` for the next session
- The selected model name is passed to `PlayvilleGame.selected_model` and displayed
  in the sidebar as "AI: <model_name>"

---

## NEW: Player Character (`player.py`)

A controllable player character is present on the map from game start:

- **Sprite**: blue-outfit 40x40 pixel character with visible face details
- **Movement**: WASD or Arrow keys; constrained to game area bounds
- **Starting position**: Player House at `(700, 750)`
- **Gold**: starts with 100g, earns/spends in the General Store
- **Reputation**: 0-100 (future: affects NPC responses)
- **Inventory**: persisted across sessions via `player_save.json`
- **Save/Load**: gold, reputation, inventory, and transaction history are auto-saved
- **Labels**: "YOU" in yellow above, gold amount in gold color below, store hint when near

### Player.update()

Called every frame when store and newspaper are closed. Handles:
- WASD/Arrow key movement
- Boundary clamping to game area
- Store proximity detection (80px radius around General Store)

---

## NEW: General Store Economy (`store.py`)

A full buy/sell economy overlay accessed by pressing E near the General Store `(220, 820)`.

### Item Catalog (`STORE_CATALOG` in `player.py`)

12 items across 4 categories:

| Category | Items |
|----------|-------|
| food | Bread (5g), Apple (3g), Water Flask (8g), Whiskey (18g) |
| tool | Lantern (25g), Rope (15g), Town Map (20g), Lockpick (40g) |
| information | Notebook (12g), Rumor Sheet (10g) |
| medicine | Medicine Kit (30g) |
| trade | Gold Nugget (50g) |

Each item has a buy price and a lower sell price.

### Store UI

- **Left panel**: item list with color dot, name, price, owned quantity
- **Right panel**: selected item details (category, buy/sell price, description)
- **Transaction log**: last 8 transactions shown in right panel
- **Inventory summary**: up to 6 items + total sell value
- **Tabs**: BUY / SELL toggled with TAB key
- **Feedback**: confirmation/error messages shown at bottom with 2-second timer

### Controls in Store

| Key | Action |
|-----|--------|
| TAB | Switch BUY/SELL tab |
| UP/DOWN | Navigate item list |
| ENTER or E | Buy/sell selected item |
| ESC | Close the store |

---

## NEW: F1 Help Overlay (`help_overlay.py`)

Press F1 at any time to toggle a comprehensive keyboard reference:

- Position: `(100, 40)` to `(SCREEN_WIDTH-500, SCREEN_HEIGHT-40)` (sidebar stays visible)
- Dark navy background with blue border
- Two-column layout covering 8 sections:
  - Movement & Interaction
  - Overlay Toggles
  - Newspaper Navigation
  - Store Navigation
  - Social Graph
  - NPC Status Dots
  - AI Model
  - Tips
- F1 or ESC to close; UP/DOWN to scroll

---

## NEW: Procedural Town Map (`map_generator.py`)

The static `map.png` has been replaced with a procedurally generated 1800x1024 surface.

### Buildings (center positions)

| Building | Position | Style |
|----------|----------|-------|
| General Store | (220, 820) | Wooden, tan/brown |
| Courthouse | (900, 280) | Grand stone, grey/white with columns |
| Jail | (1520, 200) | Dark stone, grey with bars |
| Library | (1520, 420) | Brick, dark red |
| Factory | (480, 820) | Industrial dark grey with smokestacks |
| Graveyard | (120, 150) | Enclosed green with fence and gravestones |
| Doctor's Office | (350, 400) | White/clean with red cross |
| Town Square | (900, 600) | Open plaza with animated fountain |
| Player House | (700, 750) | Small warm-colored house with chimney |

### Map Features

- Green grass background
- Tan/dirt road network connecting all buildings
- Trees (dark green circles) scattered around the map
- Each building has: body, darker roof strip, door, windows, label

---

## Core Systems (Existing)

### 1. Personality System

Each NPC has personality traits (from `npc_database.py`) that weight every decision:

| Trait | Behavioral Effect |
|-------|------------------|
| suspicious | Biased toward Suspicious/Hostile sentiment |
| friendly | Biased toward Friendly/Neutral sentiment |
| gossipy | Generates and spreads rumors; 30% chance to share gossip when near others |
| loyal | Forms lasting bonds; slower relationship decay |
| paranoid | Heightened threat detection; safety opinions drift negative |
| analytical | Neutral/Suspicious bias; observation-heavy thoughts |
| creative | Variable, unpredictable behavior |
| stern | Professional distance; Hostile when challenged |
| ambitious | Goal-oriented; economy/leadership opinions drift positive |
| cautious | Risk-averse; slower opinion changes |

### 2. Emotional States

Four states, driven by current sentiment:

| Sentiment | Emotion | Selection Ring Color |
|-----------|---------|---------------------|
| Friendly | happy | Green |
| Neutral | calm | Blue |
| Suspicious | anxious | Orange |
| Hostile | angry | Red |

Displayed via selection rings around NPCs and emoji in the social log.

### 3. Goal-Driven Behavior

Goals influence location choices (60% bias toward goal-relevant locations):

- **Investigate**: biased toward courthouse, jail, library
- **Avoid**: avoids courthouse and jail
- **Befriend**: proximity-seeking
- **Routine**: occupation-specific locations (Judge→courthouse, Police→jail, etc.)

Goals update every NPC think cycle with 15% probability.

### 4. Rich Relationship System

Each NPC-to-NPC relationship contains:
- `sentiment`: Hostile/Suspicious/Neutral/Friendly
- `score`: -100 to +100
- `reason`: Why they feel this way
- `history`: Timeline of relationship changes (last 15 interactions)
- `shared_experiences`: Last 10 co-location events

Score changes per interaction:
- Friendly: +15
- Neutral: 0
- Suspicious: -10
- Hostile: -20

Personality compatibility bonuses:
- Both gossipy: +5
- Both paranoid/suspicious: +3
- Both ambitious: -5 (competition)

### 5. Town Opinions System

Each NPC tracks opinions on 5 categories (-100 to +100):
- `town_economy`
- `safety`
- `infrastructure`
- `leadership`
- `community`

Opinions drift by -2 to +2 per think cycle, modified by personality.
When gossipy NPCs interact, they influence each other's opinions by 10%.

### 6. WishTracker and Town Consensus

NPCs generate wishes with 7-10% probability per think cycle. Wishes are tracked by
the `WishTracker` class in `main.py`.

When 5 or more NPCs share the same wish text, a **town whisper** is created and shown
in the sidebar. The threshold is configured in `config.py` as `CONSENSUS_THRESHOLD = 5`.

### 7. Faction System (`factions.py`)

`FactionManager` groups NPCs by strong opinions (absolute score > 25) into named factions:

- Town Watch Coalition (safety positive)
- Concerned Citizens Alliance (safety negative)
- Prosperity League (economy positive)
- Economic Revivalists (economy negative)
- Mayoral Support Committee (leadership positive)
- Reform Coalition (leadership negative)
- Community Builders (community positive)
- and more...

Factions update every 300 frames (~5 seconds at 60 FPS). Minimum 2 NPCs needed to form
a faction. Faction membership is passed to social graph node coloring and newspaper generation.

### 8. Life Paths System (`life_paths.py`)

Checks every 600 seconds for life-changing events:

- Career changes (doctor becomes activist, business owner closes shop)
- Relationship milestones (best friends, bitter enemies)
- Trauma development (paranoid trait added)
- Burnout (for leadership roles under negative opinion pressure)
- Faction leadership (ambitious NPCs become organizers)
- Personal growth (overcoming past trauma)

Events are logged in the social log and printed to console.

### 9. Memory System (ChromaDB)

Every NPC thought is stored in ChromaDB with metadata:
- speaker, timestamp, importance (0-100)
- is_suspicious, sentiment, emotional_state
- nearby_npc, goal_related, current_goal
- gossip, memory_themes, wish_category, wish_content

On next think cycle, NPCs retrieve 5 recent memories and 3 relationship-specific memories
to inform their current thought.

### 10. Multi-Layered Thought Generation

Each think cycle generates a thought with 9 layers:
1. Memory retrieval (ChromaDB)
2. Internal reflection (30% chance, personality-driven)
3. Core thought via `get_npc_thought()` (llm_interface.py / Ollama)
4. Relationship-depth addendum
5. Personality observations
6. Secrets/fears references (10% chance)
7. State update (emotion, goal, opinions, memory themes, wishes)
8. Relationship update (score change, history)
9. Social log entry + conversation window entry

### 11. Police Investigation

Ben Carter cross-references ChromaDB for suspicious patterns, finds the most-mentioned
suspicious location, and moves there to investigate.

### 12. Newspaper (`newspaper.py`)

Published every 300 seconds. Sections: headline, events, faction watch, opinion poll
(dynamic NPC count), crime report, gossip column, NPC interview, development, weather.
Press N to view.

### 13. Social Network Graph (`social_network.py`)

Force-directed graph of all NPC relationships. Nodes colored by faction. Edges colored
by relationship type. Press G to view. Click nodes to inspect.

---

## Integrated Systems Map

```
Startup Model Selector  -->  PlayvilleGame.selected_model
                                    |
                          NPC Database (SQLite) --> NPC objects
                                    |
                          Player (WASD) <--> General Store
                                    |
                    +---------+-----+------+
                    |                     |
              think() cycle          FactionManager
                    |               (every 300f)
         +----------+---------+
         |          |         |
   ChromaDB    opinion_changes  wishes
   memories    to town_opinions  to WishTracker
                    |
              LifePathManager
              (every 600 real seconds)
                    |
             NewspaperGenerator
             (every 300 real seconds)
                    |
             display via N key
```

---

## Configuration

All tunable parameters are in `config.py`:

```python
AUTONOMOUS_INTERVAL = 1200   # frames between NPC thoughts (~20s at 60FPS)
WISH_CHANCE = 0.07           # base wish probability per thought
GOSSIP_CHANCE = 0.30         # gossip sharing probability
NEWSPAPER_INTERVAL = 300     # seconds between newspaper editions
FACTION_FORMATION_THRESHOLD = 2  # min NPCs to form faction
FACTION_OPINION_THRESHOLD = 25   # min abs(opinion) to qualify
LIFE_PATH_CHECK_INTERVAL = 600   # seconds between life event checks
CONSENSUS_THRESHOLD = 5      # NPCs needed for town whisper

# Player economy
PLAYER_START_GOLD = 100
PLAYER_START_POS = (700, 750)
STORE_INTERACTION_RADIUS = 80

# Ollama
DEFAULT_MODEL = "llama3.1:8b"
OLLAMA_CONFIG_FILE = "ollama_config.json"
```

---

## Getting Started

```bash
python3 main.py
```

1. Select an Ollama model from the startup screen (UP/DOWN + ENTER)
2. Move around town with WASD
3. Walk near the General Store and press E to buy/sell items
4. Click NPCs to view their detail pane
5. Watch the sidebar for faction/opinion/whisper updates
6. Press F1 for the full keyboard reference
7. Press C to toggle the NPC thought window
8. Press N to read the newspaper
9. Press G to view the social network graph
10. Click the courthouse to open the memory journal
