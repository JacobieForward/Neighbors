# LLM Neighbor that uses tools to call game actions
from langchain_core.tools import StructuredTool
import random
from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
from langchain_community.chat_models.llamacpp import ChatLlamaCpp
from langchain.agents import create_tool_calling_agent, AgentExecutor
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
import os

class LLMNeighbor:
    def __init__(self, name, game_state, player_id):
        self.name = name
        self.game_state = game_state
        self.player_id = player_id

        self.system_prompt = """You are a ruler in a diplomatic strategy game. You must always act in your own long-term self-interest.
        DO NOT REPEAT YOURSELF. DO NOT SAY THE SAME THING TWICE. Quickly and concisely respond with your actions."""

        # Your current goals are: {goals}
        self.prompt_template = """You are {name}, a ruler in a diplomatic strategy game.
        Your personality traits are: {personality}
        
        Your current status is: {status}

        You can use the following tools to take actions: 
        - recruit_soldiers: Recruit soldiers from peasants
        - dismiss_soldiers: Dismiss soldiers back to peasants
        - send_message: Send a diplomatic message to another entity and decide what to say in the message.
        - attack_target: Attack another entity

        Based on your personality and current situation, decide what actions to take this turn.
        You can take multiple actions if appropriate. Be strategic and roleplay according to your personality.

        Current game state: {game_state}

        Look at the game state, then look at your personality and goals. Finally, look at your tools once and take an action. If you take an action
        look at your tools again and decide whether or not to take another action. Repeat this process until you do not want to take an any more actions with the tools.

        {agent_scratchpad}"""
        
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
        
        # Initialize LLM and tools
        self._setup_llm()
    
    def _setup_llm(self):
        """Setup the LLM pipeline"""
        # Define the Tools that the LLM can use as StructuredTools for LangChain
        self.tools = [
            StructuredTool.from_function(
                func=self.recruit_soldiers,
                name="recruit_soldiers",
                description="Recruit soldiers from peasants. Requires peasants and net profit."
            ),
            StructuredTool.from_function(
                func=self.dismiss_soldiers,
                name="dismiss_soldiers", 
                description="Dismiss soldiers back to peasants."
            ),
            StructuredTool.from_function(
                func=self.send_message,
                name="send_message",
                description="Send a diplomatic message to another entity."
            ),
            StructuredTool.from_function(
                func=self.attack_target,
                name="attack_target",
                description="Attack another entity with your soldiers."
            )
        ]

        """self.pre_tool_llm = ChatLlamaCpp(
            #model_path="./models/Qwen3-4B-Function-Calling-Pro.gguf", 
            #model_path="./models/Qwen3-1.7B-Q8_0.gguf",
            model_path="./models/Qwen3-4B-Instruct-2507-UD-IQ1_S.gguf",
            temperature=0.2, 
            n_ctx=4000, 
            #top_p=0.95, 
            max_tokens=4000, 
            n_gpu_layers=-1,
            #context_length=16384, 
            verbose=False,
            #device_map="auto"
        )"""
        if not os.environ.get("OPENAI_API_KEY"):
            raise Exception("No OPENAI_API_KEY found in environment variables")

        self.pre_tool_llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.5, max_tokens=3000, max_retries=3)

        # Create the prompt template for the agent
        prompt = ChatPromptTemplate.from_template(self.prompt_template)

        self.llm = create_tool_calling_agent(self.pre_tool_llm, self.tools, prompt)

        self.llm_agent_executor = AgentExecutor(agent=self.llm, tools=self.tools, verbose=True, handle_parsing_errors=True)
    
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
        """LLM agent takes its turn"""
        # Analyze current situation
        self.analyze_situation()
        
        # Get current game state for the LLM
        game_state_info = self._get_game_state_info()
        
        try:
            # Pass the input as a dictionary with the required variables
            input_data = {
                "name": self.name,
                "personality": self.personality,
                "status": self.get_status(),
                "game_state": game_state_info,
                "agent_scratchpad": ""  # This will be populated by the agent executor
            }

            result = self.llm_agent_executor.invoke(input_data)
            print(f"{self.name} (LLM) response: {result}")
            
        except Exception as e:
            print(f"Error in LLM turn for {self.name}: {e}")
            # Fallback to simple random actions if LLM fails
            self._fallback_actions()
        
        # Reset turn tracking
        self.reset_turn()
    
    def _get_game_state_info(self):
        """Get current game state information for the LLM"""
        all_entities = [self.game_state.player] + self.game_state.neighbors
        other_entities = [e for e in all_entities if e != self]
        
        info = f"Your resources: {self.peasants} peasants, {self.soldiers} soldiers, {self.free_land + self.worked_land} land\n"
        info += f"Your economy: {self.revenue} revenue, {self.expenses} expenses, {self.net_profit} net\n"
        
        for entity in other_entities:
            relative_power = self.game_state.get_relative_power(self, entity)
            info += f"{entity.name}: {relative_power} power, {entity.soldiers} soldiers, {entity.peasants} peasants\n"
        
        return info
    
    def _fallback_actions(self):
        """Fallback actions if LLM fails"""
        if self.net_profit < 0 and self.peasants >= 100:
            self.extort_taxes()
        elif self.peasants < 1500 and self.net_profit > 1000:
            self.invest(500)
        elif self.can_recruit_soldiers(50):
            self.recruit_soldiers(50)
    
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
    
    # Tool functions that the LLM can call
    def get_status(self) -> str:
        """Get current status and resources"""
        return f"""Status for {self.name}:
        Land: {self.free_land} free, {self.worked_land} worked
        Population: {self.peasants} peasants, {self.soldiers} soldiers
        Economy: {self.revenue} revenue, {self.expenses} expenses, {self.net_profit} net profit
        Total Power: {self.get_total_power():.1f}"""
    
    def get_entity_info(self, entity_name: str) -> str:
        """Get information about another entity"""
        entity = self.game_state.get_entity_by_name(entity_name)
        if entity:
            relative_power = self.game_state.get_relative_power(self, entity)
            return f"""{entity_name}:
            Land: {entity.free_land} free, {entity.worked_land} worked
            Population: {entity.peasants} peasants, {entity.soldiers} soldiers
            Economy: {entity.revenue} revenue, {entity.expenses} expenses
            Relative Power: {relative_power}"""
        return f"Entity {entity_name} not found"
    
    def recruit_soldiers(self, amount: int) -> str:
        """Recruit soldiers from peasants"""
        if self.can_recruit_soldiers(amount):
            self.peasants -= amount
            self.soldiers += amount
            return f"Recruited {amount} soldiers. Now have {self.soldiers} soldiers."
        return f"Cannot recruit {amount} soldiers. Need {amount} peasants and {amount * 3} net profit."
    
    def dismiss_soldiers(self, amount: int) -> str:
        """Dismiss soldiers back to peasants"""
        if amount <= self.soldiers:
            self.soldiers -= amount
            self.peasants += amount
            return f"Dismissed {amount} soldiers. Now have {self.soldiers} soldiers and {self.peasants} peasants."
        return f"Cannot dismiss {amount} soldiers. Only have {self.soldiers} soldiers."
    
    def extort_taxes(self) -> str:
        """Extort high taxes (loses peasants but gains money)"""
        if self.peasants >= 100:
            self.peasants -= 100
            money_gained = 500
            return f"Extorted high taxes! Lost 100 peasants but gained {money_gained} money."
        return "Not enough peasants to extort taxes. Need at least 100 peasants."
    
    def invest(self, amount: int) -> str:
        """Invest money to gain peasants"""
        if self.net_profit >= amount:
            new_peasants = amount // 2
            self.peasants += new_peasants
            return f"Invested {amount}! Gained {new_peasants} peasants."
        return f"Cannot invest {amount}. Need {amount} net profit."
    
    def send_message(self, recipient_name: str, content: str) -> str:
        """Send a message to another player"""
        if recipient_name not in self.messages_sent_this_turn:
            self.game_state.send_message(self, recipient_name, content)
            self.messages_sent_this_turn.add(recipient_name)
            self.message_history.append({
                'to': recipient_name,
                'content': content,
                'turn': self.game_state.turn
            })
            return f"Message sent to {recipient_name}: {content}"
        return f"Already sent a message to {recipient_name} this turn."
    
    def attack_target(self, target_name: str, attack_force: int = None) -> str:
        """Attack a target player"""
        target = self.game_state.get_entity_by_name(target_name)
        if not target:
            return f"Target {target_name} not found."
        
        if self.soldiers < 50:
            return "Need at least 50 soldiers to attack."
        
        if attack_force is None:
            attack_force = min(self.soldiers, int(self.soldiers * 0.8))
        
        if attack_force > self.soldiers:
            return f"Cannot attack with {attack_force} soldiers. Only have {self.soldiers}."
        
        # Queue combat
        self.game_state.combat_queue.append({
            'attacker': self,
            'defender': target,
            'attacker_soldiers': attack_force
        })
        
        return f"Attacking {target_name} with {attack_force} soldiers!"
    
    def can_recruit_soldiers(self, amount):
        """Check if AI can recruit specified number of soldiers"""
        return self.peasants >= amount and self.net_profit >= amount * 3
    
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
    
    def _execute_tool_calls(self, tool_calls):
        """Execute tool calls from the LLM response"""
        for tool_call in tool_calls:
            tool_name = tool_call["name"]
            tool_args = tool_call["args"]
            
            # Find and execute the tool
            for tool in self.tools:
                if tool.name == tool_name:
                    try:
                        result = tool.invoke(tool_args)
                        print(f"tool_call: {tool_call}")
                        print(f"{self.name}: {result}")
                    except Exception as e:
                        print(f"{self.name}: Error executing {tool_name}: {e}")
                    break
