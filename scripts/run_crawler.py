#!/usr/bin/env python3
"""
运行 AI Art 爬虫
"""
import argparse
import asyncio
from pathlib import Path

from crawler.civitai import CivitaiCrawler
# from crawler.lexica import LexicaCrawler  # 待实现
# from crawler.prompthero import PromptHeroCrawler  # 待实现


CRAWLERS = {
    "civitai": CivitaiCrawler,
    # "lexica": LexicaCrawler,
    # "prompthero": PromptHeroCrawler,
}


async def run_crawler(
    site: str,
    limit: int,
    output_dir: str,
    proxy: str = None,
    tag: str = None,
    download: bool = False,
):
    """运行爬虫"""
    crawler_cls = CRAWLERS.get(site)
    if not crawler_cls:
        print(f"未知的爬虫: {site}")
        print(f"可用的爬虫: {list(CRAWLERS.keys())}")
        return

    crawler = crawler_cls(
        output_dir=output_dir,
        proxy=proxy,
        rate_limit=1.0,
    )

    artworks = await crawler.run(
        limit=limit,
        tag=tag,
        download_images=download,
    )

    print(f"\n爬取完成!")
    print(f"  数量: {len(artworks)}")
    print(f"  输出目录: {output_dir}")
    
    # 打印统计
    if artworks:
        prompts = [a.prompt for a in artworks if a.prompt]
        print(f"  有提示词: {len(prompts)}/{len(artworks)}")
        
        with_prompt = len([a for a in artworks if a.prompt])
        with_image = len([a for a in artworks if a.image_url])
        print(f"  有提示词: {with_prompt}")
        print(f"  有图片: {with_image}")


def main():
    parser = argparse.ArgumentParser(description="AI Art 爬虫")
    parser.add_argument(
        "--site", "-s",
        choices=list(CRAWLERS.keys()),
        default="civitai",
        help="要爬取的网站"
    )
    parser.add_argument(
        "--limit", "-l",
        type=int,
        default=50,
        help="爬取数量 (默认 50)"
    )
    parser.add_argument(
        "--output", "-o",
        default="data/crawled",
        help="输出目录"
    )
    parser.add_argument(
        "--proxy", "-p",
        help="代理服务器 (如 http://127.0.0.1:7890)"
    )
    parser.add_argument(
        "--tag", "-t",
        help="按标签过滤"
    )
    parser.add_argument(
        "--download", "-d",
        action="store_true",
        help="下载图片到本地"
    )

    args = parser.parse_args()

    asyncio.run(run_crawler(
        site=args.site,
        limit=args.limit,
        output_dir=args.output,
        proxy=args.proxy,
        tag=args.tag,
        download=args.download,
    ))


if __name__ == "__main__":
    main()
