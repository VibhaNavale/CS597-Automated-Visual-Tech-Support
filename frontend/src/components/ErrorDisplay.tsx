import React from 'react'
import { useSelector, useDispatch } from 'react-redux'
import { RootState } from '../store/store'
import { resetAnalysis } from '../store/slices/videoAnalysisSlice'
import { AlertCircle, RefreshCw, HelpCircle } from 'lucide-react'

const ErrorDisplay: React.FC = () => {
  const dispatch = useDispatch()
  const { error } = useSelector((state: RootState) => state.videoAnalysis)

  const handleRetry = () => {
    dispatch(resetAnalysis())
  }

  const getFriendlyErrorMessage = (error: string) => {
    if (error.includes('quota')) {
      return "We're experiencing high demand right now. Please try again in a few minutes."
    }
    if (error.includes('video') || error.includes('No suitable video')) {
      return "We couldn't find a suitable tutorial video. Try rephrasing your question or asking about a different phone task."
    }
    if (error.includes('network') || error.includes('connection')) {
      return "There's a connection issue. Please check your internet connection and try again."
    }
    return "Something went wrong while creating your guide. Please try again."
  }

  return (
    <div className="bg-red-50 border-2 border-red-200 rounded-2xl p-8 shadow-lg">
      <div className="text-center mb-6">
        <div className="inline-flex items-center justify-center w-16 h-16 bg-red-100 rounded-full mb-4">
          <AlertCircle className="h-8 w-8 text-red-600" />
        </div>
        <h3 className="text-2xl font-bold text-red-800 mb-2">Oops! Something went wrong</h3>
        <p className="text-lg text-red-700">{getFriendlyErrorMessage(error || '')}</p>
      </div>

      <div className="bg-white rounded-xl p-6 mb-6">
        <div className="flex items-start space-x-4">
          <HelpCircle className="h-6 w-6 text-blue-600 mt-1 flex-shrink-0" />
          <div>
            <h4 className="text-lg font-semibold text-gray-900 mb-2">What you can try:</h4>
            <ul className="space-y-2 text-gray-700">
              <li className="flex items-start space-x-2">
                <span className="text-blue-600 font-bold">•</span>
                <span>Make sure your question is clear and specific</span>
              </li>
              <li className="flex items-start space-x-2">
                <span className="text-blue-600 font-bold">•</span>
                <span>Try asking about a different phone task</span>
              </li>
              <li className="flex items-start space-x-2">
                <span className="text-blue-600 font-bold">•</span>
                <span>Check your internet connection</span>
              </li>
              <li className="flex items-start space-x-2">
                <span className="text-blue-600 font-bold">•</span>
                <span>Wait a few minutes and try again</span>
              </li>
            </ul>
          </div>
        </div>
      </div>

      <div className="text-center">
        <button
          onClick={handleRetry}
          className="bg-red-600 hover:bg-red-700 text-white font-semibold py-4 px-8 rounded-xl transition-all duration-200 text-lg shadow-lg hover:shadow-xl flex items-center space-x-3 mx-auto"
        >
          <RefreshCw className="h-6 w-6" />
          <span>Try Again</span>
        </button>
      </div>
    </div>
  )
}

export default ErrorDisplay
