import 'vuetify/styles'
import '@mdi/font/css/materialdesignicons.css'
import { createVuetify } from 'vuetify'
import * as components from 'vuetify/components'
import * as directives from 'vuetify/directives'

export default createVuetify({
  components,
  directives,
  theme: {
    defaultTheme: 'light',
    themes: {
      light: {
        colors: {
          primary: '#4F46E5',
          secondary: '#7C3AED',
          accent: '#EC4899',
          error: '#EF4444',
          warning: '#F59E0B',
          info: '#3B82F6',
          success: '#10B981',
        },
      },
      dark: {
        colors: {
          primary: '#818CF8',
          secondary: '#A78BFA',
          accent: '#F472B6',
          error: '#F87171',
          warning: '#FBBF24',
          info: '#60A5FA',
          success: '#34D399',
        },
      },
    },
  },
  defaults: {
    VBtn: {
      variant: 'flat',
    },
    VCard: {
      variant: 'flat',
    },
  },
})
