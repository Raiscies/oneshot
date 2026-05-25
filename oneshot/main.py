"""
OneShot - 主入口文件
一键直达文献：基于快捷键的论文文献快速下载工具

架构：
- 后端服务 (KeyboardService, TrayService) 保留 Python 实现
- API 层使用 pywebview JS API
- 前端使用 Vue 3 + Vuetify (通过 pywebview 加载)
- 前端支持两种模式：
  1. 开发模式：启动 Vite 开发服务器
  2. 生产模式：加载预构建的 dist/ 目录
"""

from pathlib import Path

import asyncio
import logging
import os
import signal
import sys
import threading
import argparse
import time
import json
import webview

from oneshot.services import (
    KeyboardService,
    SelectionService,
    TrayService,
    ConfigService,
    CitationParser,
    SearchService
)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logging.getLogger('PIL.PngImagePlugin').setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

DEFAULT_STORAGE_DIR = Path(__file__).parent.parent / 'papers'
FRONTEND_DIR = Path(__file__).parent.parent / 'frontend'
FRONTEND_DIST_DIR = FRONTEND_DIR / 'dist'
FRONTEND_PORT = 5173


def _get_frontend_url() -> str:
    """获取前端 URL（优先使用本地文件）"""
    if FRONTEND_DIST_DIR.exists() and (FRONTEND_DIST_DIR / 'index.html').exists():
        # 使用本地构建文件（必须指向具体的 index.html，不能只是目录）
        logger.info(f"使用预构建前端: {FRONTEND_DIST_DIR}")
        return str((FRONTEND_DIST_DIR / 'index.html').absolute())
    else:
        # 使用开发服务器
        logger.info("使用 Vite 开发服务器")
        return f"http://localhost:{FRONTEND_PORT}"


class Api:
    """pywebview JavaScript API - 用于前后端通信"""
    
    def __init__(self):
        self._result_data = None
        self._result_ready = threading.Event()
        self._result_window = None
        self._main_window = None
    
    def setResult(self, data: str):
        """设置搜索结果，供前端通过 evaluate_js 调用"""
        self._result_data = json.loads(data) if isinstance(data, str) else data
        self._result_ready.set()
        logger.info(f"结果已设置: {len(self._result_data.get('papers', []))} 篇")
    
    def getResult(self) -> str:
        """前端获取搜索结果"""
        if self._result_data:
            logger.info(f"返回搜索结果: {len(self._result_data.get('papers', []))} 篇")
            return json.dumps(self._result_data)
        return json.dumps({"papers": [], "ready": False})
    
    def isReady(self) -> bool:
        """检查结果是否就绪"""
        return self._result_ready.is_set()
    
    def clearResult(self):
        """清除结果"""
        self._result_data = None
        self._result_ready.clear()
        logger.info("结果已清除")
    
    def closeResultWindow(self):
        """关闭结果窗口（仅关闭窗口，后台继续运行）"""
        logger.info("关闭结果窗口")
        if self._result_window:
            try:
                self._result_window.destroy()
                self._result_window = None
            except Exception as e:
                logger.error(f"关闭窗口失败: {e}")
    
    def hideMainWindow(self):
        """隐藏主窗口（保留托盘运行）"""
        logger.info("隐藏主窗口")
        if self._main_window:
            try:
                self._main_window.hide()
            except Exception as e:
                logger.error(f"隐藏窗口失败: {e}")
    
    def moveWindow(self, x: int, y: int, window_type: str = "main"):
        """移动指定窗口到屏幕坐标 (x, y)
        
        Args:
            x: 目标屏幕 X 坐标
            y: 目标屏幕 Y 坐标
            window_type: 'main' 或 'result'，指定要移动哪个窗口
        """
        try:
            target = self._result_window if window_type == "result" else self._main_window
            if target:
                target.move(x, y)
        except Exception as e:
            logger.error(f"移动窗口失败: {e}")
    
    def setMainWindow(self, window):
        """设置主窗口引用"""
        self._main_window = window
    
    def setResultWindow(self, window):
        """设置结果窗口引用"""
        self._result_window = window


