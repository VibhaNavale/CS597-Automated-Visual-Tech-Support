import { createSlice, createAsyncThunk, PayloadAction } from '@reduxjs/toolkit'
import { apiClient, SSEProgressClient } from '../../services/api'

export interface ProcessingStep {
  id: string
  name: string
  status: 'pending' | 'active' | 'completed' | 'error'
  message?: string
  data?: any
}

export interface OSAtlasResult {
  step: number
  action: string
  boundingBox: {
    x: number
    y: number
    width: number
    height: number
  }
  image: string
  thought?: string
  stepQuality?: 'good' | 'bad' | 'repeated' | 'not_relevant'
  bboxVerification?: 'correct' | 'incorrect' | 'not_needed' | 'missing'
}

export interface TimingMetrics {
  [key: string]: {
    duration: number
  }
}

export interface TestMetrics {
  correct: number
  incorrect: number
  notNeeded: number
  missing: number
  total: number
  accuracy: number
}

export interface VideoAnalysisState {
  query: string
  isProcessing: boolean
  currentStep: string | null
  steps: ProcessingStep[]
  results: OSAtlasResult[]
  error: string | null
  progress: number
  testMode: boolean
  timingMetrics: TimingMetrics | null
  testMetrics: TestMetrics | null
  videoId: string | null
}

const initialState: VideoAnalysisState = {
  query: '',
  isProcessing: false,
  currentStep: null,
  steps: [
    { id: 'video-search', name: 'Searching for Video', status: 'pending' },
    { id: 'video-download', name: 'Downloading Video', status: 'pending' },
    { id: 'frame-extraction', name: 'Extracting Frames', status: 'pending' },
    { id: 'ui-screens', name: 'Extracting UI Screens', status: 'pending' },
    { id: 'osatlas-processing', name: 'OS-Atlas Analysis', status: 'pending' },
  ],
  results: [],
  error: null,
  progress: 0,
  testMode: false,
  timingMetrics: null,
  testMetrics: null,
  videoId: null,
}

export const processVideoQuery = createAsyncThunk(
  'videoAnalysis/processQuery',
  async (query: string, { dispatch, rejectWithValue }) => {
    return new Promise((resolve, reject) => {
      let sseClient: SSEProgressClient | null = null
      let fallbackTimeout: ReturnType<typeof setTimeout> | null = null
      
      fallbackTimeout = setTimeout(() => {
        if (sseClient) {
          sseClient.close()
        }
        
        apiClient.post('/process-query', { query })
          .then(response => {
            dispatch(setProgress(100))
            resolve(response.data || [])
          })
          .catch(error => {
            reject(rejectWithValue(error.response?.data?.error || 'Analysis failed'))
          })
      }, 600000)
      
      sseClient = new SSEProgressClient(
        (data) => {
          if (data.step && data.status) {
            dispatch(updateStepStatus({
              stepId: data.step,
              status: data.status,
              message: data.message
            }))
          }
          
          const stepProgress = {
                'video-search': 10,
                'video-download': 20,
                'frame-extraction': 35,
                'ui-screens': 50,
                'osatlas-processing': 90
              }
          
          if (data.step && data.status === 'completed') {
            const progress = stepProgress[data.step as keyof typeof stepProgress] || 0
            dispatch(setProgress(progress))
            dispatch(updateStepStatus({ stepId: data.step, status: 'completed', message: data.message }))
          } else if (data.step && data.status === 'active') {
            let progress = stepProgress[data.step as keyof typeof stepProgress] || 0
            
            if (data.step === 'osatlas-processing' && data.message && data.message.includes('Processing frame')) {
              const frameMatch = data.message.match(/Processing frame (\d+)\/(\d+)/)
              if (frameMatch) {
                const currentFrame = parseInt(frameMatch[1])
                const totalFrames = parseInt(frameMatch[2])
                const osatlasProgress = 50 + (currentFrame / totalFrames) * 40
                progress = Math.round(osatlasProgress)
              }
            }
            
            dispatch(setProgress(progress))
          }
        },
        (data) => {
          if (fallbackTimeout) clearTimeout(fallbackTimeout)
          
          dispatch(setProgress(100))
          
          dispatch(updateStepStatus({ stepId: 'video-search', status: 'completed' }))
          dispatch(updateStepStatus({ stepId: 'video-download', status: 'completed' }))
          dispatch(updateStepStatus({ stepId: 'frame-extraction', status: 'completed' }))
          dispatch(updateStepStatus({ stepId: 'ui-screens', status: 'completed' }))
          dispatch(updateStepStatus({ stepId: 'osatlas-processing', status: 'completed' }))
          
          const results = data.results || []
          
          if (data.timing) {
            dispatch(setTimingMetrics(data.timing))
          }
          
          if (data.video_id) {
            dispatch(setVideoId(data.video_id))
          }
          
          resolve(results)
        },
        (error) => {
          if (fallbackTimeout) clearTimeout(fallbackTimeout)
          reject(rejectWithValue(error))
        }
      )
      
      sseClient.connect(query)
    })
  }
)

