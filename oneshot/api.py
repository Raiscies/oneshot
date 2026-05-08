"""
OneShot - FastAPI API 服务

提供文献搜索相关的 API 端点
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import logging
import asyncio

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="OneShot API",
    description="文献搜索与管理 API",
    version="0.1.0",
)

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==================== 数据模型 ====================

class Paper(BaseModel):
    """论文数据模型"""
    title: str
    authors: List[str] = []
    year: Optional[int] = None
    abstract: Optional[str] = None
    ccf_rank: Optional[str] = None
    doi: Optional[str] = None
    url: Optional[str] = None
    citation_number: Optional[int] = None
    citations: Optional[int] = None


class SearchRequest(BaseModel):
    """搜索请求"""
    query: str
    captured_text: Optional[str] = ""


class SearchResponse(BaseModel):
    """搜索响应"""
    papers: List[Paper]
    captured_text: str = ""
    message: Optional[str] = None


# ==================== 全局状态 ====================

# 当前搜索结果（用于结果窗口获取）
_current_result: Optional[SearchResponse] = None

# 搜索服务实例
_search_service = None


# 暴露给 main.py 使用的更新函数
def update_search_result(papers: List[dict], captured_text: str, message: str, ready: bool = True):
    """更新搜索结果（供 main.py 调用）"""
    global _current_result
    _current_result = SearchResponse(
        papers=[Paper(**p) for p in papers],
        captured_text=captured_text,
        message=message,
    )
    return _current_result


def _get_search_service():
    """获取搜索服务（延迟初始化）"""
    global _search_service
    if _search_service is None:
        from oneshot.services import SearchService, CitationParser
        _search_service = SearchService()
    return _search_service


def _get_citation_parser():
    """获取引用解析器（延迟初始化）"""
    global _citation_parser
    if '_citation_parser' not in globals():
        from oneshot.services import CitationParser
        globals()['_citation_parser'] = CitationParser()
    return globals()['_citation_parser']


# ==================== API 端点 ====================

@app.get("/health")
async def health_check():
    """健康检查"""
    return {"status": "ok", "service": "oneshot-api"}


@app.post("/api/search", response_model=SearchResponse)
async def search_papers(request: SearchRequest):
    """
    搜索文献 API
    
    Args:
        request: SearchRequest，包含查询字符串和捕获的文本
    
    Returns:
        SearchResponse: 包含论文列表和捕获文本
    """
    global _current_result
    
    logger.info(f"搜索请求: query='{request.query}', captured='{request.captured_text[:50] if request.captured_text else ''}...'")
    
    try:
        # 使用真正的搜索服务
        papers = await _real_search(request.query)
        
        _current_result = SearchResponse(
            papers=papers,
            captured_text=request.captured_text or "",
            message=f"找到 {len(papers)} 篇文献"
        )
        
        logger.info(f"搜索完成: {len(papers)} 篇文献")
        return _current_result
        
    except Exception as e:
        logger.error(f"搜索失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/result", response_model=SearchResponse)
async def get_result():
    """
    获取当前搜索结果
    
    用于结果窗口获取之前搜索的结果
    """
    global _current_result
    
    if _current_result is None:
        return SearchResponse(
            papers=[],
            captured_text="",
            message="暂无搜索结果"
        )
    
    return _current_result


@app.post("/api/clear")
async def clear_result():
    """清除当前搜索结果"""
    global _current_result
    _current_result = None
    return {"status": "ok", "message": "结果已清除"}


# ==================== 真正的搜索实现 ====================

async def _real_search(query: str) -> List[Paper]:
    """
    使用真正的搜索服务进行搜索
    
    Args:
        query: 查询字符串（可能是 DOI、标题或引用文本）
    
    Returns:
        论文列表
    """
    from oneshot.models import Paper as ModelPaper
    
    parser = _get_citation_parser()
    search_service = _get_search_service()
    
    # 分割引用文本
    segments = parser.split_citations(query)
    
    if not segments:
        logger.warning("未能分割出任何引用")
        return []
    
    logger.info(f"分割出 {len(segments)} 个引用")
    
    results = []
    
    for segment in segments:
        # 解析引用
        papers = parser.parse(segment, debug=False)
        
        if not papers:
            logger.warning(f"解析失败: {segment[:50]}...")
            continue
        
        paper = papers[0]
        
        # 搜索补充信息
        search_results = await search_service.search(paper)
        
        if search_results:
            # 合并搜索结果
            paper.merge(search_results[0].paper)
        
        # 转换为 API 模型
        api_paper = Paper(
            title=paper.title or "未知标题",
            authors=paper.authors or [],
            year=paper.year,
            abstract=paper.abstract,
            ccf_rank=paper.ccf_rank,
            doi=paper.doi,
            url=paper.url,
            citation_number=paper.citation_number,
            citations=getattr(paper, 'citations', None),
        )
        results.append(api_paper)
    
    return results


# ==================== 启动 ====================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)