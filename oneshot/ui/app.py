"""
OneShot - NiceGUI Web界面
"""

import asyncio
import logging
from typing import Optional
from datetime import datetime

from nicegui import app, ui

from ..models import Paper
from ..services import CitationParser, SearchService, DownloadService

logger = logging.getLogger(__name__)


class OneShotUI:
    """OneShot Web界面"""
    
    def __init__(
        self,
        citation_parser: CitationParser,
        search_service: SearchService,
        download_service: DownloadService
    ):
        """
        初始化UI
        
        Args:
            citation_parser: 引用解析器
            search_service: 检索服务
            download_service: 下载服务
        """
        self.citation_parser = citation_parser
        self.search_service = search_service
        self.download_service = download_service
        
        # 状态
        self.current_papers: list[Paper] = []
        self.search_results: list = []
        self.is_processing = False
        
        # 组件引用
        self.status_label: Optional[ui.label] = None
        self.result_container: Optional[ui.column] = None
        self.progress_bar: Optional[ui.linear_progress] = None
    
    def create_ui(self):
        """创建UI"""
        
        # 主页布局
        with ui.header().classes('bg-primary'):
            ui.label('OneShot - 文献快速下载').classes('text-h5 text-white')
        
        # 状态栏
        with ui.row().classes('w-full items-center q-pa-md'):
            self.status_label = ui.label('就绪')
            with ui.row().classes('ml-auto'):
                self.status_label = ui.label('快捷键: Ctrl+Shift+L')
        
        # 主内容区
        with ui.row().classes('w-full q-pa-md'):
            # 左侧面板 - 当前引用
            with ui.column().classes('w-1/3'):
                ui.label('当前引用').classes('text-h6')
                
                self.citation_display = ui.code('').classes('w-full')
                
                with ui.row():
                    ui.button('开始处理', on_click=self.process_clipboard)
                    ui.button('清空', on_click=self.clear)
            
            # 中间面板 - 搜索结果
            with ui.column().classes('w-1/3'):
                ui.label('搜索结果').classes('text-h6')
                self.result_container = ui.column()
                self.progress_bar = ui.linear_progress(show_value=False)
            
            # 右侧面板 - 文献库
            with ui.column().classes('w-1/3'):
                ui.label('文献库').classes('text-h6')
                self.library_container = ui.column()
                ui.button('刷新', on_click=self.refresh_library)
        
        # 设置页面
        with ui.tab('设置'):
            with ui.column():
                ui.label('存储路径设置')
                ui.input(
                    label='文献存储目录',
                    value=str(self.download_service.storage_dir)
                ).classes('w-full')
    
    async def process_clipboard(self):
        """处理剪贴板内容"""
        if self.is_processing:
            return
        
        self.is_processing = True
        self.status_label.text = '处理中...'
        self.progress_bar.value = 0
        
        try:
            # 1. 读取剪贴板
            from ..services import ClipboardService
            clipboard = ClipboardService()
            citation = clipboard.get_text()
            
            if not citation:
                ui.notify('剪贴板为空', type='warning')
                return
            
            self.citation_display.text = citation
            self.progress_bar.value = 0.2
            
            # 2. 解析引用
            papers = self.citation_parser.parse(citation)
            
            if not papers:
                ui.notify('解析失败', type='negative')
                return
            
            self.current_papers = papers
            self.progress_bar.value = 0.4
            
            # 显示解析结果
            self._display_parsed_papers(papers)
            
            # 3. 搜索
            search_results = []
            for paper in papers:
                results = await self.search_service.search(paper)
                search_results.extend(results)
            
            self.search_results = search_results
            self.progress_bar.value = 0.7
            
            # 显示搜索结果
            self._display_search_results(search_results)
            self.progress_bar.value = 1.0
            
            self.status_label.text = f'完成 - 找到 {len(search_results)} 个结果'
            ui.notify(f'处理完成，找到 {len(search_results)} 个结果', type='positive')
            
        except Exception as e:
            logger.error(f"处理失败: {e}")
            ui.notify(f'处理失败: {e}', type='negative')
            self.status_label.text = '处理失败'
        
        finally:
            self.is_processing = False
    
    def _display_parsed_papers(self, papers: list[Paper]):
        """显示解析结果"""
        # 清理之前的显示
        self.result_container.clear()
        
        with self.result_container:
            for i, paper in enumerate(papers):
                with ui.card().classes('w-full q-mb-sm'):
                    ui.label(f"文献 {i+1}").classes('text-subtitle2')
                    ui.label(f"标题: {paper.title}").classes('text-body2')
                    if paper.authors:
                        ui.label(f"作者: {', '.join(paper.authors[:3])}").classes('text-body2')
                    if paper.year:
                        ui.label(f"年份: {paper.year}").classes('text-body2')
                    if paper.doi:
                        ui.label(f"DOI: {paper.doi}").classes('text-caption text-primary')
    
    def _display_search_results(self, results: list):
        """显示搜索结果"""
        for result in results:
            with ui.card().classes('w-full q-mb-sm'):
                with ui.row():
                    ui.label(f"来源: {result.source}").classes('text-caption')
                    ui.space()
                    ui.label(f"匹配度: {result.score:.0%}").classes('text-caption')
                
                ui.label(result.paper.title).classes('text-body1')
                ui.label(f"作者: {result.paper.display_authors}").classes('text-body2')
                
                ui.button(
                    '下载',
                    on_click=lambda r=result: self._download_paper(r)
                ).props('flat color=primary size=sm')
    
    async def _download_paper(self, result):
        """下载文献"""
        try:
            ui.notify(f'开始下载: {result.paper.title[:30]}...', type='info')
            
            file_path = await self.download_service.download(result)
            
            if file_path:
                ui.notify(f'下载完成: {file_path.name}', type='positive')
                self.refresh_library()
            else:
                ui.notify('下载失败', type='negative')
                
        except Exception as e:
            logger.error(f"下载失败: {e}")
            ui.notify(f'下载失败: {e}', type='negative')
    
    def refresh_library(self):
        """刷新文献库"""
        self.library_container.clear()
        
        # 获取所有已下载的文献
        storage_dir = self.download_service.storage_dir
        if storage_dir.exists():
            for f in sorted(storage_dir.glob('*.pdf')):
                with self.library_container:
                    with ui.card().classes('w-full q-mb-xs'):
                        ui.label(f.name).classes('text-body2')
                        size = f.stat().st_size / 1024 / 1024  # MB
                        ui.label(f'大小: {size:.2f} MB').classes('text-caption')
        
        if not list(self.library_container):
            with self.library_container:
                ui.label('暂无文献').classes('text-grey-6')
    
    def clear(self):
        """清空"""
        self.current_papers = []
        self.search_results = []
        self.citation_display.text = ''
        self.result_container.clear()
        self.status_label.text = '就绪'
        self.progress_bar.value = 0


def create_app(
    citation_parser: CitationParser,
    search_service: SearchService,
    download_service: DownloadService
) -> ui:
    """创建应用"""
    
    oneshot_ui = OneShotUI(
        citation_parser,
        search_service,
        download_service
    )
    
    oneshot_ui.create_ui()
    
    return oneshot_ui
