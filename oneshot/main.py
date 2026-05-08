"""
OneShot - 主入口文件
一键直达文献：基于快捷键的论文文献快速下载工具

架构：
- 后端服务 (KeyboardService, TrayService) 保留 Python 实现
- API 层使用 FastAPI
- 前端使用 Vue 3 + Vuetify (通过 pywebview 加载)
- 前端支持两种模式：
  1. 开发模式：启动 Vite 开发服务器
  2. 生产模式：加载预构建的 dist/ 目录
"""

# 添加项目根目录到路径（必须在其他 imports 之前）
# 支持两种运行方式：
# 1. python -m oneshot.main (推荐)
# 2. python oneshot/main.py
# import sys
from pathlib import Path
# project_root = Path(__file__).parent.parent
# sys.path.insert(0, str(project_root))

import asyncio
import logging
import threading
import argparse
import time
import webview
import uvicorn
import json
import os

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
        # 使用本地构建文件
        logger.info(f"使用预构建前端: {FRONTEND_DIST_DIR}")
        return str(FRONTEND_DIST_DIR.absolute())
    else:
        # 使用开发服务器
        logger.info("使用 Vite 开发服务器")
        return f"http://localhost:{FRONTEND_PORT}"


# 全局结果数据，供前端获取
_current_search_result = {
    "papers": [],
    "captured_text": "",
    "message": "",
    "ready": False,
}


class Api:
    """pywebview JavaScript API"""
    
    def close(self):
        """关闭窗口"""
        logger.info("Closing window...")
        for window in webview.windows:
            try:
                window.destroy()
            except:
                pass
    
    def getSearchResult(self) -> str:
        """前端获取搜索结果"""
        global _current_search_result
        logger.info(f"返回搜索结果: {len(_current_search_result['papers'])} 篇")
        return json.dumps(_current_search_result)
    
    def isResultReady(self) -> bool:
        """检查结果是否就绪"""
        return _current_search_result.get("ready", False)
    
    def getFrontendUrl(self) -> str:
        """获取前端 URL"""
        return _get_frontend_url()


class OneShotApp:
    """OneShot 应用主类"""
    
    def __init__(self, debug_mode=False, force_dev=False):
        self.debug_mode = debug_mode
        self.force_dev = force_dev  # 强制使用开发服务器
        
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
        self._api_thread = None
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
        # # 直接调用搜索服务
        # threading.Thread(
        #     target=self._do_search,
        #     args=(citation,),
        #     daemon=True
        # ).start()
    
    def _do_search(self, citation: str):
        """执行搜索并显示结果窗口"""
        global _current_search_result
        
        try:
            # 分割引用
            segments = self._citation_parser.split_citations(citation)
            if not segments:
                logger.warning("未能分割出引用")
                self._tray_service.notify("OneShot", "未能解析引用文本")
                return
            
            logger.info(f"分割出 {len(segments)} 个引用")
            self._tray_service.notify("OneShot", f"正在解析 {len(segments)} 篇文献...")
            
            # 重置结果状态
            _current_search_result = {
                "papers": [],
                "captured_text": citation,
                "message": f"正在解析 {len(segments)} 篇文献...",
                "ready": False,
            }
            
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
            
            # 更新结果
            _current_search_result = {
                "papers": papers,
                "captured_text": citation,
                "message": f"找到 {len(papers)} 篇文献",
                "ready": True,
            }
            
            logger.info(f"搜索完成: {len(papers)} 篇文献")
            self._tray_service.notify("OneShot", f"找到 {len(papers)} 篇文献")
            
            # 创建结果窗口
            self._create_result_window()
            
        except Exception as e:
            logger.error(f"搜索失败: {e}")
            _current_search_result["message"] = f"搜索失败: {e}"
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
        def create_window_thread():
            try:
                # 构建结果页面的 URL 或文件路径
                frontend_url = _get_frontend_url()
                
                # 如果是本地文件路径，result.html 应该在同一目录
                if os.path.isabs(frontend_url) and os.path.isdir(frontend_url):
                    result_url = os.path.join(frontend_url, 'result.html')
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
                    always_on_top=True,
                )
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
    
    def _start_api_server(self):
        """启动 FastAPI 后端服务"""
        def run_api():
            uvicorn.run(
                "oneshot.api:app",
                host="0.0.0.0",
                port=8000,
                log_level="info",
            )
        
        self._api_thread = threading.Thread(target=run_api, daemon=True)
        self._api_thread.start()
        logger.info("FastAPI 服务已启动: http://localhost:8000")
        
        time.sleep(1)
    
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
                errors='replace',  # 忽略编码错误
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
    
    def _start_pywebview(self):
        """启动 pywebview 窗口"""
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
        
        # 创建主窗口
        window = webview.create_window(
            title='OneShot - 一键直达文献',
            url=frontend_url,
            width=400,
            height=500,
            min_size=(350, 400),
            resizable=True,
            frameless=True,
            js_api=Api(),
        )
        
        # 启动 pywebview（这会阻塞）
        webview.start(debug=self.debug_mode)
    
    def _cleanup(self):
        """清理资源"""
        logger.info("正在清理资源...")
        self._stop_event.set()
        
        if self._config_service:
            try:
                self._config_service.save()
            except Exception as e:
                logger.error(f"保存配置失败: {e}")
        
        if self._keyboard_service:
            try:
                self._keyboard_service.stop()
            except Exception as e:
                logger.error(f"停止键盘服务失败: {e}")
        
        if self._tray_service:
            try:
                self._tray_service.stop()
            except Exception as e:
                logger.error(f"停止托盘服务失败: {e}")
        
        logger.info("程序已退出")
    
    def run(self):
        """运行应用"""
        self._init_services()
        
        modifiers, key = self._get_hotkey_info()
        self._create_hotkey_display(modifiers, key)
        
        logger.info("=" * 50)
        logger.info("OneShot - 一键直达文献")
        logger.info(f"快捷键: {self._hotkey_display}")
        logger.info(f"前端模式: {'开发' if (self.force_dev or not FRONTEND_DIST_DIR.exists()) else '预构建'}")
        logger.info("=" * 50)
        
        # 启动 API 服务
        self._start_api_server()
        
        # 如果需要，启动前端开发服务器
        if self.force_dev or not FRONTEND_DIST_DIR.exists():
            self._start_frontend_dev_server()
        
        # 设置托盘
        self._setup_tray()
        
        # 设置快捷键
        self._setup_hotkey()
        
        # 启动 pywebview 窗口
        self._start_pywebview()
        
        # 清理
        self._cleanup()


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='OneShot - 一键直达文献')
    parser.add_argument('--debug', action='store_true', help='启用调试模式')
    parser.add_argument('--dev', action='store_true', help='强制使用 Vite 开发服务器')
    args = parser.parse_args()
    
    app = OneShotApp(debug_mode=args.debug, force_dev=args.dev)
    
    try:
        app.run()
    except KeyboardInterrupt:
        app._cleanup()


if __name__ == '__main__':
    main()