"""
OneShot - 文献数据模型
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from pathlib import Path


@dataclass
class Paper:
    """文献数据模型"""
    
    # 基本信息
    title: str
    authors: list[str] = field(default_factory=list)
    year: Optional[int] = None
    doi: Optional[str] = None
    
    # 来源信息
    journal: Optional[str] = None
    volume: Optional[str] = None
    pages: Optional[str] = None
    publisher: Optional[str] = None
    
    # 文件信息
    file_path: Optional[Path] = None
    file_hash: Optional[str] = None
    
    # 元数据
    abstract: Optional[str] = None
    keywords: list[str] = field(default_factory=list)
    citations: int = 0  # 被引用次数
    
    # 原始数据
    raw_citation: Optional[str] = None  # 原始引用字符串
    
    # 数据库字段
    id: Optional[int] = None
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    downloaded: bool = False
    file_size: Optional[int] = None  # 文件大小（字节）
    
    def __post_init__(self):
        """确保路径是Path对象"""
        if self.file_path and not isinstance(self.file_path, Path):
            self.file_path = Path(self.file_path)
    
    @property
    def display_authors(self) -> str:
        """格式化作者列表显示"""
        if not self.authors:
            return "未知作者"
        if len(self.authors) <= 3:
            return ", ".join(self.authors)
        return f"{self.authors[0]} 等 ({len(self.authors)}人)"
    
    @property
    def citation_string(self) -> str:
        """生成引用字符串"""
        parts = [self.display_authors]
        if self.year:
            parts.append(f"({self.year})")
        parts.append(self.title)
        if self.journal:
            parts.append(self.journal)
            if self.volume:
                parts[-1] += f", {self.volume}"
            if self.pages:
                parts[-1] += f", {self.pages}"
        return ". ".join(parts)
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "id": self.id,
            "title": self.title,
            "authors": self.authors,
            "year": self.year,
            "doi": self.doi,
            "journal": self.journal,
            "volume": self.volume,
            "pages": self.pages,
            "publisher": self.publisher,
            "file_path": str(self.file_path) if self.file_path else None,
            "abstract": self.abstract,
            "keywords": self.keywords,
            "citations": self.citations,
            "raw_citation": self.raw_citation,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "downloaded": self.downloaded,
            "file_size": self.file_size,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "Paper":
        """从字典创建"""
        # 处理日期字段
        if isinstance(data.get("created_at"), str):
            data["created_at"] = datetime.fromisoformat(data["created_at"])
        if isinstance(data.get("updated_at"), str):
            data["updated_at"] = datetime.fromisoformat(data["updated_at"])
        
        # 处理路径
        if data.get("file_path"):
            data["file_path"] = Path(data["file_path"])
        
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class SearchResult:
    """搜索结果"""
    paper: Paper
    source: str  # 来源：CrossRef, SemanticScholar, GoogleScholar等
    score: float = 1.0  # 匹配分数
    download_url: Optional[str] = None
    available: bool = True
    error: Optional[str] = None


@dataclass 
class DownloadTask:
    """下载任务"""
    paper: Paper
    url: str
    source: str
    status: str = "pending"  # pending, downloading, completed, failed
    progress: float = 0.0
    error: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
