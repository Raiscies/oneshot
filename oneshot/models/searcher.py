from . import Paper, SearchResult
from typing import Optional

from dataclasses import dataclass, field

@dataclass
class Searcher:
    """搜索器基类"""
    
    name: str = field(default_factory=lambda: "BaseSearcher")
    
    async def search(self, paper: Paper) -> Optional[SearchResult]:
        """执行搜索"""
        raise NotImplementedError
