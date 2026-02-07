#!/usr/bin/env python3
"""
Week 4 Day 25-26: Prometheus Monitoring & Grafana Dashboard Deployment
Prometheus监控和Grafana仪表板部署

监控目标:
- 实时性能监控
- 成本追踪
- 错误告警
- 容量规划

关键指标:
- 查询延迟 (P50/P95/P99)
- QPS和吞吐量
- 缓存命中率
- 错误率
- 成本/查询
- 资源使用率
"""

import yaml
from typing import Dict
from dataclasses import dataclass


# ============================================================================
# Prometheus Configuration
# ============================================================================

@dataclass
class PrometheusConfig:
    """Prometheus配置"""
    scrape_interval: str = "15s"
    evaluation_interval: str = "15s"
    scrape_timeout: str = "10s"

    def generate_config(self) -> Dict:
        """生成Prometheus配置"""
        return {
            "global": {
                "scrape_interval": self.scrape_interval,
                "evaluation_interval": self.evaluation_interval,
                "scrape_timeout": self.scrape_timeout
            },
            "scrape_configs": [
                {
                    "job_name": "salesboost_rag",
                    "static_configs": [
                        {
                            "targets": ["localhost:8000"],
                            "labels": {
                                "service": "rag_system",
                                "environment": "production"
                            }
                        }
                    ],
                    "metrics_path": "/metrics"
                }
            ],
            "rule_files": [
                "alert_rules.yml"
            ]
        }


# ============================================================================
# Alert Rules
# ============================================================================

class AlertRules:
    """告警规则"""

    @staticmethod
    def generate_rules() -> Dict:
        """生成告警规则"""
        return {
            "groups": [
                {
                    "name": "rag_system_alerts",
                    "interval": "30s",
                    "rules": [
                        # 高延迟告警
                        {
                            "alert": "HighP99Latency",
                            "expr": 'histogram_quantile(0.99, rate(production_rag_latency_seconds_bucket{stage="total"}[5m])) > 0.5',
                            "for": "5m",
                            "labels": {
                                "severity": "warning",
                                "component": "rag_system"
                            },
                            "annotations": {
                                "summary": "High P99 latency detected",
                                "description": "P99 latency is {{ $value }}s (threshold: 0.5s)"
                            }
                        },
                        # 高错误率告警
                        {
                            "alert": "HighErrorRate",
                            "expr": 'rate(production_rag_errors_total[5m]) > 0.01',
                            "for": "2m",
                            "labels": {
                                "severity": "critical",
                                "component": "rag_system"
                            },
                            "annotations": {
                                "summary": "High error rate detected",
                                "description": "Error rate is {{ $value }}/s (threshold: 0.01/s)"
                            }
                        },
                        # 低缓存命中率告警
                        {
                            "alert": "LowCacheHitRate",
                            "expr": 'production_rag_cache_hit_rate < 0.5',
                            "for": "10m",
                            "labels": {
                                "severity": "warning",
                                "component": "cache"
                            },
                            "annotations": {
                                "summary": "Low cache hit rate",
                                "description": "Cache hit rate is {{ $value }} (threshold: 0.5)"
                            }
                        },
                        # 高成本告警
                        {
                            "alert": "HighCost",
                            "expr": 'rate(production_rag_cost_cny[1h]) > 10',
                            "for": "5m",
                            "labels": {
                                "severity": "warning",
                                "component": "cost"
                            },
                            "annotations": {
                                "summary": "High cost detected",
                                "description": "Cost rate is ¥{{ $value }}/hour (threshold: ¥10/hour)"
                            }
                        },
                        # 服务不可用告警
                        {
                            "alert": "ServiceDown",
                            "expr": 'up{job="salesboost_rag"} == 0',
                            "for": "1m",
                            "labels": {
                                "severity": "critical",
                                "component": "service"
                            },
                            "annotations": {
                                "summary": "Service is down",
                                "description": "RAG service is not responding"
                            }
                        },
                        # 高并发告警
                        {
                            "alert": "HighConcurrency",
                            "expr": 'production_rag_concurrent_queries > 800',
                            "for": "5m",
                            "labels": {
                                "severity": "warning",
                                "component": "capacity"
                            },
                            "annotations": {
                                "summary": "High concurrency detected",
                                "description": "Concurrent queries: {{ $value }} (threshold: 800)"
                            }
                        }
                    ]
                }
            ]
        }


