# LLM Neighbor that uses tools to call game actions
from langchain_core.tools import StructuredTool
import random
from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
from langchain_community.chat_models.llamacpp import ChatLlamaCpp
from langchain.agents import create_tool_calling_agent, AgentExecutor
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode, tools_condition
#from langchain_ollama import ChatOllama
from langgraph.graph import MessagesState
from langchain_core.tools import tool
from langgraph.checkpoint.memory import InMemorySaver
from langchain_community.vectorstores import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from config import *
import os

class LLMNeighbor:
    def __init__(self, name, game_state, player_id):
        self.name = name
        self.game_state = game_state
        self.player_id = player_id

        # Initialize LLM and tools
        #self.llm = ChatOllama(
        #    base_url="http://localhost:11434",
        #    model="gpt-oss:20b",
        #    temperature=0.6,
        #    top_p=0.8,
        #    top_k=50,
        #    repeat_penalty=1.1,
        #    repeat_last_n=64,
        #    num_ctx=24000,
        #    num_predict=1536,
        #    keep_alive="7m",
        #    num_thread=8
        #)
        # Initialize OpenAI LLM
        self.llm = ChatOpenAI(
            api_key=os.getenv("OPENAI_API_KEY"),
            model="gpt-4o-mini",
            temperature=0.5,
            top_p=0.8,
            top_k=50,
            repeat_penalty=1.1,
            repeat_last_n=64,
            num_ctx=24000,
            num_predict=1536,
            keep_alive="7m",
            num_thread=8,
        )

        self.prompt_template = """Your name is {name}. You are: {personality}. Your current status is: {status}. The game state is: {game_state_info}.

        Events since your last turn:
        {turn_summary}

        Relevant game rules:
        {relevant_rules}

        {agent_scratchpad}"""

        # Initialize RAG system
        self.embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2", model_kwargs={"device": "cpu"})
        self.text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
        self.vectorstore = None
        self.setup_rag()
        
        # Starting resources from config
        self.land = STARTING_LAND
        self.peasants = STARTING_PEASANTS
        self.soldiers = STARTING_SOLDIERS
        self.food_production = STARTING_PEASANTS * FOOD_PER_PEASANT
        self.food_consumption = STARTING_SOLDIERS * FOOD_PER_SOLDIER
        self.net_food = self.food_production - self.food_consumption
        
        # Generate the AI's personality
        self.personality = self.generate_personality()
        
        # Message tracking
        self.messages_sent_this_turn = set()
        self.message_history = []
        
        # Attack tracking
        self.attacks_sent_this_turn = set()
        
        # AI memory
        self.checkpointer = InMemorySaver()

        # Build the langgraph graph, which is an agentic loop
        self.graph = self.build_graph()
    def take_turn(self):
        """LLM agent takes its turn"""
        print(f"""

        --------------------------------------------
        🤖🤖🤖 LLM {self.name} taking turn 🤖🤖🤖
        --------------------------------------------

        """)
        try:
            # Get current game state for the LLM
            gameStateInfo = self.get_game_state_info()
            
            turn_summary = self.get_ai_turn_summary()

            relevant_rules = self.get_relevant_rules(f"{self.get_ai_turn_summary()}")

            formatted_prompt = self.prompt_template.format(
                name=self.name,
                personality=self.personality,
                status=self.get_status(),
                game_state_info=gameStateInfo,
                turn_summary=turn_summary,
                relevant_rules=relevant_rules,
                agent_scratchpad=""
            )
		
            result = self.graph.invoke({"messages": [HumanMessage(content=formatted_prompt)]}, config={"configurable":{"thread_id":self.player_id}})
            print(formatted_prompt)
            print(result["messages"][-1].content)
        except Exception as e:
            print(f"Error in LLM turn for {self.name}: {e}")
        
        # Reset turn tracking
        self.reset_turn()

    def get_ai_turn_summary(self):
        """Get a summary of all actions that happened to this AI since its last turn"""
        summary_parts = []
        
        # Check for incoming attacks
        incoming_attacks = []
        for result in self.game_state.combat_results:
            if f"defeated by {self.name}" in result.lower() or f"repelled {self.name}" in result.lower():
                incoming_attacks.append(result)
        
        if incoming_attacks:
            summary_parts.append("INCOMING ATTACKS:")
            for attack in incoming_attacks:
                summary_parts.append(f"  - {attack}")
        
        # Check for outgoing attacks (attacks this AI made)
        outgoing_attacks = []
        for result in self.game_state.combat_results:
            if f"{self.name} defeats" in result or f"{self.name} repelled" in result:
                outgoing_attacks.append(result)
        
        if outgoing_attacks:
            summary_parts.append("YOUR ATTACKS:")
            for attack in outgoing_attacks:
                summary_parts.append(f"  - {attack}")
        
        # Check for messages received since last turn
        current_turn = self.game_state.turn
        recent_messages = [msg for msg in self.message_history 
                          if msg.get('from') and msg.get('turn', 0) == current_turn]
        if recent_messages:
            summary_parts.append("MESSAGES RECEIVED:")
            for msg in recent_messages:
                summary_parts.append(f"  - From {msg['from']}: {msg['content']}")
        
        # Check for resource changes
        resource_changes = []
        if hasattr(self, '_previous_resources'):
            land_change = self.land - self._previous_resources.get('land', 0)
            peasant_change = self.peasants - self._previous_resources.get('peasants', 0)
            soldier_change = self.soldiers - self._previous_resources.get('soldiers', 0)
            
            if land_change != 0:
                resource_changes.append(f"Land: {land_change:+d}")
            if peasant_change != 0:
                resource_changes.append(f"Peasants: {peasant_change:+d}")
            if soldier_change != 0:
                resource_changes.append(f"Soldiers: {soldier_change:+d}")
        
        if resource_changes:
            summary_parts.append("RESOURCE CHANGES:")
            summary_parts.append(f"  - {', '.join(resource_changes)}")
        
        # Store current resources for next turn comparison
        self._previous_resources = {
            'land': self.land,
            'peasants': self.peasants,
            'soldiers': self.soldiers
        }
        
        if not summary_parts:
            return "No significant events since your last turn."
        
        return "\n".join(summary_parts)
    
    def generate_personality(self):
        """Generate a personality description by asking AI to create a historical ruler"""
        
        prompt = f"""Create a brief personality description (2-3 sentences) for a historical ruler that could exist in a medieval setting ruling {self.name}. 
        Include their key traits, and ruling style. Make it unique and interesting for a diplomatic medieval strategy game. Make sure each personality loves talking to other players.
        
        Format: "[2-3 sentence personality description]"
        
        Example: "A patient and calculating ruler known for his diplomatic skills and long-term planning. He prefers negotiation over warfare but is not afraid to use force when necessary. He values knowledge and often seeks counsel from scholars and advisors.
        
        Example: "A bloodthirsty and ruthless ruler known for his brutal tactics and willingness to use violence to achieve his goals. He values strength and power above all else and is not afraid to use force to expand his territory or extract tribute."
        
        Example: "A cunning and manipulative ruler known for her ability to use diplomacy and deception to achieve her goals. She values intelligence and often seeks counsel from her advisors and spies. She is not afraid to use force to expand her territory or extract tribute."
        
        Create a new, unique ruler:"""
        
        try:
            response = self.llm.invoke(prompt)
            print(f"Personality: {response.content.strip()}")
            return response.content.strip()
        except Exception as e:
            print(f"Error generating personality: {e}")
            return "You only scream FAILURE"
    
    def get_total_power(self):
        """Calculate total power for relative comparisons"""
        return (self.peasants + self.soldiers * 2) * self.land / 1000
    
    def update_economy(self):
        """Update economic calculations (same as player)"""
        # Peasants grow naturally using config values
        max_peasants = self.land * PEASANTS_PER_ACRE
        growth_rate = PEASANT_GROWTH_RATE if self.peasants < max_peasants else PEASANT_GROWTH_RATE_CAPPED
        new_peasants = int(self.peasants * growth_rate)
        
        if self.land > 0:
            self.peasants += new_peasants
        
        # Calculate revenue based on peasants per acre efficiency
        peasants_per_acre = self.peasants / self.land if self.land > 0 else 0
        
        # Calculate food production and consumption
        self.food_production = self.peasants * FOOD_PER_PEASANT
        self.food_consumption = self.soldiers * FOOD_PER_SOLDIER
        self.net_food = self.food_production - self.food_consumption
    
    def get_game_state_info(self):
        """Get current game state information for the LLM"""
        all_entities = [self.game_state.player] + self.game_state.neighbors
        other_entities = [e for e in all_entities if e != self]
        
        info = f"Your resources: {self.peasants} peasants, {self.soldiers} soldiers, {self.land} land\n"
        info += f"Your food: {self.food_production} production, {self.food_consumption} consumption, {self.net_food} net\n"
        
        for entity in other_entities:
            relative_power = self.game_state.get_relative_power(self, entity)
            info += f"{entity.name}: {relative_power} power, {entity.soldiers} soldiers, {entity.peasants} peasants\n"
        
        return info
    
    # Tool functions that the LLM can call
    def get_status(self) -> str:
        """Get current status and resources"""
        return f"""Land: {self.land}
        Population: {self.peasants} peasants, {self.soldiers} soldiers
        Food: {self.food_production} production, {self.food_consumption} consumption, {self.net_food} net
        Total Power: {self.get_total_power():.1f}"""
    
    def get_entity_info(self, entity_name: str) -> str:
        """Get information about another entity"""
        entity = self.game_state.get_entity_by_name(entity_name)
        if entity:
            relative_power = self.game_state.get_relative_power(self, entity)
            return f"""{entity_name}:
            Land: {entity.land}
            Population: {entity.peasants} peasants, {entity.soldiers} soldiers
            Food: {entity.food_production} production, {entity.food_consumption} consumption, {entity.net_food} net
            Relative Power: {relative_power}"""
        return f"Entity {entity_name} not found"
    
    def get_player_info(self, player_name: str) -> str:
        """Get detailed information about another player including their resource counts"""
        entity = self.game_state.get_entity_by_name(player_name)
        if not entity:
            return f"Player '{player_name}' not found. Available players: {', '.join([e.name for e in [self.game_state.player] + self.game_state.neighbors if e.name != self.name])}"
        
        # Calculate relative power
        relative_power = self.game_state.get_relative_power(self, entity)
        
        return f"""Player Information for {player_name}:
        
        Resources:
        Land: {entity.land} acres
        Peasants: {entity.peasants}
        Soldiers: {entity.soldiers}
        
        Economy:
        Food Production: {entity.food_production}
        Food Consumption: {entity.food_consumption}
        Net Food: {entity.net_food}
        
        Military:
        Total Power: {entity.get_total_power():.1f}
        Relative Power vs You: {relative_power}"""
    
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
    
    def send_message(self, recipient_name: str, content: str) -> str:
        """Send a diplomatic message to another entity. This is FREE and has NO COST. Use this to negotiate, threaten, form alliances, gather information, or respond to other players. You can only message each entity once per turn, so make it count! Messages are your primary tool for diplomacy and can prevent wars or secure tribute."""
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
        
        # Check if already attacked this target this turn
        if target_name in self.attacks_sent_this_turn:
            return f"Already attacked {target_name} this turn. You can only attack each player once per turn."
        
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
        
        # Track this attack
        self.attacks_sent_this_turn.add(target_name)
        
        return f"Attacking {target_name} with {attack_force} soldiers!"
    
    def send_tribute(self, recipient_name: str, land_amount: int = 0, peasant_amount: int = 0) -> str:
        """Send tribute (land or peasants) to another player"""
        target = self.game_state.get_entity_by_name(recipient_name)
        if not target:
            return f"Target {recipient_name} not found."
        
        if land_amount < 0 or peasant_amount < 0:
            return "Cannot send negative amounts."
        
        if land_amount == 0 and peasant_amount == 0:
            return "Must send at least some land or peasants."
        
        # Check if we have enough resources
        if land_amount > self.land:
            return f"Cannot send {land_amount} land. Only have {self.land}."
        
        if peasant_amount > self.peasants:
            return f"Cannot send {peasant_amount} peasants. Only have {self.peasants}."
        
        # Transfer resources
        if land_amount > 0:
            self.land -= land_amount
            target.land += land_amount
        
        if peasant_amount > 0:
            self.peasants -= peasant_amount
            target.peasants += peasant_amount
        
        # Send a message about the tribute (don't count as a regular message)
        tribute_message = f"Tribute sent: {land_amount} land, {peasant_amount} peasants"
        self.game_state.send_message(self, recipient_name, tribute_message)
        self.message_history.append({
            'to': recipient_name,
            'content': tribute_message,
            'turn': self.game_state.turn
        })
        
        return f"Sent tribute to {recipient_name}: {land_amount} land, {peasant_amount} peasants"
    
    def can_recruit_soldiers(self, amount):
        """Check if AI can recruit specified number of soldiers"""
        return self.peasants >= amount and self.net_food >= amount * FOOD_PER_SOLDIER
    
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
        self.attacks_sent_this_turn.clear()
    
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

    def build_graph(self):
        # Define tools as instance methods
        tools = [
            StructuredTool.from_function(
                func=self.recruit_soldiers,
                name="recruit_soldiers",
                description="Recruit soldiers from peasants. Reduces peasants and increases soldiers. Since there are fewer peasants you will make less taxes and pay upkeep on soldiers."
            ),
            StructuredTool.from_function(
                func=self.dismiss_soldiers,
                name="dismiss_soldiers", 
                description="Dismiss soldiers back to peasants. Peasants can't fight, but they make money for you. This will increase your peasants and decrease your soldiers."
            ),
            StructuredTool.from_function(
                func=self.send_message,
                name="send_message",
                description="Send a diplomatic message to another entity. This is FREE and has NO COST. Use this to negotiate, threaten, form alliances, gather information, or respond to other players. You can only message each entity once per turn, so make it count! Messages are your primary tool for diplomacy and can prevent wars or secure tribute."
            ),
            StructuredTool.from_function(
                func=self.attack_target,
                name="attack_target",
                description="Attack another entity with your soldiers. It is easier to defend than to attack, but if you attack somebody successfully you take some of their land."
            ),
            StructuredTool.from_function(
                func=self.send_tribute,
                name="send_tribute",
                description="Send tribute (land or peasants) to another entity. This can be used for diplomacy, trade, alliances, or to avoid conflict."
            ),
            StructuredTool.from_function(
                func=self.get_relevant_rules,
                name="get_relevant_rules",
                description="Retrieve the most relevant game rules or policies for a question. Call this BEFORE deciding actions if you're unsure what's allowed, what's efficient, or what is strategically wise."
            ),
            StructuredTool.from_function(
                func=self.get_player_info,
                name="get_player_info",
                description="Get detailed information about another player including their resources, military strength, economy, and diplomatic relations. Use this to assess other players before making diplomatic or military decisions."
            )
        ]
        # load the system prompt from the file
        with open("system_prompt.txt", "r", encoding="utf-8") as f:
            system_prompt = f.read()

        # System message
        sys_msg = SystemMessage(content=system_prompt)

        self.llm = self.llm.bind_tools(tools)

        graph = StateGraph(MessagesState)

        # Node 1: The agent with logging
        def agent_node(state: MessagesState):
            print(f"\n🤖 AGENT NODE - Processing message for {self.name}...")
            messages = state["messages"]
            print(f"📝 Input messages count: {len(messages)}")
            
            try:
                # Add system message at the beginning
                messages_with_system = [sys_msg] + messages
                
                response = self.llm.invoke(messages_with_system)
                print(f"✅ Agent response generated successfully")
                print(f"📤 Response type: {type(response)}")
                if hasattr(response, 'tool_calls') and response.tool_calls:
                    print(f"🔧 Tool calls requested: {len(response.tool_calls)}")
                    for i, tool_call in enumerate(response.tool_calls):
                        print(f"   Tool {i+1}: {tool_call['name']} with args: {tool_call['args']}")
                else:
                    print("💬 No tool calls - direct response")
                
                return {"messages": [response]}
            except Exception as e:
                print(f"❌ Error in agent node: {e}")
                raise

        # Node 2: The tools with detailed logging
        def tool_node_with_logging(state: MessagesState):
            print(f"\n🔧 TOOL NODE - Executing tools...")
            messages = state["messages"]
            
            # Find the last message with tool calls
            last_message = messages[-1]
            if not hasattr(last_message, 'tool_calls') or not last_message.tool_calls:
                print("⚠️ No tool calls found in last message")
                return {"messages": []}
            
            print(f"🎯 Found {len(last_message.tool_calls)} tool calls to execute")
            
            tool_results = []
            for i, tool_call in enumerate(last_message.tool_calls):
                tool_name = tool_call['name']
                tool_args = tool_call['args']
                tool_id = tool_call['id']
                
                print(f"\n🔨 Executing Tool {i+1}/{len(last_message.tool_calls)}:")
                print(f"   Name: {tool_name}")
                print(f"   Args: {tool_args}")
                print(f"   ID: {tool_id}")
                
                try:
                    # Find the tool function
                    tool_func = None
                    for tool in tools:
                        if tool.name == tool_name:
                            tool_func = tool
                            break
                    
                    if not tool_func:
                        error_msg = f"Tool '{tool_name}' not found"
                        print(f"❌ {error_msg}")
                        tool_results.append(ToolMessage(
                            content=error_msg,
                            tool_call_id=tool_id
                        ))
                        continue
                    
                    # Execute the tool
                    print(f"⚡ Executing {tool_name}...")
                    result = tool_func.invoke(tool_args)
                    print(f"✅ Tool {tool_name} executed successfully")
                    print(f"📊 Result type: {type(result)}")
                    print(f"📄 Result preview: {result}")
                    
                    tool_results.append(ToolMessage(
                        content=str(result),
                        tool_call_id=tool_id
                    ))
                    
                except Exception as e:
                    error_msg = f"Error executing {tool_name}: {str(e)}"
                    print(f"❌ {error_msg}")
                    tool_results.append(ToolMessage(
                        content=error_msg,
                        tool_call_id=tool_id
                    ))
            
            print(f"🏁 Tool execution completed. {len(tool_results)} results generated")
            return {"messages": tool_results}

        # --- Graph wiring ---
        graph.add_node("agent", agent_node)
        graph.add_node("tools", tool_node_with_logging)

        # start -> agent
        graph.add_edge(START, "agent")

        # if model calls a tool, go to tools node; else, end
        graph.add_conditional_edges(
            "agent",
            tools_condition,
            {"tools": "tools", "__end__": END}
        )

        # after running tools, go back to agent
        graph.add_edge("tools", "agent")

        return graph.compile(checkpointer=self.checkpointer)

    def setup_rag(self):
        """Setup RAG system with game rules"""
        try:
            with open('game_rules.txt', 'r', encoding='utf-8') as f:
                rules_text = f.read()
            
            # Split into chunks
            chunks = self.text_splitter.split_text(rules_text)
            
            # Create vector store
            self.vectorstore = Chroma.from_texts(
                chunks, 
                self.embeddings,
                collection_name=f"game_rules_{self.player_id}"
            )
        except Exception as e:
            print(f"Error setting up RAG: {e}")
            self.vectorstore = None

    def get_relevant_rules(self, query: str) -> str:
        """Get relevant game rules for a specific query"""
        if not self.vectorstore:
            return "Game rules not available."
        
        try:
            docs = self.vectorstore.similarity_search(query, k=3)
            return "\n".join([doc.page_content for doc in docs])
        except Exception as e:
            return f"Error retrieving rules: {e}"