"""
OneShot - 引用解析服务
使用 AnyStyle (Ruby) 解析引用字符串
"""

import subprocess
import json
import logging
import os
import shutil
import re
import tempfile
from typing import Optional, Dict, List
from pathlib import Path
from datetime import datetime

from ..models import Paper

logger = logging.getLogger(__name__)

# 获取项目根目录
PROJECT_ROOT = Path(__file__).parent.parent.parent


class CitationParser:
    """引用解析服务 - 使用 AnyStyle"""
    
    def __init__(self, anystyle_path: Optional[str] = None, auto_install: bool = True):
        """
        初始化引用解析器
        
        Args:
            anystyle_path: AnyStyle 可执行文件路径，默认从 PATH 中查找
            auto_install: 是否在 AnyStyle 不可用时自动安装（需要 Ruby 环境）
        """
        self.anystyle_path = anystyle_path or self._find_anystyle()
        self._auto_install = auto_install
        
        # 如果未找到且启用了自动安装，尝试安装
        if not self.anystyle_path and auto_install:
            if self._install_anystyle():
                # 安装成功后再次查找
                self.anystyle_path = self._find_anystyle()
        
        if not self.anystyle_path:
            raise RuntimeError(
                "AnyStyle 不可用且自动安装失败。\n"
                "请确保已安装 Ruby，然后运行: gem install anystyle-cli"
            )
    
    def _find_anystyle(self) -> Optional[str]:
        """查找 AnyStyle 可执行文件"""
        # 优先使用 ruby -S anystyle，因为这是最可靠的方式
        if shutil.which("ruby"):
            try:
                result = subprocess.run(
                    ["ruby", "-S", "anystyle", "--version"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.returncode == 0:
                    logger.info(f"找到 AnyStyle: ruby -S anystyle ({result.stdout.strip()})")
                    return "ruby -S anystyle"
            except Exception:
                pass
        
        # 尝试直接调用 anystyle（需要 PATH 中有）
        if shutil.which("anystyle"):
            try:
                result = subprocess.run(
                    ["anystyle", "--version"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.returncode == 0:
                    logger.info(f"找到 AnyStyle: anystyle ({result.stdout.strip()})")
                    return "anystyle"
            except Exception:
                pass
        
        return None
    
    def _is_ruby_available(self) -> bool:
        """检查 Ruby 是否可用"""
        if not shutil.which("ruby"):
            logger.warning("Ruby 未安装或不在 PATH 中")
            return False
        
        try:
            result = subprocess.run(
                ["ruby", "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                logger.info(f"Ruby 可用: {result.stdout.strip()}")
                return True
        except Exception:
            pass
        
        return False
    
    def _install_anystyle(self) -> bool:
        """
        自动安装 AnyStyle CLI
        
        Returns:
            bool: 安装是否成功
        """
        if not self._is_ruby_available():
            logger.error("无法安装 AnyStyle：Ruby 环境不可用")
            return False
        
        try:
            logger.info("正在安装 AnyStyle CLI...")
            
            # 使用 gem 安装 anystyle-cli
            result = subprocess.run(
                ["gem", "install", "anystyle-cli"],
                capture_output=True,
                text=True,
                timeout=120  # 安装可能需要较长时间
            )
            
            if result.returncode == 0:
                logger.info("AnyStyle CLI 安装成功")
                
                # 尝试更新 gem 缓存
                subprocess.run(
                    ["gem", "environment"],
                    capture_output=True,
                    timeout=10
                )
                
                return True
            else:
                logger.error(f"AnyStyle CLI 安装失败: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            logger.error("AnyStyle CLI 安装超时")
            return False
        except Exception as e:
            logger.error(f"AnyStyle CLI 安装异常: {e}")
            return False
    
    def is_available(self) -> bool:
        """检查 AnyStyle 是否可用"""
        return self.anystyle_path is not None
    
    def _split_citations(self, text: str) -> List[str]:
        """
        将包含多个引用的文本分割成单独的引用
        
        分割逻辑：用 \\[\\d+\\] 匹配完整的方括号引用标记（如 [1]），用这些位置分段
        
        Args:
            text: 原始文本
        
        Returns:
            分割后的引用文本列表
        """
        # 先去掉换行符，把多行文本变成单行
        text = text.replace('\n', ' ').replace('\r', ' ')
        # 移除多余空格
        text = re.sub(r'\s+', ' ', text)
        
        # 查找所有完整的方括号引用标记（如 [1]、[2]）
        bracket_matches = list(re.finditer(r'\[\d+\]', text))
        
        # 如果没有方括号引用标记，返回整个文本作为单一引用
        if not bracket_matches:
            if text.strip():
                return [text.strip()]
            return []
        
        # 根据方括号引用标记位置分割文本
        # 从文本开始到第一个 [x]（或每个 [x] 到下一个 [x]）是一段
        citations = []
        
        # 处理第一段：从文本开始到第一个匹配
        first_match = bracket_matches[0]
        if first_match.start() > 0:
            prefix = text[:first_match.start()].strip()
            if prefix:
                citations.append(prefix)
        
        # 处理每个 [x] 到下一个 [x] 之间的文本
        for i, match in enumerate(bracket_matches):
            start = match.start()
            # 下一个匹配的起始位置，如果没有则到文本末尾
            if i + 1 < len(bracket_matches):
                end = bracket_matches[i + 1].start()
            else:
                end = len(text)
            
            segment = text[start:end].strip()
            if segment:
                citations.append(segment)
        
        # 过滤空字符串
        citations = [c for c in citations if c.strip()]
        
        # 如果分割出少于2个片段，返回整个文本
        if len(citations) < 2:
            return [text.strip()]
        
        logger.debug(f"分割出 {len(citations)} 个引用片段")
        # logger.debug(f"引用片段: {citations}")
        return citations
    
    def _save_debug_output(self, raw_citation: str, all_outputs: List[dict]) -> None:
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
            lines = [f"Raw Citation:\n{raw_citation}\n"]
            lines.append(f"\n{'='*50}\n")
            
            for i, item in enumerate(all_outputs):
                lines.append(f"\n--- Segment {i + 1} ---\n")
                lines.append(f"Input:\n{item['input']}\n\n")
                lines.append(f"Output:\n{item['output']}\n")
                lines.append(f"\n{'='*50}\n")
            
            with open(debug_file, 'w', encoding='utf-8') as f:
                f.write(''.join(lines))
            
            logger.info(f"调试文件已保存: {debug_file}")
                
        except Exception as e:
            logger.error(f"保存调试文件失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
    
    def _parse_single_citation(self, citation: str, raw_citation: str, debug_output: list = None) -> Optional[Paper]:
        """
        解析单个引用字符串
        
        Args:
            citation: 单个引用字符串
            raw_citation: 原始引用字符串（用于调试）
            debug_output: 如果提供，收集调试信息到此列表
        
        Returns:
            Paper 对象，解析失败返回 None
        """
        try:
            # 将引用写入临时文件
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
                f.write(citation)
                temp_file = f.name
            
            try:
                # 调用 AnyStyle 解析文件（在文件关闭后调用）
                if self.anystyle_path == "ruby -S anystyle":
                    cmd_parts = ["ruby", "-S", "anystyle", "--stdout", "-f", "csl", "parse", temp_file]
                else:
                    cmd_parts = ["anystyle", "--stdout", "-f", "csl", "parse", temp_file]
                
                result = subprocess.run(
                    cmd_parts,
                    capture_output=True,
                    text=True,
                    timeout=20,
                    encoding='utf-8'
                )
            finally:
                try:
                    os.unlink(temp_file)
                except Exception:
                    pass
            
            if result.returncode != 0:
                logger.error(f"AnyStyle 解析失败: {result.stderr}")
                return None
            
            output = result.stdout.strip()
            
            # 收集调试信息
            if debug_output is not None:
                formatted_output = output
                try:
                    output_obj = json.loads(output)
                    formatted_output = json.dumps(output_obj, ensure_ascii=False, indent=2)
                except json.JSONDecodeError:
                    pass
                debug_output.append({"input": citation, "output": formatted_output})
            
            if not output:
                logger.warning("AnyStyle 输出为空")
                return None
            
            try:
                items = json.loads(output)
                if isinstance(items, list) and len(items) > 0:
                    item = items[0]
                elif isinstance(items, dict):
                    item = items
                else:
                    return None
                
                return self._parse_item_to_paper(item, raw_citation)
            except json.JSONDecodeError:
                logger.warning(f"AnyStyle 输出无法解析: {output[:200]}")
                return None
            
        except subprocess.TimeoutExpired:
            logger.error("AnyStyle 解析超时")
            return None
        except Exception as e:
            logger.error(f"引用解析异常: {e}")
            return None
    
    def split_citations(self, citation: str) -> List[str]:
        """
        分割引用字符串（公开方法）
        
        Args:
            citation: 原始引用字符串
        
        Returns:
            分割后的引用文本列表
        """
        return self._split_citations(citation)
    
    def parse(self, citation: str, debug: bool = False) -> list[Paper]:
        """
        解析引用字符串
        
        Args:
            citation: 原始引用字符串
            debug: 是否保存调试文件
        
        Returns:
            解析后的 Paper 对象列表
        """
        if not self.anystyle_path:
            raise RuntimeError(
                "AnyStyle 不可用，请确保已安装 Ruby 并运行: gem install anystyle-cli"
            )
        
        # 先分割多个引用
        citations = self._split_citations(citation)
        
        if not citations:
            logger.warning("未能分割出任何引用")
            return []
        
        logger.info(f"分割出 {len(citations)} 个引用")
        
        # 收集所有解析结果用于调试
        debug_outputs = [] if debug else None
        
        # 逐个解析每个引用
        papers = []
        for citation_text in citations:
            paper = self._parse_single_citation(citation_text, citation, debug_outputs)
            if paper:
                papers.append(paper)
        
        # 保存调试文件（如果启用）
        if debug and debug_outputs:
            self._save_debug_output(citation, debug_outputs)
        
        if not papers:
            logger.warning("所有引用解析失败")
            raise RuntimeError("AnyStyle 未能解析出任何文献")
        
        logger.info(f"AnyStyle 解析成功，共 {len(papers)} 篇文献")
        return papers
    
    def _parse_item_to_paper(self, item: dict, raw_citation: str) -> Paper:
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
        
        # 提取 citation_number（从 AnyStyle 返回的 citation-number 字段提取）
        citation_number = None
        citation_number_field = item.get("citation-number")
        if citation_number_field:
            if isinstance(citation_number_field, str):
                # 尝试从字符串中提取数字
                match = re.search(r'\d+', citation_number_field)
                if match:
                    citation_number = int(match.group())
            elif isinstance(citation_number_field, (int, float)):
                citation_number = int(citation_number_field)
        
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
            citation_number=citation_number,
        )