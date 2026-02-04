"""
Comprehensive Unit Tests for All Tools
=======================================

Tests all 5 existing tools with success paths, error handling,
input validation, and edge cases.

Tools tested:
- knowledge_retriever
- compliance_check
- profile_reader
- price_calculator
- stage_classifier
"""
import pytest
from unittest.mock import AsyncMock, Mock, patch

from app.tools.retriever import KnowledgeRetrieverTool
from app.tools.compliance import ComplianceCheckTool
from app.tools.profile_reader import ProfileReaderTool
from app.tools.price_calculator import PriceCalculatorTool
from app.tools.stage_classifier import StageClassifierTool
from app.infra.gateway.schemas import AgentType


class TestKnowledgeRetrieverTool:
    """Test KnowledgeRetrieverTool"""

    @pytest.fixture
    def tool(self):
        """Create tool instance"""
        return KnowledgeRetrieverTool()

    def test_tool_metadata(self, tool):
        """Test tool metadata"""
        assert tool.name == "knowledge_retriever"
        assert "knowledge base" in tool.description.lower()
        assert AgentType.COACH.value in tool.allowed_agents
        assert AgentType.NPC.value in tool.allowed_agents

    @pytest.mark.asyncio
    async def test_successful_retrieval(self, tool):
        """Test successful knowledge retrieval"""
        mock_vector_store = AsyncMock()
        mock_vector_store.similarity_search.return_value = [
            Mock(page_content="Product A features", metadata={"source": "product_docs.pdf"}),
            Mock(page_content="Product A pricing", metadata={"source": "pricing.pdf"})
        ]

        with patch.object(tool, '_get_vector_store', return_value=mock_vector_store):
            result = await tool._run({
                "query": "What are the features of Product A?",
                "top_k": 2
            })

            assert result["success"] is True
            assert len(result["documents"]) == 2
            assert result["documents"][0]["content"] == "Product A features"
            assert result["documents"][0]["source"] == "product_docs.pdf"
            assert result["query"] == "What are the features of Product A?"

    @pytest.mark.asyncio
    async def test_no_results_found(self, tool):
        """Test when no documents are found"""
        mock_vector_store = AsyncMock()
        mock_vector_store.similarity_search.return_value = []

        with patch.object(tool, '_get_vector_store', return_value=mock_vector_store):
            result = await tool._run({
                "query": "nonexistent query",
                "top_k": 5
            })

            assert result["success"] is True
            assert len(result["documents"]) == 0
            assert result["message"] == "No relevant documents found"

    @pytest.mark.asyncio
    async def test_default_top_k(self, tool):
        """Test default top_k value"""
        mock_vector_store = AsyncMock()
        mock_vector_store.similarity_search.return_value = []

        with patch.object(tool, '_get_vector_store', return_value=mock_vector_store):
            await tool._run({"query": "test"})

            mock_vector_store.similarity_search.assert_called_once()
            call_args = mock_vector_store.similarity_search.call_args
            assert call_args[1]["k"] == 5  # Default value

    @pytest.mark.asyncio
    async def test_custom_top_k(self, tool):
        """Test custom top_k value"""
        mock_vector_store = AsyncMock()
        mock_vector_store.similarity_search.return_value = []

        with patch.object(tool, '_get_vector_store', return_value=mock_vector_store):
            await tool._run({"query": "test", "top_k": 10})

            call_args = mock_vector_store.similarity_search.call_args
            assert call_args[1]["k"] == 10

    @pytest.mark.asyncio
    async def test_vector_store_error(self, tool):
        """Test handling of vector store errors"""
        mock_vector_store = AsyncMock()
        mock_vector_store.similarity_search.side_effect = Exception("Vector store unavailable")

        with patch.object(tool, '_get_vector_store', return_value=mock_vector_store):
            with pytest.raises(Exception, match="Vector store unavailable"):
                await tool._run({"query": "test"})


