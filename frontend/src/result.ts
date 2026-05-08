import { createApp } from 'vue'
import { createVuetify } from 'vuetify'
import * as components from 'vuetify/components'
import * as directives from 'vuetify/directives'
import 'vuetify/styles'
import '@mdi/font/css/materialdesignicons.css'
import ResultApp from './ResultApp.vue'

// 创建 Vuetify 实例
const vuetify = createVuetify({
  components,
  directives,
  theme: {
    defaultTheme: 'dark',
    themes: {
      dark: {
        colors: {
          primary: '#2196F3',
          surface: '#1a1a1a',
        },
      },
    },
  },
})

// 创建 Vue 应用
const app = createApp(ResultApp)
app.use(vuetify)
app.mount('#app')