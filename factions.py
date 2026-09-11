"""
Factions & Political Groups System for Playville

NPCs with similar opinions naturally form political groups and alliances.
Factions compete for influence and push different agendas.
"""

import time
from collections import defaultdict

class Faction:
    """Represents a political/social faction in town"""
    
    def __init__(self, name, focus_category, alignment, description):
        self.name = name
        self.focus_category = focus_category  # What opinion category they care about
        self.alignment = alignment  # 'positive' or 'negative' (satisfied vs. dissatisfied)
        self.description = description
        self.members = []  # List of NPC names
        self.influence = 0  # 0-100, based on member count and their social status
        self.agenda = []  # List of wishes/demands
        self.formed_at = time.time()
        self.active = True
        
    def add_member(self, npc_name):
        """Add NPC to faction"""
        if npc_name not in self.members:
            self.members.append(npc_name)
            self.update_influence()
    
    def remove_member(self, npc_name):
        """Remove NPC from faction"""
        if npc_name in self.members:
            self.members.remove(npc_name)
            self.update_influence()
    
    def update_influence(self):
        """Calculate faction influence based on members"""
        # Base influence from member count
        base = min(len(self.members) * 10, 70)
        
        # Bonus if faction has high-status members
        # (In future, check member social_status from database)
        self.influence = base
    
    def get_summary(self):
        """Get faction status summary"""
        return {
            'name': self.name,
            'members': self.members,
            'member_count': len(self.members),
            'influence': self.influence,
            'focus': self.focus_category,
            'agenda_items': len(self.agenda),
            'age_days': (time.time() - self.formed_at) / 86400
        }


class FactionManager:
    """Manages faction formation, membership, and dynamics"""
    
    # Faction templates
    FACTION_TEMPLATES = {
        'safety_positive': {
            'name': 'Town Watch Coalition',
            'focus': 'safety',
            'alignment': 'positive',
            'description': 'Residents who feel safe and want to maintain security'
        },
        'safety_negative': {
            'name': 'Concerned Citizens Alliance',
            'focus': 'safety',
            'alignment': 'negative',
            'description': 'Residents demanding better safety and security measures'
        },
        'economy_positive': {
            'name': 'Prosperity League',
            'focus': 'town_economy',
            'alignment': 'positive',
            'description': 'Business owners and optimists about town economy'
        },
        'economy_negative': {
            'name': 'Economic Revivalists',
            'focus': 'town_economy',
            'alignment': 'negative',
            'description': 'Residents concerned about economic decline'
        },
        'infrastructure_positive': {
            'name': 'Infrastructure Advocates',
            'focus': 'infrastructure',
            'alignment': 'positive',
            'description': 'Proud of town facilities and public works'
        },
        'infrastructure_negative': {
            'name': 'Infrastructure Reform Group',
            'focus': 'infrastructure',
            'alignment': 'negative',
            'description': 'Demanding better roads, buildings, and services'
        },
        'leadership_positive': {
            'name': 'Mayoral Support Committee',
            'focus': 'leadership',
            'alignment': 'positive',
            'description': 'Supporters of current town leadership'
        },
        'leadership_negative': {
            'name': 'Reform Coalition',
            'focus': 'leadership',
            'alignment': 'negative',
            'description': 'Critics demanding leadership changes'
        },
        'community_positive': {
            'name': 'Community Builders',
            'focus': 'community',
            'alignment': 'positive',
            'description': 'Focused on strengthening social bonds'
        },
        'community_negative': {
            'name': 'Community Restoration Movement',
            'focus': 'community',
            'alignment': 'negative',
            'description': 'Concerned about weakening community ties'
        }
    }
    
    def __init__(self):
        self.factions = {}  # faction_id -> Faction
        self.npc_memberships = defaultdict(list)  # npc_name -> [faction_ids]
        self.formation_threshold = 2  # Reduced from 3 - only 2 NPCs needed for smaller town
        self.opinion_threshold = 25  # Opinion must be > 25 or < -25
        
    def update_factions(self, npcs):
        """Update faction memberships based on current NPC opinions"""
        
        # Clear existing memberships
        self.npc_memberships.clear()
        for faction in self.factions.values():
            faction.members.clear()
        
        # Group NPCs by their strong opinions
        opinion_groups = defaultdict(list)
        
        for npc in npcs:
            for category, score in npc.town_opinions.items():
                # Strong positive opinion
                if score > self.opinion_threshold:
                    key = f"{category}_positive"
                    opinion_groups[key].append(npc.name)
                
                # Strong negative opinion
                elif score < -self.opinion_threshold:
                    key = f"{category}_negative"
                    opinion_groups[key].append(npc.name)
        
        # Form or update factions
        formed_factions = []
        disbanded_factions = []
        
        for group_key, member_names in opinion_groups.items():
            # Only form faction if enough members
            if len(member_names) >= self.formation_threshold:
                # Create faction if doesn't exist
                if group_key not in self.factions:
                    template = self.FACTION_TEMPLATES.get(group_key)
                    if template:
                        self.factions[group_key] = Faction(
                            name=template['name'],
                            focus_category=template['focus'],
                            alignment=template['alignment'],
                            description=template['description']
                        )
                        formed_factions.append(template['name'])
                
                # Add members to faction
                faction = self.factions[group_key]
                for name in member_names:
                    faction.add_member(name)
                    self.npc_memberships[name].append(group_key)
        
        # Disband factions with too few members
        for faction_id, faction in list(self.factions.items()):
            if len(faction.members) < self.formation_threshold:
                disbanded_factions.append(faction.name)
                faction.active = False
                del self.factions[faction_id]
        
        return {
            'formed': formed_factions,
            'disbanded': disbanded_factions,
            'active_count': len(self.factions)
        }
    
    def get_npc_factions(self, npc_name):
        """Get all factions an NPC belongs to"""
        faction_ids = self.npc_memberships.get(npc_name, [])
        return [self.factions[fid] for fid in faction_ids if fid in self.factions]
    
    def get_dominant_faction(self):
        """Get faction with most influence"""
        if not self.factions:
            return None
        return max(self.factions.values(), key=lambda f: f.influence)
    
    def get_all_factions(self):
        """Get all active factions"""
        return list(self.factions.values())
    
    def detect_faction_conflicts(self):
        """Detect opposing factions (same focus, opposite alignment)"""
        conflicts = []
        
        # Group factions by focus category
        by_focus = defaultdict(list)
        for faction in self.factions.values():
            by_focus[faction.focus_category].append(faction)
        
        # Check for conflicts
        for category, factions in by_focus.items():
            if len(factions) >= 2:
                # Find positive and negative factions
                positive = [f for f in factions if f.alignment == 'positive']
                negative = [f for f in factions if f.alignment == 'negative']
                
                if positive and negative:
                    conflicts.append({
                        'category': category,
                        'positive_faction': positive[0].name,
                        'negative_faction': negative[0].name,
                        'positive_members': len(positive[0].members),
                        'negative_members': len(negative[0].members)
                    })
        
        return conflicts
    
    def get_faction_summary(self):
        """Get summary of all factions for display"""
        summaries = []
        for faction in self.factions.values():
            summaries.append({
                'name': faction.name,
                'members': ', '.join(faction.members[:5]),  # First 5 names
                'total_members': len(faction.members),
                'influence': faction.influence,
                'focus': faction.focus_category.replace('_', ' ').title()
            })
        
        # Sort by influence
        summaries.sort(key=lambda x: x['influence'], reverse=True)
        return summaries


