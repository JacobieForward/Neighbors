import time
import argparse
import os
from game_state import GameState
from human_player import HumanPlayer
from llm_neighbor import LLMNeighbor
from renderer import Renderer
from actions import ActionHandler
from dotenv import load_dotenv
from config import *

def main(verbose_logging=True, use_ollama=False):
    # Initialize game state
    game_state = GameState()
    
    # Create human player
    player = HumanPlayer("Western Kingdom", game_state)
    
    # Create neighbor names
    neighbors = []
    neighbor_names = ["Northern Realm", "Eastern Empire", "Southern Dominion"]
    
    # Create LLM Neighbors (limited by config)
    for i, name in enumerate(neighbor_names[:MAX_NEIGHBORS]):
        llm_neighbor = LLMNeighbor(name, game_state, player_id=i+1, verbose_logging=verbose_logging, use_ollama=use_ollama)
        neighbors.append(llm_neighbor)
    
    game_state.initialize_game(player, neighbors)
    
    # Initialize renderer and action handler
    renderer = Renderer()
    action_handler = ActionHandler(game_state, verbose_logging)
    action_handler.set_renderer(renderer)  # Connect renderer to action handler
    
    # Connect renderer to game state for attack tracking
    game_state.renderer = renderer
    
    # Main game loop
    while not game_state.is_game_over():
        print(f"\n=== TURN {game_state.turn} ===")
        
        # Clear attack results and old action results at start of turn
        renderer.clear_attack_results()
        renderer.clear_old_action_results(game_state.turn)
        
        # Reset turn tracking for all entities
        player.reset_turn()
        for neighbor in neighbors:
            neighbor.reset_turn()
        
        # Turn order: player first, then neighbors in creation order
        all_entities = [player] + neighbors
        
        for entity in all_entities:
            if entity == player:
                action_handler.handle_player_actions(player)
            else:
                # AI neighbor turn
                entity.take_turn()
        
        # Resolve combat and diplomacy
        game_state.resolve_combat()
        game_state.process_diplomacy()
        
        # Update economy
        game_state.update_economy()
        
        # Check win conditions
        if game_state.check_victory_conditions():
            break
            
        # Advance to next turn
        game_state.advance_turn()
        time.sleep(TURN_DELAY)  # Pause between turns from config
    
    # Game over
    renderer.display_final_results(game_state)

if __name__ == "__main__":
    load_dotenv()
    
    # Set up command line argument parsing
    parser = argparse.ArgumentParser(description="Run the Neighbors game simulation")
    parser.add_argument("-v", "--verbose", action="store_true", 
                       help="Enable verbose logging for AI neighbors")
    parser.add_argument("--ollama", action="store_true",
                       help="Use ChatOllama instead of ChatOpenAI for AI neighbors")
    
    args = parser.parse_args()
    
    # Run the game with the specified settings
    main(verbose_logging=args.verbose, use_ollama=args.ollama)
