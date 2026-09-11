import random
import time
from config import LOCATIONS


class TownEvent:
    """Represents a dynamic event that affects the town"""

    def __init__(
        self,
        event_type,
        description,
        severity=1,
        affected_npcs=None,
        location=None,
        duration=300,
    ):
        self.event_type = event_type
        self.description = description
        self.severity = severity
        self.affected_npcs = affected_npcs or []
        self.location = location
        self.start_time = time.time()
        self.duration = duration
        self.is_active = True

    def is_expired(self):
        return time.time() - self.start_time > self.duration

    def get_remaining_time(self):
        return max(0, self.duration - (time.time() - self.start_time))


class TownEventManager:
    """Manages random town events and incidents"""

    def __init__(self):
        self.active_events = []
        self.event_history = []
        self.last_event_time = 0
        self.event_cooldown = (
            1800  # Minimum frames between events (30 seconds at 60fps)
        )
        self.frame_counter = 0

    def update(self, npcs, game_ref):
        """Check for and trigger new events"""
        self.frame_counter += 1

        # Check if any events have expired
        for event in self.active_events[:]:
            if event.is_expired():
                event.is_active = False
                self.active_events.remove(event)
                self.event_history.append(event)
                game_ref.add_social_log(f"Event ended: {event.description}")

        # Only trigger new events periodically
        if self.frame_counter - self.last_event_time < self.event_cooldown:
            return None

        # Random chance to trigger event
        if random.random() < 0.02:  # 2% chance per frame after cooldown
            return self._trigger_random_event(npcs, game_ref)

        return None

    def _trigger_random_event(self, npcs, game_ref):
        """Trigger a random town event"""
        event_types = [
            self._create_accident,
            self._create_discovery,
            self._create_argument,
            self._create_celebration,
            self._create_weather_event,
            self._create_emergency,
            self._create_social_gathering,
            self._create_market_day,
        ]

        event_creator = random.choice(event_types)
        event = event_creator(npcs)

        if event:
            self.active_events.append(event)
            self.last_event_time = self.frame_counter
            self._apply_event_effects(event, npcs, game_ref)

            # Announce event
            announcement = f"🚨 TOWN EVENT: {event.description}"
            game_ref.add_social_log(announcement)

            return event
        return None

    def _create_accident(self, npcs):
        """Someone got hurt or something broke"""
        locations = ["store", "factory", "town_square", "church", "bank"]
        location = random.choice(locations)

        descriptions = [
            f"A cart overturned on Main Street, blocking traffic near the {location}",
            f"Someone slipped on the wet cobblestones near the {location}",
            f"A ladder fell at the {location} - looks like someone was hurt",
            f"A pipe burst near the {location}, flooding the street",
            f"An overturned crate spilled contents everywhere near the {location}",
        ]

        return TownEvent(
            event_type="accident",
            description=random.choice(descriptions),
            severity=random.randint(1, 3),
            location=location,
            duration=random.randint(300, 600),
        )

    def _create_discovery(self, npcs):
        """Something interesting was found"""
        locations = ["graveyard", "library", "factory", "church", "store"]
        location = random.choice(locations)

        descriptions = [
            f"Workers found something strange digging near the {location}",
            f"The librarian discovered a hidden compartment in an old book",
            f"A child found an old coin near the {location}",
            f"An old map was found in the attic of the {location}",
            f"Construction workers uncovered something unusual at the {location}",
        ]

        return TownEvent(
            event_type="discovery",
            description=random.choice(descriptions),
            severity=random.randint(1, 2),
            location=location,
            duration=random.randint(600, 900),
        )

    def _create_argument(self, npcs):
        """Two people are fighting"""
        locations = ["store", "town_square", "gazette", "bank"]
        location = random.choice(locations)

        descriptions = [
            f"Two townsfolk were yelling at each other in the square",
            f"Overheard a heated argument at the {location} about money",
            f"The Mayor and Judge were disagreeing loudly at the {location}",
            f"A heated debate at the {location} is drawing a crowd",
            f"Someone is causing a scene at the {location}",
        ]

        return TownEvent(
            event_type="argument",
            description=random.choice(descriptions),
            severity=random.randint(1, 2),
            location=location,
            duration=random.randint(180, 360),
        )

    def _create_celebration(self, npcs):
        """Something happy is happening"""
        descriptions = [
            "Someone's birthday - there's cake at the gazette",
            "A wedding procession is starting from the church",
            "The factory announced a celebration for hitting quotas",
            "A local band is playing in the town square",
            "Someone just got engaged! News is spreading fast",
        ]

        return TownEvent(
            event_type="celebration",
            description=random.choice(descriptions),
            severity=1,
            location="town_square",
            duration=random.randint(300, 500),
        )

    def _create_weather_event(self, npcs):
        """Weather changes"""
        weather_types = [
            ("storm", "A sudden storm rolled in from the east"),
            ("fog", "The fog is unusually thick this morning"),
            ("snow", "Snow has started falling - first of the season"),
            ("rain", "A heavy rain started suddenly"),
            ("heat", "A heat wave is making everyone miserable"),
        ]

        weather_type, description = random.choice(weather_types)

        return TownEvent(
            event_type="weather",
            description=description,
            severity=random.randint(1, 2),
            location=None,
            duration=random.randint(400, 800),
        )

    def _create_emergency(self, npcs):
        """Something dangerous is happening"""
        emergencies = [
            ("fire", "Smoke was seen rising from near the factory!", "factory"),
            (
                "theft",
                "A shopkeeper reports items missing from their inventory!",
                "store",
            ),
            (
                "intruder",
                "Suspicious figures seen near the graveyard after dark!",
                "graveyard",
            ),
            (
                "medical",
                "Someone collapsed in the town square - Doctor needed!",
                "town_square",
            ),
            (
                "animal",
                "A wild animal was spotted near the residential area!",
                "house_a",
            ),
        ]

        emergency_type, description, location = random.choice(emergencies)

        return TownEvent(
            event_type="emergency",
            description=description,
            severity=random.randint(2, 4),
            location=location,
            duration=random.randint(400, 700),
        )

    def _create_social_gathering(self, npcs):
        """People are getting together"""
        gatherings = [
            "A group is playing cards at the gazette",
            "Children are playing in the town square",
            "A group of locals are having lunch together",
            "Some townsfolk are playing horseshoes",
            "A book club is meeting at the library",
        ]

        return TownEvent(
            event_type="gathering",
            description=random.choice(gatherings),
            severity=1,
            location="town_square",
            duration=random.randint(300, 500),
        )

    def _create_market_day(self, npcs):
        """It's market day!"""

        return TownEvent(
            event_type="market",
            description="Market day! Vendors have set up stalls in the town square",
            severity=1,
            location="town_square",
            duration=random.randint(500, 800),
        )

    def _apply_event_effects(self, event, npcs, game_ref):
        """Apply the effects of an event to NPCs"""
        event_npcs = []

        if event.location:
            # Find NPCs who should react to this location
            for npc in npcs:
                if npc.daily_routine:
                    # NPCs who frequent this location might investigate
                    routine_locs = list(npc.daily_routine.values())
                    if event.location in routine_locs:
                        event_npcs.append(npc)

        event.affected_npcs = event_npcs

        # Apply opinion changes based on event type
        if event.event_type == "emergency":
            for npc in npcs:
                if "safety" in npc.town_opinions:
                    npc.town_opinions["safety"] -= event.severity * 3
                if "leadership" in npc.town_opinions:
                    npc.town_opinions["leadership"] -= event.severity * 2

        elif event.event_type == "celebration":
            for npc in npcs:
                if "community" in npc.town_opinions:
                    npc.town_opinions["community"] += 3

        elif event.event_type == "argument":
            for npc in npcs:
                if "community" in npc.town_opinions:
                    npc.town_opinions["community"] -= 2

        # Make NPCs investigate interesting events - only 1-2 NPCs max
        investigators = 0
        if event.location and event.severity >= 3:
            for npc in npcs:
                if investigators >= 2:
                    break
                # Only very paranoid NPCs investigate
                if any(t in npc.personality for t in ["paranoid", "suspicious"]):
                    if random.random() < 0.2:
                        if event.location in LOCATIONS:
                            npc.target_pos = LOCATIONS[event.location]
                            npc.current_goal = (
                                f"Investigate the incident at {event.location}"
                            )
                            investigators += 1

        # Make NPCs go to celebrations - only a couple NPCs
        celebrators = 0
        if event.event_type == "celebration" or event.event_type == "market":
            for npc in npcs:
                if celebrators >= 2:
                    break
                if "friendly" in npc.personality:
                    if random.random() < 0.2:
                        npc.target_pos = LOCATIONS["town_square"]
                        celebrators += 1

    def get_active_events(self):
        """Return list of currently active events"""
        return [e for e in self.active_events if e.is_active]

    def get_event_announcements(self):
        """Return formatted announcements for active events"""
        announcements = []
        for event in self.active_events:
            remaining = int(event.get_remaining_time() / 60) + 1
            announcements.append(f"[{remaining}m] {event.description}")
        return announcements


