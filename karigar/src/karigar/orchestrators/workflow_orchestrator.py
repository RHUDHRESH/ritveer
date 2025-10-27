"""
Workflow Orchestrator - LangGraph Integration
Coordinates multi-agent workflows for artisans
"""

from typing import Dict, List, Any, Optional
from datetime import datetime
from enum import Enum
from ..agents import (
    AgentState,
    AgentOrchestrator,
    IntakeAgent,
    SupplierAgent,
    CommitAgent,
    SalesAgent,
)


class WorkflowType(str, Enum):
    """Types of workflows supported"""
    ARTISAN_ONBOARDING = "artisan_onboarding"  # Intake -> Supplier
    ORDER_FULFILLMENT = "order_fulfillment"  # Commit -> Supplier
    SALES_ACTIVATION = "sales_activation"  # Sales -> Supplier -> Commit
    COMPLETE_JOURNEY = "complete_journey"  # All agents in sequence


class WorkflowState(str, Enum):
    """Workflow execution state"""
    INITIALIZED = "initialized"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"


class WorkflowOrchestrator:
    """
    Orchestrates multi-agent workflows using LangGraph concepts
    Manages agent coordination and state flow
    """

    def __init__(self):
        self.orchestrator = AgentOrchestrator()
        self.workflows: Dict[str, Dict[str, Any]] = {}
        self.workflow_definitions: Dict[WorkflowType, List[str]] = {
            WorkflowType.ARTISAN_ONBOARDING: [
                "IntakeAgent",
                "SupplierAgent",
            ],
            WorkflowType.ORDER_FULFILLMENT: [
                "CommitAgent",
                "SupplierAgent",
            ],
            WorkflowType.SALES_ACTIVATION: [
                "SalesAgent",
                "SupplierAgent",
                "CommitAgent",
            ],
            WorkflowType.COMPLETE_JOURNEY: [
                "IntakeAgent",
                "SalesAgent",
                "SupplierAgent",
                "CommitAgent",
            ],
        }

        # Initialize agents
        self._initialize_agents()

    def _initialize_agents(self):
        """Initialize all agent instances"""
        intake_agent = IntakeAgent()
        supplier_agent = SupplierAgent()
        commit_agent = CommitAgent()
        sales_agent = SalesAgent()

        self.orchestrator.register_agent(intake_agent)
        self.orchestrator.register_agent(supplier_agent)
        self.orchestrator.register_agent(commit_agent)
        self.orchestrator.register_agent(sales_agent)

    async def execute_workflow(
        self,
        workflow_type: WorkflowType,
        artisan_id: str,
        session_id: str,
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Execute a complete workflow
        """
        # Create initial agent state
        agent_state = AgentState(
            agent_id="orchestrator",
            agent_role=None,
            session_id=session_id,
            artisan_id=artisan_id,
            context=context
        )

        # Get workflow agents
        agent_sequence = self.workflow_definitions.get(workflow_type, [])

        if not agent_sequence:
            raise ValueError(f"Unknown workflow type: {workflow_type}")

        # Store workflow info
        workflow_id = f"wf_{datetime.utcnow().timestamp()}"
        self.workflows[workflow_id] = {
            "id": workflow_id,
            "type": workflow_type,
            "artisan_id": artisan_id,
            "session_id": session_id,
            "state": WorkflowState.IN_PROGRESS,
            "agents": agent_sequence,
            "started_at": datetime.utcnow(),
            "completed_at": None,
            "results": None
        }

        try:
            # Execute workflow
            final_state = await self.orchestrator.execute_workflow(
                initial_state=agent_state,
                agent_sequence=agent_sequence
            )

            # Mark workflow as complete
            self.workflows[workflow_id]["state"] = WorkflowState.COMPLETED
            self.workflows[workflow_id]["completed_at"] = datetime.utcnow()
            self.workflows[workflow_id]["results"] = final_state

            return {
                "workflow_id": workflow_id,
                "status": "completed",
                "artisan_id": artisan_id,
                "context": final_state.context,
                "history": final_state.history,
                "decisions": final_state.decisions,
                "execution_summary": self.orchestrator.get_execution_summary()
            }

        except Exception as e:
            # Mark workflow as failed
            self.workflows[workflow_id]["state"] = WorkflowState.FAILED
            self.workflows[workflow_id]["error"] = str(e)

            return {
                "workflow_id": workflow_id,
                "status": "failed",
                "error": str(e),
                "artisan_id": artisan_id
            }

    def get_workflow_status(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        """Get status of a workflow"""
        return self.workflows.get(workflow_id)

    def get_artisan_workflows(self, artisan_id: str) -> List[Dict[str, Any]]:
        """Get all workflows for an artisan"""
        return [
            wf for wf in self.workflows.values()
            if wf["artisan_id"] == artisan_id
        ]

    async def onboard_artisan(self, artisan_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Complete artisan onboarding workflow
        Artisan -> Supplier Search -> Sales Setup
        """
        return await self.execute_workflow(
            workflow_type=WorkflowType.ARTISAN_ONBOARDING,
            artisan_id=artisan_data.get("id"),
            session_id=f"onboard_{datetime.utcnow().timestamp()}",
            context={"artisan_data": artisan_data}
        )

    async def fulfill_order(self, order_data: Dict[str, Any], artisan_id: str) -> Dict[str, Any]:
        """
        Complete order fulfillment workflow
        Commit Order -> Source Materials -> Deliver
        """
        return await self.execute_workflow(
            workflow_type=WorkflowType.ORDER_FULFILLMENT,
            artisan_id=artisan_id,
            session_id=f"order_{order_data.get('order_id')}",
            context={"order_data": order_data}
        )

    async def activate_sales(self, artisan_id: str, product_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Complete sales activation workflow
        Market Products -> Source Materials -> Commit Production
        """
        return await self.execute_workflow(
            workflow_type=WorkflowType.SALES_ACTIVATION,
            artisan_id=artisan_id,
            session_id=f"sales_{datetime.utcnow().timestamp()}",
            context={"product_data": product_data}
        )

    def list_workflow_types(self) -> List[Dict[str, Any]]:
        """List all available workflow types"""
        return [
            {
                "type": wf_type.value,
                "agents": agents,
                "description": self._get_workflow_description(wf_type)
            }
            for wf_type, agents in self.workflow_definitions.items()
        ]

    def _get_workflow_description(self, workflow_type: WorkflowType) -> str:
        """Get description of workflow"""
        descriptions = {
            WorkflowType.ARTISAN_ONBOARDING: "Onboard new artisan with market analysis",
            WorkflowType.ORDER_FULFILLMENT: "Fulfill customer order from sourcing to delivery",
            WorkflowType.SALES_ACTIVATION: "Activate sales channel with product setup",
            WorkflowType.COMPLETE_JOURNEY: "Complete artisan journey from onboarding to sales",
        }
        return descriptions.get(workflow_type, "Unknown workflow")


# Global orchestrator instance
workflow_orchestrator = WorkflowOrchestrator()
