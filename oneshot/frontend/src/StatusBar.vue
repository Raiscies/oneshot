<template>
  <div class="frame" @click="onClick" @contextmenu.prevent="onContextMenu">
    <div class="status-bar pywebview-drag-region">
      <div class="status-progress" :style="{ width: progressWidth }"></div>
      <span class="status-text">{{ statusText || 'OneShot' }}</span>
    </div>
  </div>
  <teleport to="body">
    <div v-if="showMenu" class="context-menu" :style="{ left: menuX + 'px', top: menuY + 'px' }">
      <div class="menu-item" @click="closeStatusBar">关闭浮窗</div>
    </div>
  </teleport>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'

const statusText = ref('')
const progress = ref(0)
const showMenu = ref(false)
const menuX = ref(0)
const menuY = ref(0)

const progressWidth = computed(() => {
  if (progress.value <= 0) return '0%'
  return Math.min(progress.value * 100, 100) + '%'
})

onMounted(() => {
  // Poll for status updates from backend
  const api = (window as any).pywebview?.api
  setInterval(async () => {
    try {
      const json = await api?.getStatus?.()
      if (json) {
        const data = JSON.parse(json)
        statusText.value = data.text || ''
        progress.value = data.progress || 0
      }
    } catch { /* ignore */ }
  }, 500)
})

function onClick() {
  showMenu.value = false
  ;(window as any).pywebview?.api?.showResultWindow?.()
}

function onContextMenu(e: MouseEvent) {
  menuX.value = e.clientX
  menuY.value = e.clientY
  showMenu.value = true
}

function closeStatusBar() {
  showMenu.value = false
  ;(window as any).pywebview?.api?.setStatusBarEnabled?.(false)
}

function onMouseDown() {
  showMenu.value = false
}

onMounted(() => document.addEventListener('mousedown', onMouseDown))
onUnmounted(() => document.removeEventListener('mousedown', onMouseDown))
</script>

<style scoped>
.frame {
  position: fixed;
  top: 0; left: 0; right: 0; bottom: 0;
  /* background: rgb(30, 30, 30); */
  background: transparent;
  border-radius: 5px 5px 0 0;
}

.status-bar {
  position: relative;
  display: flex;
  align-items: center;
  height: 32px;
  border-radius: 16px;
  overflow: hidden;
  cursor: pointer;
  user-select: none;
  /* background: rgba(30, 30, 30, 0.92); */
  background-color: rgb(30, 30, 30);
  backdrop-filter: blur(8px);
  /* background: transparent; */
  /* border: 1px solid rgba(255, 255, 255, 0.1); */
  padding: 0 14px;
}
.status-progress {
  position: absolute;
  left: 0;
  top: 0;
  height: 100%;
  background: rgba(var(--v-theme-primary), 0.25);
  transition: width 0.4s ease;
  border-radius: 16px;
}
.status-text {
  position: relative;
  z-index: 1;
  font-size: 12px;
  color: #ddd;
  white-space: nowrap;
  text-overflow: ellipsis;
  overflow: hidden;
}

.context-menu {
  position: fixed;
  z-index: 9999;
  background: #2a2a2a;
  border: 1px solid #444;
  border-radius: 6px;
  overflow: hidden;
  min-width: 100px;
  box-shadow: 0 4px 12px rgba(0,0,0,0.4);
}
.menu-item {
  padding: 6px 14px;
  font-size: 12px;
  color: #ddd;
  cursor: pointer;
}
.menu-item:hover {
  background: #3a3a3a;
}
</style>
