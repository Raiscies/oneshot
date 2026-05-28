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
              <v-chip size="large" color="primary" variant="flat">
                {{ hotkeyDisplay }}
              </v-chip>
            </div>
            
            <div class="modifiers-section mb-4">
              <p class="text-caption text-grey mb-2">修饰键</p>
              <v-chip-group v-model="selectedModifiers" multiple selected-class="text-primary">
                <v-chip
                  v-for="mod in modifiers"
                  :key="mod.value"
                  :value="mod.value"
                  filter
                  variant="outlined"
                >
                  {{ mod.label }}
                </v-chip>
              </v-chip-group>
            </div>
            
            <div class="key-section mb-4">
              <p class="text-caption text-grey mb-2">功能键</p>
              <v-btn-toggle v-model="selectedKey" mandatory>
                <v-btn value="q">Q</v-btn>
                <v-btn value="l">L</v-btn>
                <v-btn value="k">K</v-btn>
                <v-btn value="j">J</v-btn>
              </v-btn-toggle>
            </div>
            
            <v-btn color="primary" @click="applyHotkey">
              应用快捷键
            </v-btn>
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
    
    <v-card-actions v-if="debugMode">
      <v-btn color="error" variant="tonal" @click="showTestDialog">
        <v-icon start icon="mdi-bug"></v-icon>
        测试弹窗
      </v-btn>
    </v-card-actions>
  </v-card>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { showResultDialog } from '../api'

// Props
const props = defineProps<{
  debugMode?: boolean
  showResultDialog?: boolean
  testPapers?: any[]
}>()

// Emits
const emit = defineEmits<{
  'apply-hotkey': [hotkey: { modifiers: string[], key: string }]
  'update-config': [key: string, value: any]
  'show-test-dialog': []
  'update:show-result-dialog': [val: boolean]
}>()

// 快捷键设置
const modifiers = [
  { label: 'Ctrl', value: 'ctrl' },
  { label: 'Shift', value: 'shift' },
  { label: 'Alt', value: 'alt' },
]
const selectedModifiers = ref<string[]>(['ctrl'])
const selectedKey = ref('q')

const hotkeyDisplay = computed(() => {
  const mods = selectedModifiers.value.map(m => m.toUpperCase()).join('+')
  return `${mods}+${selectedKey.value.toUpperCase()}`
})

// 窗口设置
const alwaysOnTop = ref(true)
const followMouse = ref(true)

// 存储设置
const storagePath = ref('./papers')

// 事件处理
function applyHotkey() {
  emit('apply-hotkey', {
    modifiers: selectedModifiers.value,
    key: selectedKey.value,
  })
}

function onAlwaysOnTopChange(value: boolean) {
  emit('update-config', 'window.always_on_top', value)
}

function onFollowMouseChange(value: boolean) {
  emit('update-config', 'window.follow_mouse', value)
}

function openFolder() {
  // TODO: 调用 Python 后端打开文件夹
  console.log('打开目录:', storagePath.value)
}

function showTestDialog() {
  // 调用 pywebview API 在新窗口中显示结果
  if (props.testPapers) {
    showResultDialog(props.testPapers, '[19] Robert Geisberger et al. 2008...')
  }
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