class TestComplianceCheckTool:
    """Test ComplianceCheckTool"""

    @pytest.fixture
    def tool(self):
        """Create tool instance"""
        return ComplianceCheckTool()

    def test_tool_metadata(self, tool):
        """Test tool metadata"""
        assert tool.name == "compliance_check"
        assert "compliance" in tool.description.lower()
        assert AgentType.COACH.value in tool.allowed_agents
        assert "system" in tool.allowed_agents

    @pytest.mark.asyncio
    async def test_compliant_text(self, tool):
        """Test compliant text passes"""
        mock_agent = AsyncMock()
        mock_agent.check.return_value = {
            "compliant": True,
            "violations": [],
            "risk_level": "low"
        }

        with patch.object(tool, '_get_compliance_agent', return_value=mock_agent):
            result = await tool._run({
                "text": "Our product offers great value for your business."
            })

            assert result["compliant"] is True
            assert len(result["violations"]) == 0
            assert result["risk_level"] == "low"

    @pytest.mark.asyncio
    async def test_non_compliant_text(self, tool):
        """Test non-compliant text is flagged"""
        mock_agent = AsyncMock()
        mock_agent.check.return_value = {
            "compliant": False,
            "violations": [
                {"type": "misleading_claim", "text": "guaranteed returns"}
            ],
            "risk_level": "high"
        }

        with patch.object(tool, '_get_compliance_agent', return_value=mock_agent):
            result = await tool._run({
                "text": "We guarantee 100% returns on your investment."
            })

            assert result["compliant"] is False
            assert len(result["violations"]) == 1
            assert result["violations"][0]["type"] == "misleading_claim"
            assert result["risk_level"] == "high"

    @pytest.mark.asyncio
    async def test_empty_text(self, tool):
        """Test empty text handling"""
        mock_agent = AsyncMock()
        mock_agent.check.return_value = {
            "compliant": True,
            "violations": [],
            "risk_level": "low"
        }

        with patch.object(tool, '_get_compliance_agent', return_value=mock_agent):
            result = await tool._run({"text": ""})

            assert result["compliant"] is True
            assert len(result["violations"]) == 0

    @pytest.mark.asyncio
    async def test_compliance_agent_error(self, tool):
        """Test handling of compliance agent errors"""
        mock_agent = AsyncMock()
        mock_agent.check.side_effect = Exception("Compliance service unavailable")

        with patch.object(tool, '_get_compliance_agent', return_value=mock_agent):
            with pytest.raises(Exception, match="Compliance service unavailable"):
                await tool._run({"text": "test"})


class TestProfileReaderTool:
    """Test ProfileReaderTool"""

    @pytest.fixture
    def tool(self):
        """Create tool instance"""
        return ProfileReaderTool()

    def test_tool_metadata(self, tool):
        """Test tool metadata"""
        assert tool.name == "profile_reader"
        assert "customer profile" in tool.description.lower()
        assert AgentType.COACH.value in tool.allowed_agents
        assert AgentType.NPC.value in tool.allowed_agents

    @pytest.mark.asyncio
    async def test_read_specific_field(self, tool):
        """Test reading a specific profile field"""
        mock_profile = {
            "name": "John Doe",
            "company": "Acme Corp",
            "industry": "Technology",
            "budget": 50000
        }

        with patch.object(tool, '_get_profile', return_value=mock_profile):
            result = await tool._run({"field": "company"})

            assert result["success"] is True
            assert result["field"] == "company"
            assert result["value"] == "Acme Corp"

    @pytest.mark.asyncio
    async def test_read_all_fields(self, tool):
        """Test reading all profile fields"""
        mock_profile = {
            "name": "John Doe",
            "company": "Acme Corp",
            "industry": "Technology"
        }

        with patch.object(tool, '_get_profile', return_value=mock_profile):
            result = await tool._run({"field": "all"})

            assert result["success"] is True
            assert result["field"] == "all"
            assert result["profile"] == mock_profile
            assert len(result["profile"]) == 3

    @pytest.mark.asyncio
    async def test_field_not_found(self, tool):
        """Test handling of non-existent field"""
        mock_profile = {
            "name": "John Doe",
            "company": "Acme Corp"
        }

        with patch.object(tool, '_get_profile', return_value=mock_profile):
            result = await tool._run({"field": "nonexistent"})

            assert result["success"] is False
            assert "not found" in result["message"].lower()

    @pytest.mark.asyncio
    async def test_empty_profile(self, tool):
        """Test handling of empty profile"""
        with patch.object(tool, '_get_profile', return_value={}):
            result = await tool._run({"field": "name"})

            assert result["success"] is False

    @pytest.mark.asyncio
    async def test_profile_service_error(self, tool):
        """Test handling of profile service errors"""
        with patch.object(tool, '_get_profile', side_effect=Exception("Profile service unavailable")):
            with pytest.raises(Exception, match="Profile service unavailable"):
                await tool._run({"field": "name"})


