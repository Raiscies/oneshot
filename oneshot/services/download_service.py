"""
OneShot - 下载服务
"""

import asyncio
import logging
import hashlib
from pathlib import Path
from typing import Optional, Callable
from datetime import datetime

import httpx

from ..models import Paper, SearchResult, DownloadTask

logger = logging.getLogger(__name__)


class DownloadService:
    """下载服务"""
    
    def __init__(self, storage_dir: str = "./papers"):
        """
        初始化下载服务
        
        Args:
            storage_dir: 文献存储目录
        """
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.active_tasks: dict[str, DownloadTask] = {}
    
    async def download(
        self, 
        result: SearchResult, 
        progress_callback: Optional[Callable[[float], None]] = None
    ) -> Optional[Path]:
        """
        下载文献
        
        Args:
            result: 搜索结果
            progress_callback: 进度回调
            
        Returns:
            下载后的文件路径
        """
        paper = result.paper
        task = DownloadTask(
            paper=paper,
            url=result.download_url or "",
            source=result.source,
            status="downloading"
        )
        
        # 生成文件名
        filename = self._generate_filename(paper)
        file_path = self.storage_dir / filename
        
        # 检查是否已存在
        if file_path.exists():
            logger.info(f"文献已存在: {file_path}")
            task.status = "completed"
            task.progress = 1.0
            paper.file_path = file_path
            paper.downloaded = True
            paper.file_size = file_path.stat().st_size
            return file_path
        
        try:
            # 尝试下载
            if result.download_url:
                await self._download_file(
                    result.download_url, 
                    file_path, 
                    progress_callback
                )
            else:
                # 尝试通过DOI构建URL
                if paper.doi:
                    url = self._build_download_url(paper.doi)
                    if url:
                        await self._download_file(
                            url,
                            file_path,
                            progress_callback
                        )
                else:
                    raise ValueError("没有可用的下载链接")
            
            # 计算文件哈希
            paper.file_hash = await self._calculate_hash(file_path)
            paper.file_path = file_path
            paper.downloaded = True
            paper.file_size = file_path.stat().st_size
            paper.updated_at = datetime.now()
            
            task.status = "completed"
            task.progress = 1.0
            task.completed_at = datetime.now()
            
            logger.info(f"下载完成: {paper.title[:50]}...")
            return file_path
            
        except Exception as e:
            task.status = "failed"
            task.error = str(e)
            logger.error(f"下载失败: {e}")
            
            # 清理不完整的文件
            if file_path.exists():
                file_path.unlink()
            
            return None
    
    async def _download_file(
        self,
        url: str,
        file_path: Path,
        progress_callback: Optional[Callable[[float], None]] = None
    ):
        """下载文件"""
        async with httpx.AsyncClient(timeout=60.0) as client:
            async with client.stream("GET", url) as response:
                response.raise_for_status()
                
                total_size = int(response.headers.get("content-length", 0))
                downloaded = 0
                
                with open(file_path, "wb") as f:
                    async for chunk in response.aiter_bytes(chunk_size=8192):
                        f.write(chunk)
                        downloaded += len(chunk)
                        
                        if progress_callback and total_size:
                            progress = downloaded / total_size
                            progress_callback(progress)
    
    def _generate_filename(self, paper: Paper) -> str:
        """生成文件名"""
        # 安全字符替换
        safe_title = "".join(
            c if c.isalnum() or c in " -_" else "_"
            for c in (paper.title or "unknown")[:50]
        )
        
        # 构建文件名
        parts = []
        if paper.year:
            parts.append(str(paper.year))
        if paper.authors:
            first_author = paper.authors[0].split()[-1]  # 取姓氏
            parts.append(first_author)
        parts.append(safe_title)
        
        return "_".join(parts) + ".pdf"
    
    def _build_download_url(self, doi: str) -> Optional[str]:
        """构建下载URL"""
        # 尝试多个下载源
        urls = [
            # SciHub
            f"https://sci-hub.se/{doi}",
            f"https://sci-hub.st/{doi}",
            # LibGen
            f"https://libgen.is/scimag/{doi}",
        ]
        
        # 注意：实际下载需要处理反爬虫，这里仅作为示例
        # 真实实现需要使用CloudflareBypass等工具
        return None  # 需要进一步实现
    
    async def _calculate_hash(self, file_path: Path) -> str:
        """计算文件MD5哈希"""
        md5 = hashlib.md5()
        
        def _calculate():
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(8192), b""):
                    md5.update(chunk)
            return md5.hexdigest()
        
        return await asyncio.to_thread(_calculate)
