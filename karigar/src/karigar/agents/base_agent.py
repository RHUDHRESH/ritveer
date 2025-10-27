"""
Base Agent Class
Foundation for all specialized agents in KARIGAR
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum
import uuid


class AgentRole(str, Enum):
    """Agent role types"""
    INTAKE = "intake"  # Onboard artisans
    SUPPLIER = "supplier"  # Find suppliers and negotiate
    COMMIT = "commit"  # Commit orders and track
    SALES = "sales"  # Sell products and orders
    OPS = "ops"  # Operations and production
    CASH = "cash"  # Financial management
    LEARN = "learn"  # Learn and improve
    CLUSTER = "cluster"  # Cluster artisans and collaborative selling


@dataclass
class AgentState:
    """State maintained by agent during execution"""
    agent_id: str
    agent_role: AgentRole
    session_id: str
    artisan_id: str
    context: Dict[str, Any] = field(default_factory=dict)
    history: List[Dict[str, Any]] = field(default_factory=list)
    decisions: List[Dict[str, Any]] = field(default_factory=list)
    started_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class AgentMessage:
    """Message passed between agents"""
    sender: str
    recipient: str
    message_type: str  # request, response, notification
    content: Dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.utcnow)


class BaseAgent(ABC):
    """Base class for all agents"""

    def __init__(self, role: AgentRole, name: str, description: str):
        self.agent_id = f"agent_{uuid.uuid4().hex[:8]}"
        self.role = role
        self.name = name
        self.description = description
        self.tools: List[str] = []
        self.memory: Dict[str, Any] = {}

    @abstractmethod
    async def think(self, state: AgentState) -> Dict[str, Any]:
        """
        Main thinking process for the agent
        Analyzes state and makes decisions
        """
        pass

    @abstractmethod
    async def act(self, state: AgentState, decision: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute actions based on decisions
        Uses tools and updates state
        """
        pass

    @abstractmethod
    async def observe(self, state: AgentState, result: Dict[str, Any]) -> None:
        """
        Observe results of actions
        Update memory and state
        """
        pass

    async def execute(self, state: AgentState) -> AgentState:
        """
        Main execution loop: Think -> Act -> Observe
        """
        # Phase 1: Think - analyze situation
        decision = await self.think(state)
        state.decisions.append({
            "agent": self.name,
            "decision": decision,
            "timestamp": datetime.utcnow().isoformat()
        })

        # Phase 2: Act - execute decision
        result = await self.act(state, decision)
        state.history.append({
            "agent": self.name,
            "action": result,
            "timestamp": datetime.utcnow().isoformat()
        })

        # Phase 3: Observe - process results
        await self.observe(state, result)

        # Update state
        state.updated_at = datetime.utcnow()

        return state

    def register_tool(self, tool_name: str) -> None:
        """Register a tool this agent can use"""
        if tool_name not in self.tools:
            self.tools.append(tool_name)

    def get_schema(self) -> Dict:
        """Return schema for this agent"""
        return {
            "agent_id": self.agent_id,
            "name": self.name,
            "role": self.role.value,
            "description": self.description,
            "tools": self.tools
        }

    def remember(self, key: str, value: Any) -> None:
        """Store information in agent memory"""
        self.memory[key] = {
            "value": value,
            "timestamp": datetime.utcnow()
        }

    def recall(self, key: str) -> Optional[Any]:
        """Retrieve information from agent memory"""
        if key in self.memory:
            return self.memory[key].get("value")
        return None

    async def send_message(self, recipient: str, message_type: str, content: Dict) -> AgentMessage:
        """Send message to another agent"""
        return AgentMessage(
            sender=self.name,
            recipient=recipient,
            message_type=message_type,
            content=content
        )


class AgentFactory:
    """Factory for creating agents"""

    agents_registry: Dict[AgentRole, type] = {}

    @classmethod
    def register_agent(cls, role: AgentRole, agent_class: type):
        """Register an agent class"""
        cls.agents_registry[role] = agent_class

    @classmethod
    async def create_agent(cls, role: AgentRole, name: str, description: str) -> BaseAgent:
        """Create an agent instance"""
        agent_class = cls.agents_registry.get(role)
        if not agent_class:
            raise ValueError(f"No agent registered for role: {role}")
        return agent_class(role, name, description)

    @classmethod
    def list_agents(cls) -> List[AgentRole]:
        """List all available agents"""
        return list(cls.agents_registry.keys())


class AgentOrchestrator:
    """Manages multiple agents and coordinates their work"""

    def __init__(self):
        self.agents: Dict[str, BaseAgent] = {}
        self.message_queue: List[AgentMessage] = []
        self.execution_history: List[Dict] = []

    def register_agent(self, agent: BaseAgent) -> None:
        """Register an agent"""
        self.agents[agent.name] = agent

    async def execute_workflow(self, initial_state: AgentState, agent_sequence: List[str]) -> AgentState:
        """
        Execute agents in sequence
        Each agent receives state from previous agent
        """
        current_state = initial_state

        for agent_name in agent_sequence:
            if agent_name not in self.agents:
                raise ValueError(f"Agent '{agent_name}' not found")

            agent = self.agents[agent_name]
            current_state = await agent.execute(current_state)

            self.execution_history.append({
                "agent": agent_name,
                "state": current_state,
                "timestamp": datetime.utcnow().isoformat()
            })

        return current_state

    def get_execution_summary(self) -> Dict:
        """Get summary of execution"""
        return {
            "total_steps": len(self.execution_history),
            "agents_executed": [step["agent"] for step in self.execution_history],
            "history": self.execution_history
        }
