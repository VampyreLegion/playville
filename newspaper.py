"""
Town Newspaper System for Playville

Generates daily newspapers summarizing:
- Major events
- Faction activity
- Town whispers
- Opinion polls
- Crime reports
- Rumors and gossip
- NPC interviews
- Weather and mood
"""

import time
import random
from datetime import datetime, timedelta

class NewspaperGenerator:
    """Generates daily newspapers for Playville"""
    
    def __init__(self):
        self.newspaper_name = "The Playville Chronicle"
        self.edition_number = 1
        self.last_publish_time = time.time()
        self.publish_interval = 300  # 5 minutes = 1 day in Playville
        self.archive = []
        self.seeded_stories = []  # List of dicts: {'headline': str, 'body': str, 'author': str, 'section': str}
        self.reporter_articles = []  # Articles written by the AI reporter NPC
        
    def seed_story(self, headline, body, author="Editorial", section="events"):
        """Inject a story into the next newspaper edition."""
        self.seeded_stories.append({
            'headline': headline,
            'body': body,
            'author': author,
            'section': section,
            'timestamp': time.time()
        })

    def add_reporter_article(self, article_text, reporter_name="Fletcher Haze"):
        """Add an article written by the AI reporter NPC."""
        self.reporter_articles.append({
            'text': article_text,
            'author': reporter_name,
            'timestamp': time.time()
        })

    def should_publish(self):
        """Check if it's time for a new edition"""
        return time.time() - self.last_publish_time >= self.publish_interval
    
    def generate_newspaper(self, npcs, events, factions, town_whispers, opinion_dist, evolution_log):
        """Generate a complete newspaper edition"""
        
        # Calculate in-game date (Day 1 = launch)
        days_passed = self.edition_number
        game_date = datetime.now() + timedelta(days=days_passed)
        
        newspaper = {
            'edition': self.edition_number,
            'date': game_date.strftime("%B %d, %Y"),
            'day_of_week': game_date.strftime("%A"),
            'sections': {}
        }
        
        # SECTION 1: Headline
        newspaper['sections']['headline'] = self._generate_headline(events, factions, town_whispers)
        
        # SECTION 2: Major Events
        newspaper['sections']['events'] = self._generate_events_section(events)
        
        # SECTION 3: Faction Watch
        newspaper['sections']['factions'] = self._generate_faction_section(factions)
        
        # SECTION 4: Town Opinion Poll
        newspaper['sections']['opinions'] = self._generate_opinion_poll(opinion_dist)
        
        # SECTION 5: Crime & Safety Report
        newspaper['sections']['crime'] = self._generate_crime_report(npcs, events)
        
        # SECTION 6: Rumors & Gossip
        newspaper['sections']['gossip'] = self._generate_gossip_section(npcs)
        
        # SECTION 7: NPC Spotlight Interview
        newspaper['sections']['interview'] = self._generate_npc_interview(npcs)
        
        # SECTION 8: Town Development
        newspaper['sections']['development'] = self._generate_development_section(evolution_log)
        
        # SECTION 9: Weather & Mood
        newspaper['sections']['weather'] = self._generate_weather_mood(npcs)
        
        # SECTION 10: Seeded stories and reporter articles
        if self.seeded_stories or self.reporter_articles:
            special_content = []
            for story in self.seeded_stories:
                special_content.append(f"[{story['author'].upper()}] {story['headline']}")
                special_content.append(f"  {story['body']}")
            for article in self.reporter_articles[-3:]:  # last 3 reporter articles
                special_content.append(f"[BY {article['author'].upper()}] {article['text'][:200]}")
            newspaper['sections']['special'] = special_content
            # Clear seeded stories after publication
            self.seeded_stories = []

        # Update tracking
        self.edition_number += 1
        self.last_publish_time = time.time()
        self.archive.append(newspaper)

        return newspaper
    
    def _generate_headline(self, events, factions, town_whispers):
        """Generate main headline"""
        
        # Priority: Recent crisis event > Major whisper > Faction conflict
        if events and len(events) > 0:
            recent_event = events[-1]
            severity_map = {
                'CRISIS': '💥 CRISIS',
                'MAJOR': '🚨 BREAKING',
                'MODERATE': '⚠️ UPDATE',
                'MINOR': 'ℹ️ NEWS'
            }
            event_summary = recent_event.get_summary()
            severity = severity_map.get(event_summary['severity'], 'NEWS')
            return f"{severity}: {event_summary['title']}"
        
        if town_whispers and len(town_whispers) > 0:
            latest_whisper = town_whispers[0]
            return f"🌆 TOWN CONSENSUS: {latest_whisper.replace('🌆 TOWN WHISPER: ', '')}"
        
        if factions:
            conflicts = factions.detect_faction_conflicts() if hasattr(factions, 'detect_faction_conflicts') else []
            if conflicts:
                conflict = conflicts[0]
                return f"⚔️ FACTION TENSIONS: {conflict['category'].replace('_', ' ').title()} Divides Town"
        
        return "📰 Another Peaceful Day in Playville"
    
    def _generate_events_section(self, events):
        """Generate events summary"""
        if not events or len(events) == 0:
            return {
                'title': 'Recent Events',
                'content': 'A quiet period in Playville. No major incidents to report.'
            }
        
        # Get last 3 events
        recent_events = events[-3:] if len(events) >= 3 else events
        
        articles = []
        for event in recent_events:
            summary = event.get_summary()
            articles.append({
                'severity': summary['emoji'],
                'title': summary['title'],
                'description': summary['description'],
                'category': summary['category'].title()
            })
        
        return {
            'title': 'Recent Events',
            'articles': articles
        }
    
    def _generate_faction_section(self, faction_manager):
        """Generate faction activity report"""
        if not faction_manager or not faction_manager.get_all_factions():
            return {
                'title': 'Faction Watch',
                'content': 'No organized political groups currently active in town.'
            }
        
        factions = faction_manager.get_faction_summary()[:3]  # Top 3 by influence
        conflicts = faction_manager.detect_faction_conflicts()
        
        content = []
        
        for faction in factions:
            content.append({
                'name': faction['name'],
                'members': faction['total_members'],
                'influence': faction['influence'],
                'focus': faction['focus'],
                'status': 'Growing' if faction['influence'] > 40 else 'Active'
            })
        
        return {
            'title': 'Faction Watch',
            'factions': content,
            'conflicts': len(conflicts),
            'conflict_details': conflicts[0] if conflicts else None
        }
    
    def _generate_opinion_poll(self, opinion_dist):
        """Generate town opinion poll results"""
        if not opinion_dist:
            return {
                'title': 'Town Opinion Poll',
                'content': 'Polling data unavailable.'
            }
        
        # Sort by average (most extreme first)
        sorted_opinions = sorted(
            opinion_dist.items(),
            key=lambda x: abs(x[1]['average']),
            reverse=True
        )
        
        poll_results = []
        for category, data in sorted_opinions[:3]:
            poll_results.append({
                'category': category.replace('_', ' ').title(),
                'score': round(data['average'], 1),
                'sentiment': data['sentiment'],
                'trend': 'improving' if data['average'] > 0 else 'declining' if data['average'] < -15 else 'stable'
            })
        
        npc_count = sum(data.get('count', 1) for _, data in sorted_opinions[:1]) if sorted_opinions else 0
        return {
            'title': 'Weekly Opinion Poll',
            'results': poll_results,
            'methodology': f'Poll of {npc_count} residents conducted'
        }
    
    def _generate_crime_report(self, npcs, events):
        """Generate crime and safety report"""
        
        # Count suspicious activities
        suspicious_count = sum(1 for npc in npcs 
                             if any(theme in npc.memory_themes and len(npc.memory_themes[theme]) > 0 
                                   for theme in ['suspicious_activity', 'safety_concern']))
        
        # Check for safety events
        safety_events = [e for e in events if hasattr(e, 'category') and 'safety' in str(e.category).lower()]
        
        if suspicious_count == 0 and len(safety_events) == 0:
            status = "🟢 LOW"
            report = "No significant safety concerns this week. Town remains peaceful."
        elif suspicious_count < 3:
            status = "🟡 MODERATE"
            report = f"Minor security concerns reported. {suspicious_count} residents express safety worries."
        else:
            status = "🔴 ELEVATED"
            report = f"Heightened security concerns. {suspicious_count} residents report suspicious activity."
        
        return {
            'title': 'Crime & Safety Report',
            'status': status,
            'report': report,
            'recent_incidents': len(safety_events)
        }
    
    def _generate_gossip_section(self, npcs):
        """Generate rumors and gossip column"""
        
        # Collect recent gossip from gossipy NPCs
        gossip_npcs = [npc for npc in npcs if 'gossipy' in npc.personality]
        
        rumors = []
        
        if gossip_npcs:
            for npc in gossip_npcs[:2]:  # Top 2 gossips
                if npc.gossip_heard:
                    rumors.append({
                        'source': f"Anonymous (heard near {npc.name})",
                        'rumor': random.choice(npc.gossip_heard)
                    })
        
        # Add some generated rumors based on town state
        if not rumors:
            generic_rumors = [
                "Strange lights seen near the graveyard at midnight",
                "The Whisper was spotted again near the courthouse",
                "Someone claims to have seen a secret meeting",
                "Unusual activity reported at the factory"
            ]
            rumors.append({
                'source': 'Anonymous',
                'rumor': random.choice(generic_rumors)
            })
        
        return {
            'title': 'Rumors & Whispers',
            'disclaimer': 'Unverified reports from around town',
            'rumors': rumors
        }
    
    def _generate_npc_interview(self, npcs):
        """Generate NPC spotlight interview"""
        
        # Pick an interesting NPC (one with strong opinions or active in events)
        interesting_npcs = [
            npc for npc in npcs
            if npc.get_dominant_opinion() or npc.wishes_expressed or npc.current_goal
        ]
        
        if not interesting_npcs:
            interesting_npcs = npcs
        
        interviewee = random.choice(interesting_npcs)
        
        # Generate interview questions/answers
        dominant_op = interviewee.get_dominant_opinion()
        
        qa = []
        
        # Q1: About town mood
        if dominant_op:
            category, score = dominant_op
            feeling = "optimistic" if score > 0 else "concerned"
            qa.append({
                'q': f"How do you feel about {category.replace('_', ' ')} in Playville?",
                'a': f"I'm quite {feeling}. The town's {category.replace('_', ' ')} is {('improving' if score > 0 else 'troubling')}."
            })
        
        # Q2: About wishes
        if interviewee.wishes_expressed:
            latest_wish = interviewee.wishes_expressed[-1]
            qa.append({
                'q': "What would you like to see changed in town?",
                'a': latest_wish['wish']
            })
        
        # Q3: About relationships
        important_rels = interviewee.get_relationship_summary()
        if important_rels:
            qa.append({
                'q': "How are relationships in the community?",
                'a': f"I'm building connections. Some good friendships, though there are {len([r for r in important_rels.values() if r['score'] < 0])} people I'm wary of."
            })
        
        return {
            'title': 'Resident Spotlight',
            'interviewee': {
                'name': interviewee.name,
                'occupation': interviewee.occupation,
                'age': interviewee.age
            },
            'qa': qa if qa else [{'q': 'Any thoughts on Playville?', 'a': 'It\'s home. I love it here.'}]
        }
    
    def _generate_development_section(self, evolution_log):
        """Generate town development news"""
        if not evolution_log or len(evolution_log) == 0:
            return {
                'title': 'Town Development',
                'content': 'No major development projects this week.'
            }
        
        recent_changes = evolution_log[-3:] if len(evolution_log) >= 3 else evolution_log
        
        developments = []
        for change in recent_changes:
            developments.append({
                'type': change['type'].title(),
                'name': change['name'],
                'action': change['action']
            })
        
        return {
            'title': 'Town Development',
            'developments': developments
        }
    
    def _generate_weather_mood(self, npcs):
        """Generate weather and town mood summary"""
        
        # Calculate average emotional state
        emotion_counts = {'calm': 0, 'happy': 0, 'anxious': 0, 'angry': 0}
        for npc in npcs:
            emotion_counts[npc.emotional_state] += 1
        
        dominant_emotion = max(emotion_counts, key=emotion_counts.get)
        
        mood_descriptions = {
            'calm': 'peaceful and content',
            'happy': 'cheerful and optimistic',
            'anxious': 'tense and worried',
            'angry': 'frustrated and irritable'
        }
        
        weather_options = [
            '☀️ Sunny and clear',
            '⛅ Partly cloudy',
            '🌤️ Mostly sunny',
            '🌥️ Overcast',
            '🌧️ Light rain'
        ]
        
        return {
            'title': 'Weather & Town Mood',
            'weather': random.choice(weather_options),
            'mood': mood_descriptions[dominant_emotion],
            'dominant_emotion': dominant_emotion,
            'emotion_breakdown': emotion_counts
        }
    
    def get_latest_newspaper(self):
        """Get most recent newspaper"""
        return self.archive[-1] if self.archive else None
    
    def get_newspaper_archive(self, limit=5):
        """Get recent newspapers"""
        return self.archive[-limit:] if self.archive else []


