"""
基础爬虫类
"""
import asyncio
import hashlib
import json
import re
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Any, Optional
from urllib.parse import urljoin, urlparse

from playwright.async_api import async_playwright, Browser, Page, BrowserContext
from pydantic import BaseModel, Field


class Artwork(BaseModel):
    """爬取的艺术作品数据模型"""
    id: str = Field(default_factory=lambda: "")
    source: str  # 来源网站
    source_id: str = ""  # 原网站 ID
    source_url: str  # 原链接
    prompt: str = ""  # 提示词
    negative_prompt: str = ""  # 负面提示词
    model: str = ""  # 使用的模型
    style: str = ""  # 风格
    width: int = 0
    height: int = 0
    image_url: str = ""  # 图片 URL
    local_path: str = ""  # 本地存储路径
    seed: Optional[int] = None  # 种子值
    author: str = ""  # 作者
    likes: int = 0  # 点赞数
    tags: list[str] = Field(default_factory=list)  # 标签
    created_at: Optional[datetime] = None  # 原始创建时间
    crawled_at: datetime = Field(default_factory=datetime.now)  # 爬取时间
    raw_data: dict = Field(default_factory=dict)  # 原始数据

    def __post_init__(self):
        if not self.id:
            # 使用 source + source_id 或 URL 生成唯一 ID
            unique_str = f"{self.source}:{self.source_id or self.source_url}"
            self.id = hashlib.md5(unique_str.encode()).hexdigest()[:16]


class BaseCrawler(ABC):
    """基础爬虫类"""

    def __init__(
        self,
        name: str,
        base_url: str,
        output_dir: str = "data/crawled",
        proxy: Optional[str] = None,
        headless: bool = True,
        rate_limit: float = 1.0,  # 每秒请求数
    ):
        self.name = name
        self.base_url = base_url
        self.output_dir = Path(output_dir)
        self.proxy = proxy
        self.headless = headless
        self.rate_limit = rate_limit
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self._last_request_time = 0.0

    async def setup(self):
        """初始化浏览器"""
        self.playwright = await async_playwright().start()
        
        launch_args = {
            "headless": self.headless,
        }
        
        if self.proxy:
            launch_args["proxy"] = {"server": self.proxy}

        self.browser = await self.playwright.chromium.launch(**launch_args)
        self.context = await self.browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        
        # 创建输出目录
        self.output_dir.mkdir(parents=True, exist_ok=True)
        (self.output_dir / "images").mkdir(exist_ok=True)

    async def teardown(self):
        """清理资源"""
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
        if hasattr(self, 'playwright'):
            await self.playwright.stop()

    async def rate_limit_wait(self):
        """等待以遵守速率限制"""
        import time
        elapsed = time.time() - self._last_request_time
        wait_time = (1.0 / self.rate_limit) - elapsed
        if wait_time > 0:
            await asyncio.sleep(wait_time)
        self._last_request_time = time.time()

    async def new_page(self) -> Page:
        """创建新页面"""
        return await self.context.new_page()

    async def download_image(self, url: str, save_path: Optional[Path] = None) -> str:
        """下载图片"""
        import httpx
        
        if not save_path:
            ext = Path(urlparse(url).path).suffix or ".jpg"
            filename = hashlib.md5(url.encode()).hexdigest() + ext
            save_path = self.output_dir / "images" / filename
        
        async with httpx.AsyncClient(timeout=30.0, proxy=self.proxy) as client:
            await self.rate_limit_wait()
            response = await client.get(url, follow_redirects=True)
            response.raise_for_status()
            
            save_path.write_bytes(response.content)
            return str(save_path)

    def save_artworks(self, artworks: list[Artwork], filename: Optional[str] = None):
        """保存爬取的数据"""
        if not filename:
            filename = f"{self.name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        filepath = self.output_dir / filename
        
        data = []
        for a in artworks:
            item = a.model_dump()
            # 处理 datetime 序列化
            if isinstance(item.get('crawled_at'), datetime):
                item['crawled_at'] = item['crawled_at'].isoformat()
            if isinstance(item.get('created_at'), datetime):
                item['created_at'] = item['created_at'].isoformat()
            data.append(item)
        
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        return filepath

    @abstractmethod
    async def crawl(self, limit: int = 100, **kwargs) -> list[Artwork]:
        """爬取数据（子类实现）"""
        pass

    async def run(self, limit: int = 100, **kwargs) -> list[Artwork]:
        """运行爬虫"""
        await self.setup()
        try:
            artworks = await self.crawl(limit=limit, **kwargs)
            self.save_artworks(artworks)
            return artworks
        finally:
            await self.teardown()
