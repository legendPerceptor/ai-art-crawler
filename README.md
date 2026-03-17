# AI Art Crawler - AI 艺术爬虫项目

## 项目目标

从 AI 艺术社区网站爬取提示词（prompts）和图片，用于测试 aicreatorvault 平台。

## 目标网站

| 网站 | 特点 | 难度 |
|------|------|------|
| **Midjourney Gallery** | 官方作品展示，高质量 | ⭐⭐⭐ 需要登录 |
| **Civitai** | Stable Diffusion 模型和图片 | ⭐⭐ 有 API |
| **Lexica.art** | Stable Diffusion 图片库 | ⭐⭐ 有搜索 API |
| **PromptHero** | 提示词搜索引擎 | ⭐⭐ 简单爬取 |
| **OpenArt** | AI 艺术作品库 | ⭐⭐ 有分类 |
| **ArtStation AI** | 艺术家作品，质量高 | ⭐⭐⭐ 需要反爬 |

## 技术栈

- **语言**: Python 3.11+
- **爬虫框架**: Playwright (处理 JS 渲染)
- **数据库**: SQLite (轻量) / PostgreSQL (与 aicreatorvault 共用)
- **图片存储**: 本地文件系统 / S3 兼容存储
- **任务队列**: Celery + Redis (可选，用于大规模爬取)

## 项目结构

```
ai-art-crawler/
├── crawler/
│   ├── __init__.py
│   ├── base.py           # 基础爬虫类
│   ├── midjourney.py     # Midjourney 爬虫
│   ├── civitai.py        # Civitai 爬虫
│   ├── lexica.py         # Lexica 爬虫
│   ├── prompthero.py     # PromptHero 爬虫
│   └── utils.py          # 工具函数
├── storage/
│   ├── __init__.py
│   ├── database.py       # 数据库操作
│   ├── image_store.py    # 图片存储
│   └── models.py         # 数据模型
├── exporters/
│   ├── __init__.py
│   ├── aicreatorvault.py # 导出到 aicreatorvault
│   └── json_export.py    # JSON 导出
├── config/
│   ├── __init__.py
│   ├── settings.py       # 配置文件
│   └── logging.py        # 日志配置
├── scripts/
│   ├── run_crawler.py    # 运行爬虫
│   ├── export_to_aicv.py # 导出数据
│   └── clean_duplicates.py
├── tests/
│   └── test_crawlers.py
├── docker/
│   ├── Dockerfile
│   └── docker-compose.yml
├── requirements.txt
├── pyproject.toml
└── README.md
```

## 数据模型

### Artwork (作品)

```python
{
    "id": "uuid",
    "source": "midjourney",      # 来源网站
    "source_id": "xxx",          # 原网站 ID
    "source_url": "https://...", # 原链接
    "prompt": "a beautiful...",  # 提示词
    "negative_prompt": "...",    # 负面提示词
    "model": "midjourney-v6",    # 模型
    "style": "photorealistic",   # 风格
    "width": 1024,
    "height": 1024,
    "image_url": "https://...",  # 图片 URL
    "local_path": "/path/...",   # 本地存储路径
    "seed": 12345,               # 种子值
    "author": "username",        # 作者
    "likes": 100,                # 点赞数
    "tags": ["portrait", "ai"],  # 标签
    "created_at": "2024-01-01",  # 原始创建时间
    "crawled_at": "2024-01-02",  # 爬取时间
}
```

## 开发计划

### Phase 1: 基础架构 (Day 1-2)
- [x] 创建项目结构
- [ ] 配置 Playwright 环境
- [ ] 实现基础爬虫类
- [ ] 数据库模型和存储

### Phase 2: 爬虫实现 (Day 3-5)
- [ ] Civitai 爬虫 (最简单，有 API)
- [ ] Lexica 爬虫
- [ ] PromptHero 爬虫
- [ ] Midjourney 爬虫 (需要处理登录)

### Phase 3: 数据处理 (Day 6-7)
- [ ] 图片下载和存储
- [ ] 去重机制
- [ ] 数据清洗

### Phase 4: 集成导出 (Day 8-9)
- [ ] 导出到 aicreatorvault API
- [ ] 批量导入脚本
- [ ] 数据同步机制

### Phase 5: 优化和部署 (Day 10)
- [ ] Docker 容器化
- [ ] 定时任务
- [ ] 监控和日志

## 使用方式

```bash
# 安装依赖
pip install -r requirements.txt
playwright install chromium

# 运行爬虫
python scripts/run_crawler.py --site civitai --limit 100

# 导出到 aicreatorvault
python scripts/export_to_aicv.py --input data/crawled.json
```

## 注意事项

1. **遵守 robots.txt** - 尊重网站的爬虫协议
2. **速率限制** - 避免对目标网站造成压力
3. **数据使用** - 仅用于个人测试，不用于商业用途
4. **版权** - 注意图片的版权和授权

## 下一步

1. 确认要爬取的网站优先级
2. 选择技术方案（Playwright vs Requests）
3. 开始实现第一个爬虫（推荐从 Civitai 开始）
