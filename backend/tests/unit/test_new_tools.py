"""
Unit Tests for New Tools (P1.1)
================================

Tests for CRM Integration, SMS Outreach, and Competitor Analysis tools.
"""
import pytest

from app.tools.crm_integration import CRMIntegrationTool
from app.tools.outreach.sms_tool import SMSOutreachTool
from app.tools.competitor_analysis import CompetitorAnalysisTool
from app.infra.gateway.schemas import AgentType


class TestCRMIntegrationTool:
    """Test CRM Integration Tool"""

    @pytest.fixture
    def tool(self):
        """Create tool instance"""
        return CRMIntegrationTool()

    def test_tool_metadata(self, tool):
        """Test tool metadata"""
        assert tool.name == "crm_integration"
        assert "crm" in tool.description.lower()
        assert AgentType.COACH.value in tool.allowed_agents
        assert AgentType.NPC.value in tool.allowed_agents
        assert "system" in tool.allowed_agents

    @pytest.mark.asyncio
    async def test_read_customer_success(self, tool):
        """Test reading existing customer"""
        result = await tool._run({
            "action": "read",
            "customer_id": "CUST001"
        })

        assert result["success"] is True
        assert result["action"] == "read"
        assert result["customer"]["id"] == "CUST001"
        assert result["customer"]["name"] == "Acme Corporation"

    @pytest.mark.asyncio
    async def test_read_customer_not_found(self, tool):
        """Test reading non-existent customer"""
        result = await tool._run({
            "action": "read",
            "customer_id": "CUST999"
        })

        assert result["success"] is False
        assert "not found" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_read_customer_missing_id(self, tool):
        """Test reading without customer_id"""
        result = await tool._run({
            "action": "read"
        })

        assert result["success"] is False
        assert "required" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_update_customer_success(self, tool):
        """Test updating customer"""
        result = await tool._run({
            "action": "update",
            "customer_id": "CUST001",
            "data": {
                "stage": "closing",
                "deal_value": 60000
            }
        })

        assert result["success"] is True
        assert result["action"] == "update"
        assert result["customer"]["stage"] == "closing"
        assert result["customer"]["deal_value"] == 60000
        assert "stage" in result["updated_fields"]
        assert "deal_value" in result["updated_fields"]

    @pytest.mark.asyncio
    async def test_update_customer_not_found(self, tool):
        """Test updating non-existent customer"""
        result = await tool._run({
            "action": "update",
            "customer_id": "CUST999",
            "data": {"stage": "closing"}
        })

        assert result["success"] is False
        assert "not found" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_create_customer_success(self, tool):
        """Test creating new customer"""
        result = await tool._run({
            "action": "create",
            "data": {
                "name": "New Company",
                "contact": "Jane Doe",
                "email": "jane@newcompany.com",
                "industry": "Finance"
            }
        })

        assert result["success"] is True
        assert result["action"] == "create"
        assert result["customer_id"].startswith("CUST")
        assert result["customer"]["name"] == "New Company"

    @pytest.mark.asyncio
    async def test_create_customer_missing_data(self, tool):
        """Test creating customer without data"""
        result = await tool._run({
            "action": "create"
        })

        assert result["success"] is False
        assert "required" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_list_customers(self, tool):
        """Test listing customers"""
        result = await tool._run({
            "action": "list",
            "limit": 2
        })

        assert result["success"] is True
        assert result["action"] == "list"
        assert result["count"] == 2
        assert result["total"] >= 3
        assert len(result["customers"]) == 2

    @pytest.mark.asyncio
    async def test_search_customers_success(self, tool):
        """Test searching customers"""
        result = await tool._run({
            "action": "search",
            "query": "Acme",
            "limit": 10
        })

        assert result["success"] is True
        assert result["action"] == "search"
        assert result["query"] == "Acme"
        assert result["count"] >= 1
        assert any("Acme" in c["name"] for c in result["customers"])

    @pytest.mark.asyncio
    async def test_search_customers_no_query(self, tool):
        """Test searching without query"""
        result = await tool._run({
            "action": "search"
        })

        assert result["success"] is False
        assert "required" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_invalid_action(self, tool):
        """Test invalid action"""
        result = await tool._run({
            "action": "delete"
        })

        assert result["success"] is False
        assert "unknown action" in result["error"].lower()


