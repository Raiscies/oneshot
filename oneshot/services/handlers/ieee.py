"""
OneShot - IEEE Xplore 下载处理器

IEEE 不需要 Cloudflare 绕过，直接从 stampPDF/getPDF.jsp 下载 PDF。
"""

import logging
import re
from pathlib import Path
from typing import Optional, Callable

import httpx

from .default_handler import stream_download_file

logger = logging.getLogger(__name__)


async def ieee_handler(
    client: httpx.AsyncClient,
    doi: str,
    publisher_url: str,
    download_dir: Path,
    filename: Optional[str] = None,
    progress_callback: Optional[Callable[[float], None]] = None,
) -> Optional[Path]:
    """IEEE Xplore 下载处理器

    从 publisher URL 提取 document ID，拼接 getPDF.jsp 直链下载。
    例: https://ieeexplore.ieee.org/document/123456/ → stampPDF/getPDF.jsp?arnumber=123456
    """
    # 提取 IEEE document ID
    match = re.search(r"/document/(\d+)", publisher_url)
    if not match:
        logger.error(f"无法从 URL 提取 IEEE document ID: {publisher_url}")
        return None

    doc_id = match.group(1)
    pdf_url = f"https://ieeexplore.ieee.org/stampPDF/getPDF.jsp?tp=&arnumber={doc_id}"
    logger.info(f"IEEE 下载: {pdf_url}")

    if not filename:
        filename = f"{doi.replace('/', '_')}.pdf"
    file_path = download_dir / filename

    return await stream_download_file(client, pdf_url, file_path, progress_callback)
