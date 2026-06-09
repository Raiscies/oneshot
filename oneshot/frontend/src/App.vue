<template>
  <v-app>
    <!-- 顶部导航栏 -->
    <v-app-bar color="primary" elevation="2" height="40" id="title-bar" class="pywebview-drag-region">
        <v-app-bar-title class="text-body-2">
          <v-icon icon="mdi-book-open-page-variant" size="small" class="mr-1"></v-icon>
          OneShot
        </v-app-bar-title>
        <template v-slot:append>
          <v-btn icon="mdi-theme-light-dark" variant="text" size="small" @click="toggleTheme" class="no-drag"></v-btn>
          <v-btn icon="mdi-close" variant="text" size="small" @click="onClose" class="no-drag"></v-btn>
        </template>
    </v-app-bar>

    <!-- 主内容：设置面板 -->
    <v-main class="main-content pt-12 px-2 pb-2">
      <SettingsPanel 
        :debug-mode="debugMode"
        @apply-hotkey="onApplyHotkey"
        @update-config="onUpdateConfig"
      />
    </v-main>

    <!-- 底部 --> 
    <v-footer app class="text-caption py-1">
      Vue 3 + Vuetify
    </v-footer>

    <!-- 提示组件 -->
    <v-snackbar v-model="snackbar.show" :color="snackbar.color" :timeout="2000">
      {{ snackbar.text }}
    </v-snackbar>

  </v-app>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { useTheme } from 'vuetify'
import SettingsPanel from './components/SettingsPanel.vue'
import { hideWindow } from './api'

// Theme
const theme = useTheme()
const toggleTheme = () => {
  theme.global.name.value = theme.global.current.value.dark ? 'light' : 'dark'
}

// 关闭按钮 → 隐藏窗口，保留托盘
function onClose() {
  hideWindow()
}

// ESC 隐藏窗口
function onKeyDown(e: KeyboardEvent) {
  if (e.key === 'Escape') hideWindow()
}

onMounted(() => document.addEventListener('keydown', onKeyDown))
onUnmounted(() => document.removeEventListener('keydown', onKeyDown))

// Debug mode
const debugMode = ref(true)

// Snackbar
const snackbar = ref({
  show: false,
  text: '',
  color: 'success',
})

// 设置事件
function onApplyHotkey(hotkey: { modifiers: string[], key: string }) {
  console.log('应用快捷键:', hotkey)
  window.pywebview?.api?.setHotkey?.(hotkey.modifiers, hotkey.key)
  snackbar.value = { show: true, text: `快捷键已更新: ${hotkey.modifiers.join('+').toUpperCase()}+${hotkey.key.toUpperCase()}`, color: 'success' }
}

function onUpdateConfig(key: string, value: any) {
  console.log('更新配置:', key, value)
}
</script>

<style>
/* 主内容区域可滚动 */
.main-content {
  overflow-y: auto;
  height: calc(100vh - 40px - 24px); /* 减去 app-bar 和 footer */
}

/* 标题栏拖动样式 */
#title-bar {
  cursor: move;
  user-select: none;
}

.no-drag {
  cursor: default !important;
}
</style>
