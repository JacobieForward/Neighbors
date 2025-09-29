import random
import time
from game_state import GameState
from human_player import HumanPlayer
from ai_neighbor import AINeighbor
from llm_neighbor import LLMNeighbor
from renderer import Renderer
from actions import ActionHandler

def main():
    # Initialize game state
    game_state = GameState()
    
    # Create human player
    player = HumanPlayer("Western Kingdom", game_state)
    
    # Create neighbor names
    neighbors = []
    neighbor_names = ["Northern Realm", "Eastern Empire", "Southern Dominion"]
    
    # Create LLM Neighbors
    for i, name in enumerate(neighbor_names[:3]):
        llm_neighbor = LLMNeighbor(name, game_state, player_id=i+1)
        neighbors.append(llm_neighbor)
    
    game_state.initialize_game(player, neighbors)
    
    # Initialize renderer and action handler
    renderer = Renderer()
    action_handler = ActionHandler(game_state)
    action_handler.set_renderer(renderer)  # Connect renderer to action handler
    
    # Connect renderer to game state for attack tracking
    game_state.renderer = renderer
    
    # Main game loop
    turn = 1
    while not game_state.is_game_over():
        print(f"\n=== TURN {turn} ===")
        
        # Clear attack results at start of turn
        renderer.clear_attack_results()
        
        # Reset turn tracking for all entities
        player.reset_turn()
        for neighbor in neighbors:
            neighbor.reset_turn()
        
        # Randomize turn order (no player advantage)
        all_entities = [player] + neighbors
        random.shuffle(all_entities)
        
        for entity in all_entities:
            if entity == player:
                # Human player turn - display game state without action result on first turn
                if turn == 1 and not hasattr(renderer, '_first_turn_displayed'):
                    renderer.display_game_state(game_state, player, show_action_result=False)
                    renderer._first_turn_displayed = True
                else:
                    renderer.display_game_state(game_state, player, show_action_result=True)
                action_handler.handle_player_actions(player)
            else:
                # AI neighbor turn
                entity.take_turn()
        
        # Resolve combat and diplomacy
        game_state.resolve_combat()
        game_state.process_diplomacy()
        
        # Update economy
        game_state.update_economy()
        
        # Process messages
        game_state.process_messages()
        
        # Check win conditions
        if game_state.check_victory_conditions():
            break
            
        turn += 1
        time.sleep(1)  # Brief pause between turns
    
    # Game over
    renderer.display_final_results(game_state)

if __name__ == "__main__":
    main()