const videoAnalysisSlice = createSlice({
  name: 'videoAnalysis',
  initialState,
  reducers: {
    setQuery: (state, action: PayloadAction<string>) => {
      state.query = action.payload
    },
    resetAnalysis: (state) => {
      state.isProcessing = false
      state.currentStep = null
      state.steps = initialState.steps
      state.results = []
      state.error = null
      state.progress = 0
      state.timingMetrics = null
      state.testMetrics = null
      state.videoId = null
    },
    toggleTestMode: (state) => {
      state.testMode = !state.testMode
    },
    verifyStepQuality: (state, action: PayloadAction<{ step: number; quality: 'good' | 'bad' | 'repeated' | 'not_relevant' }>) => {
      const result = state.results.find(r => r.step === action.payload.step)
      if (result) {
        result.stepQuality = action.payload.quality
      }
    },
    verifyBbox: (state, action: PayloadAction<{ step: number; verification: 'correct' | 'incorrect' | 'not_needed' | 'missing' }>) => {
      const result = state.results.find(r => r.step === action.payload.step)
      if (result) {
        result.bboxVerification = action.payload.verification
      }
      // Recalculate metrics
      const metrics = calculateTestMetrics(state.results)
      state.testMetrics = metrics
    },
    setTimingMetrics: (state, action: PayloadAction<TimingMetrics>) => {
      state.timingMetrics = action.payload
    },
    setVideoId: (state, action: PayloadAction<string>) => {
      state.videoId = action.payload
    },
    updateStepStatus: (state, action: PayloadAction<{ stepId: string; status: ProcessingStep['status']; message?: string }>) => {
      const step = state.steps.find(s => s.id === action.payload.stepId)
      if (step) {
        step.status = action.payload.status
        step.message = action.payload.message
      }
    },
    addResult: (state, action: PayloadAction<OSAtlasResult>) => {
      state.results.push(action.payload)
    },
    setProgress: (state, action: PayloadAction<number>) => {
      state.progress = action.payload
    },
    addStepResult: (state, action: PayloadAction<OSAtlasResult>) => {
      const existingIndex = state.results.findIndex(r => r.step === action.payload.step)
      if (existingIndex >= 0) {
        state.results[existingIndex] = action.payload
      } else {
        state.results.push(action.payload)
      }
      state.results.sort((a, b) => a.step - b.step)
    },
    clearResults: (state) => {
      state.results = []
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(processVideoQuery.pending, (state) => {
        state.isProcessing = true
        state.error = null
        state.currentStep = 'video-search'
        state.progress = 0
        state.results = []
        state.steps.forEach(step => {
          step.status = 'pending'
          step.message = undefined
        })
      })
          .addCase(processVideoQuery.fulfilled, (state, action) => {
            state.isProcessing = false
            state.currentStep = null
            state.progress = 100
            
            state.steps.forEach(step => {
              step.status = 'completed'
            })
            
            if (action.payload && Array.isArray(action.payload)) {
              state.results = action.payload
            }
          })
      .addCase(processVideoQuery.rejected, (state, action) => {
        state.isProcessing = false
        state.currentStep = null
        state.error = action.payload as string
        state.progress = 0
      })
  },
})

function calculateTestMetrics(results: OSAtlasResult[]): TestMetrics {
  const metrics = {
    correct: 0,
    incorrect: 0,
    notNeeded: 0,
    missing: 0,
    total: results.length,
    accuracy: 0
  }
  
  results.forEach(result => {
    const verification = result.bboxVerification
    if (verification === 'correct') metrics.correct++
    else if (verification === 'incorrect') metrics.incorrect++
    else if (verification === 'not_needed') metrics.notNeeded++
    else if (verification === 'missing') metrics.missing++
  })
  
  // Calculate accuracy: only correct bboxes count as success
  // - Correct: bbox is needed AND accurate
  // - Incorrect: bbox is needed BUT wrong
  // - Not Needed: bbox not needed (may still have one, which is extra) - neutral
  // - Missing: bbox needed BUT not present
  const verified = metrics.correct + metrics.incorrect + metrics.notNeeded + metrics.missing
  if (verified > 0) {
    // Only count "correct" as success - incorrect, missing, and not_needed all reduce accuracy
    metrics.accuracy = (metrics.correct / verified) * 100
  }
  
  return metrics
}

export const { setQuery, resetAnalysis, updateStepStatus, addResult, setProgress, addStepResult, clearResults, toggleTestMode, verifyStepQuality, verifyBbox, setTimingMetrics, setVideoId } = videoAnalysisSlice.actions
export default videoAnalysisSlice.reducer
