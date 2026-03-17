#!/usr/bin/env python3
"""
将爬取的数据导入到 aicreatorvault
"""
import argparse
import asyncio
import json
from pathlib import Path
from typing import Optional

import httpx


class AICreatorVaultExporter:
    """导出数据到 aicreatorvault"""

    def __init__(
        self,
        base_url: str = "http://localhost:3001",
        api_prefix: str = "/api",
    ):
        self.base_url = base_url.rstrip("/")
        self.api_url = f"{self.base_url}{api_prefix}"
        self.client = httpx.AsyncClient(timeout=30.0)

    async def close(self):
        await self.client.aclose()

    async def create_prompt(
        self,
        content: str,
        score: int = 0,
    ) -> dict:
        """创建提示词"""
        response = await self.client.post(
            f"{self.api_url}/prompts",
            json={
                "content": content,
                "score": score,
            }
        )
        response.raise_for_status()
        return response.json()

    async def upload_image(
        self,
        image_path: str,
        prompt_id: Optional[int] = None,
        analyze: bool = True,
    ) -> dict:
        """上传图片"""
        with open(image_path, "rb") as f:
            files = {"image": (Path(image_path).name, f, "image/jpeg")}
            data = {}
            
            if prompt_id:
                data["promptId"] = prompt_id
            if analyze:
                data["analyze"] = "true"

            response = await self.client.post(
                f"{self.api_url}/images",
                files=files,
                data=data,
            )
            response.raise_for_status()
            return response.json()

    async def import_from_json(
        self,
        json_path: str,
        upload_images: bool = True,
        analyze_images: bool = True,
    ):
        """从 JSON 文件导入数据"""
        with open(json_path, "r", encoding="utf-8") as f:
            artworks = json.load(f)

        print(f"开始导入 {len(artworks)} 条数据...")

        imported = 0
        skipped = 0

        for i, artwork in enumerate(artworks):
            try:
                # 创建提示词
                prompt_data = None
                if artwork.get("prompt"):
                    prompt_data = await self.create_prompt(
                        content=artwork["prompt"],
                        score=min(artwork.get("likes", 0) // 10, 5),  # 将点赞数转为评分
                    )
                    print(f"  [{i+1}/{len(artworks)}] 创建提示词: {artwork['prompt'][:50]}...")

                # 上传图片
                if upload_images and artwork.get("local_path"):
                    image_data = await self.upload_image(
                        image_path=artwork["local_path"],
                        prompt_id=prompt_data["id"] if prompt_data else None,
                        analyze=analyze_images,
                    )
                    print(f"  [{i+1}/{len(artworks)}] 上传图片: {artwork['local_path']}")
                
                imported += 1

            except Exception as e:
                print(f"  [{i+1}/{len(artworks)}] 导入失败: {e}")
                skipped += 1

        print(f"\n导入完成!")
        print(f"  成功: {imported}")
        print(f"  失败: {skipped}")


async def main():
    parser = argparse.ArgumentParser(description="导出数据到 aicreatorvault")
    parser.add_argument("json_file", help="爬取的 JSON 数据文件")
    parser.add_argument(
        "--url",
        default="http://localhost:3001",
        help="aicreatorvault API 地址"
    )
    parser.add_argument(
        "--no-upload",
        action="store_true",
        help="不上传图片"
    )
    parser.add_argument(
        "--no-analyze",
        action="store_true",
        help="不分析图片"
    )

    args = parser.parse_args()

    exporter = AICreatorVaultExporter(base_url=args.url)
    try:
        await exporter.import_from_json(
            json_path=args.json_file,
            upload_images=not args.no_upload,
            analyze_images=not args.no_analyze,
        )
    finally:
        await exporter.close()


if __name__ == "__main__":
    asyncio.run(main())
