"""
爬虫配置
"""
from pathlib import Path
from typing import Optional

from pydantic import BaseModel
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """应用配置"""
    
    # 输出目录
    output_dir: Path = Path("data/crawled")
    
    # 代理设置
    http_proxy: Optional[str] = None
    https_proxy: Optional[str] = None
    
    # 爬虫设置
    rate_limit: float = 1.0  # 每秒请求数
    max_retries: int = 3
    timeout: int = 30
    
    # 图片设置
    download_images: bool = True
    image_quality: int = 95
    max_image_size_mb: int = 10
    
    # 数据库设置（可选）
    database_url: Optional[str] = None
    
    # aicreatorvault 集成
    aicv_api_url: str = "http://localhost:3001/api"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


# 全局配置实例
settings = Settings()
