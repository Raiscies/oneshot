"""
OneShot - 通用页面抓取下载处理器

无需构造 PDF URL，直接从出版商页面 HTML 中提取直链。
通过配置 regex 或 CSS selector 适配不同出版商。
"""

import logging
import re
from pathlib import Path
from typing import Optional, Callable

import httpx

from .default_handler import stream_download_file

logger = logging.getLogger(__name__)


async def scrape_handler(
    client: httpx.AsyncClient,
    doi: str,
    publisher_url: str,
    download_dir: Path,
    pdf_regex: str,
    filename: Optional[str] = None,
    progress_callback: Optional[Callable[[float], None]] = None,
    headers: Optional[dict] = None,
) -> Optional[Path]:
    """从出版商页面抓取 PDF 直链并下载。

    Args:
        client: httpx 客户端
        doi: 文献 DOI
        publisher_url: 出版商页面 URL
        download_dir: 下载目录
        pdf_regex: 用于从 HTML 中提取 PDF URL 的正则（需含一个捕获组）
        filename: 保存文件名
        progress_callback: 进度回调
        headers: 额外请求头
    """
    logger.info(f"页面抓取: {publisher_url}")

    try:
        resp = await client.get(publisher_url, headers=headers)
        resp.raise_for_status()

        match = re.search(pdf_regex, resp.text)
        if not match:
            logger.error(f"未在页面中找到 PDF 链接 (regex={pdf_regex})")
            return None

        pdf_url = match.group(1)
        # 处理相对路径
        if pdf_url.startswith("/"):
            from urllib.parse import urljoin
            pdf_url = urljoin(publisher_url, pdf_url)

        logger.info(f"提取到 PDF 链接: {pdf_url}")

        if not filename:
            filename = f"{doi.replace('/', '_')}.pdf"
        file_path = download_dir / filename

        return await stream_download_file(client, pdf_url, file_path, progress_callback)

    except Exception as e:
        logger.error(f"页面抓取失败: {e}")
        return None

