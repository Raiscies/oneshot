"""
OneShot - 默认下载处理器

通用流式下载工具，供不需要特殊处理的出版商 handler 复用。
"""

import logging
from pathlib import Path
from typing import Optional, Callable

import httpx

logger = logging.getLogger(__name__)

_DEFAULT_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)


async def stream_download_file(
    client: httpx.AsyncClient,
    url: str,
    file_path: Path,
    progress_callback: Optional[Callable[[float], None]] = None,
) -> Optional[Path]:
    """通用流式下载，handler 可通过此函数直接下载文件"""
    headers = {"User-Agent": _DEFAULT_UA}
    try:
        async with client.stream("GET", url, headers=headers) as resp:
            resp.raise_for_status()
            total = int(resp.headers.get("content-length", 0))
            downloaded = 0
            if progress_callback:
                progress_callback(0.0)  # 立即通知前端下载已开始
            with open(file_path, "wb") as f:
                async for chunk in resp.aiter_bytes(8192):
                    f.write(chunk)
                    downloaded += len(chunk)
                    if progress_callback:
                        if total:
                            progress_callback(min(downloaded / total, 1.0))
        logger.info(f"下载完成: {file_path} ({downloaded} bytes)")
        return file_path
    except Exception as e:
        logger.error(f"下载失败: {e}")
        if file_path.exists():
            file_path.unlink()
        return None
