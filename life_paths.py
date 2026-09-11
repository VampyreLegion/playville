"""
NPC Life Paths System for Playville

Tracks and triggers major life events:
- Career changes
- Home moves  
- Relationship milestones
- Personal growth/decline
- Phobias and traumas
- Life goals achieved/failed
- Faction leadership
- Retirement/aging
"""

import random
import time

class LifeEvent:
    """Represents a major life event for an NPC"""
    
    def __init__(self, event_type, description, effects, triggers=None):
        self.event_type = event_type
        self.description = description
        self.effects = effects  # Dict of changes to apply
        self.triggers = triggers or {}  # Conditions that caused this
        self.timestamp = time.time()
        self.resolved = False
    
    def apply_to_npc(self, npc):
        """Apply event effects to NPC"""
        changes = []
        
        # Career change
        if 'new_occupation' in self.effects:
            old = npc.occupation
            npc.occupation = self.effects['new_occupation']
            changes.append(f"Career: {old} → {npc.occupation}")
        
        # Opinion shifts
        if 'opinion_changes' in self.effects:
            for category, change in self.effects['opinion_changes'].items():
                if category in npc.town_opinions:
                    old_val = npc.town_opinions[category]
                    npc.town_opinions[category] = max(-100, min(100, old_val + change))
                    changes.append(f"Opinion on {category}: {old_val:+d} → {npc.town_opinions[category]:+d}")
        
        # Personality changes
        if 'add_trait' in self.effects:
            trait = self.effects['add_trait']
            if trait not in npc.personality:
                npc.personality.append(trait)
                changes.append(f"Gained trait: {trait}")
        
        # Goal changes
        if 'new_goal' in self.effects:
            npc.current_goal = self.effects['new_goal']
            changes.append(f"New life goal: {self.effects['new_goal']}")
        
        return changes


