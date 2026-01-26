"""
Performance Metrics Collection System - 性能指标收集系统
实时监控系统性能，提供指标分析和优化建议
"""

import time
import asyncio
import psutil
import uuid
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class MetricType(Enum):
    """指标类型"""
    RESPONSE_TIME = "response_time"
    THROUGHPUT = "throughput"
    ERROR_RATE = "error_rate"
    COST_EFFICIENCY = "cost_efficiency"
    MODEL_PERFORMANCE = "model_performance"
    SYSTEM_HEALTH = "system_health"


@dataclass
class MetricRecord:
    """指标记录"""
    id: str
    metric_type: MetricType
    session_id: str
    agent_type: str
    value: float
    unit: str
    timestamp: float
    tags: Dict[str, str]
    metadata: Dict[str, Any]


@dataclass
class PerformanceSnapshot:
    """性能快照"""
    timestamp: float
    cpu_percent: float
    memory_percent: float
    disk_usage_percent: float
    network_io: Dict[str, float]
    active_connections: int
    active_sessions: int
    total_requests: int
    total_errors: int


class PerformanceMetricsCollector:
    """性能指标收集器"""
    
    def __init__(self):
        self.metrics_store: List[MetricRecord] = []
        self.performance_snapshots: List[PerformanceSnapshot] = []
        self.alert_thresholds = {
            "response_time": 5000.0,  # 5秒
            "error_rate": 0.05,      # 5%
            "cpu_usage": 80.0,      # 80%
            "memory_usage": 85.0,   # 85%
        }
        self.alert_subscribers = []
        
    async def record_metric(
        self,
        metric_type: MetricType,
        session_id: str,
        agent_type: str,
        value: float,
        unit: str,
        tags: Dict[str, str] = None,
        metadata: Dict[str, Any] = None
    ) -> str:
        """记录指标"""
        record = MetricRecord(
            id=str(uuid.uuid4()),
            metric_type=metric_type,
            session_id=session_id,
            agent_type=agent_type,
            value=value,
            unit=unit,
            timestamp=time.time(),
            tags=tags or {},
            metadata=metadata or {}
        )
        
        self.metrics_store.append(record)
        
        # 限制存储大小
        if len(self.metrics_store) > 10000:
            self.metrics_store = self.metrics_store[-5000:]
        
        # 检查告警条件
        await self._check_alert_conditions(record)
        
        logger.debug(f"Metric recorded: {metric_type.value} = {value} {unit}")
        return record.id
    
    async def record_response_time(self, session_id: str, agent_type: str, response_time_ms: float):
        """记录响应时间"""
        await self.record_metric(
            metric_type=MetricType.RESPONSE_TIME,
            session_id=session_id,
            agent_type=agent_type,
            value=response_time_ms,
            unit="ms"
        )
    
    async def record_throughput(self, session_id: str, agent_type: str, requests_per_second: float):
        """记录吞吐量"""
        await self.record_metric(
            metric_type=MetricType.THROUGHPUT,
            session_id=session_id,
            agent_type=agent_type,
            value=requests_per_second,
            unit="req/s"
        )
    
    async def record_error(self, session_id: str, agent_type: str, error_type: str):
        """记录错误"""
        await self.record_metric(
            metric_type=MetricType.ERROR_RATE,
            session_id=session_id,
            agent_type=agent_type,
            value=1.0,
            unit="count",
            tags={"error_type": error_type}
        )
    
    async def record_cost_efficiency(self, session_id: str, agent_type: str, cost_per_request: float):
        """记录成本效率"""
        await self.record_metric(
            metric_type=MetricType.COST_EFFICIENCY,
            session_id=session_id,
            agent_type=agent_type,
            value=cost_per_request,
            unit="USD"
        )
    
    async def capture_system_snapshot(self, active_connections: int, active_sessions: int, total_requests: int, total_errors: int):
        """捕获系统快照"""
        try:
            snapshot = PerformanceSnapshot(
                timestamp=time.time(),
                cpu_percent=psutil.cpu_percent(interval=1),
                memory_percent=psutil.virtual_memory().percent,
                disk_usage_percent=psutil.disk_usage('/').percent,
                network_io={
                    "bytes_sent": psutil.net_io_counters().bytes_sent,
                    "bytes_recv": psutil.net_io_counters().bytes_recv,
                },
                active_connections=active_connections,
                active_sessions=active_sessions,
                total_requests=total_requests,
                total_errors=total_errors
            )
            
            self.performance_snapshots.append(snapshot)
            
            # 限制快照历史
            if len(self.performance_snapshots) > 1000:
                self.performance_snapshots = self.performance_snapshots[-500:]
            
            logger.info(f"System performance snapshot captured")
            
        except Exception as e:
            logger.error(f"Failed to capture system snapshot: {e}")
    
    async def _check_alert_conditions(self, record: MetricRecord):
        """检查告警条件"""
        alerts = []
        
        # 响应时间告警
        if (record.metric_type == MetricType.RESPONSE_TIME and 
            record.value > self.alert_thresholds["response_time"]):
            alerts.append({
                "type": "response_time_alert",
                "severity": "warning",
                "message": f"High response time: {record.value:.1f}ms",
                "record_id": record.id
            })
        
        # 错误率告警
        if (record.metric_type == MetricType.ERROR_RATE):
            # 计算最近错误率
            recent_errors = [
                m for m in self.metrics_store[-100:]
                if (m.metric_type == MetricType.ERROR_RATE and 
                    m.session_id == record.session_id and
                    m.timestamp > time.time() - 300)  # 5分钟内
            ]
            
            if len(recent_errors) > 5:
                alerts.append({
                    "type": "high_error_rate",
                    "severity": "critical",
                    "message": f"High error rate: {len(recent_errors)} errors in 5 minutes",
                    "record_id": record.id
                })
        
        # CPU使用率告警
        if (record.metric_type == MetricType.SYSTEM_HEALTH and 
            record.value > self.alert_thresholds["cpu_usage"]):
            alerts.append({
                "type": "high_cpu_usage",
                "severity": "warning",
                "message": f"High CPU usage: {record.value:.1f}%",
                "record_id": record.id
            })
        
        # 发送告警
        for alert in alerts:
            await self._send_alert(alert)
    
    async def _send_alert(self, alert: Dict[str, Any]):
        """发送告警"""
        logger.warning(f"Performance alert: {alert}")
        
        # 这里可以集成到告警系统（邮件、Slack等）
        for subscriber in self.alert_subscribers:
            try:
                await subscriber(alert)
            except Exception as e:
                logger.error(f"Failed to send alert to subscriber: {e}")
    
    def subscribe_alerts(self, callback):
        """订阅告警"""
        self.alert_subscribers.append(callback)
    
    def get_metrics_summary(self, time_window_minutes: int = 60) -> Dict[str, Any]:
        """获取指标摘要"""
        current_time = time.time()
        window_start = current_time - (time_window_minutes * 60)
        
        # 过滤时间窗口内的指标
        recent_metrics = [
            m for m in self.metrics_store 
            if m.timestamp >= window_start
        ]
        
        if not recent_metrics:
            return {"error": "No metrics available"}
        
        # 计算统计
        response_times = [m.value for m in recent_metrics if m.metric_type == MetricType.RESPONSE_TIME]
        error_counts = [m.value for m in recent_metrics if m.metric_type == MetricType.ERROR_RATE]
        costs = [m.value for m in recent_metrics if m.metric_type == MetricType.COST_EFFICIENCY]
        
        summary = {
            "time_window_minutes": time_window_minutes,
            "total_metrics": len(recent_metrics),
            "response_time": {
                "avg": sum(response_times) / len(response_times) if response_times else 0,
                "p50": sorted(response_times)[len(response_times)//2] if response_times else 0,
                "p95": sorted(response_times)[int(len(response_times)*0.95)] if response_times else 0,
                "max": max(response_times) if response_times else 0,
                "count": len(response_times)
            } if response_times else {},
            "error_rate": {
                "total_errors": sum(error_counts),
                "error_rate_percent": (sum(error_counts) / len(recent_metrics)) * 100 if recent_metrics else 0,
                "count": len(error_counts)
            } if error_counts else {},
            "cost_efficiency": {
                "avg_cost_per_request": sum(costs) / len(costs) if costs else 0,
                "total_cost": sum(costs),
                "count": len(costs)
            } if costs else {},
            "timestamp": current_time
        }
        
        return summary
    
    def get_performance_trend(self, metric_type: MetricType, hours: int = 24) -> Dict[str, Any]:
        """获取性能趋势"""
        current_time = time.time()
        period_start = current_time - (hours * 3600)
        
        # 获取指定指标的数据
        metric_data = [
            (m.timestamp, m.value) for m in self.metrics_store 
            if (m.metric_type == metric_type and m.timestamp >= period_start)
        ]
        
        if not metric_data:
            return {"error": "No data available for trend analysis"}
        
        # 按时间排序
        metric_data.sort(key=lambda x: x[0])
        
        timestamps = [m[0] for m in metric_data]
        values = [m[1] for m in metric_data]
        
        # 计算趋势
        if len(values) < 2:
            return {"trend": "insufficient_data"}
        
        # 简单线性趋势分析
        first_half = values[:len(values)//2]
        second_half = values[len(values)//2:]
        
        first_avg = sum(first_half) / len(first_half)
        second_avg = sum(second_half) / len(second_half)
        
        if second_avg > first_avg * 1.1:
            trend = "increasing"
        elif second_avg < first_avg * 0.9:
            trend = "decreasing"
        else:
            trend = "stable"
        
        return {
            "trend": trend,
            "period_hours": hours,
            "data_points": len(metric_data),
            "first_period_avg": first_avg,
            "second_period_avg": second_avg,
            "change_percent": ((second_avg - first_avg) / first_avg * 100) if first_avg != 0 else 0,
            "timestamps": timestamps,
            "values": values
        }
    
    def get_system_health_score(self) -> Dict[str, Any]:
        """获取系统健康评分"""
        if not self.performance_snapshots:
            return {"error": "No system snapshots available"}
        
        latest = self.performance_snapshots[-1]
        
        # 计算健康评分
        cpu_score = max(0, 100 - latest.cpu_percent)
        memory_score = max(0, 100 - latest.memory_percent)
        disk_score = max(0, 100 - latest.disk_usage_percent)
        
        # 错误率评分
        error_score = 100
        if latest.total_requests > 0:
            error_rate = (latest.total_errors / latest.total_requests) * 100
            error_score = max(0, 100 - error_rate)
        
        # 综合评分
        overall_score = (cpu_score + memory_score + disk_score + error_score) / 4
        
        health_levels = {
            (90, 100]: "excellent",
            (75, 90): "good",
            (60, 75): "fair",
            (40, 60): "poor",
            (0, 40): "critical"
        }
        
        # 确定健康级别
        health_level = "unknown"
        for range_min, range_max, level in health_levels.items():
            if range_min <= overall_score < range_max:
                health_level = level
                break
        
        return {
            "overall_score": overall_score,
            "health_level": health_level,
            "cpu_score": cpu_score,
            "memory_score": memory_score,
            "disk_score": disk_score,
            "error_score": error_score,
            "latest_snapshot": asdict(latest)
        }


# 全局实例
performance_metrics_collector = PerformanceMetricsCollector()