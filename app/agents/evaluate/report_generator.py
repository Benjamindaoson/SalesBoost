import logging
import json
from datetime import datetime
from typing import Any, List

from app.infra.gateway.model_gateway import ModelGateway
from app.infra.gateway.schemas import ModelCall, RoutingContext
from app.agents.evaluate.strategy_analyzer import StrategyAnalyzer
from schemas.reports import (
    RadarChartData,
    SessionSummary,
    TrainingReport,
    StrategyComparison
)

logger = logging.getLogger(__name__)

class ReportService:
    def __init__(self, model_gateway: ModelGateway = None):
        self.model_gateway = model_gateway or ModelGateway()
        self.strategy_analyzer = StrategyAnalyzer(self.model_gateway)

    async def generate_report(self, session, messages: List[Any], include_turn_details: bool = True) -> TrainingReport:
        """
        Generate a comprehensive training report using AI analysis.
        """
        logger.info(f"Generating real AI report for session: {session.id}")
        
        # 1. Strategy Analysis (New)
        strategy_analysis = await self.strategy_analyzer.analyze_strategy_deviation(session.id, messages)
        
        # 2. Prepare conversation history for AI analysis
        history_text = "\n".join([
            f"{'Sales' if m.role == 'sales' else 'Customer'}: {m.content}"
            for m in messages
        ])

        # 2. Construct Evaluation Prompt
        system_prompt = """
        You are an expert sales performance evaluator. 
        Analyze the provided sales conversation and output a JSON report.
        Dimensions: 
        - Integrity (0-10): Did the salesperson follow the full process?
        - Relevance (0-10): Were the responses tailored to customer needs?
        - Correctness (0-10): Was the product info accurate?
        - Logic (0-10): Was the persuasion flow logical?
        - Compliance (0-10): Did they avoid forbidden words or false promises?
        
        Output Format:
        {
            "overall_score": float,
            "dimension_scores": {"integrity": float, "relevance": float, ...},
            "dimension_feedback": {"integrity": "...", ...},
            "top_strengths": ["..."],
            "top_improvements": ["..."],
            "recommended_focus": "..."
        }
        """
        
        call = ModelCall(
            prompt=f"Conversation History:\n{history_text}",
            system_prompt=system_prompt
        )
        context = RoutingContext(session_id=session.id, agent_type="evaluator")
        
        try:
            raw_response = await self.model_gateway.call(call, context)
            # Try to parse JSON from response
            # Note: In production, use more robust JSON extractor
            eval_data = json.loads(raw_response.strip("```json").strip("```"))
        except Exception as e:
            logger.error(f"AI Evaluation failed: {e}. Using fallback values.")
            eval_data = self._get_fallback_eval()

        # 3. Build Report Objects
        summary = SessionSummary(
            session_id=session.id,
            user_id=session.user_id,
            scenario_name=getattr(session, "scenario_name", "General Sales"),
            persona_name=getattr(session, "persona_name", "Customer"),
            started_at=session.started_at,
            completed_at=datetime.utcnow(),
            duration_minutes=int((datetime.utcnow() - session.started_at).total_seconds() / 60),
            total_turns=len(messages) // 2,
            final_stage=session.final_stage or "Completed",
            completion_rate=100.0 if session.final_stage == "Closed" else 80.0,
        )

        # 4. Self-Consistency Verification (Audit Requirement)
        await self._verify_self_consistency(eval_data)

        radar = RadarChartData(
            values=[
                eval_data["dimension_scores"].get("integrity", 0),
                eval_data["dimension_scores"].get("relevance", 0),
                eval_data["dimension_scores"].get("correctness", 0),
                eval_data["dimension_scores"].get("logic", 0),
                eval_data["dimension_scores"].get("compliance", 0),
            ]
        )

        # Convert strategy comparisons to Schema objects
        comparisons = [
            StrategyComparison(**comp) 
            for comp in strategy_analysis.get("strategy_comparisons", [])
        ]

        return TrainingReport(
            summary=summary,
            overall_score=eval_data.get("overall_score", 0.0),
            radar_chart=radar,
            dimension_scores=eval_data["dimension_scores"],
            dimension_feedback=eval_data["dimension_feedback"],
            stage_performances=[], 
            turn_details=None,
            top_strengths=eval_data.get("top_strengths", []),
            top_improvements=eval_data.get("top_improvements", []),
            recommended_focus=eval_data.get("recommended_focus", ""),
            strategy_comparisons=comparisons,
            overall_optimal_rate=strategy_analysis.get("overall_optimal_rate"),
            generated_at=datetime.utcnow(),
        )

    async def _verify_self_consistency(self, eval_data: dict) -> None:
        """
        Verify if the generated scores align with the sentiment of the feedback.
        If scores are high but feedback is negative, log a warning or adjust.
        """
        scores = eval_data.get("dimension_scores", {})
        feedback = eval_data.get("dimension_feedback", {})
        
        for dim, score in scores.items():
            fb_text = feedback.get(dim, "").lower()
            # Simple heuristic: if score is high (>8) but feedback contains negative keywords
            negative_keywords = ["bad", "poor", "fail", "error", "weak", "incorrect", "不佳", "错误", "差"]
            if score > 8 and any(kw in fb_text for kw in negative_keywords):
                logger.warning(f"Self-consistency warning: High score ({score}) for {dim} but feedback is negative: {fb_text}")
                # Optional: Force AI to re-evaluate or cap the score
                eval_data["dimension_scores"][dim] = 7.5

    def _get_fallback_eval(self) -> dict:
        return {
            "overall_score": 5.0,
            "dimension_scores": {"integrity": 5, "relevance": 5, "correctness": 5, "logic": 5, "compliance": 5},
            "dimension_feedback": {"integrity": "Analysis failed", "relevance": "Analysis failed", "correctness": "Analysis failed", "logic": "Analysis failed", "compliance": "Analysis failed"},
            "top_strengths": ["Basic participation"],
            "top_improvements": ["System analysis error"],
            "recommended_focus": "Re-run training"
        }
