#!/usr/bin/env python3
"""
将爬取的数据导入到 aicreatorvault
"""
import argparse
import asyncio
import json
from pathlib import Path
from typing import Optional
from datetime import datetime

import httpx


class AICreatorVaultImporter:
    """导入数据到 aicreatorvault"""

    def __init__(
        self,
        base_url: str = "http://localhost:3001",
        api_prefix: str = "/api",
        proxy: Optional[str] = None,
    ):
        self.base_url = base_url.rstrip("/")
        self.api_url = f"{self.base_url}{api_prefix}"
        # 默认使用 aigc-xray 代理（在 aicreatorvault 网络中）
        if proxy is None:
            proxy = "http://aigc-xray:1087"
        self.client = httpx.AsyncClient(timeout=60.0, proxy=proxy, follow_redirects=True)

    async def close(self):
        await self.client.aclose()

    async def health_check(self) -> bool:
        """检查 API 是否可用"""
        try:
            response = await self.client.get(f"{self.api_url}/prompts")
            return response.status_code == 200
        except:
            return False

    async def create_prompt(
        self,
        content: str,
        score: int = 0,
        check_duplicate: bool = True,
    ) -> dict:
        """创建提示词
        
        Args:
            content: 提示词内容
            score: 评分 (0-5)
            check_duplicate: 是否检查重复
        """
        # 检查是否已存在相同内容的提示词
        if check_duplicate:
            response = await self.client.get(f"{self.api_url}/prompts")
            if response.status_code == 200:
                existing = response.json()
                # 查找内容相同的提示词
                for p in existing:
                    if p.get('content') == content:
                        print(f"  ℹ️  提示词已存在 (ID: {p['id']})，跳过创建")
                        return p
        
        response = await self.client.post(
            f"{self.api_url}/prompts",
            json={
                "content": content,
                "score": min(max(score, 0), 5),  # 限制在 0-5
            }
        )
        response.raise_for_status()
        return response.json()

    async def download_image(self, url: str) -> bytes:
        """下载图片"""
        try:
            response = await self.client.get(url, follow_redirects=True)
            response.raise_for_status()
            return response.content
        except Exception as e:
            print(f"  ⚠️ 图片下载失败: {str(e)[:100]}")
            raise

    async def upload_image(
        self,
        image_data: bytes,
        filename: str,
        prompt_id: Optional[int] = None,
        analyze: bool = True,
    ) -> dict:
        """上传图片到 aicreatorvault
        
        Args:
            image_data: 图片二进制数据
            filename: 文件名
            prompt_id: 关联的提示词 ID
            analyze: 是否自动分析图片
        """
        files = {"image": (filename, image_data, "image/jpeg")}
        data = {}
        
        if prompt_id:
            data["promptId"] = str(prompt_id)
        
        # 关闭自动分析（导入时批量分析更高效）
        data["autoAnalyze"] = "false"

        response = await self.client.post(
            f"{self.api_url}/images",
            files=files,
            data=data,
        )
        response.raise_for_status()
        return response.json()

    async def import_artwork(
        self,
        artwork: dict,
        download_images: bool = True,
    ) -> dict:
        """导入单个作品
        
        Args:
            artwork: 爬取的作品数据
            download_images: 是否下载图片
        """
        result = {
            "source_id": artwork.get("source_id"),
            "prompt_created": False,
            "image_uploaded": False,
            "prompt_id": None,
            "image_id": None,
            "error": None,
        }
        
        try:
            # 1. 创建提示词
            prompt_content = artwork.get("prompt", "")
            if not prompt_content:
                result["error"] = "No prompt content"
                return result
            
            # 计算评分（基于点赞数）
            likes = artwork.get("likes", 0)
            score = min(likes // 10, 5)  # 每10个点赞得1分，最高5分
            
            prompt_data = await self.create_prompt(
                content=prompt_content,
                score=score,
            )
            result["prompt_created"] = True
            result["prompt_id"] = prompt_data.get("id")
            
            # 2. 上传图片（优先使用本地文件）
            if download_images:
                image_data = None
                filename = None
                
                # 优先使用本地文件
                local_path = artwork.get("local_path")
                if local_path:
                    try:
                        import os
                        if os.path.exists(local_path):
                            with open(local_path, "rb") as f:
                                image_data = f.read()
                            filename = os.path.basename(local_path)
                            print(f"  📁 使用本地图片: {filename}")
                    except Exception as e:
                        print(f"  ⚠️ 读取本地图片失败: {e}")
                
                # 如果本地文件不存在，从 URL 下载
                if not image_data and artwork.get("image_url"):
                    try:
                        image_data = await self.download_image(artwork["image_url"])
                        ext = ".jpg"
                        if "?" in artwork["image_url"]:
                            path_part = artwork["image_url"].split("?")[0]
                            ext = Path(path_part).suffix or ".jpg"
                        filename = f"civitai_{artwork.get('source_id', 'unknown')}{ext}"
                        print(f"  🌐 从 URL 下载图片: {filename}")
                    except Exception as e:
                        result["error"] = f"Image download failed: {str(e)}"
                
                # 上传图片
                if image_data and filename:
                    try:
                        image_data_result = await self.upload_image(
                            image_data=image_data,
                            filename=filename,
                            prompt_id=result["prompt_id"],
                            analyze=False,
                        )
                        result["image_uploaded"] = True
                        result["image_id"] = image_data_result.get("id")
                    except Exception as e:
                        result["error"] = f"Image upload failed: {str(e)}"
        
        except Exception as e:
            result["error"] = str(e)
        
        return result

    async def import_from_json(
        self,
        json_path: str,
        download_images: bool = True,
        limit: Optional[int] = None,
    ):
        """从 JSON 文件导入数据
        
        Args:
            json_path: JSON 文件路径
            download_images: 是否下载图片
            limit: 限制导入数量
        """
        print(f"读取文件: {json_path}")
        
        with open(json_path, "r", encoding="utf-8") as f:
            artworks = json.load(f)
        
        if limit:
            artworks = artworks[:limit]
        
        print(f"准备导入 {len(artworks)} 条数据...")
        
        # 检查 API 连接
        if not await self.health_check():
            print("❌ 无法连接到 aicreatorvault API")
            return
        
        print("✅ API 连接正常")
        
        imported = 0
        failed = 0
        results = []
        
        for i, artwork in enumerate(artworks):
            print(f"\n[{i+1}/{len(artworks)}] 处理: {artwork.get('source_id', 'unknown')}")
            
            result = await self.import_artwork(
                artwork=artwork,
                download_images=download_images,
            )
            results.append(result)
            
            if result.get("prompt_created"):
                imported += 1
                print(f"  ✅ 提示词: {artwork.get('prompt', '')[:50]}...")
                if result.get("image_uploaded"):
                    print(f"  ✅ 图片已上传")
            else:
                failed += 1
                print(f"  ❌ 失败: {result.get('error')}")
        
        print(f"\n{'='*50}")
        print(f"导入完成!")
        print(f"  ✅ 成功: {imported}")
        print(f"  ❌ 失败: {failed}")
        
        return results


async def main():
    parser = argparse.ArgumentParser(description="导入数据到 aicreatorvault")
    parser.add_argument("json_file", help="爬取的 JSON 数据文件")
    parser.add_argument("--url", default="http://localhost:3001", help="aicreatorvault API 地址")
    parser.add_argument("--proxy", help="代理服务器")
    parser.add_argument("--no-download", action="store_true", help="不上传图片")
    parser.add_argument("--limit", type=int, help="限制导入数量")
    
    args = parser.parse_args()
    
    importer = AICreatorVaultImporter(
        base_url=args.url,
        proxy=args.proxy,
    )
    
    try:
        await importer.import_from_json(
            json_path=args.json_file,
            download_images=not args.no_download,
            limit=args.limit,
        )
    finally:
        await importer.close()


if __name__ == "__main__":
    asyncio.run(main())
