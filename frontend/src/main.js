// src/main.js
import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'

const app = createApp(App)

// Set up Pinia for state management
app.use(createPinia())

// Set up Vue Router
app.use(router)

app.mount('#app')