# Integration helper functions
def assign_npc_to_factions(npcs, faction_manager):
    """Convenience function to update all faction memberships"""
    result = faction_manager.update_factions(npcs)
    
    # Generate notifications
    notifications = []
    
    for faction_name in result['formed']:
        notifications.append(f"🏛️ FACTION FORMED: {faction_name}")
    
    for faction_name in result['disbanded']:
        notifications.append(f"💔 FACTION DISBANDED: {faction_name}")
    
    # Check for conflicts
    conflicts = faction_manager.detect_faction_conflicts()
    for conflict in conflicts:
        notifications.append(
            f"⚔️ FACTION CONFLICT: {conflict['positive_faction']} vs {conflict['negative_faction']} "
            f"on {conflict['category'].replace('_', ' ')}"
        )
    
    return notifications


def get_faction_display_data(faction_manager, max_factions=5):
    """Get faction data formatted for UI display"""
    summaries = faction_manager.get_faction_summary()
    
    display_data = []
    for summary in summaries[:max_factions]:
        display_data.append({
            'line1': f"🏛️ {summary['name']} ({summary['total_members']} members)",
            'line2': f"   Focus: {summary['focus']} | Influence: {summary['influence']}"
        })
    
    return display_data


# Example usage
if __name__ == "__main__":
    # Test faction system
    fm = FactionManager()
    
    # Mock NPCs with opinions
    class MockNPC:
        def __init__(self, name, safety, economy):
            self.name = name
            self.town_opinions = {
                'safety': safety,
                'town_economy': economy,
                'infrastructure': 0,
                'leadership': 0,
                'community': 0
            }
    
    test_npcs = [
        MockNPC("Alice", -30, 10),  # Safety concern
        MockNPC("Bob", -35, 5),      # Safety concern
        MockNPC("Carol", -28, 20),   # Safety concern
        MockNPC("Dave", 10, -40),    # Economy concern
        MockNPC("Eve", 15, -35),     # Economy concern
        MockNPC("Frank", 5, -30),    # Economy concern
    ]
    
    # Update factions
    result = fm.update_factions(test_npcs)
    print("Faction Formation Result:", result)
    
    # Get summaries
    for summary in fm.get_faction_summary():
        print(f"\n{summary['name']}:")
        print(f"  Members: {summary['members']}")
        print(f"  Influence: {summary['influence']}")
    
    # Detect conflicts
    conflicts = fm.detect_faction_conflicts()
    print(f"\nConflicts detected: {len(conflicts)}")
    for conflict in conflicts:
        print(f"  {conflict['positive_faction']} vs {conflict['negative_faction']}")
