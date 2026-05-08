"""
OneShot - FastAPI 后端
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import uvicorn

app = FastAPI(title="OneShot API")

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 数据模型
class Paper(BaseModel):
    title: str
    authors: List[str] = []
    year: Optional[int] = None
    abstract: Optional[str] = None
    ccf_rank: Optional[str] = None
    doi: Optional[str] = None
    citation_number: Optional[int] = None
    citations: Optional[int] = None


class SearchRequest(BaseModel):
    query: str
    captured_text: Optional[str] = ""


class SearchResponse(BaseModel):
    papers: List[Paper]
    captured_text: str = ""


# 当前搜索结果（用于结果窗口获取）
_current_result: Optional[SearchResponse] = None


@app.post("/api/search", response_model=SearchResponse)
async def search_papers(request: SearchRequest):
    """搜索文献 API"""
    global _current_result
    
    # TODO: 调用实际的搜索服务
    # 这里先用模拟数据
    papers = [
        Paper(
            title="Contraction Hierarchies: Faster and Simpler Hierarchical Routing in Road Networks",
            authors=["Robert Geisberger", "Peter Sanders", "Dominik Schultes", "Daniel Delling"],
            year=2008,
            citation_number=19,
            ccf_rank="B",
            doi="10.1007/978-3-540-68552-4_24",
            abstract="We present a route planning technique solely based on the concept of node contraction.",
            citations=1500,
        ),
        Paper(
            title="Data structures for categorical path counting queries",
            authors=["Meng He", "Serikzhan Kazi"],
            year=2022,
            citation_number=1,
            ccf_rank="A",
            doi="10.1016/j.tcs.2022.01.023",
            abstract="Consider an ordinal tree T on n nodes, each of which is assigned a category from an alphabet.",
        ),
    ]
    
    _current_result = SearchResponse(
        papers=papers,
        captured_text=request.captured_text or "[19] Robert Geisberger et al. 2008...",
    )
    
    return _current_result


@app.get("/api/result", response_model=SearchResponse)
async def get_result():
    """获取当前搜索结果（用于结果窗口）"""
    global _current_result
    
    if _current_result is None:
        # 返回默认数据
        return SearchResponse(
            papers=[],
            captured_text="",
        )
    
    return _current_result


@app.get("/health")
async def health_check():
    """健康检查"""
    return {"status": "ok"}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)