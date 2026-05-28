"""
OneShot - pywebview 桌面应用入口

使用 pywebview 在本地窗口中加载 Vue 前端
"""

import webview
import threading
import time
import os
import sys

# 前端开发服务器端口
FRONTEND_PORT = 5173
FRONTEND_URL = f"http://localhost:{FRONTEND_PORT}"

# 结果窗口引用
_result_window = None


class Api:
    """pywebview JavaScript API"""
    
    def close(self):
        """关闭窗口"""
        print("Closing window...")
        global _result_window
        if _result_window:
            try:
                _result_window.destroy()
            except:
                pass
            _result_window = None
        # 关闭所有窗口
        for window in webview.windows:
            try:
                window.destroy()
            except:
                pass
    
    def showResultDialog(self, papers_data: str = "", captured_text: str = ""):
        """显示结果弹窗（在新窗口中）"""
        global _result_window
        print(f"显示结果弹窗, papers: {len(papers_data) if papers_data else 0}")
        
        # 如果已存在结果窗口，先关闭
        if _result_window:
            try:
                _result_window.destroy()
            except:
                pass
        
        # 创建新的结果窗口
        # 数据由 ResultApp.vue 从 FastAPI 获取
        _result_window = webview.create_window(
            title='搜索结果 - OneShot',
            url=f"{FRONTEND_URL}/result.html",
            width=550,
            height=600,
            min_size=(400, 300),
            resizable=True,
            frameless=True,
            on_top=True,
        )
        
        # # 在新线程中显示窗口
        # thread = threading.Thread(target=self._show_window_thread)
        # thread.daemon = True
        # thread.start()
    
    # def _show_window_thread(self):
    #     """在新线程中显示窗口"""
    #     # pywebview 需要在主线程或特定线程中显示
    #     pass


def main():
    """主函数"""
    print("=" * 50)
    print("OneShot - pywebview 桌面应用")
    print("=" * 50)
    
    # 创建主窗口
    main_window = webview.create_window(
        title='OneShot - 一键直达文献',
        url=FRONTEND_URL,
        width=400,
        height=500,
        min_size=(350, 400),
        resizable=True,
        frameless=True,
        js_api=Api(),
    )
            
    # 启动 pywebview（这会阻塞）
    print("启动桌面窗口...")
    webview.start(debug=False)


if __name__ == '__main__':
    main()