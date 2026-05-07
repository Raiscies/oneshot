"""
OneShot - 系统托盘服务
"""

import logging
import threading
from typing import Optional, Callable
from pathlib import Path
from PIL import Image, ImageDraw

logger = logging.getLogger(__name__)


class TrayService:
    """系统托盘服务"""
    
    def __init__(self, app_name: str = "OneShot"):
        """
        初始化托盘服务
        
        Args:
            app_name: 应用名称
        """
        self.app_name = app_name
        self._running = False
        self._tray = None
        self._menu_items = {}
        self._icon_path: Optional[Path] = None
        self._on_quit: Optional[Callable] = None
        self._on_show: Optional[Callable] = None
        self._on_left_click: Optional[Callable] = None
        self._thread: Optional[threading.Thread] = None
    
    def create_icon(self) -> Path:
        """创建应用图标"""
        # 创建一个简单的图标
        size = 64
        image = Image.new('RGB', (size, size), color=(66, 133, 244))  # Google蓝色
        draw = ImageDraw.Draw(image)
        
        # 绘制书本图标轮廓
        margin = 12
        draw.rectangle([margin, margin, size - margin, size - margin], outline='white', width=3)
        draw.line([size//2, margin, size//2, size - margin], fill='white', width=2)
        
        # 保存图标
        icon_dir = Path.home() / ".oneshot"
        icon_dir.mkdir(exist_ok=True)
        self._icon_path = icon_dir / "icon.png"
        image.save(self._icon_path)
        
        return self._icon_path
    
    def setup(
        self,
        on_quit: Optional[Callable] = None,
        on_show: Optional[Callable] = None
    ):
        """
        设置托盘
        
        Args:
            on_quit: 退出回调
            on_show: 显示主窗口回调
        """
        self._on_quit = on_quit
        self._on_show = on_show
        
        if not self._icon_path:
            self.create_icon()
    
    def set_callbacks(
        self,
        on_left_click: Optional[Callable] = None,
        on_menu_quit: Optional[Callable] = None
    ):
        """设置回调函数"""
        self._on_left_click = on_left_click
        self._on_show = on_left_click  # 左键点击也显示窗口
        self._on_quit = on_menu_quit
    
    def start(self):
        """在新线程中启动托盘"""
        self._thread = threading.Thread(target=self.run, daemon=True)
        self._thread.start()
    
    def run(self):
        """运行托盘"""
        try:
            import pystray
        except ImportError:
            logger.error("pystray未安装，请运行: pip install pystray")
            return
        
        if not self._icon_path or not self._icon_path.exists():
            self.create_icon()
        
        # 创建菜单
        menu = pystray.Menu(
            pystray.MenuItem("显示主界面", self._handle_show, default=True),
            pystray.MenuItem("关于", self._handle_about),
            pystray.MenuItem("退出", self._handle_quit)
        )
        
        # 创建托盘图标 - 使用新API
        img = Image.open(self._icon_path)
        self._tray = pystray.Icon(
            name=self.app_name,
            icon=img,
            title=self.app_name,
            menu=menu
        )
        
        self._running = True
        logger.info("系统托盘已启动")
        
        # 运行托盘
        self._tray.run()
    
    def stop(self):
        """停止托盘"""
        if self._tray:
            self._tray.stop()
            self._running = False
            logger.info("系统托盘已停止")
    
    def notify(self, title: str, message: str):
        """
        发送通知
        
        Args:
            title: 通知标题
            message: 通知内容
        """
        if self._tray:
            self._tray.notify(message, title)
    
    def _handle_show(self, icon=None, item=None):
        """处理显示"""
        if self._on_show:
            self._on_show()
    
    def _handle_about(self, icon=None, item=None):
        """处理关于"""
        self.notify(
            "OneShot",
            "一键直达文献 v1.0\n基于快捷键的论文文献快速下载工具"
        )
    
    def _handle_quit(self, icon=None, item=None):
        """处理退出"""
        # 延迟停止托盘，让主窗口有时间清理
        if self._on_quit:
            self._on_quit()
        # 延迟停止托盘，避免与 Tkinter 销毁冲突
        import threading
        threading.Thread(target=lambda: (threading.Event().wait(0.1), self.stop()), daemon=True).start()