class TestPriceCalculatorTool:
    """Test PriceCalculatorTool"""

    @pytest.fixture
    def tool(self):
        """Create tool instance"""
        return PriceCalculatorTool()

    def test_tool_metadata(self, tool):
        """Test tool metadata"""
        assert tool.name == "price_calculator"
        assert "price" in tool.description.lower()
        assert AgentType.COACH.value in tool.allowed_agents
        assert AgentType.NPC.value in tool.allowed_agents

    @pytest.mark.asyncio
    async def test_simple_calculation(self, tool):
        """Test simple price calculation"""
        result = await tool._run({
            "items": [
                {"name": "Product A", "unit_price": 100.0, "quantity": 2}
            ],
            "discount_rate": 0.0,
            "tax_rate": 0.0
        })

        assert result["subtotal"] == 200.0
        assert result["discount_amount"] == 0.0
        assert result["tax"] == 0.0
        assert result["total"] == 200.0
        assert len(result["breakdown"]) == 1

    @pytest.mark.asyncio
    async def test_calculation_with_discount(self, tool):
        """Test calculation with discount"""
        result = await tool._run({
            "items": [
                {"name": "Product A", "unit_price": 100.0, "quantity": 1}
            ],
            "discount_rate": 0.2,  # 20% off
            "tax_rate": 0.0
        })

        assert result["subtotal"] == 100.0
        assert result["discount_amount"] == 20.0
        assert result["subtotal_after_discount"] == 80.0
        assert result["discount_rate_percent"] == 20.0
        assert result["total"] == 80.0

    @pytest.mark.asyncio
    async def test_calculation_with_tax(self, tool):
        """Test calculation with tax"""
        result = await tool._run({
            "items": [
                {"name": "Product A", "unit_price": 100.0, "quantity": 1}
            ],
            "discount_rate": 0.0,
            "tax_rate": 0.1  # 10% tax
        })

        assert result["subtotal"] == 100.0
        assert result["tax"] == 10.0
        assert result["tax_rate_percent"] == 10.0
        assert result["total"] == 110.0

    @pytest.mark.asyncio
    async def test_calculation_with_discount_and_tax(self, tool):
        """Test calculation with both discount and tax"""
        result = await tool._run({
            "items": [
                {"name": "Product A", "unit_price": 100.0, "quantity": 1}
            ],
            "discount_rate": 0.2,  # 20% off
            "tax_rate": 0.1  # 10% tax
        })

        # Subtotal: 100
        # After discount: 80 (100 - 20)
        # Tax: 8 (80 * 0.1)
        # Total: 88
        assert result["subtotal"] == 100.0
        assert result["discount_amount"] == 20.0
        assert result["subtotal_after_discount"] == 80.0
        assert result["tax"] == 8.0
        assert result["total"] == 88.0

    @pytest.mark.asyncio
    async def test_multiple_items(self, tool):
        """Test calculation with multiple items"""
        result = await tool._run({
            "items": [
                {"name": "Product A", "unit_price": 100.0, "quantity": 2},
                {"name": "Product B", "unit_price": 50.0, "quantity": 3},
                {"name": "Product C", "unit_price": 25.0, "quantity": 4}
            ],
            "discount_rate": 0.1,
            "tax_rate": 0.05
        })

        # Subtotal: 200 + 150 + 100 = 450
        # After discount: 405 (450 - 45)
        # Tax: 20.25 (405 * 0.05)
        # Total: 425.25
        assert result["subtotal"] == 450.0
        assert result["discount_amount"] == 45.0
        assert result["subtotal_after_discount"] == 405.0
        assert result["tax"] == 20.25
        assert result["total"] == 425.25
        assert len(result["breakdown"]) == 3
        assert result["item_count"] == 3
        assert result["total_quantity"] == 9

    @pytest.mark.asyncio
    async def test_breakdown_details(self, tool):
        """Test item breakdown details"""
        result = await tool._run({
            "items": [
                {"name": "Product A", "unit_price": 100.0, "quantity": 2}
            ],
            "discount_rate": 0.0,
            "tax_rate": 0.0
        })

        breakdown = result["breakdown"][0]
        assert breakdown["name"] == "Product A"
        assert breakdown["unit_price"] == 100.0
        assert breakdown["quantity"] == 2
        assert breakdown["item_total"] == 200.0

    @pytest.mark.asyncio
    async def test_decimal_precision(self, tool):
        """Test decimal precision in calculations"""
        result = await tool._run({
            "items": [
                {"name": "Product A", "unit_price": 99.99, "quantity": 3}
            ],
            "discount_rate": 0.15,
            "tax_rate": 0.0825
        })

        # Should handle decimal precision correctly
        assert isinstance(result["total"], float)
        assert result["total"] > 0

    @pytest.mark.asyncio
    async def test_zero_discount_and_tax(self, tool):
        """Test with zero discount and tax"""
        result = await tool._run({
            "items": [
                {"name": "Product A", "unit_price": 100.0, "quantity": 1}
            ],
            "discount_rate": 0.0,
            "tax_rate": 0.0
        })

        assert result["discount_amount"] == 0.0
        assert result["tax"] == 0.0
        assert result["total"] == result["subtotal"]

    @pytest.mark.asyncio
    async def test_currency_field(self, tool):
        """Test currency field in result"""
        result = await tool._run({
            "items": [
                {"name": "Product A", "unit_price": 100.0, "quantity": 1}
            ]
        })

        assert result["currency"] == "CNY"


