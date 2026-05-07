"""
OneShot - 搜索器包

每个 .py 文件实现一个搜索器，SearchService 会自动加载。
命名规范：xxx_searcher.py，类名以 Searcher 结尾
"""

from .semanticscholar_searcher import SemanticScholarSearcher

__all__ = ["SemanticScholarSearcher"]