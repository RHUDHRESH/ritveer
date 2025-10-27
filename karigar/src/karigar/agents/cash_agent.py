"""
Cash Agent (CashAgent)
Manages financial operations, accounting, and profitability
Tracks income, expenses, and profit margins
"""

from typing import Dict, Any, List
from datetime import datetime, timedelta
from .base_agent import BaseAgent, AgentState, AgentRole


class CashAgent(BaseAgent):
    """
    Cash Agent - Manages financial operations
    - Tracks income and expenses
    - Calculates profit margins
    - Manages cash flow
    - Generates financial reports
    - Optimizes pricing
    """

    def __init__(self):
        super().__init__(
            role=AgentRole.CASH,
            name="CashAgent",
            description="Manages financial operations, accounting, and profitability"
        )

    async def think(self, state: AgentState) -> Dict[str, Any]:
        """
        Analyze financial situation:
        - What's the order value?
        - What are the costs?
        - What's the profit margin?
        - What's the cash flow impact?
        """
        order_data = state.context.get("order_data", {})
        supplier_results = state.context.get("supplier_results", {})
        best_quote = state.context.get("best_quote", {})

        estimated_revenue = order_data.get("estimated_cost", 0)
        material_cost = best_quote.get("total_price", 0) if best_quote else 0
        labor_cost = self._estimate_labor_cost(order_data)

        total_cost = material_cost + labor_cost
        profit = estimated_revenue - total_cost
        margin = (profit / estimated_revenue * 100) if estimated_revenue > 0 else 0

        decision = {
            "action": "financial_analysis",
            "order_id": order_data.get("order_id"),
            "revenue": estimated_revenue,
            "costs": {
                "materials": material_cost,
                "labor": labor_cost,
                "total": total_cost
            },
            "profit": profit,
            "margin_percentage": margin,
            "profitability": "high" if margin > 40 else "medium" if margin > 20 else "low"
        }

        self.remember(f"order_{order_data.get('order_id')}_financials", decision)

        return decision

    async def act(self, state: AgentState, decision: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute financial actions:
        1. Create cost breakdown
        2. Calculate profitability
        3. Setup payment tracking
        4. Create financial report
        """
        order_id = decision.get("order_id")
        revenue = decision.get("revenue", 0)
        costs = decision.get("costs", {})
        profit = decision.get("profit", 0)
        margin = decision.get("margin_percentage", 0)

        results = {}

        # Step 1: Detailed cost breakdown
        cost_breakdown = {
            "order_id": order_id,
            "items": [
                {
                    "category": "Raw Materials",
                    "amount": costs.get("materials", 0),
                    "percentage": (costs.get("materials", 0) / revenue * 100) if revenue > 0 else 0
                },
                {
                    "category": "Labor",
                    "amount": costs.get("labor", 0),
                    "percentage": (costs.get("labor", 0) / revenue * 100) if revenue > 0 else 0
                },
                {
                    "category": "Overhead",
                    "amount": revenue * 0.05,  # 5% overhead estimate
                    "percentage": 5
                }
            ],
            "total_cost": costs.get("total", 0),
        }
        results["cost_breakdown"] = cost_breakdown

        # Step 2: Profitability analysis
        profitability = {
            "order_id": order_id,
            "revenue": revenue,
            "total_cost": costs.get("total", 0),
            "gross_profit": profit,
            "profit_margin": margin,
            "profitability_rating": decision.get("profitability"),
            "break_even_units": self._calculate_breakeven(revenue, costs.get("total", 0)),
            "recommendation": self._get_financial_recommendation(margin)
        }
        results["profitability"] = profitability

        # Step 3: Payment tracking setup
        payment_schedule = {
            "order_id": order_id,
            "payments": [
                {
                    "milestone": "Order Confirmation",
                    "percentage": 30,
                    "amount": revenue * 0.3,
                    "due_date": datetime.utcnow().isoformat(),
                    "status": "pending"
                },
                {
                    "milestone": "Production Started",
                    "percentage": 40,
                    "amount": revenue * 0.4,
                    "due_date": (datetime.utcnow() + timedelta(days=7)).isoformat(),
                    "status": "pending"
                },
                {
                    "milestone": "Production Complete",
                    "percentage": 30,
                    "amount": revenue * 0.3,
                    "due_date": (datetime.utcnow() + timedelta(days=21)).isoformat(),
                    "status": "pending"
                }
            ],
            "total_amount": revenue
        }
        results["payment_schedule"] = payment_schedule

        # Step 4: Financial forecast
        monthly_impact = {
            "order_id": order_id,
            "month": datetime.utcnow().strftime("%Y-%m"),
            "revenue_impact": revenue,
            "cost_impact": costs.get("total", 0),
            "profit_impact": profit,
            "cash_flow_impact": revenue * 0.7,  # Assuming 70% paid upfront
            "expected_payback_days": self._calculate_payback_period(profit, revenue)
        }
        results["financial_forecast"] = monthly_impact

        return {
            "action": "manage_finances",
            "order_id": order_id,
            "status": "financial_plan_created",
            "results": results
        }

    async def observe(self, state: AgentState, result: Dict[str, Any]) -> None:
        """
        Observe financial planning:
        - Store cost information
        - Remember profitability metrics
        - Track payment schedule
        """
        order_id = result.get("order_id")
        results = result.get("results", {})

        # Store financial information
        self.remember(f"order_{order_id}_costs", results.get("cost_breakdown"))
        self.remember(f"order_{order_id}_profitability", results.get("profitability"))
        self.remember(f"order_{order_id}_payments", results.get("payment_schedule"))

        # Update state
        state.context["financial_plan_created"] = True
        state.context["profitability"] = results.get("profitability")
        state.context["payment_schedule"] = results.get("payment_schedule")

    def _estimate_labor_cost(self, order_data: Dict) -> float:
        """
        Estimate labor cost based on order details
        """
        quantity = order_data.get("quantity", 1)
        complexity = 1  # Simple, could be variable
        hours_per_unit = 4  # Default
        hourly_rate = 200  # Default artisan rate in INR

        return quantity * hours_per_unit * hourly_rate * complexity

    def _calculate_breakeven(self, revenue: float, cost: float) -> int:
        """
        Calculate break-even point in units
        """
        if revenue <= 0:
            return 0

        per_unit_revenue = revenue
        per_unit_cost = cost

        if per_unit_revenue <= per_unit_cost:
            return float('inf')

        return int(cost / (per_unit_revenue - per_unit_cost)) + 1

    def _get_financial_recommendation(self, margin: float) -> str:
        """
        Get financial recommendation based on margin
        """
        if margin > 50:
            return "Highly profitable - consider bulk orders"
        elif margin > 40:
            return "Good profitability - sustainable"
        elif margin > 20:
            return "Acceptable margin - optimize costs"
        else:
            return "Low margin - review pricing strategy"

    def _calculate_payback_period(self, profit: float, revenue: float) -> int:
        """
        Calculate payback period in days
        """
        if profit <= 0 or revenue <= 0:
            return 0

        # Assuming daily profit = monthly profit / 30
        daily_profit = profit / 30
        payback_days = int(revenue / daily_profit) if daily_profit > 0 else 0

        return max(1, min(payback_days, 90))  # Cap at 90 days

    async def generate_invoice(self, order_id: str, payment_details: Dict) -> Dict[str, Any]:
        """
        Generate invoice for order
        """
        invoice = {
            "invoice_id": f"INV-{order_id}",
            "order_id": order_id,
            "amount": payment_details.get("amount", 0),
            "tax": payment_details.get("amount", 0) * 0.18,  # 18% GST
            "total": payment_details.get("amount", 0) * 1.18,
            "due_date": (datetime.utcnow() + timedelta(days=7)).isoformat(),
            "status": "issued"
        }

        return invoice

    async def record_payment(self, order_id: str, amount: float, method: str) -> Dict[str, Any]:
        """
        Record payment received
        """
        payment = {
            "payment_id": f"PAY-{order_id}-{datetime.utcnow().timestamp()}",
            "order_id": order_id,
            "amount": amount,
            "method": method,
            "date": datetime.utcnow().isoformat(),
            "status": "completed"
        }

        return payment

    async def generate_financial_report(self, artisan_id: str, period: str) -> Dict[str, Any]:
        """
        Generate financial report for artisan
        """
        report = {
            "artisan_id": artisan_id,
            "period": period,
            "total_revenue": 0,
            "total_expenses": 0,
            "net_profit": 0,
            "orders_completed": 0,
            "average_margin": 0,
            "cash_balance": 0,
            "generated_at": datetime.utcnow().isoformat()
        }

        return report
