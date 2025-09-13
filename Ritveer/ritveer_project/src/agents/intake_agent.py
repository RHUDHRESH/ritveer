from typing import Any, Dict, List, Optional
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from src.graph.state import RitveerState
from config.settings import settings
from src.graph.workflow import fast_llm # Assuming fast_llm is defined in workflow.py

# Define the JSON schema for the extracted entities
# This schema will be used by the LLM to format its output
EXTRACTION_SCHEMA = {
    "type": "object",
    "properties": {
        "item": {"type": "string", "description": "The item the user is requesting."},
        "quantity": {"type": "integer", "description": "The quantity of the item."},
        "budget": {"type": "number", "description": "The budget for the item."},
        "location": {"type": "string", "description": "The delivery location."},
        "urgency": {"type": "string", "description": "The urgency of the request (e.g., 'urgent', 'normal')."},
    },
    "required": ["item", "quantity"],
}

# Craft a system prompt for the fast LLM
intake_agent_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You are an order-intake specialist. Your task is to carefully read the user\'s message "
            "and extract key entities into a strict JSON schema. "
            "If a field is not explicitly mentioned, infer it if possible, otherwise omit it. "
            "The JSON schema is as follows:\n"
            f"{EXTRACTION_SCHEMA}\n"
            "Ensure your output is a valid JSON object that conforms to the schema."
        ),
        ("human", "{initial_query}"),
    ]
)

# Create the chain for the intake agent
intake_agent_chain = intake_agent_prompt | fast_llm | JsonOutputParser()

def intake_agent_node(state: RitveerState) -> Dict[str, Any]:
    """
    The intake agent node processes the initial query, extracts key entities,
    and updates the normalized_request in the state.
    """
    print("---INTAKE AGENT: Processing initial query---")
    initial_query = state["initial_query"]
    
    # Invoke the intake agent chain to extract entities
    extracted_data = intake_agent_chain.invoke({"initial_query": initial_query})
    
    # Update the state with the normalized request
    return {"normalized_request": extracted_data}