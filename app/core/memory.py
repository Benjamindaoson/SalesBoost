import logging
import json
import uuid
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)

@dataclass
class MemoryEntry:
    id: str
    content: str
    category: str # "episodic", "semantic", "procedural"
    created_at: str
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class UserProfile:
    user_id: str
    traits: Dict[str, Any] = field(default_factory=dict)
    long_term_facts: List[str] = field(default_factory=list)
    skill_levels: Dict[str, float] = field(default_factory=dict) # e.g. {"opening": 0.8}

class MemoryManager:
    """
    Cognitive Architecture Memory Manager (Simulated Mem0)
    Manages Episodic (Short-term), Semantic (Long-term), and User Profile.
    """
    
    def __init__(self):
        # In-memory storage for demo. In prod, use Redis/Postgres/VectorDB
        self.episodic_memory: Dict[str, List[MemoryEntry]] = {} # session_id -> entries
        self.user_profiles: Dict[str, UserProfile] = {} # user_id -> profile
        self.semantic_memory: Dict[str, List[MemoryEntry]] = {} # user_id -> facts
        
    def get_user_profile(self, user_id: str) -> UserProfile:
        if user_id not in self.user_profiles:
            self.user_profiles[user_id] = UserProfile(user_id=user_id)
        return self.user_profiles[user_id]
    
    def add_episodic_memory(self, session_id: str, role: str, content: str, metadata: Dict = None):
        """Add a turn to short-term working memory"""
        if session_id not in self.episodic_memory:
            self.episodic_memory[session_id] = []
            
        entry = MemoryEntry(
            id=str(uuid.uuid4()),
            content=content,
            category="episodic",
            created_at=datetime.now().isoformat(),
            metadata={"role": role, **(metadata or {})}
        )
        self.episodic_memory[session_id].append(entry)
        
        # Trigger consolidation (simulation)
        if len(self.episodic_memory[session_id]) % 5 == 0:
            self.consolidate_memory(session_id, "user_default") # Mock user_id

    def consolidate_memory(self, session_id: str, user_id: str):
        """
        Background process to extract Semantic Memory from Episodic Memory.
        (Simulates 'Sleep' consolidation in human brain)
        """
        recent_memories = self.episodic_memory[session_id][-5:]
        text = "\n".join([f"{m.metadata.get('role')}: {m.content}" for m in recent_memories])
        
        # Heuristic extraction (Mock LLM extraction)
        # In real system: Call LLM to extract facts
        profile = self.get_user_profile(user_id)
        
        # Example heuristic: if user mentions specific keywords
        if "不懂" in text or "怎么做" in text:
            # User is struggling -> Update skill level
            current_skill = profile.skill_levels.get("general", 0.5)
            profile.skill_levels["general"] = max(0.1, current_skill - 0.05)
            logger.info(f"Memory Consolidation: Detected struggle, adjusted skill level to {profile.skill_levels['general']}")
            
        if "我叫" in text:
            # Extract name (Mock)
            pass

    def get_relevant_context(self, user_id: str, query: str, session_id: str) -> str:
        """
        Retrieve relevant context from all memory tiers.
        """
        profile = self.get_user_profile(user_id)
        
        # 1. Profile Context
        context = [f"User Profile: {json.dumps(profile.traits)}"]
        
        # 2. Long-term Facts
        if profile.long_term_facts:
            context.append("Known Facts:\n" + "\n".join(profile.long_term_facts[-3:]))
            
        # 3. Recent Episodic (Working Memory)
        if session_id in self.episodic_memory:
            recent = self.episodic_memory[session_id][-5:]
            history = "\n".join([f"{m.metadata.get('role')}: {m.content}" for m in recent])
            context.append(f"Recent Conversation:\n{history}")
            
        return "\n\n".join(context)

# Singleton
memory_manager = MemoryManager()
