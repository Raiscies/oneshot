"""
OneShot - ACM Digital Library 下载处理器

通过 CloudflareBypass 代理绕过 ACM 的 Cloudflare 防护，下载 PDF。
"""

import logging
from pathlib import Path
from typing import Optional, Callable

import httpx

from .cf_proxy import get_proxy

logger = logging.getLogger(__name__)


async def acm_handler(
    client: httpx.AsyncClient,
    doi: str,
    publisher_url: str,
    download_dir: Path,
    filename: Optional[str] = None,
    progress_callback: Optional[Callable[[float], None]] = None,
) -> Optional[Path]:
    """ACM Digital Library 下载处理器"""
    proxy = get_proxy()
    if not proxy:
        logger.error("CloudflareBypass 代理未初始化")
        return None

    pdf_path = f"/doi/pdf/{doi}"
    filename = filename or f"{doi.replace('/', '_')}.pdf"
    return await proxy.download(
        client, pdf_path, "dl.acm.org", download_dir, filename, progress_callback
    )
