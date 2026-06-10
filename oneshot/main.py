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
from typing import Optional

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
import concurrent.futures


from oneshot.services import (
    KeyboardService,
    SelectionService,
    TrayService,
    ConfigService,
    CitationParser,
    SearchService,
    DownloadService,
)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logging.getLogger('PIL.PngImagePlugin').setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

DEFAULT_STORAGE_DIR = Path(__file__).parent.parent / 'papers'
FRONTEND_DIR = Path(__file__).parent / 'frontend'
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
        self._result_version = 0
        self._result_window = None
        self._main_window = None
        self._on_hotkey_change = None  # (modifiers: list, key: str) -> None
        self._hotkey_state = {"modifiers": ["ctrl"], "key": "q"}  # 缓存当前快捷键
        self._on_cf_bypass_save = None  # (host: str, port: int) -> None
        self._cf_bypass_state = {"host": "127.0.0.1", "port": 8000, "use_external": False}  # 缓存 CF bypass 配置
        self._on_start_download = None  # (doi: str) -> None
        self._download_states: dict[str, dict] = {}  # doi → {status, progress, path, error}
        self._on_auto_open_change = None  # (enabled: bool) -> None
        self._auto_open_pdf = False
        self._on_auto_download_change = None  # (count: int) -> None
        self._auto_download_count = 0
        self._on_naming_change = None  # (pattern: str) -> None
        self._naming_pattern = "{doi}.pdf"
        self._on_doi_fail_change = None  # (enabled: bool) -> None
        self._auto_open_doi_on_fail = False
        self._on_search_url_change = None  # (url: str) -> None
        self._search_engine_url = "https://scholar.google.com/scholar?q={query}"
        self._status_state = {"text": "", "progress": 0.0}
        self._on_show_result = None  # () -> None
        self._on_status_change = None  # (enabled: bool) -> None
        self._status_bar_enabled = True
        self._on_result_auto_change = None  # (enabled: bool) -> None
        self._result_auto_open = True
        self._on_check_exists = None  # (doi: str) -> Path | None
    
    def setResult(self, data: str):
        """设置搜索结果，递增版本号通知前端"""
        self._result_data = json.loads(data) if isinstance(data, str) else data
        self._result_ready.set()
        self._result_version += 1
    
    def updatePaper(self, index: int, paper_json: str):
        """增量更新单篇论文结果（索引从 0 开始），递增版本号"""
        if not self._result_data:
            return
        try:
            paper = json.loads(paper_json) if isinstance(paper_json, str) else paper_json
            papers = self._result_data.get("papers", [])
            if 0 <= index < len(papers):
                papers[index] = paper
            self._result_version += 1
            logger.debug(f"论文 #{index} 已更新 (v{self._result_version}): {paper.get('title', '?')[:40]}")
        except Exception as e:
            logger.error(f"更新论文失败: {e}")
    
    def getResult(self) -> str:
        """前端获取搜索结果"""
        if self._result_data:
            return json.dumps(self._result_data)
        return json.dumps({"papers": [], "ready": False})
    
    def getResultVersion(self) -> int:
        """前端轮询版本号，检测是否有新结果"""
        return self._result_version
    
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
    
    def toggleResultOnTop(self) -> bool:
        """切换结果窗口置顶状态，返回新状态"""

        if not self._result_window:
            return False
        try:
            current_state = self._result_window.on_top
            logger.debug(f"toggling, current state is {current_state}")
            self._result_window.on_top = not current_state 
            
            return self._result_window.on_top
        except Exception as e:
            logger.error(f"切换置顶失败: {e}")
            return False
    
    def setMainWindow(self, window):
        """设置主窗口引用"""
        self._main_window = window
    
    def setResultWindow(self, window):
        """设置结果窗口引用"""
        self._result_window = window
    
    def setHotkey(self, modifiers: list, key: str):
        """前端更改快捷键"""
        self._hotkey_state = {"modifiers": modifiers, "key": key}
        if self._on_hotkey_change:
            self._on_hotkey_change(modifiers, key)
    
    def getHotkey(self) -> str:
        """前端获取当前快捷键配置"""
        return json.dumps(self._hotkey_state)

    def setCfBypassConfig(self, host: str, port: int, use_external: bool = False):
        """前端更新 CloudflareBypass 配置（需手动重启生效）"""
        if self._on_cf_bypass_save:
            self._on_cf_bypass_save(host, port, use_external)

    def getCfBypassConfig(self) -> str:
        """前端获取当前 CloudflareBypass 配置"""
        return json.dumps(self._cf_bypass_state)

    def downloadByDoi(self, doi: str, meta_json: str = "{}"):
        """前端触发 DOI 下载（异步，通过 getDownloadProgress 轮询进度）"""
        if self._on_start_download:
            try:
                meta = json.loads(meta_json)
            except Exception:
                meta = {}
            self._on_start_download(doi, meta)

    def getDownloadProgress(self, doi: str) -> str:
        """前端轮询下载进度"""
        state = self._download_states.get(doi, {"status": "unknown", "progress": 0, "path": None, "error": None})
        return json.dumps(state)

    def checkPaperExists(self, doi: str) -> str:
        """检查文献 PDF 是否已存在"""
        if self._on_check_exists:
            path = self._on_check_exists(doi)
            if path:
                return json.dumps({"exists": True, "path": str(path)})
        return json.dumps({"exists": False})

    def openFile(self, path: str):
        """用系统默认程序打开文件"""
        import os
        path = os.path.abspath(path)
        os.startfile(path)

    def searchInBrowser(self, query: str):
        """用浏览器搜索文献"""
        import webbrowser
        from urllib.parse import quote
        url = self._search_engine_url.replace("{query}", quote(query, safe=''))
        webbrowser.open(url)

    def setSearchUrl(self, url: str):
        """前端更新搜索引擎 URL"""
        self._search_engine_url = url
        if self._on_search_url_change:
            self._on_search_url_change(url)

    def getSearchUrl(self) -> str:
        """前端获取搜索引擎 URL"""
        return self._search_engine_url

    def getStatus(self) -> str:
        """前端轮询状态浮窗内容"""
        return json.dumps(self._status_state)

    def showResultWindow(self):
        """前端点击浮窗后打开结果弹窗"""
        if self._on_show_result:
            self._on_show_result()

    def setStatusBarEnabled(self, enabled: bool):
        self._status_bar_enabled = enabled
        if self._on_status_change:
            self._on_status_change(enabled)

    def getStatusBarEnabled(self) -> bool:
        return self._status_bar_enabled

    def setResultAutoOpen(self, enabled: bool):
        self._result_auto_open = enabled
        if self._on_result_auto_change:
            self._on_result_auto_change(enabled)

    def getResultAutoOpen(self) -> bool:
        return self._result_auto_open

    def setAutoOpenPdf(self, enabled: bool):
        """前端更新下载后自动打开 PDF 设置"""
        self._auto_open_pdf = enabled
        if self._on_auto_open_change:
            self._on_auto_open_change(enabled)

    def getAutoOpenPdf(self) -> bool:
        """前端获取自动打开 PDF 设置"""
        return self._auto_open_pdf

    def setAutoDownloadCount(self, count: int):
        """前端更新自动下载阈值"""
        self._auto_download_count = count
        if self._on_auto_download_change:
            self._on_auto_download_change(count)

    def getAutoDownloadCount(self) -> int:
        """前端获取自动下载阈值"""
        return self._auto_download_count

    def setNamingPattern(self, pattern: str):
        if self._on_naming_change:
            self._on_naming_change(pattern)

    def getNamingPattern(self) -> str:
        return self._naming_pattern

    def setAutoOpenDoiOnFail(self, enabled: bool):
        self._auto_open_doi_on_fail = enabled
        if self._on_doi_fail_change:
            self._on_doi_fail_change(enabled)

    def getAutoOpenDoiOnFail(self) -> bool:
        return self._auto_open_doi_on_fail


