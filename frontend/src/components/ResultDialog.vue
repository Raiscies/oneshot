<template>
  <v-overlay
    v-model="showDialog"
    class="result-dialog-overlay"
    scrim="transparent"
    :close-on-back="true"
  >
    <div 
      class="result-dialog"
      :style="dialogStyle"
      @mousedown="onDragStart"
    >
      <!-- 标题栏 -->
      <div class="dialog-header" @mousedown.stop="onDragStart">
        <v-icon icon="mdi-book-open-page-variant" size="small" class="mr-2"></v-icon>
        <span class="text-body-2">{{ title }}</span>
        <v-spacer></v-spacer>
        <v-btn
          icon="mdi-pin"
          variant="text"
          size="x-small"
          :color="alwaysOnTop ? 'primary' : 'default'"
          @click.stop="toggleAlwaysOnTop"
        ></v-btn>
        <v-btn
          icon="mdi-close"
          variant="text"
          size="x-small"
          @click.stop="closeDialog"
        ></v-btn>
      </div>

      <!-- 内容区域 -->
      <div class="dialog-content">
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
                <span class="info-value text-caption">{{ paper.doi }}</span>
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
    </div>
  </v-overlay>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'

// Props
const props = defineProps<{
  modelValue: boolean
  papers: any[]
  capturedText?: string
}>()

// Emits
const emit = defineEmits<{
  'update:modelValue': [value: boolean]
  'download': [paper: any]
  'openUrl': [paper: any]
}>()

// 状态
const showDialog = ref(false)
const alwaysOnTop = ref(true)
const dragOffset = ref({ x: 0, y: 0 })

// 计算属性
const title = computed(() => `找到 ${props.papers.length} 篇文献`)

const dialogStyle = computed(() => ({
  position: 'fixed' as const,
  top: '20px',
  left: '20px',
  width: '550px',
  maxHeight: '700px',
  zIndex: alwaysOnTop.value ? 9999 : undefined,
}))

// 方法
function closeDialog() {
  showDialog.value = false
  emit('update:modelValue', false)
}

function toggleAlwaysOnTop() {
  alwaysOnTop.value = !alwaysOnTop.value
}

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
  const colors: Record<string, string> = {
    'A': 'red',
    'B': 'blue',
    'C': 'green',
  }
  return colors[rank] || 'grey'
}

function truncateText(text: string, maxLength: number): string {
  if (!text || text.length <= maxLength) return text
  return text.substring(0, maxLength) + '...'
}

function onDownload(paper: any) {
  emit('download', paper)
}

function onOpenUrl(paper: any) {
  emit('openUrl', paper)
}

function onDragStart(event: MouseEvent) {
  // 拖拽逻辑（可选）
}

// 监听 modelValue
onMounted(() => {
  showDialog.value = props.modelValue
})

// 监听 props 变化
import { watch } from 'vue'
watch(() => props.modelValue, (newVal) => {
  showDialog.value = newVal
})

watch(showDialog, (newVal) => {
  emit('update:modelValue', newVal)
})
</script>

<style scoped>
.result-dialog-overlay {
  pointer-events: none;
}

.result-dialog {
  background: #1a1a1a;
  border: 1px solid #333;
  border-radius: 8px;
  overflow: hidden;
  pointer-events: auto;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.5);
}

.dialog-header {
  display: flex;
  align-items: center;
  padding: 8px 12px;
  background: #2b2b2b;
  cursor: move;
  user-select: none;
}

.dialog-content {
  max-height: 600px;
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
  background: #222;
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