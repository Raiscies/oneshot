"""
OneShot - Dagstuhl (DROPS) 下载处理器

从文档页面抓取 PDF 直链。
"""

import logging
from pathlib import Path
from typing import Optional, Callable

import httpx

from .scrape_handler import scrape_handler

logger = logging.getLogger(__name__)

DAGSTUHL_REGEX = r'href="(https://drops\.dagstuhl\.de/storage/[^"]+\.pdf)"'

async def dagstuhl_handler(
    client: httpx.AsyncClient,
    doi: str,
    publisher_url: str,
    download_dir: Path,
    filename: Optional[str] = None,
    progress_callback: Optional[Callable[[float], None]] = None,
) -> Optional[Path]:
    """Dagstuhl DROPS 下载处理器"""
    return await scrape_handler(
        client, doi, publisher_url, download_dir,
        pdf_regex=DAGSTUHL_REGEX,
        filename=filename,
        progress_callback=progress_callback,
    )

'''
<a href="https://drops.dagstuhl.de/storage/00lipics/lipics-vol123-isaac2018/LIPIcs.ISAAC.2018.56/LIPIcs.ISAAC.2018.56.pdf" title="View as PDF">
<span class="badge" style="background-color: #444; width: 300px; transform: translateY(-2px); font-size: unset;">
<i class="bi bi-file-earmark-pdf-fill" style="color:red; background-color: #fff; border-radius: 2px; padding-top: 1px"></i> PDF
</span>
<div class="mt-2">LIPIcs.ISAAC.2018.56.pdf</div>
</a>
'''