class OneShotApp:
    """OneShot 应用主类"""
    
    def __init__(self, debug_mode=False, force_dev=False):
        self.debug_mode = debug_mode
        self.force_dev = force_dev
        self._js_api = Api()
        
        # Api 调用此回调来更新快捷键
        self._js_api._on_hotkey_change = self._apply_hotkey_change
        self._js_api._on_cf_bypass_save = self._save_cf_bypass_config
        self._js_api._on_start_download = self._start_download_by_doi
        self._js_api._on_auto_open_change = self._save_auto_open_pdf
        self._js_api._on_auto_download_change = self._save_auto_download_count
        self._js_api._on_naming_change = self._save_naming_pattern
        self._js_api._on_doi_fail_change = self._save_auto_open_doi_on_fail
        self._js_api._on_search_url_change = self._save_search_url
        self._js_api._on_show_result = self._show_result_window
        self._js_api._on_status_change = self._save_status_bar_enabled
        self._js_api._on_result_auto_change = self._save_result_auto_open
        
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
        self._current_executor = None  # 当前搜索的线程池，新搜索时取消旧任务
        self._search_id = 0  # 搜索 ID，防止旧搜索的过期更新
        self._download_service: Optional[DownloadService] = None
        self._status_window = None
    
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

        # 初始化下载服务（内含 CloudflareBypass 代理）
        cf_config = self._config_service.cf_bypass
        download_config = self._config_service.download
        self._download_service = DownloadService(
            storage_dir=storage_path,
            cf_host=cf_config.get("host", "127.0.0.1"),
            cf_port=cf_config.get("port", 8000),
            cf_external=cf_config.get("use_external", False),
            naming_pattern=download_config.get("naming_pattern", "{doi}.pdf"),
            delay_seconds=download_config.get("delay_seconds", 5),
        )
        self._js_api._cf_bypass_state = {
            "host": cf_config.get("host", "127.0.0.1"),
            "port": cf_config.get("port", 8000),
            "use_external": cf_config.get("use_external", False),
        }
        self._js_api._auto_open_pdf = download_config.get("auto_open_pdf", False)
        self._js_api._auto_download_count = download_config.get("auto_download_count", 0)
        self._js_api._naming_pattern = download_config.get("naming_pattern", "{doi}.pdf")
        self._js_api._on_check_exists = self._download_service.check_file_exists
        self._js_api._auto_open_doi_on_fail = download_config.get("auto_open_doi_on_fail", False)
        self._js_api._search_engine_url = self._config_service.search.get("engine_url", "https://scholar.google.com/scholar?q={query}")
        self._js_api._status_bar_enabled = self._config_service.status_bar.get("enabled", True)
        self._js_api._result_auto_open = self._config_service.result.get("auto_open", True)

        # 创建状态浮窗
        if self._js_api._status_bar_enabled:
            self._create_status_window()
    
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
        
        # 在新线程中执行搜索，避免阻塞键盘监听
        threading.Thread(target=self._do_search, args=(citation,), daemon=True).start()
    
    def _do_search(self, citation: str):
        """执行搜索 — 立即显示窗口，并行逐篇解析，增量更新"""
        # 取消正在进行的旧搜索
        self._search_id += 1
        my_id = self._search_id
        if self._current_executor:
            logger.info(f"取消旧搜索任务 (id<{my_id})")
            self._current_executor.shutdown(wait=False, cancel_futures=True)
            self._current_executor = None
        
        try:
            # 分割引用
            segments = self._citation_parser.split_citations(citation)
            if not segments:
                logger.warning("未能分割出引用")
                self._tray_service.notify("OneShot", "未能解析引用文本")
                return
            
            logger.info(f"搜索 #{my_id}: 分割出 {len(segments)} 个引用")
            self._tray_service.notify("OneShot", f"正在解析 {len(segments)} 篇文献...")
            self._update_status(f"正在解析 {len(segments)} 篇文献...", 0.0)

            # 1. 立即设置初始结果（仅捕获文本 + 占位卡片）
            placeholders = [{"_placeholder": True, "_index": i} for i in range(len(segments))]
            initial_data = {
                "papers": placeholders,
                "captured_text": citation,
                "message": f"正在解析 {len(segments)} 篇文献...",
            }
            self._js_api.setResult(json.dumps(initial_data))
            if self._js_api._result_auto_open:
                self._create_result_window()
            def parse_segment(idx: int, segment: tuple): # idx: internal index
                """解析单个分段，分两阶段推送"""
                # 检查是否已被取消
                if self._search_id != my_id:
                    return
                try:
                    # 阶段1：解析引用 (citation-index, citation-content)
                    paper = self._citation_parser.parse_single(citation=segment[1], citation_index=segment[0], debug=self.debug_mode)
                    if self._search_id != my_id:  # 解析期间被取消
                        return
                    if not paper:
                        self._js_api.updatePaper(idx, json.dumps({
                            "_placeholder": True, "_index": idx, "_error": "解析失败"
                        }))
                        return
                    
                    paper_dict = paper.to_dict()
                    paper_dict["_searching"] = True
                    self._js_api.updatePaper(idx, json.dumps(paper_dict))
                    
                    # 阶段2：联网搜索
                    if self._search_id != my_id:  # 推送后再次检查
                        return
                    results = asyncio.run(self._search_service.search(paper))
                    if self._search_id != my_id:  # 搜索期间被取消
                        return
                    if results:
                        # use result as the major paper data 
                        results[0].paper.merge(paper)
                        paper = results[0].paper

                    paper_dict = paper.to_dict()
                    
                    self._js_api.updatePaper(idx, json.dumps(paper_dict))
                    
                except Exception as e:
                    if self._search_id == my_id:
                        logger.error(f"解析分段 #{idx} 失败: {e}")
                        self._js_api.updatePaper(idx, json.dumps({
                            "_placeholder": True, "_index": idx, "_error": str(e)
                        }))
            
            self._current_executor = concurrent.futures.ThreadPoolExecutor(
                max_workers=min(len(segments), 4)
            )
            futures = [
                self._current_executor.submit(parse_segment, i, seg)
                for i, seg in enumerate(segments) 
            ]
            concurrent.futures.wait(futures)
            
            # 检查是否被新搜索取代
            if self._search_id != my_id:
                logger.debug(f"搜索 #{my_id} 已被新搜索取代，跳过收尾")
                return
            
            # 3. 全部完成后更新最终消息
            final_papers = self._js_api._result_data.get("papers", []) if self._js_api._result_data else []
            # 成功解析 = 非占位、非错误
            parsed_count = sum(1 for p in final_papers if not p.get("_placeholder") and not p.get("_error"))
            # 可下载 = 有 DOI
            downloadable = sum(1 for p in final_papers if not p.get("_placeholder") and not p.get("_error") and p.get("doi"))
            final_data = {
                "papers": final_papers,
                "captured_text": citation,
                "message": f"找到 {parsed_count} 篇文献",
            }
            self._js_api._result_data = final_data
            self._js_api._result_version += 1
            
            logger.info(f"搜索 #{my_id} 完成: {parsed_count}/{len(segments)} 篇")
            self._tray_service.notify("OneShot", f"找到 {parsed_count} 篇文献")
            self._update_status(f"找到 {parsed_count} 篇文献", 1.0)

            # 自动下载（仅计入有 DOI 的文献）
            threshold = self._js_api._auto_download_count
            if threshold > 0 and downloadable > 0 and downloadable <= threshold:
                for p in final_papers:
                    if not p.get("_placeholder") and not p.get("_error") and p.get("doi"):
                        logger.info(f"自动下载: {p['doi']}")
                        meta = {
                            "title": p.get("title", ""),
                            "authors": p.get("authors", []),
                            "pubdate": p.get("year", ""),
                        }
                        self._start_download_by_doi(p["doi"], meta)

        except Exception as e:
            if self._search_id == my_id:
                logger.error(f"搜索失败: {e}")
                self._tray_service.notify("OneShot", f"搜索失败: {e}")
        finally:
            if self._current_executor and self._search_id == my_id:
                self._current_executor.shutdown(wait=False)
                self._current_executor = None
    
    
    def _create_result_window(self):
        """确保结果窗口存在（已存在则跳过，不存在则创建）"""
        if self._js_api._result_window:
            logger.debug("结果窗口已存在，跳过创建")
            return
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
                    easy_drag=False,
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

    def _create_status_window(self):
        """创建状态浮窗（全局唯一，圆角小条，总是置顶）"""
        if self._status_window:
            try:
                self._status_window.show()
            except Exception:
                pass
            return

        def _create():
            try:
                frontend_url = _get_frontend_url()
                status_url = None
                if os.path.isabs(frontend_url):
                    status_url = str(FRONTEND_DIST_DIR / 'status.html')
                else:
                    status_url = frontend_url.replace('index.html', 'status.html')

                self._status_window = webview.create_window( 
                    title='OneShot Status',
                    url=status_url,
                    width=200,
                    height=32,
                    frameless=True,
                    on_top=True,
                    transparent=True,
                    resizable=False,
                    easy_drag=True,
                    js_api=self._js_api,
                )
                logger.info("状态浮窗已创建")
            except Exception as e:
                logger.error(f"创建状态浮窗失败: {e}")

        threading.Thread(target=_create, daemon=True).start()
    
    def _setup_hotkey(self):
        """设置快捷键"""
        modifiers, key = self._get_hotkey_info()
        self._keyboard_service.set_hotkey(self._on_hotkey_pressed, modifiers, key)
    
    def _apply_hotkey_change(self, modifiers: list, key: str):
        """应用前端传入的快捷键变更"""
        logger.info(f"快捷键变更: {modifiers}+{key}")
        # 更新配置
        self._config_service.hotkey["modifiers"] = modifiers
        self._config_service.hotkey["key"] = key
        self._config_service.save()
        # 更新显示
        self._create_hotkey_display(set(modifiers), key)
        # 重新注册热键
        self._keyboard_service.set_hotkey(self._on_hotkey_pressed, set(modifiers), key)
        self._tray_service.notify("OneShot", f"快捷键已更新: {self._hotkey_display}")

    def _save_auto_open_pdf(self, enabled: bool):
        """保存自动打开 PDF 设置"""
        logger.info(f"自动打开 PDF: {enabled}")
        self._config_service.download["auto_open_pdf"] = enabled
        self._config_service.save()

    def _save_auto_download_count(self, count: int):
        """保存自动下载阈值"""
        logger.info(f"自动下载阈值: ≤{count} 篇")
        self._config_service.download["auto_download_count"] = count
        self._config_service.save()

    def _save_naming_pattern(self, pattern: str):
        """保存命名格式"""
        logger.info(f"命名格式: {pattern}")
        self._config_service.download["naming_pattern"] = pattern
        self._config_service.save()
        self._js_api._naming_pattern = pattern

    def _save_auto_open_doi_on_fail(self, enabled: bool):
        """保存下载失败自动打开 DOI"""
        self._config_service.download["auto_open_doi_on_fail"] = enabled
        self._config_service.save()

    def _save_search_url(self, url: str):
        """保存搜索引擎 URL"""
        logger.info(f"搜索引擎 URL 已更新")
        self._config_service.search["engine_url"] = url
        self._config_service.save()

    def _save_status_bar_enabled(self, enabled: bool):
        """保存状态浮窗开关"""
        self._config_service.status_bar["enabled"] = enabled
        self._config_service.save()
        if enabled:
            self._create_status_window()
        elif self._status_window:
            try:
                self._status_window.hide()
            except Exception:
                pass

    def _save_result_auto_open(self, enabled: bool):
        """保存结果弹窗自动打开开关"""
        self._config_service.result["auto_open"] = enabled
        self._config_service.save()

    def _update_status(self, text: str, progress: float = 0.0):
        """更新状态浮窗内容"""
        self._js_api._status_state = {"text": text, "progress": progress}

    def _show_result_window(self):
        """显示结果弹窗（由浮窗点击触发）"""
        self._create_result_window()

    def _save_cf_bypass_config(self, host: str, port: int, use_external: bool = False):
        """保存 CloudflareBypass 配置（需重启软件生效）"""
        logger.info(f"CloudflareBypass 配置已保存: {host}:{port} external={use_external}（重启生效）")
        self._config_service.cf_bypass["host"] = host
        self._config_service.cf_bypass["port"] = port
        self._config_service.cf_bypass["use_external"] = use_external
        self._config_service.save()
        self._js_api._cf_bypass_state = {"host": host, "port": port, "use_external": use_external}

    def _start_download_by_doi(self, doi: str, meta: dict = None):
        """在后台线程中启动 DOI 下载"""
        states = self._js_api._download_states
        if states.get(doi, {}).get("status") == "downloading":
            return  # 已在下载中
        states[doi] = {"status": "downloading", "progress": 0.0, "path": None, "error": None}
        self._update_status(f"正在下载...", 0.0)

        # 如果文件已存在，立即返回 done
        existing = self._download_service.check_file_exists(doi)
        if existing:
            states[doi] = {"status": "done", "progress": 1.0, "path": str(existing), "error": None}
            self._update_status("下载完成", 1.0)
            return

        def _run():
            states = self._js_api._download_states

            def progress_cb(p: float):
                states[doi]["progress"] = p

            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                path = loop.run_until_complete(self._download_service.download_by_doi(
                    doi, progress_callback=progress_cb, meta=meta
                ))
                if path:
                    states[doi] = {"status": "done", "progress": 1.0, "path": str(path), "error": None}
                    logger.info(f"下载完成: {path}")
                    self._update_status("下载完成", 1.0)
                    if self._js_api._auto_open_pdf:
                        import os
                        os.startfile(str(path))
                else:
                    states[doi] = {"status": "unsupported", "progress": 0, "path": None, "error": "暂不支持该出版商"}
                    if self._js_api._auto_open_doi_on_fail:
                        import webbrowser
                        webbrowser.open(f"https://doi.org/{doi}")
            except Exception as e:
                logger.error(f"下载失败: {e}")
                states[doi] = {"status": "error", "progress": 0, "path": None, "error": str(e)}
                if self._js_api._auto_open_doi_on_fail:
                    import webbrowser
                    webbrowser.open(f"https://doi.org/{doi}")
            finally:
                loop.close()

        threading.Thread(target=_run, daemon=True).start()
    
    
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
            # min_size=(350, 400),
            # resizable=True,
            easy_drag=False,
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

        # 6. 停止下载服务（含 CloudflareBypass 代理）
        if self._download_service:
            try:
                self._download_service.cf_proxy._stop_server()
                logger.info("下载服务已停止")
            except Exception as e:
                logger.error(f"停止下载服务失败: {e}")

        # 7. 关闭状态浮窗
        if self._status_window:
            try:
                self._status_window.destroy()
            except Exception:
                pass

        logger.info("程序已退出")
    
    def run(self):
        """运行应用 - 主线程跑 GUI，后台线程做事件监控"""
        self._init_services()
        
        modifiers, key = self._get_hotkey_info()
        self._create_hotkey_display(modifiers, key)
        self._js_api._hotkey_state = {"modifiers": sorted(modifiers), "key": key}
        
        logger.info("=" * 50)
        logger.info("OneShot - 一键直达文献")
        logger.info(f"快捷键: {self._hotkey_display}")
        logger.info(f"前端模式: {'开发' if (self.force_dev or not FRONTEND_DIST_DIR.exists()) else '预构建'}")
        logger.info("=" * 50)

        # 启动下载服务（含 CloudflareBypass 代理）
        if self._download_service:
            asyncio.run(self._download_service.start())
        
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