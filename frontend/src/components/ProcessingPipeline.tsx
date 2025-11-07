import React from 'react'
import { useSelector } from 'react-redux'
import { RootState } from '../store/store'
import { CheckCircle, Clock, AlertCircle, Loader2, Search, Download, Scissors, Smartphone, Cog } from 'lucide-react'

const ProcessingPipeline: React.FC = () => {
  const { steps, progress } = useSelector((state: RootState) => state.videoAnalysis)

  const getStepIcon = (step: any) => {
    const iconMap = {
      'video-search': Search,
      'video-download': Download,
      'frame-extraction': Scissors,
      'ui-screens': Smartphone,
      'osatlas-processing': Cog
    }
    
    const IconComponent = iconMap[step.id as keyof typeof iconMap] || Clock
    
    switch (step.status) {
      case 'completed':
        return <CheckCircle className="h-6 w-6 text-green-600" />
      case 'active':
        return <Loader2 className="h-6 w-6 text-primary-600 animate-spin" />
      case 'error':
        return <AlertCircle className="h-6 w-6 text-red-600 animate-pulse" />
      default:
        return <IconComponent className="h-6 w-6 text-primary-400" />
    }
  }

  const getStepClasses = (step: any) => {
    const baseClasses = "flex items-center justify-center w-12 h-12 rounded-full text-sm font-semibold transition-all duration-300"
    switch (step.status) {
      case 'completed':
        return `${baseClasses} bg-green-100 text-green-700 border-2 border-green-300`
      case 'active':
        return `${baseClasses} bg-primary-100 text-primary-700 border-2 border-primary-300 shadow-lg transform scale-110`
      case 'error':
        return `${baseClasses} bg-red-100 text-red-700 border-2 border-red-300`
      default:
        return `${baseClasses} bg-gray-100 text-gray-500 border-2 border-gray-200`
    }
  }

  const stepNames = {
    'video-search': 'Finding Tutorial',
    'video-download': 'Downloading Video',
    'frame-extraction': 'Extracting Steps',
    'ui-screens': 'Preparing Images',
    'osatlas-processing': 'Creating Guide'
  }

  return (
    <div className="bg-white rounded-2xl shadow-lg border border-gray-100 p-8">
      <div className="text-center mb-8">
        <div className="inline-flex items-center justify-center w-16 h-16 bg-gradient-to-br from-primary-100 to-primary-200 rounded-full mb-4 animate-pulse">
          <Cog className="h-8 w-8 text-primary-500" />
        </div>
        <h2 className="text-2xl font-bold text-gray-900 mb-2">Creating Your Visual Guide</h2>
        <p className="text-lg text-gray-600">Please wait while we process your request...</p>
      </div>

      <div className="mb-8">
        <div className="flex justify-between items-center mb-3">
          <span className="text-lg font-semibold text-gray-800">Progress</span>
          <span className="text-lg font-bold text-primary-600">{Math.round(progress)}%</span>
        </div>
        <div className="w-full bg-gray-200 rounded-full h-4 overflow-hidden">
          <div 
            className="bg-gradient-to-r from-primary-500 to-primary-600 h-4 rounded-full transition-all duration-500 ease-out shadow-sm relative"
            style={{ width: `${progress}%` }}
          >
            <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white to-transparent opacity-30 animate-pulse"></div>
          </div>
        </div>
        <div className="flex justify-between text-sm text-gray-500 mt-2">
          <span>Started</span>
          <span>Complete</span>
        </div>
      </div>

      <div className="space-y-6">
        {steps.map((step) => (
          <div key={step.id} className="flex items-center space-x-6">
            <div className={getStepClasses(step)}>
              {getStepIcon(step)}
            </div>
            
            <div className="flex-1">
              <div className="flex items-center justify-between mb-2">
                <h3 className={`text-lg font-semibold ${
                  step.status === 'active' ? 'text-primary-700' : 
                  step.status === 'completed' ? 'text-green-700' :
                  step.status === 'error' ? 'text-red-700' : 'text-gray-600'
                }`}>
                  {stepNames[step.id as keyof typeof stepNames] || step.name}
                </h3>
                <span className={`text-sm px-3 py-1 rounded-full font-medium ${
                  step.status === 'active' ? 'bg-primary-100 text-primary-700' :
                  step.status === 'completed' ? 'bg-green-100 text-green-700' :
                  step.status === 'error' ? 'bg-red-100 text-red-700' :
                  'bg-gray-100 text-gray-600'
                }`}>
                  {step.status === 'active' ? 'In Progress' :
                   step.status === 'completed' ? 'Complete' :
                   step.status === 'error' ? 'Error' : 'Waiting'}
                </span>
              </div>
              
              {step.message && (
                <p className="text-base text-gray-600 leading-relaxed">{step.message}</p>
              )}
            </div>
          </div>
        ))}
      </div>

      {progress < 100 ? (
        <div className="mt-8 p-6 bg-gradient-to-r from-primary-50 to-primary-100 rounded-xl border border-primary-200">
          <div className="flex items-center space-x-3">
            <Loader2 className="h-6 w-6 text-primary-500 animate-spin" />
            <div>
              <p className="text-lg font-semibold text-primary-700">Processing your request...</p>
              <p className="text-primary-600 mt-1">This usually takes 2-3 minutes. Please don't close this page.</p>
            </div>
          </div>
        </div>
      ) : (
        <div className="mt-8 p-6 bg-green-50 rounded-xl border border-green-200">
          <div className="flex items-center space-x-3">
            <CheckCircle className="h-6 w-6 text-green-600" />
            <div>
              <p className="text-lg font-semibold text-green-800">Guide Created Successfully!</p>
              <p className="text-green-600 mt-1">Your visual guide is ready below.</p>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default ProcessingPipeline