class LifePathManager:
    """Manages NPC life progression and major events"""
    
    def __init__(self):
        self.life_events = {}  # npc_name -> [LifeEvent]
        self.check_interval = 600  # Check every 10 minutes
        self.last_check = time.time()
        
        # Event probability thresholds
        self.career_change_threshold = 0.05  # 5% chance per check
        self.relationship_milestone_threshold = 0.1  # 10% chance if conditions met
        self.trauma_threshold = -60  # Safety opinion threshold
        self.burnout_threshold = -50  # Leadership opinion for officials
    
    def check_and_trigger_events(self, npcs, faction_manager=None, event_history=None):
        """Check all NPCs for life event triggers"""
        current_time = time.time()
        
        if current_time - self.last_check < self.check_interval:
            return []
        
        triggered_events = []
        
        for npc in npcs:
            # Check various life event triggers
            events = []
            
            # CAREER CHANGE: Opinion-driven or faction-driven
            event = self._check_career_change(npc, faction_manager)
            if event:
                events.append(event)
            
            # RELATIONSHIP MILESTONE: Strong relationships
            event = self._check_relationship_milestone(npc, npcs)
            if event:
                events.append(event)
            
            # TRAUMA/PHOBIA: Prolonged negative experience
            event = self._check_trauma_development(npc)
            if event:
                events.append(event)
            
            # BURNOUT: Prolonged stress for leaders
            event = self._check_burnout(npc)
            if event:
                events.append(event)
            
            # FACTION LEADERSHIP: High influence faction member
            event = self._check_faction_leadership(npc, faction_manager)
            if event:
                events.append(event)
            
            # PERSONAL GROWTH: Achieved goals
            event = self._check_personal_growth(npc)
            if event:
                events.append(event)
            
            # Apply events
            for event in events:
                changes = event.apply_to_npc(npc)
                
                # Track event
                if npc.name not in self.life_events:
                    self.life_events[npc.name] = []
                self.life_events[npc.name].append(event)
                
                triggered_events.append({
                    'npc': npc.name,
                    'event': event,
                    'changes': changes
                })
        
        self.last_check = current_time
        return triggered_events
    
    def _check_career_change(self, npc, faction_manager):
        """Check if NPC should change careers"""
        
        # Low chance baseline
        if random.random() > self.career_change_threshold:
            return None
        
        # Career changes based on town opinions and personality
        current_job = npc.occupation
        
        # Doctor/Nurse with low safety → Becomes activist
        if 'Doctor' in current_job or 'Nurse' in current_job:
            if npc.town_opinions.get('safety', 0) < -40:
                return LifeEvent(
                    'career_change',
                    f"{npc.name} leaves medical field to focus on community safety advocacy",
                    {
                        'new_occupation': 'Safety Advocate',
                        'opinion_changes': {'safety': +20},
                        'new_goal': 'Improve town safety through activism'
                    },
                    {'trigger': 'low safety opinion'}
                )
        
        # Business owner with bad economy → Closes shop
        if 'Owner' in current_job or 'Chef' in current_job:
            if npc.town_opinions.get('town_economy', 0) < -45:
                return LifeEvent(
                    'career_change',
                    f"{npc.name} forced to close business due to economic conditions",
                    {
                        'new_occupation': 'Former Business Owner',
                        'opinion_changes': {'town_economy': -20, 'leadership': -15},
                        'add_trait': 'cautious',
                        'new_goal': 'Find new purpose after business failure'
                    },
                    {'trigger': 'economic crisis'}
                )
        
        # Ambitious NPC with strong faction → Becomes organizer
        if 'ambitious' in npc.personality and faction_manager:
            factions = faction_manager.get_npc_factions(npc.name)
            if factions and random.random() < 0.3:
                faction = factions[0]
                return LifeEvent(
                    'career_change',
                    f"{npc.name} becomes full-time community organizer for {faction.name}",
                    {
                        'new_occupation': 'Community Organizer',
                        'opinion_changes': {'leadership': +10, 'community': +15},
                        'new_goal': f"Grow {faction.name} influence"
                    },
                    {'trigger': 'faction involvement'}
                )
        
        return None
    
    def _check_relationship_milestone(self, npc, all_npcs):
        """Check for major relationship events"""
        
        if random.random() > self.relationship_milestone_threshold:
            return None
        
        # Find strongest relationship
        important_rels = npc.get_relationship_summary()
        if not important_rels:
            return None
        
        # Strongest friendship
        friendships = {name: rel for name, rel in important_rels.items() if rel['score'] > 40}
        if friendships:
            best_friend_name = max(friendships, key=lambda x: friendships[x]['score'])
            return LifeEvent(
                'friendship_deepened',
                f"{npc.name} and {best_friend_name} become best friends",
                {
                    'opinion_changes': {'community': +10},
                    'new_goal': f"Support {best_friend_name} in their endeavors"
                },
                {'trigger': f'strong friendship with {best_friend_name}'}
            )
        
        # Bitter rivalry
        rivalries = {name: rel for name, rel in important_rels.items() if rel['score'] < -50}
        if rivalries:
            worst_enemy_name = min(rivalries, key=lambda x: rivalries[x]['score'])
            return LifeEvent(
                'rivalry_intensified',
                f"{npc.name} and {worst_enemy_name} become bitter enemies",
                {
                    'opinion_changes': {'community': -10},
                    'add_trait': 'suspicious',
                    'new_goal': f"Avoid {worst_enemy_name} at all costs"
                },
                {'trigger': f'intense conflict with {worst_enemy_name}'}
            )
        
        return None
    
    def _check_trauma_development(self, npc):
        """Check if NPC develops trauma/phobia from prolonged stress"""
        
        safety_opinion = npc.town_opinions.get('safety', 0)
        
        # Prolonged extreme fear
        if safety_opinion < self.trauma_threshold:
            safety_memories = npc.memory_themes.get('safety_concern', [])
            if len(safety_memories) > 5:
                
                # Don't re-traumatize if already paranoid
                if 'paranoid' in npc.personality:
                    return None
                
                return LifeEvent(
                    'trauma_developed',
                    f"{npc.name} develops anxiety from prolonged safety concerns",
                    {
                        'add_trait': 'paranoid',
                        'opinion_changes': {'safety': -10, 'community': -10},
                        'new_goal': 'Find a way to feel safe again'
                    },
                    {'trigger': 'prolonged safety fears'}
                )
        
        return None
    
    def _check_burnout(self, npc):
        """Check if NPC experiences burnout"""
        
        # Only applies to leaders/officials
        leadership_jobs = ['Mayor', 'Judge', 'Police Chief', 'Factory Boss']
        if not any(job in npc.occupation for job in leadership_jobs):
            return None
        
        leadership_opinion = npc.town_opinions.get('leadership', 0)
        
        # Burnout from criticism
        if leadership_opinion < self.burnout_threshold:
            return LifeEvent(
                'burnout',
                f"{npc.name} experiences burnout from leadership responsibilities",
                {
                    'opinion_changes': {'leadership': -15, 'community': -10},
                    'new_goal': 'Consider stepping down from leadership role'
                },
                {'trigger': 'prolonged criticism and stress'}
            )
        
        return None
    
    def _check_faction_leadership(self, npc, faction_manager):
        """Check if NPC becomes faction leader"""
        
        if not faction_manager:
            return None
        
        # Already a leader type
        if 'Leader' in npc.occupation or 'Organizer' in npc.occupation:
            return None
        
        factions = faction_manager.get_npc_factions(npc.name)
        if not factions:
            return None
        
        # Chance to become faction voice
        if 'ambitious' in npc.personality and random.random() < 0.15:
            faction = factions[0]
            return LifeEvent(
                'faction_leadership',
                f"{npc.name} emerges as a leader of {faction.name}",
                {
                    'opinion_changes': {'leadership': +15, 'community': +10},
                    'new_goal': f"Lead {faction.name} to achieve its goals"
                },
                {'trigger': f'faction involvement in {faction.name}'}
            )
        
        return None
    
    def _check_personal_growth(self, npc):
        """Check if NPC achieves personal growth"""
        
        # Overcome past trauma
        if 'paranoid' in npc.personality:
            safety_opinion = npc.town_opinions.get('safety', 0)
            if safety_opinion > 30:  # Safety improved significantly
                return LifeEvent(
                    'personal_growth',
                    f"{npc.name} overcomes past anxieties as town safety improves",
                    {
                        'opinion_changes': {'safety': +10, 'community': +10},
                        'new_goal': 'Help others feel safe'
                    },
                    {'trigger': 'improved safety conditions'}
                )
        
        # Ambitious person achieving influence
        if 'ambitious' in npc.personality:
            if len(npc.trust_network) > 5:
                return LifeEvent(
                    'personal_growth',
                    f"{npc.name} achieves social influence through strong network",
                    {
                        'opinion_changes': {'leadership': +10, 'community': +10},
                        'new_goal': 'Use influence to help the town'
                    },
                    {'trigger': 'built strong trust network'}
                )
        
        return None
    
    def get_npc_life_story(self, npc_name, limit=10):
        """Get life event history for an NPC"""
        if npc_name not in self.life_events:
            return []
        
        events = self.life_events[npc_name][-limit:]
        
        return [{
            'type': event.event_type,
            'description': event.description,
            'timestamp': event.timestamp,
            'triggers': event.triggers
        } for event in events]
    
    def get_recent_life_events(self, limit=10):
        """Get most recent life events across all NPCs"""
        all_events = []
        
        for npc_name, events in self.life_events.items():
            for event in events:
                all_events.append({
                    'npc': npc_name,
                    'type': event.event_type,
                    'description': event.description,
                    'timestamp': event.timestamp
                })
        
        # Sort by timestamp
        all_events.sort(key=lambda x: x['timestamp'], reverse=True)
        
        return all_events[:limit]


# Example usage
if __name__ == "__main__":
    # Mock NPC
    class MockNPC:
        def __init__(self, name):
            self.name = name
            self.occupation = "Store Owner"
            self.personality = ['ambitious']
            self.town_opinions = {
                'safety': -65,
                'town_economy': -30,
                'leadership': -20,
                'community': 10
            }
            self.memory_themes = {
                'safety_concern': ['worry1', 'worry2', 'worry3', 'worry4', 'worry5', 'worry6']
            }
            self.trust_network = {'Alice': 'trusted', 'Bob': 'trusted'}
            self.current_goal = "Run successful store"
            self.relationships = {
                'Alice': {'score': 45, 'sentiment': 'Friendly'},
                'Bob': {'score': -55, 'sentiment': 'Hostile'}
            }
        
        def get_relationship_summary(self):
            return {k: v for k, v in self.relationships.items() if abs(v['score']) > 20}
    
    lpm = LifePathManager()
    npc = MockNPC("Test NPC")
    
    events = lpm.check_and_trigger_events([npc])
    
    print(f"Triggered {len(events)} life events:")
    for event_data in events:
        print(f"\n{event_data['npc']}: {event_data['event'].description}")
        for change in event_data['changes']:
            print(f"  - {change}")
