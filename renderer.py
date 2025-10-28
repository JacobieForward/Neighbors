import os
from config import *

class Renderer:
    def __init__(self):
        #self.clear_screen()
        self.last_action_result = None  # Store the result of the last action
        self.last_action_turn = None  # Store the turn when the last action was performed
        self.player_attack_results = []  # Track player's attack results
        self.incoming_attack_results = []  # Track attacks against player
    
    def clear_screen(self):
        """Clear the terminal screen"""
        os.system('cls' if os.name == 'nt' else 'clear')
    
    def set_last_action_result(self, result, turn=None):
        """Set the result of the last action"""
        self.last_action_result = result
        self.last_action_turn = turn
    
    def add_player_attack_result(self, result):
        """Add a result from a player's attack"""
        self.player_attack_results.append(result)
    
    def add_incoming_attack_result(self, result):
        """Add a result from an attack against the player"""
        self.incoming_attack_results.append(result)
    
    def clear_attack_results(self):
        """Clear stored attack results"""
        self.player_attack_results.clear()
        self.incoming_attack_results.clear()
    
    def clear_old_action_results(self, current_turn):
        """Clear action results from previous turns"""
        if self.last_action_turn is not None and self.last_action_turn < current_turn:
            self.last_action_result = None
            self.last_action_turn = None
    
    def display_game_state(self, game_state, player, show_action_result=True):
        """Display the current game state"""
        #self.clear_screen()
        print("=" * 60)
        print("NEIGHBORS - A Diplomatic Strategy Game")
        print("=" * 60)
        
        # Display combat results from previous turn
        combat_results = game_state.get_combat_results()
        if combat_results:
            print("\n⚔️  COMBAT RESULTS:")
            for result in combat_results:
                print(f"  {result}")
            print("-" * 60)
        
        # Display player's resources
        worked_land = player.peasants // PEASANTS_PER_ACRE if PEASANTS_PER_ACRE > 0 else 0
        # Ensure worked land cannot exceed total land
        worked_land = min(worked_land, player.land)
        print(f"\n{player.name} - Your Kingdom:")
        print(f"Land: {player.land} | Worked Land: {worked_land}")
        print(f"Population: {player.peasants} peasants, {player.soldiers} soldiers")
        print(f"Food: {player.food_production} production, {player.food_consumption} consumption, {player.net_food} net")
        
        # Display neighbors' relative power
        print(f"\nNeighbors:")
        for neighbor in game_state.neighbors:
            relative_power = game_state.get_relative_power(player, neighbor)
            print(f"  {neighbor.name}: {relative_power} power")
        
        # Display recent messages
        if player.message_history:
            print(f"\nRecent Messages:")
            recent_messages = player.message_history[-9:]  # Last 9 messages
            for msg in recent_messages:
                if 'from' in msg:
                    print(f"  From {msg['from']}: {msg['content']}")
                else:
                    print(f"  To {msg['to']}: {msg['content']}")
        
        # Display attack results if available and requested
        if show_action_result:
            if self.player_attack_results:
                print(f"\n⚔️  Your Attack Results:")
                for result in self.player_attack_results:
                    print(f"  {result}")
                print("-" * 60)
            
            if self.incoming_attack_results:
                print(f"\n🛡️  Incoming Attacks:")
                for result in self.incoming_attack_results:
                    print(f"  {result}")
                print("-" * 60)
            
            if self.last_action_result and self.last_action_turn == game_state.turn:
                print(f"\n📋 Last Action Result:")
                print(f"  {self.last_action_result}")
                print("-" * 60)
        
        print("\n" + "=" * 60)
    
    def display_action_menu(self):
        """Display the action menu for the player"""
        print("\nAvailable Actions:")
        print("1. Send Message")
        print("2. Recruit Soldiers")
        print("3. Dismiss Soldiers")
        print("4. Attack Neighbor")
        print("5. Send Tribute")
        print("6. End Turn")
    
    def display_final_results(self, game_state):
        """Display final game results"""
        #self.clear_screen()
        print("=" * 60)
        print("GAME OVER")
        print("=" * 60)
        
        # Show final standings
        all_entities = [game_state.player] + game_state.neighbors
        all_entities.sort(key=lambda x: x.get_total_power(), reverse=True)
        
        print("\nFinal Rankings:")
        for i, entity in enumerate(all_entities, 1):
            power = entity.get_total_power()
            land = entity.land
            net_food = entity.net_food
            print(f"{i}. {entity.name}: {power:.1f} power, {land} acres, {net_food} net food")
        
        if all_entities[0] == game_state.player:
            print("\n🎉 Victory! You have achieved dominance!")
        else:
            print(f"\nDefeat. {all_entities[0].name} has achieved dominance.")