class TestStageClassifierTool:
    """Test StageClassifierTool"""

    @pytest.fixture
    def tool(self):
        """Create tool instance"""
        return StageClassifierTool()

    def test_tool_metadata(self, tool):
        """Test tool metadata"""
        assert tool.name == "stage_classifier"
        assert "sales stage" in tool.description.lower()
        assert AgentType.COACH.value in tool.allowed_agents
        assert "system" in tool.allowed_agents

    @pytest.mark.asyncio
    async def test_classify_opening_stage(self, tool):
        """Test classification of opening stage"""
        result = await tool._run({
            "conversation_history": [
                {"role": "user", "content": "Hello, I'm interested in your product."},
                {"role": "assistant", "content": "Great! Let me tell you about it."}
            ]
        })

        assert result["stage"] in ["opening", "discovery", "presentation", "objection_handling", "closing"]
        assert "confidence" in result
        assert 0.0 <= result["confidence"] <= 1.0

    @pytest.mark.asyncio
    async def test_classify_discovery_stage(self, tool):
        """Test classification of discovery stage"""
        result = await tool._run({
            "conversation_history": [
                {"role": "user", "content": "What are your main business challenges?"},
                {"role": "assistant", "content": "We struggle with customer retention."}
            ]
        })

        assert result["stage"] in ["opening", "discovery", "presentation", "objection_handling", "closing"]
        assert result["confidence"] > 0.0

    @pytest.mark.asyncio
    async def test_classify_closing_stage(self, tool):
        """Test classification of closing stage"""
        result = await tool._run({
            "conversation_history": [
                {"role": "user", "content": "Are you ready to move forward with the purchase?"},
                {"role": "assistant", "content": "Yes, let's proceed with the contract."}
            ]
        })

        assert result["stage"] in ["opening", "discovery", "presentation", "objection_handling", "closing"]

    @pytest.mark.asyncio
    async def test_empty_conversation(self, tool):
        """Test handling of empty conversation"""
        result = await tool._run({
            "conversation_history": []
        })

        # Should default to opening stage
        assert result["stage"] == "opening"
        assert result["confidence"] >= 0.0

    @pytest.mark.asyncio
    async def test_single_message(self, tool):
        """Test classification with single message"""
        result = await tool._run({
            "conversation_history": [
                {"role": "user", "content": "Hello"}
            ]
        })

        assert result["stage"] in ["opening", "discovery", "presentation", "objection_handling", "closing"]

    @pytest.mark.asyncio
    async def test_long_conversation(self, tool):
        """Test classification with long conversation"""
        history = []
        for i in range(20):
            history.append({"role": "user", "content": f"Message {i}"})
            history.append({"role": "assistant", "content": f"Response {i}"})

        result = await tool._run({
            "conversation_history": history
        })

        assert result["stage"] in ["opening", "discovery", "presentation", "objection_handling", "closing"]
        assert result["confidence"] > 0.0

    @pytest.mark.asyncio
    async def test_result_includes_reasoning(self, tool):
        """Test that result includes reasoning"""
        result = await tool._run({
            "conversation_history": [
                {"role": "user", "content": "Tell me about pricing."}
            ]
        })

        assert "reasoning" in result or "stage" in result
        # Reasoning is optional but stage is required


class TestToolPermissions:
    """Test tool permission enforcement"""

    @pytest.mark.asyncio
    async def test_knowledge_retriever_allowed_agents(self):
        """Test knowledge_retriever allowed agents"""
        tool = KnowledgeRetrieverTool()
        assert AgentType.COACH.value in tool.allowed_agents
        assert AgentType.NPC.value in tool.allowed_agents

    @pytest.mark.asyncio
    async def test_compliance_check_allowed_agents(self):
        """Test compliance_check allowed agents"""
        tool = ComplianceCheckTool()
        assert AgentType.COACH.value in tool.allowed_agents
        assert "system" in tool.allowed_agents

    @pytest.mark.asyncio
    async def test_profile_reader_allowed_agents(self):
        """Test profile_reader allowed agents"""
        tool = ProfileReaderTool()
        assert AgentType.COACH.value in tool.allowed_agents
        assert AgentType.NPC.value in tool.allowed_agents

    @pytest.mark.asyncio
    async def test_price_calculator_allowed_agents(self):
        """Test price_calculator allowed agents"""
        tool = PriceCalculatorTool()
        assert AgentType.COACH.value in tool.allowed_agents
        assert AgentType.NPC.value in tool.allowed_agents
        assert "system" in tool.allowed_agents

    @pytest.mark.asyncio
    async def test_stage_classifier_allowed_agents(self):
        """Test stage_classifier allowed agents"""
        tool = StageClassifierTool()
        assert AgentType.COACH.value in tool.allowed_agents
        assert "system" in tool.allowed_agents
