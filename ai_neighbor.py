#Deprecated in favor of llm_neighbor.py. This is a "dumb" AI.
import random

class AINeighbor:
    def __init__(self, name, game_state, player_id):
        self.name = name
        self.game_state = game_state
        self.player_id = player_id
        
        # Starting resources (same as player)
        self.free_land = 500
        self.worked_land = 200
        self.peasants = 2000
        self.soldiers = 200
        self.revenue = 2000
        self.expenses = 600
        self.net_profit = 1400
        
        # AI personality traits
        self.personality = self.generate_personality()
        
        # Message tracking
        self.messages_sent_this_turn = set()
        self.message_history = []
        
        # AI state
        self.current_goals = []
        self.trust_levels = {}  # Trust in other entities
    
    def generate_personality(self):
        """Generate random personality traits for this AI"""
        traits = {
            'aggression': random.uniform(0.1, 0.9),  # How likely to attack
            'diplomacy': random.uniform(0.1, 0.9),   # How likely to negotiate
            'greed': random.uniform(0.1, 0.9),       # How much they value resources
            'honor': random.uniform(0.1, 0.9),       # How likely to keep promises
            'paranoia': random.uniform(0.1, 0.9),    # How suspicious of others
            'ambition': random.uniform(0.1, 0.9)     # How expansionist
        }
        return traits
    
    def get_total_power(self):
        """Calculate total power for relative comparisons"""
        return (self.peasants + self.soldiers * 2) * (self.free_land + self.worked_land) / 1000
    
    def update_economy(self):
        """Update economic calculations (same as player)"""
        # Peasants grow naturally
        max_peasants = (self.free_land + self.worked_land) * 10
        growth_rate = 0.1 if self.peasants < max_peasants else 0.05
        new_peasants = int(self.peasants * growth_rate)
        
        if self.free_land > 0:
            self.peasants += new_peasants
        
        # Update worked land
        needed_worked_land = self.peasants // 10
        if needed_worked_land > self.worked_land:
            land_to_convert = min(needed_worked_land - self.worked_land, self.free_land)
            self.free_land -= land_to_convert
            self.worked_land += land_to_convert
        
        # Update revenue and expenses
        self.revenue = self.peasants
        self.expenses = self.soldiers * 3
        self.net_profit = self.revenue - self.expenses
    
    def take_turn(self):
        """AI takes its turn - make decisions and take actions"""
        # Analyze current situation
        self.analyze_situation()
        
        # Decide on actions based on personality and situation
        actions = self.decide_actions()
        
        # Execute actions
        self.execute_actions(actions)
        
        # Reset turn tracking
        self.reset_turn()
    
    def analyze_situation(self):
        """Analyze current game situation and update goals"""
        # Get relative power compared to other entities
        all_entities = [self.game_state.player] + self.game_state.neighbors
        other_entities = [e for e in all_entities if e != self]
        
        self.current_goals = []
        
        for entity in other_entities:
            relative_power = self.game_state.get_relative_power(self, entity)
            
            if relative_power in ["Miniscule", "Inferior"]:
                # We're weaker - consider alliance or building up
                if self.personality['diplomacy'] > 0.6:
                    self.current_goals.append(f"ally_with_{entity.name}")
                else:
                    self.current_goals.append("build_military")
            
            elif relative_power in ["Greater", "Overwhelming"]:
                # We're stronger - consider expansion
                if self.personality['aggression'] > 0.6:
                    self.current_goals.append(f"attack_{entity.name}")
                else:
                    self.current_goals.append("consolidate_power")
    
    def decide_actions(self):
        """Decide what actions to take this turn"""
        actions = []
        
        # Economic actions
        if self.net_profit < 0 and self.personality['greed'] > 0.5:
            actions.append("extort_taxes")
        
        if self.peasants < 1500 and self.net_profit > 1000:
            actions.append("invest")
        
        # Military actions
        if "build_military" in self.current_goals and self.can_recruit_soldiers(50):
            actions.append("recruit_soldiers")
        
        # Diplomatic actions
        if random.random() < self.personality['diplomacy']:
            actions.append("send_message")
        
        # Aggressive actions
        for goal in self.current_goals:
            if goal.startswith("attack_") and random.random() < self.personality['aggression']:
                target = goal.replace("attack_", "")
                actions.append(f"attack_{target}")
        
        return actions
    
    def execute_actions(self, actions):
        """Execute the decided actions"""
        for action in actions:
            if action == "extort_taxes":
                self.extort_taxes()
            elif action == "invest":
                self.invest(500)
            elif action == "recruit_soldiers":
                self.recruit_soldiers(50)
            elif action == "send_message":
                self.send_random_message()
            elif action.startswith("attack_"):
                target_name = action.replace("attack_", "")
                self.attack_target(target_name)
    
    def can_recruit_soldiers(self, amount):
        """Check if AI can recruit specified number of soldiers"""
        return self.peasants >= amount and self.net_profit >= amount * 3
    
    def recruit_soldiers(self, amount):
        """Recruit soldiers from peasants"""
        if self.can_recruit_soldiers(amount):
            self.peasants -= amount
            self.soldiers += amount
            print(f"{self.name} recruits {amount} soldiers.")
            return True
        return False
    
    def extort_taxes(self):
        """Extort high taxes"""
        if self.peasants >= 100:
            self.peasants -= 100
            print(f"{self.name} extorts high taxes, losing 100 peasants.")
            return 500
        return 0
    
    def invest(self, amount):
        """Invest money to gain peasants"""
        if self.net_profit >= amount:
            new_peasants = amount // 2
            self.peasants += new_peasants
            print(f"{self.name} invests {amount}, gaining {new_peasants} peasants.")
            return True
        return False
    
    def send_random_message(self):
        """Send a random diplomatic message"""
        all_entities = [self.game_state.player] + self.game_state.neighbors
        other_entities = [e for e in all_entities if e != self]
        
        if other_entities and random.random() < 0.3:  # 30% chance to send message
            target = random.choice(other_entities)
            message_templates = [
                f"Greetings from {self.name}. We seek peaceful relations.",
                f"{self.name} proposes a trade agreement.",
                f"We of {self.name} offer tribute in exchange for protection.",
                f"{self.name} demands tribute from your lands!",
                f"Let us form an alliance, {target.name}."
            ]
            message = random.choice(message_templates)
            self.send_message(target.name, message)
    
    def attack_target(self, target_name):
        """Attack a target entity"""
        target = self.game_state.get_entity_by_name(target_name)
        if target and self.soldiers > 50:
            # Use 50-80% of soldiers for attack
            attack_force = int(self.soldiers * random.uniform(0.5, 0.8))
            
            # Queue combat
            self.game_state.combat_queue.append({
                'attacker': self,
                'defender': target,
                'attacker_soldiers': attack_force
            })
            
            print(f"{self.name} attacks {target_name} with {attack_force} soldiers!")
    
    def send_message(self, recipient_name, content):
        """Send a message to another entity"""
        if recipient_name not in self.messages_sent_this_turn:
            self.game_state.send_message(self, recipient_name, content)
            self.messages_sent_this_turn.add(recipient_name)
            self.message_history.append({
                'to': recipient_name,
                'content': content,
                'turn': self.game_state.turn
            })
            return True
        return False
    
    def receive_message(self, message_data):
        """Receive a message from another entity"""
        self.message_history.append({
            'from': message_data['sender'],
            'content': message_data['content'],
            'turn': message_data['turn']
        })
    
    def reset_turn(self):
        """Reset turn-specific tracking"""
        self.messages_sent_this_turn.clear()