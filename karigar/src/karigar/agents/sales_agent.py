"""
Sales Agent
Markets artisan products, finds customers, processes orders
Drives revenue for artisans
"""

from typing import Dict, Any, List
from datetime import datetime
from .base_agent import BaseAgent, AgentState, AgentRole
from ..tools import (
    web_scraper,
    payment_link_generator,
    commission_calculator,
)


class SalesAgent(BaseAgent):
    """
    Sales Agent - Drives sales and customer acquisition
    - Researches market demand
    - Identifies customer segments
    - Creates product listings
    - Processes customer orders
    - Generates sales reports
    """

    def __init__(self):
        super().__init__(
            role=AgentRole.SALES,
            name="SalesAgent",
            description="Markets products, finds customers, processes orders"
        )
        # Register tools
        self.register_tool("web_scraper")
        self.register_tool("payment_link_generator")
        self.register_tool("commission_calculator")

    async def think(self, state: AgentState) -> Dict[str, Any]:
        """
        Analyze sales opportunities:
        - What products to focus on?
        - Which channels to use?
        - What pricing strategy?
        - Which customer segments?
        """
        artisan_profile = state.context.get("artisan_profile", {})
        craft_type = artisan_profile.get("craft_type")

        decision = {
            "action": "identify_sales_opportunity",
            "craft_type": craft_type,
            "focus_products": state.context.get("focus_products", ["best_sellers"]),
            "channels": ["online", "exhibitions", "wholesale"],
            "customer_segments": ["direct_retail", "corporate_gifting", "export"],
            "pricing_strategy": "premium_quality"
        }

        self.remember(f"artisan_{state.artisan_id}_sales_strategy", decision)

        return decision

    async def act(self, state: AgentState, decision: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute sales actions:
        1. Research market demand for products
        2. Identify customer segments
        3. Create product listings
        4. Set up payment system
        """
        artisan_id = state.artisan_id
        craft_type = decision.get("craft_type")
        channels = decision.get("channels", [])

        results = {
            "market_research": {},
            "customer_segments": {},
            "product_listings": [],
            "payment_setup": {}
        }

        # Action 1: Research market demand
        market_result = await web_scraper.execute(
            url=f"https://marketplace.example.com/search?q={craft_type}",
            scrape_type="prices"
        )
        if market_result.success:
            results["market_research"] = market_result.data

        # Action 2: Identify customer segments
        customer_segments = {
            "segment_1": {
                "name": "Retail Customers",
                "avg_purchase_value": 5000,
                "channels": ["online", "exhibitions"],
                "volume_potential": 50,
            },
            "segment_2": {
                "name": "Corporate Gifting",
                "avg_purchase_value": 15000,
                "channels": ["direct_sales", "wholesale"],
                "volume_potential": 20,
            },
            "segment_3": {
                "name": "Export/International",
                "avg_purchase_value": 25000,
                "channels": ["online_international"],
                "volume_potential": 10,
            }
        }
        results["customer_segments"] = customer_segments

        # Action 3: Create product listings
        product_listings = [
            {
                "listing_id": f"prod_{i}",
                "name": f"Artisan {craft_type} - Design {i}",
                "description": f"Handcrafted {craft_type} with traditional techniques",
                "price": 5000 + (i * 2000),
                "images": [],
                "channels": ["online", "exhibitions"]
            }
            for i in range(1, 4)
        ]
        results["product_listings"] = product_listings

        # Action 4: Set up payment system for each product
        for listing in product_listings:
            payment_setup = await payment_link_generator.execute(
                amount=listing["price"],
                customer_name="Customer",
                artisan_id=artisan_id,
                order_id=f"order_{listing['listing_id']}",
                description=listing["name"]
            )
            if payment_setup.success:
                listing["payment_link"] = payment_setup.data.get("payment_url")

        return {
            "action": "setup_sales_channel",
            "artisan_id": artisan_id,
            "results": results,
            "monthly_sales_target": self._calculate_sales_target(customer_segments)
        }

    async def observe(self, state: AgentState, result: Dict[str, Any]) -> None:
        """
        Observe sales setup:
        - Store product information
        - Remember customer segments
        - Prepare for customer acquisition
        """
        artisan_id = state.artisan_id
        results = result.get("results", {})

        self.remember(f"artisan_{artisan_id}_products", results.get("product_listings"))
        self.remember(f"artisan_{artisan_id}_customer_segments", results.get("customer_segments"))
        self.remember(f"artisan_{artisan_id}_sales_target", result.get("monthly_sales_target"))

        state.context["sales_setup_complete"] = True
        state.context["product_listings"] = results.get("product_listings")
        state.context["customer_segments"] = results.get("customer_segments")

    async def process_customer_order(self, customer_data: Dict[str, Any], order_items: List[Dict]) -> Dict[str, Any]:
        """
        Process customer order
        """
        total_amount = sum(item.get("price", 0) * item.get("quantity", 1) for item in order_items)

        # Calculate commission
        commission_calc = await commission_calculator.execute(
            amount=total_amount,
            commission_rate=2.5
        )

        order = {
            "order_id": f"sales_ord_{datetime.utcnow().timestamp()}",
            "customer": customer_data,
            "items": order_items,
            "total_amount": total_amount,
            "artisan_payout": commission_calc.data.get("artisan_payout") if commission_calc.success else total_amount,
            "status": "pending_confirmation",
            "created_at": datetime.utcnow().isoformat()
        }

        return order

    def _calculate_sales_target(self, customer_segments: Dict) -> float:
        """
        Calculate monthly sales target based on segments
        """
        total = 0
        for segment in customer_segments.values():
            avg_value = segment.get("avg_purchase_value", 0)
            volume = segment.get("volume_potential", 0)
            total += avg_value * volume

        return total
