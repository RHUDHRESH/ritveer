"""
KARIGAR Agents Module
All 8 specialized agents that work together to serve artisans
"""

from .base_agent import (
    BaseAgent,
    AgentRole,
    AgentState,
    AgentMessage,
    AgentFactory,
    AgentOrchestrator,
)
from .intake_agent import IntakeAgent
from .supplier_agent import SupplierAgent
from .commit_agent import CommitAgent
from .sales_agent import SalesAgent
from .ops_agent import OpsAgent
from .cash_agent import CashAgent
from .learn_agent import LearnAgent
from .cluster_agent import ClusterAgent


# Register all agents with the factory
def register_agents():
    """Register all 8 agent types"""
    AgentFactory.register_agent(AgentRole.INTAKE, IntakeAgent)
    AgentFactory.register_agent(AgentRole.SUPPLIER, SupplierAgent)
    AgentFactory.register_agent(AgentRole.COMMIT, CommitAgent)
    AgentFactory.register_agent(AgentRole.SALES, SalesAgent)
    AgentFactory.register_agent(AgentRole.OPS, OpsAgent)
    AgentFactory.register_agent(AgentRole.CASH, CashAgent)
    AgentFactory.register_agent(AgentRole.LEARN, LearnAgent)
    AgentFactory.register_agent(AgentRole.CLUSTER, ClusterAgent)


# Auto-register agents on import
register_agents()

__all__ = [
    "BaseAgent",
    "AgentRole",
    "AgentState",
    "AgentMessage",
    "AgentFactory",
    "AgentOrchestrator",
    "IntakeAgent",
    "SupplierAgent",
    "CommitAgent",
    "SalesAgent",
    "OpsAgent",
    "CashAgent",
    "LearnAgent",
    "ClusterAgent",
    "register_agents",
]
