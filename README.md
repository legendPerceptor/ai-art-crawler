# AI Art Crawler

从 AI 艺术社区网站爬取提示词和图片，支持导入到 aicreatorvault 平台。

## 🎯 支持的网站

| 网站 | 状态 | 特点 |
|------|------|------|
| **Civitai** | ✅ 已实现 | API 支持，无需浏览器 |
| **Lexica** | 🚧 待开发 | Stable Diffusion 图片库 |
| **PromptHero** | 🚧 待开发 | 提示词搜索引擎 |

## 🚀 快速开始

### 1. 构建 Docker 镜像

```bash
cd ai-art-crawler
docker build -t ai-art-crawler -f docker/Dockerfile .
```

### 2. 爬取 Civitai 数据

```bash
# 基本用法 - 爬取 50 张人像图片
docker run --rm \
  --network proxy-net \
  -e HTTP_PROXY=http://172.18.0.2:1087 \
  -e HTTPS_PROXY=http://172.18.0.2:1087 \
  -v $(pwd)/data:/data \
  ai-art-crawler \
  python scripts/run_crawler.py --site civitai --limit 50 --tag portrait --download
```

**参数说明：**
- `--site civitai` - 爬取 Civitai 网站
- `--limit 50` - 爬取数量
- `--tag portrait` - 按标签过滤（可选）
- `--download` - 下载图片到本地

**常用标签：**
- `portrait` - 人像
- `landscape` - 风景
- `anime` - 动漫
- `realistic` - 写实

### 3. 导入到 aicreatorvault

```bash
# 确保 aicreatorvault 服务已启动
docker run --rm \
  --network aicreatorvault_aicreatorvault-net \
  -v $(pwd)/data:/data \
  ai-art-crawler \
  python scripts/export_to_aicv.py /data/crawled/civitai_*.json \
  --url http://aicreatorvault-backend-1:3001
```

**参数说明：**
- `--url` - aicreatorvault 后端地址
- `--limit 10` - 限制导入数量（可选）

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

### 场景 1：爬取并导入 100 张人像图片

```bash
# Step 1: 爬取数据
docker run --rm \
  --network proxy-net \
  -e HTTP_PROXY=http://172.18.0.2:1087 \
  -e HTTPS_PROXY=http://172.18.0.2:1087 \
  -v $(pwd)/data:/data \
  ai-art-crawler \
  python scripts/run_crawler.py --site civitai --limit 100 --tag portrait --download

# Step 2: 导入到 aicreatorvault
docker run --rm \
  --network aicreatorvault_aicreatorvault-net \
  -v $(pwd)/data:/data \
  ai-art-crawler \
  python scripts/export_to_aicv.py /data/crawled/civitai_*.json \
  --url http://aicreatorvault-backend-1:3001
```

### 场景 2：测试模式 - 爬取 10 条数据

```bash
# 仅爬取提示词，不下载图片
docker run --rm \
  --network proxy-net \
  -e HTTP_PROXY=http://172.18.0.2:1087 \
  -e HTTPS_PROXY=http://172.18.0.2:1087 \
  -v $(pwd)/data:/data \
  ai-art-crawler \
  python scripts/run_crawler.py --site civitai --limit 10 --tag portrait

# 导入前 5 条测试
docker run --rm \
  --network aicreatorvault_aicreatorvault-net \
  -v $(pwd)/data:/data \
  ai-art-crawler \
  python scripts/export_to_aicv.py /data/crawled/civitai_*.json \
  --url http://aicreatorvault-backend-1:3001 --limit 5
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
├── requirements.txt
└── README.md
```

## 🔧 高级配置

### 使用代理

爬虫容器需要通过代理访问外网：

```bash
# 方式 1: 使用宿主机代理
-e HTTP_PROXY=http://172.18.0.2:1087

# 方式 2: 使用容器名（需要在同一网络）
-e HTTP_PROXY=http://xray:1087
```

### 保存到数据库

```bash
# 保存到 PostgreSQL（需要配置 DATABASE_URL）
docker run --rm \
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

导入流程：

1. **创建提示词** - 通过 API 创建提示词记录
2. **上传图片** - 优先使用本地已下载的图片
3. **关联数据** - 图片自动关联到提示词

导入后可在 aicreatorvault 前端查看：
- 提示词列表
- 图片预览
- 关联关系

## 📝 开发计划

- [x] Civitai API 爬虫
- [x] 图片下载
- [x] aicreatorvault 导入
- [ ] Lexica 爬虫
- [ ] PromptHero 爬虫
- [ ] Midjourney 爬虫
- [ ] 定时任务
- [ ] 去重机制

## 📄 License

MIT
