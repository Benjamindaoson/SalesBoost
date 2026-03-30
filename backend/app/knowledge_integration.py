"""
Knowledge Integration Module
Integrate knowledge retriever with existing agents

This module provides a bridge between the knowledge base and existing agents.
"""

import sys
from pathlib import Path
from typing import List, Dict, Any, Optional

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import the knowledge retriever
try:
    from scripts.create_agent_interface import KnowledgeRetriever, AgentKnowledgeInterface
except ImportError:
    print("[WARN] Knowledge retriever not found, using fallback")
    KnowledgeRetriever = None
    AgentKnowledgeInterface = None


class KnowledgeIntegration:
    """Integration layer for knowledge base access"""

    _instance = None
    _retriever = None
    _agent_interface = None

    def __new__(cls):
        """Singleton pattern to ensure single instance"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def initialize(self):
        """Initialize knowledge integration"""
        if self._retriever is None and KnowledgeRetriever:
            self._retriever = KnowledgeRetriever()
            self._retriever.initialize()
            self._agent_interface = AgentKnowledgeInterface(self._retriever)
            print("[OK] Knowledge integration initialized")
        return self._retriever is not None

    def get_retriever(self) -> Optional[Any]:
        """Get knowledge retriever instance"""
        if self._retriever is None:
            self.initialize()
        return self._retriever

    def get_agent_interface(self) -> Optional[Any]:
        """Get agent interface instance"""
        if self._agent_interface is None:
            self.initialize()
        return self._agent_interface

    def search_knowledge(self, query: str, agent_type: str = "coach", top_k: int = 5) -> List[Dict[str, Any]]:
        """
        Search knowledge base for agent queries

        Args:
            query: Search query
            agent_type: Type of agent (coach, compliance, practice)
            top_k: Number of results to return

        Returns:
            List of relevant knowledge chunks
        """
        if not self.initialize():
            return []

        try:
            if agent_type == "coach":
                return self._agent_interface.coach_agent_query(query)
            elif agent_type == "compliance":
                return self._agent_interface.compliance_agent_query(query)
            elif agent_type == "practice":
                return self._agent_interface.practice_agent_query(query)
            else:
                # Default to keyword search
                return self._retriever.search_by_keyword(query, top_k=top_k)
        except Exception as e:
            print(f"[ERROR] Knowledge search failed: {e}")
            return []

    def get_champion_cases(self, limit: int = 5) -> List[Dict[str, Any]]:
        """Get champion sales cases"""
        if not self.initialize():
            return []

        try:
            return self._retriever.get_champion_cases(limit=limit)
        except Exception as e:
            print(f"[ERROR] Failed to get champion cases: {e}")
            return []

    def get_training_scenarios(self, objection_type: Optional[str] = None, limit: int = 5) -> List[Dict[str, Any]]:
        """Get training scenarios"""
        if not self.initialize():
            return []

        try:
            return self._retriever.get_training_scenarios(objection_type=objection_type, limit=limit)
        except Exception as e:
            print(f"[ERROR] Failed to get training scenarios: {e}")
            return []

    def format_knowledge_for_prompt(self, knowledge_chunks: List[Dict[str, Any]], max_length: int = 2000) -> str:
        """
        Format knowledge chunks for LLM prompt

        Args:
            knowledge_chunks: List of knowledge chunks
            max_length: Maximum length of formatted text

        Returns:
            Formatted knowledge text
        """
        if not knowledge_chunks:
            return ""

        formatted_parts = []
        current_length = 0

        for i, chunk in enumerate(knowledge_chunks, 1):
            chunk_text = f"\n[Knowledge {i}]\nSource: {chunk['source']}\nType: {chunk['type']}\n\n{chunk['text']}\n"

            if current_length + len(chunk_text) > max_length:
                break

            formatted_parts.append(chunk_text)
            current_length += len(chunk_text)

        return "\n".join(formatted_parts)


# Global instance
knowledge_integration = KnowledgeIntegration()


def get_knowledge_integration() -> KnowledgeIntegration:
    """Get global knowledge integration instance"""
    return knowledge_integration


# Example usage functions for agents
def enhance_coach_response(user_query: str, base_response: str) -> str:
    """
    Enhance coach agent response with knowledge base

    Args:
        user_query: User's question
        base_response: Base response from agent

    Returns:
        Enhanced response with relevant knowledge
    """
    ki = get_knowledge_integration()

    # Search for relevant knowledge
    knowledge = ki.search_knowledge(user_query, agent_type="coach", top_k=3)

    if not knowledge:
        return base_response

    # Format knowledge for context
    knowledge_context = ki.format_knowledge_for_prompt(knowledge, max_length=1000)

    # Combine base response with knowledge
    enhanced_response = f"{base_response}\n\n[Relevant Knowledge]\n{knowledge_context}"

    return enhanced_response


def get_practice_scenario(objection_type: str = "price") -> Optional[Dict[str, Any]]:
    """
    Get a practice scenario for training

    Args:
        objection_type: Type of objection (price, feature, competitor, timing)

    Returns:
        Practice scenario or None
    """
    ki = get_knowledge_integration()

    scenarios = ki.get_training_scenarios(objection_type=objection_type, limit=1)

    return scenarios[0] if scenarios else None


def get_compliance_guidance(topic: str) -> List[Dict[str, Any]]:
    """
    Get compliance guidance from knowledge base

    Args:
        topic: Compliance topic

    Returns:
        List of relevant compliance documents
    """
    ki = get_knowledge_integration()

    return ki.search_knowledge(topic, agent_type="compliance", top_k=5)


if __name__ == "__main__":
    # Test the integration
    print("="*70)
    print("Knowledge Integration Test")
    print("="*70)

    ki = get_knowledge_integration()

    if ki.initialize():
        print("\n[OK] Knowledge integration initialized successfully")

        # Test coach query
        print("\n=== Test Coach Query ===")
        results = ki.search_knowledge("价格异议", agent_type="coach")
        print(f"Found {len(results)} results")

        # Test getting champion cases
        print("\n=== Test Champion Cases ===")
        cases = ki.get_champion_cases(limit=3)
        print(f"Found {len(cases)} champion cases")

        # Test getting training scenarios
        print("\n=== Test Training Scenarios ===")
        scenarios = ki.get_training_scenarios(objection_type="price", limit=2)
        print(f"Found {len(scenarios)} training scenarios")

        # Test formatting for prompt
        if results:
            print("\n=== Test Prompt Formatting ===")
            formatted = ki.format_knowledge_for_prompt(results[:2], max_length=500)
            print(f"Formatted length: {len(formatted)} characters")
            print(f"Preview:\n{formatted[:200]}...")

        print("\n[OK] All tests passed!")
    else:
        print("\n[X] Knowledge integration initialization failed")
