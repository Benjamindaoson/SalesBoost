
import asyncio
import logging
from cognitive.skills.study.advanced_rag_service import AdvancedRAGService
from cognitive.infra.gateway.model_gateway import ModelGateway

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def main():
    print("--- Starting Verification ---")
    
    # Initialize RAG Service (GraphRAG enabled)
    rag = AdvancedRAGService(enable_graph_rag=True)
    
    # Test Question
    question = "如果客户说年费太贵，我应该用哪个具体的权益来回击？"
    print(f"\nQuestion: {question}")
    
    # 1. Search (GraphRAG + Vector)
    results = await rag.search(question, top_k=3)
    
    print("\n--- Retrieval Results ---")
    for res in results:
        print(f"[{res.get('source', 'Unknown')}] Score: {res.get('score', 0)}")
        print(f"Content: {res['content'][:100]}...")
        print("-" * 20)
        
    # 2. Generate Answer (using Model Gateway)
    gateway = ModelGateway()
    context_str = "\n".join([r['content'] for r in results])
    messages = [
        {"role": "system", "content": "You are a professional sales assistant. Use the provided context to answer the question."},
        {"role": "user", "content": f"Context:\n{context_str}\n\nQuestion: {question}"}
    ]
    
    from cognitive.infra.gateway.model_gateway.schemas import RoutingContext, AgentType, LatencyMode
    routing_context = RoutingContext(
        session_id="test_session",
        agent_type=AgentType.RETRIEVER, # Changed from ASSISTANT to RETRIEVER (valid enum)
        latency_mode=LatencyMode.SLOW,
        turn_importance=0.5,
        budget_remaining=1.0,
        turn_number=1
    )
    
    print("\n--- Generating Answer ---")
    try:
        response = await gateway.chat(
            agent_type=AgentType.RETRIEVER,
            messages=messages,
            context=routing_context
        )
        print(f"Answer: {response['content']}")
    except Exception as e:
        print(f"Generation failed: {e}")

if __name__ == "__main__":
    asyncio.run(main())
