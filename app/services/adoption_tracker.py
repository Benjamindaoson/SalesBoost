"""
采纳追踪服务
实现「建议采纳 → 能力变化」的因果账本
"""
import os
import uuid
import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, Integer

from app.models.adoption_models import AdoptionRecord, AdoptionStyle, StrategyDecision
from app.schemas.agent_outputs import CoachOutput, EvaluatorOutput
from app.schemas.strategy import AdoptionAnalysis

logger = logging.getLogger(__name__)

OFFLINE_MODE = bool(
    os.environ.get("PYTEST_CURRENT_TEST")
    or os.environ.get("PYTEST_ADDOPTS")
    or os.environ.get("CI")
)

# 尝试导入 sentence_transformers 实现真正的语义匹配
try:
    from sentence_transformers import SentenceTransformer, util
    HAS_VECTORS = True
except ImportError:
    HAS_VECTORS = False
    logger.warning("sentence-transformers not installed. AdoptionTracker using string matching fallback.")
if OFFLINE_MODE:
    HAS_VECTORS = False

class AdoptionTracker:
    """
    采纳追踪器
    
    核心职责：
    1. 在 Evaluator 阶段检测建议是否被采纳
    2. 计算采纳后的能力变化 (skill_delta)
    3. 写入因果账本 (AdoptionRecord)
    """
    
    # 采纳检测阈值
    SIMILARITY_THRESHOLD = 0.6
    EFFECTIVENESS_THRESHOLD = 0.5
    VECTOR_SIMILARITY_THRESHOLD = 0.7  # 向量相似度阈值
    
    _model = None  # Class level singleton for model
    
    def __init__(self):
        self._pending_suggestions: Dict[str, Dict] = {}
        self._init_model()
    
    def _init_model(self):
        global HAS_VECTORS
        if HAS_VECTORS and AdoptionTracker._model is None:
            try:
                logger.info("Loading SentenceTransformer model for AdoptionTracker...")
                AdoptionTracker._model = SentenceTransformer('all-MiniLM-L6-v2')
                logger.info("SentenceTransformer model loaded successfully.")
            except Exception as e:
                logger.error(f"Failed to load SentenceTransformer: {e}")
                AdoptionTracker._model = None
                HAS_VECTORS = False
                
    def register_suggestion(
        self,
        session_id: str,
        turn_id: int,
        coach_output: CoachOutput,
        baseline_scores: Dict[str, float],
        stage: str,
        situation_type: Optional[str] = None,
    ) -> str:
        """
        注册待观察的建议
        """
        suggestion_id = str(uuid.uuid4())
        
        key = f"{session_id}:{turn_id}"
        self._pending_suggestions[key] = {
            "suggestion_id": suggestion_id,
            "suggestion_text": coach_output.suggestion,
            "example_utterance": coach_output.example_utterance,
            "technique_name": coach_output.technique_name,
            "baseline_scores": baseline_scores,
            "stage": stage,
            "situation_type": situation_type,
            "registered_at": datetime.utcnow(),
        }
        
        logger.info(f"Suggestion registered: {suggestion_id} at turn {turn_id}")
        return suggestion_id
    
    async def _check_first_time_adoption(self, db: AsyncSession, user_id: str, technique_name: str) -> bool:
        """Check if this is the first time effective adoption"""
        query = select(func.count(AdoptionRecord.id)).where(
            AdoptionRecord.user_id == user_id,
            AdoptionRecord.technique_name == technique_name,
            AdoptionRecord.is_effective == True
        )
        result = await db.execute(query)
        count = result.scalar() or 0
        return count == 0

    async def analyze_adoption(
        self,
        session_id: str,
        user_id: str,
        current_turn: int,
        user_message: str,
        current_scores: Dict[str, float],
        db: AsyncSession,
    ) -> Optional[AdoptionAnalysis]:
        """
        分析建议采纳情况（在 Evaluator 阶段调用）
        """
        result_analysis = None
        keys_to_remove = []
        
        # 检查前 1 轮和前 2 轮的建议
        for offset in [1, 2]:
            prev_turn = current_turn - offset
            key = f"{session_id}:{prev_turn}"
            
            if key not in self._pending_suggestions:
                continue
            
            pending = self._pending_suggestions[key]
            keys_to_remove.append(key)
            
            # 检测采纳
            adopted, style, evidence = self._detect_adoption(
                user_message=user_message,
                suggestion_text=pending["suggestion_text"],
                example_utterance=pending["example_utterance"],
            )
            
            # 计算能力变化（因果四要素之一）
            baseline = pending["baseline_scores"]
            skill_delta = {
                dim: round(current_scores.get(dim, 0) - baseline.get(dim, 0), 2)
                for dim in baseline.keys()
            }
            
            # Anti-Cheat: 复读机惩罚 (Parroting Penalty)
            # 如果是逐字复述 (VERBATIM)，虽然被视为采纳，但能力提升应当打折
            # 因为这代表的是记忆力而非理解力
            if style == AdoptionStyle.VERBATIM:
                logger.info(f"Applying Parroting Penalty for suggestion {pending['suggestion_id']}")
                for dim in skill_delta:
                    # 惩罚系数 0.3 (只给 30% 的功劳)
                    skill_delta[dim] = round(skill_delta[dim] * 0.3, 2)

            # 判断是否有效
            avg_delta = sum(skill_delta.values()) / len(skill_delta) if skill_delta else 0
            is_effective = adopted and avg_delta > self.EFFECTIVENESS_THRESHOLD
            effectiveness_score = round(max(0, avg_delta), 2) if adopted else 0
            
            # 生成反馈信号
            feedback_signal = "NO_ACTION"
            feedback_text = ""
            
            if adopted:
                if is_effective:
                    # Check first time
                    is_first_time = await self._check_first_time_adoption(db, user_id, pending['technique_name'])
                    if is_first_time:
                        feedback_signal = "FIRST_TIME_ACTION"
                        feedback_text = f"🎉 突破！这是你第一次成功运用 {pending['technique_name']} 技巧（提升 {avg_delta:.1f} 分）！"
                    else:
                        feedback_signal = "EFFECTIVE_ADOPTION"
                        feedback_text = f"成功采纳！你的能力提升了 {avg_delta:.1f} 分，这证明你掌握了 {pending['technique_name']} 技巧。"
                else:
                    feedback_signal = "NO_IMPROVEMENT"
                    feedback_text = f"你尝试了 {pending['technique_name']}，但效果不明显（提升 {avg_delta:.1f} 分）。注意语气和时机。"
            
            analysis = AdoptionAnalysis(
                suggestion_id=pending["suggestion_id"],
                adopted=adopted,
                adoption_style=style.value,
                adoption_evidence=evidence,
                baseline_scores=baseline,
                observed_scores=current_scores,
                skill_delta=skill_delta,
                is_effective=is_effective,
                effectiveness_score=effectiveness_score,
                feedback_signal=feedback_signal,
                feedback_text=feedback_text,
            )
            
            # 【关键】无论是否采纳，都要写入数据库形成完整样本
            await self._save_adoption_record(
                db=db,
                session_id=session_id,
                user_id=user_id,
                turn_id=prev_turn,
                pending=pending,
                analysis=analysis,
                observed_turn_offset=offset,
            )
            
            if adopted:
                logger.info(
                    f"[AdoptionTracker] 采纳检测成功: suggestion={pending['suggestion_id']}, "
                    f"style={style.value}, effective={is_effective}, delta={avg_delta:.2f}"
                )
                result_analysis = analysis
                break
            else:
                logger.debug(f"[AdoptionTracker] 未采纳: suggestion={pending['suggestion_id']}")
        
        # 清理已处理的建议
        for key in keys_to_remove:
            if key in self._pending_suggestions:
                del self._pending_suggestions[key]
        
        # 清理超过 3 轮的过期建议
        self._cleanup_stale_suggestions(session_id, current_turn)
        
        return result_analysis
    
    def _cleanup_stale_suggestions(self, session_id: str, current_turn: int) -> None:
        """清理超过 3 轮的过期建议"""
        stale_keys = []
        for key in self._pending_suggestions:
            if key.startswith(f"{session_id}:"):
                turn_str = key.split(":")[-1]
                try:
                    turn = int(turn_str)
                    if current_turn - turn > 3:
                        stale_keys.append(key)
                except ValueError:
                    pass
        
        for key in stale_keys:
            del self._pending_suggestions[key]
            logger.debug(f"[AdoptionTracker] 清理过期建议: {key}")

    def _detect_adoption(
        self,
        user_message: str,
        suggestion_text: str,
        example_utterance: str,
    ) -> Tuple[bool, AdoptionStyle, Optional[str]]:
        """
        检测用户是否采纳了建议
        优先使用向量相似度匹配，降级使用关键词匹配
        """
        user_lower = user_message.lower()
        
        # 0. 向量语义匹配 (如果可用)
        if HAS_VECTORS and AdoptionTracker._model:
            try:
                embeddings = AdoptionTracker._model.encode([user_message, example_utterance, suggestion_text])
                
                # 计算余弦相似度
                sim_example = util.cos_sim(embeddings[0], embeddings[1]).item()
                sim_suggestion = util.cos_sim(embeddings[0], embeddings[2]).item()
                
                logger.info(f"Vector Similarity: example={sim_example:.3f}, suggestion={sim_suggestion:.3f}")
                
                if sim_example > self.VECTOR_SIMILARITY_THRESHOLD:
                    return True, AdoptionStyle.VERBATIM, f"向量相似度匹配 (Example): {sim_example:.2f}"
                
                if sim_suggestion > self.VECTOR_SIMILARITY_THRESHOLD:
                    return True, AdoptionStyle.PARAPHRASED, f"向量相似度匹配 (Suggestion): {sim_suggestion:.2f}"
                    
            except Exception as e:
                logger.error(f"Vector matching failed: {e}")
        
        # 1. 字符串降级匹配 - 原封不动
        if example_utterance and (example_utterance.lower() in user_lower or self._high_similarity(user_message, example_utterance)):
            return True, AdoptionStyle.VERBATIM, f"用户话术与示例高度相似 (String Match)"
        
        # 2. 字符串降级匹配 - 关键词
        suggestion_keywords = self._extract_keywords(suggestion_text)
        example_keywords = self._extract_keywords(example_utterance)
        
        user_keywords = set(user_lower.split())
        keyword_overlap = len(suggestion_keywords & user_keywords) + len(example_keywords & user_keywords)
        
        if keyword_overlap >= 3:
            return True, AdoptionStyle.PARAPHRASED, f"关键词重叠: {keyword_overlap} 个"
        
        # 3. 字符串降级匹配 - 策略意图
        strategy_indicators = {
            "价值": ["价值", "值得", "回报", "收益", "省钱", "划算"],
            "对比": ["对比", "相比", "比较", "其他", "差异"],
            "案例": ["案例", "客户", "之前", "成功", "例子"],
            "紧迫": ["限时", "优惠", "机会", "错过", "现在"],
            "共情": ["理解", "明白", "确实", "感受", "不用担心"],
        }
        
        for strategy, indicators in strategy_indicators.items():
            suggestion_has = any(ind in suggestion_text.lower() for ind in indicators)
            user_has = any(ind in user_lower for ind in indicators)
            if suggestion_has and user_has:
                return True, AdoptionStyle.STRATEGY_ONLY, f"采纳了 {strategy} 策略 (Keyword Match)"
        
        return False, AdoptionStyle.NOT_ADOPTED, None
    
    def _high_similarity(self, text1: str, text2: str) -> bool:
        """简单的 Jaccard 相似度"""
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        if not words1 or not words2:
            return False
        overlap = len(words1 & words2)
        return overlap / min(len(words1), len(words2)) > self.SIMILARITY_THRESHOLD
    
    def _extract_keywords(self, text: str) -> set:
        """提取关键词"""
        if not text:
            return set()
        stopwords = {"的", "了", "是", "在", "我", "你", "他", "她", "它", "们", "这", "那", "有", "和", "与", "吗", "呢", "吧"}
        words = set(text.lower().split())
        return words - stopwords
    
    async def _save_adoption_record(
        self,
        db: AsyncSession,
        session_id: str,
        user_id: str,
        turn_id: int,
        pending: Dict,
        analysis: AdoptionAnalysis,
        observed_turn_offset: int,
    ) -> None:
        """保存采纳记录到数据库"""
        record = AdoptionRecord(
            id=str(uuid.uuid4()),
            session_id=session_id,
            user_id=user_id,
            turn_id=turn_id,
            suggestion_id=pending["suggestion_id"],
            suggestion_text=pending["suggestion_text"],
            technique_name=pending["technique_name"],
            adopted=analysis.adopted,
            adoption_style=AdoptionStyle(analysis.adoption_style),
            adoption_evidence=analysis.adoption_evidence,
            observed_turn_offset=observed_turn_offset,
            baseline_scores=analysis.baseline_scores,
            observed_scores=analysis.observed_scores,
            skill_delta=analysis.skill_delta,
            is_effective=analysis.is_effective,
            effectiveness_score=analysis.effectiveness_score,
            stage=pending["stage"],
            situation_type=pending.get("situation_type"),
            strategy_suggested=pending["technique_name"],
        )
        db.add(record)
        await db.flush()
        logger.info(f"AdoptionRecord saved: {record.id}")
    
    @staticmethod
    async def get_effective_suggestions_stats(
        db: AsyncSession,
        user_id: Optional[str] = None,
        limit: int = 10,
    ) -> List[Dict]:
        """
        统计最有效的建议类型
        """
        query = select(
            AdoptionRecord.technique_name,
            func.count(AdoptionRecord.id).label("total_count"),
            func.sum(func.cast(AdoptionRecord.is_effective, Integer)).label("effective_count"),
            func.avg(AdoptionRecord.effectiveness_score).label("avg_effectiveness"),
        ).where(
            AdoptionRecord.adopted == True
        ).group_by(
            AdoptionRecord.technique_name
        ).order_by(
            func.avg(AdoptionRecord.effectiveness_score).desc()
        ).limit(limit)
        
        if user_id:
            query = query.where(AdoptionRecord.user_id == user_id)
        
        result = await db.execute(query)
        rows = result.all()
        
        return [
            {
                "technique": row.technique_name,
                "total_adoptions": row.total_count,
                "effective_adoptions": row.effective_count or 0,
                "effectiveness_rate": (row.effective_count or 0) / row.total_count if row.total_count > 0 else 0,
                "avg_effectiveness_score": float(row.avg_effectiveness or 0),
            }
            for row in rows
        ]
