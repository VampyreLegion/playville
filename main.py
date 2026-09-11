import pygame
import sys
import chromadb
import random
import threading
import time
from llm_interface import get_npc_thought
from npc_database import NPCDatabase, populate_default_npcs
from factions import FactionManager
from life_paths import LifePathManager
from newspaper import NewspaperGenerator, format_newspaper_for_display
from social_network import SocialNetworkGraph
from config import (
    SCREEN_WIDTH,
    SCREEN_HEIGHT,
    SIDEBAR_WIDTH,
    FPS as CONFIG_FPS,
    AUTONOMOUS_INTERVAL as CONFIG_AUTONOMOUS_INTERVAL,
    NEWSPAPER_INTERVAL,
    MAX_NEWSPAPER_EDITIONS,
    FACTION_FORMATION_THRESHOLD,
    FACTION_OPINION_THRESHOLD,
    LIFE_PATH_CHECK_INTERVAL,
    CONSENSUS_THRESHOLD,
    CHROMA_PERSIST_PATH,
    FRAMES_PER_GAME_WEEK,
    SALARY_TIERS,
    COURT_PHASE_DURATION,
)
from map_generator import generate_town_map
from ollama_selector import OllamaModelSelector
from help_overlay import HelpOverlay
from bank_system import BankSystem
from court import CourtCaseManager
from town_events import TownEventManager, NPCActivityManager

# --- SETTINGS ---
# CONTEMPLATIVE MODE: 6 NPCs with EXTREMELY DEEP interactions
# This allows for:
# - Very slow, deliberate thinking (every 20 seconds per NPC)
# - Multi-paragraph internal monologues with real depth
# - Plenty of time to read and absorb each complete thought
# - NPCs can remember and reference past conversations
# - Character development unfolds naturally over time
# - Each thought is a complete narrative moment

GAME_WIDTH = SCREEN_WIDTH - SIDEBAR_WIDTH  # 1800
WIDTH, HEIGHT = SCREEN_WIDTH, SCREEN_HEIGHT
FPS = CONFIG_FPS
AUTONOMOUS_INTERVAL = CONFIG_AUTONOMOUS_INTERVAL

LOCATIONS = {
    "store": (220, 820),
    "courthouse": (900, 280),
    "jail": (1520, 200),
    "library": (1520, 420),
    "factory": (480, 820),
    "graveyard": (120, 150),
    "doctor": (350, 400),
    "town_square": (900, 600),
    "player_house": (700, 750),
    "gazette": (680, 400),
    "house_a": (1100, 750),
    "house_b": (350, 700),
    "house_c": (1300, 650),
    "house_d": (1450, 550),
    "bank": (1200, 300),
    "church": (1600, 700),
}
COURTHOUSE_RECT = pygame.Rect(800, 100, 250, 250)


class WishTracker:
    """Tracks NPC wishes and detects town consensus."""

    def __init__(self):
        self.wishes = {}  # category -> {wish_text -> [npc_names]}
        self.town_whispers = []

    def track_wish(self, npc_name, category, wish):
        if category not in self.wishes:
            self.wishes[category] = {}
        if wish not in self.wishes[category]:
            self.wishes[category][wish] = []
        if npc_name not in self.wishes[category][wish]:
            self.wishes[category][wish].append(npc_name)
        self._check_consensus()

    def _check_consensus(self, threshold=CONSENSUS_THRESHOLD):
        self.town_whispers = []
        for category, wish_dict in self.wishes.items():
            for wish, names in wish_dict.items():
                if len(names) >= threshold:
                    self.town_whispers.append(
                        {
                            "category": category,
                            "wish": wish,
                            "supporters": names,
                            "count": len(names),
                        }
                    )

    def get_whispers(self):
        return self.town_whispers


class SpeechBubble:
    """Floating speech bubble that tracks a live NPC position."""

    def __init__(
        self, npc, text, speaker_name, listener_name=None, color=None, lifetime=280
    ):
        self.npc = npc  # live reference so bubble follows the NPC
        self.text = text
        self.speaker_name = speaker_name
        self.listener_name = listener_name
        self.color = color or (255, 255, 240)
        self.lifetime = lifetime
        self.age = 0
        self.width = min(320, max(160, len(text) * 7))
        self.lines = self._wrap(text, self.width - 20)
        self.height = len(self.lines) * 16 + 20

    def _wrap(self, text, max_w):
        words = text.split()
        lines, current = [], []
        char_w = 7
        for w in words:
            current.append(w)
            if len(" ".join(current)) * char_w > max_w:
                if len(current) > 1:
                    lines.append(" ".join(current[:-1]))
                    current = [w]
                else:
                    lines.append(" ".join(current))
                    current = []
        if current:
            lines.append(" ".join(current))
        return lines or [""]

    def update(self):
        self.age += 1
        return self.age < self.lifetime

    def draw(self, surf, font):
        alpha = 255
        if self.age > self.lifetime - 60:
            alpha = int(255 * (self.lifetime - self.age) / 60)
        if self.age < 20:
            alpha = int(255 * self.age / 20)
        alpha = max(0, min(255, alpha))

        # Follow the NPC's current position
        nx = int(self.npc.pos.x)
        ny = int(self.npc.pos.y)
        bx = nx - self.width // 2
        by = ny - self.height - 55

        # Bubble background
        bubble_surf = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        border_col = (180, 160, 100) if self.listener_name else (140, 140, 180)
        pygame.draw.rect(
            bubble_surf,
            (30, 28, 22, min(220, alpha)),
            (0, 0, self.width, self.height),
            border_radius=8,
        )
        pygame.draw.rect(
            bubble_surf,
            (*border_col, alpha),
            (0, 0, self.width, self.height),
            2,
            border_radius=8,
        )

        for i, line in enumerate(self.lines):
            txt_surf = font.render(line, True, self.color[:3])
            txt_surf.set_alpha(alpha)
            bubble_surf.blit(txt_surf, (8, 6 + i * 16))

        surf.blit(bubble_surf, (bx, by))

        # Tail triangle pointing down to NPC
        tail_x = nx
        tail_tip_y = ny - 50
        tail_base_y = by + self.height
        pygame.draw.polygon(
            surf,
            (30, 28, 22),
            [
                (tail_x - 6, tail_base_y),
                (tail_x + 6, tail_base_y),
                (tail_x, tail_tip_y),
            ],
        )


