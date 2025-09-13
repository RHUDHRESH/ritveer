from langgraph.graph import StateGraph, END
from langchain_ollama import ChatOllama
from src.graph.state import RitveerState
from config.settings import settings

# Import all agent node functions
from src.agents.intake_agent import intake_agent_node
from src.agents.cluster_agent import cluster_agent_node
from src.agents.supplier_agent import supplier_agent_node
from src.agents.commit_agent import commit_agent_node
from src.agents.ops_agent import ops_agent_node
from src.agents.cash_agent import cash_agent_node
from src.agents.learn_agent import learn_agent_node

# Initialize the StateGraph with our RitveerState schema
workflow = StateGraph(RitveerState)

# Instantiate LLM Clients
# Fast model for quick responses (e.g., gemma3:1b)
fast_llm = ChatOllama(model="gemma3:1b", base_url=settings.OLLAMA_HOST)

# Reasoning model for complex tasks (e.g., gemma3:4b)
reasoning_llm = ChatOllama(model="gemma3:4b", base_url=settings.OLLAMA_HOST)

# Add Nodes to Graph
workflow.add_node("intake_agent", intake_agent_node)
workflow.add_node("cluster_agent", cluster_agent_node)
workflow.add_node("supplier_agent", supplier_agent_node)
workflow.add_node("commit_agent", commit_agent_node)
workflow.add_node("ops_agent", ops_agent_node)
workflow.add_node("cash_agent", cash_agent_node)
workflow.add_node("learn_agent", learn_agent_node)

# Define Edges
workflow.add_edge("intake_agent", "cluster_agent")
workflow.add_edge("cluster_agent", "supplier_agent")
workflow.add_edge("supplier_agent", "commit_agent")
workflow.add_edge("commit_agent", "ops_agent")
workflow.add_edge("ops_agent", "cash_agent")
workflow.add_edge("cash_agent", "learn_agent")

# Set Entry and End Points
workflow.set_entry_point("intake_agent")
workflow.add_edge("learn_agent", END)

# Compile the Graph
app = workflow.compile()
