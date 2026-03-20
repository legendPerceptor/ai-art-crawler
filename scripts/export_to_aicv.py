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
        # 不设置默认代理，由调用者决定
        self.client = httpx.AsyncClient(timeout=60.0, proxy=proxy, follow_redirects=True)
        self._existing_prompts_cache = None  # 缓存已存在的提示词

    async def close(self):
        await self.client.aclose()

    async def health_check(self) -> bool:
        """检查 API 是否可用"""
        try:
            response = await self.client.get(f"{self.api_url}/prompts")
            return response.status_code == 200
        except:
            return False

    async def _get_existing_prompts(self) -> dict:
        """获取所有已存在的提示词，缓存以提高性能"""
        if self._existing_prompts_cache is None:
            try:
                response = await self.client.get(f"{self.api_url}/prompts")
                if response.status_code == 200:
                    existing = response.json()
                    # 使用 content 作为 key 建立索引
                    self._existing_prompts_cache = {
                        p.get('content'): p for p in existing
                    }
                    print(f"  ℹ️  已加载 {len(self._existing_prompts_cache)} 个现有提示词")
                else:
                    self._existing_prompts_cache = {}
            except Exception as e:
                print(f"  ⚠️ 获取现有提示词失败: {e}")
                self._existing_prompts_cache = {}
        return self._existing_prompts_cache

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
        # 检查是否已存在相同内容的提示词（使用缓存）
        if check_duplicate:
            existing_prompts = await self._get_existing_prompts()
            if content in existing_prompts:
                p = existing_prompts[content]
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
        result = response.json()
        # 更新缓存
        if check_duplicate and self._existing_prompts_cache is not None:
            self._existing_prompts_cache[content] = result
        return result

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
        analyze: bool = False,
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
        data["autoAnalyze"] = analyze

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
        json_paths: list[str],
        download_images: bool = True,
        limit: Optional[int] = None,
    ):
        """从 JSON 文件导入数据（支持多个文件）

        Args:
            json_paths: JSON 文件路径列表
            download_images: 是否下载图片
            limit: 限制导入数量
        """
        # 1. 加载所有文件并去重
        all_artworks = []
        seen_ids = set()  # 使用 (source, source_id) 作为唯一标识

        for json_path in json_paths:
            print(f"读取文件: {json_path}")
            try:
                with open(json_path, "r", encoding="utf-8") as f:
                    artworks = json.load(f)

                # 去重：跳过已见过的 artwork
                new_count = 0
                for artwork in artworks:
                    unique_key = (artwork.get("source"), artwork.get("source_id"))
                    if unique_key not in seen_ids:
                        seen_ids.add(unique_key)
                        all_artworks.append(artwork)
                        new_count += 1

                print(f"  → 加载 {len(artworks)} 条，新增 {new_count} 条（去重后）")
            except FileNotFoundError:
                print(f"  ⚠️  文件不存在: {json_path}")
            except Exception as e:
                print(f"  ❌ 读取文件失败: {e}")

        if not all_artworks:
            print("❌ 没有可导入的数据")
            return

        if limit:
            all_artworks = all_artworks[:limit]

        print(f"\n{'='*50}")
        print(f"准备导入 {len(all_artworks)} 条数据（已去重）...")

        # 检查 API 连接
        if not await self.health_check():
            print("❌ 无法连接到 aicreatorvault API")
            return

        print("✅ API 连接正常")

        imported = 0
        failed = 0
        skipped = 0
        results = []

        for i, artwork in enumerate(all_artworks):
            print(f"\n[{i+1}/{len(all_artworks)}] 处理: {artwork.get('source_id', 'unknown')}")

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
            elif "已存在" in result.get("error", ""):
                skipped += 1
                print(f"  ⏭️  跳过: {result.get('error')}")
            else:
                failed += 1
                print(f"  ❌ 失败: {result.get('error')}")

        print(f"\n{'='*50}")
        print(f"导入完成!")
        print(f"  ✅ 成功: {imported}")
        print(f"  ⏭️  跳过: {skipped}")
        print(f"  ❌ 失败: {failed}")

        return results


async def main():
    parser = argparse.ArgumentParser(description="导入数据到 aicreatorvault")
    parser.add_argument("json_files", nargs="+", help="爬取的 JSON 数据文件（支持多个文件或通配符）")
    parser.add_argument("--url", default="http://localhost:3001", help="aicreatorvault API 地址")
    parser.add_argument("--proxy", help="代理服务器")
    parser.add_argument("--no-proxy", action="store_true", help="不使用代理")
    parser.add_argument("--no-download", action="store_true", help="不上传图片")
    parser.add_argument("--limit", type=int, help="限制导入数量")

    args = parser.parse_args()

    importer = AICreatorVaultImporter(
        base_url=args.url,
        proxy=None if args.no_proxy else args.proxy,
    )

    try:
        await importer.import_from_json(
            json_paths=args.json_files,
            download_images=not args.no_download,
            limit=args.limit,
        )
    finally:
        await importer.close()


if __name__ == "__main__":
    asyncio.run(main())
