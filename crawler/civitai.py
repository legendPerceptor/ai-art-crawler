"""
Civitai 爬虫 - 从 Civitai.com 爬取 AI 图片和提示词

Civitai 有公开 API，比较容易爬取
API 文档: https://civitai.com/api/v1
"""
import asyncio
from datetime import datetime
from typing import Optional
from urllib.parse import urlencode

from crawler.base import BaseCrawler, Artwork


class CivitaiCrawler(BaseCrawler):
    """Civitai 爬虫"""

    API_BASE = "https://civitai.com/api/v1"

    def __init__(self, **kwargs):
        super().__init__(
            name="civitai",
            base_url="https://civitai.com",
            **kwargs
        )
        self.session = None

    async def setup(self):
        """初始化"""
        await super().setup()
        import httpx
        self.http_client = httpx.AsyncClient(
            timeout=30.0,
            proxy=self.proxy,
            follow_redirects=True
        )

    async def teardown(self):
        """清理"""
        if self.http_client:
            await self.http_client.aclose()
        await super().teardown()

    async def fetch_images(
        self,
        limit: int = 100,
        cursor: Optional[str] = None,
        model_id: Optional[int] = None,
        tag: Optional[str] = None,
    ) -> dict:
        """
        获取图片列表
        
        Args:
            limit: 数量限制 (1-200)
            cursor: 分页游标
            model_id: 模型 ID
            tag: 标签过滤
        """
        params = {"limit": min(limit, 200), "nsfw": "false"}
        
        if cursor:
            params["cursor"] = cursor
        if model_id:
            params["modelId"] = model_id
        if tag:
            params["tag"] = tag

        url = f"{self.API_BASE}/images?{urlencode(params)}"
        
        await self.rate_limit_wait()
        response = await self.http_client.get(url)
        response.raise_for_status()
        
        return response.json()

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
        
        # 解析创建时间
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
        **kwargs
    ) -> list[Artwork]:
        """
        爬取图片
        
        Args:
            limit: 爬取数量
            tag: 按标签过滤 (如 "portrait", "landscape")
            download_images: 是否下载图片
        """
        artworks = []
        cursor = None
        batch_size = 100  # API 每次最多返回 100 条

        print(f"开始爬取 Civitai，目标数量: {limit}")
        
        while len(artworks) < limit:
            remaining = min(batch_size, limit - len(artworks))
            
            data = await self.fetch_images(
                limit=remaining,
                cursor=cursor,
                tag=tag
            )
            
            items = data.get("items", [])
            if not items:
                print("没有更多数据")
                break
            
            for item in items:
                artwork = self.parse_image_data(item)
                
                # 下载图片
                if download_images and artwork.image_url:
                    try:
                        local_path = await self.download_image(artwork.image_url)
                        artwork.local_path = local_path
                    except Exception as e:
                        print(f"下载图片失败: {e}")
                
                artworks.append(artwork)
                
                if len(artworks) >= limit:
                    break
            
            # 获取下一页游标
            cursor = data.get("metadata", {}).get("nextCursor")
            if not cursor:
                print("已到达最后一页")
                break
            
            print(f"已爬取 {len(artworks)}/{limit}")
        
        print(f"爬取完成，共 {len(artworks)} 条数据")
        return artworks


async def main():
    """测试爬虫"""
    crawler = CivitaiCrawler(
        output_dir="data/civitai",
        rate_limit=2.0,  # 每秒 2 个请求
    )
    
    # 爬取 50 张人像图片
    artworks = await crawler.run(
        limit=50,
        tag="portrait",
        download_images=True
    )
    
    print(f"\n爬取结果:")
    for a in artworks[:5]:
        print(f"  - {a.prompt[:50]}... (by {a.author})")
    
    print(f"\n数据已保存到: {crawler.output_dir}")


if __name__ == "__main__":
    asyncio.run(main())
