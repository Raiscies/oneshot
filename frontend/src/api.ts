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
        setResult: (data: string) => void
        hideMainWindow: () => void
        moveWindow: (x: number, y: number, windowType?: string) => void
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

// 窗口拖动工具
// windowType: 'main' 或 'result'，告诉后端移动哪个窗口
export function createDragHandler(headerSelector: string, windowType: string = 'main') {
  let isDragging = false
  let startX = 0
  let startY = 0
  let winStartX = 0
  let winStartY = 0

  const onMouseDown = (e: MouseEvent) => {
    // 只在标题栏区域触发（排除按钮等交互元素）
    const target = e.target as HTMLElement
    if (target.closest('button, a, input, select, textarea, .v-btn, .no-drag')) {
      return
    }
    isDragging = true
    startX = e.screenX
    startY = e.screenY
    winStartX = window.screenX
    winStartY = window.screenY
    document.body.style.cursor = 'move'
    e.preventDefault()
  }

  const onMouseMove = (e: MouseEvent) => {
    if (!isDragging) return
    const dx = e.screenX - startX
    const dy = e.screenY - startY
    window.pywebview?.api?.moveWindow?.(winStartX + dx, winStartY + dy, windowType)
  }

  const onMouseUp = () => {
    if (isDragging) {
      isDragging = false
      document.body.style.cursor = ''
    }
  }

  const attach = () => {
    const header = document.querySelector(headerSelector)
    if (header) {
      header.addEventListener('mousedown', onMouseDown as EventListener)
      document.addEventListener('mousemove', onMouseMove as EventListener)
      document.addEventListener('mouseup', onMouseUp as EventListener)
    }
  }

  const detach = () => {
    const header = document.querySelector(headerSelector)
    if (header) {
      header.removeEventListener('mousedown', onMouseDown as EventListener)
    }
    document.removeEventListener('mousemove', onMouseMove as EventListener)
    document.removeEventListener('mouseup', onMouseUp as EventListener)
  }

  return { attach, detach }
}
