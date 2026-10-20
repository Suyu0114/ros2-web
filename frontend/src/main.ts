import 'leaflet/dist/leaflet.css'
import './style.css'

import { createApp } from 'vue'

import App from './App.vue'
import { loadConfig } from './config'

createApp(App, { config: await loadConfig() }).mount('#app')
