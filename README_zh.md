# AI Art Crawler

[English](README.md)

从 AI 艺术社区网站爬取提示词和图片，支持导入到 aicreatorvault 平台。

## 🎯 支持的网站

| 网站 | 状态 | 特点 |
|------|------|------|
| **Civitai** | ✅ 已实现 | API 支持，无需浏览器 |
| **Lexica** | 🚧 待开发 | Stable Diffusion 图片库 |
| **PromptHero** | 🚧 待开发 | 提示词搜索引擎 |

## 🚀 快速开始

### 方式一：本地运行（推荐开发）

**安装依赖**：

```bash
# 使用 uv 安装依赖（推荐）
uv sync
# Editable Install
uv pip install -e .
```

**运行爬虫**：

```bash
# 基本用法
uv run python scripts/run_crawler.py --site civitai --limit 50 --download

# 使用代理
HTTPS_PROXY=http://localhost:1087 python scripts/run_crawler.py --limit 100 --download

# 获取本周最热图片
uv run python scripts/run_crawler.py --limit 50 --period Week --sort "Most Reactions" --download

# 保存到数据库
DATABASE_URL="postgresql://user:pass@localhost:5432/db" \
  python scripts/run_crawler.py --limit 50 --save-db
```

**导出到 aicreatorvault**：

```bash
# 导入数据（需要认证 - 使用邮箱登录，用户不存在时自动注册）
uv run python scripts/export_to_aicv.py data/crawled/civitai_*.json \
  --url http://localhost:3001 \
  --email your@email.com --password yourpassword

# 或直接指定用户ID
uv run python scripts/export_to_aicv.py data/crawled/civitai_*.json \
  --url http://localhost:3001 --user-id 1

# 使用旧 API（禁用知识图谱）
uv run python scripts/export_to_aicv.py data/crawled/civitai_*.json --url http://localhost:3001 --no-kg

# 限制导入数量（测试用）
uv run python scripts/export_to_aicv.py data/crawled/civitai_*.json --limit 10
```

---

### 方式二：使用 Docker Compose（推荐部署）

**构建镜像**：

```bash
docker build -t ai-art-crawler -f docker/Dockerfile .
```

**爬取数据**：

```bash
# 使用docker compose
docker compose --profile crawl run --rm crawler
```


```bash
# 爬取 50 张人像图片（需要配置代理）
docker run --rm \
  --network aicreatorvault-net \
  -e HTTP_PROXY=http://aigc-xray:1087 \
  -e HTTPS_PROXY=http://aigc-xray:1087 \
  -v $(pwd)/data:/data \
  ai-art-crawler \
  python scripts/run_crawler.py --site civitai --limit 50 --tag portrait --download
```

**导入到 aicreatorvault**（需要认证）：

```bash
docker run --rm \
  --network aicreatorvault-net \
  -v $(pwd)/data:/data \
  ai-art-crawler \
  python scripts/export_to_aicv.py /data/crawled/civitai_*.json \
  --url http://aicreatorvault-backend-1:3001 \
  --email your@email.com --password yourpassword
```

### 命令行参数说明

**爬虫参数**：
- `--site civitai` - 爬取 Civitai 网站
- `--limit 50` - 爬取数量
- `--download` - 下载图片到本地
- `--save-db` - 保存到数据库（需要配置 DATABASE_URL）
- `--period Day` - 时间范围：AllTime, Year, Month, Week, Day
- `--sort Newest` - 排序方式：Newest, Most Reactions, Most Comments

**获取不同数据**：
```bash
# 今日最新
python scripts/run_crawler.py --limit 50 --period Day --sort Newest

# 本周最热
python scripts/run_crawler.py --limit 50 --period Week --sort "Most Reactions"

# 历史最热
python scripts/run_crawler.py --limit 50 --period AllTime --sort "Most Reactions"
```

**导出参数**：
- `--url` - aicreatorvault 后端地址
- `--limit 10` - 限制导入数量（可选）
- `--no-kg` - 禁用知识图谱模式（使用旧 API）
- `--no-download` - 不上传图片（仅导入提示词）
- `--proxy` - 代理服务器（可选）
- `--no-proxy` - 不使用代理（可选）

## 📁 数据格式

爬取的数据保存为 JSON 格式：

```json
{
  "source": "civitai",
  "source_id": "12097475",
  "prompt": "score_9, score_8_up, score_7_up, 1girl, full body...",
  "negative_prompt": "score_6, score_5, score_4",
  "image_url": "https://image.civitai.com/...",
  "local_path": "/data/crawled/images/xxx.jpeg",
  "width": 1520,
  "height": 1952,
  "seed": 3269595310,
  "author": "Stellaaa",
  "likes": 0
}
```

## 🛠️ 完整示例