class NPCActivityManager:
    """Manages NPC daily activities beyond just walking around"""

    def __init__(self):
        self.npc_activities = {}  # npc_name -> current_activity
        self.activity_types = [
            "working",
            "shopping",
            "socializing",
            "resting",
            "walking",
            "observing",
            "waiting",
        ]

    def update(self, npcs, locations, frame_count):
        """Update NPC activities based on time and location"""
        time_of_day = (frame_count % 3600) / 3600  # 0-1 during game day

        for npc in npcs:
            activity = self._determine_activity(npc, time_of_day, locations)
            self.npc_activities[npc.name] = activity

            # Apply activity-based behavior
            self._apply_activity_behavior(npc, activity, locations, frame_count)

    def _determine_activity(self, npc, time_of_day, locations):
        """Determine what an NPC should be doing"""
        # Morning (0-0.3): Going to work
        if time_of_day < 0.3:
            return (
                "working"
                if hasattr(npc, "occupation") and npc.occupation
                else "walking"
            )
        # Mid-day (0.3-0.7): Work or shopping
        elif time_of_day < 0.7:
            if random.random() < 0.1:
                return "shopping"
            return "working"
        # Evening (0.7-0.9): Socializing
        elif time_of_day < 0.9:
            return "socializing" if random.random() < 0.3 else "walking"
        # Night (0.9-1.0): Resting or going home
        else:
            return "resting"

    def _apply_activity_behavior(self, npc, activity, locations, frame_count):
        """Apply activity-specific behavior - only if NPC doesn't have a specific goal"""
        # Don't override if NPC is already moving toward something specific
        if hasattr(npc, "current_goal") and npc.current_goal:
            return

        # Only occasionally redirect NPCs (5% chance per frame)
        if random.random() > 0.05:
            return

        if activity == "shopping":
            npc.target_pos = pygame.Vector2(locations["store"])

        elif activity == "socializing":
            npc.target_pos = pygame.Vector2(locations["town_square"])

        elif activity == "resting":
            if hasattr(npc, "home_position"):
                npc.target_pos = pygame.Vector2(npc.home_position)

    def get_activity_summary(self):
        """Get a summary of what NPCs are doing"""
        activity_counts = {}
        for activity in self.activity_types:
            activity_counts[activity] = 0

        for activity in self.npc_activities.values():
            if activity in activity_counts:
                activity_counts[activity] += 1

        return activity_counts


# Import pygame for Vector2
import pygame
