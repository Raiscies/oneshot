<template>
  <v-app>
    <!-- 标题栏 -->
    <div class="result-header">
      <v-icon icon="mdi-book-open-page-variant" size="small" class="mr-2"></v-icon>
      <span class="text-body-2">搜索结果 - {{ papers.length }} 篇文献</span>
      <v-spacer></v-spacer>
      <v-btn icon="mdi-close" variant="text" size="x-small" @click="closeWindow" class="no-drag"></v-btn>
    </div>

    <!-- 内容区域 -->
    <div class="result-content">
      <!-- 捕获的文本 -->
      <div v-if="capturedText" class="captured-text-card">
        <pre>{{ capturedText }}</pre>
      </div>

      <!-- 论文卡片列表 -->
      <div class="papers-list">
        <div 
          v-for="(paper, index) in papers" 
          :key="index"
          class="paper-card"
        >
          <div class="paper-header">
            <span class="paper-title">{{ formatTitle(paper) }}</span>
            <div class="paper-actions">
              <v-btn
                icon="mdi-download"
                color="success"
                variant="flat"
                size="x-small"
                @click="onDownload(paper)"
              ></v-btn>
              <v-btn
                icon="mdi-open-in-new"
                color="primary"
                variant="flat"
                size="x-small"
                @click="onOpenUrl(paper)"
              ></v-btn>
            </div>
          </div>

          <div class="paper-info">
            <div class="info-row">
              <span class="info-label">作者:</span>
              <span class="info-value">{{ formatAuthors(paper.authors) }}</span>
            </div>
            <div class="info-row">
              <span class="info-label">年份:</span>
              <span class="info-value">{{ paper.year || '未知' }}</span>
              <v-chip v-if="paper.ccf_rank" :color="getCcfColor(paper.ccf_rank)" size="x-small" class="ml-2">
                CCF {{ paper.ccf_rank }}
              </v-chip>
            </div>
            <div v-if="paper.doi" class="info-row">
              <span class="info-label">DOI:</span>
              <span class="info-value">{{ paper.doi }}</span>
            </div>
            <div v-if="paper.citations !== undefined" class="info-row">
              <span class="info-label">引用:</span>
              <span class="info-value">{{ paper.citations }}</span>
            </div>
            <div v-if="paper.abstract" class="info-row abstract">
              <span class="info-label">摘要:</span>
              <span class="info-value">{{ truncateText(paper.abstract, 200) }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </v-app>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { closeResultWindow, createDragHandler } from './api'

// 从 pywebview API 获取数据
const capturedText = ref('')
const papers = ref<any[]>([])

// 窗口拖动
const dragHandler = createDragHandler('.result-header', 'result')
onMounted(async () => {
  dragHandler.attach()

  // 轮询检查结果是否就绪
  const maxRetries = 60
  const interval = 500 // 500ms
  
  for (let i = 0; i < maxRetries; i++) {
    try {
      // 调用 pywebview API (返回 Promise)
      const resultJson = await (window as any).pywebview?.api?.getResult?.()
      if (resultJson) {
        const data = JSON.parse(resultJson)
        if (data.papers && data.papers.length > 0) {
          papers.value = data.papers
          capturedText.value = data.captured_text || ''
          console.info('结果已加载:', data.papers.length, '篇')
          return
        }
      }
    } catch (error) {
      console.error('获取结果失败:', error)
    }
    await new Promise(resolve => setTimeout(resolve, interval))
  }
  
  console.warn('结果加载超时')
})

function formatTitle(paper: any): string {
  const citeNum = paper.citation_number || paper.citeNum
  if (citeNum) {
    return `[${citeNum}] ${paper.title}`
  }
  return paper.title || '未知标题'
}

function formatAuthors(authors: string[] | undefined): string {
  if (!authors || authors.length === 0) return '未知'
  const display = authors.slice(0, 3).join(', ')
  return authors.length > 3 ? `${display} et al.` : display
}

function getCcfColor(rank: string): string {
  const colors: Record<string, string> = { 'A': 'red', 'B': 'blue', 'C': 'green' }
  return colors[rank] || 'grey'
}

function truncateText(text: string, maxLength: number): string {
  if (!text || text.length <= maxLength) return text
  return text.substring(0, maxLength) + '...'
}

function onDownload(paper: any) {
  console.log('下载论文:', paper.title)
}

function onOpenUrl(paper: any) {
  const doiUrl = paper.doi ? `https://doi.org/${paper.doi}` : null
  if (doiUrl) {
    window.open(doiUrl, '_blank')
  }
}

function closeWindow() {
  closeResultWindow()
}
</script>

<style scoped>
/* 整个应用容器隐藏溢出 */
:deep(.v-application) {
  overflow: hidden;
}

.result-header {
  display: flex;
  align-items: center;
  padding: 8px 12px;
  background: #1a1a1a;
  border-bottom: 1px solid #333;
  cursor: move;
  user-select: none;
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
  align-items: flex-start;
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

.paper-actions {
  display: flex;
  gap: 4px;
  margin-left: 8px;
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
}

.info-value {
  color: white;
  word-wrap: break-word;
}

.abstract .info-value {
  color: #aaa;
  margin-top: 4px;
}
</style>