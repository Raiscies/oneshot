"""
OneShot - 结果对话框 UI
"""

import customtkinter as ctk
import logging
import webbrowser
from pathlib import Path
from PIL import Image

logger = logging.getLogger(__name__)

# 窗口配置常量
WINDOW_WIDTH = 550
WINDOW_MIN_HEIGHT = 100
WINDOW_MAX_HEIGHT = 700

# 颜色常量
COLOR_OUTER = "#333333"
COLOR_INNER = "#222222"
COLOR_TEXT = "white"
COLOR_TEXT_GRAY = "gray"

# 图标缓存
_icon_cache = {}


def load_icon(name, size=20):
    """加载 PNG 图标并转换为 CTk 可用的图像（带缓存）"""
    cache_key = (name, size)
    if cache_key in _icon_cache:
        return _icon_cache[cache_key]
    
    icon_dir = Path(__file__).parent.parent / "assets"
    png_path = icon_dir / f"{name}.png"
    
    if not png_path.exists():
        return None
    
    try:
        img = Image.open(png_path)
        img = img.resize((size, size), Image.Resampling.LANCZOS)
        icon = ctk.CTkImage(img, size=(size, size))
        _icon_cache[cache_key] = icon
        return icon
    except Exception as e:
        logger.error(f"加载图标失败 {name}: {e}")
        return None


def clear_icon_cache():
    """清除图标缓存"""
    global _icon_cache
    _icon_cache = {}