### 场景 1：爬取并导入 100 张人像图片（Docker Compose）

```bash
# Step 1: 爬取数据
docker compose --profile crawl run --rm crawler \
  python scripts/run_crawler.py --site civitai --limit 100 --tag portrait --download

# Step 2: 导入到 aicreatorvault
docker compose --profile export run --rm exporter
```

### 场景 2：测试模式 - 爬取 10 条数据

```bash
# 仅爬取提示词，不下载图片
docker compose --profile crawl run --rm crawler \
  python scripts/run_crawler.py --site civitai --limit 10 --tag portrait

# 导入前 5 条测试
docker compose --profile export run --rm exporter \
  python scripts/export_to_aicv.py /data/crawled/civitai_*.json --url $$AICV_URL --limit 5
```

## 📊 项目结构

```
ai-art-crawler/
├── crawler/
│   ├── base.py           # 基础爬虫类
│   └── civitai.py        # Civitai API 爬虫
├── scripts/
│   ├── run_crawler.py    # 运行爬虫
│   └── export_to_aicv.py # 导出到 aicreatorvault
├── storage/
│   └── database.py       # 数据库操作
├── config/
│   └── settings.py       # 配置
├── docker/
│   └── Dockerfile        # Docker 镜像
├── data/                 # 数据目录
│   ├── crawled/          # 爬取的 JSON
│   └── images/           # 下载的图片
├── docker-compose.yml    # Docker Compose 配置
├── requirements.txt
└── README.md
```

## 🔧 高级配置

### 使用代理

爬虫需要通过代理访问外网，Docker Compose 方式已自动配置 `aigc-xray` 代理：

```bash
# Docker Compose 方式（自动配置）
HTTP_PROXY=http://aigc-xray:1087
HTTPS_PROXY=http://aigc-xray:1087

# docker run 方式需要手动指定
docker run --rm \
  --network aicreatorvault-net \
  -e HTTP_PROXY=http://aigc-xray:1087 \
  -e HTTPS_PROXY=http://aigc-xray:1087 \
  ...
```

### 保存到数据库

```bash
# Docker Compose 方式（已配置 DATABASE_URL）
docker compose --profile crawl run --rm crawler \
  python scripts/run_crawler.py --site civitai --limit 50 --save-db

# docker run 方式需要手动指定
docker run --rm \
  --network aicreatorvault-net \
  -e DATABASE_URL="postgresql://user:pass@host:5432/db" \
  ai-art-crawler \
  python scripts/run_crawler.py --site civitai --limit 50 --save-db
```

## ⚠️ 注意事项

1. **遵守 robots.txt** - 尊重网站的爬虫协议
2. **速率限制** - 默认 2 请求/秒，避免对目标网站造成压力
3. **数据使用** - 仅用于个人测试，不用于商业用途
4. **版权** - 注意图片的版权和授权

## 🔄 与 aicreatorvault 集成

### 知识图谱模式（默认）

导入流程：

1. **创建提示词资产** - 通过 `/api/assets` 创建 Prompt 资产
2. **上传图片资产** - 通过 `/api/assets/upload` 创建 Image 资产
3. **创建图谱关系** - 通过 `/api/relationships` 创建 Prompt → Image 的 `generated` 关系

导入后可在 aicreatorvault 前端的"知识图谱"页面查看：
- 资产节点（提示词、图片）
- 关系边（生成关系）
- 图谱可视化

### 旧 API 模式

使用 `--no-kg` 参数启用旧 API：

1. **创建提示词** - 通过 `/api/prompts` 创建提示词
2. **上传图片** - 通过 `/api/images` 上传图片并关联 promptId
3. **关联数据** - 图片自动关联到提示词

### API 对比

| 功能 | 知识图谱模式 (默认) | 旧 API 模式 (--no-kg) |
|------|-------------------|---------------------|
| 提示词创建 | `/api/assets` (type: prompt) | `/api/prompts` |
| 图片上传 | `/api/assets/upload` | `/api/images` |
| 关系管理 | `/api/relationships` | 通过 promptId 自动关联 |
| 图谱支持 | ✅ 完整知识图谱 | ❌ 仅基础关联 |
| 评分范围 | 0-10 | 0-5 |
| 前端展示 | "知识图谱"标签页 | "提示词"和"图片"标签页 |

## 📝 开发计划

- [x] Civitai API 爬虫
- [x] 图片下载
- [x] aicreatorvault 导入
- [x] 去重机制（支持多文件导入和跨文件去重）
- [x] 知识图谱支持（Prompt -> Image 关系）
- [ ] Lexica 爬虫
- [ ] PromptHero 爬虫
- [ ] Midjourney 爬虫
- [ ] 定时任务

## 📄 License

MIT
