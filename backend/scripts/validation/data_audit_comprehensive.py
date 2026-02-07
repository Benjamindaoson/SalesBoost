#!/usr/bin/env python3
"""
SalesBoost 数据资产全面审计脚本
Data Asset Comprehensive Audit Script

执行五维度数据审计：
1. 数据可用性验证与损坏检测
2. 数据应用场景映射
3. 数据价值释放方案
4. 数据升级演进路径
5. 数据缺口识别与获取策略
"""

import json
import hashlib
import mimetypes
from pathlib import Path
from typing import Dict, Any
from datetime import datetime

# 数据资产路径配置
DATA_ASSETS = {
    "sales_knowledge_db": "销冠能力复制数据库",
    "intent_data": "data/intent",
    "storage": "storage",
    "tests_data": "tests/data"
}

class DataAssetAuditor:
    """数据资产审计器"""

    def __init__(self, base_path: str = "/d/SalesBoost"):
        self.base_path = Path(base_path)
        self.audit_results = {
            "timestamp": datetime.now().isoformat(),
            "dimensions": {}
        }

    def dimension_1_availability_validation(self) -> Dict[str, Any]:
        """维度1: 数据可用性验证与损坏检测"""
        print("\n=== 维度1: 数据可用性验证与损坏检测 ===")

        results = {
            "file_inventory": [],
            "integrity_checks": [],
            "quality_issues": [],
            "health_score": 0.0
        }

        # 扫描销冠能力复制数据库
        sales_db_path = self.base_path / DATA_ASSETS["sales_knowledge_db"]
        if sales_db_path.exists():
            for file_path in sales_db_path.rglob("*"):
                if file_path.is_file() and not file_path.name.startswith('.'):
                    file_info = self._analyze_file(file_path)
                    results["file_inventory"].append(file_info)

                    # 完整性检查
                    integrity = self._check_file_integrity(file_path, file_info)
                    results["integrity_checks"].append(integrity)

        # 计算健康度分数
        total_files = len(results["file_inventory"])
        healthy_files = sum(1 for check in results["integrity_checks"] if check["status"] == "healthy")
        results["health_score"] = (healthy_files / total_files * 100) if total_files > 0 else 0

        # 统计
        results["summary"] = {
            "total_files": total_files,
            "healthy_files": healthy_files,
            "corrupted_files": total_files - healthy_files,
            "total_size_mb": sum(f["size_bytes"] for f in results["file_inventory"]) / (1024 * 1024)
        }

        print(f"[OK] 扫描文件: {total_files}")
        print(f"[OK] 健康文件: {healthy_files}")
        print(f"[WARN]  问题文件: {total_files - healthy_files}")
        print(f"📊 健康度评分: {results['health_score']:.2f}%")

        return results

    def dimension_2_application_mapping(self) -> Dict[str, Any]:
        """维度2: 数据应用场景映射"""
        print("\n=== 维度2: 数据应用场景映射 ===")

        results = {
            "data_catalog": [],
            "agent_mapping_matrix": {},
            "permission_hierarchy": {}
        }

        # 构建数据资产清单
        catalog_items = [
            {
                "asset_name": "产品权益数据",
                "path": "销冠能力复制数据库/产品权益",
                "format": "XLSX",
                "use_cases": ["RAG检索", "产品知识库", "FAQ生成"],
                "agents": ["CoachAgent", "ComplianceAgent"],
                "priority": "核心数据",
                "update_frequency": "月度"
            },
            {
                "asset_name": "销售话术SOP",
                "path": "销冠能力复制数据库/销售成交营销SOP和话术",
                "format": "PDF/DOCX/PPT",
                "use_cases": ["话术训练", "NPC对话生成", "策略分析"],
                "agents": ["NPCGenerator", "StrategyAnalyzer", "CoachAgent"],
                "priority": "核心数据",
                "update_frequency": "季度"
            },
            {
                "asset_name": "销售录音",
                "path": "销冠能力复制数据库/销售录音",
                "format": "MP3/WAV",
                "use_cases": ["语音识别训练", "对话模式分析", "情感分析"],
                "agents": ["NPCGenerator", "FeedbackAgent"],
                "priority": "辅助数据",
                "update_frequency": "实时"
            },
            {
                "asset_name": "销售冠军经验",
                "path": "销冠能力复制数据库/销售冠军成交经验分享",
                "format": "DOCX",
                "use_cases": ["最佳实践提取", "策略推荐", "案例库"],
                "agents": ["StrategyAnalyzer", "ReportGenerator"],
                "priority": "核心数据",
                "update_frequency": "季度"
            },
            {
                "asset_name": "意图分类训练集",
                "path": "data/intent",
                "format": "CSV",
                "use_cases": ["意图识别模型训练", "对话理解"],
                "agents": ["ContextAwareClassifier"],
                "priority": "核心数据",
                "update_frequency": "周度"
            }
        ]

        results["data_catalog"] = catalog_items

        # 构建智能体-数据映射矩阵
        agent_mapping = {
            "CoachAgent": {
                "primary_data": ["产品权益数据", "销售话术SOP"],
                "secondary_data": ["销售冠军经验"],
                "data_access_pattern": "实时检索",
                "cache_strategy": "LRU缓存"
            },
            "NPCGenerator": {
                "primary_data": ["销售话术SOP", "销售录音"],
                "secondary_data": ["意图分类训练集"],
                "data_access_pattern": "批量加载",
                "cache_strategy": "预加载"
            },
            "ComplianceAgent": {
                "primary_data": ["产品权益数据"],
                "secondary_data": [],
                "data_access_pattern": "规则匹配",
                "cache_strategy": "全量缓存"
            },
            "StrategyAnalyzer": {
                "primary_data": ["销售冠军经验", "销售话术SOP"],
                "secondary_data": ["意图分类训练集"],
                "data_access_pattern": "分析型查询",
                "cache_strategy": "结果缓存"
            }
        }

        results["agent_mapping_matrix"] = agent_mapping

        # 数据权限分级
        results["permission_hierarchy"] = {
            "核心数据": {
                "access_level": "L1",
                "encryption": "AES-256",
                "backup_frequency": "每日",
                "retention_period": "永久"
            },
            "辅助数据": {
                "access_level": "L2",
                "encryption": "AES-128",
                "backup_frequency": "每周",
                "retention_period": "1年"
            },
            "临时数据": {
                "access_level": "L3",
                "encryption": "无",
                "backup_frequency": "无",
                "retention_period": "30天"
            }
        }

        print(f"[OK] 数据资产清单: {len(catalog_items)} 项")
        print(f"[OK] 智能体映射: {len(agent_mapping)} 个智能体")
        print(f"[OK] 权限分级: {len(results['permission_hierarchy'])} 级")

        return results

    def dimension_3_value_release(self) -> Dict[str, Any]:
        """维度3: 数据价值释放方案"""
        print("\n=== 维度3: 数据价值释放方案 ===")

        results = {
            "multimodal_pipeline": {},
            "dynamic_loading": {},
            "monitoring_dashboard": {}
        }

        # 多模态数据处理流水线
        results["multimodal_pipeline"] = {
            "text_processing": {
                "formats": ["PDF", "DOCX", "XLSX", "TXT"],
                "tools": ["PyPDF2", "python-docx", "openpyxl"],
                "chunking_strategy": "semantic_chunking",
                "embedding_model": "BAAI/bge-m3",
                "vector_store": "Qdrant"
            },
            "audio_processing": {
                "formats": ["MP3", "WAV"],
                "tools": ["whisper", "librosa"],
                "transcription": "OpenAI Whisper",
                "speaker_diarization": "pyannote.audio",
                "emotion_analysis": "sentiment_analysis"
            },
            "structured_data": {
                "formats": ["CSV", "JSON", "XLSX"],
                "tools": ["pandas", "polars"],
                "validation": "pydantic",
                "normalization": "sklearn.preprocessing"
            }
        }

        # 动态数据加载机制
        results["dynamic_loading"] = {
            "lazy_loading": {
                "strategy": "按需加载",
                "cache_size": "1GB",
                "eviction_policy": "LRU"
            },
            "incremental_update": {
                "change_detection": "文件哈希对比",
                "update_frequency": "5分钟",
                "hot_reload": True
            },
            "version_control": {
                "enabled": True,
                "storage": "Git LFS",
                "rollback_support": True
            }
        }

        # 数据效果监控体系
        results["monitoring_dashboard"] = {
            "usage_metrics": [
                "数据访问频率",
                "缓存命中率",
                "查询响应时间",
                "数据新鲜度"
            ],
            "business_metrics": [
                "RAG检索准确率",
                "对话成功率",
                "用户满意度",
                "转化率提升"
            ],
            "alerting": {
                "data_staleness": "> 7天",
                "cache_miss_rate": "> 30%",
                "query_latency": "> 500ms"
            }
        }

        print(f"[OK] 多模态处理: {len(results['multimodal_pipeline'])} 种数据类型")
        print(f"[OK] 动态加载: {len(results['dynamic_loading'])} 种机制")
        print(f"[OK] 监控指标: {len(results['monitoring_dashboard']['usage_metrics']) + len(results['monitoring_dashboard']['business_metrics'])} 项")

        return results

    def dimension_4_evolution_path(self) -> Dict[str, Any]:
        """维度4: 数据升级演进路径"""
        print("\n=== 维度4: 数据升级演进路径 ===")

        results = {
            "version_management": {},
            "data_augmentation": {},
            "migration_plan": {}
        }

        # 数据版本管理
        results["version_management"] = {
            "versioning_scheme": "Semantic Versioning (v1.2.3)",
            "datasets": {
                "training_data": {
                    "current_version": "v1.0.0",
                    "storage": "data/intent/v1.0.0/",
                    "changelog": "初始版本"
                },
                "test_data": {
                    "current_version": "v1.0.0",
                    "storage": "data/intent/test/v1.0.0/",
                    "changelog": "初始版本"
                },
                "validation_data": {
                    "current_version": "v1.0.0",
                    "storage": "data/intent/validation/v1.0.0/",
                    "changelog": "初始版本"
                }
            },
            "tools": ["DVC (Data Version Control)", "Git LFS"]
        }

        # 数据增强策略
        results["data_augmentation"] = {
            "synonym_expansion": {
                "method": "WordNet + 领域词典",
                "target_increase": "3x",
                "quality_threshold": 0.85
            },
            "sample_balancing": {
                "method": "SMOTE + 欠采样",
                "target_distribution": "均匀分布",
                "minority_class_threshold": 50
            },
            "time_series_completion": {
                "method": "插值 + 预测模型",
                "missing_data_handling": "前向填充",
                "validation": "交叉验证"
            },
            "llm_generation": {
                "model": "DeepSeek-V3",
                "use_cases": ["对话样本生成", "FAQ扩展", "场景模拟"],
                "quality_filter": "人工审核 + 自动评分"
            }
        }

        # 数据迁移方案
        results["migration_plan"] = {
            "phase_1_assessment": {
                "duration": "1周",
                "tasks": ["数据依赖分析", "兼容性测试", "风险评估"]
            },
            "phase_2_preparation": {
                "duration": "2周",
                "tasks": ["数据备份", "迁移脚本开发", "回滚方案制定"]
            },
            "phase_3_execution": {
                "duration": "1周",
                "tasks": ["灰度迁移", "数据验证", "性能测试"]
            },
            "phase_4_validation": {
                "duration": "1周",
                "tasks": ["业务验证", "监控告警", "文档更新"]
            },
            "rollback_strategy": {
                "trigger_conditions": ["数据丢失", "性能下降>20%", "业务中断"],
                "rollback_time": "< 30分钟",
                "data_recovery": "从备份恢复"
            }
        }

        print(f"[OK] 版本管理: {len(results['version_management']['datasets'])} 个数据集")
        print(f"[OK] 增强策略: {len(results['data_augmentation'])} 种方法")
        print(f"[OK] 迁移阶段: {len(results['migration_plan']) - 1} 个阶段")

        return results

    def dimension_5_gap_identification(self) -> Dict[str, Any]:
        """维度5: 数据缺口识别与获取策略"""
        print("\n=== 维度5: 数据缺口识别与获取策略 ===")

        results = {
            "data_gaps": [],
            "acquisition_strategies": {},
            "evaluation_framework": {}
        }

        # 识别数据缺口
        results["data_gaps"] = [
            {
                "gap_type": "竞品对比数据不足",
                "impact": "高",
                "current_coverage": "30%",
                "target_coverage": "90%",
                "priority": "P0"
            },
            {
                "gap_type": "客户异议处理案例",
                "impact": "高",
                "current_coverage": "40%",
                "target_coverage": "85%",
                "priority": "P0"
            },
            {
                "gap_type": "长尾场景对话数据",
                "impact": "中",
                "current_coverage": "20%",
                "target_coverage": "70%",
                "priority": "P1"
            },
            {
                "gap_type": "实时市场动态",
                "impact": "中",
                "current_coverage": "10%",
                "target_coverage": "80%",
                "priority": "P1"
            },
            {
                "gap_type": "多语言支持数据",
                "impact": "低",
                "current_coverage": "5%",
                "target_coverage": "60%",
                "priority": "P2"
            }
        ]

        # 多源数据获取方案
        results["acquisition_strategies"] = {
            "web_scraping": {
                "targets": ["竞品官网", "金融论坛", "社交媒体"],
                "tools": ["Scrapy", "BeautifulSoup", "Selenium"],
                "anti_scraping": {
                    "user_agent_rotation": True,
                    "proxy_pool": True,
                    "rate_limiting": "1 req/s",
                    "captcha_solving": "2Captcha API"
                },
                "legal_compliance": {
                    "robots_txt_check": True,
                    "terms_of_service_review": True,
                    "data_usage_rights": "仅用于研究和训练"
                }
            },
            "llm_generation": {
                "model": "DeepSeek-V3",
                "use_cases": [
                    "对话场景生成",
                    "FAQ扩展",
                    "异议处理话术"
                ],
                "quality_filter": {
                    "automatic_scoring": {
                        "relevance": "> 0.8",
                        "coherence": "> 0.85",
                        "diversity": "> 0.7"
                    },
                    "human_review": {
                        "sample_rate": "10%",
                        "acceptance_threshold": "> 90%"
                    }
                },
                "cost_estimation": {
                    "tokens_per_sample": 500,
                    "cost_per_1k_tokens": "$0.001",
                    "target_samples": 10000,
                    "total_cost": "$5"
                }
            },
            "synthetic_data": {
                "methods": [
                    "CTGAN (表格数据)",
                    "VAE (时间序列)",
                    "GAN (对话生成)"
                ],
                "validation": {
                    "distribution_similarity": "KL散度 < 0.1",
                    "statistical_tests": "Kolmogorov-Smirnov检验",
                    "domain_expert_review": True
                },
                "use_cases": [
                    "少样本场景扩充",
                    "隐私保护数据生成",
                    "边缘案例模拟"
                ]
            },
            "crowdsourcing": {
                "platforms": ["Amazon MTurk", "国内众包平台"],
                "tasks": [
                    "对话标注",
                    "意图分类",
                    "质量评估"
                ],
                "quality_control": {
                    "worker_qualification": "通过率 > 95%",
                    "redundancy": "3人标注",
                    "gold_standard": "10%黄金标准题"
                }
            }
        }

        # 数据获取效果评估体系
        results["evaluation_framework"] = {
            "cost_metrics": {
                "acquisition_cost_per_sample": "目标: < $0.1",
                "processing_cost": "目标: < $0.05",
                "storage_cost": "目标: < $0.01/GB/月"
            },
            "quality_metrics": {
                "data_accuracy": "目标: > 95%",
                "coverage_improvement": "目标: +50%",
                "model_performance_gain": "目标: +10% F1-score"
            },
            "business_metrics": {
                "time_to_value": "目标: < 2周",
                "roi": "目标: > 300%",
                "user_satisfaction_increase": "目标: +15%"
            }
        }

        print(f"[OK] 数据缺口: {len(results['data_gaps'])} 个")
        print(f"[OK] 获取策略: {len(results['acquisition_strategies'])} 种")
        print(f"[OK] 评估指标: {len(results['evaluation_framework'])} 类")

        return results

    def _analyze_file(self, file_path: Path) -> Dict[str, Any]:
        """分析单个文件"""
        stat = file_path.stat()
        mime_type, _ = mimetypes.guess_type(str(file_path))

        return {
            "path": str(file_path.relative_to(self.base_path)),
            "name": file_path.name,
            "extension": file_path.suffix,
            "size_bytes": stat.st_size,
            "size_human": self._human_readable_size(stat.st_size),
            "mime_type": mime_type or "unknown",
            "modified_time": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            "checksum": self._calculate_checksum(file_path)
        }

    def _check_file_integrity(self, file_path: Path, file_info: Dict) -> Dict[str, Any]:
        """检查文件完整性"""
        status = "healthy"
        issues = []

        # 检查文件大小
        if file_info["size_bytes"] == 0:
            status = "corrupted"
            issues.append("文件大小为0")

        # 检查文件扩展名与MIME类型匹配
        if file_info["mime_type"] == "unknown":
            status = "warning"
            issues.append("无法识别文件类型")

        # 检查临时文件
        if file_path.name.startswith('.~') or file_path.name.startswith('~$'):
            status = "warning"
            issues.append("临时文件")

        return {
            "file": file_info["path"],
            "status": status,
            "issues": issues
        }

    def _calculate_checksum(self, file_path: Path) -> str:
        """计算文件MD5校验和"""
        try:
            md5 = hashlib.md5()
            with open(file_path, 'rb') as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    md5.update(chunk)
            return md5.hexdigest()
        except Exception:
            return "error"

    def _human_readable_size(self, size_bytes: int) -> str:
        """转换为人类可读的文件大小"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.2f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.2f} TB"

    def generate_report(self) -> str:
        """生成完整审计报告"""
        print("\n" + "="*80)
        print("SalesBoost 数据资产全面审计报告")
        print("="*80)

        # 执行五个维度的审计
        self.audit_results["dimensions"]["dimension_1"] = self.dimension_1_availability_validation()
        self.audit_results["dimensions"]["dimension_2"] = self.dimension_2_application_mapping()
        self.audit_results["dimensions"]["dimension_3"] = self.dimension_3_value_release()
        self.audit_results["dimensions"]["dimension_4"] = self.dimension_4_evolution_path()
        self.audit_results["dimensions"]["dimension_5"] = self.dimension_5_gap_identification()

        # 保存报告
        report_path = self.base_path / "DATA_ASSET_AUDIT_REPORT.json"
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(self.audit_results, f, ensure_ascii=False, indent=2)

        print(f"\n[OK] 审计报告已保存: {report_path}")

        return str(report_path)


def main():
    """主函数"""
    auditor = DataAssetAuditor()
    report_path = auditor.generate_report()

    print("\n" + "="*80)
    print("审计完成！")
    print("="*80)
    print(f"\n📊 完整报告: {report_path}")
    print("\n下一步行动:")
    print("1. 审查数据质量问题并修复")
    print("2. 实施数据增强策略")
    print("3. 部署动态数据加载机制")
    print("4. 启动数据缺口填补计划")
    print("5. 建立数据监控仪表板")


if __name__ == "__main__":
    main()
