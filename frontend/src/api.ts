/**
 * pywebview JS API
 */

declare global {
  interface Window {
    pywebview: {
      api: {
        close: () => void
        showResultDialog: (papers: string, captured: string) => void
      }
    }
  }
}

export const pywebview = {
  api: {
    close: () => {
      window.pywebview?.api?.close?.()
    },
    showResultDialog: (papers: string, captured: string = '') => {
      window.pywebview?.api?.showResultDialog?.(papers, captured)
    },
  },
}

// 在需要关闭时调用
export function closeWindow() {
  pywebview.api.close()
}

// 显示结果弹窗
export function showResultDialog(papers: any[], captured: string = '') {
  pywebview.api.showResultDialog(JSON.stringify(papers), captured)
}
