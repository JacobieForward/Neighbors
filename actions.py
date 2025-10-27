from config import *

class ActionHandler:
    def __init__(self, game_state):
        self.game_state = game_state
        self.renderer = None  # Will be set by main game loop
    
    def set_renderer(self, renderer):
        """Set the renderer reference"""
        self.renderer = renderer
    
    def handle_player_actions(self, player):
        """Handle player input and actions"""
        while True:
            # Display game state with last action result
            self.renderer.display_game_state(self.game_state, player, show_action_result=True)
            self.renderer.display_action_menu()
            
            try:
                choice = input("\nChoose an action (1-9): ").strip()
                
                if choice == "1":
                    self.handle_send_message(player)
                elif choice == "2":
                    self.handle_recruit_soldiers(player)
                elif choice == "3":
                    self.handle_dismiss_soldiers(player)
                elif choice == "4":
                    self.handle_extort_taxes(player)
                elif choice == "5":
                    self.handle_invest(player)
                elif choice == "6":
                    self.handle_attack(player)
                elif choice == "7":
                    self.handle_send_diplomat(player)
                elif choice == "8":
                    self.handle_send_tribute(player)
                elif choice == "9":
                    break  # End turn
                elif choice == "10":
                    self.display_detailed_status(player)
                else:
                    print("Invalid choice. Please try again.")
                    
            except KeyboardInterrupt:
                print("\nGame interrupted.")
                exit()
            except Exception as e:
                print(f"Error: {e}")
    
    def handle_send_message(self, player):
        """Handle sending a message"""
        print("\nAvailable recipients:")
        for i, neighbor in enumerate(self.game_state.neighbors, 1):
            print(f"{i}. {neighbor.name}")
        
        try:
            choice = int(input("Choose recipient (1-3): ")) - 1
            if 0 <= choice < len(self.game_state.neighbors):
                recipient = self.game_state.neighbors[choice]
                if recipient.name not in player.messages_sent_this_turn:
                    message = input("Enter your message: ")
                    if player.send_message(recipient.name, message):
                        result = f"Message sent to {recipient.name}!"
                        self.renderer.set_last_action_result(result, self.game_state.turn)
                    else:
                        result = "Failed to send message."
                        self.renderer.set_last_action_result(result, self.game_state.turn)
                else:
                    result = f"You've already sent a message to {recipient.name} this turn."
                    self.renderer.set_last_action_result(result, self.game_state.turn)
            else:
                result = "Invalid choice."
                self.renderer.set_last_action_result(result, self.game_state.turn)
        except ValueError:
            result = "Please enter a valid number."
            self.renderer.set_last_action_result(result, self.game_state.turn)
    
    def handle_recruit_soldiers(self, player):
        """Handle recruiting soldiers"""
        try:
            amount = int(input("How many soldiers to recruit? "))
            if player.recruit_soldiers(amount):
                result = f"Recruited {amount} soldiers!"
                self.renderer.set_last_action_result(result, self.game_state.turn)
            else:
                result = "Cannot recruit that many soldiers. Check your peasants and finances."
                self.renderer.set_last_action_result(result, self.game_state.turn)
        except ValueError:
            result = "Please enter a valid number."
            self.renderer.set_last_action_result(result, self.game_state.turn)
    
    def handle_dismiss_soldiers(self, player):
        """Handle dismissing soldiers"""
        try:
            amount = int(input("How many soldiers to dismiss? "))
            if player.dismiss_soldiers(amount):
                result = f"Dismissed {amount} soldiers!"
                self.renderer.set_last_action_result(result, self.game_state.turn)
            else:
                result = "Cannot dismiss that many soldiers."
                self.renderer.set_last_action_result(result, self.game_state.turn)
        except ValueError:
            result = "Please enter a valid number."
            self.renderer.set_last_action_result(result, self.game_state.turn)
    
    def handle_extort_taxes(self, player):
        """Handle extorting taxes"""
        if player.peasants >= 100:
            money_gained = player.extort_taxes()
            result = f"Extorted high taxes! Gained {money_gained} but lost 100 peasants."
            self.renderer.set_last_action_result(result, self.game_state.turn)
        else:
            result = "Not enough peasants to extort taxes."
            self.renderer.set_last_action_result(result, self.game_state.turn)
    
    def handle_invest(self, player):
        """Handle investing"""
        try:
            amount = int(input("How much to invest? "))
            if player.invest(amount):
                result = f"Invested {amount}!"
                self.renderer.set_last_action_result(result, self.game_state.turn)
            else:
                result = "Cannot invest that much. Check your finances."
                self.renderer.set_last_action_result(result, self.game_state.turn)
        except ValueError:
            result = "Please enter a valid number."
            self.renderer.set_last_action_result(result, self.game_state.turn)
    
    def handle_attack(self, player):
        """Handle attacking a neighbor"""
        if player.soldiers < MIN_ATTACK_FORCE:
            result = f"You need at least {MIN_ATTACK_FORCE} soldiers to launch an attack!"
            self.renderer.set_last_action_result(result, self.game_state.turn)
            return
        
        print("\nAvailable targets:")
        for i, neighbor in enumerate(self.game_state.neighbors, 1):
            relative_power = self.game_state.get_relative_power(player, neighbor)
            print(f"{i}. {neighbor.name} ({relative_power} power)")
        
        try:
            choice = int(input("Choose target (1-3): ")) - 1
            if 0 <= choice < len(self.game_state.neighbors):
                target = self.game_state.neighbors[choice]
                
                print(f"\nYou have {player.soldiers} soldiers available.")
                print(f"{target.name} has {target.soldiers} soldiers.")
                
                max_attack = min(player.soldiers, int(player.soldiers * 0.8))  # Max 80% of army
                min_attack = MIN_ATTACK_FORCE
                
                attack_force = int(input(f"How many soldiers to attack with? ({min_attack}-{max_attack}): "))
                
                if min_attack <= attack_force <= max_attack:
                    if player.attack_target(target.name, attack_force):
                        # Queue the attack to be resolved with others
                        result = f"Attack queued! You will attack {target.name} with {attack_force} soldiers at the end of the turn."
                        self.renderer.set_last_action_result(result, self.game_state.turn)
                    else:
                        # Check if it's because they already attacked this turn
                        if target.name in player.attacks_sent_this_turn:
                            result = f"You have already attacked {target.name} this turn. You can only attack each player once per turn."
                        else:
                            result = "Failed to launch attack."
                        self.renderer.set_last_action_result(result, self.game_state.turn)
                else:
                    result = f"Attack force must be between {min_attack} and {max_attack}."
                    self.renderer.set_last_action_result(result, self.game_state.turn)
            else:
                result = "Invalid choice."
                self.renderer.set_last_action_result(result, self.game_state.turn)
        except ValueError:
            result = "Please enter a valid number."
            self.renderer.set_last_action_result(result, self.game_state.turn)
    
    
    def handle_send_diplomat(self, player):
        """Handle sending a diplomat (simplified for now)"""
        result = "Diplomatic system not yet implemented. Use 'Send Message' for now to communicate with neighbors."
        self.renderer.set_last_action_result(result, self.game_state.turn)
    
    def handle_send_tribute(self, player):
        """Handle sending tribute to a neighbor"""
        print("\nAvailable recipients:")
        for i, neighbor in enumerate(self.game_state.neighbors, 1):
            print(f"{i}. {neighbor.name}")
        
        try:
            choice = int(input("Choose recipient (1-3): ")) - 1
            if 0 <= choice < len(self.game_state.neighbors):
                recipient = self.game_state.neighbors[choice]
                
                print(f"\nYour resources: {player.land} land, {player.peasants} peasants")
                print(f"{recipient.name}'s resources: {recipient.land} land, {recipient.peasants} peasants")
                
                # Get land amount
                land_amount = int(input(f"How much land to send? (0-{player.land}): "))
                if land_amount < 0 or land_amount > player.land:
                    result = "Invalid land amount."
                    self.renderer.set_last_action_result(result, self.game_state.turn)
                    return
                
                # Get peasant amount
                peasant_amount = int(input(f"How many peasants to send? (0-{player.peasants}): "))
                if peasant_amount < 0 or peasant_amount > player.peasants:
                    result = "Invalid peasant amount."
                    self.renderer.set_last_action_result(result, self.game_state.turn)
                    return
                
                # Check if at least something is being sent
                if land_amount == 0 and peasant_amount == 0:
                    result = "Must send at least some land or peasants."
                    self.renderer.set_last_action_result(result, self.game_state.turn)
                    return
                
                # Send tribute
                if player.send_tribute(recipient.name, land_amount, peasant_amount):
                    result = f"Tribute sent to {recipient.name}: {land_amount} land, {peasant_amount} peasants"
                    self.renderer.set_last_action_result(result, self.game_state.turn)
                else:
                    result = "Failed to send tribute."
                    self.renderer.set_last_action_result(result, self.game_state.turn)
            else:
                result = "Invalid choice."
                self.renderer.set_last_action_result(result, self.game_state.turn)
        except ValueError:
            result = "Please enter valid numbers."
            self.renderer.set_last_action_result(result, self.game_state.turn)
    
    def display_detailed_status(self, player):
        """Display detailed status information"""
        print(f"\nDetailed Status for {player.name}:")
        print(f"Land: {player.land}")
        print(f"Peasants: {player.peasants}")
        print(f"Soldiers: {player.soldiers}")
        print(f"Food Production: {player.food_production}")
        print(f"Food Consumption: {player.food_consumption}")
        print(f"Net Food: {player.net_food}")
        print(f"Total Power: {player.get_total_power():.1f}")
        
        input("\nPress Enter to continue...")