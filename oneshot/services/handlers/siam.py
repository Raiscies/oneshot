"""
OneShot - SIAM 下载处理器

通过 CloudflareBypass 代理下载 PDF。
"""

import logging
from pathlib import Path
from typing import Optional, Callable

import httpx

from .cf_proxy import get_proxy

logger = logging.getLogger(__name__)


async def siam_handler(
    client: httpx.AsyncClient,
    doi: str,
    publisher_url: str,
    download_dir: Path,
    filename: Optional[str] = None,
    progress_callback: Optional[Callable[[float], None]] = None,
) -> Optional[Path]:
    """SIAM 下载处理器"""
    proxy = get_proxy()
    if not proxy:
        logger.error("CloudflareBypass 代理未初始化")
        return None

    pdf_path = f"/doi/pdf/{doi}?download=true"
    return await proxy.download(
        client, pdf_path, "epubs.siam.org", download_dir, filename, progress_callback
    )
