"""
OneShot - 多源检索服务
"""

import asyncio
import logging
from typing import Optional

from ..models import Paper, SearchResult

logger = logging.getLogger(__name__)


class SearchService:
    """多源检索服务"""
    
    def __init__(self):
        """初始化检索服务"""
        self.searchers = []
    
    def add_searcher(self, searcher):
        """添加搜索器"""
        self.searchers.append(searcher)
    
    async def search(self, paper: Paper) -> list[SearchResult]:
        """
        并行搜索多个数据源
        
        Args:
            paper: 搜索目标文献
            
        Returns:
            搜索结果列表
        """
        if not self.searchers:
            logger.warning("没有配置任何搜索器")
            return []
        
        # 创建搜索任务
        tasks = []
        for searcher in self.searchers:
            if hasattr(searcher, 'search'):
                tasks.append(self._search_with_source(searcher, paper))
        
        if not tasks:
            return []
        
        # 并行执行所有搜索
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 过滤无效结果
        valid_results = []
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"搜索异常: {result}")
            elif result:
                valid_results.append(result)
        
        # 按分数排序
        valid_results.sort(key=lambda x: x.score, reverse=True)
        
        return valid_results
    
    async def _search_with_source(self, searcher, paper: Paper) -> Optional[SearchResult]:
        """使用指定搜索器搜索"""
        try:
            result = await searcher.search(paper)
            if result:
                result.source = getattr(searcher, 'name', 'Unknown')
                return result
        except Exception as e:
            logger.error(f"搜索器 {getattr(searcher, 'name', 'Unknown')} 错误: {e}")
        return None


class BaseSearcher:
    """搜索器基类"""
    
    name: str = "Base"
    
    async def search(self, paper: Paper) -> Optional[SearchResult]:
        """执行搜索"""
        raise NotImplementedError


class CrossRefSearcher(BaseSearcher):
    """CrossRef搜索器"""
    
    name = "CrossRef"
    
    def __init__(self, timeout: int = 10):
        self.timeout = timeout
        self.base_url = "https://api.crossref.org"
    
    async def search(self, paper: Paper) -> Optional[SearchResult]:
        """搜索CrossRef"""
        import httpx
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                # 根据DOI或标题搜索
                if paper.doi:
                    url = f"{self.base_url}/works/{paper.doi}"
                else:
                    url = f"{self.base_url}/works"
                    params = {"query.title": paper.title, "rows": 1}
                
                response = await client.get(url, params=params if not paper.doi else None)
                
                if response.status_code == 200:
                    data = response.json()
                    items = data.get("message", {}).get("items", [])
                    
                    if items:
                        item = items[0]
                        paper.doi = item.get("DOI")
                        paper.title = item.get("title", [""])[0] if item.get("title") else paper.title
                        paper.authors = [
                            f"{a.get('given', '')} {a.get('family', '')}".strip()
                            for a in item.get("author", [])
                        ]
                        paper.year = int(item.get("published-print", {}).get("date-parts", [[None]])[0][0] or
                                       item.get("published-online", {}).get("date-parts", [[None]])[0][0])
                        paper.journal = item.get("container-title", [None])[0] if item.get("container-title") else None
                        paper.volume = item.get("volume", [None])[0] if item.get("volume") else None
                        paper.pages = item.get("page", None)
                        paper.publisher = item.get("publisher", None)
                        paper.abstract = item.get("abstract", None)
                        paper.citations = item.get("is-referenced-by-count", 0)
                        
                        return SearchResult(
                            paper=paper,
                            source=self.name,
                            score=1.0,
                            available=True
                        )
        except Exception as e:
            logger.error(f"CrossRef搜索失败: {e}")
        
        return None


class SemanticScholarSearcher(BaseSearcher):
    """Semantic Scholar搜索器"""
    
    name = "SemanticScholar"
    
    def __init__(self, timeout: int = 10):
        self.timeout = timeout
        self.base_url = "https://api.semanticscholar.org/graph/v1"
    
    async def search(self, paper: Paper) -> Optional[SearchResult]:
        """搜索Semantic Scholar"""
        import httpx
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                if paper.doi:
                    url = f"{self.base_url}/paper/DOI:{paper.doi}"
                    params = {"fields": "title,authors,year,journal,citations,externalIds"}
                else:
                    url = f"{self.base_url}/paper/search"
                    params = {
                        "query": paper.title,
                        "fields": "title,authors,year,journal,citations,externalIds",
                        "limit": 1
                    }
                
                response = await client.get(url, params=params)
                
                if response.status_code == 200:
                    data = response.json()
                    
                    if paper.doi:
                        # DOI查询直接返回
                        if data.get("title"):
                            paper.title = data["title"]
                            paper.year = data.get("year")
                            paper.journal = data.get("journal")
                            paper.citations = data.get("citations", 0)
                            if data.get("authors"):
                                paper.authors = [a["name"] for a in data["authors"]]
                            if data.get("externalIds"):
                                paper.doi = data["externalIds"].get("DOI", paper.doi)
                    else:
                        papers = data.get("data", [])
                        if papers:
                            item = papers[0]
                            paper.title = item.get("title", paper.title)
                            paper.year = item.get("year")
                            paper.journal = item.get("journal")
                            paper.citations = item.get("citations", 0)
                            if item.get("authors"):
                                paper.authors = [a["name"] for a in item["authors"]]
                    
                    return SearchResult(
                        paper=paper,
                        source=self.name,
                        score=0.9,
                        available=True
                    )
        except Exception as e:
            logger.error(f"Semantic Scholar搜索失败: {e}")
        
        return None
