# 小红书爬虫使用指南

## 概述

小红书爬虫用于采集销售相关笔记，输出 JSONL 格式，与 TikTok 数据结构对齐，便于后续分析。

## 依赖安装

```bash
pip install -r scripts/crawlers/requirements.txt
playwright install
```

可选：下载 stealth.min.js 用于反检测（签名失败时可尝试）

```bash
curl -o scripts/crawlers/xhs/stealth.min.js \
  https://cdn.jsdelivr.net/gh/requireCool/stealth.min.js/stealth.min.js
```

## 获取 Cookie

1. 使用 Chrome 打开 https://www.xiaohongshu.com
2. 登录账号
3. F12 打开开发者工具 → Application → Cookies → 选择 xiaohongshu.com
4. 复制 `a1`、`web_session`、`webId` 三个字段，格式化为：
   ```
   a1=xxx; web_session=xxx; webId=xxx
   ```

## 运行方式

### 方式一：环境变量

```bash
export XHS_COOKIE="a1=xxx; web_session=xxx; webId=xxx"
python -m scripts.crawlers.xhs.run_xhs_crawl
```

### 方式二：命令行参数

```bash
python -m scripts.crawlers.xhs.run_xhs_crawl \
  --keywords "销售话术" "成交技巧" \
  --max 30 \
  --cookie "a1=xxx; web_session=xxx; webId=xxx"
```

### 方式三：使用签名服务（推荐，更稳定）

```bash
# 启动 xhs-api Docker
docker run -it -d -p 5005:5005 reajason/xhs-api:latest

# 运行爬虫
XHS_SIGN_API_URL=http://localhost:5005 XHS_COOKIE="a1=xxx; web_session=xxx; webId=xxx" \
  python -m scripts.crawlers.xhs.run_xhs_crawl
```

## 输出格式

输出文件：`data/raw/xhs/xhs-{timestamp}.jsonl`

每行一条 JSON，字段与 TikTok 对齐：

| 字段 | 说明 |
|------|------|
| note_id | 笔记 ID |
| title | 标题 |
| desc | 正文内容 |
| user_id | 作者 ID |
| liked_count | 点赞数 |
| comment_count | 评论数 |
| collected_count | 收藏数 |
| share_count | 分享数 |
| tags | 标签列表 |
| image_urls | 图片 URL |
| url | 笔记链接 |
| keyword | 搜索关键词 |
| collected_at | 采集时间 |
| source | 固定为 "xhs" |

## 数据用途

采集后的 JSONL 数据可用于：内容分析、趋势研究、与 TikTok 等平台数据合并处理（schema 对齐）。

## 注意事项

1. **合规**：仅采集公开可访问数据，遵守平台协议与法律法规
2. **频率**：默认请求间隔 2 秒，避免触发反爬
3. **Cookie 有效期**：web_session 会过期，需定期更新
4. **验证码**：若出现验证码，可尝试更换 IP 或使用签名服务
