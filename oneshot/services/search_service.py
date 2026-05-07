"""
OneShot - 多源检索服务
"""

import asyncio
import logging
import pkgutil
from typing import Optional

from ..models import Paper, SearchResult

logger = logging.getLogger(__name__)


class SearchService:
    """多源检索服务"""
    
    def __init__(self):
        """初始化检索服务"""
        self.searchers = []
        self._init_searchers()
    
    def _init_searchers(self):
        """自动加载 searchers 目录下的所有搜索器"""
        import os
        from pathlib import Path
        
        # 获取 searchers 目录
        searchers_dir = Path(__file__).parent.parent / "searchers"
        
        if not searchers_dir.exists():
            logger.warning(f"searchers 目录不存在: {searchers_dir}")
            return
        
        # 遍历目录中的所有 .py 文件（排除 __init__.py）
        for file_path in searchers_dir.glob("*.py"):
            if file_path.name.startswith("_"):
                continue
            
            module_name = file_path.stem
            
            try:
                # 动态导入模块
                module = __import__(f"oneshot.searchers.{module_name}", fromlist=[""])
                
                # 查找模块中的 Searcher 类
                for attr_name in dir(module):
                    attr = getattr(module, attr_name)
                    
                    # 检查是否是类且名字以 Searcher 结尾
                    if (isinstance(attr, type) 
                        and attr_name.endswith("Searcher")
                        and attr_name != "Searcher"
                        and hasattr(attr, 'search')):
                        
                        try:
                            searcher = attr()
                            self.searchers.append(searcher)
                            logger.info(f"已加载 {attr_name}")
                        except Exception as e:
                            logger.error(f"初始化 {attr_name} 失败: {e}")
                            
            except Exception as e:
                logger.warning(f"加载搜索器模块 {module_name} 失败: {e}")
    
    def add_searcher(self, searcher):
        """添加搜索器实例"""
        self.searchers.append(searcher)
    
    async def search(self, paper: Paper) -> list[SearchResult]:
        """
        并行搜索多个数据源
        
        Args:
            paper: 搜索目标文献
            
        Returns:
            搜索结果列表
        """
        if not self.searchers:
            logger.warning("没有配置任何搜索器")
            return []
        
        # 创建搜索任务
        tasks = []
        for searcher in self.searchers:
            if hasattr(searcher, 'search'):
                tasks.append(self._search_with_source(searcher, paper))
        
        if not tasks:
            return []
        
        # 并行执行所有搜索
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 过滤无效结果
        valid_results = []
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"搜索异常: {result}")
            elif result:
                valid_results.append(result)
        
        # 按分数排序
        # valid_results.sort(key=lambda x: x.score, reverse=True)
        
        return valid_results
    
    async def _search_with_source(self, searcher, paper: Paper) -> Optional[SearchResult]:
        """使用指定搜索器搜索"""
        try:
            result = await searcher.search(paper)
            if result:
                result.source = getattr(searcher, 'name', 'Unknown')
                return result
        except Exception as e:
            logger.error(f"搜索器 {getattr(searcher, 'name', 'Unknown')} 错误: {e}")
        return None