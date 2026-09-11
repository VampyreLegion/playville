# Game display
SCREEN_WIDTH = 2300
SCREEN_HEIGHT = 1024
SIDEBAR_WIDTH = 500
FPS = 60

# NPC behavior
AUTONOMOUS_INTERVAL = 1200  # frames between thought generation
WISH_CHANCE = 0.07
GOSSIP_CHANCE = 0.30
OPINION_DRIFT_MAX = 3

# Newspaper
NEWSPAPER_INTERVAL = 300  # seconds (5 minutes = 1 in-game day)
MAX_NEWSPAPER_EDITIONS = 5

# Factions
FACTION_FORMATION_THRESHOLD = 2  # min NPCs to form faction
FACTION_OPINION_THRESHOLD = 25  # min opinion strength

# Life paths
LIFE_PATH_CHECK_INTERVAL = 600  # seconds

# Town consensus
CONSENSUS_THRESHOLD = 5  # NPCs needed to trigger whisper

# ChromaDB
CHROMA_PERSIST_PATH = "./chroma_data"

# Player economy
PLAYER_START_GOLD = 100
PLAYER_START_POS = (700, 750)
STORE_INTERACTION_RADIUS = 80

# Ollama
DEFAULT_MODEL = "llama3.1:8b"
OLLAMA_CONFIG_FILE = "ollama_config.json"

# Economy
FRAMES_PER_GAME_WEEK = 18000  # 5 min at 60fps = 1 in-game week
SALARY_TIERS = {
    "Judge": 200,
    "Mayor": 200,
    "Doctor": 200,
    "Banker": 175,
    "Police Chief": 150,
    "Factory Boss": 150,
    "Store Owner": 100,
    "Chef/Restaurant Owner": 100,
    "Librarian": 100,
    "Newspaper Reporter": 100,
    "Artist": 75,
    "Traveler/Drifter": 75,
    "Priest": 75,
    "Schoolteacher": 75,
    "Unknown": 50,
}

# New building positions (map pixel coords)
BANK_POS = (1200, 300)
CHURCH_POS = (1600, 700)

# Location coordinates for NPC movement
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

# Court
COURT_PHASE_DURATION = {
    "opening": 300,  # frames
    "evidence": 180,  # frames per evidence item
    "deliberation": 600,
    "verdict": 480,
}
