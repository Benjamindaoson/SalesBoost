#!/usr/bin/env node

/**
 * Figma Design Export Script for SalesBoost
 * 这个脚本用于从 Figma 导出设计资源到前端项目
 */

import fetch from 'node-fetch';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import { dirname } from 'path';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

// 配置
const FIGMA_TOKEN = process.env.VITE_FIGMA_TOKEN;
const FIGMA_FILE_KEY = process.env.VITE_FIGMA_FILE_KEY;

// Figma API 端点
const FIGMA_API_BASE = 'https://api.figma.com/v1';

// 输出目录
const OUTPUT_DIR = path.join(__dirname, '..', 'src', 'assets', 'figma');

/**
 * 创建输出目录
 */
function ensureOutputDir() {
  const dirs = [
    OUTPUT_DIR,
    path.join(OUTPUT_DIR, 'icons'),
    path.join(OUTPUT_DIR, 'images'),
    path.join(OUTPUT_DIR, 'components'),
  ];

  dirs.forEach(dir => {
    if (!fs.existsSync(dir)) {
      fs.mkdirSync(dir, { recursive: true });
      console.log(`✓ 创建目录: ${dir}`);
    }
  });
}

/**
 * 调用 Figma API
 */
async function callFigmaAPI(endpoint) {
  const response = await fetch(`${FIGMA_API_BASE}${endpoint}`, {
    headers: {
      'X-Figma-Token': FIGMA_TOKEN,
    },
  });

  if (!response.ok) {
    const error = await response.text();
    throw new Error(`Figma API 错误: ${response.status} - ${error}`);
  }

  return response.json();
}

/**
 * 获取文件信息
 */
async function getFile() {
  console.log('📥 获取 Figma 文件...');
  const data = await callFigmaAPI(`/files/${FIGMA_FILE_KEY}`);
  return data;
}

/**
 * 导出图片
 */
async function exportImage(nodeId, format = 'png', scale = 2) {
  const response = await fetch(
    `${FIGMA_API_BASE}/images/${FIGMA_FILE_KEY}?ids=${nodeId}&format=${format}&scale=${scale}`,
    {
      headers: {
        'X-Figma-Token': FIGMA_TOKEN,
      },
    }
  );

  if (!response.ok) {
    throw new Error(`导出图片失败: ${response.status}`);
  }

  const data = await response.json();
  const imageUrl = data.images[nodeId];

  // 下载图片
  const imageResponse = await fetch(imageUrl);
  const buffer = await imageResponse.buffer();
  return buffer;
}

/**
 * 导出图标
 */
async function exportIcons(nodes) {
  console.log('\n🎨 导出图标...');

  const iconNodes = nodes.filter(node =>
    node.name.toLowerCase().includes('icon') ||
    node.name.toLowerCase().includes('图标')
  );

  for (const icon of iconNodes) {
    try {
      console.log(`  - 导出: ${icon.name}`);
      const buffer = await exportImage(icon.id, 'svg', 1);
      const fileName = `${icon.name.replace(/\s+/g, '-').toLowerCase()}.svg`;
      const filePath = path.join(OUTPUT_DIR, 'icons', fileName);
      fs.writeFileSync(filePath, buffer);
      console.log(`    ✓ 保存到: ${filePath}`);
    } catch (error) {
      console.error(`    ✗ 导出失败: ${icon.name}`, error.message);
    }
  }
}

/**
 * 导出图片资源
 */
async function exportImages(nodes) {
  console.log('\n📸 导出图片资源...');

  const imageNodes = nodes.filter(node =>
    (node.type === 'RECTANGLE' || node.type === 'ELLIPSE' || node.type === 'FRAME') &&
    !node.name.toLowerCase().includes('icon') &&
    !node.name.toLowerCase().includes('图标')
  );

  for (const image of imageNodes) {
    try {
      console.log(`  - 导出: ${image.name}`);
      const buffer = await exportImage(image.id, 'png', 2);
      const fileName = `${image.name.replace(/\s+/g, '-').toLowerCase()}.png`;
      const filePath = path.join(OUTPUT_DIR, 'images', fileName);
      fs.writeFileSync(filePath, buffer);
      console.log(`    ✓ 保存到: ${filePath}`);
    } catch (error) {
      console.error(`    ✗ 导出失败: ${image.name}`, error.message);
    }
  }
}

/**
 * 导出设计 Token (颜色、字体等)
 */
