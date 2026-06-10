"""
OneShot - Nature 下载处理器

Nature 不需要 Cloudflare 绕过，直接追加 .pdf 下载。
"""

import logging
from pathlib import Path
from typing import Optional, Callable

import httpx

from .default_handler import stream_download_file

logger = logging.getLogger(__name__)


async def nature_handler(
    client: httpx.AsyncClient,
    doi: str,
    publisher_url: str,
    download_dir: Path,
    filename: Optional[str] = None,
    progress_callback: Optional[Callable[[float], None]] = None,
) -> Optional[Path]:
    """Nature 下载处理器
    """
    pdf_url = publisher_url.rstrip("/") + ".pdf"
    logger.info(f"Nature 下载: {pdf_url}")

    if not filename:
        filename = f"{doi.replace('/', '_')}.pdf"
    file_path = download_dir / filename

    return await stream_download_file(client, pdf_url, file_path, progress_callback)