class TestSMSOutreachTool:
    """Test SMS Outreach Tool"""

    @pytest.fixture
    def tool(self):
        """Create tool instance"""
        return SMSOutreachTool()

    def test_tool_metadata(self, tool):
        """Test tool metadata"""
        assert tool.name == "sms_outreach"
        assert "sms" in tool.description.lower()
        assert AgentType.COACH.value in tool.allowed_agents
        assert "system" in tool.allowed_agents

    @pytest.mark.asyncio
    async def test_send_sms_success(self, tool):
        """Test sending SMS successfully"""
        result = await tool._run({
            "phone_number": "+15550001000",
            "message": "Hi John, following up on our conversation.",
            "customer_id": "CUST001",
            "campaign": "Q1_followup"
        })

        assert result["success"] is True
        assert result["status"] == "sent"
        assert result["phone_number"] == "+15550001000"
        assert result["message_length"] == 42
        assert "message_id" in result
        assert result["message_id"].startswith("sms_")

    @pytest.mark.asyncio
    async def test_send_sms_invalid_phone(self, tool):
        """Test sending SMS with invalid phone number"""
        result = await tool._run({
            "phone_number": "invalid",
            "message": "Test message"
        })

        assert result["success"] is False
        assert "invalid phone number" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_send_sms_too_long(self, tool):
        """Test sending SMS that's too long"""
        long_message = "A" * 161

        result = await tool._run({
            "phone_number": "+15550001000",
            "message": long_message
        })

        assert result["success"] is False
        assert "too long" in result["error"].lower()
        assert result["message_length"] == 161

    @pytest.mark.asyncio
    async def test_send_sms_rate_limit(self, tool):
        """Test SMS rate limiting"""
        phone = "+15550002000"

        # Send 5 SMS (should succeed)
        for i in range(5):
            result = await tool._run({
                "phone_number": phone,
                "message": f"Message {i+1}"
            })
            assert result["success"] is True

        # 6th SMS should fail due to rate limit
        result = await tool._run({
            "phone_number": phone,
            "message": "Message 6"
        })

        assert result["success"] is False
        assert "rate limit" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_validate_phone_number_valid(self, tool):
        """Test phone number validation - valid formats"""
        assert tool._validate_phone_number("+15550001000") is True
        assert tool._validate_phone_number("+8613800000000") is True
        assert tool._validate_phone_number("+442012345678") is True

    @pytest.mark.asyncio
    async def test_validate_phone_number_invalid(self, tool):
        """Test phone number validation - invalid formats"""
        assert tool._validate_phone_number("555-0100") is False
        assert tool._validate_phone_number("invalid") is False
        assert tool._validate_phone_number("") is False

    @pytest.mark.asyncio
    async def test_calculate_segments(self, tool):
        """Test SMS segment calculation"""
        # Standard SMS: 160 chars per segment
        assert tool._calculate_segments("A" * 160) == 1
        assert tool._calculate_segments("A" * 161) == 2
        assert tool._calculate_segments("A" * 320) == 2

        # With special chars: 70 chars per segment
        assert tool._calculate_segments("你好" * 35) == 1
        assert tool._calculate_segments("你好" * 36) == 2

    @pytest.mark.asyncio
    async def test_get_history(self, tool):
        """Test getting SMS history"""
        # Send some SMS
        await tool._run({
            "phone_number": "+15550003000",
            "message": "Test 1"
        })
        await tool._run({
            "phone_number": "+15550003000",
            "message": "Test 2"
        })

        # Get history
        history = await tool.get_history(phone_number="+15550003000")

        assert history["success"] is True
        assert history["count"] >= 2

    @pytest.mark.asyncio
    async def test_get_campaign_stats(self, tool):
        """Test getting campaign statistics"""
        # Send SMS for campaign
        await tool._run({
            "phone_number": "+15550004000",
            "message": "Campaign message 1",
            "campaign": "test_campaign"
        })
        await tool._run({
            "phone_number": "+15550005000",
            "message": "Campaign message 2",
            "campaign": "test_campaign"
        })

        # Get stats
        stats = await tool.get_campaign_stats("test_campaign")

        assert stats["success"] is True
        assert stats["campaign"] == "test_campaign"
        assert stats["total_sent"] >= 2
        assert stats["unique_recipients"] >= 2


