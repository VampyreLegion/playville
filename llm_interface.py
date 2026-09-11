import uuid
import random
import time
import json
import os

DATA_FILE = os.path.join(os.path.dirname(__file__), "character_data.json")

def load_character_data():
    """Load character configuration from JSON file"""
    try:
        with open(DATA_FILE, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"[ERROR] character_data.json not found at {DATA_FILE}")
        return {}
    except json.JSONDecodeError as e:
        print(f"[ERROR] Failed to parse character_data.json: {e}")
        return {}

CHAR_DATA = load_character_data()

PERSONALITY_WEIGHTS = CHAR_DATA.get("personality_weights", {})
GOAL_TEMPLATES = CHAR_DATA.get("goal_templates", {})
EMOTION_TRIGGERS = CHAR_DATA.get("emotion_triggers", {})
WISH_CATEGORIES = CHAR_DATA.get("wish_categories", {})
WISH_WEIGHTS = CHAR_DATA.get("wish_weights", {})
MEMORY_THEMES = CHAR_DATA.get("memory_themes", {})
THOUGHT_TEMPLATES = CHAR_DATA.get("thought_templates", {})
INTERACTION_TEMPLATES = CHAR_DATA.get("interaction_templates", {})
SOLO_REFLECTIONS = CHAR_DATA.get("solo_reflections", {})
GOSSIP_TOPICS = CHAR_DATA.get("gossip_topics", [])
SENTIMENT_REASONS = CHAR_DATA.get("sentiment_reasons", {})
OCCUPATION_INFLUENCES = CHAR_DATA.get("occupation_influences", {})
TOWN_EVENTS = CHAR_DATA.get("town_events", {})

def get_town_events():
    """Return town events dictionary for game use"""
    return TOWN_EVENTS

def calculate_importance(sentiment, is_suspicious, nearby_npc, goal_related):
    """Calculate memory importance score (0-100)"""
    score = 50
    
    if is_suspicious:
        score += 30
    if sentiment in ["Hostile", "Suspicious"]:
        score += 15
    if nearby_npc:
        score += 10
    if goal_related:
        score += 20
    
    return min(100, score)

def weighted_choice(weights_dict):
    """Make a weighted random choice"""
    choices = list(weights_dict.keys())
    weights = list(weights_dict.values())
    return random.choices(choices, weights=weights, k=1)[0]

def generate_sentiment_reason(name, nearby_npc, sentiment, memories, personality):
    """Generate a reason for the sentiment"""
    reasons = SENTIMENT_REASONS.get(sentiment, SENTIMENT_REASONS.get("Neutral", []))
    formatted = [r.replace("{npc}", nearby_npc) for r in reasons]
    return random.choice(formatted) if formatted else "No particular reason"

def generate_wish(personality_traits, occupation, core_values, fears, town_opinions):
    """Generate a wish based on NPC characteristics and town state"""
    
    wish_category_weights = {"infrastructure": 0.15, "social": 0.15, "economy": 0.15, "safety": 0.15, "personal": 0.2, "political": 0.2}
    
    for trait in personality_traits:
        if trait in WISH_WEIGHTS:
            for category, weight in WISH_WEIGHTS[trait].items():
                wish_category_weights[category] = wish_category_weights.get(category, 0) + weight
    
    for job_keyword, influences in OCCUPATION_INFLUENCES.items():
        if job_keyword in occupation:
            for category, weight in influences.items():
                wish_category_weights[category] = wish_category_weights.get(category, 0) + weight
    
    if town_opinions:
        if town_opinions.get("safety", 0) < -30:
            wish_category_weights["safety"] = wish_category_weights.get("safety", 0) + 0.3
        if town_opinions.get("town_economy", 0) < -30:
            wish_category_weights["economy"] = wish_category_weights.get("economy", 0) + 0.3
        if town_opinions.get("infrastructure", 0) < -30:
            wish_category_weights["infrastructure"] = wish_category_weights.get("infrastructure", 0) + 0.3
    
    total = sum(wish_category_weights.values())
    wish_category_weights = {k: v/total for k, v in wish_category_weights.items()}
    
    category = weighted_choice(wish_category_weights)
    wish = random.choice(WISH_CATEGORIES.get(category, ["Nothing specific"]))
    
    return {"category": category, "wish": wish}

def classify_memory_theme(thought_text):
    """Classify a thought into thematic categories"""
    themes = []
    thought_lower = thought_text.lower()
    
    for theme, keywords in MEMORY_THEMES.items():
        for keyword in keywords:
            if keyword in thought_lower:
                themes.append(theme)
                break
    
    return themes if themes else ["general"]

