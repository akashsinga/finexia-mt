// src/services/websocket.js
import { useAuthStore } from '@/stores/auth'

class WebSocketService {
  constructor() {
    this.connections = {}
    this.listeners = {}
    this.connectionStatus = {}
  }

  connect(topic, taskId = null) {
    const authStore = useAuthStore()
    const token = authStore.token

    if (!token) {
      console.error('No authentication token available')
      return false
    }

    // Create connection key
    const connectionKey = taskId ? `${topic}_${taskId}` : topic

    // Check if already connected
    if (this.connections[connectionKey]) {
      return true
    }

    // Build websocket URL
    let wsUrl = `${import.meta.env.VITE_WS_BASE_URL || window.location.origin.replace('http', 'ws')}/ws/${topic}`
    if (taskId) {
      wsUrl += `/${taskId}`
    }

    // Add token to query parameters
    wsUrl += `?token=${token}`

    // Create WebSocket connection
    this.connections[connectionKey] = new WebSocket(wsUrl)
    this.connectionStatus[connectionKey] = 'connecting'

    // Set up event handlers
    this.connections[connectionKey].onopen = () => {
      console.log(`WebSocket connected: ${connectionKey}`)
      this.connectionStatus[connectionKey] = 'connected'
      this._notifyListeners(connectionKey, 'connection', { status: 'connected' })
    }

    this.connections[connectionKey].onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        this._notifyListeners(connectionKey, data.type, data)

        // Handle heartbeats
        if (data.type === 'heartbeat') {
          this.connections[connectionKey].send('heartbeat')
        }
      } catch (error) {
        console.error('Error parsing WebSocket message:', error)
      }
    }

    this.connections[connectionKey].onclose = () => {
      console.log(`WebSocket disconnected: ${connectionKey}`)
      this.connectionStatus[connectionKey] = 'disconnected'
      this._notifyListeners(connectionKey, 'connection', { status: 'disconnected' })
      delete this.connections[connectionKey]
    }

    this.connections[connectionKey].onerror = (error) => {
      console.error(`WebSocket error: ${connectionKey}`, error)
      this.connectionStatus[connectionKey] = 'error'
      this._notifyListeners(connectionKey, 'error', { error })
    }

    return true
  }

  disconnect(topic, taskId = null) {
    const connectionKey = taskId ? `${topic}_${taskId}` : topic

    if (this.connections[connectionKey]) {
      this.connections[connectionKey].close()
      delete this.connections[connectionKey]
      this.connectionStatus[connectionKey] = 'disconnected'
      return true
    }

    return false
  }

  addListener(topic, taskId, eventType, callback) {
    const connectionKey = taskId ? `${topic}_${taskId}` : topic

    if (!this.listeners[connectionKey]) {
      this.listeners[connectionKey] = {}
    }

    if (!this.listeners[connectionKey][eventType]) {
      this.listeners[connectionKey][eventType] = []
    }

    this.listeners[connectionKey][eventType].push(callback)
  }

  removeListener(topic, taskId, eventType, callback) {
    const connectionKey = taskId ? `${topic}_${taskId}` : topic

    if (!this.listeners[connectionKey] || !this.listeners[connectionKey][eventType]) {
      return false
    }

    this.listeners[connectionKey][eventType] = this.listeners[connectionKey][eventType]
      .filter(cb => cb !== callback)

    return true
  }

  _notifyListeners(connectionKey, eventType, data) {
    if (!this.listeners[connectionKey] || !this.listeners[connectionKey][eventType]) {
      return
    }

    this.listeners[connectionKey][eventType].forEach(callback => {
      try {
        callback(data)
      } catch (error) {
        console.error('Error in WebSocket listener callback:', error)
      }
    })
  }

  getStatus(topic, taskId = null) {
    const connectionKey = taskId ? `${topic}_${taskId}` : topic
    return this.connectionStatus[connectionKey] || 'disconnected'
  }
}

export const websocketService = new WebSocketService()