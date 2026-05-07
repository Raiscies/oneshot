"""
OneShot - 主入口文件
一键直达文献：基于快捷键的论文文献快速下载工具
"""
import asyncio
import sys
import logging
import threading
import argparse
import signal
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent))

# 配置日志 - 默认 INFO 级别，关闭第三方库的 DEBUG 日志
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# 关闭 PIL 的 DEBUG 日志
logging.getLogger('PIL.PngImagePlugin').setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

# 默认存储目录
DEFAULT_STORAGE_DIR = Path(__file__).parent.parent / 'papers'


class OneShotApp:
    """OneShot 应用主类"""
    
    def __init__(self, debug_mode=False):
        """
        初始化应用
        
        Args:
            debug_mode: 是否启用调试模式
        """
        self.debug_mode = debug_mode
        
        # 服务实例
        self._citation_parser = None
        self._search_service = None
        self._download_service = None
        self._keyboard_service = None
        self._selection_service = None
        self._tray_service = None
        self._config_service = None
        
        # UI 组件
        self._app = None
        self._result_dialog = None
        self._main_window = None
        
        # 配置
        self._hotkey_display = None
        self._storage_path = None
    
    def _init_services(self):
        """初始化所有服务"""
        from oneshot.services import (
            CitationParser,
            SearchService,
            DownloadService,
            KeyboardService,
            SelectionService,
            TrayService,
            ConfigService,
        )
        
        self._config_service = ConfigService()
        self._citation_parser = CitationParser()
        self._search_service = SearchService()
        self._download_service = DownloadService()
        self._keyboard_service = KeyboardService()
        self._selection_service = SelectionService()
        self._tray_service = TrayService()
        
        # 设置存储目录
        storage_config = self._config_service.storage
        self._storage_path = storage_config.get("path") or str(DEFAULT_STORAGE_DIR)
        if self._storage_path == str(DEFAULT_STORAGE_DIR):
            DEFAULT_STORAGE_DIR.mkdir(parents=True, exist_ok=True)
        self._download_service.storage_dir = Path(self._storage_path)
    
    def _get_hotkey_info(self):
        """获取快捷键信息"""
        hotkey_config = self._config_service.hotkey
        modifiers = set(hotkey_config.get("modifiers", ["ctrl"]))
        key = hotkey_config.get("key", "q")
        return modifiers, key
    
    def _create_hotkey_display(self, modifiers, key):
        """创建快捷键显示字符串"""
        self._hotkey_display = "+".join(sorted(m.upper() for m in modifiers)) + "+" + key.upper()
    
    def _on_hotkey_pressed(self):
        """快捷键回调"""
        logger.info("快捷键触发，开始处理...")
        
        citation = self._selection_service.get_text()
        if not citation:
            logger.warning("选中文本为空")
            self._tray_service.notify("OneShot", "未检测到选中文本")
            return
        
        logger.debug(f"获取到文本内容: {citation[:50]}...")
        
        # 分割引用文本
        segments = self._citation_parser.split_citations(citation)
        if not segments:
            logger.warning("未能分割出任何引用")
            return
        
        logger.info(f"分割出 {len(segments)} 个引用")
        
        # 立即显示加载状态的卡片
        self._app.after(0, lambda: self._result_dialog.show_loading_cards(segments, captured_text=citation))
        
        # 并行解析并搜索
        for i, segment in enumerate(segments):
            threading.Thread(
                target=self._parse_and_search,
                args=(i, segment),
                daemon=True
            ).start()
    
    def _parse_and_search(self, index, segment):
        """解析单个分段并搜索补充信息"""
        papers = self._citation_parser.parse(segment, debug=self.debug_mode)
        if not papers:
            logger.warning(f"分段 {index + 1} 解析失败: {segment[:50]}...")
            # self._app.after(0, lambda: self._result_dialog.update_card_with_paper(index, None))
            return

        paper = papers[0]
        
        async def search_and_update():
            # try:
            results = await self._search_service.search(paper)
            if not results:
                logger.warning(f"分段 {index + 1} 未找到匹配的文献: {paper.title[:50] if paper.title else '未知'}")
                return

            # 使用 Paper.merge() 合并搜索结果
            # logger.debug(f"卡片 {index} 已合并搜索结果")
            paper.merge(results[0].paper)
            self._app.after(0, lambda: self._result_dialog.update_card_with_paper(index, paper))
            # except Exception as e:
            #     logger.error(f"搜索异常: {e}")
            #     self._app.after(0, lambda: self._result_dialog.update_card_with_paper(index, paper))
        
        asyncio.run(search_and_update())
    
    def _setup_ui(self):
        """设置 UI"""
        import customtkinter as ctk
        from oneshot.ui import MainWindow, ResultDialog
        
        # 设置外观
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        
        # 创建主窗口
        self._app = ctk.CTk(fg_color="#1a1a1a")
        
        # 创建结果对话框
        self._result_dialog = ResultDialog(self._app)
        
        # 服务字典
        services = {
            'keyboard': self._keyboard_service,
            'tray': self._tray_service,
            'ui': self._result_dialog,
            'config': self._config_service,
        }
        
        # 创建主窗口
        self._main_window = MainWindow(self._app, services, self._storage_path, self.debug_mode)
    
    def _setup_tray(self):
        """设置托盘"""
        def show_window():
            self._main_window.show()
        
        def quit_app():
            self._config_service.save()
            try:
                self._app.after(0, self._app.destroy)
            except Exception:
                pass
            self._keyboard_service.remove_hotkey()
            threading.Thread(
                target=lambda: (threading.Event().wait(0.2), self._tray_service.stop()),
                daemon=True
            ).start()
        
        self._tray_service.set_callbacks(
            on_left_click=show_window,
            on_menu_quit=quit_app
        )
        self._tray_service.start()
        self._tray_service.notify("OneShot", f"程序已启动，按 {self._hotkey_display} 触发")
    
    def _setup_hotkey(self):
        """设置快捷键"""
        modifiers, key = self._get_hotkey_info()
        self._keyboard_service.set_hotkey(self._on_hotkey_pressed, modifiers, key)
    
    def _apply_window_config(self):
        """应用窗口配置"""
        window_config = self._config_service.window
        self._result_dialog.set_always_on_top(window_config.get("always_on_top", True))
        self._result_dialog.set_follow_mouse(window_config.get("follow_mouse", True))
    
    def _cleanup(self):
        """清理资源"""
        logger.info("正在清理资源...")
        
        # 保存配置
        if self._config_service:
            try:
                self._config_service.save()
                logger.info("配置已保存")
            except Exception as e:
                logger.error(f"保存配置失败: {e}")
        
        # 停止键盘服务
        if self._keyboard_service:
            try:
                self._keyboard_service.stop()
                logger.info("键盘服务已停止")
            except Exception as e:
                logger.error(f"停止键盘服务失败: {e}")
        
        # 停止托盘服务
        if self._tray_service:
            try:
                self._tray_service.stop()
                logger.info("托盘服务已停止")
            except Exception as e:
                logger.error(f"停止托盘服务失败: {e}")
        
        # 销毁主窗口
        if self._app:
            try:
                self._app.destroy()
                logger.info("主窗口已销毁")
            except Exception as e:
                logger.error(f"销毁主窗口失败: {e}")
        
        logger.info("程序已退出")
    
    def run(self):
        """运行应用"""
        # 初始化服务
        self._init_services()
        
        # 获取快捷键信息
        modifiers, key = self._get_hotkey_info()
        self._create_hotkey_display(modifiers, key)
        
        logger.info("=" * 50)
        logger.info("OneShot - 一键直达文献")
        logger.info(f"调试模式: {'启用' if self.debug_mode else '禁用'}")
        logger.info(f"快捷键: {self._hotkey_display}")
        logger.info("=" * 50)
        
        # 设置 UI
        self._setup_ui()
        
        # 设置托盘
        self._setup_tray()
        
        # 设置快捷键
        self._setup_hotkey()
        
        # 应用窗口配置
        self._apply_window_config()
        
        # 设置关闭回调
        self._app.protocol("WM_DELETE_WINDOW", self._main_window.on_closing)
        
        # 运行主循环
        self._app.mainloop()


def cleanup_and_exit(signum=None, frame=None):
    """全局清理函数（供信号处理调用）"""
    if hasattr(cleanup_and_exit, '_app'):
        cleanup_and_exit._app._cleanup()
    sys.exit(0)


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='OneShot - 一键直达文献')
    parser.add_argument('--debug', action='store_true', help='启用调试模式')
    args = parser.parse_args()
    
    signal.signal(signal.SIGINT, cleanup_and_exit)
    signal.signal(signal.SIGTERM, cleanup_and_exit)
    
    app = OneShotApp(debug_mode=args.debug)
    cleanup_and_exit._app = app
    
    try:
        app.run()
    except Exception as e:
        logger.error(f"应用运行异常: {e}")
        raise


if __name__ == '__main__':
    main()