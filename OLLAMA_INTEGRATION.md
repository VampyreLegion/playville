# Ollama / Local LLM Integration Guide

## Current State

Playville currently uses a **rule-based cognition system** in `llm_interface.py`.
There is no LLM dependency at runtime. The system uses:

- Personality-weighted random sentiment selection
- Occupation and personality-specific thought templates
- Weighted random location choice (goal-influenced)
- Opinion drift with random variance
- Wish generation via category-weighted random selection

This is intentional - the rule-based system runs in milliseconds, requires no
external services, and produces consistent, character-appropriate behavior.

---

## Rule-Based System Architecture (`llm_interface.py`)

### Input

```python
get_npc_thought(
    name, bio, collection, nearby_npc, event,
    personality_traits, current_goal, emotional_state,
    relationship_history, secrets_known, occupation,
    core_values, fears, town_opinions
)
```

### Processing Steps

1. **Memory retrieval** - Query ChromaDB for 5 recent memories + 3 relationship memories
2. **Sentiment decision** - Weighted random based on personality traits
3. **Emotion update** - Derived from sentiment (Friendly→happy, Hostile→angry, etc.)
4. **Opinion drift** - Each category drifts -2 to +2, personality-modified
5. **Location decision** - Random with goal-based bias
6. **Thought generation** - Templates selected by occupation, personality, sentiment
7. **Suspicion flag** - Based on sentiment and personality
8. **Goal update** - 15% chance to generate new goal
9. **Wish generation** - 7-10% chance based on personality
10. **Memory storage** - Full metadata stored to ChromaDB

### Return Value

```python
{
    "thought": str,
    "thought_components": {
        "observation": str,
        "interpretation": str,
        "emotional_reaction": str,
        "decision": str
    },
    "location": str,
    "nearby_npc": str | None,
    "sentiment": str,
    "emotion": str,
    "new_goal": str | None,
    "gossip": str | None,
    "importance": int,
    "is_suspicious": bool,
    "opinion_changes": dict,
    "opinion_expression": str | None,
    "wish": dict | None,
    "memory_themes": list
}
```

---

## Path to LLM Integration

The rule-based system is designed to be replaced or augmented with an LLM.
The function signature and return format are stable.

### Option 1: Full Replacement

Replace the template logic inside `get_npc_thought()` with Ollama calls:

```python
try:
    from ollama_interface import generate_with_fallback
    LLM_AVAILABLE = True
except ImportError:
    LLM_AVAILABLE = False
```

If `LLM_AVAILABLE`, build a prompt from the NPC context and call Ollama.
Parse the JSON response and map it to the existing return dict.

### Option 2: Hybrid (Recommended)

Keep the rule-based system for:
- Location pathfinding
- Sentiment weights
- Goal selection
- Opinion drift

Add LLM only for:
- Thought phrasing (`interpretation` field)
- Wish generation text
- Opinion expression text

### Prompt Template

```
You are {name}, {age}, {occupation} in Playville.

BACKGROUND: {full_background}

PERSONALITY: {', '.join(personality_traits)}
CURRENT EMOTION: {emotional_state}
CURRENT GOAL: {current_goal}

SITUATION:
- Heading to: {location}
- Nearby: {nearby_npc or 'No one'}

TOWN OPINIONS (yours):
{json.dumps(town_opinions, indent=2)}

Generate a 1-2 sentence internal thought. Respond in JSON:
{"thought": "...", "opinion_expression": "optional comment on town conditions"}
```

### Recommended Models

| Model | Speed | Quality | Use Case |
|-------|-------|---------|---------|
| phi3:mini | ~1s | Good | Background NPCs |
| gemma3:12b | ~2-3s | Very good | Main NPCs |
| qwen2.5:14b | ~4-6s | Excellent | Key moments |

---

## Installing Ollama (When Ready)

```bash
# Linux/macOS
curl -fsSL https://ollama.com/install.sh | sh

# Pull a model
ollama pull gemma3:12b

# Install Python client
pip install ollama

# Test
ollama run gemma3:12b "Hello, respond in one sentence."
```

---

## Error Handling Pattern

The current rule-based system always succeeds. When adding LLM calls,
use this fallback pattern:

```python
def get_npc_thought_llm(name, context):
    try:
        import ollama
        response = ollama.generate(model='gemma3:12b', prompt=context)
        return json.loads(response['response'])
    except Exception as e:
        print(f"[WARNING] LLM failed for {name}: {e}")
        return None  # Caller falls back to rule-based

# In get_npc_thought():
llm_result = get_npc_thought_llm(name, prompt)
if llm_result and 'thought' in llm_result:
    interpretation = llm_result['thought']
# else: continue with existing template-based interpretation
```

---

## Performance Considerations

- NPCs think every 1200 frames (~20 seconds at 60 FPS)
- With 6 active NPCs, that is at most 1 LLM call every ~3 seconds
- Threading is already used for NPC thinking (`threading.Thread`)
- LLM calls must happen inside the thread to avoid blocking the game loop

---

## Current Limitations of Rule-Based System

- Thought templates are finite and repeat over long sessions
- Cannot reference specific recent events with natural language
- Opinion expressions are simple template strings
- Gossip topics are from a fixed list

These are the best areas for LLM enhancement when it is added.
