#!/usr/bin/env node

/**
 * 快速 Figma 导出工具
 * 简化版本,用于快速导出特定资源
 */

import https from 'https';
import fs from 'fs';
import path from 'path';

// 从环境变量读取配置
const FIGMA_TOKEN = 'FIGMA_TOKEN_REDACTED';
const FIGMA_FILE_KEY = process.env.VITE_FIGMA_FILE_KEY;

/**
 * 调用 Figma API (使用 HTTPS)
 */
function callFigmaAPI(endpoint) {
  return new Promise((resolve, reject) => {
    const options = {
      hostname: 'api.figma.com',
      port: 443,
      path: `/v1${endpoint}`,
      method: 'GET',
      headers: {
        'X-Figma-Token': FIGMA_TOKEN,
      },
    };

    const req = https.request(options, (res) => {
      let data = '';

      res.on('data', (chunk) => {
        data += chunk;
      });

      res.on('end', () => {
        try {
          const json = JSON.parse(data);
          if (res.statusCode >= 400) {
            reject(new Error(`Figma API Error: ${res.statusCode} - ${JSON.stringify(json)}`));
          } else {
            resolve(json);
          }
        } catch (e) {
          reject(new Error(`Failed to parse response: ${e.message}`));
        }
      });
    });

    req.on('error', (error) => {
      reject(error);
    });

    req.end();
  });
}

/**
 * 下载图片
 */
function downloadImage(url, outputPath) {
  return new Promise((resolve, reject) => {
    const file = fs.createWriteStream(outputPath);
    https.get(url, (response) => {
      response.pipe(file);
      file.on('finish', () => {
        file.close();
        resolve();
      });
    }).on('error', (error) => {
      fs.unlink(outputPath, () => {}); // 删除失败的文件
      reject(error);
    });
  });
}

/**
 * 主函数
 */
async function main() {
  console.log('🚀 Figma 快速导出工具\n');

  if (!FIGMA_FILE_KEY) {
    console.error('❌ 请设置 VITE_FIGMA_FILE_KEY 环境变量');
    console.log('\n获取方法:');
    console.log('1. 打开你的 Figma 文件');
    console.log('2. 从 URL 复制 File Key');
    console.log('   URL: https://www.figma.com/file/FILE_KEY/FILE_NAME');
    console.log('   例如: VITE_FIGMA_FILE_KEY=abc123xyz');
    process.exit(1);
  }

  try {
    // 获取文件信息
    console.log('📥 正在获取 Figma 文件...');
    const file = await callFigmaAPI(`/files/${FIGMA_FILE_KEY}`);

    console.log(`✓ 文件名称: ${file.document.name}`);
    console.log(`✓ 最后修改: ${file.lastModified}\n`);

    // 显示文件结构
    console.log('📁 文件结构:');
    file.document.children.forEach((page, index) => {
      console.log(`  ${index + 1}. ${page.name}`);
      if (page.children && page.children.length > 0) {
        page.children.slice(0, 3).forEach((frame, frameIndex) => {
          console.log(`     ${frameIndex + 1}. ${frame.name} (${frame.type})`);
        });
        if (page.children.length > 3) {
          console.log(`     ... 还有 ${page.children.length - 3} 个`);
        }
      }
    });

    // 导出文件信息到 JSON
    const outputDir = path.join(process.cwd(), 'src', 'assets', 'figma');
    if (!fs.existsSync(outputDir)) {
      fs.mkdirSync(outputDir, { recursive: true });
    }

    const fileInfo = {
      name: file.document.name,
      fileKey: FIGMA_FILE_KEY,
      lastModified: file.lastModified,
      pages: file.document.children.map(page => ({
        name: page.name,
        id: page.id,
        frameCount: page.children ? page.children.length : 0,
      })),
    };

    const outputPath = path.join(outputDir, 'file-info.json');
    fs.writeFileSync(outputPath, JSON.stringify(fileInfo, null, 2));
    console.log(`\n✓ 文件信息已保存到: ${outputPath}`);

    // 检查是否有可导出的节点
    const exportableNodes = [];
    const collectNodes = (node) => {
      if (node.exportSettings && node.exportSettings.length > 0) {
        exportableNodes.push(node);
      }
      if (node.children) {
        node.children.forEach(collectNodes);
      }
    };

    file.document.children.forEach(collectNodes);

    if (exportableNodes.length > 0) {
      console.log(`\n📤 找到 ${exportableNodes.length} 个可导出的节点:`);
      exportableNodes.slice(0, 5).forEach((node, index) => {
        console.log(`  ${index + 1}. ${node.name} (ID: ${node.id})`);
      });

      if (exportableNodes.length > 5) {
        console.log(`  ... 还有 ${exportableNodes.length - 5} 个`);
      }
    } else {
      console.log('\n💡 提示: 在 Figma 中为需要导出的图层设置导出设置');
      console.log('   右键点击图层 → Export → 添加导出设置');
    }

    console.log('\n✅ 完成!');

  } catch (error) {
    console.error('\n❌ 错误:', error.message);
    process.exit(1);
  }
}

// 运行
main();
