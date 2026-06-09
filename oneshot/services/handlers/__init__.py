"""
OneShot - 出版商处理器注册中心

所有出版商的下载处理器在此统一注册。
添加新出版商：在此 import handler 并加入 register_all()。
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..download_service import DownloadService

logger = logging.getLogger(__name__)


def register_all(service: "DownloadService"):
    """向 DownloadService 注册所有内置的出版商处理器"""
    from .acm import acm_handler
    from .ieee import ieee_handler

    service.register_handler("dl.acm.org", acm_handler)
    service.register_handler("ieeexplore.ieee.org", ieee_handler)