class Card:
    """论文卡片"""
    
    def __init__(self, parent, index, paper=None, segment=None):
        """
        创建卡片
        
        Args:
            parent: 父容器
            index: 卡片索引
            paper: 论文对象（可选，用于完整显示）
            segment: 分段文本（作为初始标题显示）
        """
        self.parent = parent
        self.index = index
        
        # 卡片数据
        self._paper = paper
        self._segment = segment
        
        # widget 引用
        self._card = None
        self._content = None
        self._title_frame = None
        
        # 信息行 widget 引用
        self._author_label = None
        self._year_label = None
        self._abstract_label = None
        self._spacer = None
        self._extra_labels = []  # 额外的标签（DOI, URL, Citations 等）
        
        if paper is not None:
            self._build_card(self._paper_to_display_data(paper), paper=paper)
        elif segment is not None:
            self._build_card(self._segment_to_display_data())
    
    def _segment_to_display_data(self):
        """从分段文本生成显示数据"""
        display_text = self._segment[:80] + "..." if len(self._segment) > 80 else self._segment
        
        return {
            'full_title': display_text,
            'authors': [],
            'year': None,
            'abstract': '',
            'ccf_rank': '',
            'doi': None,
            'url': None,
            'citations': None
        }
    
    def _paper_to_display_data(self, paper):
        """从 paper 对象提取显示数据"""
        title = getattr(paper, 'title', None) or 'unknown title'
        authors = getattr(paper, 'authors', None) or []
        year = getattr(paper, 'year', None)
        abstract = getattr(paper, 'abstract', None) or None
        ccf_rank = getattr(paper, 'ccf_rank', None) or None
        cite_num = getattr(paper, 'citation_number', None)
        doi = getattr(paper, 'doi', None) or None
        url = getattr(paper, 'url', None) or None
        citations = getattr(paper, 'citations', None)
        
        full_title = f"[{cite_num}] {title}" if cite_num is not None else title
        
        return {
            'full_title': full_title,
            'authors': authors,
            'year': year,
            'abstract': abstract,
            'ccf_rank': ccf_rank,
            'doi': doi,
            'url': url,
            'citations': citations
        }
    
    def _build_card(self, data, paper=None, callbacks=None):
        """构建完整卡片"""
        self._card = ctk.CTkFrame(self.parent, fg_color=COLOR_OUTER)
        self._card.pack(fill="x", pady=5, padx=5)
        
        self._content = ctk.CTkFrame(self._card, fg_color=COLOR_INNER)
        self._content.pack(fill="x", padx=1, pady=1)
        
        # 标题行
        self._title_frame = ctk.CTkFrame(self._content, fg_color="transparent")
        self._title_frame.pack(fill="x", padx=10, pady=(10, 5))
        
        self._build_title_row(self._title_frame, data['full_title'], paper, callbacks)
        self._build_info_rows(self._content, data)
    
    def _build_title_row(self, parent, full_title, paper=None, callbacks=None):
        """构建标题行"""
        title_height = min(max((len(full_title) // 50 + 1), 2), 4) * 20
        
        title_text = ctk.CTkTextbox(
            parent, height=title_height, wrap="word",
            font=ctk.CTkFont(weight="bold", size=12),
            fg_color=COLOR_INNER, text_color=COLOR_TEXT, border_width=0
        )
        title_text.insert("1.0", full_title)
        title_text.configure(state="disabled")
        title_text.pack(side="left", fill="x", expand=True)
        
        buttons_frame = ctk.CTkFrame(parent, fg_color="transparent")
        self._add_buttons(buttons_frame, paper, callbacks)
        buttons_frame.pack(side="right")
    
    def _build_info_rows(self, parent, data):
        """构建信息行（作者、年份、摘要、DOI、URL、引用数）"""
        # 清空之前的额外标签
        self._extra_labels = []
        
        # 作者行
        author_display = self._format_authors(data.get('authors', []))
        
        self._author_label = ctk.CTkLabel(
            parent, text=f"作者: {author_display}",
            font=ctk.CTkFont(size=11),
            text_color=COLOR_TEXT,
            anchor="w"
        )
        self._author_label.pack(anchor="w", padx=10, fill="x")
        
        # 年份 + CCF
        year_text = data.get('year') if data.get('year') is not None else 'unknown'
        year_ccf_text = f"年份: {year_text}"
        if data.get('ccf_rank'):
            year_ccf_text += f"    CCF: {data.get('ccf_rank')}"
        
        self._year_label = ctk.CTkLabel(
            parent, text=year_ccf_text,
            font=ctk.CTkFont(size=11),
            text_color=COLOR_TEXT,
            anchor="w"
        )
        self._year_label.pack(anchor="w", padx=10, pady=(0, 5), fill="x")
        
        # DOI
        if data.get('doi'):
            doi_label = ctk.CTkLabel(
                parent, text=f"DOI: {data.get('doi')}",
                font=ctk.CTkFont(size=10),
                text_color="#888888",
                anchor="w"
            )
            doi_label.pack(anchor="w", padx=10, pady=(0, 2), fill="x")
            self._extra_labels.append(doi_label)
        
        # 引用数
        if data.get('citations') is not None:
            cite_label = ctk.CTkLabel(
                parent, text=f"引用: {data.get('citations')}",
                font=ctk.CTkFont(size=10),
                text_color="#888888",
                anchor="w"
            )
            cite_label.pack(anchor="w", padx=10, pady=(0, 2), fill="x")
            self._extra_labels.append(cite_label)
        
        # 摘要
        if data.get('abstract'):
            self._abstract_label = ctk.CTkLabel(
                parent, text=f"摘要: {data.get('abstract')[:200]}..." if len(data.get('abstract', '')) > 200 else f"摘要: {data.get('abstract')}",
                font=ctk.CTkFont(size=11),
                text_color="#aaaaaa",
                anchor="w",
                wraplength=500
            )
            self._abstract_label.pack(anchor="w", padx=10, pady=(5, 10), fill="x")
    
    @staticmethod
    def _format_authors(authors):
        """格式化作者列表"""
        if not authors:
            return "unknown"
        author_display = ", ".join(authors[:3])
        if len(authors) > 3:
            author_display += " et al."
        return author_display
    
    @staticmethod
    def _add_buttons(parent, paper, callbacks=None, first=True):
        """添加操作按钮"""
        button_configs = [
            {"icon": "download", "fallback": "⬇", "key": "download", "fg_color": "#2b7a0b", "hover_color": "#3a9a1b"},
            {"icon": "open_url", "fallback": "🌐", "key": "open_url", "fg_color": "#1f6aa5", "hover_color": "#2a7ab5"},
        ]
        
        for config in button_configs:
            icon = load_icon(config["icon"], size=18)
            callback = callbacks.get(config["key"]) if callbacks else None
            
            btn = ctk.CTkButton(
                parent, 
                image=icon if icon else None, 
                text="" if icon else config["fallback"],
                width=30, height=25,
                command=lambda c=callback: c(paper) if c else None,
                fg_color=config["fg_color"], hover_color=config["hover_color"],
                font=ctk.CTkFont(size=12)
            )
            
            padx = (5, 0) if first else (2, 0)
            first = False
            btn.pack(side="right", padx=padx)
    
    def update(self, paper, callbacks=None):
        """更新卡片内容"""
        data = self._paper_to_display_data(paper)
        
        # 更新标题行
        for widget in self._title_frame.winfo_children():
            widget.destroy()
        self._build_title_row(self._title_frame, data['full_title'], paper, callbacks)
        
        # 更新作者
        author_display = self._format_authors(data.get('authors', []))
        self._author_label.configure(text=f"作者: {author_display}")
        
        # 更新年份
        year_text = data.get('year') if data.get('year') is not None else 'unknown'
        year_ccf_text = f"年份: {year_text}"
        if data.get('ccf_rank'):
            year_ccf_text += f"    CCF: {data.get('ccf_rank')}"
        self._year_label.configure(text=year_ccf_text)
        
        # 清空并重建额外标签
        for label in self._extra_labels:
            label.destroy()
        self._extra_labels = []
        
        # 添加 DOI
        if data.get('doi'):
            doi_label = ctk.CTkLabel(
                self._content, text=f"DOI: {data.get('doi')}",
                font=ctk.CTkFont(size=10),
                text_color="#888888",
                anchor="w"
            )
            doi_label.pack(anchor="w", padx=10, pady=(0, 2), fill="x")
            self._extra_labels.append(doi_label)
        
        # 添加引用数
        if data.get('citations') is not None:
            cite_label = ctk.CTkLabel(
                self._content, text=f"引用: {data.get('citations')}",
                font=ctk.CTkFont(size=10),
                text_color="#888888",
                anchor="w"
            )
            cite_label.pack(anchor="w", padx=10, pady=(0, 2), fill="x")
            self._extra_labels.append(cite_label)
        
        # 更新摘要
        if data.get('abstract'):
            if self._spacer:
                self._spacer.destroy()
                self._spacer = None
            if self._abstract_label:
                self._abstract_label.configure(text=f"摘要: {data.get('abstract')[:200]}..." if len(data.get('abstract', '')) > 200 else f"摘要: {data.get('abstract')}")
            else:
                self._abstract_label = ctk.CTkLabel(
                    self._content, text=f"摘要: {data.get('abstract')[:200]}..." if len(data.get('abstract', '')) > 200 else f"摘要: {data.get('abstract')}",
                    font=ctk.CTkFont(size=11),
                    text_color="#aaaaaa",
                    anchor="w",
                    wraplength=500
                )
                self._abstract_label.pack(anchor="w", padx=10, pady=(5, 10), fill="x")
        else:
            if self._abstract_label:
                self._abstract_label.destroy()
                self._abstract_label = None
            if not self._spacer:
                self._spacer = ctk.CTkFrame(self._content, height=5, fg_color="transparent")
                self._spacer.pack(fill="x")
        
        # 更新状态
        self._paper = paper
        self._segment = None
    
    def is_loading(self):
        """是否处于加载状态"""
        return self._paper is None and self._segment is not None
    
    def destroy(self):
        """销毁卡片"""
        if self._card:
            self._card.destroy()
    
    def get_card(self):
        return self._card


class ResultDialog:
    """结果显示对话框"""
    
    def __init__(self, parent):
        self.parent = parent
        self.dialog = None
        self._captured_text = ""
        self._is_always_on_top = True
        self._follow_mouse = True
        self._scroll_frame = None
        self._title_label = None
        self._captured_text_widget = None
        self._loading_cards = {}  # {index: Card}
        self._mouse_x = None
        self._mouse_y = None
        self._drag_data = {"x": 0, "y": 0}
    
    def set_always_on_top(self, enabled):
        self._is_always_on_top = enabled
        if self.dialog:
            self.dialog.attributes('-topmost', enabled)
    
    def set_follow_mouse(self, enabled):
        self._follow_mouse = enabled
    
    def show(self, papers, captured_text=""):
        """显示结果"""
        self._captured_text = captured_text
        
        if self.dialog is not None:
            try:
                if self.dialog.winfo_exists():
                    self._update_content(papers)
                    self._bring_to_front()
                    return
            except Exception:
                pass
        
        self._create_dialog(papers)
    
    def _get_mouse_position(self):
        """获取鼠标位置"""
        if self._follow_mouse:
            try:
                import pyautogui
                return pyautogui.position()
            except Exception:
                return None
        return None
    
    def _init_dialog_base(self, title_text):
        """初始化对话框基础结构"""
        self.dialog = ctk.CTkToplevel(self.parent)
        self.dialog.overrideredirect(True)
        
        mouse_pos = self._get_mouse_position()
        if mouse_pos:
            self._mouse_x, self._mouse_y = mouse_pos
        else:
            self._mouse_x = None
            self._mouse_y = None
        
        self.dialog.geometry(f"{WINDOW_WIDTH}x{WINDOW_MIN_HEIGHT}")
        self.dialog.attributes('-topmost', True)
        self.dialog.attributes('-alpha', 0.95)
        
        frame = ctk.CTkFrame(self.dialog, fg_color="transparent")
        frame.pack(fill="both", expand=True)
        
        # 标题栏
        header_frame = ctk.CTkFrame(frame, fg_color="transparent", cursor="fleur", height=30)
        header_frame.pack(fill="x", pady=(3, 0), padx=10)
        header_frame.pack_propagate(False)
        
        header_frame.bind("<Button-1>", self._on_drag_start)
        header_frame.bind("<B1-Motion>", self._on_drag_motion)
        
        self._title_label = ctk.CTkLabel(
            header_frame, text=title_text,
            font=ctk.CTkFont(weight="bold", size=12),
            cursor="fleur"
        )
        self._title_label.pack(side="left", padx=5, pady=3)
        self._title_label.bind("<Button-1>", self._on_drag_start)
        self._title_label.bind("<B1-Motion>", self._on_drag_motion)
        
        # 右上角按钮
        btn_frame = ctk.CTkFrame(header_frame, fg_color="transparent")
        btn_frame.pack(side="right")
        
        self._pin_button = self._create_header_button(
            btn_frame, "pin", size=16,
            command=self._toggle_always_on_top,
            fg_color="#1f6aa5", hover_color="#2a7ab5",
            padx=(3, 0)
        )
        
        close_button = self._create_header_button(
            btn_frame, "close", size=16,
            command=self._close_dialog,
            fg_color="#c42b1c", hover_color="#d73a2f",
            padx=(3, 0)
        )
        
        # 滚动区域
        self._scroll_frame = ctk.CTkScrollableFrame(
            frame,
            scrollbar_button_color="#555555",
            scrollbar_button_hover_color="#777777"
        )
        self._scroll_frame.pack(fill="both", expand=True, pady=10)
        
        self.dialog.bind('<Escape>', lambda e: self._close_dialog())
        self.dialog.protocol("WM_DELETE_WINDOW", self._close_dialog)
        self.dialog.focus_force()
    
    def _create_dialog(self, papers):
        """创建对话框"""
        self._init_dialog_base(f"找到 {len(papers)} 篇文献")
        
        if self._captured_text:
            self._create_captured_text_card()
        
        for i, paper in enumerate(papers):
            Card(self._scroll_frame, i, paper=paper)
        
        self._finish_dialog()
    
    def _finish_dialog(self):
        """完成对话框布局"""
        self.dialog.update_idletasks()
        content_height = self._scroll_frame.winfo_reqheight() + 80
        content_height = min(max(content_height, WINDOW_MIN_HEIGHT), WINDOW_MAX_HEIGHT)
        
        if self._mouse_x is not None and self._mouse_y is not None:
            self.dialog.geometry(f"{WINDOW_WIDTH}x{content_height}+{self._mouse_x + 20}+{self._mouse_y + 20}")
        else:
            self.dialog.geometry(f"{WINDOW_WIDTH}x{content_height}")
    
    def _create_captured_text_card(self):
        """创建捕获文本卡片"""
        card = ctk.CTkFrame(self._scroll_frame, fg_color="#1a3a5c")
        card.pack(fill="x", pady=5, padx=5)
        
        lines = min(max(self._captured_text.count('\n') + 1, 1), 10)
        height = lines * 20
        
        self._captured_text_widget = ctk.CTkTextbox(
            card, height=height, wrap="none",
            font=ctk.CTkFont(size=11),
            fg_color="#0d2137", text_color="white", border_width=0
        )
        self._captured_text_widget.pack(fill="x", expand=True, padx=10, pady=10)
        self._captured_text_widget.insert("1.0", self._captured_text)
        self._captured_text_widget.configure(state="disabled")
    
    def _update_content(self, papers):
        """更新窗口内容"""
        if self._title_label:
            self._title_label.configure(text=f"找到 {len(papers)} 篇文献")
        
        if self._scroll_frame:
            for widget in self._scroll_frame.winfo_children():
                widget.destroy()
            
            self._captured_text_widget = None
            self._loading_cards = {}
            
            if self._captured_text:
                self._create_captured_text_card()
            
            for i, paper in enumerate(papers):
                Card(self._scroll_frame, i, paper=paper)
            
            self._resize_window()
    
    def _resize_window(self):
        """更新窗口大小"""
        self.dialog.update_idletasks()
        content_height = self._scroll_frame.winfo_reqheight() + 80
        content_height = min(max(content_height, WINDOW_MIN_HEIGHT), WINDOW_MAX_HEIGHT)
        
        current_geometry = self.dialog.geometry()
        parts = current_geometry.split('+')
        if len(parts) >= 3:
            self.dialog.geometry(f"{WINDOW_WIDTH}x{content_height}+{parts[1]}+{parts[2]}")
        else:
            self.dialog.geometry(f"{WINDOW_WIDTH}x{content_height}")
    
    def _create_header_button(self, parent, icon_name, size=16, command=None, fg_color="#1f6aa5", hover_color="#2a7ab5", padx=(0, 0)):
        """创建标题栏按钮"""
        icon = load_icon(icon_name, size=size)
        btn = ctk.CTkButton(
            parent, image=icon, text="",
            width=30, height=22,
            command=command,
            fg_color=fg_color, hover_color=hover_color
        )
        btn.pack(side="left", padx=padx)
        return btn
    
    def _bring_to_front(self):
        if self.dialog:
            self.dialog.lift()
            self.dialog.focus_force()
    
    def _close_dialog(self):
        if self.dialog:
            try:
                self.dialog.destroy()
            except Exception:
                pass
            self.dialog = None
            self._scroll_frame = None
            self._title_label = None
            self._captured_text_widget = None
            self._loading_cards = {}
    
    # ========== 加载状态方法 ==========
    
    def show_loading_cards(self, segments, captured_text=""):
        """显示加载状态的卡片列表"""
        self._captured_text = captured_text
        self._loading_cards = {}
        
        if self.dialog is not None:
            try:
                if self.dialog.winfo_exists():
                    self._create_loading_cards(segments)
                    return
            except Exception:
                pass
        
        self._init_dialog_base(f"正在解析 {len(segments)} 篇文献")
        
        if self._captured_text:
            self._create_captured_text_card()
        
        for i, segment in enumerate(segments):
            self._loading_cards[i] = Card(self._scroll_frame, i, segment=segment)
        
        self._finish_dialog()
    
    def _create_loading_cards(self, segments):
        """创建加载状态的卡片"""
        self._loading_cards = {}
        
        if self._scroll_frame:
            for widget in self._scroll_frame.winfo_children():
                widget.destroy()
        
        self._captured_text_widget = None
        
        if self._captured_text:
            self._create_captured_text_card()
        
        for i, segment in enumerate(segments):
            self._loading_cards[i] = Card(self._scroll_frame, i, segment=segment)
        
        if self._title_label:
            self._title_label.configure(text=f"正在解析 {len(segments)} 篇文献")
        
        self._resize_window()
        self._bring_to_front()
    
    def update_card_with_paper(self, index, paper):
        """更新单个卡片的内容"""
        if index not in self._loading_cards:
            logger.warning(f"卡片 {index} 不存在")
            return
        
        callbacks = {
            'download': self._on_download_paper,
            'open_url': self._on_open_paper_url
        }
        self._loading_cards[index].update(paper, callbacks)
        
        del self._loading_cards[index]
        
        if not self._loading_cards and self._title_label:
            self._title_label.configure(text="解析完成")
    
    # ========== 事件处理方法 ==========
    
    def _toggle_always_on_top(self):
        self._is_always_on_top = not self._is_always_on_top
        self.dialog.attributes('-topmost', self._is_always_on_top)
        self._pin_button.configure(fg_color="#1f6aa5" if self._is_always_on_top else "#2b2b2b")
    
    def _on_drag_start(self, event):
        self._drag_data["x"] = event.x
        self._drag_data["y"] = event.y
    
    def _on_drag_motion(self, event):
        delta_x = event.x - self._drag_data["x"]
        delta_y = event.y - self._drag_data["y"]
        new_x = self.dialog.winfo_x() + delta_x
        new_y = self.dialog.winfo_y() + delta_y
        self.dialog.geometry(f"+{new_x}+{new_y}")
    
    def _on_download_paper(self, paper):
        logger.info(f"下载文献: {getattr(paper, 'title', '未知')}")

    def get_doi_url(self, paper):
        doi = getattr(paper, 'doi', None)
        return f"https://doi.org/{doi}" if doi else None
    
    def _on_open_paper_url(self, paper):
        
        doi_url = self.get_doi_url(paper) 
        if not doi_url:
            doi_url = getattr(paper, 'url', None)
        
        if doi_url:
            title = getattr(paper, 'title', 'unknown title')
            logger.info(f"打开文献网页: {title} -> {doi_url}")
            try:
                webbrowser.open(doi_url)
            except Exception as e:
                logger.error(f"打开网页失败: {e}")
        else:
            logger.info(f"文献没有 URL: {title}")