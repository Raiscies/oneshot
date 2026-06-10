<template>
  <v-card class="settings-card pt-0">
    <v-card-title class="d-flex align-center py-2 px-3">
      <v-icon icon="mdi-cog" class="mr-2" size="small"></v-icon>
      <span class="text-body-2">设置</span>
    </v-card-title>
    
    <v-divider></v-divider>
    
    <v-card-text>
      <!-- 快捷键设置 -->
      <v-expansion-panels variant="accordion" multiple>
        <v-expansion-panel title="快捷键">
          <v-expansion-panel-text>
            <div class="hotkey-display mb-4">
              <v-chip size="large" :color="recording ? 'error' : 'primary'" variant="flat" class="hotkey-chip">
                {{ recording ? '按下组合键...' : (hotkeyDisplay || '未设置') }}
              </v-chip>
            </div>
            
            <v-btn 
              :color="recording ? 'error' : 'primary'"
              @click="toggleRecording"
              class="mb-3"
            >
              <v-icon start :icon="recording ? 'mdi-stop' : 'mdi-record'"></v-icon>
              {{ recording ? '停止录制' : '录制快捷键' }}
            </v-btn>
            
            <v-btn color="success" @click="applyHotkey" :disabled="!capturedHotkey" class="ml-2 mb-3">
              应用快捷键
            </v-btn>
            
            <p class="text-caption text-grey mt-2">点击"录制快捷键"，然后按下你想要的组合键（如 Ctrl+Shift+L）</p>
          </v-expansion-panel-text>
        </v-expansion-panel>

        <!-- 窗口设置 -->
        <v-expansion-panel title="窗口">
          <v-expansion-panel-text>
            <v-switch
              v-model="alwaysOnTop"
              label="结果弹窗置顶显示"
              color="primary"
              hide-details
              @update:model-value="(v) => onAlwaysOnTopChange(v ?? false)"
            ></v-switch>
            
            <v-switch
              v-model="followMouse"
              label="弹窗跟随鼠标位置"
              color="primary"
              hide-details
              @update:model-value="(v) => onFollowMouseChange(v ?? false)"
            ></v-switch>
          </v-expansion-panel-text>
        </v-expansion-panel>

        <!-- 存储设置 -->
        <v-expansion-panel title="存储">
          <v-expansion-panel-text>
            <v-text-field
              v-model="storagePath"
              label="文献存储路径"
              variant="outlined"
              density="compact"
              hide-details
              readonly
            ></v-text-field>
            
            <v-btn
              color="secondary"
              variant="tonal"
              class="mt-3"
              @click="openFolder"
            >
              <v-icon start icon="mdi-folder-open"></v-icon>
              打开目录
            </v-btn>
          </v-expansion-panel-text>
        </v-expansion-panel>

        <!-- 显示设置 -->
        <v-expansion-panel title="显示">
          <v-expansion-panel-text>
            <!--
            <v-switch
              v-model="statusBarEnabled"
              label="显示状态浮窗"
              color="primary"
              hide-details
              @update:model-value="(v) => onStatusBarEnabledChange(v ?? true)"
            ></v-switch>
            -->
            <v-switch
              v-model="resultAutoOpen"
              label="触发快捷键时自动弹出结果窗口"
              color="primary"
              hide-details
              class="mt-3"
              @update:model-value="(v) => onResultAutoOpenChange(v ?? true)"
            ></v-switch>
          </v-expansion-panel-text>
        </v-expansion-panel>

        <!-- 下载设置 -->
        <v-expansion-panel title="下载">
          <v-expansion-panel-text>
            <v-switch
              v-model="autoOpenPdf"
              label="下载完成后自动打开 PDF"
              color="primary"
              hide-details
              @update:model-value="(v) => onAutoOpenPdfChange(v ?? false)"
            ></v-switch>
            <v-text-field
              v-model.number="autoDownloadCount"
              label="文献数 ≤ 此值时自动下载（0=关闭）"
              type="number"
              variant="outlined"
              density="compact"
              hide-details
              min="0"
              class="mt-3"
              @update:model-value="onAutoDownloadCountChange"
            ></v-text-field>
            <v-text-field
              v-model="namingPattern"
              label="PDF 命名格式（{doi}=DOI）"
              variant="outlined"
              density="compact"
              hide-details
              class="mt-3"
              @update:model-value="onNamingPatternChange"
            ></v-text-field>
            <v-text-field
              v-model.number="delaySeconds"
              label="同出版商下载间隔（秒）"
              type="number"
              variant="outlined"
              density="compact"
              hide-details
              min="0"
              class="mt-3"
              hint="重启生效"
              persistent-hint
            ></v-text-field>
            <v-switch
              v-model="autoOpenDoiOnFail"
              label="下载失败后自动打开 DOI 链接"
              color="primary"
              hide-details
              class="mt-3"
              @update:model-value="(v) => onAutoOpenDoiOnFailChange(v ?? false)"
            ></v-switch>
            <p class="text-caption text-warning mt-3">请确保您的网络已经处于能够手动下载文献的环境下！</p>
          </v-expansion-panel-text>
        </v-expansion-panel>

        <!-- 搜索设置 -->
        <v-expansion-panel title="搜索">
          <v-expansion-panel-text>
            <v-combobox
              v-model="searchEngineUrl"
              :items="searchEnginePresets"
              label="搜索引擎 URL（{query} 为占位符）"
              variant="outlined"
              density="compact"
              hide-details
              @update:model-value="onSearchUrlChange"
            ></v-combobox>
          </v-expansion-panel-text>
        </v-expansion-panel>

        <!-- CloudflareBypass 设置 -->
        <v-expansion-panel title="Cloudflare 绕过">
          <v-expansion-panel-text>
            <v-switch
              v-model="cfBypassExternal"
              label="使用外部 CF 代理（不自动启动内置服务器）"
              color="primary"
              hide-details
              class="mb-3"
            ></v-switch>

            <v-text-field
              v-model="cfBypassHost"
              label="代理服务器地址"
              variant="outlined"
              density="compact"
              hide-details
              class="mb-3"
            ></v-text-field>

            <v-text-field
              v-model.number="cfBypassPort"
              label="代理服务器端口"
              type="number"
              variant="outlined"
              density="compact"
              hide-details
              class="mb-3"
            ></v-text-field>

            <v-btn
              color="primary"
              variant="tonal"
              @click="applyCfBypass"
              :disabled="!cfBypassChanged"
            >
              保存配置
            </v-btn>

            <p class="text-caption text-grey mt-2">修改后需重启软件生效</p>
          </v-expansion-panel-text>
        </v-expansion-panel>

        <!-- 关于 -->
        <v-expansion-panel title="关于">
          <v-expansion-panel-text>
            <v-list density="compact">
              <v-list-item>
                <v-list-item-title>OneShot - 一键直达文献</v-list-item-title>
              </v-list-item>
              <v-list-item>
                <v-list-item-subtitle>版本</v-list-item-subtitle>
                <v-list-item-title class="text-primary">0.1.0</v-list-item-title>
              </v-list-item>
              <v-list-item>
                <v-list-item-subtitle>技术栈</v-list-item-subtitle>
                <v-list-item-title>Vue 3 + Vuetify + FastAPI</v-list-item-title>
              </v-list-item>
            </v-list>
          </v-expansion-panel-text>
        </v-expansion-panel>
      </v-expansion-panels>
    </v-card-text>
    
    <!-- 调试区域 -->
    <v-divider></v-divider>
  </v-card>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'