class TestCompetitorAnalysisTool:
    """Test Competitor Analysis Tool"""

    @pytest.fixture
    def tool(self):
        """Create tool instance"""
        return CompetitorAnalysisTool()

    def test_tool_metadata(self, tool):
        """Test tool metadata"""
        assert tool.name == "competitor_analysis"
        assert "competitor" in tool.description.lower()
        assert AgentType.COACH.value in tool.allowed_agents
        assert "system" in tool.allowed_agents

    @pytest.mark.asyncio
    async def test_analyze_specific_competitor(self, tool):
        """Test analyzing specific competitor"""
        result = await tool._run({
            "competitor_name": "CompetitorA"
        })

        assert result["success"] is True
        assert result["competitor"]["name"] == "CompetitorA"
        assert "market_share" in result["competitor"]
        assert "pricing" in result["competitor"]
        assert "features" in result["competitor"]

    @pytest.mark.asyncio
    async def test_analyze_competitor_not_found(self, tool):
        """Test analyzing non-existent competitor"""
        result = await tool._run({
            "competitor_name": "NonExistent"
        })

        assert result["success"] is False
        assert "not found" in result["error"].lower()
        assert "available_competitors" in result

    @pytest.mark.asyncio
    async def test_analyze_competitor_pricing(self, tool):
        """Test analyzing competitor pricing"""
        result = await tool._run({
            "competitor_name": "CompetitorA",
            "aspect": "pricing"
        })

        assert result["success"] is True
        assert result["aspect"] == "pricing"
        assert "data" in result
        assert "comparison" in result

    @pytest.mark.asyncio
    async def test_analyze_competitor_features(self, tool):
        """Test analyzing competitor features"""
        result = await tool._run({
            "competitor_name": "CompetitorA",
            "aspect": "features"
        })

        assert result["success"] is True
        assert result["aspect"] == "features"
        assert isinstance(result["data"], list)
        assert result["feature_count"] > 0

    @pytest.mark.asyncio
    async def test_analyze_competitor_market_share(self, tool):
        """Test analyzing competitor market share"""
        result = await tool._run({
            "competitor_name": "CompetitorA",
            "aspect": "market_share"
        })

        assert result["success"] is True
        assert result["aspect"] == "market_share"
        assert isinstance(result["data"], float)
        assert result["rank"] >= 1

    @pytest.mark.asyncio
    async def test_analyze_competitor_strengths(self, tool):
        """Test analyzing competitor strengths"""
        result = await tool._run({
            "competitor_name": "CompetitorA",
            "aspect": "strengths"
        })

        assert result["success"] is True
        assert result["aspect"] == "strengths"
        assert isinstance(result["data"], list)
        assert len(result["data"]) > 0

    @pytest.mark.asyncio
    async def test_analyze_competitor_weaknesses(self, tool):
        """Test analyzing competitor weaknesses"""
        result = await tool._run({
            "competitor_name": "CompetitorA",
            "aspect": "weaknesses"
        })

        assert result["success"] is True
        assert result["aspect"] == "weaknesses"
        assert isinstance(result["data"], list)
        assert "opportunities" in result

    @pytest.mark.asyncio
    async def test_analyze_by_category(self, tool):
        """Test analyzing by category"""
        result = await tool._run({
            "category": "direct"
        })

        assert result["success"] is True
        assert result["category"] == "direct"
        assert result["count"] >= 2
        assert "total_market_share" in result

    @pytest.mark.asyncio
    async def test_analyze_invalid_category(self, tool):
        """Test analyzing invalid category"""
        result = await tool._run({
            "category": "invalid"
        })

        assert result["success"] is False
        assert "valid_categories" in result

    @pytest.mark.asyncio
    async def test_market_overview(self, tool):
        """Test market overview"""
        result = await tool._run({})

        assert result["success"] is True
        assert "total_competitors" in result
        assert "total_market_share_tracked" in result
        assert "market_leader" in result
        assert "category_breakdown" in result

    @pytest.mark.asyncio
    async def test_compare_pricing(self, tool):
        """Test pricing comparison"""
        comparison = tool._compare_pricing("CompetitorA")

        assert isinstance(comparison, dict)
        assert len(comparison) >= 2  # At least 2 other competitors

    @pytest.mark.asyncio
    async def test_get_market_rank(self, tool):
        """Test getting market rank"""
        rank = tool._get_market_rank("CompetitorA")

        assert rank >= 1
        assert rank <= 3

    @pytest.mark.asyncio
    async def test_identify_opportunities(self, tool):
        """Test identifying opportunities"""
        weaknesses = ["Higher pricing", "Limited customization"]
        opportunities = tool._identify_opportunities(weaknesses)

        assert isinstance(opportunities, list)
        assert len(opportunities) >= 2

    @pytest.mark.asyncio
    async def test_invalid_aspect(self, tool):
        """Test invalid aspect"""
        result = await tool._run({
            "competitor_name": "CompetitorA",
            "aspect": "invalid"
        })

        assert result["success"] is False
        assert "valid_aspects" in result
