"""
OneShot - 一键直达文献
基于快捷键的论文文献快速下载工具
"""

__version__ = "1.0.0"
__author__ = "OneShot"

from .models import Paper, SearchResult, DownloadTask
from .services import (
    CitationParser,
    SearchService,
    DownloadService,
    KeyboardService,
    SelectionService,
    TrayService,
)

__all__ = [
    "Paper",
    "SearchResult", 
    "DownloadTask",
    "CitationParser",
    "SearchService",
    "DownloadService",
    "KeyboardService",
    "SelectionService",
    "TrayService",
]
