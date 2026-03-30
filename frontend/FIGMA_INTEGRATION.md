# Figma 设计导出集成

这个指南说明如何从 Figma 导出设计资源到 SalesBoost 前端项目。

## 📋 前置要求

1. **Figma 账户和设计文件**
   - 确保你有 Figma 账户
   - 准备好要导出的设计文件

2. **Figma Personal Access Token**
   - 访问: https://www.figma.com/developers/api#access-tokens
   - 点击 "Generate new access token"
   - 复制生成的 token (格式: `figd_...`)

3. **Figma File Key**
   - 打开你的 Figma 文件
   - 从 URL 中复制文件 key
   - URL 格式: `https://www.figma.com/file/FILE_KEY/FILE_NAME`
   - 示例: `https://www.figma.com/file/abc123xyz/SalesBoost-Design` → File Key: `abc123xyz`

## ⚙️ 配置步骤

### 1. 安装依赖

```bash
cd frontend
npm install node-fetch
```

### 2. 配置环境变量

编辑 `frontend/.env` 文件,添加以下配置:

```env
# Figma 配置
VITE_FIGMA_TOKEN=FIGMA_TOKEN_REDACTED
VITE_FIGMA_FILE_KEY=your-file-key-here
```

### 3. 获取你的 Figma File Key

1. 打开你的 Figma 设计文件
2. 复制浏览器地址栏中的 URL
3. 从 URL 中提取文件 key

**示例:**
```
URL: https://www.figma.com/file/abc123xyz/SalesBoost-Design
File Key: abc123xyz
```

将 File Key 添加到 `.env` 文件:

```env
VITE_FIGMA_FILE_KEY=abc123xyz
```

## 🚀 使用方法

### 基本导出

```bash
cd frontend

# 执行导出脚本
node scripts/export-from-figma.js
```

### 导出内容

脚本会自动导出以下内容:

1. **图标 (SVG 格式)**
   - 位置: `src/assets/figma/icons/`
   - 命名规则: 小写+连字符

2. **图片 (PNG 格式)**
   - 位置: `src/assets/figma/images/`
   - 命名规则: 小写+连字符

3. **设计 Token (JSON)**
   - 位置: `src/assets/figma/design-tokens.json`
   - 包含: 颜色、字体、间距等

4. **TypeScript 类型定义**
   - 位置: `src/assets/figma/tokens.ts`
   - 自动生成类型安全的设计 Token

5. **Tailwind CSS 配置**
   - 位置: `src/assets/figma/tailwind.config.json`
   - 自动生成 Tailwind 扩展配置

## 📁 导出后的文件结构

```
frontend/src/assets/figma/
├── icons/                      # 图标文件 (SVG)
│   ├── logo.svg
│   ├── user-icon.svg
│   └── ...
├── images/                     # 图片文件 (PNG)
│   ├── hero-banner.png
│   ├── product-image.png
│   └── ...
├── components/                 # 组件截图 (可选)
├── design-tokens.json          # 设计 Token
├── tokens.ts                   # TypeScript 类型定义
└── tailwind.config.json        # Tailwind 配置
```

## 💡 在代码中使用

### 使用导出的图标

```tsx
import LogoIcon from '@/assets/figma/icons/logo.svg';

function Header() {
  return <img src={LogoIcon} alt="Logo" />;
}
```

### 使用设计 Token

```tsx
import { designTokens } from '@/assets/figma/tokens';

function MyComponent() {
  const primaryColor = designTokens.colors['primary'];

  return (
    <div style={{ color: primaryColor }}>
      Content
    </div>
  );
}
```

### 使用 CSS 变量

```tsx
import { generateCSSVariables } from '@/assets/figma/tokens';

function App() {
  return (
    <>
      <style dangerouslySetInnerHTML={{ __html: generateCSSVariables() }} />
      <div className="text-primary">
        Content
      </div>
    </>
  );
}
```

## 🔄 自动化工作流

### 方案 1: 添加到 package.json 脚本

编辑 `package.json`:

```json
{
  "scripts": {
    "figma:export": "node scripts/export-from-figma.js",
    "figma:watch": "nodemon --watch .env --exec 'node scripts/export-from-figma.js'"
  }
}
```

使用:

```bash
# 导出设计
npm run figma:export

# 监听变化并自动导出 (需要安装 nodemon)
npm run figma:watch
```

### 方案 2: Git 钩子

使用 husky 在提交前自动导出:

```bash
# 安装 husky
npm install --save-dev husky

# 添加钩子
npx husky install
npx husky add .husky/pre-commit "npm run figma:export"
```

### 方案 3: CI/CD 集成

在 GitHub Actions 中自动导出:

```yaml
name: Export from Figma

on:
  workflow_dispatch:

jobs:
  export:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-node@v3
        with:
          node-version: '18'

      - name: Install dependencies
        run: |
          cd frontend
          npm install

      - name: Export from Figma
        env:
          VITE_FIGMA_TOKEN: ${{ secrets.FIGMA_TOKEN }}
          VITE_FIGMA_FILE_KEY: ${{ secrets.FIGMA_FILE_KEY }}
        run: |
          cd frontend
          npm run figma:export

      - name: Commit changes
        run: |
          git config --local user.email "action@github.com"
          git config --local user.name "GitHub Action"
          git add frontend/src/assets/figma/
          git commit -m "chore: export design from figma" || exit 0
          git push
```

## 🎨 Figma 命名规范

为了获得最佳的导出效果,请在 Figma 中遵循以下命名规范:

### 图标命名
- 使用英文命名
- 使用小写字母和连字符
- 示例: `user-icon`, `logo`, `arrow-right`

### 图片命名
- 描述性名称
- 使用小写字母和连字符
- 示例: `hero-banner`, `product-shot-1`, `background-image`

### 设计 Token
- 命名图层以标识其用途
- 示例: `Color-Primary`, `Color-Secondary`, `Font-Heading`

## ⚠️ 注意事项

1. **权限问题**
   - 确保 Figma 文件设置为 "Anyone with the link can view"
   - 或者 token 账号有文件访问权限

2. **大文件导出**
   - 避免一次导出过多资源
   - 可以分批次导出不同页面

3. **API 限制**
   - Figma API 有速率限制
   - 避免频繁调用

4. **版本控制**
   - 导出的 SVG 和 PNG 应该提交到 Git
   - JSON 配置文件也应该提交

## 🔧 故障排除

### 错误: "Figma API 错误: 403"
- 检查 token 是否有效
- 确认 token 有权限访问该文件

### 错误: "未找到文件"
- 检查 File Key 是否正确
- 确认文件存在且可访问

### 导出的文件不完整
- 检查 Figma 命名规范
- 确保图层没有被锁定

### 图标导出失败
- 确保图标是矢量图
- 检查图层结构是否正确

## 📚 相关资源

- [Figma API 文档](https://www.figma.com/developers/api)
- [Figma 插件开发](https://www.figma.com/plugin-docs/)
- [SalesBoost 设计系统](../docs/DESIGN_SYSTEM.md)

## 🆘 获取帮助

如果遇到问题:
1. 检查 Figma token 和 file key 配置
2. 查看 Figma 文档
3. 提交 Issue 到项目仓库