// Props
const props = defineProps<{
  debugMode?: boolean
}>()

// Emits
const emit = defineEmits<{
  'apply-hotkey': [hotkey: { modifiers: string[], key: string }]
  'update-config': [key: string, value: any]
}>()

// 快捷键设置
const recording = ref(false)
const capturedModifiers = ref<string[]>([])
const capturedKey = ref('')
const capturedHotkey = ref(false)

const hotkeyDisplay = computed(() => {
  if (!capturedHotkey.value) return '未设置'
  const mods = capturedModifiers.value.map(m => m === 'ctrl' ? 'Ctrl' : m === 'shift' ? 'Shift' : m === 'alt' ? 'Alt' : m).join('+')
  return `${mods}+${capturedKey.value.toUpperCase()}`
})

function toggleRecording() {
  if (recording.value) {
    recording.value = false
    return
  }
  recording.value = true
  capturedHotkey.value = false
}

function onKeyDown(e: KeyboardEvent) {
  if (!recording.value) return
  e.preventDefault()
  
  // ESC 取消录制
  if (e.key === 'Escape') {
    recording.value = false
    return
  }
  
  // 忽略纯修饰键
  if (['Control', 'Shift', 'Alt', 'Meta'].includes(e.key)) return
  
  const mods: string[] = []
  if (e.ctrlKey || e.metaKey) mods.push('ctrl')
  if (e.shiftKey) mods.push('shift')
  if (e.altKey) mods.push('alt')
  
  capturedModifiers.value = mods
  capturedKey.value = e.key.toLowerCase()
  capturedHotkey.value = true
  recording.value = false
}

