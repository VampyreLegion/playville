# Advanced Narrative Systems Guide

## Overview

Playville integrates four narrative systems that transform it from a simulation into a living story engine:

1. **Town Newspaper** - Daily digest of town life (press N)
2. **Social Network Visualization** - Interactive relationship graph (press G)
3. **Life Paths** - Multi-year character arcs
4. **WishTracker + Opinion Distribution** - Collective will and mood tracking

All systems are active and integrated into `main.py` through `PlayvilleGame`.

---

## SYSTEM 1: Town Newspaper (`newspaper.py`)

### What It Does

Generates a newspaper every 300 seconds (5 minutes of real time = 1 in-game day).
The newspaper summarizes:

- Major events (passed in from game state)
- Faction activity
- Town opinion poll
- Crime and safety report
- Rumors and gossip (from gossipy NPCs)
- NPC spotlight interview
- Town development log
- Weather and mood

### How It Works

`NewspaperGenerator` is initialized in `PlayvilleGame.__init__`:

```python
self.newspaper_generator = NewspaperGenerator()
self.current_newspaper = None
```

Each frame, the game loop checks `should_publish()`. When true, it calls:

```python
self.current_newspaper = self.newspaper_generator.generate_newspaper(
    npcs=self.npcs,
    events=[],
    factions=self.faction_manager,
    town_whispers=whisper_strings,
    opinion_dist=self.get_opinion_distribution(),
    evolution_log=[]
)
```

The `opinion_dist` parameter is populated dynamically from `get_opinion_distribution()`,
which returns per-category averages and counts across all active NPCs.

### Player Interaction

- Press **N** to open or close the newspaper overlay.
- Press **UP/DOWN arrow** to scroll the newspaper.
- A new newspaper is auto-generated on first N press if none exists yet.
- The sidebar shows "Chronicle Edition #N available" when a paper has been published.

### Opinion Poll - Dynamic NPC Count

The methodology line in the Opinion Poll section reads the actual count from
`opinion_dist[category]['count']`, not a hardcoded number.

---

## SYSTEM 2: Social Network Visualization (`social_network.py`)

### What It Does

Renders an interactive force-directed graph showing:
- Friendships (green edges, score > 30)
- Rivalries (red edges, score < -30)
- Positive acquaintances (light green)
- Negative acquaintances (light red)
- Trust relationships (thick lines)
- Gossip chains (gold dashed lines between gossipy + trusted NPCs)
- Faction membership (node colors)

### How It Works

`SocialNetworkGraph` is initialized in `PlayvilleGame.__init__`:

```python
self.social_graph = SocialNetworkGraph(GAME_WIDTH, HEIGHT)
self.show_social_graph = False
```

When toggled on (G key), `build_graph(self.npcs, self.faction_manager)` is called
and the graph is rebuilt from current NPC relationship data.

Physics simulation (force-directed layout) runs each frame when the graph is visible.

### Player Interaction

- Press **G** to open or close the social graph overlay.
- Click a node to select it and view its relationship summary panel.
- Hover over nodes to highlight them.
- Network statistics (total links, friendships, rivalries, density) shown at the bottom.
- The graph is also rebuilt whenever factions update (every 300 frames).

---

## SYSTEM 3: Life Paths (`life_paths.py`)

### What It Does

`LifePathManager` checks all NPCs every 600 seconds for life event triggers.
Life events modify NPC attributes directly (`occupation`, `personality`, `town_opinions`,
`current_goal`).

### Event Types

| Event | Trigger |
|-------|---------|
| Career Change | 5% base chance + occupation/opinion thresholds |
| Friendship Deepened | 10% chance + relationship score > 40 |
| Rivalry Intensified | 10% chance + relationship score < -50 |
| Trauma | Safety opinion < -60 + 5+ safety memories |
| Burnout | Leadership job + leadership opinion < -50 |
| Faction Leadership | Ambitious trait + in a faction + 15% chance |
| Personal Growth | Has paranoid trait + safety opinion > 30 |

### Integration in main.py

`LifePathManager` is initialized in `PlayvilleGame.__init__`:

```python
self.life_path_manager = LifePathManager()
```

In the game loop, each frame:

```python
life_events = self.life_path_manager.check_and_trigger_events(
    self.npcs, self.faction_manager
)
for event_data in life_events:
    desc = event_data['event'].description
    self.add_social_log(f"LIFE EVENT: {event_data['npc']} - {desc[:60]}")
```

`LifePathManager` enforces its own 600-second cooldown internally so this call
is cheap on most frames.

### Effects Applied

`LifeEvent.apply_to_npc(npc)` modifies:
- `npc.occupation` (career changes)
- `npc.town_opinions[category]` (opinion shifts, clamped -100 to +100)
- `npc.personality` (trait additions)
- `npc.current_goal` (new life goal)

---

## SYSTEM 4: WishTracker and Opinion Distribution

### WishTracker

`WishTracker` is a standalone class defined in `main.py`. It tracks which NPCs
have expressed which wishes, by category.

```python
self.wish_tracker = WishTracker()
```

When an NPC generates a wish (7-10% chance per thought), `PlayvilleGame.track_wish()`
is called, which calls `self.wish_tracker.track_wish(npc_name, category, wish_text)`.

`_check_consensus()` runs automatically after each new wish. When 5+ NPCs share
the same wish text, a `town_whispers` entry is created:

```python
{
    'category': 'safety',
    'wish': 'We need more patrols near the graveyard',
    'supporters': ['Ben Carter', 'Elias Vance', ...],
    'count': 5
}
```

Whisper strings are passed to newspaper generation and shown in the sidebar.

### get_opinion_distribution()

Returns per-category sentiment and average across all active NPCs:

```python
{
    'town_economy': {'average': -12.3, 'sentiment': 'negative', 'count': 6},
    'safety': {'average': 4.0, 'sentiment': 'neutral', 'count': 6},
    ...
}
```

Thresholds: `positive` if avg > 10, `negative` if avg < -10, `neutral` otherwise.

Used by: sidebar Town Mood display, newspaper opinion poll.

---

## Data Flow

```
NPC thinks (llm_interface.py)
    -> opinion_changes applied to npc.town_opinions
    -> wish generated -> WishTracker.track_wish()
    -> gossip -> gossip_heard list
    -> memory stored in ChromaDB

Every 300 frames:
    -> FactionManager.update_factions(npcs)
    -> SocialNetworkGraph rebuilt (if visible)

Every 600 real seconds:
    -> LifePathManager.check_and_trigger_events()
    -> NPC attributes updated

Every 300 real seconds:
    -> NewspaperGenerator.generate_newspaper()
    -> current_newspaper set, sidebar updated

Player presses N:
    -> Newspaper overlay shown
Player presses G:
    -> Social graph overlay shown
```

---

## Keybindings

| Key | Action |
|-----|--------|
| C | Toggle NPC thought/conversation window |
| N | Toggle newspaper overlay |
| G | Toggle social network graph |
| UP/DOWN | Scroll newspaper (when open) |
| Click NPC | Select NPC, show detail pane |
| Click courthouse | Open memory journal |
