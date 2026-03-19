"""
Civitai 爬虫 - 从 Civitai.com 爬取 AI 图片和提示词
"""
import asyncio
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Optional
from urllib.parse import urlencode

import httpx
from pydantic import BaseModel, Field


class Artwork(BaseModel):
    """爬取的艺术作品数据模型"""
    id: str = ""
    source: str
    source_id: str = ""
    source_url: str = ""
    prompt: str = ""
    negative_prompt: str = ""
    model: str = ""
    style: str = ""
    width: int = 0
    height: int = 0
    image_url: str = ""
    local_path: str = ""
    seed: Optional[int] = None
    author: str = ""
    likes: int = 0
    tags: list[str] = Field(default_factory=list)
    created_at: Optional[datetime] = None
    crawled_at: datetime = Field(default_factory=datetime.now)
    raw_data: dict = Field(default_factory=dict)

    def __post_init__(self):
        if not self.id:
            unique_str = f"{self.source}:{self.source_id or self.source_url}"
            self.id = hashlib.md5(unique_str.encode()).hexdigest()[:16]


class CivitaiCrawler:
    """Civitai API 爬虫（无需浏览器）"""

    API_BASE = "https://civitai.com/api/v1"

    def __init__(
        self,
        output_dir: str = "data/crawled",
        proxy: Optional[str] = None,
        rate_limit: float = 2.0,
    ):
        self.output_dir = Path(output_dir)
        self.proxy = proxy
        self.rate_limit = rate_limit
        self.http_client = None
        self._last_request_time = 0.0

    async def setup(self):
        """初始化"""
        self.output_dir.mkdir(parents=True, exist_ok=True)
        (self.output_dir / "images").mkdir(exist_ok=True)
        
        self.http_client = httpx.AsyncClient(
            timeout=30.0,
            proxy=self.proxy,
            follow_redirects=True
        )

    async def teardown(self):
        """清理"""
        if self.http_client:
            await self.http_client.aclose()

    async def rate_limit_wait(self):
        """等待以遵守速率限制"""
        import time
        elapsed = time.time() - self._last_request_time
        wait_time = (1.0 / self.rate_limit) - elapsed
        if wait_time > 0:
            await asyncio.sleep(wait_time)
        self._last_request_time = time.time()

    async def fetch_images(
        self,
        limit: int = 100,
        cursor: Optional[str] = None,
        tag: Optional[str] = None,
        period: str = "day",
        sort: str = "newest",
    ) -> dict:
        """获取图片列表

        Args:
            limit: 获取数量
            cursor: 分页游标
            tag: 标签过滤
            period: 时间范围 (day, week, month, year, all)
            sort: 排序方式 (newest, most_reacted, most_collected)
        """
        params = {
            "limit": min(limit, 200),
            "nsfw": "false",
            "period": period,
            "sort": sort,
        }

        if cursor:
            params["cursor"] = cursor
        if tag:
            params["tag"] = tag

        url = f"{self.API_BASE}/images?{urlencode(params)}"

        await self.rate_limit_wait()
        response = await self.http_client.get(url)
        response.raise_for_status()

        return response.json()

    async def download_image(self, url: str) -> str:
        """下载图片"""
        ext = Path(url.split("?")[0]).suffix or ".jpg"
        filename = hashlib.md5(url.encode()).hexdigest() + ext
        save_path = self.output_dir / "images" / filename
        
        await self.rate_limit_wait()
        response = await self.http_client.get(url)
        response.raise_for_status()
        
        save_path.write_bytes(response.content)
        return str(save_path)

    def parse_image_data(self, data: dict) -> Artwork:
        """解析图片数据"""
        meta = data.get("meta", {}) or {}
        
        artwork = Artwork(
            source="civitai",
            source_id=str(data.get("id", "")),
            source_url=f"https://civitai.com/images/{data.get('id')}",
            prompt=meta.get("prompt", ""),
            negative_prompt=meta.get("negativePrompt", ""),
            model=meta.get("Model", meta.get("model", "")),
            style=meta.get("Style", ""),
            width=data.get("width", 0),
            height=data.get("height", 0),
            image_url=data.get("url", ""),
            seed=meta.get("seed"),
            author=data.get("username", ""),
            likes=data.get("stats", {}).get("likeCount", 0),
            tags=[tag.get("name", "") for tag in data.get("tags", [])],
            raw_data=data,
        )
        
        if data.get("createdAt"):
            try:
                artwork.created_at = datetime.fromisoformat(
                    data["createdAt"].replace("Z", "+00:00")
                )
            except:
                pass
        
        return artwork

    async def crawl(
        self,
        limit: int = 100,
        tag: Optional[str] = None,
        download_images: bool = False,
        period: str = "day",
        sort: str = "newest",
    ) -> list[Artwork]:
        """爬取图片"""
        artworks = []
        cursor = None
        batch_size = 100

        print(f"开始爬取 Civitai，目标数量: {limit}")
        print(f"  标签: {tag or '全部'}")
        print(f"  时间范围: {period}")
        print(f"  排序: {sort}")

        while len(artworks) < limit:
            remaining = min(batch_size, limit - len(artworks))

            data = await self.fetch_images(
                limit=remaining,
                cursor=cursor,
                tag=tag,
                period=period,
                sort=sort,
            )

            items = data.get("items", [])
            if not items:
                print("没有更多数据")
                break

            for item in items:
                artwork = self.parse_image_data(item)

                if download_images and artwork.image_url:
                    try:
                        local_path = await self.download_image(artwork.image_url)
                        artwork.local_path = local_path
                    except Exception as e:
                        print(f"下载图片失败: {e}")

                artworks.append(artwork)

                if len(artworks) >= limit:
                    break

            cursor = data.get("metadata", {}).get("nextCursor")
            if not cursor:
                break

            print(f"已爬取 {len(artworks)}/{limit}")

        print(f"爬取完成，共 {len(artworks)} 条数据")
        return artworks

    def save_artworks(self, artworks: list[Artwork]) -> Path:
        """保存数据到 JSON"""
        import json
        
        filename = f"civitai_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        filepath = self.output_dir / filename
        
        data = []
        for a in artworks:
            item = a.model_dump()
            if isinstance(item.get('crawled_at'), datetime):
                item['crawled_at'] = item['crawled_at'].isoformat()
            if isinstance(item.get('created_at'), datetime):
                item['created_at'] = item['created_at'].isoformat()
            data.append(item)
        
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        return filepath

    async def run(
        self,
        limit: int = 100,
        tag: Optional[str] = None,
        download_images: bool = False,
        period: str = "day",
        sort: str = "newest",
    ) -> list[Artwork]:
        """运行爬虫"""
        await self.setup()
        try:
            artworks = await self.crawl(
                limit=limit,
                tag=tag,
                download_images=download_images,
                period=period,
                sort=sort,
            )
            self.save_artworks(artworks)
            return artworks
        finally:
            await self.teardown()
