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
                    break  # End turn
                elif choice == "9":
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
                        self.renderer.set_last_action_result(result)
                    else:
                        result = "Failed to send message."
                        self.renderer.set_last_action_result(result)
                else:
                    result = f"You've already sent a message to {recipient.name} this turn."
                    self.renderer.set_last_action_result(result)
            else:
                result = "Invalid choice."
                self.renderer.set_last_action_result(result)
        except ValueError:
            result = "Please enter a valid number."
            self.renderer.set_last_action_result(result)
    
    def handle_recruit_soldiers(self, player):
        """Handle recruiting soldiers"""
        try:
            amount = int(input("How many soldiers to recruit? "))
            if player.recruit_soldiers(amount):
                result = f"Recruited {amount} soldiers!"
                self.renderer.set_last_action_result(result)
            else:
                result = "Cannot recruit that many soldiers. Check your peasants and finances."
                self.renderer.set_last_action_result(result)
        except ValueError:
            result = "Please enter a valid number."
            self.renderer.set_last_action_result(result)
    
    def handle_dismiss_soldiers(self, player):
        """Handle dismissing soldiers"""
        try:
            amount = int(input("How many soldiers to dismiss? "))
            if player.dismiss_soldiers(amount):
                result = f"Dismissed {amount} soldiers!"
                self.renderer.set_last_action_result(result)
            else:
                result = "Cannot dismiss that many soldiers."
                self.renderer.set_last_action_result(result)
        except ValueError:
            result = "Please enter a valid number."
            self.renderer.set_last_action_result(result)
    
    def handle_extort_taxes(self, player):
        """Handle extorting taxes"""
        if player.peasants >= 100:
            money_gained = player.extort_taxes()
            result = f"Extorted high taxes! Gained {money_gained} but lost 100 peasants."
            self.renderer.set_last_action_result(result)
        else:
            result = "Not enough peasants to extort taxes."
            self.renderer.set_last_action_result(result)
    
    def handle_invest(self, player):
        """Handle investing"""
        try:
            amount = int(input("How much to invest? "))
            if player.invest(amount):
                result = f"Invested {amount}!"
                self.renderer.set_last_action_result(result)
            else:
                result = "Cannot invest that much. Check your finances."
                self.renderer.set_last_action_result(result)
        except ValueError:
            result = "Please enter a valid number."
            self.renderer.set_last_action_result(result)
    
    def handle_attack(self, player):
        """Handle attacking a neighbor"""
        if player.soldiers < 50:
            result = "You need at least 50 soldiers to launch an attack!"
            self.renderer.set_last_action_result(result)
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
                min_attack = 50  # Minimum attack force
                
                attack_force = int(input(f"How many soldiers to attack with? ({min_attack}-{max_attack}): "))
                
                if min_attack <= attack_force <= max_attack:
                    if player.attack_target(target.name, attack_force):
                        # Immediately resolve the combat and show results
                        result = self._resolve_player_attack(player, target, attack_force)
                        self.renderer.set_last_action_result(result)
                    else:
                        result = "Failed to launch attack."
                        self.renderer.set_last_action_result(result)
                else:
                    result = f"Attack force must be between {min_attack} and {max_attack}."
                    self.renderer.set_last_action_result(result)
            else:
                result = "Invalid choice."
                self.renderer.set_last_action_result(result)
        except ValueError:
            result = "Please enter a valid number."
            self.renderer.set_last_action_result(result)
    
    def _resolve_player_attack(self, attacker, defender, attack_force):
        """Resolve a player's attack immediately and return detailed results"""
        import random
        
        # Simple combat resolution (same logic as in game_state.py)
        defender_soldiers = defender.soldiers
        
        # Attacker needs advantage to win
        attack_power = attack_force * 0.8  # Attacker penalty
        defense_power = defender_soldiers * 1.2  # Defender bonus
        
        total_power = attack_power + defense_power
        attacker_win_chance = attack_power / total_power if total_power > 0 else 0.5
        
        if random.random() < attacker_win_chance:
            # Attacker wins - calculate gains and losses
            land_gained = min(50, defender.free_land + defender.worked_land // 4)
            peasants_gained = min(200, defender.peasants // 4)
            
            # Transfer resources
            defender.free_land = max(0, defender.free_land - land_gained)
            defender.worked_land = max(0, defender.worked_land - land_gained)
            defender.peasants = max(0, defender.peasants - peasants_gained)
            
            attacker.free_land += land_gained
            attacker.peasants += peasants_gained
            
            # Both sides lose soldiers
            attacker_losses = attack_force // 3
            defender_losses = defender_soldiers // 2
            
            attacker.soldiers = max(0, attacker.soldiers - attacker_losses)
            defender.soldiers = max(0, defender.soldiers - defender_losses)
            
            # Return detailed victory result
            return f"VICTORY! You defeated {defender.name}!\n" \
                   f"• Gained: {land_gained} acres, {peasants_gained} peasants\n" \
                   f"• Your losses: {attacker_losses} soldiers\n" \
                   f"• Enemy losses: {defender_losses} soldiers"
        else:
            # Defender wins - calculate losses
            attacker_losses = attack_force // 2
            defender_losses = defender_soldiers // 4
            
            attacker.soldiers = max(0, attacker.soldiers - attacker_losses)
            defender.soldiers = max(0, defender.soldiers - defender_losses)
            
            # Return detailed defeat result
            return f"DEFEAT! {defender.name} repelled your attack!\n" \
                   f"• Your losses: {attacker_losses} soldiers\n" \
                   f"• Enemy losses: {defender_losses} soldiers"
    
    def handle_send_diplomat(self, player):
        """Handle sending a diplomat (simplified for now)"""
        result = "Diplomatic system not yet implemented. Use 'Send Message' for now to communicate with neighbors."
        self.renderer.set_last_action_result(result)
    
    def display_detailed_status(self, player):
        """Display detailed status information"""
        print(f"\nDetailed Status for {player.name}:")
        print(f"Free Land: {player.free_land}")
        print(f"Worked Land: {player.worked_land}")
        print(f"Total Land: {player.free_land + player.worked_land}")
        print(f"Peasants: {player.peasants}")
        print(f"Soldiers: {player.soldiers}")
        print(f"Revenue: {player.revenue}")
        print(f"Expenses: {player.expenses}")
        print(f"Net Profit/Loss: {player.net_profit}")
        print(f"Total Power: {player.get_total_power():.1f}")
        
        input("\nPress Enter to continue...")