onMounted(async () => {
  document.addEventListener('keydown', onKeyDown)
  // 加载当前快捷键配置（pywebview API 可能尚未就绪，重试几次）
  for (let retry = 0; retry < 20; retry++) {
    try {
      const json = await (window as any).pywebview?.api?.getHotkey?.()
      if (json) {
        const cfg = JSON.parse(json)
        if (cfg.modifiers && cfg.key) {
          capturedModifiers.value = cfg.modifiers
          capturedKey.value = cfg.key
          capturedHotkey.value = true
          break
        }
      }
    } catch { /* API not ready yet */ }
    await new Promise(r => setTimeout(r, 200))
  }
  // 加载 CF bypass 配置
  for (let retry = 0; retry < 20; retry++) {
    try {
      const json = await (window as any).pywebview?.api?.getCfBypassConfig?.()
      if (json) {
        const cfg = JSON.parse(json)
        if (cfg.host) cfBypassHost.value = cfg.host
        if (cfg.port) cfBypassPort.value = cfg.port
        if (typeof cfg.use_external === 'boolean') cfBypassExternal.value = cfg.use_external
        cfBypassChanged.value = false
        break
      }
    } catch { /* API not ready yet */ }
    await new Promise(r => setTimeout(r, 200))
  }
  // 加载自动打开 PDF 设置
  for (let retry = 0; retry < 20; retry++) {
    try {
      const val = await (window as any).pywebview?.api?.getAutoOpenPdf?.()
      if (typeof val === 'boolean') {
        autoOpenPdf.value = val
        break
      }
    } catch { /* API not ready yet */ }
    await new Promise(r => setTimeout(r, 200))
  }
  // 加载自动下载阈值
  for (let retry = 0; retry < 20; retry++) {
    try {
      const val = await (window as any).pywebview?.api?.getAutoDownloadCount?.()
      if (typeof val === 'number') {
        autoDownloadCount.value = val
        break
      }
    } catch { /* API not ready yet */ }
    await new Promise(r => setTimeout(r, 200))
  }
  // 加载命名格式
  for (let retry = 0; retry < 20; retry++) {
    try {
      const val = await (window as any).pywebview?.api?.getNamingPattern?.()
      if (typeof val === 'string' && val) {
        namingPattern.value = val
        break
      }
    } catch { /* API not ready yet */ }
    await new Promise(r => setTimeout(r, 200))
  }
  // 加载下载失败打开 DOI 设置
  for (let retry = 0; retry < 20; retry++) {
    try {
      const val = await (window as any).pywebview?.api?.getAutoOpenDoiOnFail?.()
      if (typeof val === 'boolean') {
        autoOpenDoiOnFail.value = val
        break
      }
    } catch { /* API not ready yet */ }
    await new Promise(r => setTimeout(r, 200))
  }
  // 加载搜索引擎 URL
  for (let retry = 0; retry < 20; retry++) {
    try {
      const val = await (window as any).pywebview?.api?.getSearchUrl?.()
      if (typeof val === 'string' && val) {
        searchEngineUrl.value = val
        break
      }
    } catch { /* API not ready yet */ }
    await new Promise(r => setTimeout(r, 200))
  }
  // 加载显示设置
  for (let retry = 0; retry < 20; retry++) {
    try {
      const s = await (window as any).pywebview?.api?.getStatusBarEnabled?.()
      if (typeof s === 'boolean') { statusBarEnabled.value = s; }
      const r = await (window as any).pywebview?.api?.getResultAutoOpen?.()
      if (typeof r === 'boolean') { resultAutoOpen.value = r; }
      break
    } catch { /* API not ready yet */ }
    await new Promise(r => setTimeout(r, 200))
  }
})
onUnmounted(() => document.removeEventListener('keydown', onKeyDown))

