"""
OneShot - 引用解析服务
使用 AnyStyle (Ruby) 解析引用字符串
"""

import subprocess
import json
import logging
from typing import Optional
from pathlib import Path

from ..models import Paper

logger = logging.getLogger(__name__)


class CitationParser:
    """引用解析服务 - 使用AnyStyle"""
    
    def __init__(self, anystyle_path: Optional[str] = None):
        """
        初始化引用解析器
        
        Args:
            anystyle_path: AnyStyle可执行文件路径，默认从PATH中查找
        """
        self.anystyle_path = anystyle_path or self._find_anystyle()
        if not self.anystyle_path:
            logger.warning("AnyStyle未安装或未在PATH中找到，部分功能可能受限")
    
    def _find_anystyle(self) -> Optional[str]:
        """查找AnyStyle可执行文件"""
        # 检查常见位置
        possible_paths = [
            "anystyle",  # 直接调用（需要Ruby环境）
            "C:\\Ruby33-x64\\bin\\anystyle.bat",  # Windows Ruby默认安装
            "C:\\Ruby30-x64\\bin\\anystyle.bat",
        ]
        
        for path in possible_paths:
            try:
                result = subprocess.run(
                    [path, "--version"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.returncode == 0:
                    logger.info(f"找到AnyStyle: {path}")
                    return path
            except (subprocess.TimeoutExpired, FileNotFoundError):
                continue
        
        # 尝试通过Ruby调用
        try:
            result = subprocess.run(
                ["ruby", "-S", "anystyle", "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                return "ruby -S anystyle"
        except:
            pass
        
        return None
    
    def parse(self, citation: str) -> list[Paper]:
        """
        解析引用字符串
        
        Args:
            citation: 原始引用字符串
            
        Returns:
            解析后的Paper对象列表
        """
        if not self.anystyle_path:
            logger.error("AnyStyle不可用，无法解析引用")
            return [self._fallback_parse(citation)]
        
        try:
            # 调用AnyStyle解析
            result = subprocess.run(
                f'{self.anystyle_path} parse -f json'.split(),
                input=citation,
                capture_output=True,
                text=True,
                timeout=30,
                encoding='utf-8'
            )
            
            if result.returncode != 0:
                logger.error(f"AnyStyle解析失败: {result.stderr}")
                return [self._fallback_parse(citation)]
            
            # 解析JSON输出
            data = json.loads(result.stdout)
            papers = []
            
            for item in data:
                paper = Paper(
                    title=item.get("title", ["未知标题"])[0] if item.get("title") else "未知标题",
                    authors=item.get("author", []) or [],
                    year=int(item["date"][0]["value"]) if item.get("date") else None,
                    doi=item.get("DOI", [None])[0] if item.get("DOI") else None,
                    journal=item.get("container-title", [None])[0] if item.get("container-title") else None,
                    volume=item.get("volume", [None])[0] if item.get("volume") else None,
                    pages=item.get("page", [None])[0] if item.get("page") else None,
                    publisher=item.get("publisher", [None])[0] if item.get("publisher") else None,
                    raw_citation=citation,
                )
                papers.append(paper)
            
            return papers if papers else [self._fallback_parse(citation)]
            
        except subprocess.TimeoutExpired:
            logger.error("AnyStyle解析超时")
            return [self._fallback_parse(citation)]
        except json.JSONDecodeError as e:
            logger.error(f"AnyStyle输出解析失败: {e}")
            return [self._fallback_parse(citation)]
        except Exception as e:
            logger.error(f"引用解析异常: {e}")
            return [self._fallback_parse(citation)]
    
    def _fallback_parse(self, citation: str) -> Paper:
        """
        回退解析方法 - 使用正则表达式提取基本信息
        
        Args:
            citation: 原始引用字符串
            
        Returns:
            Paper对象
        """
        import re
        
        paper = Paper(
            title="待解析",
            raw_citation=citation
        )
        
        # 尝试提取DOI
        doi_pattern = r'10\.\d{4,}/[^\s]+'
        doi_match = re.search(doi_pattern, citation)
        if doi_match:
            paper.doi = doi_match.group()
            # 清理DOI末尾的标点
            paper.doi = re.sub(r'[.,;:)\]]+$', '', paper.doi)
        
        # 尝试提取年份
        year_pattern = r'\((\d{4})\)|\b(19|20)\d{2}\b'
        year_match = re.search(year_pattern, citation)
        if year_match:
            year = year_match.group(1) or year_match.group(2)
            paper.year = int(year)
        
        # 尝试提取标题（假设在引号内或特定格式中）
        title_patterns = [
            r'"([^"]+)"',  # 双引号
            r"'([^']+)'",  # 单引号
            r'《([^》]+)》',  # 中文书名号
        ]
        for pattern in title_patterns:
            match = re.search(pattern, citation)
            if match:
                potential_title = match.group(1).strip()
                if len(potential_title) > 10:  # 标题通常较长
                    paper.title = potential_title
                    break
        
        # 如果标题仍是"待解析"，使用DOI或原始文本
        if paper.title == "待解析":
            if paper.doi:
                paper.title = f"文献 DOI: {paper.doi}"
            else:
                # 取前100个字符作为标题
                paper.title = citation[:100] + ("..." if len(citation) > 100 else "")
        
        return paper
    
    def is_available(self) -> bool:
        """检查AnyStyle是否可用"""
        return self.anystyle_path is not None
