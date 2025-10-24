import random
from typing import List, Dict, Any
from config import *

class GameState:
    def __init__(self):
        self.turn = 0
        self.player = None
        self.neighbors = []
        self.message_queue = []
        self.diplomatic_relations = {}  # Store alliances, tribute agreements, etc.
        self.combat_queue = []
        self.combat_results = []  # Store combat results to display later
        
    def initialize_game(self, player, neighbors):
        """Initialize the game with starting resources"""
        self.player = player
        self.neighbors = neighbors
        
        # Initialize diplomatic relations
        all_entities = [player] + neighbors
        for i, entity1 in enumerate(all_entities):
            for j, entity2 in enumerate(all_entities):
                if i != j:
                    key = (entity1.name, entity2.name)
                    self.diplomatic_relations[key] = {
                        'trust': 50,  # 0-100 scale
                        'alliance': False,
                        'tribute': None,  # None, 'paying', 'receiving'
                        'non_aggression': False
                    }
    
    def get_entity_by_name(self, name):
        """Get entity (player or neighbor) by name"""
        if self.player.name == name:
            return self.player
        for neighbor in self.neighbors:
            if neighbor.name == name:
                return neighbor
        return None
    
    def get_relative_power(self, entity1, entity2):
        """Calculate relative power between two entities"""
        power1 = entity1.get_total_power()
        power2 = entity2.get_total_power()
        
        ratio = power1 / power2 if power2 > 0 else float('inf')
        
        if ratio < 0.3:
            return "Miniscule"
        elif ratio < 0.6:
            return "Inferior"
        elif ratio < 1.4:
            return "Equal"
        elif ratio < 2.0:
            return "Greater"
        else:
            return "Overwhelming"
    
    def resolve_combat(self):
        """Resolve all queued combat actions"""
        for combat_data in self.combat_queue:
            attacker = combat_data['attacker']
            defender = combat_data['defender']
            attacker_soldiers = combat_data['attacker_soldiers']
            
            # Simple combat resolution
            defender_soldiers = defender.soldiers
            
            # Attacker needs advantage to win
            attack_power = attacker_soldiers * ATTACKER_PENALTY
            defense_power = defender_soldiers * DEFENDER_BONUS
            
            total_power = attack_power + defense_power
            attacker_win_chance = attack_power / total_power if total_power > 0 else 0.5
            
            if random.random() < attacker_win_chance:
                # Attacker wins
                self.handle_attacker_victory(attacker, defender, attacker_soldiers, defender_soldiers)
            else:
                # Defender wins
                self.handle_defender_victory(attacker, defender, attacker_soldiers, defender_soldiers)
        self.combat_queue.clear()
    
    def process_combat(self, combat_data):
        """Process a single combat between two entities"""

    def handle_attacker_victory(self, attacker, defender, attacker_soldiers, defender_soldiers):
        """Handle attacker victory"""
        # Check if defender has land and peasants to gain
        defender_land = defender.land
        defender_peasants = defender.peasants
        
        # Only gain resources if defender has them
        land_gained = 0
        peasants_gained = 0
        
        if defender_land > 0:
            land_gained = min(50, defender_land // 4)
            # Transfer land
            defender.land = max(0, defender.land - land_gained)
            attacker.land += land_gained
        
        if defender_peasants > 0:
            peasants_gained = min(200, defender_peasants // 4)
            # Transfer peasants
            defender.peasants = max(0, defender.peasants - peasants_gained)
            attacker.peasants += peasants_gained
        
        # Both sides lose soldiers
        attacker_losses = attacker_soldiers // 3
        defender_losses = defender_soldiers // 2
        
        attacker.soldiers = max(0, attacker.soldiers - attacker_losses)
        defender.soldiers = max(0, defender.soldiers - defender_losses)
        
        # Store combat result with more detail
        if land_gained > 0 and peasants_gained > 0:
            result = f"{attacker.name} defeats {defender.name}! Gains {land_gained} acres and {peasants_gained} peasants."
        elif land_gained > 0:
            result = f"{attacker.name} defeats {defender.name}! Gains {land_gained} acres (defender had no peasants)."
        elif peasants_gained > 0:
            result = f"{attacker.name} defeats {defender.name}! Gains {peasants_gained} peasants (defender had no land)."
        else:
            result = f"{attacker.name} defeats {defender.name}! No resources gained (defender had no land or peasants)."
        
        self.combat_results.append(result)
        
        # Track specific results for player
        if attacker == self.player:
            # Player's outgoing attack
            if hasattr(self, 'renderer') and self.renderer:
                if land_gained > 0 and peasants_gained > 0:
                    self.renderer.add_player_attack_result(f"Victory! You gained {land_gained} acres and {peasants_gained} peasants from {defender.name}.")
                elif land_gained > 0:
                    self.renderer.add_player_attack_result(f"Victory! You gained {land_gained} acres from {defender.name} (they had no peasants).")
                elif peasants_gained > 0:
                    self.renderer.add_player_attack_result(f"Victory! You gained {peasants_gained} peasants from {defender.name} (they had no land).")
                else:
                    self.renderer.add_player_attack_result(f"Victory! No resources gained from {defender.name} (they had no land or peasants).")
        elif defender == self.player:
            # Attack against player
            if hasattr(self, 'renderer') and self.renderer:
                if land_gained > 0 and peasants_gained > 0:
                    self.renderer.add_incoming_attack_result(f"Defeated by {attacker.name}! Lost {land_gained} acres and {peasants_gained} peasants.")
                elif land_gained > 0:
                    self.renderer.add_incoming_attack_result(f"Defeated by {attacker.name}! Lost {land_gained} acres (you had no peasants).")
                elif peasants_gained > 0:
                    self.renderer.add_incoming_attack_result(f"Defeated by {attacker.name}! Lost {peasants_gained} peasants (you had no land).")
                else:
                    self.renderer.add_incoming_attack_result(f"Defeated by {attacker.name}! No resources lost (you had no land or peasants).")
    
    def handle_defender_victory(self, attacker, defender, attacker_soldiers, defender_soldiers):
        """Handle defender victory"""
        # Defender gains nothing but attacker loses heavily
        attacker_losses = attacker_soldiers // 2
        defender_losses = defender_soldiers // 4
        
        attacker.soldiers = max(0, attacker.soldiers - attacker_losses)
        defender.soldiers = max(0, defender.soldiers - defender_losses)
        
        # Store combat result with more detail
        result = f"{defender.name} repels {attacker.name}'s attack! {attacker.name} loses {attacker_losses} soldiers."
        self.combat_results.append(result)
        
        # Track specific results for player
        if attacker == self.player:
            # Player's outgoing attack failed
            if hasattr(self, 'renderer') and self.renderer:
                self.renderer.add_player_attack_result(f"Attack failed! {defender.name} repelled your attack. You lost {attacker_losses} soldiers.")
        elif defender == self.player:
            # Player successfully defended
            if hasattr(self, 'renderer') and self.renderer:
                self.renderer.add_incoming_attack_result(f"Successfully defended against {attacker.name}! They lost {attacker_losses} soldiers.")
    
    def get_combat_results(self):
        """Get and clear combat results"""
        results = self.combat_results.copy()
        self.combat_results.clear()
        return results
    
    def process_diplomacy(self):
        """Process diplomatic actions and agreements"""
        # This will handle alliance effects, tribute payments, etc.
        pass
    
    def update_economy(self):
        """Update all entities' economies"""
        all_entities = [self.player] + self.neighbors
        
        for entity in all_entities:
            entity.update_economy()
    
    def send_message(self, sender, recipient_name, content):
        """Deliver a message immediately to the recipient"""
        recipient = self.get_entity_by_name(recipient_name)
        if recipient:
            message_data = {
                'sender': sender.name,
                'recipient': recipient_name,
                'content': content,
                'turn': self.turn
            }
            recipient.receive_message(message_data)
    
    def is_game_over(self):
        """Check if game should end"""
        # Game ends if player has no subjects or no land
        if self.player.peasants <= 0 or self.player.land <= 0:
            return True
        
        # Game ends if player controls all land
        total_land = sum(entity.land for entity in [self.player] + self.neighbors)
        player_land = self.player.land
        
        if player_land >= total_land * 0.9:  # 90% control
            return True
            
        return False
    
    def check_victory_conditions(self):
        """Check for victory conditions"""
        return self.is_game_over()