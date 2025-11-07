import axios from 'axios'

const API_BASE_URL = 'https://compaasgold06.evl.uic.edu/api-vnava22'

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 300000,
  headers: {
    'Content-Type': 'application/x-www-form-urlencoded',
  },
})

export class SSEProgressClient {
  private eventSource: EventSource | null = null
  private onProgress: (data: any) => void
  private onComplete: (data: any) => void
  private onError: (error: string) => void
  private reconnectAttempts = 0
  private maxReconnectAttempts = 5
  private reconnectDelay = 3000
  private isCompleted = false
  private isClosed = false

  constructor(
    onProgress: (data: any) => void,
    onComplete: (data: any) => void,
    onError: (error: string) => void
  ) {
    this.onProgress = onProgress
    this.onComplete = onComplete
    this.onError = onError
  }

  connect(query: string) {
    if (this.isCompleted || this.isClosed) {
      return
    }
    
    if (this.eventSource) {
      this.eventSource.close()
      this.eventSource = null
    }
    
    const url = `${API_BASE_URL}/process-query-stream?query=${encodeURIComponent(query)}`
    
    this.eventSource = new EventSource(url)
    
    this.eventSource.onopen = () => {
      this.reconnectAttempts = 0
    }
    
    this.eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        
        if (data.step === 'connection') {
          return
        }
        
        if (data.step === 'complete') {
          this.isCompleted = true
          this.onComplete(data.data)
          this.close()
        } else if (data.step === 'stream-end') {
          this.isCompleted = true
          this.close()
        } else if (data.status === 'error') {
          this.isCompleted = true
          this.onError(data.message)
          this.close()
        } else {
          this.onProgress(data)
        }
      } catch (error) {
        this.onError('Failed to parse progress data')
      }
    }
    
    this.eventSource.onerror = () => {
      if (this.isCompleted || this.isClosed) {
        return
      }
      
      if (this.eventSource?.readyState === EventSource.CLOSED) {
        return
      }
      
      if (this.reconnectAttempts < this.maxReconnectAttempts) {
        this.reconnectAttempts++
        
        setTimeout(() => {
          if (!this.isCompleted && !this.isClosed) {
            this.close()
            // Note: reconnection not supported in current implementation
          }
        }, this.reconnectDelay)
      } else {
        this.isCompleted = true
        this.onError('Connection lost after multiple attempts')
        this.close()
      }
    }
  }

  close() {
    this.isClosed = true
    if (this.eventSource) {
      this.eventSource.close()
      this.eventSource = null
    }
  }
}

export interface SaveAccuracyMetricsRequest {
  video_id: string
  query: string
  correct: number
  incorrect: number
  not_needed: number
  missing: number
  total: number
  accuracy: number
  step_qualities: any[]
  bbox_verifications: any[]
}

export async function saveAccuracyMetrics(metrics: SaveAccuracyMetricsRequest): Promise<any> {
  const response = await apiClient.post('/save-accuracy-metrics', metrics, {
    headers: {
      'Content-Type': 'application/json',
    },
  })
  return response.data
}

export default apiClient
