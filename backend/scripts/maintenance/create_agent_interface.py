#!/usr/bin/env python3
"""
Create Agent-Data Mapping Interface
Connect agents to knowledge base

Features:
1. Knowledge retriever interface with semantic vector search
2. Agent-specific query methods
3. Context-aware search
4. Metadata filtering

Updated: 2026-02-01 - Integrated SimpleVectorStore for semantic retrieval
"""

import sys
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import semantic vector store
try:
    from scripts.fix_semantic_search import SimpleVectorStore
    SEMANTIC_SEARCH_AVAILABLE = True
except ImportError:
    print("[WARN] SimpleVectorStore not available, falling back to keyword search")
    SimpleVectorStore = None
    SEMANTIC_SEARCH_AVAILABLE = False


class KnowledgeRetriever:
    """Knowledge retriever for agent-data mapping with semantic vector search"""

    def __init__(self, chroma_path: str = "storage/chromadb", chunks_file: str = "data/processed/semantic_chunks.json"):
        self.chroma_path = Path(chroma_path)
        self.chunks_file = Path(chunks_file)
        self.collection_name = "sales_knowledge"
        self.client = None
        self.collection = None
        self.chunks_cache = None

        # Semantic vector store
        self.vector_store = None
        self.use_semantic_search = SEMANTIC_SEARCH_AVAILABLE

    def initialize(self):
        """Initialize knowledge retriever with semantic vector search"""
        print("\n=== Initialize Knowledge Retriever ===")

        # Load chunks from file (always needed for fallback)
        if self.chunks_file.exists():
            with open(self.chunks_file, 'r', encoding='utf-8') as f:
                self.chunks_cache = json.load(f)
            print(f"[OK] Loaded {len(self.chunks_cache)} chunks from file")
        else:
            print(f"[WARN] Chunks file not found: {self.chunks_file}")
            self.chunks_cache = []

        # Initialize semantic vector store (preferred method)
        if self.use_semantic_search and SimpleVectorStore:
            try:
                print("[INFO] Initializing semantic vector store...")
                self.vector_store = SimpleVectorStore()
                self.vector_store.load_data(str(self.chunks_file))
                print("[OK] Semantic vector search enabled")
                return True
            except Exception as e:
                print(f"[WARN] Semantic vector store initialization failed: {e}")
                print("[INFO] Falling back to keyword search")
                self.use_semantic_search = False

        # Fallback: Try to initialize ChromaDB
        if not self.use_semantic_search:
            try:
                import chromadb
                self.client = chromadb.PersistentClient(path=str(self.chroma_path))
                try:
                    self.collection = self.client.get_collection(self.collection_name)
                    print(f"[OK] Connected to ChromaDB collection: {self.collection_name}")
                    print(f"[OK] Collection has {self.collection.count()} documents")
                except:
                    print(f"[WARN] Collection not found: {self.collection_name}")
                    print("[INFO] Using keyword search fallback")
            except Exception as e:
                print(f"[WARN] ChromaDB not available: {e}")
                print("[INFO] Using keyword search fallback")

        return True

    def search_by_keyword(self, query: str, top_k: int = 5, chunk_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Search knowledge base by keyword or semantic similarity

        Priority:
        1. Semantic vector search (if available)
        2. Keyword search (fallback)
        """
        print(f"\n[INFO] Searching for: {query}")

        # Use semantic vector search if available
        if self.use_semantic_search and self.vector_store:
            try:
                results = self.vector_store.search(
                    query=query,
                    top_k=top_k,
                    min_score=0.3,  # Minimum similarity threshold
                    filter_type=chunk_type
                )
                print(f"[OK] Semantic search returned {len(results)} results")
                return results
            except Exception as e:
                print(f"[WARN] Semantic search failed: {e}, falling back to keyword search")

        # Fallback: Use file-based keyword search
        results = []

        for chunk in self.chunks_cache:
            # Filter by type if specified
            if chunk_type and chunk['type'] != chunk_type:
                continue

            # Simple keyword matching (case-insensitive)
            if query.lower() in chunk['text'].lower():
                results.append({
                    "id": chunk['id'],
                    "text": chunk['text'],
                    "source": chunk['source'],
                    "type": chunk['type'],
                    "metadata": chunk.get('metadata', {}),
                    "score": chunk['text'].lower().count(query.lower())  # Simple relevance score
                })

        # Sort by score
        results.sort(key=lambda x: x['score'], reverse=True)

        # Return top_k results
        return results[:top_k]

    def search_by_type(self, chunk_type: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get chunks by type"""
        print(f"\n[INFO] Retrieving chunks of type: {chunk_type}")

        results = []
        for chunk in self.chunks_cache:
            if chunk['type'] == chunk_type:
                results.append({
                    "id": chunk['id'],
                    "text": chunk['text'],
                    "source": chunk['source'],
                    "type": chunk['type'],
                    "metadata": chunk.get('metadata', {})
                })

            if len(results) >= limit:
                break

        return results

    def get_champion_cases(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get champion sales cases"""
        return self.search_by_type("champion_case", limit=limit)

    def get_training_scenarios(self, objection_type: Optional[str] = None, limit: int = 10) -> List[Dict[str, Any]]:
        """Get training scenarios"""
        results = []

        for chunk in self.chunks_cache:
            if chunk['type'] == "training_scenario":
                # Filter by objection type if specified
                if objection_type:
                    metadata = chunk.get('metadata', {})
                    if metadata.get('objection_type') != objection_type:
                        continue

                results.append({
                    "id": chunk['id'],
                    "text": chunk['text'],
                    "source": chunk['source'],
                    "type": chunk['type'],
                    "metadata": chunk.get('metadata', {})
                })

                if len(results) >= limit:
                    break

        return results

    def get_sales_sop(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get sales SOP documents"""
        return self.search_by_type("sales_sop", limit=limit)

    def get_statistics(self) -> Dict[str, Any]:
        """Get knowledge base statistics"""
        stats = {
            "total_chunks": len(self.chunks_cache),
            "chunks_by_type": {},
            "chunks_by_source": {},
            "total_characters": sum(c['char_count'] for c in self.chunks_cache),
            "average_chunk_size": sum(c['char_count'] for c in self.chunks_cache) / len(self.chunks_cache) if self.chunks_cache else 0
        }

        for chunk in self.chunks_cache:
            # Count by type
            chunk_type = chunk['type']
            stats['chunks_by_type'][chunk_type] = stats['chunks_by_type'].get(chunk_type, 0) + 1

            # Count by source
            source = chunk['source']
            stats['chunks_by_source'][source] = stats['chunks_by_source'].get(source, 0) + 1

        return stats


class AgentKnowledgeInterface:
    """Agent-specific knowledge interface"""

    def __init__(self, retriever: KnowledgeRetriever):
        self.retriever = retriever

    def coach_agent_query(self, user_question: str) -> List[Dict[str, Any]]:
        """Query knowledge for coach agent"""
        print("\n=== Coach Agent Query ===")

        # Search for relevant champion cases and training scenarios
        results = []

        # Get champion cases
        champion_results = self.retriever.search_by_keyword(user_question, top_k=3, chunk_type="champion_case")
        results.extend(champion_results)

        # Get training scenarios
        scenario_results = self.retriever.search_by_keyword(user_question, top_k=2, chunk_type="training_scenario")
        results.extend(scenario_results)

        print(f"[OK] Found {len(results)} relevant knowledge chunks")
        return results

    def compliance_agent_query(self, compliance_topic: str) -> List[Dict[str, Any]]:
        """Query knowledge for compliance agent"""
        print("\n=== Compliance Agent Query ===")

        # Search for relevant SOP documents
        results = self.retriever.search_by_keyword(compliance_topic, top_k=5, chunk_type="sales_sop")

        print(f"[OK] Found {len(results)} relevant SOP documents")
        return results

    def practice_agent_query(self, scenario_type: str) -> List[Dict[str, Any]]:
        """Query knowledge for practice agent"""
        print("\n=== Practice Agent Query ===")

        # Get training scenarios by objection type
        results = self.retriever.get_training_scenarios(objection_type=scenario_type, limit=5)

        print(f"[OK] Found {len(results)} training scenarios")
        return results


def main():
    """Main function"""
    print("="*70)
    print("Agent-Data Mapping Interface")
    print("="*70)

    # 1. Initialize retriever
    retriever = KnowledgeRetriever()
    retriever.initialize()

    # 2. Get statistics
    stats = retriever.get_statistics()
    print("\n=== Knowledge Base Statistics ===")
    print(f"Total chunks: {stats['total_chunks']}")
    print(f"Total characters: {stats['total_characters']:,}")
    print(f"Average chunk size: {stats['average_chunk_size']:.0f} chars")
    print("\nChunks by type:")
    for chunk_type, count in stats['chunks_by_type'].items():
        print(f"  {chunk_type}: {count}")

    # 3. Create agent interface
    agent_interface = AgentKnowledgeInterface(retriever)

    # 4. Test queries
    print("\n=== Test Agent Queries ===")

    # Test coach agent query
    coach_results = agent_interface.coach_agent_query("如何处理客户的价格异议？")
    if coach_results:
        print("\nCoach Agent Result 1:")
        print(f"  Type: {coach_results[0]['type']}")
        print(f"  Source: {coach_results[0]['source']}")
        print(f"  Preview: {coach_results[0]['text'][:100]}...")

    # Test practice agent query
    practice_results = agent_interface.practice_agent_query("price")
    if practice_results:
        print("\nPractice Agent Result 1:")
        print(f"  Type: {practice_results[0]['type']}")
        print(f"  Metadata: {practice_results[0]['metadata']}")
        print(f"  Preview: {practice_results[0]['text'][:100]}...")

    # 5. Save interface configuration
    config = {
        "created_at": datetime.now().isoformat(),
        "retriever_config": {
            "chroma_path": str(retriever.chroma_path),
            "chunks_file": str(retriever.chunks_file),
            "collection_name": retriever.collection_name
        },
        "agent_interfaces": {
            "coach_agent": {
                "query_method": "coach_agent_query",
                "supported_types": ["champion_case", "training_scenario"]
            },
            "compliance_agent": {
                "query_method": "compliance_agent_query",
                "supported_types": ["sales_sop"]
            },
            "practice_agent": {
                "query_method": "practice_agent_query",
                "supported_types": ["training_scenario"]
            }
        },
        "statistics": stats
    }

    config_file = Path("data/processed/agent_interface_config.json")
    with open(config_file, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=2)

    print(f"\n[OK] Interface configuration saved to: {config_file}")

    print("\n" + "="*70)
    print("[OK] Agent-data mapping interface created successfully!")
    print("="*70)
    print("\nNext steps:")
    print("1. Integrate with existing agents in app/agents/")
    print("2. Test with real agent queries")
    print("3. Deploy to production environment")


if __name__ == "__main__":
    main()
