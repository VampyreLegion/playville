"""
Social Network Visualization for Playville

Creates an interactive graph showing:
- Friendships (green edges)
- Rivalries (red edges)
- Trust networks (thick edges)
- Faction membership (node colors)
- Gossip chains (dashed edges)
- Relationship strength (edge thickness)
"""

import pygame
import math
import random

class SocialNetworkGraph:
    """Visualize NPC social relationships as a force-directed graph"""
    
    def __init__(self, width=800, height=600):
        self.width = width
        self.height = height
        self.nodes = {}  # npc_name -> {pos, velocity, data}
        self.edges = []  # {source, target, type, strength, color}
        
        # Physics parameters for force-directed layout
        self.repulsion_force = 5000
        self.attraction_force = 0.01
        self.damping = 0.85
        self.center_force = 0.001
        
        # Visual parameters
        self.node_radius = 25
        self.selected_node = None
        self.hovered_node = None
        
    def build_graph(self, npcs, faction_manager=None):
        """Build graph from NPC data"""
        self.nodes.clear()
        self.edges.clear()
        
        # Create nodes with initial random positions
        for i, npc in enumerate(npcs):
            angle = (i / len(npcs)) * 2 * math.pi
            radius = min(self.width, self.height) * 0.3
            
            self.nodes[npc.name] = {
                'pos': [
                    self.width/2 + math.cos(angle) * radius,
                    self.height/2 + math.sin(angle) * radius
                ],
                'velocity': [0.0, 0.0],
                'npc': npc,
                'faction': None,
                'color': (100, 100, 100)
            }
        
        # Assign faction colors
        if faction_manager:
            faction_colors = [
                (255, 100, 100),  # Red
                (100, 100, 255),  # Blue
                (100, 255, 100),  # Green
                (255, 255, 100),  # Yellow
                (255, 100, 255),  # Magenta
                (100, 255, 255),  # Cyan
            ]
            
            for faction_idx, faction in enumerate(faction_manager.get_all_factions()):
                color = faction_colors[faction_idx % len(faction_colors)]
                for member_name in faction.members:
                    if member_name in self.nodes:
                        self.nodes[member_name]['faction'] = faction.name
                        self.nodes[member_name]['color'] = color
        
        # Create edges from relationships
        for npc in npcs:
            for target_name, rel_data in npc.relationships.items():
                if target_name not in self.nodes:
                    continue
                
                score = rel_data['score']
                sentiment = rel_data['sentiment']
                
                # Only show meaningful relationships
                if abs(score) > 15:
                    # Determine edge type and color
                    if score > 30:
                        edge_type = 'friendship'
                        color = (100, 255, 100)  # Green
                    elif score < -30:
                        edge_type = 'rivalry'
                        color = (255, 100, 100)  # Red
                    elif score > 0:
                        edge_type = 'positive'
                        color = (150, 200, 150)  # Light green
                    else:
                        edge_type = 'negative'
                        color = (200, 150, 150)  # Light red
                    
                    # Check if trust relationship
                    is_trust = target_name in npc.trust_network
                    
                    # Determine thickness based on strength
                    thickness = max(1, min(5, abs(score) // 20))
                    
                    self.edges.append({
                        'source': npc.name,
                        'target': target_name,
                        'type': edge_type,
                        'strength': abs(score),
                        'color': color,
                        'thickness': thickness,
                        'is_trust': is_trust,
                        'dashed': False
                    })
        
        # Add gossip chains (dashed lines)
        for npc in npcs:
            if 'gossipy' in npc.personality:
                # Find who they share gossip with (trusted gossipy NPCs)
                for target_name in npc.trust_network:
                    if target_name in self.nodes:
                        target_npc = self.nodes[target_name]['npc']
                        if 'gossipy' in target_npc.personality:
                            self.edges.append({
                                'source': npc.name,
                                'target': target_name,
                                'type': 'gossip',
                                'strength': 50,
                                'color': (255, 200, 100),  # Gold
                                'thickness': 2,
                                'is_trust': True,
                                'dashed': True
                            })
    
    def update_physics(self, iterations=1):
        """Update node positions using force-directed layout"""
        for _ in range(iterations):
            # Calculate forces
            for name1, node1 in self.nodes.items():
                force_x, force_y = 0.0, 0.0
                
                # Repulsion from other nodes
                for name2, node2 in self.nodes.items():
                    if name1 == name2:
                        continue
                    
                    dx = node1['pos'][0] - node2['pos'][0]
                    dy = node1['pos'][1] - node2['pos'][1]
                    dist = math.sqrt(dx*dx + dy*dy) + 0.1  # Avoid division by zero
                    
                    # Repulsion force (inverse square)
                    repulsion = self.repulsion_force / (dist * dist)
                    force_x += (dx / dist) * repulsion
                    force_y += (dy / dist) * repulsion
                
                # Attraction from connected nodes
                for edge in self.edges:
                    if edge['source'] == name1:
                        target_node = self.nodes[edge['target']]
                        dx = target_node['pos'][0] - node1['pos'][0]
                        dy = target_node['pos'][1] - node1['pos'][1]
                        dist = math.sqrt(dx*dx + dy*dy)
                        
                        # Attraction force (spring)
                        attraction = dist * self.attraction_force * edge['strength'] / 100
                        force_x += dx * attraction
                        force_y += dy * attraction
                
                # Center force (pull towards center)
                dx = (self.width/2) - node1['pos'][0]
                dy = (self.height/2) - node1['pos'][1]
                force_x += dx * self.center_force
                force_y += dy * self.center_force
                
                # Update velocity and position
                node1['velocity'][0] = (node1['velocity'][0] + force_x) * self.damping
                node1['velocity'][1] = (node1['velocity'][1] + force_y) * self.damping
                
                node1['pos'][0] += node1['velocity'][0]
                node1['pos'][1] += node1['velocity'][1]
                
                # Keep within bounds
                margin = self.node_radius
                node1['pos'][0] = max(margin, min(self.width - margin, node1['pos'][0]))
                node1['pos'][1] = max(margin, min(self.height - margin, node1['pos'][1]))
    
    def draw(self, surface, font):
        """Draw the social network graph"""
        # Draw edges first (behind nodes)
        for edge in self.edges:
            source_pos = self.nodes[edge['source']]['pos']
            target_pos = self.nodes[edge['target']]['pos']
            
            if edge['dashed']:
                # Draw dashed line for gossip chains
                self._draw_dashed_line(surface, edge['color'], source_pos, target_pos, edge['thickness'])
            else:
                # Draw solid line
                if edge['is_trust']:
                    # Double line for trust
                    pygame.draw.line(surface, edge['color'], source_pos, target_pos, edge['thickness'] + 2)
                else:
                    pygame.draw.line(surface, edge['color'], source_pos, target_pos, edge['thickness'])
        
        # Draw nodes
        for name, node in self.nodes.items():
            pos = node['pos']
            color = node['color']
            
            # Highlight if hovered or selected
            if name == self.selected_node:
                pygame.draw.circle(surface, (255, 255, 0), (int(pos[0]), int(pos[1])), self.node_radius + 5, 3)
            elif name == self.hovered_node:
                pygame.draw.circle(surface, (255, 255, 255), (int(pos[0]), int(pos[1])), self.node_radius + 3, 2)
            
            # Draw node circle
            pygame.draw.circle(surface, color, (int(pos[0]), int(pos[1])), self.node_radius)
            pygame.draw.circle(surface, (255, 255, 255), (int(pos[0]), int(pos[1])), self.node_radius, 2)
            
            # Draw name label
            text = font.render(name[:8], True, (255, 255, 255))
            text_rect = text.get_rect(center=(int(pos[0]), int(pos[1])))
            surface.blit(text, text_rect)
        
        # Draw legend
        self._draw_legend(surface, font)
        
        # Draw selected node info
        if self.selected_node:
            self._draw_node_info(surface, font, self.selected_node)
    
    def _draw_dashed_line(self, surface, color, start, end, width):
        """Draw a dashed line"""
        dx = end[0] - start[0]
        dy = end[1] - start[1]
        dist = math.sqrt(dx*dx + dy*dy)
        
        if dist < 1:
            return
        
        dash_length = 10
        gap_length = 5
        num_dashes = int(dist / (dash_length + gap_length))
        
        for i in range(num_dashes):
            t1 = i * (dash_length + gap_length) / dist
            t2 = (i * (dash_length + gap_length) + dash_length) / dist
            
            x1 = start[0] + dx * t1
            y1 = start[1] + dy * t1
            x2 = start[0] + dx * t2
            y2 = start[1] + dy * t2
            
            pygame.draw.line(surface, color, (int(x1), int(y1)), (int(x2), int(y2)), width)
    
    def _draw_legend(self, surface, font):
        """Draw graph legend"""
        legend_x = 10
        legend_y = 10
        
        legends = [
            ("Green line: Friendship", (100, 255, 100)),
            ("Red line: Rivalry", (255, 100, 100)),
            ("Gold dash: Gossip chain", (255, 200, 100)),
            ("Thick line: Trust", (255, 255, 255)),
        ]
        
        for i, (text_str, color) in enumerate(legends):
            # Draw line sample
            y = legend_y + i * 20
            pygame.draw.line(surface, color, (legend_x, y + 5), (legend_x + 30, y + 5), 3)
            
            # Draw text
            text = font.render(text_str, True, (255, 255, 255))
            surface.blit(text, (legend_x + 40, y))
    
    def _draw_node_info(self, surface, font, node_name):
        """Draw detailed info about selected node"""
        if node_name not in self.nodes:
            return
        
        node = self.nodes[node_name]
        npc = node['npc']
        
        info_x = self.width - 250
        info_y = 10
        info_width = 240
        info_height = 200
        
        # Background
        pygame.draw.rect(surface, (40, 40, 50), (info_x, info_y, info_width, info_height))
        pygame.draw.rect(surface, (200, 200, 200), (info_x, info_y, info_width, info_height), 2)
        
        # Name
        text = font.render(npc.name, True, (255, 255, 100))
        surface.blit(text, (info_x + 10, info_y + 10))
        
        # Occupation
        text = font.render(f"{npc.occupation}, {npc.age}", True, (200, 200, 200))
        surface.blit(text, (info_x + 10, info_y + 30))
        
        # Faction
        if node['faction']:
            text = font.render(f"Faction: {node['faction'][:15]}", True, node['color'])
            surface.blit(text, (info_x + 10, info_y + 50))
        
        # Relationship counts
        rels = npc.get_relationship_summary()
        friends = len([r for r in rels.values() if r['score'] > 30])
        rivals = len([r for r in rels.values() if r['score'] < -30])
        
        text = font.render(f"Friends: {friends}", True, (100, 255, 100))
        surface.blit(text, (info_x + 10, info_y + 70))
        
        text = font.render(f"Rivals: {rivals}", True, (255, 100, 100))
        surface.blit(text, (info_x + 10, info_y + 90))
        
        # Trust network
        trusted = len([name for name, status in npc.trust_network.items() if status == 'trusted'])
        text = font.render(f"Trusted: {trusted}", True, (200, 200, 255))
        surface.blit(text, (info_x + 10, info_y + 110))
        
        # Emotional state
        emotion_emoji = {"calm": "😐", "happy": "😊", "anxious": "😰", "angry": "😠"}
        emoji = emotion_emoji.get(npc.emotional_state, "")
        text = font.render(f"Mood: {emoji} {npc.emotional_state}", True, (255, 255, 255))
        surface.blit(text, (info_x + 10, info_y + 130))
    
    def handle_click(self, pos):
        """Handle mouse click on graph"""
        for name, node in self.nodes.items():
            node_pos = node['pos']
            dist = math.sqrt((pos[0] - node_pos[0])**2 + (pos[1] - node_pos[1])**2)
            
            if dist <= self.node_radius:
                self.selected_node = name
                return name
        
        self.selected_node = None
        return None
    
    def handle_hover(self, pos):
        """Handle mouse hover on graph"""
        for name, node in self.nodes.items():
            node_pos = node['pos']
            dist = math.sqrt((pos[0] - node_pos[0])**2 + (pos[1] - node_pos[1])**2)
            
            if dist <= self.node_radius:
                self.hovered_node = name
                return name
        
        self.hovered_node = None
        return None
    
    def get_network_stats(self):
        """Get statistics about the social network"""
        total_edges = len(self.edges)
        friendships = len([e for e in self.edges if e['type'] == 'friendship'])
        rivalries = len([e for e in self.edges if e['type'] == 'rivalry'])
        gossip_chains = len([e for e in self.edges if e['type'] == 'gossip'])
        
        # Calculate network density
        max_possible_edges = len(self.nodes) * (len(self.nodes) - 1) / 2
        density = total_edges / max_possible_edges if max_possible_edges > 0 else 0
        
        return {
            'total_relationships': total_edges,
            'friendships': friendships,
            'rivalries': rivalries,
            'gossip_chains': gossip_chains,
            'network_density': round(density * 100, 1),
            'avg_connections': round(total_edges / len(self.nodes), 1) if self.nodes else 0
        }


# Example standalone viewer (commented out - use main.py integration instead)
# if __name__ == "__main__":
#     import pygame
#     pygame.init()
#     screen = pygame.display.set_mode((1000, 700))
#     clock = pygame.time.Clock()
#     font = pygame.font.SysFont("Arial", 12)
#     # ... (mock/example code removed; see main.py for real integration)
