"""
OneShot - SemanticScholar 搜索器
基于 SemanticScholar Graph API 实现文献搜索

文档: https://semanticscholar.org
API: https://api.semanticscholar.org/api-docs/graph
"""

import logging
from typing import Optional

from semanticscholar import AsyncSemanticScholar

from ..models import Paper, SearchResult

logger = logging.getLogger(__name__)

# API 返回的字段列表
PAPER_FIELDS = [
    'title', 'authors', 'year', 'abstract', 'tldr', 
    'citationCount', 'externalIds', 'url', 'venue',
    'openAccessPdf', 'fieldsOfStudy'
]


class SemanticScholarSearcher:
    """SemanticScholar 搜索器"""
    
    def __init__(self):
        self.name = "SemanticScholar"
        self._client = AsyncSemanticScholar()
    
    async def search(self, paper: Paper) -> Optional[SearchResult]:
        """搜索论文"""
        try:
            # 优先使用 DOI 搜索
            if paper.doi:
                paper_data = await self._search_by_doi(paper.doi)
                if paper_data:
                    return self._paper_to_search_result(paper_data, "doi")
            
            # 使用标题搜索
            if paper.title:
                paper_data = await self._search_by_title(paper)
                if paper_data:
                    return self._paper_to_search_result(paper_data, "title")
            
            logger.warning(f"SemanticScholar 未找到: {paper.title[:50] if paper.title else '未知'}")
            
        except Exception as e:
            logger.error(f"SemanticScholar 搜索异常: {e}")
        
        return None
    
    async def _search_by_doi(self, doi: str) -> Optional[object]:
        """通过 DOI 搜索"""
        try:
            result = await self._client.search_paper(
                f"DOI:{doi}",
                match_title=False,
                fields=PAPER_FIELDS
            )
            return result if result else None
        except Exception as e:
            logger.debug(f"DOI 搜索失败: {e}")
            return None
    
    async def _search_by_title(self, paper: Paper) -> Optional[object]:
        """通过标题搜索"""
        try:
            result = await self._client.search_paper(
                paper.title,
                match_title=True,
                fields=PAPER_FIELDS
            )
            return result if result else None
        except Exception as e:
            logger.debug(f"标题搜索失败: {e}")
            return None
    
    def _paper_to_search_result(self, paper_data, match_type: str) -> SearchResult:
        """将 API 返回的论文数据转换为 SearchResult"""
        title = getattr(paper_data, 'title', '') or '未知标题'
        year = getattr(paper_data, 'year', None)
        abstract = getattr(paper_data, 'abstract', '') or ''
        tldr = ''
        if hasattr(paper_data, 'tldr') and hasattr(paper_data.tldr, 'text'):
            tldr = paper_data.tldr.text
        
        citation_count = getattr(paper_data, 'citationCount', 0) or 0
        
        # 提取作者
        authors_data = getattr(paper_data, 'authors', []) or []
        authors = []
        for a in authors_data:
            name = getattr(a, 'name', '') if hasattr(a, 'name') else str(a) if a else ''
            if name:
                authors.append(name)
        
        # 提取 DOI
        external_ids = getattr(paper_data, 'externalIds', None) or {}
        doi = external_ids.get('DOI', '') if isinstance(external_ids, dict) else ''
        
        # 提取 URL
        url = getattr(paper_data, 'url', '') or ''
        if not url and doi:
            url = f"https://doi.org/{doi}"
        
        # 创建 Paper 对象
        result_paper = Paper(
            title=title,
            authors=authors,
            year=year,
            doi=doi,
            abstract=abstract,
            url=url,
            citation_count=citation_count,
            ccf_rank='',
            tldr=tldr
        )
        
        # 提取下载 URL
        open_access_pdf = getattr(paper_data, 'openAccessPdf', None)
        download_url = None
        if open_access_pdf and isinstance(open_access_pdf, dict):
            download_url = open_access_pdf.get('url')
        elif hasattr(open_access_pdf, 'url'):
            download_url = open_access_pdf.url
        
        return SearchResult(
            paper=result_paper,
            source=self.name,
            download_url=download_url,
            available=bool(download_url or url)
        )