def _get_interaction_text(template_key, npc_name, location, sentiment=None):
    """Get interaction text from templates, handling None values"""
    templates = INTERACTION_TEMPLATES.get(template_key, {})
    if not templates:
        return None
    
    result = None
    
    if sentiment and sentiment in templates:
        sentiment_templates = templates[sentiment]
        if isinstance(sentiment_templates, dict):
            keys = list(sentiment_templates.keys())
            if keys:
                selected = random.choice(keys)
                result = random.choice(sentiment_templates[selected])
        else:
            result = random.choice(sentiment_templates)
    else:
        keys = list(templates.keys())
        if keys:
            selected = random.choice(keys)
            data = templates[selected]
            if isinstance(data, list):
                result = random.choice(data)
            elif isinstance(data, dict):
                subkeys = list(data.keys())
                if subkeys:
                    result = random.choice(data[random.choice(subkeys)])
                else:
                    result = None
            else:
                result = data
    
    if result:
        result = result.replace("{npc}", npc_name).replace("{location}", location)
    return result

def get_npc_thought(name, bio, collection, nearby_npc, event, personality_traits, current_goal,
                   emotional_state, relationship_history, secrets_known, occupation="Unknown",
                   core_values=None, fears=None, town_opinions=None, thinking_depth=3):
    """
    Enhanced NPC cognition with deep personality, goals, memory integration, wishes, and opinions.
    Now loads all templates from character_data.json
    """
    timestamp = time.time()

    memory_results = max(2, thinking_depth * 2)

    recent_memories = []
    relationship_memories = []

    try:
        recent_query = collection.query(
            query_texts=[f"Recent thoughts and observations by {name}"],
            n_results=memory_results,
            where={"speaker": name}
        )
        if recent_query and recent_query.get('documents'):
            recent_memories = recent_query['documents'][0] if recent_query['documents'] else []

        if nearby_npc:
            rel_query = collection.query(
                query_texts=[f"{name}'s feelings and interactions with {nearby_npc}"],
                n_results=max(2, thinking_depth)
            )
            if rel_query and rel_query.get('documents'):
                relationship_memories = rel_query['documents'][0] if rel_query['documents'] else []
    except Exception as e:
        pass
    
    sentiment_weights = {"Neutral": 0.3, "Friendly": 0.3, "Suspicious": 0.2, "Hostile": 0.2}
    
    for trait in personality_traits:
        if trait in PERSONALITY_WEIGHTS:
            trait_weights = PERSONALITY_WEIGHTS[trait]
            for sent, weight in trait_weights.items():
                sentiment_weights[sent] = sentiment_weights.get(sent, 0) + weight
    
    total_weight = sum(sentiment_weights.values())
    sentiment_weights = {k: v/total_weight for k, v in sentiment_weights.items()}
    
    new_sentiment = weighted_choice(sentiment_weights)
    new_emotion = EMOTION_TRIGGERS.get(new_sentiment, emotional_state)
    
    opinion_changes = {}
    if town_opinions:
        for category in ["town_economy", "safety", "infrastructure", "leadership", "community"]:
            if category in town_opinions:
                drift = random.randint(-2, 2)
                if "paranoid" in personality_traits and category == "safety":
                    drift -= 1
                if "ambitious" in personality_traits and category in ["town_economy", "leadership"]:
                    drift += random.choice([-1, 0, 1])
                
                opinion_changes[category] = drift
    
    locs = ["store", "courthouse", "jail", "library", "factory", "graveyard", "town_square", "bank", "church", "doctor"]
    chosen_loc = random.choice(locs)
    
    goal_related = False
    if current_goal:
        if "investigate" in current_goal.lower() or "watch" in current_goal.lower():
            if random.random() < 0.6:
                chosen_loc = random.choice(["courthouse", "jail", "library"])
                goal_related = True
        elif "avoid" in current_goal.lower():
            chosen_loc = random.choice([loc for loc in locs if loc not in ["courthouse", "jail"]])
        elif "routine" in current_goal.lower():
            occ_lower = occupation.lower()
            if "judge" in occ_lower:
                chosen_loc = "courthouse"
                goal_related = True
            elif "police" in occ_lower or "chief" in occ_lower:
                chosen_loc = "jail"
                goal_related = True
            elif "librarian" in occ_lower:
                chosen_loc = "library"
                goal_related = True
            elif "store" in occ_lower:
                chosen_loc = "store"
                goal_related = True
            elif "factory" in occ_lower:
                chosen_loc = "factory"
                goal_related = True
    
    observation = f"{name} is heading to the {chosen_loc}"
    interpretation = ""
    emotional_reaction = ""
    decision = ""
    opinion_expression = None
    
    occupation_lower = occupation.lower()
    
    if nearby_npc:
        sentiment_reason = generate_sentiment_reason(name, nearby_npc, new_sentiment, relationship_memories, personality_traits)
        
        obs = _get_interaction_text(new_sentiment, nearby_npc, chosen_loc, "observations")
        if obs:
            observation = obs
        
        interp = _get_interaction_text(new_sentiment, nearby_npc, chosen_loc, "interpretations")
        if interp:
            interpretation = interp
        elif not interpretation:
            if new_sentiment == "Friendly":
                interpretation = random.choice(SOLO_REFLECTIONS.get("friendly", SOLO_REFLECTIONS.get("default", ["Just another day."])))
            elif new_sentiment == "Hostile":
                interpretation = "This town has too many problems."
            else:
                interpretation = "Keep moving forward."
        
        dec = _get_interaction_text(new_sentiment, nearby_npc, chosen_loc, "decisions")
        if dec:
            decision = dec
        elif not decision:
            decision = "Stay focused on my goals."
        
        emotional_reaction = f"Feeling {new_emotion}"
        
    else:
        occ_key = None
        if "judge" in occupation_lower:
            occ_key = "judge"
        elif "mayor" in occupation_lower:
            occ_key = "mayor"
        elif "police" in occupation_lower or "chief" in occupation_lower:
            occ_key = "police"
        elif "librarian" in occupation_lower:
            occ_key = "librarian"
        elif "doctor" in occupation_lower or "dr." in occupation_lower.replace(".", ""):
            occ_key = "doctor"
        elif "reporter" in occupation_lower or "newspaper" in occupation_lower:
            occ_key = "reporter"
        elif "whisper" in name.lower():
            occ_key = "whisper"
        
        if occ_key and occ_key in THOUGHT_TEMPLATES:
            template = THOUGHT_TEMPLATES[occ_key]
            
            if "neutral" in template:
                observation = random.choice(template["neutral"]).replace("{location}", chosen_loc)
            
            trait_key = None
            if "stern" in personality_traits and "stern_interpretations" in template:
                trait_key = "stern_interpretations"
            elif "ambitious" in personality_traits and "ambitious_interpretations" in template:
                trait_key = "ambitious_interpretations"
            elif "paranoid" in personality_traits and "paranoid_interpretations" in template:
                trait_key = "paranoid_interpretations"
            elif "gossipy" in personality_traits and "gossipy_interpretations" in template:
                trait_key = "gossipy_interpretations"
            elif "analytical" in personality_traits and "analytical_interpretations" in template:
                trait_key = "analytical_interpretations"
            elif "responsible_interpretations" in template:
                trait_key = "responsible_interpretations"
            elif "kind_interpretations" in template:
                trait_key = "kind_interpretations"
            elif "struggling_interpretations" in template:
                trait_key = "struggling_interpretations"
            elif "thoughtful_interpretations" in template:
                trait_key = "thoughtful_interpretations"
            elif "interpretations" in template:
                trait_key = "interpretations"
            
            if trait_key and trait_key in template:
                interpretation = random.choice(template[trait_key])
            elif "interpretations" in template:
                interpretation = random.choice(template["interpretations"])
        else:
            solo_key = None
            for key in ["paranoid", "friendly", "ambitious", "analytical", "stern"]:
                if key in personality_traits:
                    solo_key = key
                    break
            
            if not solo_key:
                solo_key = "default"
            
            reflections = SOLO_REFLECTIONS.get(solo_key, SOLO_REFLECTIONS.get("default", ["Just another day."]))
            interpretation = random.choice(reflections)
            
            activity_templates = [
                f"heading to the {chosen_loc} for work",
                f"on the way to the {chosen_loc}, mind wandering",
                f"walking to the {chosen_loc}, thinking about the day ahead"
            ]
            observation = random.choice(activity_templates)
        
        emotional_reaction = f"Feeling {new_emotion}"
        
        if town_opinions and random.random() < 0.20:
            opinion_categories = ["town_economy", "safety", "infrastructure", "leadership", "community"]
            opinion_cat = random.choice(opinion_categories)
            opinion_score = town_opinions.get(opinion_cat, 0)
            
            if opinion_score < -40:
                opinion_expression = f"The {opinion_cat.replace('_', ' ')} situation is reaching a crisis point"
            elif opinion_score < -20:
                opinion_expression = f"Concerned about where {opinion_cat.replace('_', ' ')} is heading"
            elif opinion_score > 40:
                opinion_expression = f"Genuinely proud of our {opinion_cat.replace('_', ' ')}"
            elif opinion_score > 20:
                opinion_expression = f"Good to see {opinion_cat.replace('_', ' ')} improving"
        
        if current_goal and "investigate" in current_goal.lower():
            decision = f"Need to {current_goal.lower()}"
        elif opinion_expression:
            decision = opinion_expression
        else:
            if "paranoid" in personality_traits:
                decision = "Staying alert. Trust my instincts."
            elif "ambitious" in personality_traits:
                decision = "Moving forward. Eyes on the prize."
            elif "stern" in personality_traits:
                decision = "Stay focused. Keep standards high."
            else:
                decision = "One step at a time."
    
    is_suspicious = (new_sentiment in ["Suspicious", "Hostile"]) or (random.random() < 0.15)
    
    if "paranoid" in personality_traits or "suspicious" in personality_traits:
        is_suspicious = is_suspicious or (random.random() < 0.25)
    
    status_tag = "[GUILTY]" if is_suspicious else "[CLEARED]"
    
    thought_parts = []
    if observation:
        thought_parts.append(observation)
    if interpretation:
        thought_parts.append(interpretation)
    if decision:
        thought_parts.append(decision)
    
    thought_content = ". ".join(thought_parts) if thought_parts else "Wandering through town"
    thought = f"{status_tag} {thought_content}"
    
    thought_components = {
        'observation': observation,
        'interpretation': interpretation,
        'emotional_reaction': emotional_reaction,
        'decision': decision
    }
    
    importance = calculate_importance(new_sentiment, is_suspicious, nearby_npc, goal_related)
    memory_themes = classify_memory_theme(thought)
    
    gossip = None
    if "gossipy" in personality_traits and nearby_npc and random.random() < 0.3:
        gossip_template = random.choice(GOSSIP_TOPICS)
        gossip = gossip_template.replace("{location}", chosen_loc).replace("{npc}", random.choice(["Elias", "Ben", "Marco", "Kai"]))
    
    new_goal = current_goal
    if random.random() < 0.15:
        if is_suspicious and nearby_npc:
            new_goal = random.choice(GOAL_TEMPLATES.get("investigate", ["Investigate"])).replace("{target}", nearby_npc)
        elif new_sentiment == "Friendly" and nearby_npc:
            new_goal = random.choice(GOAL_TEMPLATES.get("befriend", ["Be friendly"])).replace("{target}", nearby_npc)
        elif new_sentiment == "Hostile" and nearby_npc:
            new_goal = random.choice(GOAL_TEMPLATES.get("avoid", ["Avoid"])).replace("{target}", nearby_npc)
        else:
            new_goal = random.choice(GOAL_TEMPLATES.get("routine", ["Check location"])).replace("{location}", chosen_loc)
    
    wish_data = None
    wish_chance = 0.07
    if "ambitious" in personality_traits or "analytical" in personality_traits:
        wish_chance += 0.03
    
    if random.random() < wish_chance:
        wish_data = generate_wish(personality_traits, occupation, core_values or [], fears or [], town_opinions or {})
    
    try:
        collection.add(
            documents=[thought],
            metadatas=[{
                "speaker": name,
                "memory_type": "social_observation" if nearby_npc else "routine_action",
                "timestamp": timestamp,
                "importance": importance,
                "is_suspicious": is_suspicious,
                "service_loc": chosen_loc if is_suspicious else "none",
                "nearby_npc": str(nearby_npc) if nearby_npc else "none",
                "sentiment": new_sentiment,
                "sentiment_reason": interpretation if nearby_npc else "none",
                "emotional_state": new_emotion,
                "goal_related": goal_related,
                "current_goal": str(new_goal) if new_goal else "none",
                "gossip": str(gossip) if gossip else "none",
                "related_npcs": json.dumps([nearby_npc] if nearby_npc else []),
                "memory_themes": json.dumps(memory_themes),
                "wish_category": wish_data["category"] if wish_data else "none",
                "wish_content": wish_data["wish"] if wish_data else "none"
            }],
            ids=[str(uuid.uuid4())]
        )
    except Exception as e:
        pass
    
    return {
        "thought": thought,
        "thought_components": thought_components,
        "location": chosen_loc,
        "nearby_npc": nearby_npc,
        "sentiment": new_sentiment,
        "sentiment_reason": interpretation if nearby_npc else None,
        "emotion": new_emotion,
        "new_goal": new_goal,
        "gossip": gossip,
        "importance": importance,
        "is_suspicious": is_suspicious,
        "opinion_changes": opinion_changes,
        "opinion_expression": opinion_expression,
        "wish": wish_data,
        "memory_themes": memory_themes
    }
