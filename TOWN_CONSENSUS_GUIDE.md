# Town Consensus & Living Society Guide

## Overview

Playville tracks collective NPC sentiment through two parallel systems:
1. **WishTracker** - detects when multiple NPCs share the same wish
2. **Opinion Distribution** - aggregates per-category sentiment across all NPCs

Both systems update in real time as NPCs think and interact.

---

## NPC Opinions System

Every NPC carries opinions on 5 town categories, initialized randomly in -20 to +20:

| Category | Meaning |
|----------|---------|
| `town_economy` | How the NPC views economic conditions |
| `safety` | How safe the NPC feels |
| `infrastructure` | NPC satisfaction with buildings/services |
| `leadership` | NPC trust in town leadership |
| `community` | NPC sense of social connection |

### Opinion Drift

Every think cycle, each opinion drifts by a small random amount (configured in
`config.py` as `OPINION_DRIFT_MAX = 3`):

```python
drift = random.randint(-2, 2)
if "paranoid" in personality_traits and category == "safety":
    drift -= 1
if "ambitious" in personality_traits and category in ["town_economy", "leadership"]:
    drift += random.choice([-1, 0, 1])
```

Changes are bounded to -100 to +100.

### Opinion Influence via Gossip

When two gossipy NPCs are near each other:
```python
diff = other_npc.town_opinions[category] - self.town_opinions[category]
influence = int(diff * 0.1)  # 10% pull
self.town_opinions[category] += influence
```

This causes opinion clusters to form over time.

### Life Event Opinion Changes

Life events from `life_paths.py` can also shift opinions directly:
- Career change → related category changes
- Trauma → safety -10, community -10
- Burnout → leadership -15, community -10
- Personal growth → safety +10, community +10

---

## NPC Wishes System

NPCs generate wishes with a 7-10% probability per think cycle
(higher for `ambitious` and `analytical` personalities).

### Wish Categories

| Category | Example Wishes |
|----------|---------------|
| infrastructure | "The town needs a clinic expansion" |
| social | "We need more community events" |
| economy | "The store needs more supplies" |
| safety | "We need more patrols near the graveyard" |
| personal | "I wish I had a better home" |
| political | "The Mayor needs to be more transparent" |

### Wish Generation Weights

Wishes are weighted by personality traits and occupation:

| Personality | Dominant Category |
|-------------|------------------|
| suspicious | safety (40%), political (30%) |
| paranoid | safety (50%), political (25%) |
| friendly | social (40%) |
| gossipy | social (50%), political (20%) |
| ambitious | economy (40%), political (30%) |
| analytical | infrastructure (30%), economy (30%) |

Occupation also influences category weights (Doctor→infrastructure, Police→safety, etc.).

A 120-second cooldown prevents the same NPC from wishing twice in quick succession.

---

## WishTracker Class

Defined in `main.py`, the `WishTracker` class tracks wishes and detects consensus:

```python
class WishTracker:
    def __init__(self):
        self.wishes = {}       # category -> {wish_text -> [npc_names]}
        self.town_whispers = []
```

### How It Works

1. `track_wish(npc_name, category, wish)` is called from `PlayvilleGame.track_wish()`
2. The wish is stored under its category and text
3. `_check_consensus()` is called automatically
4. When `len(names) >= CONSENSUS_THRESHOLD` (default 5), a whisper dict is created

### Whisper Format

```python
{
    'category': 'safety',
    'wish': 'We need more patrols near the graveyard',
    'supporters': ['Ben Carter', 'Elias Vance', 'Dr. Aris Thorne', 'The Whisper', 'Lena Thorne'],
    'count': 5
}
```

### Retrieving Whispers

```python
whispers = self.wish_tracker.get_whispers()
```

Returns all active whispers (those meeting the threshold). Used by the newspaper
generator to populate the opinion section and headline selection.

---

## PlayvilleGame.track_wish()

This method is the entry point called from `NPC.think()`:

```python
game_obj.track_wish(self.name, wish_data)
```

It:
1. Calls `self.wish_tracker.track_wish(npc_name, category, wish_text)` (WishTracker)
2. Also maintains `self.town_wishes` dict (legacy compatibility)
3. When threshold reached, creates a display string and adds to `self.town_whispers`
4. Calls `self.add_social_log()` so the whisper appears in the sidebar

---

## get_opinion_distribution()

```python
def get_opinion_distribution(self):
    distribution = {}
    for category in ['town_economy', 'safety', 'infrastructure', 'leadership', 'community']:
        opinions = [npc.town_opinions.get(category, 0) for npc in self.npcs]
        if opinions:
            avg = sum(opinions) / len(opinions)
            distribution[category] = {
                'average': round(avg, 1),
                'sentiment': 'positive' if avg > 10 else 'negative' if avg < -10 else 'neutral',
                'count': len(opinions)
            }
    return distribution
```

Thresholds: positive = avg > 10, negative = avg < -10, neutral = in between.

Used by:
- Sidebar "Town Mood" section (top 3 categories shown)
- Newspaper opinion poll section
- Newspaper headline priority (extreme opinion = newsworthy)

---

## Sidebar Display

The sidebar shows:

### Town Whispers (gold, top of sidebar)
- Up to 2 most recent consensus wishes
- Format: "🌆 TOWN WHISPER: N residents want: '...'"
- Word-wrapped at 70 chars

### Town Mood
- Top 3 opinion categories
- 👍 positive (avg > 10), 👎 negative (avg < -10), ➖ neutral
- Score shown as signed integer (+12, -8, etc.)

---

## Configuration

In `config.py`:

```python
CONSENSUS_THRESHOLD = 5      # NPCs needed to trigger a town whisper
WISH_CHANCE = 0.07           # Base wish probability per NPC thought
OPINION_DRIFT_MAX = 3        # Max opinion drift per cycle
```

---

## Example Flow

```
[NPC thinks] Dr. Aris generates wish: "The town needs a clinic expansion"
  -> WishTracker.track_wish("Dr. Aris Thorne", "infrastructure", "The town needs a clinic expansion")
  -> wishes["infrastructure"]["The town needs a clinic expansion"] = ["Dr. Aris Thorne"]

[Later] Lena Thorne, Ben Carter, Agnes Peabody, Elias Vance each generate same wish
  -> list grows to 5

[_check_consensus] 5 >= CONSENSUS_THRESHOLD(5)
  -> town_whispers entry created:
     {'category': 'infrastructure', 'wish': '...', 'supporters': [...], 'count': 5}

[PlayvilleGame.track_wish] builds display string:
  "🌆 TOWN WHISPER: 5 residents want: 'The town needs a clinic expansion'"
  -> added to self.town_whispers
  -> logged in social log
  -> printed to console

[Next newspaper] whisper_strings passed to NewspaperGenerator
  -> may become headline: "TOWN CONSENSUS: The town needs a clinic expansion"
```

---

## Memory Themes

Each NPC thought is classified into thematic clusters by `classify_memory_theme()` in `llm_interface.py`:

| Theme | Keywords |
|-------|---------|
| safety_concern | crime, suspicious, danger, threat, unsafe, patrol |
| economic_worry | money, business, trade, economy, poor, struggling |
| suspicious_activity | GUILTY, investigate, hiding, secret, suspicious |
| town_gossip | heard, rumor, gossip, said, told |
| personal_regret | regret, mistake, guilt, sorry, failed |
| future_hope | wish, hope, dream, want, desire, better |

Active memory themes are stored on each NPC and displayed in the detail pane.
`LifePathManager` uses `npc.memory_themes['safety_concern']` to check for trauma
thresholds (5+ memories triggers trauma event check).
