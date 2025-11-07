import { configureStore } from '@reduxjs/toolkit'
import videoAnalysisReducer from './slices/videoAnalysisSlice'

export const store = configureStore({
  reducer: {
    videoAnalysis: videoAnalysisReducer,
  },
})

export type RootState = ReturnType<typeof store.getState>
export type AppDispatch = typeof store.dispatch
