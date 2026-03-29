"""
OneShot - 主入口文件
一键直达文献：基于快捷键的论文文献快速下载工具
"""

import os
import sys
import asyncio
import logging
import threading
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent))

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 全局变量
_app_instance = None


def create_app_instance():
    """创建应用实例"""
    global _app_instance
    
    if _app_instance is not None:
        return _app_instance
    
    # 导入服务
    from oneshot.services import (
        CitationParser,
        SearchService,
        DownloadService,
        KeyboardService,
        ClipboardService,
        TrayService,
        CrossRefSearcher,
        SemanticScholarSearcher
    )
    
    # 初始化服务
    citation_parser = CitationParser()
    search_service = SearchService()
    download_service = DownloadService()
    keyboard_service = KeyboardService()
    clipboard_service = ClipboardService()
    tray_service = TrayService()
    
    # 添加搜索器
    search_service.add_searcher(CrossRefSearcher())
    search_service.add_searcher(SemanticScholarSearcher())
    
    # 创建快捷键回调
    async def on_hotkey_pressed():
        """快捷键触发处理"""
        logger.info("快捷键触发，开始处理...")
        
        # 读取剪贴板
        citation = clipboard_service.get_text()
        if not citation:
            logger.warning("剪贴板为空")
            tray_service.notify("OneShot", "剪贴板为空，请先复制文献引用")
            return
        
        logger.info(f"读取到剪贴板内容: {citation[:50]}...")
        
        # 解析引用
        papers = citation_parser.parse(citation)
        if not papers:
            logger.warning("引用解析失败")
            tray_service.notify("OneShot", "引用解析失败")
            return
        
        logger.info(f"解析到 {len(papers)} 个文献")
        
        # 搜索（使用新事件循环）
        for paper in papers:
            results = await search_service.search(paper)
            if results:
                logger.info(f"搜索到 {len(results)} 个结果: {results[0].paper.title}")
                
                # 下载第一个可用结果
                result = results[0]
                try:
                    file_path = await download_service.download(result)
                    if file_path:
                        tray_service.notify(
                            "下载完成",
                            f"《{paper.title[:20]}...》已保存"
                        )
                    else:
                        tray_service.notify("下载失败", f"未能下载: {paper.title[:20]}")
                except Exception as e:
                    logger.error(f"下载异常: {e}")
                    tray_service.notify("下载异常", str(e))
    
    # 设置快捷键
    keyboard_service.set_hotkey(on_hotkey_pressed)
    
    _app_instance = {
        'citation_parser': citation_parser,
        'search_service': search_service,
        'download_service': download_service,
        'keyboard_service': keyboard_service,
        'clipboard_service': clipboard_service,
        'tray_service': tray_service,
    }
    
    return _app_instance


def run_web_ui():
    """运行Web界面"""
    from nicegui import ui
    from oneshot.ui import create_app
    
    app_instance = create_app_instance()
    
    # 创建UI
    oneshot_ui = create_app(
        app_instance['citation_parser'],
        app_instance['search_service'],
        app_instance['download_service']
    )
    
    # 设置快捷键触发UI处理
    async def handle_hotkey():
        await oneshot_ui.process_clipboard()
    
    app_instance['keyboard_service'].set_hotkey(handle_hotkey)
    app_instance['keyboard_service'].start()
    
    # 运行UI
    ui.run(
        title="OneShot - 文献快速下载",
        port=8080,
        reload=False,
        show=False,  # 不显示浏览器窗口（后台运行）
    )


def run_tray():
    """运行系统托盘"""
    app_instance = create_app_instance()
    tray_service = app_instance['tray_service']
    
    tray_service.setup(
        on_quit=lambda: stop_app(),
        on_show=lambda: logger.info("显示主界面")
    )
    
    tray_service.run()


def stop_app():
    """停止应用"""
    global _app_instance
    
    if _app_instance:
        logger.info("正在停止应用...")
        
        # 停止服务
        if 'keyboard_service' in _app_instance:
            _app_instance['keyboard_service'].stop()
        
        if 'tray_service' in _app_instance:
            _app_instance['tray_service'].stop()
        
        logger.info("应用已停止")
        
        # 退出程序
        import os
        os._exit(0)


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='OneShot - 文献快速下载')
    parser.add_argument('--mode', choices=['ui', 'tray', 'both'], default='both',
                        help='运行模式: ui(仅Web界面), tray(仅托盘), both(两者)')
    parser.add_argument('--storage', type=str, default='./papers',
                        help='文献存储目录')
    
    args = parser.parse_args()
    
    logger.info("="*50)
    logger.info("OneShot - 一键直达文献")
    logger.info("快捷键: Ctrl+Shift+L")
    logger.info("="*50)
    
    # 设置存储目录
    app_instance = create_app_instance()
    app_instance['download_service'].storage_dir = Path(args.storage)
    app_instance['download_service'].storage_dir.mkdir(parents=True, exist_ok=True)
    
    if args.mode in ['ui', 'both']:
        # 启动键盘监听
        app_instance['keyboard_service'].start()
        
        # 在新线程中运行Web UI
        ui_thread = threading.Thread(target=run_web_ui, daemon=True)
        ui_thread.start()
    
    if args.mode in ['tray', 'both']:
        # 运行托盘
        run_tray()
    
    if args.mode == 'both':
        # 保持主线程运行
        try:
            while True:
                import time
                time.sleep(1)
        except KeyboardInterrupt:
            stop_app()


if __name__ == '__main__':
    main()
