"""
Price Calculator Tool

Calculates pricing including discounts, taxes, and ROI for sales scenarios.
"""
from typing import List, Dict, Any
from pydantic import Field, BaseModel
from decimal import Decimal

from app.tools.base import BaseTool, ToolInputModel
from app.infra.gateway.schemas import AgentType


class PriceItem(BaseModel):
    """Individual price item"""
    name: str = Field(..., description="Product/service name")
    unit_price: float = Field(..., gt=0, description="Unit price")
    quantity: int = Field(..., gt=0, description="Quantity")


class PriceCalculatorInput(ToolInputModel):
    """Price calculation input"""
    items: List[Dict[str, Any]] = Field(..., description="List of items to calculate")
    discount_rate: float = Field(
        0.0,
        ge=0.0,
        le=1.0,
        description="Discount rate (0-1), e.g., 0.2 means 20% off"
    )
    tax_rate: float = Field(
        0.0,
        ge=0.0,
        le=1.0,
        description="Tax rate (0-1)"
    )


class PriceCalculatorTool(BaseTool):
    """
    Price Calculator Tool

    Calculates total price, discounts, taxes for multi-item orders.
    Used for quotations and ROI analysis.

    Allowed agents: NPC, Coach, System
    """

    name = "price_calculator"
    description = "Calculate total price, discounts, and taxes for products/services. Useful for quotations and price negotiations."
    args_schema = PriceCalculatorInput
    allowed_agents = {
        AgentType.NPC.value,
        AgentType.COACH.value,
        "system"
    }

    async def _run(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute price calculation

        Args:
            payload: {
                "items": [{"name": "VIP会员", "unit_price": 1000, "quantity": 1}],
                "discount_rate": 0.2,  # 20% off
                "tax_rate": 0.06       # 6% tax
            }

        Returns:
            {
                "subtotal": 1000.0,
                "discount_amount": 200.0,
                "subtotal_after_discount": 800.0,
                "tax": 48.0,
                "total": 848.0,
                "breakdown": [...],
                "currency": "CNY"
            }
        """
        items = payload["items"]
        discount_rate = Decimal(str(payload.get("discount_rate", 0.0)))
        tax_rate = Decimal(str(payload.get("tax_rate", 0.0)))

        # Calculate item breakdown
        breakdown = []
        subtotal = Decimal("0")

        for item in items:
            unit_price = Decimal(str(item["unit_price"]))
            quantity = item["quantity"]
            item_total = unit_price * quantity

            breakdown.append({
                "name": item["name"],
                "unit_price": float(unit_price),
                "quantity": quantity,
                "item_total": float(item_total)
            })

            subtotal += item_total

        # Apply discount
        discount_amount = subtotal * discount_rate
        subtotal_after_discount = subtotal - discount_amount

        # Calculate tax
        tax = subtotal_after_discount * tax_rate

        # Calculate total
        total = subtotal_after_discount + tax

        return {
            "subtotal": float(subtotal),
            "discount_amount": float(discount_amount),
            "discount_rate_percent": float(discount_rate * 100),
            "subtotal_after_discount": float(subtotal_after_discount),
            "tax": float(tax),
            "tax_rate_percent": float(tax_rate * 100),
            "total": float(total),
            "breakdown": breakdown,
            "currency": "CNY",
            "item_count": len(items),
            "total_quantity": sum(item["quantity"] for item in items)
        }
