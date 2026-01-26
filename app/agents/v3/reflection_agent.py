import logging
from typing import List, Optional, Type, Dict
from pydantic import BaseModel, Field

from app.agents.roles.base import BaseAgent
from app.services.memory_service import memory_service

logger = logging.getLogger(__name__)

class KeyInsight(BaseModel):
    category: str = Field(description="Insight category: strength, weakness, opportunity")
    content: str = Field(description="The insight content")
    actionable: bool = Field(description="Is this insight actionable?")

class ReflectionOutput(BaseModel):
    summary: str = Field(description="Brief summary of the conversation performance")
    score: float = Field(description="Overall performance score 0-100")
    insights: List[KeyInsight] = Field(description="Key insights extracted from the session")
    skill_updates: List[str] = Field(description="Skills that showed improvement or regression (format: 'skill_name:+0.1' or 'skill_name:-0.1')")
    plan_for_next: str = Field(description="Suggestion for the next training focus")

class ReflectionAgent(BaseAgent):
    """
    Reflection Agent (Memory Engineering)
    Analyzes completed sessions to extract long-term memories and update user profile.
    """

    def __init__(self, **kwargs):
        super().__init__(temperature=0.4, model_name="gpt-4o", **kwargs)

    @property
    def system_prompt(self) -> str:
        return """You are an Expert Sales Coach and Cognitive Architect.
Your goal is to perform a "Post-Mortem Analysis" (Reflection) on a completed sales training session.

Your analysis will be used to:
1. Update the user's Long-Term Memory (what worked, what didn't).
2. Adjust the User's Skill Profile.
3. Plan the next training step.

Analyze the conversation history strictly based on:
- Adherence to sales techniques (Opening, Discovery, Objection Handling, Closing).
- Empathy and communication style.
- Strategic thinking.

Output must be structured JSON.
"""

    @property
    def output_schema(self) -> Type[BaseModel]:
        return ReflectionOutput

    async def reflect_and_store(self, user_id: str, session_id: str, conversation_history: List[Dict]):
        """
        Run reflection pipeline:
        1. Analyze history
        2. Generate insights
        3. Update Memory Service
        """
        # Format history for LLM
        history_text = "\n".join([f"{msg['role']}: {msg['content']}" for msg in conversation_history])
        
        memory_context = await memory_service.get_relevant_context(
            user_id=user_id,
            query="sales training reflection",
        )
        user_prompt = f"""
Analyze this sales training session for User ID: {user_id}.

Existing Memory Context:
{memory_context}

Conversation History:
{history_text}

Provide a structured reflection.
"""
        try:
            # 1. Generate Reflection
            reflection: ReflectionOutput = await self.invoke_with_parser(user_prompt)
            
            # 2. Store Summary as Episodic/Semantic Memory
            await memory_service.add_long_term_memory(
                user_id=user_id,
                content=f"Session {session_id} Summary: {reflection.summary}. Score: {reflection.score}",
                category="reflection",
                session_id=session_id,
                metadata={"score": reflection.score}
            )
            
            # 3. Store Insights as Facts/Rules
            for insight in reflection.insights:
                await memory_service.add_long_term_memory(
                    user_id=user_id,
                    content=f"Insight: {insight.content}",
                    category="fact" if insight.actionable else "observation",
                    session_id=session_id,
                    metadata={"type": insight.category}
                )
            
            # 4. Update Skill Profile
            for update in reflection.skill_updates:
                try:
                    skill, delta_str = update.split(":")
                    delta = float(delta_str)
                    await memory_service.update_skill_level(user_id, skill.strip(), delta)
                except Exception as e:
                    logger.warning(f"Failed to parse skill update '{update}': {e}")
            
            logger.info(f"Reflection completed for session {session_id}")
            return reflection
            
        except Exception as e:
            logger.error(f"Reflection failed: {e}")
            raise
