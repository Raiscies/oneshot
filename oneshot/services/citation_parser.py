"""
OneShot - 引用解析服务
使用 AnyStyle (Ruby) 解析引用字符串
"""

import subprocess
import json
import logging
import re
from typing import Optional, Dict, List, Callable
from pathlib import Path
from datetime import datetime

from ..models import Paper

logger = logging.getLogger(__name__)

# 获取项目根目录
PROJECT_ROOT = Path(__file__).parent.parent.parent

# AnyStyle 内置路径
ANYSTYLE_PATH = PROJECT_ROOT / "oneshot" / "third_party" / "anystyle" / "bin" / "anystyle"


class CitationParser:
    """引用解析服务 - 使用 AnyStyle"""

    BREAKET_ITEM_MATCHER = re.compile(r'\[[\w\+]{1,8}\]')
    LINEBREAK_SPLITER    = re.compile(r'[\n\t\v\r\f]')
    
    def __init__(self):
        """
        初始化引用解析器
        """
        if not ANYSTYLE_PATH.exists():
            raise RuntimeError(f"AnyStyle 未找到: {ANYSTYLE_PATH}")
        
        self.anystyle_path = str(ANYSTYLE_PATH)
        logger.info(f"AnyStyle 路径: {self.anystyle_path}")
    
    def is_available(self) -> bool:
        """检查 AnyStyle 是否可用"""
        return self.anystyle_path is not None
    
    def split_citations(self, text: str) -> List[tuple]:
        """
        将包含多个引用的文本分割成单独的引用
        
        分割逻辑：用方括号引用标记（如 [1]、[17]、[n.d.]）分段
        
        Args:
            text: 原始文本
        
        Returns:
            分割后的引用文本列表
        """

        # 1. 处理换行：单词边界插入空格，其余直接拼接
        
        lines = re.split(self.LINEBREAK_SPLITER, text)
        text = ''
        should_insert_space = False
        # rebuild the text
        for line in lines:
            line = line.lstrip(' ')
            if len(line) == 0: continue
            # insert a space only if there are atleast one word boundary between two lines
            # 空格的插入可能会对解析造成相当微妙的影响, 进而影响文献查询
            # 目前也只能面向cases进行调整, 无法保证所有的空格插入都是合适的
            if should_insert_space or line[0].isalpha():
                text += ' '
            should_insert_space = line[-1].isalpha()
            text += line

        if len(text) == 0: return []

        citations = [] 
        last_match = None
        for match in re.finditer(self.BREAKET_ITEM_MATCHER, text): 
            # complete the segment before this match
            if last_match is None:
                content = text[0:match.start()].strip()
                if len(content) != 0: 
                    citations.append((None, content))
            else:
                content = text[last_match.end():match.start()].rstrip()
                # [(cite-index, cite-content), ...]
                # eat the '[' and ']' breakets
                citations.append((last_match.group()[1:-1], content))

            last_match = match

        # handle the last segment
        if last_match is None:
            citations.append((None, text))
        else:
            citations.append((last_match.group()[1:-1], text[last_match.end():]))

        logger.debug(f"分割出 {len(citations)} 个引用片段")
        return citations
    
    def _save_debug_output(self, raw_citation: str, output: dict) -> None:
        """
        保存调试文件（整段源文本的所有解析结果）
        
        Args:
            raw_citation: 原始引用字符串
            all_outputs: 所有解析结果列表，每项为 {"input": str, "output": str}
        """
        try:
            debug_dir = PROJECT_ROOT / "debug"
            debug_dir.mkdir(exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            debug_file = debug_dir / f"anystyle_debug_{timestamp}_output.json"
            
            logger.info(f"正在保存调试文件到: {debug_file}")
            
            # 构建输出内容
            lines = [raw_citation]
            lines.append(f"\n{'='*50}\n")
            lines.append(output)
            lines.append(f"\n{'='*50}\n")
            
            with open(debug_file, 'w', encoding='utf-8') as f:
                f.write(''.join(lines))
            
            logger.info(f"调试文件已保存: {debug_file}")
                
        except Exception as e:
            logger.error(f"保存调试文件失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
    
    def parse_single(self, citation: str, citation_index: Optional[str] = None, debug: bool = False) -> Optional[Paper]:
        """
        解析单个引用字符串
        
        Args:
            citation: 单个引用字符串
            citation_index: 引用索引号
            debug: 保存调试输出
        
        Returns:
            Paper 对象，解析失败返回 None
        """
        try:
            # 直接调用 AnyStyle
            result = subprocess.run(
                ["ruby", self.anystyle_path],
                input=citation,
                capture_output=True,
                text=True,
                timeout=10,
                encoding='utf-8'
            )
            
            if result.returncode != 0:
                logger.error(f"AnyStyle 解析失败: {result.stderr}")
                return None
            
            output = result.stdout.strip()
            if not output:
                logger.warning("AnyStyle 输出为空")
                return None
            
            try:
                items = json.loads(output)
            except json.JSONDecodeError:
                logger.warning("Failed to load anystyle output as json")
                return None

            # get the first item and ignore others(if possible)
            if isinstance(items, list) and len(items) > 0:
                item = items[0]
            elif isinstance(items, dict):
                item = items
            else:
                logger.warning(f"AnyStyle 输出无法解析: {output[:200]}")
                return None
            
            # 收集调试信息
            if debug: 
                self._save_debug_output(
                    citation, 
                    json.dumps(item, ensure_ascii=False, indent=2)
                )
            
            return self._parse_item_to_paper(item, citation, citation_index)
            
        except subprocess.TimeoutExpired:
            logger.error("AnyStyle 解析超时")
            return None
        except Exception as e:
            logger.error(f"引用解析异常: {e}")
            return None
    
    def parse(self, citation: str, debug: bool = False) -> list[Paper]:
        """
        解析引用字符串
        
        Args:
            citation: 原始引用字符串
            debug: 是否保存调试文件
        
        Returns:
            解析后的 Paper 对象列表
        """
        # 先分割多个引用
        citations = self.split_citations(citation)
        
        if not citations:
            logger.warning("未能分割出任何引用")
            return []
        
        logger.info(f"分割出 {len(citations)} 个引用")
        
        # 逐个解析每个引用
        papers = []
        for index, content in citations:
            paper = self.parse_single(content, citation_index=index, debug = debug)
            if paper:
                papers.append(paper)
        
        if not papers:
            logger.warning("所有引用解析失败")
            return []
            # raise RuntimeError("AnyStyle 未能解析出任何文献")
        
        logger.info(f"AnyStyle 解析成功，共 {len(papers)} 篇文献")
        return papers
    
    def _parse_item_to_paper(self, item: dict, raw_citation: str, citation_index: Optional[str] = None) -> Paper:
        """
        将 AnyStyle 解析的 JSON 项转换为 Paper 对象
        
        Args:
            item: AnyStyle 解析的字典（CSL 格式）
            raw_citation: 原始引用字符串
        
        Returns:
            Paper 对象
        """
        # AnyStyle 返回的字段可能是列表或单个值
        def get_first(value, default=None):
            if value is None:
                return default
            if isinstance(value, list):
                return value[0] if value else default
            return value
        
        if citation_index is None:
            # 提取 citation_number（从 AnyStyle 返回的 citation-number 字段提取）
            citation_number_field = item.get("citation-number", None)
            if citation_number_field and isinstance(citation_number_field, (str, int, float)):
                citation_index = str(citation_number_field)

        # 提取作者
        authors = item.get("author", []) or []
        if isinstance(authors, list):
            formatted_authors = []
            for a in authors:
                if isinstance(a, dict):
                    family = a.get("family", "")
                    given = a.get("given", "")
                    name = f"{given} {family}".strip() if family else (given or "")
                    if name:
                        formatted_authors.append(name)
                elif isinstance(a, str):
                    formatted_authors.append(a)
            authors = formatted_authors
        
        # 提取年份
        year = None
        issued = item.get("issued") or item.get("date")
        if issued:
            if isinstance(issued, str):
                year_match = re.search(r'\b(19|20)\d{2}\b', str(issued))
                if year_match:
                    year = int(year_match.group())
            elif isinstance(issued, dict):
                date_parts = issued.get("date-parts", [[None]])
                if date_parts and date_parts[0]:
                    year = date_parts[0][0]
        
        # 提取标题，如果没有则使用 URL
        title = get_first(item.get("title"))
        if not title:
            # 如果没有标题但有 URL，使用 URL 作为标题
            url_for_title = get_first(item.get("URL"))
            if url_for_title:
                title = url_for_title
            else:
                title = "未知标题"
        
        # 提取期刊
        journal = get_first(item.get("container-title"))
        
        # 提取卷号
        volume = get_first(item.get("volume"))
        
        # 提取期号
        issue = get_first(item.get("issue"))
        
        # 提取页码
        pages = get_first(item.get("page"))
        
        # 提取出版商
        publisher = get_first(item.get("publisher"))
        
        # 提取 URL，并清理末尾的标点符号（AnyStyle 有时会保留引用中的句号）
        url = get_first(item.get("URL"))
        if url:
            # 去掉 URL 末尾的点和逗号
            url = url.rstrip('.,;')
        
        # 提取 DOI
        doi = get_first(item.get("DOI"))
        
        # 提取 DOI 链接
        if doi and not url:
            url = f"https://doi.org/{doi}"
        
        return Paper(
            title=title,
            authors=authors,
            year=year,
            doi=doi,
            journal=journal,
            volume=volume,
            issue=issue,
            pages=pages,
            publisher=publisher,
            url=url,
            raw_citation=raw_citation,
            citation_index=citation_index
        )