async function exportDesignTokens(file) {
  console.log('\n🎯 导出设计 Token...');

  const tokens = {
    colors: {},
    typography: {},
    spacing: {},
  };

  // 遍历所有页面和节点
  for (const page of file.document.children) {
    console.log(`  - 处理页面: ${page.name}`);

    for (const node of page.children) {
      // 提取颜色
      if (node.fills && node.fills.length > 0) {
        for (const fill of node.fills) {
          if (fill.type === 'SOLID' && fill.color) {
            const colorName = node.name.toLowerCase().replace(/\s+/g, '-');
            const colorValue = `rgba(${Math.round(fill.color.r * 255)}, ${Math.round(fill.color.g * 255)}, ${Math.round(fill.color.b * 255)}, ${fill.opacity || 1})`;
            tokens.colors[colorName] = colorValue;
          }
        }
      }
    }
  }

  // 保存 Token 文件
  const tokensPath = path.join(OUTPUT_DIR, 'design-tokens.json');
  fs.writeFileSync(tokensPath, JSON.stringify(tokens, null, 2));
  console.log(`  ✓ 保存设计 Token 到: ${tokensPath}`);

  return tokens;
}

/**
 * 生成 TypeScript 类型定义
 */
function generateTypeDefinitions(tokens) {
  console.log('\n📝 生成 TypeScript 类型定义...');

  const tsContent = `/**
 * 从 Figma 导出的设计 Token
 * 自动生成,请勿手动修改
 */

export interface DesignTokens {
  colors: Record<string, string>;
  typography: Record<string, any>;
  spacing: Record<string, any>;
}

export const designTokens: DesignTokens = ${JSON.stringify(tokens, null, 2)};

// CSS 变量生成
export const generateCSSVariables = () => {
  const cssVars = ':root {\n';

  for (const [key, value] of Object.entries(tokens.colors)) {
    cssVars += `  --color-${key}: ${value};\n`;
  }

  cssVars += '}';
  return cssVars;
};
`;

  const tsPath = path.join(OUTPUT_DIR, 'tokens.ts');
  fs.writeFileSync(tsPath, tsContent);
  console.log(`  ✓ 保存类型定义到: ${tsPath}`);
}

/**
 * 生成 Tailwind CSS 配置
 */
function generateTailwindConfig(tokens) {
  console.log('\n🎨 生成 Tailwind CSS 配置...');

  const tailwindColors = {};
  for (const [key, value] of Object.entries(tokens.colors)) {
    const colorKey = key.replace(/-/g, '');
    tailwindColors[colorKey] = value;
  }

  const tailwindConfig = {
    theme: {
      extend: {
        colors: tailwindColors,
      },
    },
  };

  const configPath = path.join(OUTPUT_DIR, 'tailwind.config.json');
  fs.writeFileSync(configPath, JSON.stringify(tailwindConfig, null, 2));
  console.log(`  ✓ 保存 Tailwind 配置到: ${configPath}`);
}

/**
 * 收集所有节点
 */
function collectNodes(node, nodes = []) {
  nodes.push(node);

  if (node.children) {
    for (const child of node.children) {
      collectNodes(child, nodes);
    }
  }

  return nodes;
}

/**
 * 主函数
 */
async function main() {
  try {
    console.log('🚀 开始从 Figma 导出设计资源...\n');

    // 检查配置
    if (!FIGMA_TOKEN || !FIGMA_FILE_KEY) {
      throw new Error('请配置 VITE_FIGMA_TOKEN 和 VITE_FIGMA_FILE_KEY 环境变量');
    }

    // 创建输出目录
    ensureOutputDir();

    // 获取文件
    const file = await getFile();
    console.log(`✓ 文件名称: ${file.document.name}`);
    console.log(`✓ 最后修改: ${file.lastModified}`);

    // 收集所有节点
    const allNodes = collectNodes(file.document);
    console.log(`✓ 找到 ${allNodes.length} 个节点\n`);

    // 导出设计 Token
    const tokens = await exportDesignTokens(file);

    // 生成类型定义
    generateTypeDefinitions(tokens);

    // 生成 Tailwind 配置
    generateTailwindConfig(tokens);

    // 导出图标
    await exportIcons(allNodes);

    // 导出图片
    await exportImages(allNodes);

    console.log('\n✅ 导出完成!');
    console.log(`\n导出文件位置: ${OUTPUT_DIR}\n`);

  } catch (error) {
    console.error('\n❌ 导出失败:', error.message);
    process.exit(1);
  }
}

// 运行脚本
main();
