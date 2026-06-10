/**
 * pywebview JS API
 */

declare global {
  interface Window {
    pywebview: {
      api: {
        close: () => void
        closeResultWindow: () => void
        getResult: () => Promise<string>
        getResultVersion: () => Promise<number>
        setResult: (data: string) => void
        hideMainWindow: () => void
        toggleResultOnTop: () => Promise<boolean>
        setHotkey: (modifiers: string[], key: string) => void
        getHotkey: () => Promise<string>
        setCfBypassConfig: (host: string, port: number, use_external?: boolean) => void
        getCfBypassConfig: () => Promise<string>
        downloadByDoi: (doi: string, meta_json?: string) => void
        getDownloadProgress: (doi: string) => Promise<string>
        checkPaperExists: (doi: string) => Promise<string>
        openFile: (path: string) => void
        searchInBrowser: (query: string) => void
        setAutoOpenPdf: (enabled: boolean) => void
        getAutoOpenPdf: () => Promise<boolean>
        setAutoDownloadCount: (count: number) => void
        getAutoDownloadCount: () => Promise<number>
        setNamingPattern: (pattern: string) => void
        getNamingPattern: () => Promise<string>
        setAutoOpenDoiOnFail: (enabled: boolean) => void
        getAutoOpenDoiOnFail: () => Promise<boolean>
        setSearchUrl: (url: string) => void
        getSearchUrl: () => Promise<string>
        getStatus: () => Promise<string>
        showResultWindow: () => void
        setStatusBarEnabled: (enabled: boolean) => void
        getStatusBarEnabled: () => Promise<boolean>
        setResultAutoOpen: (enabled: boolean) => void
        getResultAutoOpen: () => Promise<boolean>
      }
    }
  }
}

export const pywebview = {
  api: {
    close: () => {
      window.pywebview?.api?.close?.()
    },
    closeResultWindow: () => {
      window.pywebview?.api?.closeResultWindow?.()
    },
    getResult: () => window.pywebview?.api?.getResult?.(),
    hideMainWindow: () => {
      window.pywebview?.api?.hideMainWindow?.()
    },
  },
}

// 隐藏主窗口（保留托盘运行，不退出程序）
export function hideWindow() {
  pywebview.api.hideMainWindow()
}

// 关闭结果窗口（仅关闭窗口，后台继续运行）
export function closeResultWindow() {
  pywebview.api.closeResultWindow()
}

// 显示测试结果弹窗
export function showResultDialog(papers: any[], capturedText: string) {
  const data = {
    papers,
    captured_text: capturedText,
    message: `测试：找到 ${papers.length} 篇文献`,
  }
  window.pywebview?.api?.setResult?.(JSON.stringify(data))
  // 结果窗口由 Python 端创建
}
