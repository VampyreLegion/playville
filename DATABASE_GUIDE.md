# NPC Database System Guide

## Overview

Playville uses a **SQLite database** (`npc_data.db`) to store static NPC character data,
and **ChromaDB** (`chroma_data/`) for dynamic vector memory.

The database schema has not changed from its initial design. This guide reflects the
current implementation.

---

## Database Schema

### NPCs Table

```sql
npcs (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT
    name                TEXT UNIQUE NOT NULL
    sprite_rect         TEXT    -- JSON [x, y, w, h]
    home_position       TEXT    -- JSON [x, y]

    -- Core Identity
    short_bio           TEXT NOT NULL
    full_background     TEXT
    age                 INTEGER
    occupation          TEXT

    -- Personality & Psychology
    personality_traits  TEXT    -- JSON list
    core_values         TEXT    -- JSON list
    fears               TEXT    -- JSON list
    desires             TEXT    -- JSON list

    -- History & Secrets
    personal_history    TEXT
    secrets             TEXT    -- JSON list
    guilty_conscience   TEXT

    -- Social Dynamics
    social_status       TEXT    -- high/middle/low
    reputation          TEXT

    -- Behavioral Patterns
    daily_routine       TEXT    -- JSON dict
    habits              TEXT    -- JSON list
    speech_patterns     TEXT

    -- Metadata
    is_active           BOOLEAN DEFAULT 1
    created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    updated_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
```

### Relationships Table

```sql
npc_relationships (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT
    npc_name            TEXT NOT NULL
    target_name         TEXT NOT NULL
    preset_sentiment    TEXT    -- Hostile/Suspicious/Neutral/Friendly
    preset_score        INTEGER -- -100 to +100
    relationship_history TEXT
    shared_history      TEXT
    UNIQUE(npc_name, target_name)
)
```

### Knowledge Table

```sql
npc_knowledge (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT
    npc_name            TEXT NOT NULL
    knowledge_type      TEXT    -- rumor/fact/observation
    content             TEXT NOT NULL
    source              TEXT
    reliability         INTEGER -- 0-100
    timestamp           TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
```

---

## Default NPCs (11 total, 6 active by default)

The database is populated by `populate_default_npcs()` in `npc_database.py` on first run.
All 11 NPCs are created, but `PlayvilleGame.__init__` deactivates all except:

| NPC | Occupation | Personality |
|-----|-----------|-------------|
| Elias Vance | Judge | stern, analytical, suspicious |
| Lena Thorne | Mayor | ambitious, cautious, friendly |
| Ben Carter | Police Chief | suspicious, loyal, stern |
| Agnes Peabody | Librarian | gossipy, analytical, friendly |
| Dr. Aris Thorne | Doctor | paranoid, analytical, cautious |
| The Whisper | Unknown | paranoid, suspicious, analytical |

The inactive NPCs (Marco Rossi, Kai, Bea Miller, Silas Blackwood, Leo Jensen) remain
in the database and can be reactivated.

---

## Quick Start

```bash
# First run: auto-populates database
python3 main.py

# Inspect database directly
python3 npc_database.py
```

---

## Managing NPCs

### View all active NPCs

```python
from npc_database import NPCDatabase
db = NPCDatabase()
npcs = db.get_all_active_npcs()
for npc in npcs:
    print(f"{npc['name']}: {npc['occupation']}")
```

### Add a new NPC

```python
new_npc = {
    'name': 'Sarah Chen',
    'sprite_rect': [512, 512, 256, 256],
    'home_position': [400, 600],
    'age': 31,
    'occupation': 'Journalist',
    'short_bio': 'Investigative reporter searching for the truth.',
    'full_background': 'Sarah came to Playville following a lead about local corruption...',
    'personality_traits': ['analytical', 'suspicious', 'ambitious'],
    'core_values': ['truth', 'justice', 'integrity'],
    'fears': ['being silenced', 'missing the story'],
    'desires': ['expose the truth', 'make a difference'],
    'personal_history': 'Grew up in the city, daughter of immigrants...',
    'secrets': ['Found evidence linking the Mayor to irregularities'],
    'guilty_conscience': 'A source was killed after she published a story',
    'social_status': 'middle',
    'reputation': 'troublemaker but respected',
    'daily_routine': {'morning': 'library', 'afternoon': 'courthouse', 'evening': 'store'},
    'habits': ['takes extensive notes', 'asks pointed questions'],
    'speech_patterns': 'Direct, asks why a lot'
}
db.add_npc(new_npc)
```

### Activate/Deactivate NPCs

```python
db.deactivate_npc('Sarah Chen')  # Remove from simulation (data preserved)
db.activate_npc('Sarah Chen')    # Re-add to simulation
```

To add a reactivated NPC to the game, add their name to the `ACTIVE_NPC_NAMES` list
in `PlayvilleGame.__init__` before starting.

### Preset Relationships

```python
db.add_relationship('Sarah Chen', 'Lena Thorne', {
    'sentiment': 'Suspicious',
    'score': -40,
    'shared_history': 'Sarah is investigating Lena for financial irregularities'
})
```

---

## Database vs Vector Memory

| | SQLite (`npc_data.db`) | ChromaDB (`chroma_data/`) |
|--|------------------------|--------------------------|
| What | Static character data | Dynamic thought memories |
| When | Loaded at startup | Written every NPC think cycle |
| Changes | No (during gameplay) | Yes (constantly) |
| Defines | Who NPCs ARE | What NPCs DO and THINK |

ChromaDB path is configured in `config.py`:
```python
CHROMA_PERSIST_PATH = "./chroma_data"
```

---

## NPC Attributes at Runtime

When NPC objects are created, these attributes come from the database:
- `name`, `bio`, `full_background`, `age`, `occupation`
- `personality` (list of traits)
- `core_values`, `fears`, `desires`, `secrets`
- `personal_history`

These attributes are initialized fresh each session (not from the database):
- `town_opinions` (random -20 to +20 for each category)
- `relationships` (loaded from preset data, then evolved during gameplay)
- `emotional_state`, `current_goal`, `trust_network`
- `memory_themes`, `wishes_expressed`, `gossip_heard`

---

## Tips

### Writing Good Backstories

- `full_background`: 200-500 words with internal conflict
- `secrets`: 2-4 consequential secrets per NPC
- Link NPCs through `shared_history` in the relationships table
- Give each NPC clear `fears` and `desires` that create tension

### Personality Trait Dynamics

Good combinations create emergent behavior:
- `paranoid + friendly` = likeable but anxious
- `ambitious + cautious` = strategic, careful risk-taker
- `gossipy + analytical` = information broker

Available traits: `suspicious`, `friendly`, `gossipy`, `loyal`, `paranoid`,
`analytical`, `creative`, `stern`, `ambitious`, `cautious`
