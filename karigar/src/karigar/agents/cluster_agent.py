"""
Cluster Agent (ClusterAgent)
Clusters artisans for collaborative selling and bulk operations
Enables artisan communities and cooperative selling
"""

from typing import Dict, Any, List
from datetime import datetime
from .base_agent import BaseAgent, AgentState, AgentRole


class ClusterAgent(BaseAgent):
    """
    Cluster Agent - Manages artisan collaboration
    - Identifies similar artisans
    - Forms artisan clusters
    - Enables bulk selling
    - Coordinates collaborative projects
    - Manages shared resources
    """

    def __init__(self):
        super().__init__(
            role=AgentRole.CLUSTER,
            name="ClusterAgent",
            description="Clusters artisans for collaborative selling and bulk operations"
        )

    async def think(self, state: AgentState) -> Dict[str, Any]:
        """
        Analyze clustering opportunities:
        - Who are similar artisans?
        - What's the collaboration potential?
        - What are the synergies?
        - What can be shared?
        """
        artisan_id = state.artisan_id
        artisan_profile = state.context.get("artisan_profile", {})

        decision = {
            "action": "identify_cluster_opportunities",
            "artisan_id": artisan_id,
            "craft_type": artisan_profile.get("craft_type"),
            "location": artisan_profile.get("location"),
            "collaboration_readiness": "high",
            "potential_benefits": self._assess_collaboration_benefits(artisan_profile)
        }

        return decision

    async def act(self, state: AgentState, decision: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute clustering actions:
        1. Find similar artisans
        2. Assess compatibility
        3. Create cluster proposal
        4. Setup shared infrastructure
        """
        artisan_id = state.artisan_id
        craft_type = decision.get("craft_type")
        location = decision.get("location")

        results = {}

        # Step 1: Find similar artisans
        similar_artisans = self._find_similar_artisans(craft_type, location)
        results["similar_artisans"] = similar_artisans

        # Step 2: Assess compatibility
        compatibility_analysis = []
        for artisan in similar_artisans:
            compat = {
                "artisan": artisan.get("name"),
                "compatibility_score": 0.85,
                "synergies": [
                    "Complementary skill sets",
                    "Geographic proximity",
                    "Similar target market"
                ],
                "potential_collaboration": [
                    "Joint orders",
                    "Shared suppliers",
                    "Bulk marketing"
                ]
            }
            compatibility_analysis.append(compat)

        results["compatibility"] = compatibility_analysis

        # Step 3: Create cluster proposal
        cluster_proposal = {
            "cluster_name": f"{craft_type.title()} Cluster - {location}",
            "members": [artisan_id] + [a.get("id") for a in similar_artisans[:3]],
            "cluster_type": "craft_based",
            "goals": [
                "Bulk purchasing for better rates",
                "Collective marketing",
                "Shared workspace/equipment",
                "Joint order fulfillment",
                "Knowledge sharing"
            ],
            "expected_benefits": {
                "cost_reduction": "15-20%",
                "revenue_increase": "25-30%",
                "efficiency_gain": "20%"
            },
            "proposed_structure": {
                "governance": "Democratic cooperative",
                "profit_sharing": "Based on contribution",
                "decision_making": "Consensus with majority override",
                "membership_fee": "500/month per artisan"
            }
        }
        results["cluster_proposal"] = cluster_proposal

        # Step 4: Setup shared infrastructure
        shared_resources = {
            "cluster_name": cluster_proposal.get("cluster_name"),
            "resources": [
                {
                    "resource": "Raw Material Warehouse",
                    "location": location,
                    "capacity": "1000 units",
                    "cost_per_artisan": "2000/month",
                    "status": "proposed"
                },
                {
                    "resource": "Shared Workshop",
                    "location": location,
                    "capacity": "10 artisans",
                    "cost_per_artisan": "5000/month",
                    "status": "proposed"
                },
                {
                    "resource": "Marketing Fund",
                    "budget": "50000/month",
                    "allocation": "Equal share",
                    "status": "proposed"
                },
                {
                    "resource": "Quality Lab",
                    "location": location,
                    "cost_per_artisan": "1000/month",
                    "status": "proposed"
                }
            ]
        }
        results["shared_resources"] = shared_resources

        # Step 5: Bulk selling strategy
        bulk_selling = {
            "bulk_order_capacity": self._calculate_cluster_capacity(similar_artisans),
            "large_buyer_targets": [
                "Hotels and Resorts",
                "Corporate Gifting Agencies",
                "Export Companies",
                "Government Agencies"
            ],
            "minimum_bulk_order": 100,
            "bulk_discount_structure": {
                "100_250": "5% discount",
                "250_500": "10% discount",
                "500_plus": "15% discount"
            },
            "estimated_monthly_bulk_orders": 5,
            "estimated_additional_revenue": 500000
        }
        results["bulk_selling"] = bulk_selling

        return {
            "action": "create_cluster",
            "artisan_id": artisan_id,
            "status": "cluster_proposal_created",
            "results": results
        }

    async def observe(self, state: AgentState, result: Dict[str, Any]) -> None:
        """
        Observe clustering outcomes:
        - Store cluster information
        - Remember opportunities
        - Track collaboration potential
        """
        artisan_id = state.artisan_id
        results = result.get("results", {})

        # Store cluster information
        self.remember(f"artisan_{artisan_id}_cluster", results.get("cluster_proposal"))
        self.remember(f"artisan_{artisan_id}_collaborators", results.get("similar_artisans"))
        self.remember(f"artisan_{artisan_id}_shared_resources", results.get("shared_resources"))

        # Update state
        state.context["cluster_proposal_created"] = True
        state.context["cluster_proposal"] = results.get("cluster_proposal")
        state.context["collaboration_opportunities"] = results.get("compatibility")

    def _find_similar_artisans(self, craft_type: str, location: str) -> List[Dict]:
        """
        Find artisans with similar craft and location
        """
        artisans = [
            {
                "id": "artisan_001",
                "name": "Arjun Sharma",
                "craft_type": craft_type,
                "location": location,
                "experience": 10,
                "rating": 4.5
            },
            {
                "id": "artisan_002",
                "name": "Meera Singh",
                "craft_type": craft_type,
                "location": location,
                "experience": 8,
                "rating": 4.3
            },
            {
                "id": "artisan_003",
                "name": "Raj Kumar",
                "craft_type": craft_type,
                "location": location,
                "experience": 12,
                "rating": 4.7
            }
        ]

        return artisans

    def _assess_collaboration_benefits(self, artisan_profile: Dict) -> List[str]:
        """
        Assess what benefits collaboration would bring
        """
        benefits = [
            "Reduced material costs through bulk purchasing",
            "Access to larger orders and bulk contracts",
            "Shared marketing and brand building",
            "Knowledge and skill sharing",
            "Access to shared equipment and workspace",
            "Stronger negotiating power with suppliers",
            "Collective quality assurance",
            "Risk distribution across cluster members"
        ]

        return benefits

    def _calculate_cluster_capacity(self, artisans: List[Dict]) -> int:
        """
        Calculate total production capacity of cluster
        """
        capacity_per_artisan = 20  # Units per month
        return (len(artisans) + 1) * capacity_per_artisan  # +1 for primary artisan

    async def propose_collaborative_project(self, project_details: Dict) -> Dict[str, Any]:
        """
        Propose a collaborative project for cluster
        """
        proposal = {
            "project_id": f"proj_{datetime.utcnow().timestamp()}",
            "name": project_details.get("name"),
            "description": project_details.get("description"),
            "participating_artisans": project_details.get("artisan_ids", []),
            "target_outcome": project_details.get("target"),
            "timeline": "3 months",
            "expected_roi": "40%",
            "status": "proposed"
        }

        return proposal

    async def manage_cluster_finances(self, cluster_name: str) -> Dict[str, Any]:
        """
        Manage finances for a cluster
        """
        finances = {
            "cluster_name": cluster_name,
            "member_count": 5,
            "total_monthly_revenue": 500000,
            "total_monthly_costs": 150000,
            "monthly_profit": 350000,
            "profit_per_member": 70000,
            "reserve_fund": 100000,
            "status": "healthy"
        }

        return finances

    async def coordinate_bulk_order(self, order_details: Dict) -> Dict[str, Any]:
        """
        Coordinate fulfillment of a bulk order across cluster
        """
        coordination = {
            "order_id": order_details.get("order_id"),
            "total_quantity": order_details.get("quantity", 0),
            "allocation": self._allocate_cluster_capacity(
                order_details.get("quantity", 0),
                order_details.get("artisan_ids", [])
            ),
            "timeline": "21 days",
            "quality_standard": "premium",
            "coordination_manager": "ClusterAgent",
            "status": "coordinating"
        }

        return coordination

    def _allocate_cluster_capacity(self, quantity: int, artisan_ids: List[str]) -> List[Dict]:
        """
        Allocate bulk order across cluster members
        """
        per_artisan = quantity // len(artisan_ids) if artisan_ids else quantity
        remainder = quantity % len(artisan_ids) if artisan_ids else 0

        allocation = []
        for i, artisan_id in enumerate(artisan_ids):
            qty = per_artisan + (1 if i == 0 else 0) if remainder > 0 else per_artisan
            allocation.append({
                "artisan_id": artisan_id,
                "quantity": qty,
                "deadline": "Day 21"
            })

        return allocation

    async def provide_cluster_support(self, artisan_id: str, support_type: str) -> Dict[str, Any]:
        """
        Provide support services through cluster
        """
        support = {
            "artisan_id": artisan_id,
            "support_type": support_type,
            "services": [
                "Technical mentoring",
                "Market access",
                "Financial assistance",
                "Equipment sharing",
                "Quality support"
            ],
            "status": "available"
        }

        return support
