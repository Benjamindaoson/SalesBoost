#!/usr/bin/env python3
"""
Agent Knowledge Interface - Enhanced Version
智能体知识接口增强版 - 数据唤醒层

核心功能：
1. 为不同Agent提供专门化的数据视图
2. 动态Context Engineering（上下文工程）
3. 冠军案例的Few-Shot注入
4. SOP的Grounding对齐
5. 产品数据的精准查询

Author: Claude Sonnet 4.5
Date: 2026-02-01
"""

import os
import sys
import json
import sqlite3
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
    print("[WARN] SimpleVectorStore not available")
    SimpleVectorStore = None
    SEMANTIC_SEARCH_AVAILABLE = False


class AgentKnowledgeInterface:
    """
    智能体知识接口 - 数据唤醒层

    为不同的Agent提供专门化的数据访问接口
    """

    def __init__(
        self,
        chunks_file: str = "data/processed/semantic_chunks.json",
        db_path: str = "data/databases/salesboost_local.db"
    ):
        self.chunks_file = Path(chunks_file)
        self.db_path = Path(db_path)

        # 向量存储（内存中）
        self.vector_store = None

        # 数据库连接
        self.db_conn = None

        # 初始化状态
        self.initialized = False

    def initialize(self):
        """初始化知识接口"""
        if self.initialized:
            return True

        print("\n=== Initializing Agent Knowledge Interface ===")

        # 1. 加载向量存储到内存
        if SEMANTIC_SEARCH_AVAILABLE and SimpleVectorStore:
            try:
                print("[INFO] Loading vector store into memory...")
                self.vector_store = SimpleVectorStore()
                self.vector_store.load_data(str(self.chunks_file))
                print(f"[OK] Vector store loaded: {self.vector_store.get_stats()['total_documents']} chunks")
            except Exception as e:
                print(f"[WARN] Vector store initialization failed: {e}")
                self.vector_store = None

        # 2. 连接产品数据库
        if self.db_path.exists():
            try:
                self.db_conn = sqlite3.connect(str(self.db_path))
                self.db_conn.row_factory = sqlite3.Row  # 返回字典格式
                print("[OK] Product database connected")
            except Exception as e:
                print(f"[WARN] Database connection failed: {e}")
                self.db_conn = None

        self.initialized = True
        return True

    # ========================================
    # Analyst Agent 专用接口
    # ========================================

    def get_context_for_analyst(
        self,
        user_dialogue: str,
        top_k: int = 1
    ) -> Dict[str, Any]:
        """
        为分析师Agent提取冠军案例作为参考

        用途：In-Context Learning（上下文学习）
        场景：用户表现不佳时，动态注入冠军案例作为参考

        Args:
            user_dialogue: 用户的对话内容
            top_k: 返回最相似的案例数量（默认1个）

        Returns:
            包含冠军案例的上下文字典
        """
        if not self.vector_store:
            return {"champion_case": "", "available": False}

        # 只搜索冠军案例类型
        results = self.vector_store.search(
            query=user_dialogue,
            top_k=top_k,
            min_score=0.4,
            filter_type="champion_case"
        )

        if not results:
            return {"champion_case": "", "available": False}

        # 格式化为Few-Shot Prompt
        champion_case = results[0]

        formatted_context = f"""
【参考案例 - 销售冠军的实战经验】

场景：{champion_case['source']}
冠军做法：
{champion_case['text']}

相似度：{champion_case['score']:.2%}
"""

        return {
            "champion_case": formatted_context,
            "raw_text": champion_case['text'],
            "score": champion_case['score'],
            "source": champion_case['source'],
            "available": True
        }

    def get_multiple_champion_cases(
        self,
        scenario_type: str,
        top_k: int = 3
    ) -> List[Dict[str, Any]]:
        """
        获取多个冠军案例用于学习

        用途：为用户提供多个参考案例
        场景：用户主动请求学习某类场景的处理方法
        """
        if not self.vector_store:
            return []

        results = self.vector_store.search(
            query=scenario_type,
            top_k=top_k,
            min_score=0.3,
            filter_type="champion_case"
        )

        return [
            {
                "text": r['text'],
                "source": r['source'],
                "score": r['score']
            }
            for r in results
        ]

    # ========================================
    # Coach Agent 专用接口
    # ========================================

    def get_sop_for_coach(
        self,
        current_intent: str,
        top_k: int = 2
    ) -> Dict[str, Any]:
        """
        为教练Agent提取SOP标准流程

        用途：Grounding（基准对齐）
        场景：判断用户回答是否符合标准流程

        Args:
            current_intent: 当前对话意图（如"价格异议"）
            top_k: 返回最相关的SOP数量

        Returns:
            包含SOP标准的上下文字典
        """
        if not self.vector_store:
            return {"sop_standard": "", "available": False}

        # 搜索SOP类型的数据
        results = self.vector_store.search(
            query=current_intent,
            top_k=top_k,
            min_score=0.3,
            filter_type="sales_sop"
        )

        if not results:
            return {"sop_standard": "", "available": False}

        # 格式化为标准流程
        sop_texts = []
        for i, result in enumerate(results, 1):
            sop_texts.append(f"""
【标准流程 {i}】
{result['text']}
""")

        formatted_sop = "\n".join(sop_texts)

        return {
            "sop_standard": formatted_sop,
            "raw_results": results,
            "available": True
        }

    def check_compliance(
        self,
        user_response: str,
        expected_intent: str
    ) -> Dict[str, Any]:
        """
        检查用户回答是否符合SOP标准

        用途：合规性检查
        场景：实时判断用户话术是否符合标准
        """
        sop_context = self.get_sop_for_coach(expected_intent, top_k=1)

        if not sop_context['available']:
            return {
                "compliant": None,
                "reason": "No SOP standard available",
                "suggestion": ""
            }

        # 这里可以进一步使用LLM判断合规性
        # 简化版本：检查关键词匹配
        return {
            "compliant": True,  # 需要LLM判断
            "sop_reference": sop_context['sop_standard'],
            "available": True
        }

    # ========================================
    # NPC Agent 专用接口
    # ========================================

    def get_product_info(
        self,
        query: str,
        exact_match: bool = False
    ) -> Dict[str, Any]:
        """
        为NPC Agent查询产品信息

        用途：Fact Checking（事实核查）
        场景：NPC需要准确回答产品相关问题

        注意：使用数据库查询，不使用向量检索（避免幻觉）

        Args:
            query: 查询关键词（如"百夫长"、"年费"）
            exact_match: 是否精确匹配

        Returns:
            产品信息字典
        """
        if not self.db_conn:
            # Fallback: 使用向量检索
            return self._get_product_info_from_vector(query)

        try:
            cursor = self.db_conn.cursor()

            # 查询FAQ表
            if exact_match:
                query_sql = "SELECT * FROM product_FAQ WHERE 问题 = ? OR 答案 = ?"
                cursor.execute(query_sql, (query, query))
            else:
                query_sql = "SELECT * FROM product_FAQ WHERE 问题 LIKE ? OR 答案 LIKE ?"
                cursor.execute(query_sql, (f"%{query}%", f"%{query}%"))

            results = cursor.fetchall()

            if results:
                return {
                    "found": True,
                    "source": "database",
                    "data": [dict(row) for row in results],
                    "count": len(results)
                }

            # 如果数据库没找到，使用向量检索
            return self._get_product_info_from_vector(query)

        except Exception as e:
            print(f"[WARN] Database query failed: {e}")
            return self._get_product_info_from_vector(query)

    def _get_product_info_from_vector(self, query: str) -> Dict[str, Any]:
        """从向量存储中检索产品信息（备用方案）"""
        if not self.vector_store:
            return {"found": False, "source": "none", "data": []}

        results = self.vector_store.search(
            query=query,
            top_k=3,
            min_score=0.4,
            filter_type="product_info"
        )

        return {
            "found": len(results) > 0,
            "source": "vector_store",
            "data": [
                {
                    "text": r['text'],
                    "score": r['score'],
                    "source": r['source']
                }
                for r in results
            ],
            "count": len(results)
        }

    def get_stats(self) -> Dict[str, Any]:
        """
        获取知识库统计信息

        返回：
            包含统计信息的字典
        """
        stats = {
            "total_chunks": 0,
            "memory_mb": 0.0,
            "vector_dimensions": 0,
            "database_connected": False,
            "chunk_types": {}
        }

        # Vector store stats
        if self.vector_store:
            stats["total_chunks"] = len(self.vector_store.documents)

            # Get embedding dimensions from embeddings shape
            if hasattr(self.vector_store, 'embeddings') and self.vector_store.embeddings is not None:
                stats["vector_dimensions"] = self.vector_store.embeddings.shape[1]
                # Calculate memory usage
                import sys
                stats["memory_mb"] = sys.getsizeof(self.vector_store.embeddings) / (1024 * 1024)

            # Count chunk types
            for i, metadata in enumerate(self.vector_store.metadata):
                chunk_type = metadata.get('type', 'unknown')
                stats["chunk_types"][chunk_type] = stats["chunk_types"].get(chunk_type, 0) + 1

        # Database stats
        if self.db_conn:
            stats["database_connected"] = True

        return stats

    def get_objection_scenarios(
        self,
        objection_type: str = None
    ) -> List[Dict[str, Any]]:
        """
        为NPC Agent获取异议场景

        用途：NPC模拟客户异议
        场景：训练模式下，NPC需要提出各种异议
        """
        if not self.vector_store:
            return []

        if objection_type:
            # 搜索特定类型的训练场景
            results = self.vector_store.search(
                query=objection_type,
                top_k=5,
                min_score=0.3,
                filter_type="training_scenario"
            )
        else:
            # 获取所有训练场景
            # 这里需要从chunks_cache中筛选
            results = [
                chunk for chunk in self.vector_store.chunks_cache
                if chunk.get('type') == 'training_scenario'
            ]

        return results

    # ========================================
    # 通用接口
    # ========================================

    def search_knowledge(
        self,
        query: str,
        agent_type: str = None,
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """
        通用知识检索接口

        根据agent_type自动路由到专门化接口
        """
        if not self.vector_store:
            return []

        # 根据Agent类型使用不同的检索策略
        if agent_type == "analyst":
            context = self.get_context_for_analyst(query, top_k=top_k)
            return [context] if context['available'] else []

        elif agent_type == "coach":
            context = self.get_sop_for_coach(query, top_k=top_k)
            return [context] if context['available'] else []

        elif agent_type == "npc":
            product_info = self.get_product_info(query)
            return product_info['data'] if product_info['found'] else []

        else:
            # 默认：全局检索
            return self.vector_store.search(
                query=query,
                top_k=top_k,
                min_score=0.3
            )

    def format_context_for_prompt(
        self,
        context_data: Dict[str, Any],
        agent_type: str
    ) -> str:
        """
        为不同Agent格式化上下文

        Context Engineering的核心：
        - Analyst: Few-Shot格式
        - Coach: SOP标准格式
        - NPC: 事实信息格式
        """
        if agent_type == "analyst":
            if context_data.get('available'):
                return context_data['champion_case']
            return ""

        elif agent_type == "coach":
            if context_data.get('available'):
                return f"""
【标准流程参考】
{context_data['sop_standard']}

请基于以上标准流程，判断用户的回答是否符合要求。
"""
            return ""

        elif agent_type == "npc":
            if context_data.get('found'):
                data_items = context_data['data']
                formatted = []
                for item in data_items[:3]:  # 最多3条
                    if isinstance(item, dict):
                        if 'text' in item:
                            formatted.append(item['text'])
                        else:
                            formatted.append(str(item))
                return "\n\n".join(formatted)
            return ""

        return str(context_data)

    def get_statistics(self) -> Dict[str, Any]:
        """获取知识库统计信息"""
        stats = {
            "vector_store_available": self.vector_store is not None,
            "database_available": self.db_conn is not None,
            "initialized": self.initialized
        }

        if self.vector_store:
            vector_stats = self.vector_store.get_stats()
            stats.update({
                "total_chunks": vector_stats['total_documents'],
                "memory_mb": vector_stats['memory_mb'],
                "embedding_dimension": vector_stats['embedding_dimension']
            })

        return stats


# ========================================
# 全局单例
# ========================================

_global_interface = None

def get_agent_knowledge_interface() -> AgentKnowledgeInterface:
    """获取全局知识接口实例（单例模式）"""
    global _global_interface

    if _global_interface is None:
        _global_interface = AgentKnowledgeInterface()
        _global_interface.initialize()

    return _global_interface


# ========================================
# 测试代码
# ========================================

def main():
    """测试知识接口"""
    print("="*70)
    print("Agent Knowledge Interface - Enhanced Version")
    print("="*70)

    # 初始化接口
    interface = get_agent_knowledge_interface()

    # 测试1: Analyst Agent - 获取冠军案例
    print("\n[Test 1] Analyst Agent - Champion Case Retrieval")
    analyst_context = interface.get_context_for_analyst("客户说太贵了")
    if analyst_context['available']:
        print(analyst_context['champion_case'])
        print(f"Score: {analyst_context['score']:.2%}")

    # 测试2: Coach Agent - 获取SOP标准
    print("\n[Test 2] Coach Agent - SOP Standard Retrieval")
    coach_context = interface.get_sop_for_coach("价格异议处理")
    if coach_context['available']:
        print(coach_context['sop_standard'][:200] + "...")

    # 测试3: NPC Agent - 查询产品信息
    print("\n[Test 3] NPC Agent - Product Info Query")
    product_info = interface.get_product_info("年费")
    print(f"Found: {product_info['found']}")
    print(f"Source: {product_info['source']}")
    print(f"Count: {product_info['count']}")

    # 统计信息
    print("\n[Statistics]")
    stats = interface.get_statistics()
    for key, value in stats.items():
        print(f"  {key}: {value}")

    print("\n[OK] All tests completed!")


if __name__ == "__main__":
    main()
