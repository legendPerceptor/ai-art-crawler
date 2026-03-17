"""
数据库模型和操作
"""
from datetime import datetime
from typing import Optional
from sqlalchemy import create_engine, Column, String, Integer, Text, DateTime, JSON, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

Base = declarative_base()


class ArtworkDB(Base):
    """爬取的艺术作品数据库模型"""
    __tablename__ = "crawled_artworks"

    id = Column(String(32), primary_key=True)
    source = Column(String(50), nullable=False, index=True)
    source_id = Column(String(100))
    source_url = Column(Text)
    prompt = Column(Text)
    negative_prompt = Column(Text)
    model = Column(String(100))
    style = Column(String(100))
    width = Column(Integer, default=0)
    height = Column(Integer, default=0)
    image_url = Column(Text)
    local_path = Column(Text)
    seed = Column(Integer, nullable=True)
    author = Column(String(100))
    likes = Column(Integer, default=0)
    tags = Column(JSON, default=list)
    created_at = Column(DateTime, nullable=True)
    crawled_at = Column(DateTime, default=datetime.now)
    raw_data = Column(JSON, default=dict)

    __table_args__ = (
        Index('idx_source_source_id', 'source', 'source_id'),
        Index('idx_crawled_at', 'crawled_at'),
    )


class Database:
    """数据库操作类"""
    
    def __init__(self, database_url: str):
        self.engine = create_engine(database_url, echo=False)
        self.Session = sessionmaker(bind=self.engine)
        self.create_tables()
    
    def create_tables(self):
        """创建表"""
        Base.metadata.create_all(self.engine)
    
    def save_artwork(self, artwork_data: dict) -> ArtworkDB:
        """保存单个作品"""
        session = self.Session()
        try:
            artwork = ArtworkDB(**artwork_data)
            session.merge(artwork)  # 使用 merge 避免重复
            session.commit()
            return artwork
        finally:
            session.close()
    
    def save_artworks_batch(self, artworks: list[dict]) -> int:
        """批量保存作品"""
        session = self.Session()
        count = 0
        try:
            for data in artworks:
                artwork = ArtworkDB(**data)
                session.merge(artwork)
                count += 1
            session.commit()
            return count
        finally:
            session.close()
    
    def get_stats(self) -> dict:
        """获取统计信息"""
        session = self.Session()
        try:
            total = session.query(ArtworkDB).count()
            return {"total": total}
        finally:
            session.close()
