class HumanPlayer:
    def __init__(self, name, game_state):
        self.name = name
        self.game_state = game_state
        
        # Starting resources as specified
        self.free_land = 500
        self.worked_land = 200
        self.peasants = 2000
        self.soldiers = 200
        self.revenue = 2000  # 1 per peasant
        self.expenses = 600  # 3 per soldier
        self.net_profit = 1400
        
        # Message tracking
        self.messages_sent_this_turn = set()
        self.message_history = []
    
    def get_total_power(self):
        """Calculate total power for relative comparisons"""
        return (self.peasants + self.soldiers * 2) * (self.free_land + self.worked_land) / 1000
    
    def update_economy(self):
        """Update economic calculations"""
        # Peasants grow naturally (10% growth rate, but limited by available land)
        max_peasants = (self.free_land + self.worked_land) * 10
        growth_rate = 0.1 if self.peasants < max_peasants else 0.05
        new_peasants = int(self.peasants * growth_rate)
        
        # Peasants can only grow if there's free land
        if self.free_land > 0:
            self.peasants += new_peasants
        
        # Update worked land (10 peasants per acre)
        needed_worked_land = self.peasants // 10
        if needed_worked_land > self.worked_land:
            # Convert free land to worked land
            land_to_convert = min(needed_worked_land - self.worked_land, self.free_land)
            self.free_land -= land_to_convert
            self.worked_land += land_to_convert
        
        # Update revenue and expenses
        self.revenue = self.peasants  # 1 per peasant
        self.expenses = self.soldiers * 3  # 3 per soldier
        self.net_profit = self.revenue - self.expenses
    
    def can_recruit_soldiers(self, amount):
        """Check if player can recruit specified number of soldiers"""
        return self.peasants >= amount and self.net_profit >= amount * 3
    
    def recruit_soldiers(self, amount):
        """Recruit soldiers from peasants"""
        if self.can_recruit_soldiers(amount):
            self.peasants -= amount
            self.soldiers += amount
            return True
        return False
    
    def dismiss_soldiers(self, amount):
        """Dismiss soldiers back to peasants"""
        if self.soldiers >= amount:
            self.soldiers -= amount
            self.peasants += amount
            return True
        return False
    
    def extort_taxes(self):
        """Extort high taxes - gain money but lose peasants"""
        if self.peasants >= 100:
            self.peasants -= 100
            # Gain immediate money (simplified - in real game this would be more complex)
            return 500
        return 0
    
    def invest(self, amount):
        """Invest money to gain peasants"""
        if self.net_profit >= amount:
            # Convert money to peasants (simplified)
            new_peasants = amount // 2
            self.peasants += new_peasants
            return True
        return False
    
    def attack_target(self, target_name, attack_force):
        """Attack a target entity"""
        target = self.game_state.get_entity_by_name(target_name)
        if target and self.soldiers >= attack_force and attack_force > 0:
            # Queue combat
            self.game_state.combat_queue.append({
                'attacker': self,
                'defender': target,
                'attacker_soldiers': attack_force
            })
            return True
        return False
    
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