// 窗口设置
const alwaysOnTop = ref(true)
const followMouse = ref(true)

// 存储设置
const storagePath = ref('./papers')

// CloudflareBypass 设置
const cfBypassHost = ref('127.0.0.1')
const cfBypassPort = ref(8000)
const cfBypassExternal = ref(false)
const cfBypassChanged = ref(false)

// 下载设置
const autoOpenPdf = ref(false)
const autoDownloadCount = ref(0)
const namingPattern = ref('{doi}.pdf')
const autoOpenDoiOnFail = ref(false)
const delaySeconds = ref(5)

// 搜索设置
const searchEngineUrl = ref('https://scholar.google.com/scholar?q={query}')
const searchEnginePresets = [
  'https://scholar.google.com/scholar?q={query}',
  'https://www.google.com/search?q={query}',
  'https://dblp.org/search?q={query}',
  'https://www.bing.com/search?q={query}',
  'https://arxiv.org/search/?query={query}&searchtype=all',
]

// 显示设置
const statusBarEnabled = ref(true)
const resultAutoOpen = ref(true)

// 事件处理
function applyHotkey() {
  if (!capturedHotkey.value) return
  emit('apply-hotkey', {
    modifiers: capturedModifiers.value,
    key: capturedKey.value,
  })
}

function onAlwaysOnTopChange(value: boolean) {
  emit('update-config', 'window.always_on_top', value)
}

function onFollowMouseChange(value: boolean) {
  emit('update-config', 'window.follow_mouse', value)
}

function openFolder() {
  ;(window as any).pywebview?.api?.openFile?.(storagePath.value)
}

// CF bypass 配置变更检测
watch([cfBypassHost, cfBypassPort, cfBypassExternal], () => {
  cfBypassChanged.value = true
})

async function applyCfBypass() {
  const api = (window as any).pywebview?.api
  if (!api?.setCfBypassConfig) return
  try {
    await api.setCfBypassConfig(cfBypassHost.value, cfBypassPort.value, cfBypassExternal.value)
    cfBypassChanged.value = false
  } catch (e) {
    console.error('应用 CF bypass 配置失败:', e)
  }
}

function onAutoOpenPdfChange(value: boolean) {
  ;(window as any).pywebview?.api?.setAutoOpenPdf?.(value)
}

function onAutoDownloadCountChange(value: string | number) {
  const num = typeof value === 'string' ? parseInt(value) : value
  ;(window as any).pywebview?.api?.setAutoDownloadCount?.(num || 0)
}

function onNamingPatternChange(value: string) {
  ;(window as any).pywebview?.api?.setNamingPattern?.(value)
}

function onAutoOpenDoiOnFailChange(value: boolean) {
  ;(window as any).pywebview?.api?.setAutoOpenDoiOnFail?.(value)
}

function onSearchUrlChange(value: string) {
  ;(window as any).pywebview?.api?.setSearchUrl?.(value)
}

function onStatusBarEnabledChange(value: boolean) {
  ;(window as any).pywebview?.api?.setStatusBarEnabled?.(value)
}

function onResultAutoOpenChange(value: boolean) {
  ;(window as any).pywebview?.api?.setResultAutoOpen?.(value)
}
</script>

<style scoped>
.hotkey-display {
  text-align: center;
}

:deep(.v-expansion-panel-title) {
  min-height: 36px;
  padding: 8px 12px;
  font-size: 13px;
}

:deep(.v-expansion-panel-text__wrapper) {
  padding: 8px 12px;
}
</style>
