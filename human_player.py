from config import *

class HumanPlayer:
    def __init__(self, name, game_state):
        self.name = name
        self.game_state = game_state
        
        # Starting resources from config
        self.land = STARTING_LAND
        self.peasants = STARTING_PEASANTS
        self.soldiers = STARTING_SOLDIERS
        self.revenue = STARTING_PEASANTS * REVENUE_PER_PEASANT
        self.expenses = STARTING_SOLDIERS * EXPENSE_PER_SOLDIER
        self.net_profit = self.revenue - self.expenses
        
        # Message tracking
        self.messages_sent_this_turn = set()
        self.message_history = []
    
    def get_total_power(self):
        """Calculate total power for relative comparisons"""
        return (self.peasants + self.soldiers * 2) * self.land / 1000
    
    def update_economy(self):
        """Update economic calculations"""
        # Peasants grow naturally (growth rate from config, limited by available land)
        max_peasants = self.land * PEASANTS_PER_ACRE
        growth_rate = PEASANT_GROWTH_RATE if self.peasants < max_peasants else PEASANT_GROWTH_RATE_CAPPED
        new_peasants = int(self.peasants * growth_rate)
        
        # Peasants can grow if there's land
        if self.land > 0:
            self.peasants += new_peasants
        
        # Calculate revenue based on peasants per acre efficiency
        peasants_per_acre = self.peasants / self.land if self.land > 0 else 0
        
        # Update revenue and expenses using config values
        self.revenue = int(self.peasants * REVENUE_PER_PEASANT * (peasants_per_acre / REVENUE_EFFICIENCY_SCALE))
        self.expenses = self.soldiers * EXPENSE_PER_SOLDIER
        self.net_profit = self.revenue - self.expenses
    
    def can_recruit_soldiers(self, amount):
        """Check if player can recruit specified number of soldiers"""
        return self.peasants >= amount and self.net_profit >= amount * EXPENSE_PER_SOLDIER
    
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
    
    def send_tribute(self, recipient_name, land_amount, peasant_amount):
        """Send tribute (land or peasants) to another entity"""
        target = self.game_state.get_entity_by_name(recipient_name)
        if not target:
            return False
        
        if land_amount < 0 or peasant_amount < 0:
            return False
        
        if land_amount == 0 and peasant_amount == 0:
            return False
        
        # Check if we have enough resources
        if land_amount > self.land:
            return False
        
        if peasant_amount > self.peasants:
            return False
        
        # Transfer resources
        if land_amount > 0:
            self.land -= land_amount
            target.land += land_amount
        
        if peasant_amount > 0:
            self.peasants -= peasant_amount
            target.peasants += peasant_amount
        
        # Send a message about the tribute
        tribute_message = f"Tribute sent: {land_amount} land, {peasant_amount} peasants"
        self.send_message(recipient_name, tribute_message)
        
        return True
    
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