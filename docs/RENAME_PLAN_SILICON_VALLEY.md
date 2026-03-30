# SalesBoost → 硅谷 AI 项目标准命名方案

**目标**: 将项目重命名为符合 LangChain、OpenAI、Hugging Face 等开源 AI 项目的命名规范。

---

## 一、硅谷 AI 项目命名参考

| 项目 | 根目录 | 后端 | 前端 | 风格 |
|------|--------|------|------|------|
| LangChain | langchain | - | - | 小写连字符 |
| OpenAI Python | openai-python | - | - | 小写连字符 |
| Hugging Face | transformers | - | - | 小写 |
| Vercel AI SDK | ai | - | - | 极简 |
| Anthropic | anthropic-sdk-python | - | - | 小写连字符 |

**通用规则**:
- 根目录: **小写 + 连字符** (kebab-case)
- 无空格、无下划线（目录）
- 简洁、可搜索、易记忆

---

## 二、推荐重命名方案

### 1. 根目录（需手动执行）

| 当前 | 推荐 | 说明 |
|------|------|------|
| `D:\SalesBoost` | `D:\sales-boost` | 小写 kebab-case，符合 GitHub 规范 |

**执行方式**（在资源管理器中）:
```
1. 关闭 Cursor/IDE
2. 重命名 D:\SalesBoost → D:\sales-boost
3. 重新打开项目
```

### 2. 顶层文件夹

| 当前 | 推荐 | 说明 |
|------|------|------|
| backend | server | 硅谷常见（Vercel、Railway） |
| frontend | web | 或 client，更简洁 |
| deployment | deploy | 或 infra |
| docs | docs | 保持 |
| scripts | scripts | 保持 |
| data | data | 保持 |

**可选（保持现状）**: backend / frontend 在 monorepo 中也很常见，可不改。

### 3. 后端文件（Python snake_case）

| 当前 | 推荐 | 说明 |
|------|------|------|
| courses_simple.py | courses.py | 合并后删除 _simple |
| customers_simple.py | customers.py | 合并后删除 _simple |
| tasks_simple.py | tasks.py | 合并后删除 _simple |
| statistics_simple.py | statistics.py | 合并后删除 _simple |
| admin_deps.py | admin_dependencies.py | 更明确 |
| auth_utils.py | auth_utils.py | 保持 |

### 4. 前端文件（TypeScript/React）

| 当前 | 推荐 | 说明 |
|------|------|------|
| use_enhanced_websocket.ts | useEnhancedWebSocket.ts | React Hooks 用 camelCase |
| adminMockData.ts | mocks/admin.data.ts | 统一 mock 目录 |
| mockData.ts | mocks/data.ts | 统一 mock 目录 |
| LoginPage.tsx | LoginPage.tsx | 保持 PascalCase |
| COPILOT_SDK.md | copilot-sdk.md | 小写 kebab-case |

### 5. 配置文件

| 当前 | 推荐 | 说明 |
|------|------|------|
| docker-compose.prod.yml | docker-compose.production.yml | 更明确 |
| .env.example | .env.example | 保持 |

---

## 三、最小改动方案（推荐）

若希望**最小化破坏性**，仅执行：

| 操作 | 说明 |
|------|------|
| 根目录 `SalesBoost` → `sales-boost` | 唯一必须项，符合开源规范 |
| 其余保持 | backend、frontend 等不变 |

---

## 四、完整执行清单（可选）

```
Phase 1 - 根目录（必须）
  [ ] D:\SalesBoost → D:\sales-boost

Phase 2 - 顶层文件夹（可选）
  [ ] backend → server
  [ ] frontend → web
  [ ] deployment → deploy

Phase 3 - 后端 _simple 合并（需代码调整）
  [ ] 合并 courses_simple 到 courses
  [ ] 合并 customers_simple 到 customers
  [ ] 合并 tasks_simple 到 tasks
  [ ] 合并 statistics_simple 到 statistics

Phase 4 - 前端规范（可选）
  [ ] use_enhanced_websocket → useEnhancedWebSocket
  [ ] adminMockData.ts → mocks/admin.data.ts
  [ ] mockData.ts → mocks/data.ts

Phase 5 - 文档
  [ ] COPILOT_SDK.md → copilot-sdk.md
```

---

## 五、重命名后需更新的引用

若执行重命名，需全局替换：

| 旧值 | 新值 |
|------|------|
| SalesBoost | sales-boost |
| backend | server（若改） |
| frontend | web（若改） |
| courses_simple | courses |
| customers_simple | customers |

**涉及文件**: main.py, package.json, docker-compose*.yml, README.md, 各 import 路径。

---

## 六、Git 仓库重命名

```bash
# 若使用 Git，重命名后
cd D:\sales-boost
git status  # 确认路径
# 无需特殊操作，Git 会跟踪重命名
```

---

## 七、总结

**最小可行方案**: 仅将 `D:\SalesBoost` 重命名为 `D:\sales-boost`，其余保持不变。

**完整方案**: 按 Phase 1–5 逐步执行，适合作为长期开源项目发布前的规范化。
