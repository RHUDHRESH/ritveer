"""
Supplier-related Tools
Search for suppliers, get quotes, validate supplier info
"""

import asyncio
import requests
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from .base_tool import BaseTool, ToolResult


class SupplierSearchTool(BaseTool):
    """Search for suppliers of specific materials"""

    def __init__(self):
        super().__init__(
            name="supplier_search",
            description="Search for suppliers of specific materials and quantities",
            required_params=["material_name", "location", "quantity"]
        )
        # In production, this would connect to supplier databases
        self.supplier_database = {
            "clay": [
                {"name": "India Clay Corp", "location": "Bangalore", "phone": "080-1234-5678", "url": "indiaclay.com"},
                {"name": "Ceramic Materials Ltd", "location": "Delhi", "phone": "011-2345-6789", "url": "ceramicmat.in"},
            ],
            "wool": [
                {"name": "Wool Traders", "location": "Jaipur", "phone": "0141-5555-1234", "url": "wooltraders.in"},
                {"name": "Premium Textiles", "location": "Mumbai", "phone": "022-6666-7890", "url": "premiumtex.in"},
            ],
            "wood": [
                {"name": "Timber House", "location": "Bangalore", "phone": "080-8888-9999", "url": "timberhouse.com"},
                {"name": "Quality Woods", "location": "Chennai", "phone": "044-9999-0000", "url": "qualitywoods.in"},
            ],
        }

    async def execute(self, **kwargs) -> ToolResult:
        """Search for suppliers"""
        start_time = datetime.utcnow()

        try:
            material_name = kwargs.get("material_name", "").lower()
            location = kwargs.get("location", "")
            quantity = kwargs.get("quantity", 0)

            # Search in database
            suppliers = self.supplier_database.get(material_name, [])

            # Filter by location proximity (simplified)
            if location:
                # In production, use geolocation
                filtered = [s for s in suppliers if location.lower() in s["location"].lower()]
                suppliers = filtered if filtered else suppliers

            # Prepare results
            results = []
            for supplier in suppliers:
                results.append({
                    "name": supplier["name"],
                    "location": supplier["location"],
                    "phone": supplier["phone"],
                    "website": supplier["url"],
                    "rating": 4.5,  # Mock rating
                    "estimated_price": quantity * 500,  # Mock pricing
                    "delivery_time_days": 7,
                })

            execution_time = (datetime.utcnow() - start_time).total_seconds()

            return ToolResult(
                success=True,
                data=results,
                message=f"Found {len(results)} suppliers for {material_name}",
                execution_time=execution_time,
                timestamp=datetime.utcnow(),
                metadata={"material": material_name, "count": len(results)}
            )

        except Exception as e:
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            return ToolResult(
                success=False,
                data=None,
                message=f"Supplier search failed: {str(e)}",
                execution_time=execution_time,
                timestamp=datetime.utcnow()
            )


class QuoteGeneratorTool(BaseTool):
    """Generate price quotes from suppliers"""

    def __init__(self):
        super().__init__(
            name="quote_generator",
            description="Generate price quotes from suppliers for materials",
            required_params=["supplier_name", "material_name", "quantity", "unit"]
        )

    async def execute(self, **kwargs) -> ToolResult:
        """Generate quote"""
        start_time = datetime.utcnow()

        try:
            supplier_name = kwargs.get("supplier_name")
            material_name = kwargs.get("material_name")
            quantity = float(kwargs.get("quantity", 0))
            unit = kwargs.get("unit", "kg")

            # Mock quote generation logic
            base_price_per_unit = {
                "clay": 50,
                "wool": 500,
                "wood": 100,
                "metal": 200,
                "thread": 10,
            }.get(material_name.lower(), 100)

            # Bulk discount logic
            discount = 0
            if quantity > 100:
                discount = 10
            elif quantity > 50:
                discount = 5

            total_price = quantity * base_price_per_unit * (1 - discount / 100)

            quote_data = {
                "supplier": supplier_name,
                "material": material_name,
                "quantity": quantity,
                "unit": unit,
                "price_per_unit": base_price_per_unit,
                "discount_percentage": discount,
                "total_price": total_price,
                "min_order_quantity": 10,
                "delivery_days": 5,
                "payment_terms": "Net 30",
                "valid_until": (datetime.utcnow() + timedelta(days=30)).isoformat(),
            }

            execution_time = (datetime.utcnow() - start_time).total_seconds()

            return ToolResult(
                success=True,
                data=quote_data,
                message=f"Quote generated for {material_name} from {supplier_name}",
                execution_time=execution_time,
                timestamp=datetime.utcnow(),
                metadata={"total_price": total_price}
            )

        except Exception as e:
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            return ToolResult(
                success=False,
                data=None,
                message=f"Quote generation failed: {str(e)}",
                execution_time=execution_time,
                timestamp=datetime.utcnow()
            )


class SupplierValidationTool(BaseTool):
    """Validate supplier information and credibility"""

    def __init__(self):
        super().__init__(
            name="supplier_validation",
            description="Validate supplier information and credibility score",
            required_params=["supplier_name"]
        )

    async def execute(self, **kwargs) -> ToolResult:
        """Validate supplier"""
        start_time = datetime.utcnow()

        try:
            supplier_name = kwargs.get("supplier_name")

            # Mock validation logic
            validation_result = {
                "supplier": supplier_name,
                "is_verified": True,
                "credibility_score": 4.5,  # Out of 5
                "years_in_business": 8,
                "total_customers": 500,
                "complaint_rate": 0.02,
                "average_delivery_time": 5,
                "payment_reliability": "excellent",
                "certifications": ["ISO 9001", "GST Registered"],
            }

            execution_time = (datetime.utcnow() - start_time).total_seconds()

            return ToolResult(
                success=True,
                data=validation_result,
                message=f"Supplier {supplier_name} validated successfully",
                execution_time=execution_time,
                timestamp=datetime.utcnow(),
                metadata={"credibility_score": validation_result["credibility_score"]}
            )

        except Exception as e:
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            return ToolResult(
                success=False,
                data=None,
                message=f"Supplier validation failed: {str(e)}",
                execution_time=execution_time,
                timestamp=datetime.utcnow()
            )


# Tool instances
supplier_search_tool = SupplierSearchTool()
quote_generator_tool = QuoteGeneratorTool()
supplier_validation_tool = SupplierValidationTool()