# ============================================================================
# Grafana Dashboard
# ============================================================================

class GrafanaDashboard:
    """Grafana仪表板"""

    @staticmethod
    def generate_dashboard() -> Dict:
        """生成Grafana仪表板配置"""
        return {
            "dashboard": {
                "title": "SalesBoost RAG System - Production Monitoring",
                "tags": ["rag", "production", "salesboost"],
                "timezone": "browser",
                "schemaVersion": 16,
                "version": 1,
                "refresh": "30s",
                "panels": [
                    # Row 1: Overview
                    {
                        "id": 1,
                        "title": "Query Rate (QPS)",
                        "type": "graph",
                        "gridPos": {"x": 0, "y": 0, "w": 8, "h": 8},
                        "targets": [
                            {
                                "expr": 'rate(production_rag_query_total[1m])',
                                "legendFormat": "QPS"
                            }
                        ],
                        "yaxes": [
                            {"format": "short", "label": "Queries/sec"},
                            {"format": "short"}
                        ]
                    },
                    {
                        "id": 2,
                        "title": "P99 Latency",
                        "type": "graph",
                        "gridPos": {"x": 8, "y": 0, "w": 8, "h": 8},
                        "targets": [
                            {
                                "expr": 'histogram_quantile(0.99, rate(production_rag_latency_seconds_bucket{stage="total"}[5m]))',
                                "legendFormat": "P99"
                            },
                            {
                                "expr": 'histogram_quantile(0.95, rate(production_rag_latency_seconds_bucket{stage="total"}[5m]))',
                                "legendFormat": "P95"
                            },
                            {
                                "expr": 'histogram_quantile(0.50, rate(production_rag_latency_seconds_bucket{stage="total"}[5m]))',
                                "legendFormat": "P50"
                            }
                        ],
                        "yaxes": [
                            {"format": "s", "label": "Latency"},
                            {"format": "short"}
                        ],
                        "alert": {
                            "conditions": [
                                {
                                    "evaluator": {"params": [0.5], "type": "gt"},
                                    "query": {"params": ["A", "5m", "now"]},
                                    "type": "query"
                                }
                            ],
                            "name": "P99 Latency Alert"
                        }
                    },
                    {
                        "id": 3,
                        "title": "Error Rate",
                        "type": "graph",
                        "gridPos": {"x": 16, "y": 0, "w": 8, "h": 8},
                        "targets": [
                            {
                                "expr": 'rate(production_rag_errors_total[5m])',
                                "legendFormat": "{{error_type}}"
                            }
                        ],
                        "yaxes": [
                            {"format": "short", "label": "Errors/sec"},
                            {"format": "short"}
                        ]
                    },

                    # Row 2: Cache & Performance
                    {
                        "id": 4,
                        "title": "Cache Hit Rate",
                        "type": "graph",
                        "gridPos": {"x": 0, "y": 8, "w": 8, "h": 8},
                        "targets": [
                            {
                                "expr": 'production_rag_cache_hit_rate',
                                "legendFormat": "{{cache_type}}"
                            }
                        ],
                        "yaxes": [
                            {"format": "percentunit", "label": "Hit Rate", "max": 1, "min": 0},
                            {"format": "short"}
                        ]
                    },
                    {
                        "id": 5,
                        "title": "Latency by Stage",
                        "type": "graph",
                        "gridPos": {"x": 8, "y": 8, "w": 8, "h": 8},
                        "targets": [
                            {
                                "expr": 'rate(production_rag_latency_seconds_sum{stage="retrieval"}[5m]) / rate(production_rag_latency_seconds_count{stage="retrieval"}[5m])',
                                "legendFormat": "Retrieval"
                            },
                            {
                                "expr": 'rate(production_rag_latency_seconds_sum{stage="reranking"}[5m]) / rate(production_rag_latency_seconds_count{stage="reranking"}[5m])',
                                "legendFormat": "Reranking"
                            },
                            {
                                "expr": 'rate(production_rag_latency_seconds_sum{stage="generation"}[5m]) / rate(production_rag_latency_seconds_count{stage="generation"}[5m])',
                                "legendFormat": "Generation"
                            }
                        ],
                        "yaxes": [
                            {"format": "s", "label": "Latency"},
                            {"format": "short"}
                        ]
                    },
                    {
                        "id": 6,
                        "title": "Concurrent Queries",
                        "type": "graph",
                        "gridPos": {"x": 16, "y": 8, "w": 8, "h": 8},
                        "targets": [
                            {
                                "expr": 'production_rag_concurrent_queries',
                                "legendFormat": "Concurrent"
                            }
                        ],
                        "yaxes": [
                            {"format": "short", "label": "Queries"},
                            {"format": "short"}
                        ]
                    },

                    # Row 3: Cost & Business Metrics
                    {
                        "id": 7,
                        "title": "Cost Rate (¥/hour)",
                        "type": "graph",
                        "gridPos": {"x": 0, "y": 16, "w": 8, "h": 8},
                        "targets": [
                            {
                                "expr": 'rate(production_rag_cost_cny[1h]) * 3600',
                                "legendFormat": "{{service}}"
                            }
                        ],
                        "yaxes": [
                            {"format": "currencyCNY", "label": "Cost/hour"},
                            {"format": "short"}
                        ]
                    },
                    {
                        "id": 8,
                        "title": "Query Distribution by Complexity",
                        "type": "piechart",
                        "gridPos": {"x": 8, "y": 16, "w": 8, "h": 8},
                        "targets": [
                            {
                                "expr": 'sum by (complexity) (rate(production_rag_query_total[5m]))',
                                "legendFormat": "{{complexity}}"
                            }
                        ]
                    },
                    {
                        "id": 9,
                        "title": "Success Rate",
                        "type": "stat",
                        "gridPos": {"x": 16, "y": 16, "w": 8, "h": 8},
                        "targets": [
                            {
                                "expr": 'sum(rate(production_rag_query_total{status="success"}[5m])) / sum(rate(production_rag_query_total[5m]))',
                                "legendFormat": "Success Rate"
                            }
                        ],
                        "options": {
                            "reduceOptions": {
                                "values": False,
                                "calcs": ["lastNotNull"]
                            },
                            "orientation": "auto",
                            "textMode": "value_and_name",
                            "colorMode": "value",
                            "graphMode": "area"
                        },
                        "fieldConfig": {
                            "defaults": {
                                "unit": "percentunit",
                                "thresholds": {
                                    "mode": "absolute",
                                    "steps": [
                                        {"value": None, "color": "red"},
                                        {"value": 0.95, "color": "yellow"},
                                        {"value": 0.99, "color": "green"}
                                    ]
                                }
                            }
                        }
                    }
                ]
            }
        }