class NPC:
    def __init__(self, npc_data, sheet):
        self.name = npc_data["name"]
        self.bio = npc_data["short_bio"]
        self.full_background = npc_data["full_background"]
        self.age = npc_data.get("age", "Unknown")
        self.occupation = npc_data["occupation"]

        # Extract sprite and position from database
        sprite_rect = npc_data["sprite_rect"]
        home_pos = npc_data["home_position"]

        self.pos = pygame.Vector2(home_pos)
        self.target_pos = pygame.Vector2(home_pos)
        self.full_thought = "Wandering..."
        self.thought_history = []

        # Deep AI Features from database
        self.personality = npc_data["personality_traits"]
        self.core_values = npc_data.get("core_values", [])
        self.fears = npc_data.get("fears", [])
        self.desires = npc_data.get("desires", [])
        self.secrets = npc_data.get("secrets", [])
        self.personal_history = npc_data.get("personal_history", "")

        # Town Opinions System (NEW)
        self.town_opinions = {
            "town_economy": random.randint(-20, 20),
            "safety": random.randint(-20, 20),
            "infrastructure": random.randint(-20, 20),
            "leadership": random.randint(-20, 20),
            "community": random.randint(-20, 20),
        }

        # Thematic Memory Clusters (NEW)
        self.memory_themes = {
            "safety_concern": [],
            "economic_worry": [],
            "suspicious_activity": [],
            "town_gossip": [],
            "personal_regret": [],
            "future_hope": [],
        }

        # Wishes (NEW)
        self.wishes_expressed = []  # List of wishes this NPC has expressed
        self.last_wish_time = 0

        # Initialize relationships (will be enriched with preset data later)
        self.relationships = {}
        self.emotional_state = "calm"
        self.current_goal = None
        self.trust_network = {}
        self.secrets_known = list(self.secrets)  # Start with their own secrets
        self.gossip_heard = []
        self.memory_importance_threshold = 60

        # Conversation Memory (NEW) - Track past interactions
        self.conversation_memory = {}  # {npc_name: {'last_topic': str, 'last_time': float, 'memorable_moments': []}}

        # Newspaper reading tracking
        self.last_newspaper_read = 0
        self.speech_bubble = None  # Active SpeechBubble or None (main thread only)
        self._pending_bubble = None  # Set by think() thread, applied by main thread
        self.last_spoke_to = {}  # {npc_name: timestamp} to avoid spam
        self.conversation_excerpts = []  # Short memorable quotes from past conversations

        self.gold = 0  # current cash on hand

        # Extended character data from npc_data
        self.daily_routine = npc_data.get("daily_routine", {})
        self.habits = npc_data.get("habits", [])
        self.speech_patterns = npc_data.get("speech_patterns", "")
        self.guilty_conscience = npc_data.get("guilty_conscience", "")

        self.autonomous_timer = random.randint(50, 150)
        self.sheet = sheet
        self.rect = sprite_rect
        self.image = self.extract_image()
        self.screen_rect = self.image.get_rect()

    def extract_image(self):
        temp = pygame.Surface((256, 256), pygame.SRCALPHA)
        temp.blit(self.sheet, (0, 0), self.rect)
        return pygame.transform.scale(temp, (64, 64))

    def get_full_bio_context(self):
        """Generate comprehensive bio context for deeper AI thinking"""
        context = f"""
{self.name} ({self.age}, {self.occupation})

BACKGROUND: {self.full_background}

PERSONALITY: {", ".join(self.personality)}
CORE VALUES: {", ".join(self.core_values)}
FEARS: {", ".join(self.fears)}
DESIRES: {", ".join(self.desires)}

PERSONAL HISTORY: {self.personal_history}

SECRETS THEY CARRY: {len(self.secrets)} deep secrets
        """.strip()
        return context

    def update(self, all_npcs, col, game_obj):
        move_vec = self.target_pos - self.pos
        if move_vec.length() > 5:
            self.pos += move_vec.normalize() * 2.2

        self.autonomous_timer -= 1
        if self.autonomous_timer <= 0:
            self.autonomous_timer = (
                AUTONOMOUS_INTERVAL  # uses global that depth controls
            )
            threading.Thread(
                target=self.think, args=(all_npcs, col, game_obj), daemon=True
            ).start()

        # Apply pending bubble from think() thread (main thread only)
        if self._pending_bubble:
            kind, spoken, listener_name = self._pending_bubble
            self._pending_bubble = None
            if kind == "convo":
                self.speech_bubble = SpeechBubble(
                    npc=self,
                    text=spoken,
                    speaker_name=self.name,
                    listener_name=listener_name,
                    color=(255, 255, 220),
                )
            else:
                self.speech_bubble = SpeechBubble(
                    npc=self,
                    text=spoken,
                    speaker_name=self.name,
                    color=(200, 220, 255),
                    lifetime=200,
                )

        # Update speech bubble (main thread only)
        if self.speech_bubble:
            if not self.speech_bubble.update():
                self.speech_bubble = None

    def process_social_interaction(self, other_npc, col):
        """Handle interactions between two NPCs when they're close"""
        # Exchange gossip if both are gossipy
        if "gossipy" in self.personality and "gossipy" in other_npc.personality:
            if other_npc.gossip_heard and random.random() < 0.5:
                shared_gossip = random.choice(other_npc.gossip_heard)
                if shared_gossip not in self.gossip_heard:
                    self.gossip_heard.append(shared_gossip)
                    self.secrets_known.append(
                        f"Heard from {other_npc.name}: {shared_gossip}"
                    )

            # Opinion influence (gossip affects opinions)
            if random.random() < 0.3:
                for opinion_cat in self.town_opinions.keys():
                    if opinion_cat in other_npc.town_opinions:
                        # Slight influence towards other's opinion
                        diff = (
                            other_npc.town_opinions[opinion_cat]
                            - self.town_opinions[opinion_cat]
                        )
                        influence = int(diff * 0.1)  # 10% influence
                        self.town_opinions[opinion_cat] += influence

        # Update trust based on relationship
        if other_npc.name in self.relationships:
            current_rel = self.relationships[other_npc.name]
            if current_rel["score"] > 30:
                self.trust_network[other_npc.name] = "trusted"
            elif current_rel["score"] < -30:
                self.trust_network[other_npc.name] = "distrusted"

        # Share information if trusted
        if (
            other_npc.name in self.trust_network
            and self.trust_network[other_npc.name] == "trusted"
        ):
            if self.secrets_known and random.random() < 0.3:
                secret = random.choice(self.secrets_known)
                if secret not in other_npc.secrets_known:
                    other_npc.secrets_known.append(f"Told by {self.name}: {secret}")

    def think(self, all_npcs, col, game_obj):
        """Deep, multi-layered thinking with personality, memories, relationships, and internal dialogue"""
        nearby = next(
            (o for o in all_npcs if o != self and self.pos.distance_to(o.pos) < 100),
            None,
        )

        # Use full bio context for richer thinking
        bio_context = self.get_full_bio_context()

        # LAYER 1: Retrieve relevant memories for context
        recent_memories = []
        relationship_context = {}

        try:
            # Get recent memories
            mem_query = col.query(
                query_texts=[f"{self.name}'s recent experiences and thoughts"],
                n_results=5,
                where={"speaker": self.name},
            )
            if mem_query and mem_query.get("documents"):
                recent_memories = (
                    mem_query["documents"][0] if mem_query["documents"] else []
                )

            # Get relationship-specific memories if nearby NPC
            if nearby:
                rel_query = col.query(
                    query_texts=[f"{self.name}'s history with {nearby.name}"],
                    n_results=3,
                )
                if rel_query and rel_query.get("documents"):
                    relationship_context[nearby.name] = (
                        rel_query["documents"][0] if rel_query["documents"] else []
                    )
        except Exception:
            pass  # Silent fail for memory queries

        # LAYER 2: Reflect on recent memories (internal monologue)
        internal_reflection = None
        if recent_memories and random.random() < 0.3:  # 30% chance to reflect
            memory_themes = [m for m in recent_memories if len(m) > 20]
            if memory_themes:
                recent_theme = random.choice(memory_themes)

                # Generate reflection based on personality
                if "paranoid" in self.personality or "suspicious" in self.personality:
                    reflections = [
                        f"Can't stop thinking about what I noticed earlier",
                        f"Something's been bothering me all day",
                        f"My instincts are rarely wrong about these things",
                        f"The pieces are starting to come together",
                    ]
                elif "analytical" in self.personality:
                    reflections = [
                        f"I need to examine this more carefully",
                        f"The pattern is becoming clearer",
                        f"This requires deeper analysis",
                        f"Let me think through this logically",
                    ]
                elif "gossipy" in self.personality:
                    reflections = [
                        f"Wait until I tell someone about this",
                        f"This is exactly the kind of thing people should know",
                        f"I wonder who else has noticed",
                        f"The others need to hear about this",
                    ]
                else:
                    reflections = [
                        f"Been mulling this over",
                        f"Still processing everything",
                        f"Lot on my mind today",
                        f"Trying to make sense of it all",
                    ]

                internal_reflection = random.choice(reflections)

        # LAYER 3: Call enhanced LLM interface with full context
        depth = getattr(game_obj, "thinking_depth", 3)
        result = get_npc_thought(
            self.name,
            bio_context,
            col,
            nearby.name if nearby else None,
            None,
            self.personality,
            self.current_goal,
            self.emotional_state,
            self.relationships,
            self.secrets_known,
            self.occupation,
            self.core_values,
            self.fears,
            self.town_opinions,
            thinking_depth=depth,
        )

        # LAYER 4: Build rich, multi-part thought with dialogue
        base_thought = result["thought"]

        # Add internal reflection if generated
        if internal_reflection:
            base_thought = f"{base_thought} {internal_reflection}."

        # LAYER 5: Add relationship-specific dialogue/thoughts
        if nearby:
            relationship_depth = self.relationships.get(nearby.name, {})
            score = relationship_depth.get("score", 0) if relationship_depth else 0

            # Generate deeper social interaction based on relationship
            if score > 40:  # Close friends
                friendly_thoughts = [
                    f"Always good to see {nearby.name}. We've been through a lot together",
                    f"Grateful to have {nearby.name} as a friend in this town",
                    f"{nearby.name} is one of the few people I truly trust here",
                    f"Need to catch up with {nearby.name} properly soon",
                ]
                base_thought += f" {random.choice(friendly_thoughts)}."

            elif score < -40:  # Bitter enemies
                hostile_thoughts = [
                    f"Of course {nearby.name} is here. Can't seem to avoid them",
                    f"Every time I see {nearby.name}, it reminds me why I can't stand them",
                    f"{nearby.name} better keep their distance today",
                    f"Don't have the energy to deal with {nearby.name} right now",
                ]
                base_thought += f" {random.choice(hostile_thoughts)}."

            elif score > 15:  # Friendly acquaintance
                positive_thoughts = [
                    f"{nearby.name} seems like good people",
                    f"Building a decent rapport with {nearby.name}",
                    f"Glad to see {nearby.name} around",
                    f"Should get to know {nearby.name} better",
                ]
                base_thought += f" {random.choice(positive_thoughts)}."

            elif score < -15:  # Mild distrust
                negative_thoughts = [
                    f"Not sure what to make of {nearby.name} yet",
                    f"Something about {nearby.name} rubs me the wrong way",
                    f"Keeping {nearby.name} at arm's length for now",
                    f"Need to figure out what {nearby.name}'s deal is",
                ]
                base_thought += f" {random.choice(negative_thoughts)}."

        # LAYER 6: Add personality-driven observations
        personality_observations = []

        if "ambitious" in self.personality and random.random() < 0.2:
            personality_observations.append(
                "Every interaction is an opportunity to advance"
            )

        if "cautious" in self.personality and random.random() < 0.2:
            personality_observations.append("Need to be careful about who I trust")

        if "creative" in self.personality and random.random() < 0.15:
            personality_observations.append(
                "Seeing patterns and connections others miss"
            )

        if "loyal" in self.personality and nearby and random.random() < 0.15:
            personality_observations.append("Loyalty matters more than convenience")

        if personality_observations:
            base_thought += f" {random.choice(personality_observations)}."

        # LAYER 7: Reference secrets or fears (rare, adds depth)
        if random.random() < 0.1:  # 10% chance
            if self.fears and random.random() < 0.5:
                fear = random.choice(self.fears)
                fear_thoughts = [
                    f"Can't shake the worry about {fear}",
                    f"What if {fear} becomes reality?",
                    f"Been thinking too much about {fear} lately",
                ]
                base_thought += f" {random.choice(fear_thoughts)}."
            elif self.secrets_known and random.random() < 0.3:
                secret_burden = [
                    "Carrying too many secrets these days",
                    "Some things are better left unsaid",
                    "What I know could change everything",
                ]
                base_thought += f" {random.choice(secret_burden)}."

        # Update NPC state
        self.full_thought = base_thought
        self.thought_history.insert(0, base_thought)
        if len(self.thought_history) > 20:  # Keep more history
            self.thought_history.pop()

        self.emotional_state = result["emotion"]

        if result["new_goal"]:
            self.current_goal = result["new_goal"]

        # Apply opinion changes
        if result.get("opinion_changes"):
            for opinion_cat, change in result["opinion_changes"].items():
                if opinion_cat in self.town_opinions:
                    self.town_opinions[opinion_cat] = max(
                        -100, min(100, self.town_opinions[opinion_cat] + change)
                    )

        # Store thematic memories
        if result.get("memory_themes"):
            for theme in result["memory_themes"]:
                if theme in self.memory_themes:
                    self.memory_themes[theme].insert(0, base_thought)
                    if len(self.memory_themes[theme]) > 15:  # Keep more themed memories
                        self.memory_themes[theme].pop()

        # Track wishes
        if result.get("wish"):
            wish_data = result["wish"]
            current_time = time.time()

            if current_time - self.last_wish_time > 120:
                self.wishes_expressed.append(
                    {
                        "category": wish_data["category"],
                        "wish": wish_data["wish"],
                        "timestamp": current_time,
                    }
                )
                self.last_wish_time = current_time
                game_obj.track_wish(self.name, wish_data)

                if len(self.wishes_expressed) > 8:  # Keep more wish history
                    self.wishes_expressed.pop(0)

        # LAYER 8: Deep relationship updates with history
        if nearby:
            peer_name = nearby.name
            if peer_name not in self.relationships:
                self.relationships[peer_name] = {
                    "sentiment": "Neutral",
                    "score": 0,
                    "reason": "Just met",
                    "history": [],
                    "shared_experiences": [],
                }

            old_rel = self.relationships[peer_name]
            sentiment_scores = {
                "Hostile": -20,
                "Suspicious": -10,
                "Neutral": 0,
                "Friendly": 15,
            }
            score_change = sentiment_scores.get(result["sentiment"], 0)

            # Add nuance based on personality compatibility
            if "gossipy" in self.personality and "gossipy" in nearby.personality:
                score_change += 5  # Gossips bond
            if "suspicious" in self.personality and "paranoid" in nearby.personality:
                score_change += 3  # Paranoid minds think alike
            if "ambitious" in self.personality and "ambitious" in nearby.personality:
                score_change -= 5  # Competition

            new_score = max(-100, min(100, old_rel["score"] + score_change))

            # Create shared experience entry
            shared_exp = {
                "location": result["location"],
                "sentiment": result["sentiment"],
                "context": base_thought[:100],
                "timestamp": time.time(),
            }

            # Update relationship with richer history
            self.relationships[peer_name] = {
                "sentiment": result["sentiment"],
                "score": new_score,
                "reason": result["sentiment_reason"] or old_rel["reason"],
                "history": old_rel["history"]
                + [
                    {
                        "time": time.time(),
                        "sentiment": result["sentiment"],
                        "score": new_score,
                    }
                ],
                "shared_experiences": (
                    old_rel.get("shared_experiences", []) + [shared_exp]
                )[-10:],  # Keep last 10
            }

            # Limit history
            if len(self.relationships[peer_name]["history"]) > 15:
                self.relationships[peer_name]["history"] = self.relationships[
                    peer_name
                ]["history"][-15:]

            # Process social interaction
            self.process_social_interaction(nearby, col)

        # Handle gossip
        if result["gossip"]:
            self.gossip_heard.insert(0, result["gossip"])
            if len(self.gossip_heard) > 15:
                self.gossip_heard.pop()

        # Limit secrets_known to prevent memory leak
        if len(self.secrets_known) > 30:
            self.secrets_known = self.secrets_known[:30]

        # Move to location
        if result["location"] in LOCATIONS:
            self.target_pos = pygame.Vector2(LOCATIONS[result["location"]])

        # Update conversation memory when interacting with someone
        if nearby:
            current_time = time.time()
            if nearby.name not in self.conversation_memory:
                self.conversation_memory[nearby.name] = {
                    "last_topic": None,
                    "last_time": 0,
                    "interaction_count": 0,
                    "memorable_moments": [],
                }

            # Store this interaction
            self.conversation_memory[nearby.name]["last_topic"] = base_thought[:150]
            self.conversation_memory[nearby.name]["last_time"] = current_time
            self.conversation_memory[nearby.name]["interaction_count"] += 1

            # Store memorable moments (strong emotions)
            if self.emotional_state in ["angry", "anxious"] or result["sentiment"] in [
                "Hostile",
                "Suspicious",
            ]:
                moment = {
                    "time": current_time,
                    "thought": base_thought[:200],
                    "emotion": self.emotional_state,
                }
                self.conversation_memory[nearby.name]["memorable_moments"].append(
                    moment
                )
                if len(self.conversation_memory[nearby.name]["memorable_moments"]) > 5:
                    self.conversation_memory[nearby.name]["memorable_moments"].pop(0)

        # LAYER 9: Generate rich social log entry
        emotion_emoji = {"calm": "😐", "happy": "😊", "anxious": "😰", "angry": "😠"}
        emoji = emotion_emoji.get(self.emotional_state, "")

        # Create meaningful log entry
        if nearby:
            # Social interaction - show the relationship dynamic
            relationship_data = self.relationships.get(nearby.name, {})
            score = relationship_data.get("score", 0)

            if score > 30:
                log_entry = f"{emoji} {self.name} & {nearby.name}: Deepening friendship"
            elif score < -30:
                log_entry = f"{emoji} {self.name} vs {nearby.name}: Tension rising"
            elif result["sentiment"] == "Suspicious":
                log_entry = f"{emoji} {self.name} watches {nearby.name} carefully"
            elif result["sentiment"] == "Friendly":
                log_entry = f"{emoji} {self.name} enjoys seeing {nearby.name}"
            else:
                log_entry = f"{emoji} {self.name} encounters {nearby.name}"
        else:
            # Solo - show internal state or action
            if internal_reflection:
                log_entry = f"{emoji} {self.name}: {internal_reflection}"
            elif result.get("opinion_expression"):
                log_entry = f"{emoji} {self.name}: {result['opinion_expression']}"
            else:
                # Extract key phrase from thought
                clean_thought = (
                    base_thought.replace("[GUILTY]", "")
                    .replace("[CLEARED]", "")
                    .strip()
                )
                sentences = clean_thought.split(".")
                if sentences and len(sentences[0]) > 10:
                    log_entry = f"{emoji} {self.name}: {sentences[0][:70]}"
                else:
                    log_entry = f"{emoji} {self.name} → {result['location']}"

        # Wishes get special treatment
        if result.get("wish"):
            wish_text = result["wish"]["wish"]
            log_entry = f"💭 {self.name}: {wish_text[:60]}"

        game_obj.add_social_log(log_entry)

        # Add FULL conversation/thought details for deep interaction window
        # Use the rich components from the result
        components = result.get("thought_components", {})
        clean_thought = (
            base_thought.replace("[GUILTY]", "").replace("[CLEARED]", "").strip()
        )

        game_obj.add_conversation_entry(
            self.name,
            {
                "full_thought": clean_thought,
                "observation": components.get("observation", ""),
                "interpretation": components.get("interpretation", ""),
                "decision": components.get("decision", ""),
                "emotion": self.emotional_state,
                "nearby_npc": nearby.name if nearby else None,
                "sentiment": result["sentiment"] if nearby else None,
                "opinion": result.get("opinion_expression"),
                "internal_reflection": internal_reflection
                if internal_reflection
                else None,
                "goal": self.current_goal,
            },
        )

        # Generate speech bubble data (thread-safe: stored in _pending_bubble, applied by main thread)
        if nearby and base_thought:
            current_time = time.time()
            last_spoke = self.last_spoke_to.get(nearby.name, 0)
            # Only bubble once every 20 seconds per pair
            if current_time - last_spoke > 20:
                self.last_spoke_to[nearby.name] = current_time
                spoken = self._thought_to_speech(base_thought, nearby)
                if spoken:
                    # Store excerpt first (safe — list append is GIL-protected)
                    self.conversation_excerpts.insert(
                        0, {"text": spoken, "with": nearby.name, "time": current_time}
                    )
                    if len(self.conversation_excerpts) > 10:
                        self.conversation_excerpts.pop()
                    # Signal main thread to create the bubble
                    self._pending_bubble = ("convo", spoken, nearby.name)
        elif not nearby and base_thought and random.random() < 0.15:
            spoken = self._thought_to_speech(base_thought, None)
            if spoken:
                self._pending_bubble = ("solo", spoken, None)

    def get_relationship_summary(self):
        """Get a summary of important relationships"""
        important_rels = {
            k: v
            for k, v in self.relationships.items()
            if v["sentiment"] != "Neutral" or abs(v["score"]) > 20
        }
        return important_rels

    def get_dominant_opinion(self):
        """Get the opinion category this NPC cares most strongly about"""
        if not self.town_opinions:
            return None

        # Find most extreme opinion (positive or negative)
        max_opinion = max(self.town_opinions.items(), key=lambda x: abs(x[1]))
        if abs(max_opinion[1]) > 15:  # Only return if it's meaningful
            return max_opinion
        return None

    def read_newspaper(self, newspaper, game_obj):
        """NPC reads the latest Chronicle and reacts based on personality."""
        if not newspaper:
            return
        headline = newspaper["sections"].get("headline", "")
        sections = newspaper["sections"]

        # Extract key info
        crime_status = sections.get("crime", {}).get("status", "")
        gossip_items = sections.get("gossip", {}).get("rumors", [])
        special = sections.get("special", [])

        # Personality-driven reactions
        reactions = []
        opinion_changes = {}

        # React to headline
        if "CRISIS" in headline or "BREAKING" in headline:
            if "paranoid" in self.personality or "suspicious" in self.personality:
                reactions.append(f"Just as I suspected. The Chronicle confirms it.")
                opinion_changes["safety"] = -8
            elif "analytical" in self.personality:
                reactions.append(
                    f"The headline says: {headline[:60]}. I need to think about the implications."
                )
                opinion_changes["leadership"] = -5
            else:
                reactions.append(f"Troubling news in the Chronicle today.")
                opinion_changes["safety"] = -5
        elif "PEACEFUL" in headline or "Peaceful" in headline:
            if "suspicious" in self.personality or "paranoid" in self.personality:
                reactions.append(
                    "'Peaceful day.' They always say that before something goes wrong."
                )
            elif "friendly" in self.personality:
                reactions.append(
                    "Good news in the Chronicle. Things seem to be looking up."
                )
                opinion_changes["community"] = 3

        # React to crime report
        if "🔴 ELEVATED" in crime_status:
            opinion_changes["safety"] = opinion_changes.get("safety", 0) - 10
            if "stern" in self.personality or "loyal" in self.personality:
                reactions.append(
                    "The crime report is alarming. Someone needs to do something."
                )
        elif "🟢 LOW" in crime_status:
            opinion_changes["safety"] = opinion_changes.get("safety", 0) + 5

        # React to gossip (gossipy NPCs love this)
        if gossip_items and "gossipy" in self.personality:
            rumor = gossip_items[0]["rumor"] if gossip_items else ""
            if rumor:
                reactions.append(f"Oh, this is interesting: {rumor[:60]}")
                if rumor not in self.gossip_heard:
                    self.gossip_heard.insert(0, f"Chronicle: {rumor}")

        # React to special/seeded stories
        if special:
            for line in special[:2]:
                if line.strip() and not line.startswith("["):
                    reactions.append(f"The special report says: {line[:70]}")
                    # Seeded stories affect opinions more strongly
                    opinion_changes["leadership"] = (
                        opinion_changes.get("leadership", 0) - 3
                    )

        # Apply opinion changes
        for cat, delta in opinion_changes.items():
            if cat in self.town_opinions:
                self.town_opinions[cat] = max(
                    -100, min(100, self.town_opinions[cat] + delta)
                )

        if reactions:
            reaction = random.choice(reactions)
            self.full_thought = f"[Reading Chronicle] {reaction}"
            self.thought_history.insert(0, self.full_thought)
            if len(self.thought_history) > 20:
                self.thought_history.pop()

            emotion_map = {
                "paranoid": "anxious",
                "suspicious": "anxious",
                "friendly": "happy",
                "gossipy": "happy",
                "stern": "calm",
                "analytical": "calm",
            }
            for trait in self.personality:
                if trait in emotion_map:
                    self.emotional_state = emotion_map[trait]
                    break

            game_obj.add_social_log(f"📰 {self.name}: {reaction[:60]}")
            game_obj.add_conversation_entry(
                self.name,
                {
                    "full_thought": f"[Reading Chronicle] {reaction}",
                    "observation": f"Reading The Playville Chronicle, Edition #{newspaper.get('edition', '?')}",
                    "interpretation": reaction,
                    "decision": "I should keep this in mind.",
                    "emotion": self.emotional_state,
                    "nearby_npc": None,
                    "sentiment": None,
                },
            )

            # Mark that this NPC read this edition
            self.last_newspaper_read = newspaper.get("edition", 0)

    def _thought_to_speech(self, thought, listener):
        """Convert internal thought to a spoken line, referencing memory if available."""
        if not thought:
            return None

        # Strip guilt tags
        clean = thought.replace("[GUILTY]", "").replace("[CLEARED]", "").strip()

        # If talking to someone, try to reference past conversations
        memory_prefix = ""
        if listener:
            mem = self.conversation_memory.get(listener.name, {})
            excerpts = self.conversation_excerpts
            prev_with = [e for e in excerpts if e.get("with") == listener.name]
            if prev_with:
                # Reference a past moment
                refs = [
                    f"Last time we spoke you said something that stuck with me...",
                    f"I've been thinking about what you told me...",
                    f"Remember when we talked near the {prev_with[0].get('text', '')[:30]}...",
                    f"You and I have spoken {mem.get('interaction_count', 1)} times now.",
                ]
                memory_prefix = random.choice(refs) + " "

        # Extract the most conversational sentence from the thought
        sentences = [s.strip() for s in clean.split(".") if len(s.strip()) > 15]
        if not sentences:
            return None

        # Pick the sentence most likely to be spoken aloud
        # Prefer sentences with "I", emotional words, names
        def score_sentence(s):
            score = 0
            if s.startswith("I ") or " I " in s:
                score += 3
            if listener and listener.name in s:
                score += 5
            for w in [
                "feel",
                "think",
                "know",
                "wonder",
                "worry",
                "hope",
                "believe",
                "heard",
            ]:
                if w in s.lower():
                    score += 2
            return score

        sentences.sort(key=score_sentence, reverse=True)
        spoken = sentences[0]

        # If talking to listener, sometimes address them directly
        if listener and memory_prefix:
            spoken = memory_prefix + spoken
        elif listener and listener.name not in spoken:
            # Occasionally address listener by name
            if random.random() < 0.3:
                spoken = f"{listener.name.split()[0]}, {spoken[0].lower()}{spoken[1:]}"

        # Truncate to reasonable length
        if len(spoken) > 180:
            spoken = spoken[:177] + "..."

        return spoken

    def draw(self, surf, font, is_selected):
        self.screen_rect = self.image.get_rect(
            center=(int(self.pos.x), int(self.pos.y))
        )

        # Emotion-colored selection ring
        if is_selected:
            emotion_colors = {
                "calm": (100, 200, 255),
                "happy": (100, 255, 100),
                "anxious": (255, 200, 100),
                "angry": (255, 100, 100),
            }
            ring_color = emotion_colors.get(self.emotional_state, (255, 215, 0))
            pygame.draw.circle(surf, ring_color, self.screen_rect.center, 40, 3)

        surf.blit(self.image, self.screen_rect)

        # Status dot instead of thought bubble
        # Determine status based on recent thoughts
        is_suspicious = False
        if self.thought_history:
            latest_thought = self.thought_history[0]
            is_suspicious = (
                "suspicious" in latest_thought.lower()
                or "guilty" in latest_thought.lower()
            )

        # Status colors
        if is_suspicious:
            dot_color = (255, 50, 50)  # Red - Guilty/Suspicious
        elif self.current_goal and "investigate" in self.current_goal.lower():
            dot_color = (100, 150, 255)  # Blue - Pending/Investigating
        else:
            dot_color = (50, 255, 50)  # Green - Cleared/Normal

        # Draw status dot above NPC
        dot_x = int(self.pos.x)
        dot_y = int(self.pos.y) - 35

        # Outer glow for visibility
        pygame.draw.circle(surf, (255, 255, 255), (dot_x, dot_y), 6)
        # Status dot
        pygame.draw.circle(surf, dot_color, (dot_x, dot_y), 4)

        # Name label below NPC (small and clean)
        name_text = font.render(self.name, True, (255, 255, 255))
        name_rect = name_text.get_rect(center=(int(self.pos.x), int(self.pos.y) + 40))

        # Black background for readability
        bg_rect = name_rect.inflate(4, 2)
        pygame.draw.rect(surf, (0, 0, 0), bg_rect)
        surf.blit(name_text, name_rect)

        # Speech bubble
        if self.speech_bubble:
            self.speech_bubble.draw(surf, font)


