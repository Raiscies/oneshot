<template>
  <v-app>
    <!-- 标题栏 -->
    <div class="result-header pywebview-drag-region">
      <v-icon icon="mdi-book-open-page-variant" size="small" class="mr-2"></v-icon>
      <span class="text-body-2">搜索结果 - {{ papers.length }} 篇文献</span>
      <v-spacer></v-spacer>
      <v-btn :icon="isPinned ? 'mdi-pin' : 'mdi-pin-off'" variant="text" size="x-small" @click="togglePin" class="no-drag" :color="isPinned ? 'primary' : undefined"></v-btn>
      <v-btn icon="mdi-close" variant="text" size="x-small" @click="closeWindow" class="no-drag"></v-btn>
    </div>

    <!-- 内容区域 -->
    <div class="result-content">
      <!-- 捕获的文本 -->
      <div v-if="capturedText" class="captured-text-card">
        <pre class="selectable">{{ capturedText }}</pre>
      </div>

      <!-- 论文卡片列表 -->
      <div class="papers-list">
        <div 
          v-for="(paper, index) in sortedPapers" 
          :key="index"
          class="paper-card"
        >
          <div class="paper-header">
            <!-- 占位/加载状态 -->
            <template v-if="paper._placeholder && !paper._error">
              <span class="paper-title text-grey">
                <v-progress-circular indeterminate size="14" width="2" class="mr-2"></v-progress-circular>
                {{ paper._searching ? '搜索补充信息中...' : '解析引用中...' }}
              </span>
            </template>
            <!-- 错误状态 -->
            <template v-else-if="paper._error">
              <span class="paper-title text-error">[{{ paper._index + 1 }}] 解析失败: {{ paper._error }}</span>
            </template>
            <!-- 正常结果 -->
            <template v-else>
              <span class="cite-index clickable" @click="copyText(paper.title)" title="点击复制标题">[{{ paper.citation_index || "*"}}]</span>
              <span class="paper-title selectable">{{ paper.title }}</span>
            </template>
            <div class="paper-actions" v-if="!paper._placeholder && !paper._error">
              <span class="download-btn-wrapper" v-if="paper.doi">
                <v-btn
                  v-if="downloadStates[paper.doi]?.status === 'unsupported'"
                  icon="mdi-download-off"
                  variant="flat"
                  size="x-small"
                  disabled
                  title="暂不支持该出版商"
                ></v-btn>
                <v-btn
                  v-else-if="downloadStates[paper.doi]?.status !== 'done'"
                  icon="mdi-download"
                  color="success"
                  variant="flat"
                  size="x-small"
                  :disabled="downloadStates[paper.doi]?.status === 'downloading'"
                  @click="onDownload(paper)"
                ></v-btn>
                <v-btn
                  v-else
                  icon="mdi-file-pdf-box"
                  color="error"
                  variant="flat"
                  size="x-small"
                  @click="onOpenPdf(paper.doi)"
                  title="打开已下载的 PDF"
                ></v-btn>
                <v-progress-circular
                  v-if="downloadStates[paper.doi]?.status === 'downloading'"
                  :model-value="(downloadStates[paper.doi]?.progress ?? 0) * 100"
                  :indeterminate="downloadStates[paper.doi]?.progress === undefined"
                  size="26"
                  width="3"
                  color="success"
                  class="download-progress"
                ></v-progress-circular>
              </span>
              <v-btn
                v-if="paper.url || paper.doi"
                icon="mdi-open-in-new"
                color="primary"
                variant="flat"
                size="x-small"
                @click="onOpenUrl(paper)"
              ></v-btn>
              <v-btn
                v-if="!paper._placeholder && !paper._error && !paper.doi && !paper.url"
                icon="mdi-magnify"
                color="warning"
                variant="flat"
                size="x-small"
                @click="onSearchTitle(paper)"
                title="在 Google Scholar 中搜索"
              ></v-btn>
              <!-- 搜索中指示器 -->
              <v-progress-circular
                v-if="paper._searching"
                indeterminate
                size="16"
                width="2"
                class="ml-1"
              ></v-progress-circular>
            </div>
          </div>

          <div class="paper-info" v-if="!paper._placeholder">
            <div class="info-row">
              <span class="info-label clickable" @click="copyText(paper.authors?.join(', ') || '')" title="点击复制所有作者">作者:</span>
              <span class="info-value selectable">
                <template v-if="paper.authors && paper.authors.length > 0">
                  <span v-for="(author, i) in paper.authors.slice(0, 3)" :key="i"
                        class="author-chip" @click="copyText(author)" title="点击复制作者">
                    {{ author }}
                  </span>
                  <span v-if="paper.authors.length > 3" class="author-more">et al.</span>
                </template>
                <template v-else>未知</template>
              </span>
            </div>
            <div class="info-row">
              <span class="info-label">年份:</span>
              <span class="info-value selectable">{{ paper.year || '未知' }}</span>
              <v-chip v-if="paper.ccf_rank" :color="getCcfColor(paper.ccf_rank)" size="x-small" class="ml-2">
                CCF {{ paper.ccf_rank }}
              </v-chip>
            </div>
            <div v-if="paper.doi" class="info-row">
              <span class="info-label clickable" title="点击复制" @click="copyText(paper.doi)">DOI:</span>
              <span class="info-value selectable">{{ paper.doi }}</span>
            </div>
            <div v-if="paper.citation_count !== undefined" class="info-row">
              <span class="info-label">引用:</span>
              <span class="info-value selectable">{{ paper.citation_count }}</span>
            </div>
            <div v-if="paper.abstract" class="info-row abstract">
              <span class="info-label clickable" @click="copyText(paper.abstract)" title="点击复制">摘要:</span>
              <span class="info-value selectable abstract-scroll">{{ paper.abstract }}</span>
            </div>
            <div v-else-if="paper.tldr" class="info-row abstract">
              <span class="info-label clickable" @click="copyText(paper.tldr)" title="点击复制">TLDR:</span>
              <span class="info-value selectable abstract-scroll">{{ paper.tldr }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </v-app>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { closeResultWindow } from './api'

// 从 pywebview API 获取数据
const capturedText = ref('')
const papers = ref<any[]>([])
const isPinned = ref(true)  // 默认置顶
const downloadStates = ref<Record<string, { status: string; progress: number; path: string | null; error: string | null }>>({})

// 排序：有 DOI/URL 的在前，既无 DOI 也无 URL 的（失败文献）在底部
const sortedPapers = computed(() => {
  const arr = [...papers.value]
  arr.sort((a, b) => {
    const aFailed = !a._placeholder && !a._error && !a.doi && !a.url
    const bFailed = !b._placeholder && !b._error && !b.doi && !b.url
    if (aFailed && !bFailed) return 1
    if (!aFailed && bFailed) return -1
    return 0
  })
  return arr
})

// 窗口拖动
// 上次获取的版本号，用于检测更新
let lastVersion = -1

onMounted(async () => {
  // 获取初始结果
  await fetchAndApplyResult()

  // 轮询版本号，有更新时自动刷新（纯 pywebview JS API，无 evaluate_js）
  const pollInterval = setInterval(async () => {
    await fetchAndApplyResult()
    await pollDownloadProgress()
  }, 500)

  // 组件卸载时清除轮询
  onUnmounted(() => {
    clearInterval(pollInterval)
  })
})

async function fetchAndApplyResult() {
  try {
    const version = await (window as any).pywebview?.api?.getResultVersion?.()
    if (version !== undefined && version !== lastVersion) {
      lastVersion = version
      const resultJson = await (window as any).pywebview?.api?.getResult?.()
      if (resultJson) {
        const data = JSON.parse(resultJson)
        applyResult(data)
      }
    }
  } catch (error) {
    // pywebview API 可能尚未就绪，静默忽略
  }
}

function applyResult(data: any) {
  if (data.papers && data.papers.length > 0) {
    papers.value = data.papers
    capturedText.value = data.captured_text || ''
    console.info('结果已加载:', data.papers.length, '篇')
  }
}

async function pollDownloadProgress() {
  const api = (window as any).pywebview?.api
  if (!api?.getDownloadProgress) return
  // 检查所有有 DOI 的文献的下载状态（包括自动下载触发的）
  for (const paper of papers.value) {
    if (!paper.doi) continue
    try {
      const json = await api.getDownloadProgress(paper.doi)
      if (json) {
        const updated = JSON.parse(json)
        if (updated.status !== 'unknown') {
          downloadStates.value[paper.doi] = updated
        }
      }
    } catch { /* ignore */ }
  }
}

function getCcfColor(rank: string): string {
  const colors: Record<string, string> = { 'A': 'red', 'B': 'blue', 'C': 'green' }
  return colors[rank] || 'grey'
}

async function onDownload(paper: any) {
  if (!paper.doi) return
  const api = (window as any).pywebview?.api
  if (!api?.downloadByDoi) return
  api.downloadByDoi(paper.doi)
  downloadStates.value[paper.doi] = { status: 'downloading', progress: 0, path: null, error: null }
}

function onOpenPdf(doi: string) {
  const state = downloadStates.value[doi]
  if (state?.path) {
    ;(window as any).pywebview?.api?.openFile?.(state.path)
  }
}

function onSearchTitle(paper: any) {
  const query = paper.raw_citation || paper.title
  if (query) {
    ;(window as any).pywebview?.api?.searchInBrowser?.(query)
  }
}

function onOpenUrl(paper: any) {
  // 优先 DOI URL，其次 paper.url
  const url = (paper.doi ? `https://doi.org/${paper.doi}` : null) || paper.url
  if (url) {
    window.open(url, '_blank')
  }
}

function closeWindow() {
  closeResultWindow()
}

function copyText(text: string) {
  navigator.clipboard.writeText(text).catch(() => {
    // fallback for older browsers
    const ta = document.createElement('textarea')
    ta.value = text
    document.body.appendChild(ta)
    ta.select()
    document.execCommand('copy')
    document.body.removeChild(ta)
  })
}

// ESC 关闭窗口
function onKeyDown(e: KeyboardEvent) {
  if (e.key === 'Escape') closeWindow()
}

document.addEventListener('keydown', onKeyDown)
onUnmounted(() => document.removeEventListener('keydown', onKeyDown))

async function togglePin() {
  // function currently has some problem
  // try {
    
    // console.log("toggling")

    // const result = await (window as any).pywebview?.api?.toggleResultOnTop?.()
  //   if (result !== undefined) {
  //     isPinned.value = result
  //   } else {
  //     isPinned.value = !isPinned.value
  //   }
  // } catch {
  //   isPinned.value = !isPinned.value
  // }
}
</script>

<style scoped>
.download-btn-wrapper {
  position: relative;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}
.download-progress {
  position: absolute;
  pointer-events: none;
}
/* 整个应用容器隐藏溢出 */
:deep(.v-application) {
  overflow: hidden;
}

.result-header {
  display: flex;
  align-items: center;
  padding: 4px 8px;
  background: #1a1a1a;
  border-bottom: 1px solid #333;
  cursor: move;
  user-select: none;
  font-size: 11px;
}

.no-drag {
  cursor: default;
}

.result-content {
  background: #121212;
  height: calc(100vh - 40px);
  overflow-y: auto;
  padding: 8px;
}

.captured-text-card {
  background: #0d2137;
  padding: 10px;
  border-radius: 4px;
  margin-bottom: 8px;
}

.captured-text-card pre {
  white-space: pre-wrap;
  word-wrap: break-word;
  color: white;
  font-size: 11px;
  font-family: inherit;
  margin: 0;
  max-height: calc(1.5em * 3);
  overflow-y: auto;
}

.papers-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.paper-card {
  background: #1e1e1e;
  border-radius: 6px;
  overflow: hidden;
}

.paper-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 10px;
  background: #2a2a2a;
}

