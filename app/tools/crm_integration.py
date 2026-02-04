"""
CRM Integration Tool

Provides CRM operations for reading, updating, and creating customer records.
Simulates integration with CRM systems like Salesforce, HubSpot, etc.
"""
from typing import Dict, Any, Optional
from pydantic import Field
from enum import Enum

from app.tools.base import BaseTool, ToolInputModel
from app.infra.gateway.schemas import AgentType


class CRMAction(str, Enum):
    """CRM action types"""
    READ = "read"
    UPDATE = "update"
    CREATE = "create"
    LIST = "list"
    SEARCH = "search"


class CRMIntegrationInput(ToolInputModel):
    """CRM integration input"""
    action: str = Field(..., description="Action to perform: read, update, create, list, search")
    customer_id: Optional[str] = Field(None, description="Customer ID for read/update operations")
    data: Optional[Dict[str, Any]] = Field(None, description="Data for create/update operations")
    query: Optional[str] = Field(None, description="Search query for search operation")
    limit: Optional[int] = Field(10, ge=1, le=100, description="Limit for list/search operations")


class CRMIntegrationTool(BaseTool):
    """
    CRM Integration Tool

    Provides operations for interacting with CRM systems:
    - Read customer records
    - Update customer information
    - Create new customer records
    - List customers
    - Search customers

    Allowed agents: Coach, NPC, System
    """

    name = "crm_integration"
    description = "Interact with CRM system to read, update, create, list, or search customer records. Essential for managing customer relationships."
    args_schema = CRMIntegrationInput
    allowed_agents = {
        AgentType.COACH.value,
        AgentType.NPC.value,
        "system"
    }

    def __init__(self):
        super().__init__()
        # Simulated CRM database
        self._crm_db: Dict[str, Dict[str, Any]] = {
            "CUST001": {
                "id": "CUST001",
                "name": "Acme Corporation",
                "contact": "John Smith",
                "email": "john@acme.com",
                "phone": "+1-555-0100",
                "industry": "Technology",
                "stage": "negotiation",
                "deal_value": 50000,
                "last_contact": "2026-01-28",
                "notes": "Interested in enterprise plan"
            },
            "CUST002": {
                "id": "CUST002",
                "name": "Global Industries",
                "contact": "Sarah Johnson",
                "email": "sarah@global.com",
                "phone": "+1-555-0200",
                "industry": "Manufacturing",
                "stage": "discovery",
                "deal_value": 75000,
                "last_contact": "2026-01-25",
                "notes": "Needs custom integration"
            },
            "CUST003": {
                "id": "CUST003",
                "name": "Tech Startup Inc",
                "contact": "Mike Chen",
                "email": "mike@techstartup.com",
                "phone": "+1-555-0300",
                "industry": "Software",
                "stage": "proposal",
                "deal_value": 25000,
                "last_contact": "2026-01-29",
                "notes": "Budget-conscious, looking for ROI"
            }
        }

    async def _run(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute CRM operation

        Args:
            payload: {
                "action": "read|update|create|list|search",
                "customer_id": "CUST001",  # for read/update
                "data": {...},              # for create/update
                "query": "search term",     # for search
                "limit": 10                 # for list/search
            }

        Returns:
            Operation result with customer data
        """
        action = payload["action"].lower()

        if action == "read":
            return await self._read_customer(payload.get("customer_id"))
        elif action == "update":
            return await self._update_customer(payload.get("customer_id"), payload.get("data", {}))
        elif action == "create":
            return await self._create_customer(payload.get("data", {}))
        elif action == "list":
            return await self._list_customers(payload.get("limit", 10))
        elif action == "search":
            return await self._search_customers(payload.get("query", ""), payload.get("limit", 10))
        else:
            return {
                "success": False,
                "error": f"Unknown action: {action}",
                "valid_actions": ["read", "update", "create", "list", "search"]
            }

    async def _read_customer(self, customer_id: Optional[str]) -> Dict[str, Any]:
        """Read customer record"""
        if not customer_id:
            return {
                "success": False,
                "error": "customer_id is required for read action"
            }

        customer = self._crm_db.get(customer_id)
        if not customer:
            return {
                "success": False,
                "error": f"Customer {customer_id} not found",
                "customer_id": customer_id
            }

        return {
            "success": True,
            "action": "read",
            "customer": customer
        }

    async def _update_customer(self, customer_id: Optional[str], data: Dict[str, Any]) -> Dict[str, Any]:
        """Update customer record"""
        if not customer_id:
            return {
                "success": False,
                "error": "customer_id is required for update action"
            }

        if customer_id not in self._crm_db:
            return {
                "success": False,
                "error": f"Customer {customer_id} not found",
                "customer_id": customer_id
            }

        # Update fields
        customer = self._crm_db[customer_id]
        updated_fields = []
        for key, value in data.items():
            if key != "id":  # Don't allow ID changes
                customer[key] = value
                updated_fields.append(key)

        return {
            "success": True,
            "action": "update",
            "customer_id": customer_id,
            "updated_fields": updated_fields,
            "customer": customer
        }

    async def _create_customer(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create new customer record"""
        if not data:
            return {
                "success": False,
                "error": "data is required for create action"
            }

        # Generate new customer ID
        existing_ids = [int(cid.replace("CUST", "")) for cid in self._crm_db.keys()]
        new_id_num = max(existing_ids) + 1 if existing_ids else 1
        new_id = f"CUST{new_id_num:03d}"

        # Create customer record
        customer = {
            "id": new_id,
            **data
        }
        self._crm_db[new_id] = customer

        return {
            "success": True,
            "action": "create",
            "customer_id": new_id,
            "customer": customer
        }

    async def _list_customers(self, limit: int) -> Dict[str, Any]:
        """List customers"""
        customers = list(self._crm_db.values())[:limit]

        return {
            "success": True,
            "action": "list",
            "count": len(customers),
            "total": len(self._crm_db),
            "customers": customers
        }

    async def _search_customers(self, query: str, limit: int) -> Dict[str, Any]:
        """Search customers"""
        if not query:
            return {
                "success": False,
                "error": "query is required for search action"
            }

        query_lower = query.lower()
        results = []

        for customer in self._crm_db.values():
            # Search in name, contact, email, industry
            searchable = f"{customer.get('name', '')} {customer.get('contact', '')} {customer.get('email', '')} {customer.get('industry', '')}".lower()
            if query_lower in searchable:
                results.append(customer)

            if len(results) >= limit:
                break

        return {
            "success": True,
            "action": "search",
            "query": query,
            "count": len(results),
            "customers": results
        }
