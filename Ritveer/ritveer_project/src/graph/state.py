from typing import List, Tuple, Annotated, TypedDict, Optional, Any
from langchain_core.messages import BaseMessage


class RitveerState(TypedDict):
    """
    Represents the state of our graph. It contains the following:

    - `initial_query`: The initial query from the user, which is often a question or task.
    - `chat_history`: A list of all messages in the current conversation.
    - `current_agent_name`: The name of the agent currently responsible for responding.
    - `tool_code`: Any code that the current agent wants to execute.
    - `tool_output`: The output of any tool code that was executed.
    - `parsed_tool_output`: The parsed output of any tool code that was executed.
    - `error`: Any error message that occurred during the execution.
    - `return_direct_response`: A flag to indicate if the agent should return a direct response.
    - `final_answer`: The final answer to the user's query.

    # --- NEW FIELDS FOR PHASE 1 --- #
    raw_message: str
    normalized_request: Optional[dict[str, Any]]
    artisan_clusters: Optional[List[dict[str, Any]]]
    supplier_quotes: Optional[List[dict[str, Any]]]
    final_order: Optional[dict[str, Any]]
    shipping_label_url: Optional[str]
    """
    initial_query: str
    chat_history: List[BaseMessage]
    current_agent_name: str
    tool_code: str
    tool_output: str
    parsed_tool_output: str
    error: str
    return_direct_response: bool
    final_answer: str

    # --- NEW FIELDS FOR PHASE 1 --- #
    raw_message: str
    normalized_request: Optional[dict[str, Any]]
    artisan_clusters: Optional[List[dict[str, Any]]]
    supplier_quotes: Optional[List[dict[str, Any]]]
    final_order: Optional[dict[str, Any]]
    shipping_label_url: Optional[str]
