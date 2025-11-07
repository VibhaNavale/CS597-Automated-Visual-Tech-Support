import React, { useState } from 'react'
import { useDispatch, useSelector } from 'react-redux'
import { RootState } from '../store/store'
import { setQuery, processVideoQuery, resetAnalysis } from '../store/slices/videoAnalysisSlice'
import { Search, Loader2, MessageCircle, RotateCcw } from 'lucide-react'

const QueryInput: React.FC = () => {
  const dispatch = useDispatch()
  const { query, isProcessing } = useSelector((state: RootState) => state.videoAnalysis)
  const [localQuery, setLocalQuery] = useState(query)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!localQuery.trim() || isProcessing) return

    dispatch(setQuery(localQuery))
    dispatch(resetAnalysis())
    dispatch(processVideoQuery(localQuery) as any)
  }

  const handleReset = () => {
    setLocalQuery('')
    dispatch(resetAnalysis())
  }

  const exampleQueries = [
    "How to enable dark mode on WhatsApp?",
    "How to increase font size on an iPhone?",
    "How to set up Apple Mail on an iPhone?",
    "How do I turn off dark mode in the YouTube app on my phone?"
  ]

  return (
    <div className="transform transition-all duration-300">
      <div className="text-center mb-6 sm:mb-8">
        <div className="inline-flex items-center justify-center w-12 h-12 sm:w-16 sm:h-16 bg-gradient-to-br from-primary-100 to-primary-200 rounded-full mb-3 sm:mb-4 animate-pulse">
          <MessageCircle className="h-6 w-6 sm:h-8 sm:w-8 text-primary-600" />
        </div>
        <h2 className="text-xl sm:text-2xl font-bold text-gray-900 mb-2">What would you like help with?</h2>
        <p className="text-base sm:text-lg text-gray-600 max-w-2xl mx-auto">
          Tell us about any phone task you need help with. We'll create a step-by-step visual guide just for you.
        </p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-4 sm:space-y-6">
        <div>
          <label htmlFor="query" className="block text-base sm:text-lg font-semibold text-gray-800 mb-2 sm:mb-3">
            Describe your question or task
          </label>
          <div className="relative">
            <textarea
              id="query"
              value={localQuery}
              onChange={(e) => setLocalQuery(e.target.value)}
              placeholder="For example: How do I change my phone's ringtone?"
              className="w-full px-4 sm:px-6 py-2 sm:py-3 text-base sm:text-lg border-2 border-gray-200 rounded-xl focus:outline-none focus:ring-4 focus:ring-primary-100 focus:border-primary-400 resize-none transition-all duration-200 hover:border-primary-300"
              rows={1}
              disabled={isProcessing}
            />
            <Search className="absolute right-3 sm:right-4 top-3 sm:top-4 h-5 w-5 sm:h-6 sm:w-6 text-gray-400" />
          </div>
        </div>

        <div className="flex flex-col sm:flex-row gap-3 sm:gap-4">
          <button
            type="submit"
            disabled={!localQuery.trim() || isProcessing}
            className="flex-1 bg-gradient-to-r from-primary-600 to-primary-700 hover:from-primary-700 hover:to-primary-800 text-white font-semibold py-3 sm:py-4 px-6 sm:px-8 rounded-xl transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed text-base sm:text-lg shadow-lg hover:shadow-xl flex items-center justify-center space-x-2 sm:space-x-3 transform hover:scale-105"
          >
            {isProcessing ? (
              <>
                <Loader2 className="h-5 w-5 sm:h-6 sm:w-6 animate-spin" />
                <span>Creating your guide...</span>
              </>
            ) : (
              <>
                <Search className="h-5 w-5 sm:h-6 sm:w-6" />
                <span>Create Visual Guide</span>
              </>
            )}
          </button>
          
          {!isProcessing && localQuery.trim() && (
            <button
              type="button"
              onClick={handleReset}
              className="bg-gray-100 hover:bg-gray-200 text-gray-700 font-semibold py-3 sm:py-4 px-4 sm:px-6 rounded-xl transition-all duration-200 flex items-center space-x-2"
            >
              <RotateCcw className="h-4 w-4 sm:h-5 sm:w-5" />
              <span>Clear</span>
            </button>
          )}
        </div>
      </form>

      {!isProcessing && (
        <div className="mt-6 sm:mt-8 p-4 sm:p-6 bg-gradient-to-br from-primary-50 to-primary-100 rounded-xl border border-primary-200">
          <h3 className="text-base sm:text-lg font-semibold text-primary-900 mb-3">Need ideas? Try these examples:</h3>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 sm:gap-3">
            {exampleQueries.map((example, index) => (
              <button
                key={index}
                onClick={() => setLocalQuery(example)}
                className="text-left p-2 sm:p-3 bg-white rounded-lg border border-primary-200 hover:border-primary-400 hover:bg-primary-50 transition-all duration-200 text-primary-800 transform hover:scale-102 text-sm sm:text-base"
                disabled={isProcessing}
              >
                {example}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

export default QueryInput
