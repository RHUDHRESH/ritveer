"""
Commit Agent
Commits to orders, tracks production, manages timelines
Ensures artisans deliver on commitments
"""

from typing import Dict, Any, List
from datetime import datetime, timedelta
from .base_agent import BaseAgent, AgentState, AgentRole
from ..tools import (
    pdf_generator_tool,
    qrcode_generator_tool,
)


class CommitAgent(BaseAgent):
    """
    Commit Agent - Manages order commitments
    - Receives confirmed orders
    - Creates order contracts
    - Tracks production timeline
    - Manages quality checks
    - Handles delivery coordination
    """

    def __init__(self):
        super().__init__(
            role=AgentRole.COMMIT,
            name="CommitAgent",
            description="Commits to orders, tracks production, manages timelines"
        )
        # Register tools
        self.register_tool("pdf_generator")
        self.register_tool("qrcode_generator")

    async def think(self, state: AgentState) -> Dict[str, Any]:
        """
        Analyze order commitment:
        - Is production timeline realistic?
        - Do we have materials?
        - Do we have capacity?
        - What's the risk?
        """
        order_data = state.context.get("order_data", {})
        artisan_profile = state.context.get("artisan_profile", {})

        decision = {
            "action": "evaluate_commitment",
            "order_id": order_data.get("order_id"),
            "quantity": order_data.get("quantity", 0),
            "timeline_days": order_data.get("timeline_days", 30),
            "artisan_capacity": artisan_profile.get("production_capacity_units_per_month", 20),
            "risk_assessment": "low" if order_data.get("quantity", 0) <= 10 else "medium"
        }

        self.remember(f"order_{order_data.get('order_id')}_assessment", decision)

        return decision

    async def act(self, state: AgentState, decision: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute commitment actions:
        1. Create order contract (PDF)
        2. Generate tracking QR code
        3. Set up production timeline
        4. Create quality checklist
        """
        order_data = state.context.get("order_data", {})
        artisan_data = state.context.get("artisan_profile", {})

        order_id = order_data.get("order_id")
        artisan_name = artisan_data.get("name", "Unknown Artisan")
        customer_name = order_data.get("customer_name", "Customer")
        quantity = order_data.get("quantity", 1)
        amount = order_data.get("estimated_cost", 5000)

        results = {}

        # Action 1: Create order contract
        pdf_result = await pdf_generator_tool.execute(
            document_type="invoice",
            artisan_name=artisan_name,
            customer_name=customer_name,
            items=[{"name": order_data.get("description", "Custom Item"), "quantity": quantity}],
            amount=amount
        )
        results["contract_pdf"] = pdf_result.to_dict() if pdf_result.success else None

        # Action 2: Generate tracking QR code
        qr_result = await qrcode_generator_tool.execute(
            data=f"ORDER:{order_id}:TRACKING",
            qr_type="product"
        )
        results["tracking_qr"] = qr_result.to_dict() if qr_result.success else None

        # Action 3: Create production timeline
        timeline_days = decision.get("timeline_days", 30)
        today = datetime.utcnow()
        production_timeline = {
            "order_id": order_id,
            "start_date": today.isoformat(),
            "milestone_1": (today + timedelta(days=timeline_days//3)).isoformat(),  # 1/3 done
            "milestone_2": (today + timedelta(days=2*timeline_days//3)).isoformat(),  # 2/3 done
            "completion_date": (today + timedelta(days=timeline_days)).isoformat(),
            "phases": [
                "Material sourcing and preparation",
                "Active production",
                "Quality control and finishing",
                "Packaging and delivery readiness"
            ]
        }
        results["production_timeline"] = production_timeline

        # Action 4: Create quality checklist
        quality_checklist = {
            "order_id": order_id,
            "checklist": [
                "Materials match specifications",
                "Craftsmanship meets quality standards",
                "Dimensions and measurements correct",
                "Surface finish and appearance acceptable",
                "Packaging meets standards",
                "Delivery condition verified"
            ],
            "status": "pending"
        }
        results["quality_checklist"] = quality_checklist

        return {
            "action": "commit_to_order",
            "order_id": order_id,
            "commitment_status": "confirmed",
            "results": results
        }

    async def observe(self, state: AgentState, result: Dict[str, Any]) -> None:
        """
        Observe order commitment:
        - Store order tracking info
        - Set up monitoring
        - Prepare for handoff to operations
        """
        order_id = result.get("order_id")
        results = result.get("results", {})

        # Store order information
        self.remember(f"order_{order_id}_contract", results.get("contract_pdf"))
        self.remember(f"order_{order_id}_tracking", results.get("tracking_qr"))
        self.remember(f"order_{order_id}_timeline", results.get("production_timeline"))

        # Update state for operations
        state.context["order_committed"] = True
        state.context["order_id"] = order_id
        state.context["production_timeline"] = results.get("production_timeline")
        state.context["next_agent"] = "OpsAgent"

    async def update_production_status(self, order_id: str, status: str, completion_percentage: int) -> Dict[str, Any]:
        """
        Update production status for an order
        """
        update = {
            "order_id": order_id,
            "status": status,
            "completion_percentage": completion_percentage,
            "updated_at": datetime.utcnow().isoformat()
        }

        self.remember(f"order_{order_id}_status", update)

        return update

    async def verify_quality(self, order_id: str, checklist_results: Dict[str, bool]) -> Dict[str, Any]:
        """
        Verify quality against checklist
        """
        quality_result = {
            "order_id": order_id,
            "all_checks_passed": all(checklist_results.values()),
            "checks": checklist_results,
            "verified_at": datetime.utcnow().isoformat()
        }

        return quality_result