class OneShotApp:
    """OneShot 应用主类"""
    
    def __init__(self, debug_mode=False, force_dev=False):
        self.debug_mode = debug_mode
        self.force_dev = force_dev
        self._js_api = Api()
        
        # 根据 debug 模式调整全局日志级别
        if debug_mode:
            logging.getLogger().setLevel(logging.DEBUG)
            logging.getLogger('pywebview').setLevel(logging.DEBUG)
        
        # 始终抑制第三方库的 DEBUG 日志
        logging.getLogger('PIL').setLevel(logging.WARNING)
        logging.getLogger('urllib3').setLevel(logging.WARNING)
        logging.getLogger('asyncio').setLevel(logging.WARNING)
        logging.getLogger('httpcore').setLevel(logging.WARNING)
        
        # 服务实例
        self._keyboard_service = None
        self._tray_service = None
        self._selection_service = None
        self._config_service = None
        self._citation_parser = None
        self._search_service = None
        
        # 配置
        self._hotkey_display = None
        
        # 线程
        self._frontend_thread = None
        self._stop_event = threading.Event()
    
    def _init_services(self):
        """初始化所有服务"""
        self._config_service = ConfigService()
        self._keyboard_service = KeyboardService()
        self._selection_service = SelectionService()
        self._tray_service = TrayService()
        self._citation_parser = CitationParser()
        self._search_service = SearchService()
        
        # 初始化存储目录
        storage_config = self._config_service.storage
        storage_path = storage_config.get("path") or str(DEFAULT_STORAGE_DIR)
        if storage_path == str(DEFAULT_STORAGE_DIR):
            DEFAULT_STORAGE_DIR.mkdir(parents=True, exist_ok=True)
    
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
        """快捷键回调 - 触发搜索"""
        logger.info("快捷键触发，开始处理...")
        
        citation = self._selection_service.get_text()
        if not citation:
            logger.warning("选中文本为空")
            self._tray_service.notify("OneShot", "未检测到选中文本")
            return
        
        logger.debug(f"获取到文本内容: {citation[:50]}...")
        
        self._do_search(citation)
    
    def _do_search(self, citation: str):
        """执行搜索并显示结果窗口"""
        try:
            # 分割引用
            segments = self._citation_parser.split_citations(citation)
            if not segments:
                logger.warning("未能分割出引用")
                self._tray_service.notify("OneShot", "未能解析引用文本")
                return
            
            logger.info(f"分割出 {len(segments)} 个引用")
            self._tray_service.notify("OneShot", f"正在解析 {len(segments)} 篇文献...")
            
            # 解析并搜索
            papers = []
            for segment in segments:
                parsed = self._citation_parser.parse(segment, debug=self.debug_mode)
                if not parsed:
                    continue
                
                paper = parsed[0]
                # 搜索补充信息
                results = asyncio.run(self._search_service.search(paper))
                if results:
                    paper.merge(results[0].paper)
                papers.append(self._paper_to_dict(paper))
            
            logger.info(f"搜索完成: {len(papers)} 篇文献")
            self._tray_service.notify("OneShot", f"找到 {len(papers)} 篇文献")
            
            # 设置结果供前端获取
            result_data = {
                "papers": papers,
                "captured_text": citation,
                "message": f"找到 {len(papers)} 篇文献",
            }
            self._js_api.setResult(json.dumps(result_data))
            
            # 创建结果窗口
            self._create_result_window()
            
        except Exception as e:
            logger.error(f"搜索失败: {e}")
            self._tray_service.notify("OneShot", f"搜索失败: {e}")
    
    def _paper_to_dict(self, paper) -> dict:
        """将 Paper 对象转换为字典"""
        return {
            "title": paper.title or "未知标题",
            "authors": paper.authors or [],
            "year": paper.year,
            "abstract": paper.abstract,
            "ccf_rank": paper.ccf_rank,
            "doi": paper.doi,
            "url": paper.url,
            "citation_number": paper.citation_number,
            "citations": getattr(paper, 'citations', None),
        }
    
    def _create_result_window(self):
        """创建结果窗口"""
        # 先关闭旧窗口（如果存在）
        if self._js_api._result_window:
            try:
                self._js_api._result_window.destroy()
                self._js_api._result_window = None
            except Exception as e:
                logger.debug(f"关闭旧窗口失败: {e}")
        
        def create_window_thread():
            try:
                frontend_url = _get_frontend_url()
                result_url = None
                # 如果是本地文件路径，result.html 应该在同一目录
                if os.path.isabs(frontend_url):
                    result_url = str(FRONTEND_DIST_DIR / 'result.html')
                else:
                    result_url = frontend_url.replace('index.html', 'result.html')
                
                window = webview.create_window(
                    title='搜索结果 - OneShot',
                    url=result_url,
                    width=550,
                    height=600,
                    min_size=(400, 300),
                    resizable=True,
                    frameless=True,
                    on_top=True,
                    js_api=self._js_api,
                )
                # 保存窗口引用
                self._js_api._result_window = window
                logger.info("结果窗口已创建")
            except Exception as e:
                logger.error(f"创建结果窗口失败: {e}")
        
        thread = threading.Thread(target=create_window_thread, daemon=True)
        thread.start()
    
    def _setup_hotkey(self):
        """设置快捷键"""
        modifiers, key = self._get_hotkey_info()
        self._keyboard_service.set_hotkey(self._on_hotkey_pressed, modifiers, key)
    
    def _setup_tray(self):
        """设置托盘"""
        self._tray_service.set_callbacks(
            on_left_click=self._show_main_window,
            on_menu_quit=self._cleanup
        )
        self._tray_service.start()
        self._tray_service.notify("OneShot", f"程序已启动，按 {self._hotkey_display} 触发")
    
    def _show_main_window(self):
        """显示主窗口"""
        for window in webview.windows:
            try:
                window.show()
                window.focus()
                return
            except:
                pass
    
    def _start_frontend_dev_server(self):
        """启动 Vite 开发服务器"""
        import subprocess
        
        def run_frontend():
            process = subprocess.Popen(
                ["npm", "run", "dev"],
                cwd=str(FRONTEND_DIR),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                shell=True,
                encoding='utf-8',
                errors='replace',
            )
            
            try:
                for line in process.stdout:
                    print(f"[Vite] {line}", end="")
            except Exception as e:
                logger.debug(f"Vite 进程输出结束: {e}")
        
        self._frontend_thread = threading.Thread(target=run_frontend, daemon=True)
        self._frontend_thread.start()
        logger.info("前端开发服务器启动中...")
        
        # 等待服务就绪
        for _ in range(30):
            time.sleep(1)
            try:
                import urllib.request
                urllib.request.urlopen(f"http://localhost:{FRONTEND_PORT}")
                logger.info("前端开发服务器已就绪")
                break
            except:
                continue
    
    def _prepare_webview(self) -> webview.Window:
        """准备 pywebview 窗口（获取 URL、等待服务、创建窗口，不阻塞）"""
        frontend_url = _get_frontend_url()
        
        # 如果使用开发服务器，等待其就绪
        if not os.path.isabs(frontend_url):
            logger.info("等待前端服务...")
            for _ in range(30):
                time.sleep(1)
                try:
                    import urllib.request
                    urllib.request.urlopen(frontend_url)
                    logger.info("前端服务已就绪")
                    break
                except:
                    continue
        
        # 创建主窗口（不阻塞，不调用 start）
        window = webview.create_window(
            title='OneShot - 一键直达文献',
            url=frontend_url,
            width=400,
            height=500,
            min_size=(350, 400),
            resizable=True,
            frameless=True,
            js_api=self._js_api,
        )
        self._js_api.setMainWindow(window)
        logger.info("主窗口已创建")
        return window
    
    def _event_monitor(self):
        """后台事件监控线程：检测键盘进程死亡、GUI 退出等，触发清理"""
        while not self._stop_event.is_set():
            if (self._keyboard_service
                    and not self._keyboard_service.is_alive
                    and not self._stop_event.is_set()):
                logger.info("键盘监听进程意外退出，触发清理...")
                self._cleanup()
                break
            time.sleep(0.5)
    
    def _cleanup(self):
        """清理所有资源并退出程序
        
        此方法可安全地多次调用（幂等），支持两种退出路径：
        1. 托盘菜单"退出" → _cleanup() → 销毁窗口 → webview.start() 返回
        2. Ctrl+C → KeyboardInterrupt → _cleanup()
        """
        # 防止重复清理
        if self._stop_event.is_set():
            logger.debug("清理已在进行中，跳过")
            return

        logger.info("正在清理资源...")
        self._stop_event.set()
        
        # 1. 停止键盘监听进程
        if self._keyboard_service:
            try:
                self._keyboard_service.stop()
                logger.info("键盘监听已停止")
            except Exception as e:
                logger.error(f"停止键盘服务失败: {e}")
        
        # 2. 保存配置
        if self._config_service:
            try:
                self._config_service.save()
                logger.info("配置已保存")
            except Exception as e:
                logger.error(f"保存配置失败: {e}")
        
        # 3. 停止托盘
        if self._tray_service:
            try:
                self._tray_service.stop()
                logger.info("系统托盘已停止")
            except Exception as e:
                logger.error(f"停止托盘服务失败: {e}")
        
        # 4. 销毁所有 webview 窗口（这会触发 webview.start() 返回）
        try:
            windows_to_close = list(webview.windows)
            for w in windows_to_close:
                try:
                    w.destroy()
                except Exception:
                    pass
            logger.info("所有窗口已关闭")
        except Exception as e:
            logger.error(f"关闭窗口失败: {e}")
        
        # 5. 停止前端开发服务器（如果启动了的话）
        if self._frontend_thread and self._frontend_thread.is_alive():
            logger.info("前端开发服务器已随主进程退出")
        
        logger.info("程序已退出")
    
    def run(self):
        """运行应用 - 主线程跑 GUI，后台线程做事件监控"""
        self._init_services()
        
        modifiers, key = self._get_hotkey_info()
        self._create_hotkey_display(modifiers, key)
        
        logger.info("=" * 50)
        logger.info("OneShot - 一键直达文献")
        logger.info(f"快捷键: {self._hotkey_display}")
        logger.info(f"前端模式: {'开发' if (self.force_dev or not FRONTEND_DIST_DIR.exists()) else '预构建'}")
        logger.info("=" * 50)
        
        # 启动前端开发服务器（如需要）
        if self.force_dev or not FRONTEND_DIST_DIR.exists():
            self._start_frontend_dev_server()
        
        # 创建 pywebview 窗口（准备阶段，不阻塞）
        self._prepare_webview()
        
        # 设置托盘
        self._setup_tray()
        
        # 设置快捷键
        self._setup_hotkey()
        
        # 启动后台事件监控线程（检测键盘进程死亡 / Ctrl+C）
        threading.Thread(target=self._event_monitor, name="event-monitor", daemon=True).start()
        
        # ============================================================
        # 主线程：运行 pywebview GUI 事件循环（阻塞）
        # 当 _cleanup() 被调用时，窗口被销毁，start() 自动返回
        # ============================================================
        try:
            webview.start(debug=self.debug_mode)
        except KeyboardInterrupt:
            pass  # 由 _event_monitor 触发 _cleanup()，这里安静吞掉
        finally:
            self._cleanup()


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='OneShot - 一键直达文献')
    parser.add_argument('--debug', action='store_true', help='启用调试模式')
    parser.add_argument('--dev', action='store_true', help='强制使用 Vite 开发服务器')
    args = parser.parse_args()
    
    app = OneShotApp(debug_mode=args.debug, force_dev=args.dev)
    app.run()


if __name__ == '__main__':
    main()