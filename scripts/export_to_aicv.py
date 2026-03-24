#!/usr/bin/env python3
"""
将爬取的数据导入到 aicreatorvault（支持知识图谱）
"""
import argparse
import asyncio
import json
from pathlib import Path
from typing import Optional
from datetime import datetime

import httpx


class AICreatorVaultImporter:
    """导入数据到 aicreatorvault（支持知识图谱）"""

    def __init__(
        self,
        base_url: str = "http://localhost:3001",
        api_prefix: str = "/api",
        proxy: Optional[str] = None,
        use_knowledge_graph: bool = True,
    ):
        self.base_url = base_url.rstrip("/")
        self.api_url = f"{self.base_url}{api_prefix}"
        self.use_knowledge_graph = use_knowledge_graph
        # 不设置默认代理，由调用者决定
        self.client = httpx.AsyncClient(timeout=60.0, proxy=proxy, follow_redirects=True)
        # 使用本地缓存避免重复查询（比全量加载高效得多）
        self._local_cache = {}  # 格式: {(assetType, content): asset_id}

    async def close(self):
        await self.client.aclose()

    async def health_check(self) -> bool:
        """检查 API 是否可用"""
        try:
            if self.use_knowledge_graph:
                response = await self.client.get(f"{self.api_url}/assets", params={'limit': 1})
            else:
                response = await self.client.get(f"{self.api_url}/prompts")
            return response.status_code == 200
        except:
            return False

    async def _check_asset_exists(self, asset_type: str, content: str) -> Optional[dict]:
        """高效检查资产是否存在（使用 /api/assets/find）

        Returns:
            资产数据如果存在，否则 None
        """
        # 先检查本地缓存
        cache_key = (asset_type, content)
        if cache_key in self._local_cache:
            return {'id': self._local_cache[cache_key]}

        # 使用后端的精确查询 API
        try:
            response = await self.client.get(
                f"{self.api_url}/assets/find",
                params={'assetType': asset_type, 'content': content}
            )
            if response.status_code == 200:
                asset = response.json()
                # 缓存结果
                self._local_cache[cache_key] = asset.get('id')
                return asset
            elif response.status_code == 404:
                # 不存在，缓存这个信息避免重复查询
                self._local_cache[cache_key] = None
                return None
        except Exception as e:
            print(f"  ⚠️ 检查资产失败: {e}")
        return None

    async def _check_prompt_exists(self, content: str) -> Optional[dict]:
        """检查提示词是否存在（使用数据库查询）

        Returns:
            提示词数据如果存在，否则 None
        """
        # 先检查本地缓存
        cache_key = ('prompt', content)
        if cache_key in self._local_cache:
            return {'id': self._local_cache[cache_key]} if self._local_cache[cache_key] else None

        # 使用数据库级别的查询 API
        try:
            response = await self.client.get(
                f"{self.api_url}/prompts/find",
                params={'content': content}
            )
            if response.status_code == 200:
                prompt = response.json()
                # 缓存结果
                self._local_cache[cache_key] = prompt.get('id')
                return prompt
            elif response.status_code == 404:
                # 不存在，缓存这个信息避免重复查询
                self._local_cache[cache_key] = None
                return None
        except Exception as e:
            print(f"  ⚠️ 检查提示词失败: {e}")
        return None

    async def create_prompt_asset(
        self,
        content: str,
        score: int = 0,
        check_duplicate: bool = True,
    ) -> dict:
        """创建提示词资产（知识图谱模式）- 优化版本

        Args:
            content: 提示词内容
            score: 评分 (0-10)
            check_duplicate: 是否检查重复
        """
        # 高效检查是否已存在
        if check_duplicate:
            existing = await self._check_asset_exists('prompt', content)
            if existing:
                print(f"  ℹ️  提示词资产已存在 (ID: {existing['id']})，跳过创建")
                return {'id': existing['id'], 'assetType': 'prompt', **existing}

        # 创建新资产
        try:
            response = await self.client.post(
                f"{self.api_url}/assets",
                json={
                    "assetType": "prompt",
                    "content": content,
                    "score": min(max(score, 0), 10),
                }
            )
            response.raise_for_status()
            result = response.json()

            # 缓存新创建的资产
            self._local_cache[('prompt', content)] = result.get('id')
            return result
        except Exception as e:
            # 处理唯一约束冲突（后端可能在我们检查后、创建前被其他请求创建了）
            if '409' in str(e) or 'already exists' in str(e).lower():
                # 再查一次
                existing = await self._check_asset_exists('prompt', content)
                if existing:
                    print(f"  ℹ️  提示词资产已存在 (并发创建, ID: {existing['id']})")
                    return {'id': existing['id'], 'assetType': 'prompt', **existing}
            raise

    async def create_prompt(
        self,
        content: str,
        score: int = 0,
        check_duplicate: bool = True,
    ) -> dict:
        """创建提示词（旧 API 模式，兼容性保留）

        Args:
            content: 提示词内容
            score: 评分 (0-5)
            check_duplicate: 是否检查重复
        """
        # 高效检查是否已存在
        if check_duplicate:
            existing = await self._check_prompt_exists(content)
            if existing:
                print(f"  ℹ️  提示词已存在 (ID: {existing['id']})，跳过创建")
                return existing

        # 创建新提示词
        response = await self.client.post(
            f"{self.api_url}/prompts",
            json={
                "content": content,
                "score": min(max(score, 0), 5),
            }
        )
        response.raise_for_status()
        result = response.json()

        # 缓存新创建的提示词
        self._local_cache[('prompt', content)] = result.get('id')
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
            prompt_id: 关联的提示词 ID（资产 ID 或提示词 ID）
            analyze: 是否自动分析图片
        """
        files = {"image": (filename, image_data, "image/jpeg")}
        data = {}

        if self.use_knowledge_graph:
            # 知识图谱模式：使用 /api/assets/upload
            if prompt_id:
                data["prompt_id"] = str(prompt_id)
            data["score"] = 0  # 可以根据需要调整

            response = await self.client.post(
                f"{self.api_url}/assets/upload",
                files=files,
                data=data,
            )
            response.raise_for_status()
            return response.json()
        else:
            # 旧模式：使用 /api/images
            if prompt_id:
                data["prompt_id"] = str(prompt_id)

            # 关闭自动分析（导入时批量分析更高效）
            data["autoAnalyze"] = analyze

            response = await self.client.post(
                f"{self.api_url}/images",
                files=files,
                data=data,
            )
            response.raise_for_status()
            return response.json()

    async def create_relationship(
        self,
        source_id: int,
        target_id: int,
        relationship_type: str = "generated",
        properties: Optional[dict] = None,
    ) -> dict:
        """创建资产关系（知识图谱模式）

        Args:
            source_id: 源资产 ID
            target_id: 目标资产 ID
            relationship_type: 关系类型 (generated, derived_from, version_of, inspired_by)
            properties: 关系属性
        """
        response = await self.client.post(
            f"{self.api_url}/relationships",
            json={
                "source_id": source_id,
                "target_id": target_id,
                "relationship_type": relationship_type,
                "properties": properties or {},
            }
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
            "relationship_created": False,
            "prompt_id": None,
            "image_id": None,
            "error": None,
        }

        try:
            # 1. 创建提示词（或提示词资产）
            prompt_content = artwork.get("prompt", "")
            if not prompt_content:
                result["error"] = "No prompt content"
                return result

            # 计算评分（基于点赞数）
            likes = artwork.get("likes", 0)
            score = min(likes // 10, 10 if self.use_knowledge_graph else 5)  # KG: 0-10, 旧API: 0-5

            if self.use_knowledge_graph:
                # 知识图谱模式：创建 Prompt 资产
                prompt_data = await self.create_prompt_asset(
                    content=prompt_content,
                    score=score,
                )
                result["prompt_created"] = True
                result["prompt_id"] = prompt_data.get("id")
            else:
                # 旧模式：创建提示词
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

                        # 知识图谱模式：如果没有通过 promptId 自动创建关系，手动创建
                        if self.use_knowledge_graph and result["prompt_id"] and result["image_id"]:
                            try:
                                await self.create_relationship(
                                    source_id=result["prompt_id"],
                                    target_id=result["image_id"],
                                    relationship_type="generated",
                                    properties={
                                        "source": artwork.get("source"),
                                        "source_id": artwork.get("source_id"),
                                        "imported_at": datetime.now().isoformat(),
                                    }
                                )
                                result["relationship_created"] = True
                            except Exception as e:
                                print(f"  ⚠️ 创建关系失败: {e}")
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
                    print(f"  ✅ 图片已上传 (ID: {result.get('image_id')})")
                    if self.use_knowledge_graph and result.get("relationship_created"):
                        print(f"  ✅ 知识图谱关系已创建")
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
        if self.use_knowledge_graph:
            print(f"  📊 知识图谱: 已启用")

        return results


async def main():
    parser = argparse.ArgumentParser(description="导入数据到 aicreatorvault")
    parser.add_argument("json_files", nargs="+", help="爬取的 JSON 数据文件（支持多个文件或通配符）")
    parser.add_argument("--url", default="http://localhost:3001", help="aicreatorvault API 地址")
    parser.add_argument("--proxy", help="代理服务器")
    parser.add_argument("--no-proxy", action="store_true", help="不使用代理")
    parser.add_argument("--no-download", action="store_true", help="不上传图片")
    parser.add_argument("--limit", type=int, help="限制导入数量")
    parser.add_argument("--no-kg", action="store_true", help="禁用知识图谱模式（使用旧 API）")

    args = parser.parse_args()

    importer = AICreatorVaultImporter(
        base_url=args.url,
        proxy=None if args.no_proxy else args.proxy,
        use_knowledge_graph=not args.no_kg,  # 默认启用知识图谱
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
