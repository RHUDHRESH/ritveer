"""
Supplier Agent
Finds suppliers, negotiates quotes, validates supplier credibility
Handles material sourcing for artisans
"""

from typing import Dict, Any, List
from datetime import datetime
from .base_agent import BaseAgent, AgentState, AgentRole
from ..tools import (
    supplier_search_tool,
    quote_generator_tool,
    supplier_validation_tool,
)


class SupplierAgent(BaseAgent):
    """
    Supplier Agent - Finds and manages suppliers
    - Searches for suppliers of materials
    - Negotiates quotes
    - Validates supplier credibility
    - Maintains supplier relationships
    """

    def __init__(self):
        super().__init__(
            role=AgentRole.SUPPLIER,
            name="SupplierAgent",
            description="Finds suppliers, negotiates quotes, validates supplier credibility"
        )
        # Register tools
        self.register_tool("supplier_search")
        self.register_tool("quote_generator")
        self.register_tool("supplier_validation")

    async def think(self, state: AgentState) -> Dict[str, Any]:
        """
        Analyze artisan's material needs:
        - What materials are needed?
        - What quantities?
        - What budget?
        - What timeline?
        """
        artisan_profile = state.context.get("artisan_profile", {})
        craft_type = artisan_profile.get("craft_type")
        location = artisan_profile.get("location")

        # Get material requirements from context
        material_needs = state.context.get("material_needs", {})

        decision = {
            "action": "find_suppliers",
            "craft_type": craft_type,
            "location": location,
            "materials": material_needs,
            "priority": "cost_optimization"  # Could be: cost_optimization, speed, quality
        }

        self.remember(f"artisan_{state.artisan_id}_strategy", decision)

        return decision

    async def act(self, state: AgentState, decision: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute supplier actions:
        1. Search for suppliers
        2. Get quotes
        3. Validate suppliers
        4. Compare options
        """
        craft_type = decision.get("craft_type")
        location = decision.get("location")
        materials = decision.get("materials", {})

        supplier_results = {
            "suppliers_found": [],
            "quotes_received": [],
            "validated_suppliers": []
        }

        # For each material needed
        for material_name, material_info in materials.items():
            quantity = material_info.get("quantity", 10)

            # Step 1: Search for suppliers
            search_result = await supplier_search_tool.execute(
                material_name=material_name,
                location=location,
                quantity=quantity
            )

            if search_result.success:
                suppliers = search_result.data or []
                supplier_results["suppliers_found"].extend(suppliers)

                # Step 2: Get quotes from each supplier
                for supplier in suppliers[:2]:  # Top 2 suppliers
                    quote_result = await quote_generator_tool.execute(
                        supplier_name=supplier.get("name"),
                        material_name=material_name,
                        quantity=quantity,
                        unit=material_info.get("unit", "kg")
                    )

                    if quote_result.success:
                        supplier_results["quotes_received"].append(quote_result.data)

                        # Step 3: Validate supplier
                        validation_result = await supplier_validation_tool.execute(
                            supplier_name=supplier.get("name")
                        )

                        if validation_result.success:
                            supplier_results["validated_suppliers"].append({
                                "supplier": supplier.get("name"),
                                "validation": validation_result.data,
                                "quote": quote_result.data
                            })

        return {
            "action": "complete_supplier_search",
            "artisan_id": state.artisan_id,
            "supplier_results": supplier_results,
            "best_quote": self._select_best_quote(supplier_results["quotes_received"])
        }

    async def observe(self, state: AgentState, result: Dict[str, Any]) -> None:
        """
        Observe supplier search results:
        - Store supplier information
        - Remember best quotes
        - Prepare for procurement
        """
        artisan_id = state.artisan_id
        supplier_results = result.get("supplier_results", {})
        best_quote = result.get("best_quote", {})

        # Store supplier information in memory
        self.remember(f"artisan_{artisan_id}_suppliers", supplier_results)
        self.remember(f"artisan_{artisan_id}_best_quote", best_quote)

        # Update state with supplier information
        state.context["suppliers_identified"] = True
        state.context["supplier_results"] = supplier_results
        state.context["best_quote"] = best_quote
        state.context["next_action"] = "commit_order"

    def _select_best_quote(self, quotes: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Select the best quote based on:
        - Price
        - Delivery time
        - Supplier credibility
        """
        if not quotes:
            return {}

        # Simple scoring: lower total_price is better
        best = min(quotes, key=lambda q: q.get("total_price", float("inf")))
        return best

    async def negotiate_supplier(self, supplier_name: str, desired_price: float) -> Dict[str, Any]:
        """
        Negotiate with supplier for better terms
        """
        negotiation = {
            "supplier": supplier_name,
            "desired_price": desired_price,
            "status": "requested",
            "estimated_response_time": "24 hours"
        }

        return negotiation
