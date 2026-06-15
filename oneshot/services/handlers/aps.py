"""
OneShot - APS (American Physical Society) 下载处理器

通过 CloudflareBypass 代理绕过 journals.aps.org 的 Cloudflare 防护。
DOI 解析后 URL 格式为 https://journals.aps.org/{journal}/abstract/{doi}，
将 /abstract/ 替换为 /pdf/ 即可得到 PDF 直链。
"""

import logging
from pathlib import Path
from typing import Optional, Callable
from urllib.parse import urlparse

import httpx

from .cf_proxy import get_proxy

logger = logging.getLogger(__name__)


async def aps_handler(
    client: httpx.AsyncClient,
    doi: str,
    publisher_url: str,
    download_dir: Path,
    filename: Optional[str] = None,
    progress_callback: Optional[Callable[[float], None]] = None,
) -> Optional[Path]:
    """APS 下载处理器 (journals.aps.org)

    将 publisher URL 中的 /abstract/ 替换为 /pdf/，
    通过 CloudflareBypass 代理下载。
    """
    proxy = get_proxy()
    if not proxy:
        logger.error("CloudflareBypass 代理未初始化")
        return None

    parsed = urlparse(publisher_url)
    pdf_path = parsed.path.replace("/abstract/", "/pdf/")
    logger.info(f"APS 下载: https://journals.aps.org{pdf_path}")

    if not filename:
        filename = f"{doi.replace('/', '_')}.pdf"

    return await proxy.download(
        client, pdf_path, "journals.aps.org", download_dir, filename, progress_callback
    )