.paper-title {
  font-weight: bold;
  font-size: 12px;
  color: white;
  flex: 1;
  word-wrap: break-word;
}

.paper-title.title-scroll {
  max-height: 48px;
  overflow-y: auto;
}

.cite-index {
  color: #66b3ff;
  font-weight: bold;
  font-size: 12px;
  margin-right: 6px;
  flex-shrink: 0;
}

.paper-actions {
  display: flex;
  gap: 4px;
  margin-left: 8px;
  align-items: center;
  flex-shrink: 0;
}

.paper-info {
  padding: 8px 10px;
}

.info-row {
  display: flex;
  align-items: baseline;
  margin-bottom: 4px;
  font-size: 11px;
}

.info-row.abstract {
  flex-direction: column;
}

.info-label {
  color: #888;
  min-width: 40px;
  flex-shrink: 0;
}

.author-chip {
  display: inline;
  padding: 1px 6px;
  margin: 0 2px 2px 0;
  border-radius: 4px;
  background: #333;
  cursor: pointer;
  white-space: nowrap;
}
.author-chip:hover {
  background: #555;
}
.author-chip:active {
  background: #777;
}
.author-more {
  color: #888;
}

.clickable {
  cursor: pointer;
}
.clickable:hover {
  opacity: 0.8;
}
.clickable:active {
  opacity: 0.5;
}

.info-value {
  color: white;
  word-wrap: break-word;
}

.abstract-scroll {
  max-height: 80px;
  overflow-y: auto;
  display: block;
}

.abstract .info-value {
  color: #aaa;
  margin-top: 4px;
}

/* 可选中文本 */
.selectable {
  user-select: text !important;
  cursor: text;
}
</style>