"""
OneShot - 服务包初始化
"""

from .citation_parser import CitationParser
from .search_service import SearchService
from .download_service import DownloadService
from .keyboard_service import KeyboardService
from .selection_service import SelectionService
from .tray_service import TrayService
from .config_service import ConfigService
from .handlers import register_all as register_download_handlers

# 导入搜索器
try:
    from ..searchers import SemanticScholarSearcher
except ImportError:
    SemanticScholarSearcher = None

__all__ = [
    "CitationParser",
    "SearchService",
    "DownloadService",
    "KeyboardService",
    "SelectionService",
    "TrayService",
    "ConfigService",
    "SemanticScholarSearcher",
]
