"""
Operations Agent (OpsAgent)
Manages production operations, quality control, and logistics
Ensures smooth production and timely delivery
"""

from typing import Dict, Any, List
from datetime import datetime, timedelta
from .base_agent import BaseAgent, AgentState, AgentRole
from ..tools import report_generator_tool


class OpsAgent(BaseAgent):
    """
    Operations Agent - Manages production and delivery
    - Tracks production progress
    - Manages quality control
    - Coordinates logistics
    - Optimizes production schedule
    - Handles supplier coordination
    """

    def __init__(self):
        super().__init__(
            role=AgentRole.OPS,
            name="OpsAgent",
            description="Manages production operations, quality control, and logistics"
        )
        # Register tools
        self.register_tool("report_generator")

    async def think(self, state: AgentState) -> Dict[str, Any]:
        """
        Analyze production requirements:
        - What's the production timeline?
        - What resources are needed?
        - What are the bottlenecks?
        - What's the quality standard?
        """
        order_data = state.context.get("order_data", {})
        production_timeline = state.context.get("production_timeline", {})
        artisan_profile = state.context.get("artisan_profile", {})

        decision = {
            "action": "optimize_production",
            "order_id": order_data.get("order_id"),
            "timeline_days": production_timeline.get("completion_date"),
            "production_capacity": artisan_profile.get("production_capacity_units_per_month", 20),
            "quality_standard": "premium",
            "resource_requirements": self._analyze_resource_needs(order_data)
        }

        self.remember(f"order_{order_data.get('order_id')}_production_plan", decision)

        return decision

    async def act(self, state: AgentState, decision: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute production operations:
        1. Create detailed production schedule
        2. Allocate resources
        3. Setup quality checkpoints
        4. Coordinate with suppliers
        5. Plan logistics
        """
        order_id = decision.get("order_id")
        timeline_days = decision.get("timeline_days")

        # Parse completion date if it's a string
        if isinstance(timeline_days, str):
            try:
                timeline_date = datetime.fromisoformat(timeline_days)
                days_available = (timeline_date - datetime.utcnow()).days
            except:
                days_available = 21  # Default
        else:
            days_available = 21

        results = {}

        # Step 1: Create detailed production schedule
        production_schedule = {
            "order_id": order_id,
            "phases": [
                {
                    "phase": "Material Preparation",
                    "duration_days": max(1, days_available // 4),
                    "start_date": (datetime.utcnow()).isoformat(),
                    "end_date": (datetime.utcnow() + timedelta(days=days_available // 4)).isoformat(),
                    "tasks": [
                        "Source and inspect materials",
                        "Prepare workspace",
                        "Test material quality",
                    ]
                },
                {
                    "phase": "Active Production",
                    "duration_days": max(1, days_available // 2),
                    "start_date": (datetime.utcnow() + timedelta(days=days_available // 4)).isoformat(),
                    "end_date": (datetime.utcnow() + timedelta(days=3 * days_available // 4)).isoformat(),
                    "tasks": [
                        "Craft products",
                        "Quality checks",
                        "Refinements",
                    ]
                },
                {
                    "phase": "Finishing & QC",
                    "duration_days": max(1, days_available // 4),
                    "start_date": (datetime.utcnow() + timedelta(days=3 * days_available // 4)).isoformat(),
                    "end_date": (datetime.utcnow() + timedelta(days=days_available)).isoformat(),
                    "tasks": [
                        "Final quality check",
                        "Packaging",
                        "Delivery preparation",
                    ]
                }
            ]
        }
        results["production_schedule"] = production_schedule

        # Step 2: Allocate resources
        resources = {
            "order_id": order_id,
            "materials": [
                {"name": "Primary material", "allocated": True, "supplier": "TBD"},
                {"name": "Tools & equipment", "allocated": True, "status": "ready"},
                {"name": "Packaging", "allocated": True, "status": "ordered"},
            ],
            "labor": {
                "artisan": "Primary",
                "hours_estimated": days_available * 8,
                "assistants_needed": 0 if days_available >= 21 else 1,
            }
        }
        results["resources"] = resources

        # Step 3: Setup quality checkpoints
        quality_checkpoints = {
            "order_id": order_id,
            "checkpoints": [
                {
                    "checkpoint": "Material Quality",
                    "timing": "Day 1",
                    "responsibility": "Artisan",
                    "criteria": ["Material meets spec", "No defects"],
                    "status": "pending"
                },
                {
                    "checkpoint": "Mid-production Review",
                    "timing": f"Day {days_available // 2}",
                    "responsibility": "Artisan",
                    "criteria": ["Progress on track", "Quality maintains"],
                    "status": "pending"
                },
                {
                    "checkpoint": "Final Quality Check",
                    "timing": f"Day {days_available}",
                    "responsibility": "Artisan",
                    "criteria": [
                        "All items completed",
                        "Meets quality standards",
                        "Packaging approved"
                    ],
                    "status": "pending"
                }
            ]
        }
        results["quality_checkpoints"] = quality_checkpoints

        # Step 4: Generate operations report
        report = await report_generator_tool.execute(
            report_type="production",
            artisan_id=state.artisan_id,
            period="project"
        )
        if report.success:
            results["operations_report"] = report.data

        # Step 5: Create logistics plan
        logistics = {
            "order_id": order_id,
            "pickup_date": (datetime.utcnow() + timedelta(days=days_available)).isoformat(),
            "delivery_location": "TBD",
            "packaging_requirements": [
                "Secure packaging",
                "Branded packing slip",
                "QR code tracking",
            ],
            "shipping_options": [
                {"method": "Courier", "estimated_days": 3, "cost": "TBD"},
                {"method": "Local pickup", "estimated_days": 0, "cost": "Free"},
            ]
        }
        results["logistics"] = logistics

        return {
            "action": "manage_production",
            "order_id": order_id,
            "status": "production_planned",
            "results": results
        }

    async def observe(self, state: AgentState, result: Dict[str, Any]) -> None:
        """
        Observe production planning:
        - Store production schedule
        - Remember quality requirements
        - Track resources
        - Prepare for execution
        """
        order_id = result.get("order_id")
        results = result.get("results", {})

        # Store production information
        self.remember(f"order_{order_id}_schedule", results.get("production_schedule"))
        self.remember(f"order_{order_id}_resources", results.get("resources"))
        self.remember(f"order_{order_id}_quality", results.get("quality_checkpoints"))

        # Update state for monitoring
        state.context["production_planned"] = True
        state.context["production_schedule"] = results.get("production_schedule")
        state.context["quality_checkpoints"] = results.get("quality_checkpoints")
        state.context["next_action"] = "start_production"

    def _analyze_resource_needs(self, order_data: Dict) -> List[Dict]:
        """
        Analyze resource requirements based on order
        """
        quantity = order_data.get("quantity", 1)

        resources = [
            {
                "type": "materials",
                "quantity": quantity,
                "status": "to_be_sourced"
            },
            {
                "type": "labor",
                "hours": quantity * 8,
                "status": "allocated"
            },
            {
                "type": "packaging",
                "units": quantity,
                "status": "to_be_ordered"
            }
        ]

        return resources

    async def update_production_status(self, order_id: str, phase: str, completion: int) -> Dict[str, Any]:
        """
        Update production progress
        """
        update = {
            "order_id": order_id,
            "current_phase": phase,
            "completion_percentage": completion,
            "updated_at": datetime.utcnow().isoformat()
        }

        self.remember(f"order_{order_id}_progress", update)

        return update

    async def report_quality_issue(self, order_id: str, issue: str) -> Dict[str, Any]:
        """
        Report quality issues during production
        """
        issue_report = {
            "order_id": order_id,
            "issue": issue,
            "severity": "medium",
            "reported_at": datetime.utcnow().isoformat(),
            "status": "open"
        }

        return issue_report

    async def confirm_ready_for_shipping(self, order_id: str) -> Dict[str, Any]:
        """
        Confirm production complete and ready for shipping
        """
        confirmation = {
            "order_id": order_id,
            "production_status": "complete",
            "quality_checks_passed": True,
            "ready_for_shipping": True,
            "confirmed_at": datetime.utcnow().isoformat()
        }

        return confirmation
