import React, { useState } from 'react'
import { useSelector } from 'react-redux'
import { RootState } from '../store/store'
import QueryInput from './QueryInput'
import ProcessingPipeline from './ProcessingPipeline'
import ResultsDisplay from './ResultsDisplay'
import ErrorDisplay from './ErrorDisplay'
import { Smartphone, BookOpen, Search, ZoomIn, MousePointer } from 'lucide-react'

const TabbedInterface: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'query' | 'results'>('query')
  const { isProcessing, error, results } = useSelector((state: RootState) => state.videoAnalysis)

  React.useEffect(() => {
    if (isProcessing || results.length > 0) {
      setActiveTab('results')
    }
  }, [isProcessing, results.length])

  const renderEmptyState = () => (
    <div className="text-center">
      <div>
        <div className="inline-flex items-center justify-center w-12 h-12 sm:w-16 sm:h-16 bg-gradient-to-br from-primary-100 to-primary-200 rounded-full mb-3 sm:mb-4 animate-pulse">
          <Smartphone className="h-6 w-6 sm:h-8 sm:w-8 text-primary-600" />
        </div>
        
        <h3 className="text-xl sm:text-2xl font-bold text-gray-900 mb-2">Your Visual Guide Will Appear Here</h3>
        <p className="text-base sm:text-lg text-gray-600 mb-4 sm:mb-6 leading-relaxed">
          Once you ask a question, we'll create a step-by-step visual guide just for you.
        </p>

        <div className="bg-white rounded-2xl p-4 sm:p-6 shadow-lg border border-gray-100 mb-6 sm:mb-8">
          <h4 className="text-lg sm:text-xl font-bold text-gray-900 mb-4 sm:mb-6 text-center">How it works:</h4>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 sm:gap-6">
            <div className="text-center">
              <div className="inline-flex items-center justify-center w-10 h-10 sm:w-12 sm:h-12 bg-gradient-to-r from-primary-600 to-primary-700 text-white rounded-full mb-2 sm:mb-3 text-sm sm:text-base font-bold">1</div>
              <h5 className="text-xs sm:text-sm font-semibold text-gray-900 mb-1">Ask Your Question</h5>
              <p className="text-gray-600 text-xs">Tell us what you need help with</p>
            </div>
            <div className="text-center">
              <div className="inline-flex items-center justify-center w-10 h-10 sm:w-12 sm:h-12 bg-gradient-to-r from-primary-600 to-primary-700 text-white rounded-full mb-2 sm:mb-3 text-sm sm:text-base font-bold">2</div>
              <h5 className="text-xs sm:text-sm font-semibold text-gray-900 mb-1">We Find a Video</h5>
              <p className="text-gray-600 text-xs">We search for the best tutorial</p>
            </div>
            <div className="text-center">
              <div className="inline-flex items-center justify-center w-10 h-10 sm:w-12 sm:h-12 bg-gradient-to-r from-primary-600 to-primary-700 text-white rounded-full mb-2 sm:mb-3 text-sm sm:text-base font-bold">3</div>
              <h5 className="text-xs sm:text-sm font-semibold text-gray-900 mb-1">Create Your Guide</h5>
              <p className="text-gray-600 text-xs">We make clear step-by-step images</p>
            </div>
            <div className="text-center">
              <div className="inline-flex items-center justify-center w-10 h-10 sm:w-12 sm:h-12 bg-gradient-to-r from-primary-600 to-primary-700 text-white rounded-full mb-2 sm:mb-3 text-sm sm:text-base font-bold">4</div>
              <h5 className="text-xs sm:text-sm font-semibold text-gray-900 mb-1">Follow Along</h5>
              <p className="text-gray-600 text-xs">Use your guide at your own pace</p>
            </div>
          </div>
        </div>

        <div className="bg-gradient-to-br from-primary-50 to-primary-100 rounded-2xl p-4 sm:p-6 border border-primary-200">
          <h4 className="text-base sm:text-lg font-bold text-primary-900 mb-3 sm:mb-4 text-center">What you'll get:</h4>
          <div className="border border-gray-200 rounded-lg p-4 sm:p-6 bg-white shadow-sm">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center space-x-3">
                <div className="flex items-center justify-center min-w-[2.75rem] h-11 bg-primary-600 text-white rounded-lg font-semibold text-base px-3">
                  Step 1
                </div>
                <div className="flex items-center space-x-2">
                  <MousePointer className="h-5 w-5 text-primary-600" />
                  <span className="text-sm sm:text-base font-semibold text-gray-900">Click at coordinates (220, 480)</span>
                </div>
              </div>
              <div className="flex items-center space-x-2 text-gray-400">
                <ZoomIn className="h-5 w-5" />
                <span className="text-xs font-medium">Tap to enlarge</span>
              </div>
            </div>
            
            <p className="text-sm text-gray-600 mb-4 italic">"Tap the Settings app on your home screen"</p>
            
            <div className="rounded-lg border border-gray-200 overflow-hidden">
              <div className="bg-gray-100 rounded-lg p-3 text-center">
                <div className="w-full h-32 bg-gray-300 rounded-lg mx-auto mb-1"></div>
                <p className="text-xs text-gray-600">Screenshot with highlighted area</p>
              </div>
            </div>
          </div>
        </div>

        <div className="mt-6 sm:mt-8">
          <button
            onClick={() => setActiveTab('query')}
            className="bg-gradient-to-r from-primary-600 to-primary-700 hover:from-primary-700 hover:to-primary-800 text-white font-semibold py-3 sm:py-4 px-6 sm:px-8 rounded-xl transition-all duration-200 shadow-lg hover:shadow-xl flex items-center space-x-2 sm:space-x-3 mx-auto transform hover:scale-105 text-base sm:text-lg"
          >
            <Search className="h-5 w-5 sm:h-6 sm:w-6" />
            <span>Ask Your Question Now</span>
          </button>
        </div>
      </div>
    </div>
  )

  return (
    <div className="bg-white rounded-2xl shadow-lg border border-gray-100 overflow-hidden">
      <div className="flex border-b border-gray-200">
        <button
          onClick={() => setActiveTab('query')}
          className={`flex-1 py-4 px-6 text-lg font-semibold transition-all duration-200 flex items-center justify-center space-x-3 ${
            activeTab === 'query'
              ? 'bg-primary-50 text-primary-700 border-b-2 border-primary-600'
              : 'text-gray-600 hover:text-gray-900 hover:bg-gray-50'
          }`}
        >
          <Search className="h-6 w-6" />
          <span>Ask a Question</span>
        </button>
        <button
          onClick={() => setActiveTab('results')}
          className={`flex-1 py-4 px-6 text-lg font-semibold transition-all duration-200 flex items-center justify-center space-x-3 ${
            activeTab === 'results'
              ? 'bg-primary-50 text-primary-700 border-b-2 border-primary-600'
              : 'text-gray-600 hover:text-gray-900 hover:bg-gray-50'
          }`}
        >
          <BookOpen className="h-6 w-6" />
          <span>Your Guide</span>
          {results.length > 0 && (
            <div className="w-2 h-2 bg-primary-600 rounded-full"></div>
          )}
        </button>
      </div>

      <div className="p-4 sm:p-6">
        {activeTab === 'query' && (
          <div>
            <QueryInput />
          </div>
        )}

        {activeTab === 'results' && (
          <div>
            {isProcessing && (
              <div className="mb-8">
                <ProcessingPipeline />
              </div>
            )}

            {error && (
              <div className="mb-8">
                <ErrorDisplay />
              </div>
            )}

            {results.length > 0 && (
              <div className="mb-8">
                <ResultsDisplay />
              </div>
            )}

            {!isProcessing && !error && results.length === 0 && renderEmptyState()}
          </div>
        )}
      </div>
    </div>
  )
}

export default TabbedInterface
