# GitHub上传指南 - SalesBoost项目

## ✅ 已完成的准备工作

### 1. 项目清理完成
- ✅ 删除了大型模型文件 (intent_classifier.bin - 763MB)
- ✅ 删除了训练数据文件
- ✅ 删除了处理后的图片文件 (17个PNG, ~20MB)
- ✅ 删除了storage/目录 (chromadb, qdrant, traces)
- ✅ 删除了frontend assets backup (9.3MB)
- ✅ 更新了.gitignore以排除所有大文件

### 2. 文件大小检查
所有剩余文件都 < 10MB，符合GitHub要求

### 3. Git提交完成
- 最新提交: `8f70d47` - "chore: Remove all large data and storage files"
- 分支: `main`
- 所有更改已提交

---

## 📋 上传到GitHub的步骤

### 方法1：使用GitHub Desktop（最简单）

1. **下载并安装GitHub Desktop**
   - 访问: https://desktop.github.com/
   - 下载并安装

2. **登录GitHub账号**
   - 打开GitHub Desktop
   - File → Options → Accounts
   - 登录你的GitHub账号 (Benjamindaoson)

3. **添加本地仓库**
   - File → Add Local Repository
   - 选择路径: `d:\SalesBoost`
   - 点击"Add Repository"

4. **推送到GitHub**
   - 确保当前分支是 `main`
   - 点击顶部的 "Push origin" 按钮
   - GitHub Desktop会自动处理认证和上传

### 方法2：使用命令行（需要认证）

```bash
cd d:\SalesBoost

# 1. 配置Git凭据（如果还没有）
git config --global user.name "Benjamindaoson"
git config --global user.email "your_email@example.com"

# 2. 使用Personal Access Token推送
# 首先在GitHub创建token:
# https://github.com/settings/tokens
# 选择: repo (full control)

# 3. 推送时使用token
git push https://YOUR_TOKEN@github.com/Benjamindaoson/SalesBoost main

# 或者设置credential helper
git config --global credential.helper wincred
git push origin main
# 然后输入用户名和token
```

### 方法3：使用SSH（推荐长期使用）

```bash
# 1. 生成SSH密钥（如果还没有）
ssh-keygen -t ed25519 -C "your_email@example.com"

# 2. 复制公钥
cat ~/.ssh/id_ed25519.pub

# 3. 添加到GitHub
# 访问: https://github.com/settings/keys
# 点击 "New SSH key"
# 粘贴公钥内容

# 4. 更改远程URL为SSH
git remote set-url origin git@github.com:Benjamindaoson/SalesBoost.git

# 5. 推送
git push origin main
```

---

## 📊 上传内容清单

### ✅ 将要上传的内容

#### 源代码 (~50MB)
- `app/` - 核心多智能体系统
- `api/` - API层
- `core/` - 核心工具
- `schemas/` - 数据模式
- `frontend/src/` - React前端源码

#### 配置文件 (~2MB)
- `config/` - 所有配置
- `.env.example` - 环境变量示例
- `requirements.txt` - Python依赖
- `package.json` - Node依赖

#### 文档 (~15MB)
- `docs/` - 完整文档
- `README.md` - 精彩的项目说明
- `CONTRIBUTING.md` - 贡献指南
- `CODE_OF_CONDUCT.md` - 行为准则
- `SECURITY.md` - 安全政策
- `CHANGELOG.md` - 变更日志

#### 脚本和工具 (~5MB)
- `scripts/` - 工具脚本
- `main.py` - 入口文件
- `deployment/` - 部署配置

#### 测试 (~3MB)
- `tests/` - 测试代码

#### GitHub集成
- `.github/` - Issue和PR模板
- `.gitignore` - 忽略规则
- `.gitattributes` - Git属性

### ❌ 已排除的内容

- ❌ `models/*.bin` - 大型模型文件 (763MB)
- ❌ `data/raw_sop/` - 原始数据
- ❌ `data/training_data/` - 训练数据
- ❌ `data/databases/` - 数据库文件
- ❌ `storage/` - 运行时存储
- ❌ `.cache/` - 缓存文件
- ❌ `*.png` - 处理后的图片

---

## 🎯 推送后验证

推送成功后，访问 https://github.com/Benjamindaoson/SalesBoost 应该看到:

### 主页展示
- ✅ 精彩的README，包含所有创新点
- ✅ 徽章显示: Python, React, FastAPI, LangGraph
- ✅ 清晰的项目描述和特性列表

### 文件结构
- ✅ 22个根目录，组织清晰
- ✅ 完整的开源项目文件
- ✅ GitHub模板 (.github/)

### 文档完整性
- ✅ 贡献指南
- ✅ 行为准则
- ✅ 安全政策
- ✅ 变更日志

---

## 🚨 常见问题

### Q: 推送失败 "Repository not found"
**A**: 需要认证。使用GitHub Desktop或配置Personal Access Token。

### Q: 推送超时
**A**: 仓库已经清理，现在大小合适。如果还是超时，使用GitHub Desktop。

### Q: 需要输入密码
**A**: GitHub不再支持密码认证，需要使用Personal Access Token或SSH。

### Q: 如何创建Personal Access Token?
**A**:
1. 访问 https://github.com/settings/tokens
2. 点击 "Generate new token (classic)"
3. 选择 `repo` 权限
4. 生成并复制token
5. 使用token代替密码

---

## 📝 推送命令总结

```bash
# 检查状态
git status

# 查看提交历史
git log --oneline -5

# 推送到GitHub（需要认证）
git push origin main

# 或使用token
git push https://YOUR_TOKEN@github.com/Benjamindaoson/SalesBoost main
```

---

## ✅ 完成清单

- [x] 删除大文件
- [x] 更新.gitignore
- [x] 提交所有更改
- [x] 准备推送命令
- [ ] 执行推送（需要你的GitHub认证）
- [ ] 验证GitHub页面

---

**当前状态**: 项目已准备好推送，只需要GitHub认证即可完成上传。

**推荐方法**: 使用GitHub Desktop，最简单快捷！

**仓库地址**: https://github.com/Benjamindaoson/SalesBoost
