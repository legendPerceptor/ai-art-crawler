#!/usr/bin/env python3
"""
运行 AI Art 爬虫
"""
import argparse
import asyncio
import os
from datetime import datetime
from pathlib import Path

from crawler.civitai import CivitaiCrawler

CRAWLERS = {
    "civitai": CivitaiCrawler,
}


async def run_crawler(
    site: str,
    limit: int,
    output_dir: str,
    proxy: str = None,
    tag: str = None,
    download: bool = False,
    save_db: bool = False,
    database_url: str = None,
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
    
    # 保存到数据库
    if save_db and database_url:
        from storage.database import Database
        
        print("\n保存到数据库...")
        db = Database(database_url)
        
        data_list = []
        for a in artworks:
            data = a.model_dump()
            if isinstance(data.get('crawled_at'), datetime):
                data['crawled_at'] = data['crawled_at']
            if isinstance(data.get('created_at'), datetime):
                data['created_at'] = data['created_at']
            data_list.append(data)
        
        saved = db.save_artworks_batch(data_list)
        print(f"  已保存: {saved} 条")
    
    # 打印统计
    if artworks:
        with_prompt = len([a for a in artworks if a.prompt])
        with_image = len([a for a in artworks if a.image_url])
        print(f"\n统计:")
        print(f"  有提示词: {with_prompt}/{len(artworks)}")
        print(f"  有图片: {with_image}/{len(artworks)}")


def main():
    parser = argparse.ArgumentParser(description="AI Art 爬虫")
    parser.add_argument("--site", "-s", choices=list(CRAWLERS.keys()), default="civitai", help="要爬取的网站")
    parser.add_argument("--limit", "-l", type=int, default=50, help="爬取数量 (默认 50)")
    parser.add_argument("--output", "-o", default="data/crawled", help="输出目录")
    parser.add_argument("--proxy", "-p", help="代理服务器")
    parser.add_argument("--tag", "-t", help="按标签过滤")
    parser.add_argument("--download", "-d", action="store_true", help="下载图片")
    parser.add_argument("--save-db", action="store_true", help="保存到数据库")
    parser.add_argument("--database-url", default=os.environ.get("DATABASE_URL"), help="数据库连接 URL")

    args = parser.parse_args()

    asyncio.run(run_crawler(
        site=args.site,
        limit=args.limit,
        output_dir=args.output,
        proxy=args.proxy or os.environ.get("HTTPS_PROXY"),
        tag=args.tag,
        download=args.download,
        save_db=args.save_db,
        database_url=args.database_url,
    ))


if __name__ == "__main__":
    main()