# ============================================================================
# Docker Compose for Monitoring Stack
# ============================================================================

class MonitoringStack:
    """监控栈"""

    @staticmethod
    def generate_docker_compose() -> Dict:
        """生成Docker Compose配置"""
        return {
            "version": "3.8",
            "services": {
                "prometheus": {
                    "image": "prom/prometheus:latest",
                    "container_name": "prometheus",
                    "ports": ["9090:9090"],
                    "volumes": [
                        "./prometheus.yml:/etc/prometheus/prometheus.yml",
                        "./alert_rules.yml:/etc/prometheus/alert_rules.yml",
                        "prometheus_data:/prometheus"
                    ],
                    "command": [
                        "--config.file=/etc/prometheus/prometheus.yml",
                        "--storage.tsdb.path=/prometheus",
                        "--web.console.libraries=/usr/share/prometheus/console_libraries",
                        "--web.console.templates=/usr/share/prometheus/consoles"
                    ],
                    "restart": "unless-stopped"
                },
                "grafana": {
                    "image": "grafana/grafana:latest",
                    "container_name": "grafana",
                    "ports": ["3000:3000"],
                    "volumes": [
                        "grafana_data:/var/lib/grafana",
                        "./grafana/provisioning:/etc/grafana/provisioning"
                    ],
                    "environment": {
                        "GF_SECURITY_ADMIN_PASSWORD": "admin",
                        "GF_USERS_ALLOW_SIGN_UP": "false"
                    },
                    "restart": "unless-stopped",
                    "depends_on": ["prometheus"]
                },
                "alertmanager": {
                    "image": "prom/alertmanager:latest",
                    "container_name": "alertmanager",
                    "ports": ["9093:9093"],
                    "volumes": [
                        "./alertmanager.yml:/etc/alertmanager/alertmanager.yml"
                    ],
                    "command": [
                        "--config.file=/etc/alertmanager/alertmanager.yml"
                    ],
                    "restart": "unless-stopped"
                }
            },
            "volumes": {
                "prometheus_data": {},
                "grafana_data": {}
            }
        }