def format_newspaper_for_display(newspaper):
    """Format newspaper as readable text for UI"""
    if not newspaper:
        return ["No newspaper available yet."]
    
    lines = []
    
    # Header
    lines.append("=" * 70)
    lines.append(f"  {newspaper.get('edition', 1)} | {newspaper.get('day_of_week', '')} | {newspaper.get('date', '')}")
    lines.append("=" * 70)
    lines.append("")
    
    # Headline
    if 'headline' in newspaper['sections']:
        lines.append(f">>> {newspaper['sections']['headline']}")
        lines.append("")
    
    # Events
    if 'events' in newspaper['sections']:
        section = newspaper['sections']['events']
        lines.append(f"--- {section['title']} ---")
        if 'articles' in section:
            for article in section['articles']:
                lines.append(f"{article['severity']} {article['title']}")
                lines.append(f"   {article['description']}")
        else:
            lines.append(section['content'])
        lines.append("")
    
    # Opinion Poll
    if 'opinions' in newspaper['sections']:
        section = newspaper['sections']['opinions']
        lines.append(f"--- {section['title']} ---")
        if 'results' in section:
            for result in section['results']:
                icon = "📈" if result['trend'] == 'improving' else "📉" if result['trend'] == 'declining' else "➡️"
                lines.append(f"{icon} {result['category']}: {result['score']:+.1f} ({result['sentiment']})")
        lines.append("")
    
    # Crime Report
    if 'crime' in newspaper['sections']:
        section = newspaper['sections']['crime']
        lines.append(f"--- {section['title']} ---")
        lines.append(f"Status: {section['status']}")
        lines.append(f"{section['report']}")
        lines.append("")
    
    # Gossip
    if 'gossip' in newspaper['sections']:
        section = newspaper['sections']['gossip']
        lines.append(f"--- {section['title']} ---")
        if 'rumors' in section:
            for rumor in section['rumors']:
                lines.append(f"• {rumor['rumor']}")
        lines.append("")

    # Special Report (seeded stories + reporter articles)
    if 'special' in newspaper['sections']:
        lines.append("")
        lines.append("=== SPECIAL REPORT ===")
        for item in newspaper['sections']['special']:
            lines.append(f"  {item}")
        lines.append("")

    return lines


# Example usage
if __name__ == "__main__":
    ng = NewspaperGenerator()
    
    # Mock data
    class MockNPC:
        def __init__(self):
            self.name = "Test"
            self.personality = ['gossipy']
            self.gossip_heard = ["Strange things happening"]
            self.emotional_state = "calm"
            self.memory_themes = {}
            self.wishes_expressed = []
            self.current_goal = None
            self.occupation = "Tester"
            self.age = 30
        
        def get_dominant_opinion(self):
            return ("safety", -25)
        
        def get_relationship_summary(self):
            return {}
    
    npcs = [MockNPC() for _ in range(11)]
    
    newspaper = ng.generate_newspaper(npcs, [], None, [], {}, [])
    
    print("\n".join(format_newspaper_for_display(newspaper)))
