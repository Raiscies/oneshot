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
    from .dagstuhl import dagstuhl_handler
    from .springer import springer_handler
    from .nature import nature_handler
    from .siam import siam_handler
    from .arxiv import arxiv_handler
    from .aps import aps_handler

    service.register_handler("dl.acm.org", acm_handler)
    service.register_handler("ieeexplore.ieee.org", ieee_handler)
    service.register_handler("drops.dagstuhl.de", dagstuhl_handler)
    service.register_handler("link.springer.com", springer_handler)
    service.register_handler("www.nature.com", nature_handler)
    service.register_handler("epubs.siam.org", siam_handler)
    service.register_handler("arxiv.org", arxiv_handler)
    service.register_handler("journals.aps.org", aps_handler)
