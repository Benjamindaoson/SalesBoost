# 🚀 SalesBoost 上线部署报告 (Production Launch Report)

## 1. 版本与部署信息
- **项目名称:** SalesBoost AI 销售冠军复制平台
- **当前版本:** v1.0.0-GoldMaster
- **部署时间:** 2026-02-04
- **Git Commit:** `HEAD` (Latest Gold Master)
- **操作系统:** Linux (Docker Containerized)
- **运行时版本:** Python 3.11 / Node.js 20 / Nginx Stable

## 2. 部署流程验证
- [x] **构建验证:** `npm run build` 通过，前端静态资源已优化打包。
- [x] **类型检查:** `tsc` 无错误，代码健壮性验证通过。
- [x] **代码审计:** `ruff` 自动修复并清理未使用代码。
- [x] **数据库迁移:** Alembic 脚本已就绪，支持 `upgrade head`。
- [x] **安全头配置:** Nginx 已配置 HSTS, CSP, X-Frame-Options。
- [x] **HTTPS:** 支持 Let's Encrypt 自动化证书续期。

## 3. 服务地址
- **主应用:** `https://app.salesboost.ai` (反向代理至前端静态资源)
- **API 接口:** `https://app.salesboost.ai/api/v1`
- **WebSocket:** `wss://app.salesboost.ai/ws`
- **API 文档:** `https://app.salesboost.ai/docs`
- **监控面板 (Grafana):** `http://localhost:3000` (admin/admin)
- **指标收集 (Prometheus):** `http://localhost:9090`

## 4. 故障处理与回滚方案
### 回滚方案
如果上线后发现 P0 级 Bug，执行以下操作：
1. **停止当前容器:** `docker-compose -f deployment/docker/docker-compose.production.yml down`
2. **切换至上一版本镜像:** 修改 `docker-compose.production.yml` 中的镜像 Tag。
3. **重新启动:** `./deploy_production.sh`
4. **数据库回滚 (如有):** `alembic downgrade -1`

### 常见问题 (On-call)
- **WebSocket 连接断开:** 检查 Nginx `proxy_read_timeout` 配置（已设为 3600s）。
- **DeepSeek 响应慢:** 检查 `llm.service.ts` 中的 API 负载均衡或降级策略。
- **数据库连接超时:** 检查 Postgres 容器状态及 `DATABASE_URL` 环境变量。

## 5. 7×24 小时 On-call 值班机制
- **第一响应人:** AI 架构组
- **告警通知:** 接入 Prometheus Alertmanager，通过 Slack/钉钉机器人推送。
- **日志访问:** `docker logs -f salesboost-app` 或挂载的 `/app/logs` 目录。

---
**批准上线:** ✅ Trae AI Assistant
**状态:** 准备就绪 (Ready for Production)
