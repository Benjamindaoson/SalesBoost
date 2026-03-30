# Figma 集成快速开始指南

## ✅ 配置已完成

您的 Figma token 已配置到项目中:
- **Token**: `FIGMA_TOKEN_REDACTED`
- **配置文件**: `frontend/.env`

## 🚀 3 步开始使用

### 第 1 步: 获取 Figma File Key

1. 打开您的 Figma 设计文件
2. 复制浏览器地址栏中的 URL
3. 从 URL 中提取 File Key

**示例:**
```
URL: https://www.figma.com/file/abc123xyz/SalesBoost-Design
      └───────┬───────┘
         File Key
```

### 第 2 步: 配置 File Key

编辑 `frontend/.env` 文件:

```env
VITE_FIGMA_FILE_KEY=abc123xyz
```

将您的 File Key 替换 `abc123xyz`

### 第 3 步: 运行导出命令

```bash
cd frontend

# 快速查看文件结构
npm run figma:quick

# 完整导出设计资源
npm run figma:export
```

## 📋 可用的导出命令

### 快速预览 (推荐首次使用)

```bash
npm run figma:quick
```

**作用:**
- 连接到您的 Figma 文件
- 显示文件结构
- 列出可导出的节点
- 不实际下载资源

**适用场景:**
- 第一次使用
- 检查文件连接
- 查看导出选项

### 完整导出

```bash
npm run figma:export
```

**作用:**
- 导出所有图标 (SVG)
- 导出所有图片 (PNG)
- 导出设计 Token (颜色、字体)
- 生成 TypeScript 类型定义
- 生成 Tailwind 配置

**适用场景:**
- 导出完整设计系统
- 同步最新设计
- 构建前导出

## 📁 导出后的资源位置

```
frontend/src/assets/figma/
├── icons/              # 图标 (SVG)
├── images/             # 图片 (PNG)
├── design-tokens.json  # 设计 Token
├── tokens.ts          # TypeScript 类型
├── tailwind.config.json # Tailwind 配置
└── file-info.json     # 文件信息
```

## 💡 使用建议

### 在 Figma 中准备

为了获得最佳导出效果,请:

1. **命名规范**
   - 图标: `icon-name`, `logo`, `user-avatar`
   - 图片: `hero-banner`, `product-shot`, `background`

2. **设置导出**
   - 右键点击图层
   - 选择 "Export"
   - 添加导出设置 (格式、尺寸)

3. **整理结构**
   - 按功能分组
   - 使用清晰的命名
   - 删除不需要导出的隐藏图层

### 集成到工作流

#### 开发时
```bash
# 每次设计更新后
npm run figma:export

# 然后开发
npm run dev
```

#### 部署前
```bash
# 构建前导出
npm run figma:export

# 构建
npm run build
```

#### 自动化 (可选)
在 `package.json` 中添加:
```json
{
  "scripts": {
    "build": "npm run figma:export && tsc -b && vite build"
  }
}
```

## 🎯 常见问题

### Q: 我没有 Figma 文件怎么办?

A: 您可以:
1. 在 Figma 中创建一个新文件
2. 导入现有设计
3. 或者跳过此功能,直接使用现有资源

### Q: 导出的资源在哪里使用?

A: 参考示例组件:
```
frontend/src/components/FigmaAssetsExample.tsx
```

### Q: Token 无效怎么办?

A:
1. 检查 token 格式是否正确 (`figd_...`)
2. 确认 token 未过期
3. 在 Figma 设置中重新生成

### Q: File Key 找不到?

A:
- 确保使用的是完整的 File Key
- 检查文件 URL 格式是否正确
- 确认文件存在且有访问权限

## 📚 更多信息

完整文档请查看:
- [Figma 集成完整指南](./FIGMA_INTEGRATION.md)
- [Figma API 文档](https://www.figma.com/developers/api)

## 🆘 需要帮助?

1. 运行 `npm run figma:quick` 测试连接
2. 检查 `.env` 文件配置
3. 查看 FIGMA_INTEGRATION.md 详细文档
4. 提交 Issue 到项目仓库