# ============================================================================
# Deployment Script
# ============================================================================

def deploy_monitoring_stack():
    """部署监控栈"""
    print("\n" + "="*70)
    print("Deploying Prometheus & Grafana Monitoring Stack")
    print("="*70)

    # 1. 生成Prometheus配置
    print("\n[STEP 1] Generating Prometheus configuration...")
    prom_config = PrometheusConfig()
    prometheus_yml = prom_config.generate_config()

    with open("prometheus.yml", "w") as f:
        yaml.dump(prometheus_yml, f, default_flow_style=False)
    print("  ✅ prometheus.yml created")

    # 2. 生成告警规则
    print("\n[STEP 2] Generating alert rules...")
    alert_rules = AlertRules.generate_rules()

    with open("alert_rules.yml", "w") as f:
        yaml.dump(alert_rules, f, default_flow_style=False)
    print("  ✅ alert_rules.yml created")

    # 3. 生成Grafana仪表板
    print("\n[STEP 3] Generating Grafana dashboard...")
    dashboard = GrafanaDashboard.generate_dashboard()

    import json
    with open("grafana_dashboard.json", "w") as f:
        json.dump(dashboard, f, indent=2)
    print("  ✅ grafana_dashboard.json created")

    # 4. 生成Docker Compose
    print("\n[STEP 4] Generating Docker Compose configuration...")
    docker_compose = MonitoringStack.generate_docker_compose()

    with open("docker-compose.monitoring.yml", "w") as f:
        yaml.dump(docker_compose, f, default_flow_style=False)
    print("  ✅ docker-compose.monitoring.yml created")

    # 5. 部署说明
    print("\n" + "="*70)
    print("Deployment Instructions")
    print("="*70)
    print("\n1. Start monitoring stack:")
    print("   docker-compose -f docker-compose.monitoring.yml up -d")
    print("\n2. Access services:")
    print("   - Prometheus: http://localhost:9090")
    print("   - Grafana: http://localhost:3000 (admin/admin)")
    print("   - Alertmanager: http://localhost:9093")
    print("\n3. Import Grafana dashboard:")
    print("   - Login to Grafana")
    print("   - Go to Dashboards → Import")
    print("   - Upload grafana_dashboard.json")
    print("\n4. Configure data source:")
    print("   - Go to Configuration → Data Sources")
    print("   - Add Prometheus: http://prometheus:9090")
    print("\n5. Verify metrics:")
    print("   - Check http://localhost:8000/metrics")
    print("   - Verify Prometheus targets: http://localhost:9090/targets")

    print("\n" + "="*70)
    print("Monitoring Stack Deployment Complete")
    print("="*70)

    print("\n[SUCCESS] Monitoring stack configured!")
    print("[INFO] Key features:")
    print("  - ✅ Prometheus metrics collection")
    print("  - ✅ Grafana dashboards (9 panels)")
    print("  - ✅ Alert rules (6 alerts)")
    print("  - ✅ Alertmanager integration")
    print("  - ✅ Docker Compose deployment")
    print("\n[INFO] Monitored metrics:")
    print("  - Query rate (QPS)")
    print("  - Latency (P50/P95/P99)")
    print("  - Error rate")
    print("  - Cache hit rate")
    print("  - Cost tracking")
    print("  - Concurrent queries")
    print("  - Success rate")


if __name__ == "__main__":
    deploy_monitoring_stack()
