"""
OneShot - 文献数据模型
"""

from dataclasses import dataclass, field, fields
from datetime import datetime
from typing import Optional, get_type_hints
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
    issue: Optional[str] = None
    pages: Optional[str] = None
    publisher: Optional[str] = None
    url: Optional[str] = None
    type_: Optional[str] = None  # 文献类型：article, book, inproceedings 等
    
    # 文件信息
    file_path: Optional[Path] = None
    file_hash: Optional[str] = None
    
    # 元数据
    abstract: Optional[str] = None
    tldr: Optional[str] = None  # 论文摘要的简短版本
    keywords: list[str] = field(default_factory=list)
    citation_count: Optional[int] = None  # 被引用次数
    ccf_rank: Optional[str] = None  # CCF 等级：A/B/C/none
    
    # 原始数据
    raw_citation: Optional[str] = None  # 原始引用字符串
    citation_index: Optional[str] = None  # 引用索引（例如 [1] [Tho00a] 方括号里的内容, 不一定为数字）
    
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
    
    @staticmethod
    def _is_empty(val, field_type) -> bool:
        """判断字段是否为空"""
        # int 类型默认值为 0
        if field_type == int:
            return val == 0
        # list 类型默认值为 []
        if field_type == list:
            return not val
        # 其他类型（str, datetime, Path 等）默认值为 None/空
        return not val
    
    def merge(self, other: "Paper"):
        """
        从另一个 Paper 对象合并信息（保留已有值，只填充空值）
        """
        if not other:
            return
        
        # 获取类型注解
        hints = get_type_hints(Paper)
        
        for f in fields(self):
            if f.name == 'title':  # title 是必填字段，跳过
                continue
            
            self_val = getattr(self, f.name)
            other_val = getattr(other, f.name)
            
            field_type = hints.get(f.name)
            if self._is_empty(self_val, field_type) and not self._is_empty(other_val, field_type):
                setattr(self, f.name, other_val)
    
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
        result = {}
        for f in fields(self):
            val = getattr(self, f.name)
            # 特殊处理
            if f.name == 'file_path':
                result[f.name] = str(val) if val else None
            elif f.name in ('created_at', 'updated_at') and val:
                result[f.name] = val.isoformat()
            elif val is not None:
                # ignore None values
                result[f.name] = val
        return result
    
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