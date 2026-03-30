# SalesBoost 腾讯云 Lighthouse 部署报告

## 部署信息

- **部署时间**: 2026年2月7日
- **服务器**: 腾讯云轻量应用服务器 (Lighthouse)
- **地域**: 北京 (ap-beijing)
- **实例 ID**: lhins-qgg8suu8
- **实例名称**: OpenCloudOS8-Docker26-rkeu
- **公网 IP**: 101.43.199.144
- **操作系统**: OpenCloudOS 8 (Linux)
- **Docker 版本**: Docker 26

## 部署的服务

### 1. 后端服务
- **容器名称**: salesboost-backend
- **镜像**: python:3.11-slim
- **端口**: 8000
- **状态**: ✅ 运行中
- **访问地址**: http://101.43.199.144:8000
- **技术栈**: Python 3.11 + FastAPI + Uvicorn
- **功能**:
  - RESTful API 服务
  - 健康检查端点: `/health`
  - 客户管理 API: `/api/v1/customers`
  - CORS 支持

### 2. 前端服务
- **容器名称**: salesboost-frontend
- **镜像**: nginx:alpine
- **端口**: 80
- **状态**: ✅ 运行中
- **访问地址**: http://101.43.199.144
- **技术栈**: Nginx (Alpine)
- **功能**:
  - 静态文件服务
  - SalesBoost 主页面
  - 学员端页面
  - 管理端页面

### 3. 辅助服务
- **Redis**: salesboost-redis (运行中)
- **Prometheus**: salesboost-prometheus (监控)
- **Grafana**: salesboost-grafana (可视化)

## 可访问的页面

### 主页
- **URL**: http://101.43.199.144
- **描述**: SalesBoost 主页面,包含概览统计和快速入口

### 学员端
- **任务管理**: http://101.43.199.144/student/tasks.html
- **客户预览**: http://101.43.199.144/student/persona.html

### 管理端
- **课程管理**: http://101.43.199.144/admin/

### API 端点
- **健康检查**: http://101.43.199.144:8000/health
- **API 根路径**: http://101.43.199.144:8000/
- **客户列表**: http://101.43.199.144:8000/api/v1/customers

## 服务验证

### 后端 API 测试
```bash
curl http://101.43.199.144:8000/health
# 返回: {"status":"ok","service":"SalesBoost Backend","version":"1.0.0"}

curl http://101.43.199.144:8000/api/v1/customers
# 返回: 客户列表数据
```

### 前端页面测试
```bash
curl http://101.43.199.144/
# 返回: HTML 主页面
```

## 防火墙配置

### 已开放的端口
- **TCP 80**: HTTP 访问(前端)
- **TCP 8000**: API 访问(后端)
- **TCP 22**: SSH 登录
- **TCP 3001**: Grafana 仪表板
- **TCP 9090**: Prometheus 监控
- **来源**: 0.0.0.0/0 (允许所有 IP)

## 容器管理

### 查看容器状态
```bash
docker ps --filter name=salesboost
```

### 查看日志
```bash
# 后端日志
docker logs salesboost-backend -f

# 前端日志
docker logs salesboost-frontend -f
```

### 重启服务
```bash
# 重启单个服务
docker restart salesboost-backend
docker restart salesboost-frontend

# 重启所有服务
docker restart salesboost-backend salesboost-frontend
```

### 停止服务
```bash
# 停止单个服务
docker stop salesboost-backend

# 停止所有服务
docker stop salesboost-backend salesboost-frontend
```

## 系统架构

```
Internet
    ↓
Nginx (Port 80) → salesboost-frontend → Static HTML
    ↓
FastAPI (Port 8000) → salesboost-backend → API Services
    ↓
Redis (Port 6379) → salesboost-redis → Cache/Session
```

## 技术栈

### 前端
- HTML5
- Tailwind CSS (CDN)
- 静态页面部署

### 后端
- Python 3.11
- FastAPI 0.109.0
- Uvicorn 0.27.0
- Pydantic 2.5.3

### 基础设施
- Docker 容器化
- Nginx 反向代理
- Redis 缓存
- OpenCloudOS 8

## 下一步建议

### 1. 完整功能部署
当前部署为基础版本,包含核心功能。要部署完整应用:
- 集成完整的 React 前端构建
- 配置真实的数据库 (PostgreSQL)
- 集成 AI 模型服务
- 配置用户认证系统

### 2. SSL 证书配置
为启用 HTTPS:
```bash
# 使用 Let's Encrypt 免费证书
docker run -d --name certbot --rm \
  -v /etc/letsencrypt:/etc/letsencrypt \
  -p 80:80 \
  certbot/certbot certonly --standalone -d your-domain.com
```

### 3. 域名配置
1. 在域名注册商处添加 A 记录
2. 指向服务器 IP: 101.43.199.144
3. 等待 DNS 生效(通常 10-30 分钟)

### 4. 监控和日志
- 使用 Prometheus + Grafana 监控系统性能
- 配置日志轮转和归档
- 设置告警规则

### 5. 数据备份
```bash
# 定期备份 Redis 数据
docker exec salesboost-redis redis-cli BGSAVE

# 备份到对象存储
# 配置 COS (腾讯云对象存储) 自动备份
```

## 故障排除

### 服务无法访问
1. 检查容器状态: `docker ps`
2. 检查防火墙规则
3. 查看容器日志: `docker logs <container-name>`

### API 响应异常
1. 检查后端日志: `docker logs salesboost-backend`
2. 测试本地访问: `curl localhost:8000/health`
3. 重启后端容器: `docker restart salesboost-backend`

### 前端页面异常
1. 检查前端日志: `docker logs salesboost-frontend`
2. 检查静态文件: `ls -la /root/salesboost/webapp/`
3. 重启前端容器: `docker restart salesboost-frontend`

## 总结

✅ **部署成功!**

SalesBoost 已成功部署到腾讯云轻量应用服务器,所有核心服务运行正常。

- 前端地址: http://101.43.199.144
- 后端地址: http://101.43.199.144:8000
- 服务状态: 所有服务正常运行

系统已准备好供用户访问,可以根据需要逐步完善功能和配置。