class StorySeeder:
    """Simple text input for seeding newspaper stories."""

    def __init__(self):
        self.visible = False
        self.headline = ""
        self.body = ""
        self.active_field = "headline"  # 'headline' or 'body'
        self.cursor_blink = 0

    def toggle(self):
        self.visible = not self.visible
        if self.visible:
            self.headline = ""
            self.body = ""
            self.active_field = "headline"

    def handle_event(self, event):
        """Returns ('submit', headline, body) or None."""
        if not self.visible:
            return None
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.visible = False
            elif event.key == pygame.K_TAB:
                self.active_field = (
                    "body" if self.active_field == "headline" else "headline"
                )
            elif event.key == pygame.K_RETURN:
                # Enter (any modifier) submits when headline is non-empty
                if self.headline.strip():
                    result = ("submit", self.headline.strip(), self.body.strip())
                    self.visible = False
                    self.headline = ""
                    self.body = ""
                    return result
            elif event.key == pygame.K_BACKSPACE:
                if self.active_field == "headline":
                    self.headline = self.headline[:-1]
                else:
                    self.body = self.body[:-1]
            elif event.unicode and event.unicode.isprintable():
                if self.active_field == "headline" and len(self.headline) < 100:
                    self.headline += event.unicode
                elif self.active_field == "body" and len(self.body) < 400:
                    self.body += event.unicode
        return None

    def draw(self, screen, font_s, font_m):
        if not self.visible:
            return
        self.cursor_blink += 1
        panel = pygame.Rect(200, 300, 1300, 380)
        bg = pygame.Surface((panel.width, panel.height))
        bg.set_alpha(250)
        bg.fill((20, 25, 40))
        screen.blit(bg, panel.topleft)
        pygame.draw.rect(screen, (150, 180, 100), panel, 3)

        screen.blit(
            font_m.render("SEED NEWSPAPER STORY", True, (200, 240, 150)),
            (panel.x + 20, panel.y + 15),
        )
        screen.blit(
            font_s.render(
                "TAB to switch fields | ENTER to submit | ESC to cancel",
                True,
                (150, 170, 130),
            ),
            (panel.x + 20, panel.y + 38),
        )

        # Headline field
        hl_active = self.active_field == "headline"
        hl_color = (255, 255, 100) if hl_active else (180, 180, 180)
        screen.blit(
            font_m.render("HEADLINE:", True, hl_color), (panel.x + 20, panel.y + 70)
        )
        hl_box = pygame.Rect(panel.x + 20, panel.y + 92, panel.width - 40, 28)
        pygame.draw.rect(
            screen, (30, 35, 55) if not hl_active else (40, 50, 70), hl_box
        )
        pygame.draw.rect(screen, hl_color, hl_box, 2)
        cursor_char = "|" if (self.cursor_blink // 30) % 2 == 0 else ""
        hl_cursor = cursor_char if hl_active else ""
        hl_txt = font_m.render(self.headline + hl_cursor, True, (240, 240, 220))
        screen.blit(hl_txt, (hl_box.x + 8, hl_box.y + 6))

        # Body field
        bd_active = self.active_field == "body"
        bd_color = (255, 255, 100) if bd_active else (180, 180, 180)
        screen.blit(
            font_m.render("STORY BODY:", True, bd_color), (panel.x + 20, panel.y + 135)
        )
        bd_box = pygame.Rect(panel.x + 20, panel.y + 157, panel.width - 40, 150)
        pygame.draw.rect(
            screen, (30, 35, 55) if not bd_active else (40, 50, 70), bd_box
        )
        pygame.draw.rect(screen, bd_color, bd_box, 2)

        # Word-wrap body text
        bd_cursor = cursor_char if bd_active else ""
        words = (self.body + bd_cursor).split()
        line, y_off = "", 0
        for word in words:
            if len(line) + len(word) + 1 > 100:
                screen.blit(
                    font_s.render(line, True, (220, 220, 200)),
                    (bd_box.x + 8, bd_box.y + 8 + y_off),
                )
                line = word + " "
                y_off += 15
                if y_off > 130:
                    break
            else:
                line += word + " "
        if line and y_off <= 130:
            screen.blit(
                font_s.render(line, True, (220, 220, 200)),
                (bd_box.x + 8, bd_box.y + 8 + y_off),
            )

        # Submit hint
        screen.blit(
            font_m.render("ENTER to publish in next edition", True, (150, 220, 100)),
            (panel.x + 20, panel.y + 330),
        )


class PlayvilleGame:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        self.font_s = pygame.font.SysFont("Arial", 12)
        self.font_m = pygame.font.SysFont("Arial", 16, bold=True)

        # Generate the town map procedurally
        self.world = generate_town_map(GAME_WIDTH, HEIGHT)

        try:
            self.sheet = pygame.image.load("high_res_villagers.png").convert_alpha()
        except:
            self.sheet = pygame.Surface((1024, 1024), pygame.SRCALPHA)

        # Initialize NPC Database
        self.npc_db = NPCDatabase()

        # Check if database needs population
        active_npcs_data = self.npc_db.get_all_active_npcs()
        if len(active_npcs_data) == 0:
            print("First run - populating NPC database...")
            populate_default_npcs(self.npc_db)
            active_npcs_data = self.npc_db.get_all_active_npcs()

        # CONFIGURATION: Full town with all 15 NPCs
        ACTIVE_NPC_NAMES = [
            "Elias Vance",
            "Lena Thorne",
            "Ben Carter",
            "Agnes Peabody",
            "Dr. Aris Thorne",
            "The Whisper",
            "Fletcher Haze",
            "Marco Rossi",
            "Kai",
            "Bea Miller",
            "Silas Blackwood",
            "Leo Jensen",
            "Walt Drummond",
            "Rosa Chen",
            "Padre Serrano",
            "Hector Malone",
        ]

        # Deactivate NPCs not in active list (can be re-enabled anytime in database)
        if active_npcs_data:
            for npc_data in active_npcs_data:
                if npc_data["name"] not in ACTIVE_NPC_NAMES:
                    self.npc_db.deactivate_npc(npc_data["name"])

        # Reload with only active NPCs
        active_npcs_data = self.npc_db.get_all_active_npcs()

        if not active_npcs_data:
            print("[ERROR] No active NPCs found in database!")
            active_npcs_data = []

        print(
            f"Loading {len(active_npcs_data)} NPCs from database (smaller town mode)..."
        )
        npc_names = [n["name"] for n in active_npcs_data if n and "name" in n]
        print(f"Active NPCs: {', '.join(npc_names)}")

        self.col = chromadb.PersistentClient(
            path=CHROMA_PERSIST_PATH
        ).get_or_create_collection("npc_memories")

        # Coordinate scaling - map is generated at 1800px; positions are stored in map coordinates
        COORD_SCALE_X = (
            1.0  # Map is generated at 1800px; positions are stored in map coordinates
        )
        COORD_SCALE_Y = 1.0

        # Create NPC objects from database with scaled coordinates
        self.npcs = []
        for npc_data in active_npcs_data:
            # Scale home position
            original_pos = npc_data["home_position"]
            scaled_pos = [
                int(original_pos[0] * COORD_SCALE_X),
                int(original_pos[1] * COORD_SCALE_Y),
            ]
            npc_data["home_position"] = scaled_pos

            self.npcs.append(NPC(npc_data, self.sheet))

        # Initialize relationships with preset data from database
        for npc in self.npcs:
            for other_npc in self.npcs:
                if npc.name != other_npc.name:
                    preset_rel = self.npc_db.get_relationship(npc.name, other_npc.name)
                    if preset_rel:
                        npc.relationships[other_npc.name] = {
                            "sentiment": preset_rel["sentiment"],
                            "score": preset_rel["score"],
                            "reason": preset_rel.get(
                                "shared_history", "Pre-existing relationship"
                            ),
                            "history": [],
                        }
                    else:
                        # Initialize default relationship
                        npc.relationships[other_npc.name] = {
                            "sentiment": "Neutral",
                            "score": 0,
                            "reason": "Haven't interacted much",
                            "history": [],
                        }

        print(f"Initialized {len(self.npcs)} NPCs with deep backgrounds")

        self.selected_npc = None
        self.social_logs = []
        self.show_journal = False
        self.emergent_stories = []  # Track story threads

        # Conversation/Thought Window (NEW)
        self.show_conversation_window = True  # Always show by default
        self.conversation_history = []  # Full detailed thoughts
        self.max_conversation_entries = 12  # Show more entries (was 8)

        # Town Consensus System (Adjusted for smaller town)
        self.town_wishes = {}  # Track wishes by category
        self.town_whispers = []  # Important notifications about town consensus
        self.wish_threshold = CONSENSUS_THRESHOLD

        # WishTracker integration
        self.wish_tracker = WishTracker()

        # Faction system
        self.faction_manager = FactionManager()
        self.faction_frame_counter = 0

        # Life path system
        self.life_path_manager = LifePathManager()

        # Newspaper system
        self.newspaper_generator = NewspaperGenerator()
        self.current_newspaper = None
        self.show_newspaper = False
        self.newspaper_scroll = 0  # scroll offset for newspaper overlay

        # Social network graph
        game_area_w = GAME_WIDTH
        game_area_h = HEIGHT
        self.social_graph = SocialNetworkGraph(game_area_w, game_area_h)
        self.show_social_graph = False
        self.social_graph_built = False

        # Map version for future expansion
        self.map_version = 1
        self.coordinate_scale = 1.0  # For map expansion

        # Help overlay
        self.help_overlay = HelpOverlay()

        # Story seeder
        self.story_seeder = StorySeeder()

        # Economy
        self.bank = BankSystem()
        self.game_week = 0

        # Court system
        self.court_manager = CourtCaseManager()
        self.show_court = False

        # Town events system (makes the town feel alive)
        self.town_event_manager = TownEventManager()
        self.npc_activity_manager = NPCActivityManager()

        # Time slot (0=morning, 1=afternoon, 2=evening)
        self.current_time_slot = 0

        # Bio tab state for tabbed character panel
        self.bio_tab = 0  # 0=Identity 1=Mind 2=Social 3=Secrets
        self.bio_scroll = 0

        # Thinking depth: 1=shallow/fast, 3=default, 5=deep/slow
        self.thinking_depth = 3
        self._apply_thinking_depth()

        # Selected LLM model (set from startup selector)
        self.selected_model = "llama3.1:8b"  # default, overridden by selector

    def add_social_log(self, text):
        self.social_logs.insert(0, text)
        if len(self.social_logs) > 30:
            self.social_logs.pop()

        # Track emergent stories - if 3+ NPCs mention same topic, it's a story
        self.track_emergent_stories(text)

    def add_conversation_entry(self, npc_name, full_thought_data):
        """Add detailed conversation entry with full context"""
        entry = {
            "timestamp": time.time(),
            "npc": npc_name,
            "full_thought": full_thought_data.get("full_thought", ""),
            "observation": full_thought_data.get("observation", ""),
            "interpretation": full_thought_data.get("interpretation", ""),
            "decision": full_thought_data.get("decision", ""),
            "emotion": full_thought_data.get("emotion", "calm"),
            "nearby_npc": full_thought_data.get("nearby_npc", None),
            "sentiment": full_thought_data.get("sentiment", None),
            "opinion": full_thought_data.get("opinion", None),
            "internal_reflection": full_thought_data.get("internal_reflection", None),
            "goal": full_thought_data.get("goal", None),
        }

        self.conversation_history.insert(0, entry)
        if len(self.conversation_history) > self.max_conversation_entries:
            self.conversation_history.pop()

    def track_wish(self, npc_name, wish_data):
        """Track NPC wishes and detect town consensus"""
        category = wish_data["category"]
        wish_text = wish_data["wish"]

        # Also track via WishTracker
        self.wish_tracker.track_wish(npc_name, category, wish_text)

        # Initialize category if needed
        if category not in self.town_wishes:
            self.town_wishes[category] = {}

        # Track this specific wish
        if wish_text not in self.town_wishes[category]:
            self.town_wishes[category][wish_text] = []

        # Add NPC to wish list if not already there
        if npc_name not in self.town_wishes[category][wish_text]:
            self.town_wishes[category][wish_text].append(npc_name)

            # Check for consensus
            supporter_count = len(self.town_wishes[category][wish_text])
            if supporter_count >= self.wish_threshold:
                # Generate town whisper
                whisper = (
                    f"TOWN WHISPER: {supporter_count} residents want: '{wish_text}'"
                )
                display_whisper = f"🌆 {whisper}"
                if display_whisper not in self.town_whispers:
                    self.town_whispers.insert(0, display_whisper)
                    self.add_social_log(display_whisper)

                    if len(self.town_whispers) > 5:
                        self.town_whispers.pop()

    def get_town_opinion_average(self, opinion_category):
        """Get average town opinion on a topic"""
        opinions = [npc.town_opinions.get(opinion_category, 0) for npc in self.npcs]
        return sum(opinions) / len(opinions) if opinions else 0

    def get_opinion_distribution(self):
        """Get distribution of opinions across all NPCs for each category."""
        distribution = {}
        for category in [
            "town_economy",
            "safety",
            "infrastructure",
            "leadership",
            "community",
        ]:
            opinions = [npc.town_opinions.get(category, 0) for npc in self.npcs]
            if opinions:
                avg = sum(opinions) / len(opinions)
                distribution[category] = {
                    "average": round(avg, 1),
                    "sentiment": "positive"
                    if avg > 10
                    else "negative"
                    if avg < -10
                    else "neutral",
                    "count": len(opinions),
                }
        return distribution

    def track_emergent_stories(self, text):
        """Identify emerging narrative threads"""
        keywords = [
            "courthouse",
            "jail",
            "Whisper",
            "suspicious",
            "GUILTY",
            "investigate",
        ]
        for keyword in keywords:
            if keyword in text.lower():
                # Count mentions
                mentions = sum(1 for log in self.social_logs if keyword in log.lower())
                if mentions >= 3:
                    story = f"Multiple NPCs discussing: {keyword}"
                    if story not in self.emergent_stories:
                        self.emergent_stories.insert(0, story)
                        if len(self.emergent_stories) > 5:
                            self.emergent_stories.pop()

    def generate_reporter_article(self):
        """Fletcher generates an article from recent social logs."""
        fletcher = next((n for n in self.npcs if n.name == "Fletcher Haze"), None)
        if not fletcher:
            return

        # Gather recent events for article material
        recent_logs = self.social_logs[:10]
        if not recent_logs:
            return

        # Build an article from social log snippets
        notable = [
            log
            for log in recent_logs
            if any(
                kw in log
                for kw in [
                    "GUILTY",
                    "LIFE EVENT",
                    "TOWN WHISPER",
                    "suspicious",
                    "tension",
                    "investigate",
                ]
            )
        ]

        if notable:
            lead = (
                notable[0]
                .replace("\U0001f610", "")
                .replace("\U0001f60a", "")
                .replace("\U0001f630", "")
                .replace("\U0001f620", "")
                .strip()
            )
            article = f"Sources indicate unusual activity in Playville. {lead}. "
            if len(notable) > 1:
                secondary = (
                    notable[1]
                    .replace("\U0001f610", "")
                    .replace("\U0001f60a", "")
                    .replace("\U0001f630", "")
                    .replace("\U0001f620", "")
                    .strip()
                )
                article += f"Additionally, {secondary.lower()}. "
            article += "This reporter will continue to follow developments closely."
        else:
            # Quiet day article
            quiets = [
                "Playville remains quiet this season, though tensions simmer beneath the surface.",
                "Town residents go about their routines. Normalcy, or careful concealment?",
                "Nothing to report -- which, in this town, is itself suspicious.",
            ]
            article = random.choice(quiets)

        self.newspaper_generator.add_reporter_article(article, "Fletcher Haze")
        fletcher.full_thought = f"[ARTICLE FILED] {article[:80]}..."
        self.add_social_log(f"Fletcher: Article filed for next edition")

    def distribute_newspaper(self):
        """Some NPCs near the store pick up and read the Chronicle."""
        if not self.current_newspaper:
            return
        edition = self.current_newspaper.get("edition", 0)
        store_pos = pygame.Vector2(LOCATIONS["store"])

        for npc in self.npcs:
            # Skip if already read this edition
            if getattr(npc, "last_newspaper_read", 0) >= edition:
                continue
            # Check proximity to store or gazette
            gazette_pos = pygame.Vector2(LOCATIONS.get("gazette", LOCATIONS["store"]))
            at_store = npc.pos.distance_to(store_pos) < 120
            at_gazette = npc.pos.distance_to(gazette_pos) < 120

            if at_store or at_gazette:
                # Probability depends on personality
                read_chance = 0.15
                if "gossipy" in npc.personality:
                    read_chance = 0.6
                if "analytical" in npc.personality:
                    read_chance += 0.2
                if "paranoid" in npc.personality:
                    read_chance += 0.15
                if npc.occupation == "Newspaper Reporter":
                    read_chance = 1.0

                if random.random() < read_chance:
                    threading.Thread(
                        target=npc.read_newspaper,
                        args=(self.current_newspaper, self),
                        daemon=True,
                    ).start()

    def police_patrol(self):
        """Enhanced police patrol with cross-referencing suspicious patterns"""
        chief = next((n for n in self.npcs if n.name == "Ben Carter"), None)
        if not chief:
            return

        try:
            # Cross-reference: Look for patterns
            res = self.col.get(where={"is_suspicious": True}, limit=5)

            if res["metadatas"]:
                # Find most mentioned suspicious location
                locations = {}
                for meta in res["metadatas"]:
                    loc = meta.get("service_loc", "none")
                    if loc != "none":
                        locations[loc] = locations.get(loc, 0) + 1

                if locations:
                    # Go to most suspicious location
                    target_loc = max(locations, key=lambda k: locations.get(k, 0))
                    if target_loc in LOCATIONS:
                        chief.target_pos = pygame.Vector2(LOCATIONS[target_loc])
                        chief.current_goal = (
                            f"Investigate suspicious activity at {target_loc}"
                        )
        except Exception:
            pass

    def _apply_thinking_depth(self):
        """Adjust NPC autonomous interval and thought richness based on depth setting."""
        global AUTONOMOUS_INTERVAL
        depth_intervals = {1: 360, 2: 720, 3: 1200, 4: 1800, 5: 2700}
        AUTONOMOUS_INTERVAL = depth_intervals.get(self.thinking_depth, 1200)
        # Update existing NPC timers to not fire immediately
        for npc in getattr(self, "npcs", []):
            npc.autonomous_timer = min(npc.autonomous_timer, AUTONOMOUS_INTERVAL)
        print(
            f"[DEPTH] Thinking depth: {self.thinking_depth}/5  interval: {AUTONOMOUS_INTERVAL} frames"
        )

    def get_depth_label(self):
        labels = {
            1: "SHALLOW (fast)",
            2: "LIGHT",
            3: "NORMAL",
            4: "DEEP",
            5: "PROFOUND (slow)",
        }
        return labels.get(self.thinking_depth, "NORMAL")

    def draw_court_scene(self, screen):
        """Render court cutscene overlay."""
        if not self.court_manager.active_case:
            return

        case = self.court_manager.active_case
        sw, sh = screen.get_size()

        # Dark semi-transparent overlay
        overlay = pygame.Surface((sw, sh), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        screen.blit(overlay, (0, 0))

        # Courtroom background panel
        panel_rect = pygame.Rect(sw // 2 - 400, sh // 2 - 280, 800, 560)
        pygame.draw.rect(screen, (40, 35, 25), panel_rect, border_radius=8)
        pygame.draw.rect(screen, (160, 140, 80), panel_rect, 2, border_radius=8)

        # Title bar
        title_rect = pygame.Rect(panel_rect.x, panel_rect.y, panel_rect.width, 40)
        pygame.draw.rect(screen, (80, 60, 30), title_rect, border_radius=8)
        title_surf = self.font_m.render("PLAYVILLE COURT OF LAW", True, (255, 230, 100))
        screen.blit(
            title_surf,
            (panel_rect.centerx - title_surf.get_width() // 2, panel_rect.y + 10),
        )

        # Judge's bench (top center)
        bench_rect = pygame.Rect(panel_rect.centerx - 70, panel_rect.y + 55, 140, 35)
        pygame.draw.rect(screen, (100, 75, 40), bench_rect)
        pygame.draw.rect(screen, (180, 150, 80), bench_rect, 1)
        judge_label = self.font_s.render("JUDGE", True, (220, 200, 100))
        screen.blit(
            judge_label,
            (bench_rect.centerx - judge_label.get_width() // 2, bench_rect.y + 10),
        )

        # Defendant box (left)
        def_rect = pygame.Rect(panel_rect.x + 20, panel_rect.y + 110, 160, 60)
        pygame.draw.rect(screen, (80, 40, 40), def_rect)
        pygame.draw.rect(screen, (200, 80, 80), def_rect, 1)
        def_title = self.font_s.render("DEFENDANT", True, (200, 100, 100))
        def_name = self.font_s.render(case.defendant[:18], True, (240, 200, 200))
        screen.blit(def_title, (def_rect.x + 5, def_rect.y + 5))
        screen.blit(def_name, (def_rect.x + 5, def_rect.y + 22))

        # Witness stand (center)
        wit_rect = pygame.Rect(panel_rect.centerx - 70, panel_rect.y + 110, 140, 60)
        pygame.draw.rect(screen, (30, 60, 80), wit_rect)
        pygame.draw.rect(screen, (80, 160, 200), wit_rect, 1)
        wit_title = self.font_s.render("WITNESS STAND", True, (100, 180, 220))
        screen.blit(wit_title, (wit_rect.x + 5, wit_rect.y + 8))
        if case.witnesses:
            wit_name = self.font_s.render(case.witnesses[0][:16], True, (200, 230, 240))
            screen.blit(wit_name, (wit_rect.x + 5, wit_rect.y + 26))

        # Jury box (right side, grid)
        jury_x = panel_rect.x + 200
        jury_y = panel_rect.y + 110
        jury_label = self.font_s.render("JURY:", True, (180, 180, 120))
        screen.blit(jury_label, (jury_x, jury_y - 16))
        for i, juror_name in enumerate(case.jury[:12]):
            col = i % 4
            row = i // 4
            jx = jury_x + col * 130
            jy = jury_y + row * 22
            color = (120, 160, 120)
            name_surf = self.font_s.render(juror_name[:15], True, color)
            screen.blit(name_surf, (jx, jy))

        # Case info lines
        info_y = panel_rect.y + 210
        display_lines = self.court_manager.get_display_lines({})
        for line in display_lines:
            if line:
                col = (200, 200, 160)
                if line.startswith("VERDICT") or line.startswith("CASE"):
                    col = (255, 230, 80)
                elif "GUILTY" in line:
                    col = (255, 100, 100)
                elif "INNOCENT" in line:
                    col = (100, 255, 150)
                line_surf = self.font_s.render(line[:90], True, col)
                screen.blit(line_surf, (panel_rect.x + 20, info_y))
            info_y += 16

        # Vote tally bar
        total_v = case.votes_guilty + case.votes_innocent
        if total_v > 0:
            bar_y = panel_rect.y + 440
            bar_x = panel_rect.x + 20
            bar_w = panel_rect.width - 40
            pygame.draw.rect(screen, (60, 60, 60), (bar_x, bar_y, bar_w, 16))
            guilty_w = int(bar_w * case.votes_guilty / total_v)
            pygame.draw.rect(screen, (200, 60, 60), (bar_x, bar_y, guilty_w, 16))
            pygame.draw.rect(
                screen, (60, 180, 80), (bar_x + guilty_w, bar_y, bar_w - guilty_w, 16)
            )
            g_label = self.font_s.render(
                f"Guilty: {case.votes_guilty}", True, (255, 150, 150)
            )
            i_label = self.font_s.render(
                f"Innocent: {case.votes_innocent}", True, (150, 255, 180)
            )
            screen.blit(g_label, (bar_x, bar_y + 18))
            screen.blit(i_label, (bar_x + bar_w - i_label.get_width(), bar_y + 18))

        # Phase progress bar
        phase_y = panel_rect.y + 500
        phase_label = self.font_s.render(
            f"Phase: {case.phase.upper()}  (Timer: {case.phase_timer})",
            True,
            (160, 160, 160),
        )
        screen.blit(phase_label, (panel_rect.x + 20, phase_y))

        # Flashing verdict text
        if case.phase == "verdict" and case.verdict:
            flash = (case.phase_timer // 20) % 2 == 0
            if flash:
                v_color = (255, 80, 80) if case.verdict == "guilty" else (80, 255, 120)
                v_text = f"*** {case.verdict.upper()} ***"
                v_surf = self.font_m.render(v_text, True, v_color)
                screen.blit(
                    v_surf,
                    (panel_rect.centerx - v_surf.get_width() // 2, panel_rect.y + 480),
                )

        # Close hint
        hint = self.font_s.render("[ESC or J] to close court", True, (120, 120, 100))
        screen.blit(
            hint, (panel_rect.centerx - hint.get_width() // 2, panel_rect.bottom - 20)
        )

    def draw_sidebar(self):
        sidebar_rect = pygame.Rect(GAME_WIDTH, 0, SIDEBAR_WIDTH, HEIGHT)
        pygame.draw.rect(self.screen, (30, 30, 35), sidebar_rect)
        pygame.draw.line(
            self.screen, (100, 100, 100), (GAME_WIDTH, 0), (GAME_WIDTH, HEIGHT), 2
        )

        y_pos = 8
        # Keybinding hints
        keys_hint = self.font_s.render(
            "C=Thoughts N=Paper G=Graph T=Story B=Bulletin J=Court F1=Help",
            True,
            (140, 140, 160),
        )
        self.screen.blit(keys_hint, (GAME_WIDTH + 10, y_pos))
        y_pos += 16

        # AI model display
        if hasattr(self, "selected_model") and self.selected_model:
            model_txt = self.font_s.render(
                f"AI: {self.selected_model[:30]}", True, (100, 180, 100)
            )
            self.screen.blit(model_txt, (GAME_WIDTH + 10, y_pos))
            y_pos += 14

        # Thinking depth display
        depth_color = {
            1: (180, 180, 100),
            2: (160, 200, 100),
            3: (100, 200, 150),
            4: (100, 180, 220),
            5: (180, 120, 255),
        }
        dc = depth_color.get(self.thinking_depth, (150, 150, 150))
        depth_txt = self.font_s.render(
            f"Depth: {self.thinking_depth}/5 {self.get_depth_label()}  (+/- to change)",
            True,
            dc,
        )
        self.screen.blit(depth_txt, (GAME_WIDTH + 10, y_pos))
        y_pos += 14

        # Newspaper edition indicator
        if self.current_newspaper:
            ed = self.current_newspaper.get("edition", 1)
            np_txt = self.font_s.render(
                f"Chronicle Edition #{ed} available", True, (200, 180, 100)
            )
            self.screen.blit(np_txt, (GAME_WIDTH + 10, y_pos))
            y_pos += 14

        # Status Legend
        legend_header = self.font_m.render("STATUS LEGEND", True, (200, 200, 200))
        self.screen.blit(legend_header, (GAME_WIDTH + 20, y_pos))
        y_pos += 22

        # Draw legend dots
        dot_y = y_pos + 5
        # Green - Cleared
        pygame.draw.circle(self.screen, (255, 255, 255), (GAME_WIDTH + 25, dot_y), 6)
        pygame.draw.circle(self.screen, (50, 255, 50), (GAME_WIDTH + 25, dot_y), 4)
        txt = self.font_s.render("Cleared/Normal", True, (150, 255, 150))
        self.screen.blit(txt, (GAME_WIDTH + 35, dot_y - 6))

        # Red - Suspicious
        dot_y += 16
        pygame.draw.circle(self.screen, (255, 255, 255), (GAME_WIDTH + 25, dot_y), 6)
        pygame.draw.circle(self.screen, (255, 50, 50), (GAME_WIDTH + 25, dot_y), 4)
        txt = self.font_s.render("Suspicious/Guilty", True, (255, 150, 150))
        self.screen.blit(txt, (GAME_WIDTH + 35, dot_y - 6))

        # Blue - Investigating
        dot_y += 16
        pygame.draw.circle(self.screen, (255, 255, 255), (GAME_WIDTH + 25, dot_y), 6)
        pygame.draw.circle(self.screen, (100, 150, 255), (GAME_WIDTH + 25, dot_y), 4)
        txt = self.font_s.render("Investigating", True, (150, 180, 255))
        self.screen.blit(txt, (GAME_WIDTH + 35, dot_y - 6))

        y_pos = dot_y + 20

        # Town Whispers Section
        if self.town_whispers:
            header = self.font_m.render("🌆 TOWN WHISPERS", True, (255, 220, 100))
            self.screen.blit(header, (GAME_WIDTH + 20, y_pos))
            y_pos += 25

            for whisper in self.town_whispers[:2]:
                # Word wrap at 70 chars (wider sidebar)
                if len(whisper) > 70:
                    line1 = whisper[:70]
                    line2 = whisper[70:140]
                    txt1 = self.font_s.render(line1, True, (255, 200, 80))
                    self.screen.blit(txt1, (GAME_WIDTH + 20, y_pos))
                    y_pos += 12
                    if line2:
                        txt2 = self.font_s.render(line2, True, (255, 200, 80))
                        self.screen.blit(txt2, (GAME_WIDTH + 25, y_pos))
                        y_pos += 14
                else:
                    txt = self.font_s.render(whisper, True, (255, 200, 80))
                    self.screen.blit(txt, (GAME_WIDTH + 20, y_pos))
                    y_pos += 18

            y_pos += 5

        # Emerging Stories Section
        header = self.font_m.render("EMERGING STORIES", True, (255, 200, 100))
        self.screen.blit(header, (GAME_WIDTH + 20, y_pos))
        y_pos += 25

        for story in self.emergent_stories[:2]:
            txt = self.font_s.render(story[:68], True, (255, 180, 80))
            self.screen.blit(txt, (GAME_WIDTH + 20, y_pos))
            y_pos += 18

        y_pos += 10

        # Active Town Events Section
        active_events = self.town_event_manager.get_active_events()
        if active_events:
            header = self.font_m.render("🚨 TOWN EVENTS", True, (255, 100, 100))
            self.screen.blit(header, (GAME_WIDTH + 20, y_pos))
            y_pos += 22

            for event in active_events[:2]:
                event_text = event.description[:65]
                txt = self.font_s.render(f"• {event_text}", True, (255, 150, 150))
                self.screen.blit(txt, (GAME_WIDTH + 25, y_pos))
                y_pos += 16

            y_pos += 8

        # Town Opinion Distribution (NEW)
        opinion_dist = self.get_opinion_distribution()
        header = self.font_m.render("TOWN MOOD", True, (180, 180, 255))
        self.screen.blit(header, (GAME_WIDTH + 20, y_pos))
        y_pos += 22

        for category, data in list(opinion_dist.items())[:3]:
            avg = data["average"]
            sentiment = data["sentiment"]

            # Color based on sentiment
            if sentiment == "positive":
                color = (100, 255, 150)
                icon = "👍"
            elif sentiment == "negative":
                color = (255, 150, 100)
                icon = "👎"
            else:
                color = (200, 200, 200)
                icon = "➖"

            cat_label = category.replace("_", " ").title()[:15]
            score_text = f"{icon} {cat_label}: {avg:+.0f}"
            txt = self.font_s.render(score_text, True, color)
            self.screen.blit(txt, (GAME_WIDTH + 20, y_pos))
            y_pos += 16

        y_pos += 10

        # Social Log with wider format
        log_header = self.font_m.render("GLOBAL SOCIAL LOG", True, (200, 200, 200))
        self.screen.blit(log_header, (GAME_WIDTH + 20, y_pos))
        y_pos += 25

        # Render each log entry with word wrapping
        for i, log in enumerate(self.social_logs[:22]):
            if y_pos > HEIGHT - 50:
                break

            color = (200, 100, 100) if "GUILTY" in log else (150, 180, 150)
            # Add emotion color hints
            if "😠" in log:
                color = (255, 100, 100)
            elif "😰" in log:
                color = (255, 200, 100)
            elif "😊" in log:
                color = (100, 255, 150)
            # Town whispers in gold
            if "TOWN WHISPER" in log:
                color = (255, 220, 100)

            # Word wrap for longer messages (75 chars for wider sidebar)
            max_chars = 75
            if len(log) > max_chars:
                # Split into two lines
                first_line = log[:max_chars]
                second_line = log[max_chars : max_chars * 2]

                txt1 = self.font_s.render(first_line, True, color)
                self.screen.blit(txt1, (GAME_WIDTH + 20, y_pos))

                if second_line:
                    txt2 = self.font_s.render(second_line, True, color)
                    self.screen.blit(txt2, (GAME_WIDTH + 25, y_pos + 12))
                    y_pos += 28
                else:
                    y_pos += 20
            else:
                txt = self.font_s.render(log, True, color)
                self.screen.blit(txt, (GAME_WIDTH + 20, y_pos))
                y_pos += 20

    def draw_conversation_window(self):
        """Draw detailed conversation/thought window showing full NPC interactions"""
        # Much larger window to show complete thoughts
        window = pygame.Rect(50, 50, 1100, 900)  # Expanded from 800x550

        # Semi-transparent dark background
        bg_surface = pygame.Surface((window.width, window.height))
        bg_surface.set_alpha(240)
        bg_surface.fill((20, 20, 30))
        self.screen.blit(bg_surface, window.topleft)

        # Border
        pygame.draw.rect(self.screen, (100, 150, 200), window, 3)

        # Header
        header = self.font_m.render(
            "💬 DEEP NPC THOUGHTS & CONVERSATIONS", True, (200, 220, 255)
        )
        self.screen.blit(header, (window.x + 20, window.y + 15))

        # Draw conversation entries
        y_pos = window.y + 50

        for i, entry in enumerate(self.conversation_history[:10]):  # Show last 10
            if y_pos > window.y + window.height - 50:
                break

            # NPC name with emotion
            emotion_emoji = {
                "calm": "😐",
                "happy": "😊",
                "anxious": "😰",
                "angry": "😠",
            }
            emoji = emotion_emoji.get(entry["emotion"], "😐")

            # Interaction type indicator
            if entry["nearby_npc"]:
                if entry.get("sentiment") == "Friendly":
                    interaction_icon = "💚"
                elif entry.get("sentiment") == "Hostile":
                    interaction_icon = "💔"
                elif entry.get("sentiment") == "Suspicious":
                    interaction_icon = "👁️"
                else:
                    interaction_icon = "👥"
                name_header = (
                    f"{emoji} {entry['npc']} {interaction_icon} {entry['nearby_npc']}"
                )
            else:
                name_header = f"{emoji} {entry['npc']} (internal)"

            # Draw name header
            name_text = self.font_m.render(name_header, True, (255, 255, 100))
            self.screen.blit(name_text, (window.x + 20, y_pos))
            y_pos += 22

            # Draw full thought components with proper formatting
            observation = entry.get("observation", "")
            interpretation = entry.get("interpretation", "")
            decision = entry.get("decision", "")

            # Helper function to word-wrap and draw text WITHOUT truncation
            def draw_wrapped_text(text, x, y_start, color, prefix=""):
                if not text:
                    return y_start

                words = (prefix + text).split()
                current_line = ""
                max_chars = 120  # Much longer lines (was 85)
                y = y_start

                for word in words:
                    if len(current_line) + len(word) + 1 <= max_chars:
                        current_line += word + " "
                    else:
                        if current_line:
                            line_text = self.font_s.render(
                                current_line.strip(), True, color
                            )
                            self.screen.blit(line_text, (x, y))
                            y += 13
                        current_line = word + " "

                        # No max line limit - show EVERYTHING

                if current_line:
                    line_text = self.font_s.render(current_line.strip(), True, color)
                    self.screen.blit(line_text, (x, y))
                    y += 13

                return y

            # Draw observation
            if observation:
                y_pos = draw_wrapped_text(
                    observation, window.x + 30, y_pos, (220, 220, 255)
                )

            # Draw interpretation
            if interpretation:
                y_pos = draw_wrapped_text(
                    interpretation, window.x + 30, y_pos, (255, 220, 180), "↳ "
                )

            # Draw decision
            if decision:
                y_pos = draw_wrapped_text(
                    decision, window.x + 30, y_pos, (180, 255, 180), "→ "
                )

            # Draw goal if present
            if entry.get("goal"):
                goal_text = self.font_s.render(
                    f"  🎯 Goal: {entry['goal'][:60]}", True, (150, 255, 200)
                )
                self.screen.blit(goal_text, (window.x + 30, y_pos))
                y_pos += 13

            # Draw internal reflection if present
            if entry.get("internal_reflection"):
                reflection_text = self.font_s.render(
                    f"  ↳ {entry['internal_reflection']}", True, (180, 200, 255)
                )
                self.screen.blit(reflection_text, (window.x + 30, y_pos))
                y_pos += 14

            # Draw opinion if expressed
            if entry.get("opinion"):
                opinion_text = self.font_s.render(
                    f"  💭 {entry['opinion']}", True, (255, 200, 150)
                )
                self.screen.blit(opinion_text, (window.x + 30, y_pos))
                y_pos += 14

            # Spacing between entries
            y_pos += 8

            # Separator line
            if (
                i < len(self.conversation_history) - 1
                and y_pos < window.y + window.height - 50
            ):
                pygame.draw.line(
                    self.screen,
                    (60, 60, 80),
                    (window.x + 20, y_pos),
                    (window.x + window.width - 20, y_pos),
                    1,
                )
                y_pos += 8

        # Footer instructions
        footer = self.font_s.render(
            "Press 'C' to toggle this window", True, (150, 150, 150)
        )
        self.screen.blit(footer, (window.x + 20, window.y + window.height - 25))

    def draw_detail_pane(self):
        if not self.selected_npc:
            return
        n = self.selected_npc

        # Panel: large centered overlay
        panel = pygame.Rect(30, 520, 1740, 490)

        # Semi-transparent background
        bg = pygame.Surface((panel.width, panel.height))
        bg.set_alpha(245)
        # Tab-specific background tint
        tab_bg_colors = [(20, 22, 35), (18, 28, 22), (25, 18, 28), (28, 18, 18)]
        bg.fill(tab_bg_colors[self.bio_tab])
        self.screen.blit(bg, panel.topleft)

        tab_border_colors = [
            (80, 120, 200),
            (60, 160, 80),
            (140, 80, 180),
            (180, 60, 80),
        ]
        pygame.draw.rect(self.screen, tab_border_colors[self.bio_tab], panel, 2)

        # --- TAB BAR ---
        tab_labels = ["1 IDENTITY", "2 MIND & STATE", "3 SOCIAL", "4 SECRETS"]
        tab_colors_active = [
            (120, 160, 255),
            (80, 220, 120),
            (180, 100, 220),
            (220, 80, 100),
        ]
        tab_colors_inactive = [
            (60, 70, 100),
            (40, 80, 50),
            (80, 50, 100),
            (100, 50, 60),
        ]

        tab_w = panel.width // 4
        for i, label in enumerate(tab_labels):
            tab_rect = pygame.Rect(panel.x + i * tab_w, panel.y, tab_w, 26)
            active = i == self.bio_tab
            pygame.draw.rect(
                self.screen, (30, 35, 50) if not active else (20, 25, 40), tab_rect
            )
            pygame.draw.rect(
                self.screen,
                tab_colors_active[i] if active else tab_colors_inactive[i],
                tab_rect,
                1 if not active else 2,
            )
            tc = tab_colors_active[i] if active else (130, 130, 150)
            tab_txt = self.font_s.render(label, True, tc)
            self.screen.blit(
                tab_txt,
                (
                    tab_rect.x + tab_rect.width // 2 - tab_txt.get_width() // 2,
                    tab_rect.y + 6,
                ),
            )

        # --- NPC HEADER (always shown) ---
        emotion_emoji = {"calm": "😐", "happy": "😊", "anxious": "😰", "angry": "😠"}
        emoji = emotion_emoji.get(n.emotional_state, "")
        header = f"{emoji}  {n.name}  ·  {n.age}  ·  {n.occupation}  ·  {n.emotional_state.upper()}"
        self.screen.blit(
            self.font_m.render(header, True, (230, 230, 255)),
            (panel.x + 15, panel.y + 30),
        )

        # Dismiss hint
        close_hint = self.font_s.render(
            "Click map to dismiss  |  < > or 1-4 to switch tabs  |  UP/DOWN scroll",
            True,
            (100, 100, 120),
        )
        self.screen.blit(
            close_hint, (panel.right - close_hint.get_width() - 10, panel.y + 32)
        )

        # Content area
        content_top = panel.y + 56
        content_h = panel.height - 60

        # Helper: word-wrap renderer returning lines
        def wrap_text(text, max_chars):
            if not text:
                return []
            words = text.split()
            lines, cur = [], ""
            for w in words:
                if len(cur) + len(w) + 1 <= max_chars:
                    cur += w + " "
                else:
                    if cur:
                        lines.append(cur.rstrip())
                    cur = w + " "
            if cur:
                lines.append(cur.rstrip())
            return lines

        # Create scrollable content surface
        content_surf = pygame.Surface((panel.width - 10, 2000))
        content_surf.fill((1, 2, 3))
        content_surf.set_colorkey((1, 2, 3))

        # ==============================
        # TAB 0: IDENTITY
        # ==============================
        if self.bio_tab == 0:
            col1_x, col2_x = 10, (panel.width - 10) // 2
            col_w = (panel.width - 30) // 2

            y1 = 5
            content_surf.blit(
                self.font_m.render("SHORT BIO", True, (180, 200, 255)), (col1_x, y1)
            )
            y1 += 20
            for line in wrap_text(n.bio, col_w // 7):
                content_surf.blit(
                    self.font_s.render(line, True, (200, 210, 230)), (col1_x + 4, y1)
                )
                y1 += 15
            y1 += 8
            content_surf.blit(
                self.font_m.render("BACKGROUND", True, (180, 200, 255)), (col1_x, y1)
            )
            y1 += 20
            bg_text = (
                n.full_background.replace("\n", " ").replace("  ", " ").strip()
                if n.full_background
                else ""
            )
            for line in wrap_text(bg_text, col_w // 7):
                content_surf.blit(
                    self.font_s.render(line, True, (180, 190, 210)), (col1_x + 4, y1)
                )
                y1 += 14
            y1 += 8
            content_surf.blit(
                self.font_m.render("PERSONAL HISTORY", True, (180, 200, 255)),
                (col1_x, y1),
            )
            y1 += 20
            hist = (
                n.personal_history.replace("\n", " ").replace("  ", " ").strip()
                if n.personal_history
                else "Unknown."
            )
            for line in wrap_text(hist, col_w // 7):
                content_surf.blit(
                    self.font_s.render(line, True, (160, 175, 200)), (col1_x + 4, y1)
                )
                y1 += 14

            y2 = 5
            content_surf.blit(
                self.font_m.render("PERSONALITY TRAITS", True, (180, 255, 180)),
                (col2_x, y2),
            )
            y2 += 20
            for trait in n.personality:
                content_surf.blit(
                    self.font_s.render(f"• {trait}", True, (150, 230, 150)),
                    (col2_x + 4, y2),
                )
                y2 += 15
            y2 += 6
            content_surf.blit(
                self.font_m.render("CORE VALUES", True, (180, 255, 180)), (col2_x, y2)
            )
            y2 += 20
            for val in n.core_values:
                content_surf.blit(
                    self.font_s.render(f"• {val}", True, (140, 220, 160)),
                    (col2_x + 4, y2),
                )
                y2 += 14
            y2 += 6
            content_surf.blit(
                self.font_m.render("FEARS", True, (255, 160, 160)), (col2_x, y2)
            )
            y2 += 20
            for fear in n.fears:
                for line in wrap_text(f"• {fear}", 42):
                    content_surf.blit(
                        self.font_s.render(line, True, (220, 140, 140)),
                        (col2_x + 4, y2),
                    )
                    y2 += 14
            y2 += 6
            content_surf.blit(
                self.font_m.render("DESIRES", True, (255, 220, 120)), (col2_x, y2)
            )
            y2 += 20
            for desire in n.desires:
                for line in wrap_text(f"• {desire}", 42):
                    content_surf.blit(
                        self.font_s.render(line, True, (220, 200, 120)),
                        (col2_x + 4, y2),
                    )
                    y2 += 14

        # ==============================
        # TAB 1: MIND & STATE
        # ==============================
        elif self.bio_tab == 1:
            col1_x, col2_x = 10, (panel.width - 10) // 2
            col_w = (panel.width - 30) // 2

            y1 = 5
            content_surf.blit(
                self.font_m.render("RECENT THOUGHTS", True, (200, 220, 255)),
                (col1_x, y1),
            )
            y1 += 20
            for i, thought in enumerate(n.thought_history[:6]):
                t_clean = (
                    thought.replace("[GUILTY]", "").replace("[CLEARED]", "").strip()
                )
                t_color = (220, 100, 100) if "[GUILTY]" in thought else (140, 220, 140)
                content_surf.blit(
                    self.font_s.render(f"[{i + 1}]", True, (100, 100, 140)),
                    (col1_x, y1),
                )
                for line in wrap_text(t_clean, col_w // 7):
                    content_surf.blit(
                        self.font_s.render(line, True, t_color), (col1_x + 22, y1)
                    )
                    y1 += 14
                y1 += 4

            y1 += 6
            content_surf.blit(
                self.font_m.render("CURRENT GOAL", True, (200, 220, 255)), (col1_x, y1)
            )
            y1 += 20
            goal_text = n.current_goal or "No active goal"
            for line in wrap_text(goal_text, col_w // 7):
                content_surf.blit(
                    self.font_s.render(line, True, (160, 200, 255)), (col1_x + 4, y1)
                )
                y1 += 14

            y1 += 8
            content_surf.blit(
                self.font_m.render("LATEST WISH", True, (200, 180, 255)), (col1_x, y1)
            )
            y1 += 20
            if n.wishes_expressed:
                for w in n.wishes_expressed[-3:]:
                    for line in wrap_text(
                        f"• [{w['category']}] {w['wish']}", col_w // 7
                    ):
                        content_surf.blit(
                            self.font_s.render(line, True, (180, 160, 220)),
                            (col1_x + 4, y1),
                        )
                        y1 += 14
            else:
                content_surf.blit(
                    self.font_s.render(
                        "No wishes recorded yet.", True, (120, 120, 140)
                    ),
                    (col1_x + 4, y1),
                )

            y2 = 5
            content_surf.blit(
                self.font_m.render("TOWN OPINIONS", True, (255, 220, 120)), (col2_x, y2)
            )
            y2 += 20
            for cat, score in n.town_opinions.items():
                bar_w = min(80, max(-80, score))
                label = cat.replace("_", " ").title()
                color = (
                    (100, 220, 100)
                    if score > 0
                    else (220, 100, 100)
                    if score < 0
                    else (160, 160, 160)
                )
                score_txt = f"{label[:18]:<18} {score:+4d}"
                content_surf.blit(
                    self.font_s.render(score_txt, True, color), (col2_x + 4, y2)
                )
                bar_x = col2_x + 200
                pygame.draw.rect(
                    content_surf, (40, 40, 50), pygame.Rect(bar_x, y2 + 2, 80, 10)
                )
                if bar_w > 0:
                    pygame.draw.rect(
                        content_surf,
                        (80, 180, 80),
                        pygame.Rect(bar_x + 40, y2 + 2, bar_w // 2, 10),
                    )
                elif bar_w < 0:
                    pygame.draw.rect(
                        content_surf,
                        (180, 80, 80),
                        pygame.Rect(bar_x + 40 + bar_w // 2, y2 + 2, -bar_w // 2, 10),
                    )
                pygame.draw.line(
                    content_surf,
                    (100, 100, 120),
                    (bar_x + 40, y2 + 1),
                    (bar_x + 40, y2 + 12),
                    1,
                )
                y2 += 16

            y2 += 8
            content_surf.blit(
                self.font_m.render("MEMORY THEMES", True, (180, 180, 255)), (col2_x, y2)
            )
            y2 += 20
            for theme, memories in n.memory_themes.items():
                if memories:
                    count = len(memories)
                    bar_fill = min(100, count * 15)
                    theme_label = theme.replace("_", " ").title()
                    content_surf.blit(
                        self.font_s.render(
                            f"{theme_label}: {count} memories", True, (150, 160, 220)
                        ),
                        (col2_x + 4, y2),
                    )
                    pygame.draw.rect(
                        content_surf,
                        (40, 40, 60),
                        pygame.Rect(col2_x + 4, y2 + 13, 200, 6),
                    )
                    pygame.draw.rect(
                        content_surf,
                        (100, 110, 200),
                        pygame.Rect(col2_x + 4, y2 + 13, bar_fill * 2, 6),
                    )
                    y2 += 22

            y2 += 6
            content_surf.blit(
                self.font_m.render("EMOTIONAL STATE", True, (255, 200, 100)),
                (col2_x, y2),
            )
            y2 += 20
            em_colors = {
                "calm": (120, 200, 220),
                "happy": (120, 220, 120),
                "anxious": (220, 180, 80),
                "angry": (220, 100, 100),
            }
            em_c = em_colors.get(n.emotional_state, (200, 200, 200))
            content_surf.blit(
                self.font_m.render(n.emotional_state.upper(), True, em_c),
                (col2_x + 4, y2),
            )
            y2 += 10
            content_surf.blit(
                self.font_m.render("FINANCES", True, (220, 200, 80)), (col2_x, y2)
            )
            y2 += 20
            bank_bal = self.bank.get_balance(n.name) if hasattr(self, "bank") else 0
            content_surf.blit(
                self.font_s.render(f"Cash: ${n.gold}", True, (200, 200, 80)),
                (col2_x + 4, y2),
            )
            y2 += 14
            content_surf.blit(
                self.font_s.render(f"Bank: ${bank_bal}", True, (180, 200, 80)),
                (col2_x + 4, y2),
            )
            y2 += 14

        # ==============================
        # TAB 2: SOCIAL
        # ==============================
        elif self.bio_tab == 2:
            col1_x, col2_x = 10, (panel.width - 10) // 2
            col_w = (panel.width - 30) // 2

            y1 = 5
            content_surf.blit(
                self.font_m.render("RELATIONSHIPS", True, (180, 220, 255)), (col1_x, y1)
            )
            y1 += 20

            all_rels = sorted(
                n.relationships.items(),
                key=lambda x: abs(x[1].get("score", 0)),
                reverse=True,
            )
            for rname, rel in all_rels[:12]:
                score = rel.get("score", 0)
                sentiment = rel.get("sentiment", "Neutral")
                reason = rel.get("reason", "")[:50]
                shared = len(rel.get("shared_experiences", []))
                s_color = (
                    (220, 100, 100)
                    if score < -20
                    else (100, 220, 100)
                    if score > 20
                    else (160, 160, 180)
                )
                content_surf.blit(
                    self.font_s.render(f"{rname}", True, s_color), (col1_x + 4, y1)
                )
                score_str = f"{sentiment} ({score:+d})  {shared} shared moments"
                content_surf.blit(
                    self.font_s.render(score_str, True, (140, 150, 170)),
                    (col1_x + 130, y1),
                )
                y1 += 14
                if reason:
                    for line in wrap_text(f"  > {reason}", 75):
                        content_surf.blit(
                            self.font_s.render(line, True, (110, 115, 140)),
                            (col1_x + 8, y1),
                        )
                        y1 += 12
                y1 += 2

            y2 = 5
            content_surf.blit(
                self.font_m.render("TRUST NETWORK", True, (200, 180, 255)), (col2_x, y2)
            )
            y2 += 20
            if n.trust_network:
                for tname, tstatus in n.trust_network.items():
                    tc = (100, 220, 130) if tstatus == "trusted" else (220, 100, 100)
                    icon = "+" if tstatus == "trusted" else "-"
                    content_surf.blit(
                        self.font_s.render(f"{icon}  {tname}: {tstatus}", True, tc),
                        (col2_x + 4, y2),
                    )
                    y2 += 16
            else:
                content_surf.blit(
                    self.font_s.render("No trust records yet.", True, (120, 120, 140)),
                    (col2_x + 4, y2),
                )
                y2 += 16

            y2 += 10
            content_surf.blit(
                self.font_m.render("GOSSIP HEARD", True, (220, 200, 100)), (col2_x, y2)
            )
            y2 += 20
            for gossip in n.gossip_heard[:8]:
                for line in wrap_text(f"• {gossip}", 55):
                    content_surf.blit(
                        self.font_s.render(line, True, (200, 180, 100)),
                        (col2_x + 4, y2),
                    )
                    y2 += 13
            if not n.gossip_heard:
                content_surf.blit(
                    self.font_s.render("Nothing overheard yet.", True, (120, 120, 100)),
                    (col2_x + 4, y2),
                )

            y2 += 10
            content_surf.blit(
                self.font_m.render("CONVERSATION HISTORY", True, (180, 200, 220)),
                (col2_x, y2),
            )
            y2 += 20
            for cname, cmem in list(n.conversation_memory.items())[:5]:
                count = cmem.get("interaction_count", 0)
                last_topic = cmem.get("last_topic", "")[:60]
                content_surf.blit(
                    self.font_s.render(
                        f"{cname}: {count} interactions", True, (160, 180, 200)
                    ),
                    (col2_x + 4, y2),
                )
                y2 += 13
                if last_topic:
                    content_surf.blit(
                        self.font_s.render(f"  > {last_topic}", True, (120, 140, 160)),
                        (col2_x + 4, y2),
                    )
                    y2 += 12

        # ==============================
        # TAB 3: SECRETS
        # ==============================
        elif self.bio_tab == 3:
            col1_x, col2_x = 10, (panel.width - 10) // 2
            col_w = (panel.width - 30) // 2

            y1 = 5
            content_surf.blit(
                self.font_m.render("KNOWN SECRETS", True, (220, 100, 180)), (col1_x, y1)
            )
            y1 += 20
            for i, secret in enumerate(n.secrets):
                content_surf.blit(
                    self.font_s.render(f"[{i + 1}]", True, (160, 60, 120)), (col1_x, y1)
                )
                for line in wrap_text(secret, col_w // 7):
                    content_surf.blit(
                        self.font_s.render(line, True, (200, 120, 160)),
                        (col1_x + 24, y1),
                    )
                    y1 += 14
                y1 += 4

            y1 += 8
            content_surf.blit(
                self.font_m.render("GUILTY CONSCIENCE", True, (200, 80, 80)),
                (col1_x, y1),
            )
            y1 += 20
            guilty = getattr(n, "guilty_conscience", "")
            if guilty:
                for line in wrap_text(guilty, col_w // 7):
                    content_surf.blit(
                        self.font_s.render(line, True, (200, 100, 100)),
                        (col1_x + 4, y1),
                    )
                    y1 += 14
            else:
                content_surf.blit(
                    self.font_s.render("No recorded guilt.", True, (120, 100, 100)),
                    (col1_x + 4, y1),
                )

            y2 = 5
            content_surf.blit(
                self.font_m.render("SECRETS THEY KNOW", True, (180, 100, 220)),
                (col2_x, y2),
            )
            y2 += 20
            for i, sk in enumerate(n.secrets_known[:10]):
                for line in wrap_text(f"• {sk}", 55):
                    content_surf.blit(
                        self.font_s.render(line, True, (160, 120, 200)),
                        (col2_x + 4, y2),
                    )
                    y2 += 13

            y2 += 10
            content_surf.blit(
                self.font_m.render("DAILY ROUTINE", True, (180, 200, 180)), (col2_x, y2)
            )
            y2 += 20
            daily_routine = getattr(n, "daily_routine", {})
            if daily_routine:
                for period, loc in daily_routine.items():
                    content_surf.blit(
                        self.font_s.render(
                            f"  {period.title()}: {loc}", True, (160, 190, 160)
                        ),
                        (col2_x + 4, y2),
                    )
                    y2 += 15

            y2 += 8
            content_surf.blit(
                self.font_m.render("HABITS & SPEECH", True, (180, 200, 180)),
                (col2_x, y2),
            )
            y2 += 20
            habits = getattr(n, "habits", [])
            if habits:
                for habit in habits:
                    content_surf.blit(
                        self.font_s.render(f"• {habit}", True, (150, 180, 150)),
                        (col2_x + 4, y2),
                    )
                    y2 += 14
            speech = getattr(n, "speech_patterns", "")
            if speech:
                y2 += 4
                for line in wrap_text(f"Speech: {speech}", 55):
                    content_surf.blit(
                        self.font_s.render(line, True, (140, 170, 140)),
                        (col2_x + 4, y2),
                    )
                    y2 += 14

        # Blit content surface with scroll clipping
        scroll_y = min(self.bio_scroll, max(0, 1800 - content_h))
        self.screen.blit(
            content_surf,
            (panel.x + 5, content_top),
            pygame.Rect(0, scroll_y, panel.width - 10, content_h),
        )

        # Scroll indicators
        if scroll_y > 0:
            up_arrow = self.font_s.render("^ scroll up", True, (150, 150, 180))
            self.screen.blit(up_arrow, (panel.right - 90, content_top + 2))
        scroll_hint = self.font_s.render("v scroll", True, (100, 100, 130))
        self.screen.blit(scroll_hint, (panel.right - 75, panel.bottom - 18))

    def draw_newspaper_overlay(self):
        """Render the latest newspaper as a scrollable text overlay."""
        if not self.current_newspaper:
            return
        overlay_rect = pygame.Rect(100, 50, GAME_WIDTH - 200, HEIGHT - 100)
        bg = pygame.Surface((overlay_rect.width, overlay_rect.height))
        bg.set_alpha(245)
        bg.fill((245, 240, 220))
        self.screen.blit(bg, overlay_rect.topleft)
        pygame.draw.rect(self.screen, (80, 40, 0), overlay_rect, 3)

        lines = format_newspaper_for_display(self.current_newspaper)
        title_text = self.font_m.render(
            "THE PLAYVILLE CHRONICLE - Press N to close", True, (80, 40, 0)
        )
        self.screen.blit(title_text, (overlay_rect.x + 20, overlay_rect.y + 8))

        y = overlay_rect.y + 35 - self.newspaper_scroll
        for line in lines:
            if y > overlay_rect.y + overlay_rect.height - 10:
                break
            if y >= overlay_rect.y + 30:
                color = (
                    (80, 40, 0)
                    if line.startswith("=") or line.startswith(">")
                    else (30, 30, 30)
                )
                txt = self.font_s.render(line[:110], True, color)
                self.screen.blit(txt, (overlay_rect.x + 15, y))
            y += 16

        footer = self.font_s.render("Scroll: UP/DOWN arrows", True, (120, 80, 40))
        self.screen.blit(
            footer, (overlay_rect.x + 20, overlay_rect.y + overlay_rect.height - 18)
        )

    def draw_social_graph_overlay(self):
        """Render the social network graph as a full game-area overlay."""
        overlay = pygame.Surface((GAME_WIDTH, HEIGHT))
        overlay.set_alpha(230)
        overlay.fill((15, 15, 25))
        self.screen.blit(overlay, (0, 0))

        self.social_graph.update_physics(2)
        self.social_graph.draw(self.screen, self.font_s)

        stats = self.social_graph.get_network_stats()
        stats_str = (
            f"Network: {stats['total_relationships']} links | "
            f"Friendships: {stats['friendships']} | "
            f"Rivalries: {stats['rivalries']} | "
            f"Density: {stats['network_density']}%"
        )
        txt = self.font_s.render(stats_str, True, (220, 220, 220))
        self.screen.blit(txt, (10, HEIGHT - 20))
        hint = self.font_s.render(
            "Press G to close | Click nodes to inspect", True, (180, 180, 180)
        )
        self.screen.blit(hint, (10, HEIGHT - 36))

    def run(self):
        clock = pygame.time.Clock()
        frame_count = 0
        while True:
            for e in pygame.event.get():
                if e.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()

                # Story seeder gets priority when open
                if self.story_seeder.visible:
                    seeder_result = self.story_seeder.handle_event(e)
                    if seeder_result and seeder_result[0] == "submit":
                        self.newspaper_generator.seed_story(
                            seeder_result[1], seeder_result[2], author="Editor"
                        )
                        # Generate new newspaper immediately with the seeded story
                        self.generate_reporter_article()
                        opinion_dist = self.get_opinion_distribution()
                        whisper_strings = [
                            w["wish"] for w in self.wish_tracker.get_whispers()
                        ]
                        self.current_newspaper = (
                            self.newspaper_generator.generate_newspaper(
                                npcs=self.npcs,
                                events=[],
                                factions=self.faction_manager,
                                town_whispers=whisper_strings,
                                opinion_dist=opinion_dist,
                                evolution_log=[],
                            )
                        )
                        self.distribute_newspaper()  # immediately spread
                        self.add_social_log(f"📰 BULLETIN: {seeder_result[1][:50]}")
                        self.show_newspaper = True  # auto-open newspaper
                    continue  # don't process any other handlers while seeder is open

                if e.type == pygame.KEYDOWN:
                    if e.key == pygame.K_c:
                        self.show_conversation_window = (
                            not self.show_conversation_window
                        )
                    elif e.key == pygame.K_n:
                        # Toggle newspaper overlay; generate one now if needed
                        if not self.show_newspaper:
                            if not self.current_newspaper:
                                opinion_dist = self.get_opinion_distribution()
                                faction_data = self.faction_manager
                                whisper_strings = [
                                    w["wish"] for w in self.wish_tracker.get_whispers()
                                ]
                                self.current_newspaper = (
                                    self.newspaper_generator.generate_newspaper(
                                        npcs=self.npcs,
                                        events=[],
                                        factions=faction_data,
                                        town_whispers=whisper_strings,
                                        opinion_dist=opinion_dist,
                                        evolution_log=[],
                                    )
                                )
                            self.newspaper_scroll = 0
                        self.show_newspaper = not self.show_newspaper
                        self.show_social_graph = False  # close graph if open
                    elif e.key == pygame.K_g:
                        self.show_social_graph = not self.show_social_graph
                        self.show_newspaper = False  # close newspaper if open
                        if self.show_social_graph:
                            self.social_graph.build_graph(
                                self.npcs, self.faction_manager
                            )
                    elif e.key == pygame.K_UP and self.show_newspaper:
                        self.newspaper_scroll = max(0, self.newspaper_scroll - 30)
                    elif e.key == pygame.K_DOWN and self.show_newspaper:
                        self.newspaper_scroll += 30
                    elif e.key == pygame.K_t:
                        self.story_seeder.toggle()
                        self.show_newspaper = False
                        self.show_social_graph = False
                    elif e.key == pygame.K_b:
                        # Force-publish an urgent bulletin (always works)
                        opinion_dist = self.get_opinion_distribution()
                        whisper_strings = [
                            w["wish"] for w in self.wish_tracker.get_whispers()
                        ]
                        self.current_newspaper = (
                            self.newspaper_generator.generate_newspaper(
                                npcs=self.npcs,
                                events=[],
                                factions=self.faction_manager,
                                town_whispers=whisper_strings,
                                opinion_dist=opinion_dist,
                                evolution_log=[],
                            )
                        )
                        self.distribute_newspaper()
                        self.show_newspaper = True
                        self.add_social_log("📰 BULLETIN: Urgent edition published!")
                    elif e.key == pygame.K_F1:
                        self.help_overlay.toggle()
                    elif e.key == pygame.K_ESCAPE:
                        if self.help_overlay.visible:
                            self.help_overlay.visible = False
                        elif self.show_court:
                            self.show_court = False
                        elif self.show_newspaper:
                            self.show_newspaper = False
                        elif self.show_social_graph:
                            self.show_social_graph = False
                    elif e.key == pygame.K_j:
                        if self.court_manager.active_case:
                            # Toggle court overlay
                            self.show_court = not self.show_court
                        else:
                            # Pick defendant: selected NPC, or most suspicious NPC
                            defendant = self.selected_npc
                            if not defendant:
                                suspects = [
                                    n for n in self.npcs if getattr(n, "secrets", [])
                                ]
                                defendant = (
                                    random.choice(suspects)
                                    if suspects
                                    else (
                                        random.choice(self.npcs) if self.npcs else None
                                    )
                                )
                            if defendant:
                                charges = [
                                    "Suspicious Activity",
                                    "Disturbing the Peace",
                                    "Property Damage",
                                    "Public Misconduct",
                                    "Conspiracy",
                                ]
                                charge = random.choice(charges)
                                self.court_manager.file_case(
                                    defendant.name, charge, self.npcs
                                )
                                self.show_court = True
                                for npc in self.npcs:
                                    npc.target_pos = pygame.Vector2(
                                        LOCATIONS["courthouse"]
                                    )
                                self.add_social_log(
                                    f"⚖️ COURT: {defendant.name} charged with {charge}"
                                )
                    elif (
                        e.key == pygame.K_EQUALS or e.key == pygame.K_PLUS
                    ):  # + key = deeper
                        self.thinking_depth = min(5, self.thinking_depth + 1)
                        self._apply_thinking_depth()
                        self.add_social_log(
                            f"🧠 Thinking depth: {self.thinking_depth}/5 ({self.get_depth_label()})"
                        )
                    elif e.key == pygame.K_MINUS:  # - key = shallower
                        self.thinking_depth = max(1, self.thinking_depth - 1)
                        self._apply_thinking_depth()
                        self.add_social_log(
                            f"🧠 Thinking depth: {self.thinking_depth}/5 ({self.get_depth_label()})"
                        )
                    elif (
                        not self.show_newspaper
                        and not self.show_social_graph
                        and self.selected_npc
                    ):
                        if e.key == pygame.K_RIGHT:
                            self.bio_tab = (self.bio_tab + 1) % 4
                            self.bio_scroll = 0
                        elif e.key == pygame.K_LEFT:
                            self.bio_tab = (self.bio_tab - 1) % 4
                            self.bio_scroll = 0
                        elif e.key in (pygame.K_1, pygame.K_KP1):
                            self.bio_tab = 0
                            self.bio_scroll = 0
                        elif e.key in (pygame.K_2, pygame.K_KP2):
                            self.bio_tab = 1
                            self.bio_scroll = 0
                        elif e.key in (pygame.K_3, pygame.K_KP3):
                            self.bio_tab = 2
                            self.bio_scroll = 0
                        elif e.key in (pygame.K_4, pygame.K_KP4):
                            self.bio_tab = 3
                            self.bio_scroll = 0
                        elif e.key == pygame.K_UP:
                            self.bio_scroll = max(0, self.bio_scroll - 20)
                        elif e.key == pygame.K_DOWN:
                            self.bio_scroll += 20
                    # Help overlay scroll only (F1 toggle handled above in elif chain)
                    if self.help_overlay.visible and e.key in (
                        pygame.K_UP,
                        pygame.K_DOWN,
                    ):
                        self.help_overlay.handle_event(e)
                if e.type == pygame.MOUSEBUTTONDOWN:
                    if self.show_social_graph:
                        self.social_graph.handle_click(e.pos)
                    else:
                        # Check for NPC Clicks
                        clicked_npc = False
                        for n in self.npcs:
                            if n.screen_rect.collidepoint(e.pos):
                                self.selected_npc = n
                                clicked_npc = True
                                break
                        if not clicked_npc and not pygame.Rect(
                            30, 520, 1740, 490
                        ).collidepoint(e.pos):
                            if COURTHOUSE_RECT.collidepoint(e.pos):
                                res = self.col.get(limit=10)
                                self.journal_logs = (
                                    res["documents"]
                                    if res["documents"]
                                    else ["Peaceful."]
                                )
                                self.show_journal = not self.show_journal
                            else:
                                self.selected_npc = None
                                self.show_journal = False
                if e.type == pygame.MOUSEMOTION and self.show_social_graph:
                    self.social_graph.handle_hover(e.pos)

            # --- Periodic systems ---
            frame_count += 1

            # Newspaper distribution every 600 frames (~10 seconds at 60 FPS)
            if frame_count % 600 == 0:
                self.distribute_newspaper()

            # Faction update every 300 frames (~5 seconds at 60 FPS)
            self.faction_frame_counter += 1
            if self.faction_frame_counter >= 300:
                self.faction_frame_counter = 0
                try:
                    self.faction_manager.update_factions(self.npcs)
                    if self.show_social_graph:
                        self.social_graph.build_graph(self.npcs, self.faction_manager)
                except Exception:
                    pass

            # Life path check (governed by LifePathManager's own timer)
            try:
                life_events = self.life_path_manager.check_and_trigger_events(
                    self.npcs, self.faction_manager
                )
                for event_data in life_events:
                    desc = event_data["event"].description
                    self.add_social_log(
                        f"LIFE EVENT: {event_data['npc']} - {desc[:60]}"
                    )
            except Exception:
                pass

            # Court case update
            if self.court_manager.active_case:
                phase_result = self.court_manager.update(COURT_PHASE_DURATION)
                if phase_result and phase_result[0] == "vote_time":
                    for npc in self.npcs:
                        if npc.name != self.court_manager.active_case.defendant:
                            self.court_manager.cast_vote(
                                npc, self.court_manager.active_case.evidence
                            )
                if phase_result and phase_result[0] == "case_over":
                    if self.court_manager.case_history:
                        finished = self.court_manager.case_history[-1]
                        self.add_social_log(
                            f"⚖️ VERDICT: {finished.defendant} — {finished.verdict.upper()}"
                        )
                    self.show_court = False

            # Town events - random incidents and activities
            self.town_event_manager.update(self.npcs, self)
            self.npc_activity_manager.update(self.npcs, LOCATIONS, frame_count)

            # Newspaper generation on interval
            if self.newspaper_generator.should_publish():
                try:
                    self.generate_reporter_article()
                    opinion_dist = self.get_opinion_distribution()
                    whisper_strings = [
                        w["wish"] for w in self.wish_tracker.get_whispers()
                    ]
                    self.current_newspaper = (
                        self.newspaper_generator.generate_newspaper(
                            npcs=self.npcs,
                            events=[],
                            factions=self.faction_manager,
                            town_whispers=whisper_strings,
                            opinion_dist=opinion_dist,
                            evolution_log=[],
                        )
                    )
                    edition = self.current_newspaper.get("edition", "?")
                    self.add_social_log(f"NEWSPAPER: Edition #{edition} published")
                except Exception:
                    pass

            # Pay weekly salaries
            new_week = frame_count // FRAMES_PER_GAME_WEEK
            if new_week > self.game_week:
                self.game_week = new_week
                for npc in self.npcs:
                    salary = SALARY_TIERS.get(npc.occupation, 50)
                    npc.gold += salary
                    self.bank.pay_salary(npc.name, salary)
                self.add_social_log(f"💰 Week {self.game_week}: Salaries paid")

            # Auto court case: every ~3 game weeks a new case is filed
            if (
                not self.court_manager.active_case
                and frame_count > 0
                and frame_count % (FRAMES_PER_GAME_WEEK * 3) == 0
            ):
                suspects = [n for n in self.npcs if getattr(n, "secrets", [])]
                defendant = (
                    random.choice(suspects)
                    if suspects
                    else (random.choice(self.npcs) if self.npcs else None)
                )
                if defendant:
                    charges = [
                        "Suspicious Activity",
                        "Disturbing the Peace",
                        "Property Damage",
                        "Public Misconduct",
                        "Conspiracy",
                    ]
                    charge = random.choice(charges)
                    self.court_manager.file_case(defendant.name, charge, self.npcs)
                    self.show_court = True
                    for npc in self.npcs:
                        npc.target_pos = pygame.Vector2(LOCATIONS["courthouse"])
                    self.add_social_log(
                        f"⚖️ COURT: {defendant.name} charged with {charge}"
                    )

            # Time-slot routine system
            new_slot = (frame_count // 6000) % 3
            if new_slot != self.current_time_slot:
                self.current_time_slot = new_slot
                slot_name = ["morning", "afternoon", "evening"][new_slot]
                for npc in self.npcs:
                    routine_loc = npc.daily_routine.get(slot_name)
                    if routine_loc and routine_loc in LOCATIONS:
                        npc.target_pos = pygame.Vector2(LOCATIONS[routine_loc])
                self.add_social_log(f"🌅 Time: {slot_name.title()}")

            # --- Rendering ---
            self.police_patrol()
            self.screen.blit(self.world, (0, 0))
            for n in self.npcs:
                n.update(self.npcs, self.col, self)
                n.draw(self.screen, self.font_s, n == self.selected_npc)

            self.draw_sidebar()
            self.draw_detail_pane()

            # Draw conversation window (shows deep NPC interactions)
            if (
                self.show_conversation_window
                and not self.show_newspaper
                and not self.show_social_graph
            ):
                self.draw_conversation_window()

            # Newspaper overlay (N key)
            if self.show_newspaper:
                self.draw_newspaper_overlay()

            # Social graph overlay (G key)
            if self.show_social_graph:
                self.draw_social_graph_overlay()

            # Court scene overlay (J key)
            if self.show_court and self.court_manager.active_case:
                self.draw_court_scene(self.screen)

            # Help overlay (F1 key)
            self.help_overlay.draw(self.screen, self.font_s, self.font_m)

            # Story seeder overlay (T key)
            self.story_seeder.draw(self.screen, self.font_s, self.font_m)

            if (
                self.show_journal
                and not self.show_newspaper
                and not self.show_social_graph
            ):
                box = pygame.Rect(300, 150, 1200, 500)  # Wider journal
                pygame.draw.rect(self.screen, (250, 245, 230), box)
                pygame.draw.rect(self.screen, (60, 0, 0), box, 3)
                for i, log in enumerate(self.journal_logs[:18]):  # More entries fit
                    c = (150, 0, 0) if "GUILTY" in log else (0, 80, 0)
                    log_display = log[:140] if len(log) <= 140 else log[:137] + "..."
                    self.screen.blit(
                        self.font_s.render(log_display, True, c),
                        (box.x + 20, box.y + 40 + (i * 25)),
                    )

            pygame.display.flip()
            clock.tick(FPS)


if __name__ == "__main__":
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Playville - Select AI Model")
    font_s = pygame.font.SysFont("Arial", 12)
    font_m = pygame.font.SysFont("Arial", 16, bold=True)
    clock = pygame.time.Clock()

    selector = OllamaModelSelector(screen, font_s, font_m)
    selected_model = selector.run(clock)
    print(f"[STARTUP] Selected Ollama model: {selected_model}")

    pygame.display.set_caption("Playville")
    game = PlayvilleGame()
    game.selected_model = selected_model
    game.run()
