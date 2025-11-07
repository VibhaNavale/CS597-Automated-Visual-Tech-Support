import React from 'react'
import { Smartphone, HelpCircle, Users, FlaskConical } from 'lucide-react'
import { useSelector, useDispatch } from 'react-redux'
import { RootState } from '../store/store'
import { toggleTestMode } from '../store/slices/videoAnalysisSlice'

const Header: React.FC = () => {
  const dispatch = useDispatch()
  const { testMode, results } = useSelector((state: RootState) => state.videoAnalysis)
  const hasResults = results.length > 0

  return (
    <header className="bg-gradient-to-r from-primary-600 to-primary-700 shadow-lg">
      <div className="container mx-auto px-4 sm:px-6 py-4 sm:py-6 max-w-6xl">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3 sm:space-x-4">
            <div className="flex items-center space-x-2 bg-white/10 rounded-lg p-2 sm:p-3">
              <Smartphone className="h-6 w-6 sm:h-8 sm:w-8 text-white" />
              <HelpCircle className="h-5 w-5 sm:h-6 sm:w-6 text-primary-200" />
            </div>
            <div>
              <h1 className="text-xl sm:text-2xl font-bold text-white mb-0.5 sm:mb-1">Mobile Tech Support</h1>
              <p className="text-sm sm:text-base text-primary-100">Step-by-step visual guides for your phone</p>
            </div>
          </div>
          <div className="flex items-center space-x-4">
            {hasResults && (
              <button
                onClick={() => dispatch(toggleTestMode())}
                className={`flex items-center space-x-2 px-4 py-2 rounded-lg transition-colors ${
                  testMode
                    ? 'bg-amber-500 hover:bg-amber-600 text-white'
                    : 'bg-white/20 hover:bg-white/30 text-white'
                }`}
                title="Toggle test mode for bbox verification"
              >
                <FlaskConical className="h-4 w-4" />
                <span className="text-sm font-medium">Test Mode</span>
              </button>
            )}
            <div className="hidden md:flex items-center space-x-2 text-primary-100">
            <Users className="h-4 w-4" />
            <span className="text-xs font-medium">Designed for older adults</span>
            </div>
          </div>
        </div>
      </div>
    </header>
  )
}

export default Header
