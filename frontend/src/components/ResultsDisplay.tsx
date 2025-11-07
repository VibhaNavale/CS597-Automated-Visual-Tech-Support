import React, { useState } from 'react'
import { useSelector, useDispatch } from 'react-redux'
import { RootState } from '../store/store'
import { verifyStepQuality, verifyBbox } from '../store/slices/videoAnalysisSlice'
import { saveAccuracyMetrics } from '../services/api'
import { MousePointer, CheckCircle, ArrowRight, Hand, RotateCcw, Home, ChevronLeft, ChevronRight, ArrowUp, ArrowDown, ArrowLeft, CheckCircle2, ZoomIn, X, XCircle, AlertCircle, Save } from 'lucide-react'

const ResultsDisplay: React.FC = () => {
  const dispatch = useDispatch()
  const { results, query, testMode, testMetrics, videoId } = useSelector((state: RootState) => state.videoAnalysis)
  const [currentPage, setCurrentPage] = useState(0)
  const [selectedStep, setSelectedStep] = useState<number | null>(null)
  const [savingMetrics, setSavingMetrics] = useState(false)
  const [saveMessage, setSaveMessage] = useState<string | null>(null)
  
  React.useEffect(() => {
    setCurrentPage(0)
  }, [results.length])
  
  const shouldPaginate = results.length >= 9
  const stepsPerPage = 6
  const totalPages = shouldPaginate ? Math.ceil(results.length / stepsPerPage) : 1
  const startIndex = shouldPaginate ? currentPage * stepsPerPage : 0
  const endIndex = shouldPaginate ? startIndex + stepsPerPage : results.length
  const currentResults = shouldPaginate ? results.slice(startIndex, endIndex) : results
  
  const goToNextPage = () => {
    if (currentPage < totalPages - 1) {
      setCurrentPage(currentPage + 1)
    }
  }
  
  const goToPreviousPage = () => {
    if (currentPage > 0) {
      setCurrentPage(currentPage - 1)
    }
  }

  const getActionIcon = (action: string) => {
    const actionLower = action.toLowerCase()
    if (actionLower.includes('click') || actionLower.includes('tap')) {
      return <MousePointer className="h-5 w-5" />
    } else if (actionLower.includes('scroll [up]') || actionLower.includes('scroll up')) {
      return <ArrowUp className="h-5 w-5" />
    } else if (actionLower.includes('scroll [down]') || actionLower.includes('scroll down')) {
      return <ArrowDown className="h-5 w-5" />
    } else if (actionLower.includes('scroll [left]') || actionLower.includes('scroll left')) {
      return <ArrowLeft className="h-5 w-5" />
    } else if (actionLower.includes('scroll [right]') || actionLower.includes('scroll right')) {
      return <ArrowRight className="h-5 w-5" />
    } else if (actionLower.includes('scroll')) {
      return <ArrowRight className="h-5 w-5" />
    } else if (actionLower.includes('press_back')) {
      return <RotateCcw className="h-5 w-5" />
    } else if (actionLower.includes('press_home')) {
      return <Home className="h-5 w-5" />
    } else if (actionLower.includes('type') || actionLower.includes('enter')) {
      return <Hand className="h-5 w-5" />
    } else if (actionLower.includes('complete')) {
      return <CheckCircle2 className="h-5 w-5" />
    }
    return <CheckCircle className="h-5 w-5" />
  }

  const formatAction = (action: string) => {
    let cleanAction = action
      .replace(/<point>\[\[(\d+),(\d+)\]\]<\/point>/g, 'at coordinates ($1, $2)')
      .replace(/<point>\[(\d+),(\d+)\]<\/point>/g, 'at coordinates ($1, $2)')
      .replace(/\[\[(\d+),(\d+)\]\]/g, 'at coordinates ($1, $2)')
      .replace(/\[(\d+),(\d+)\]/g, 'at coordinates ($1, $2)')
      .replace(/<\|im_end\|>/g, '')
      .trim()
    
    return cleanAction
  }

  const handleVerifyStepQuality = (step: number, quality: 'good' | 'bad' | 'repeated' | 'not_relevant') => {
    dispatch(verifyStepQuality({ step, quality }))
  }

  const handleVerify = (step: number, verification: 'correct' | 'incorrect' | 'not_needed' | 'missing') => {
    dispatch(verifyBbox({ step, verification }))
  }

  const getStepQualityLabel = (quality: string) => {
    const labels: { [key: string]: string } = {
      'good': 'Good Step',
      'bad': 'Bad Step',
      'repeated': 'Repeated Step',
      'not_relevant': 'Not Relevant'
    }
    return labels[quality] || quality
  }

  const getVerificationColor = (verification?: string) => {
    switch (verification) {
      case 'correct': return 'bg-green-100 border-green-300'
      case 'incorrect': return 'bg-red-100 border-red-300'
      case 'not_needed': return 'bg-blue-100 border-blue-300'
      case 'missing': return 'bg-orange-100 border-orange-300'
      default: return 'bg-white border-gray-200'
    }
  }

  const getVerificationLabel = (verification?: string) => {
    switch (verification) {
      case 'correct': return 'Correct'
      case 'incorrect': return 'Incorrect'
      case 'not_needed': return 'Not Needed'
      case 'missing': return 'Missing'
      default: return null
    }
  }

  const handleSaveAccuracyMetrics = async () => {
    if (!videoId) {
      setSaveMessage('Error: No video ID available')
      return
    }

    if (!testMetrics || testMetrics.total === 0) {
      setSaveMessage('Error: No verifications to save')
      return
    }

    setSavingMetrics(true)
    setSaveMessage(null)

    try {
      const allVerifications = results.map(r => ({
        step: r.step,
        verification: r.bboxVerification || null
      }))

      const allStepQualities = results.map(r => ({
        step: r.step,
        quality: r.stepQuality || null
      }))

      await saveAccuracyMetrics({
        video_id: videoId,
        query: query,
        correct: testMetrics.correct,
        incorrect: testMetrics.incorrect,
        not_needed: testMetrics.notNeeded,
        missing: testMetrics.missing,
        total: testMetrics.total,
        accuracy: testMetrics.accuracy,
        step_qualities: allStepQualities,
        bbox_verifications: allVerifications
      })

      setSaveMessage('Accuracy metrics saved successfully!')
      setTimeout(() => setSaveMessage(null), 3000)
    } catch (error: any) {
      setSaveMessage(`Error saving metrics: ${error.response?.data?.detail || error.message}`)
    } finally {
      setSavingMetrics(false)
    }
  }

  return (
    <div className="card">
      <div className="mb-6">
        <div className="flex items-center justify-between mb-2">
          <h2 className="text-lg font-semibold text-gray-900">Analysis Results</h2>
          {testMode && (
            <div className="px-3 py-1 bg-amber-100 text-amber-800 rounded-full text-xs font-medium">
              Test Mode Active
            </div>
          )}
        </div>
        <p className="text-sm text-gray-600">
          Step-by-step breakdown for: <span className="font-medium">"{query}"</span>
        </p>
      </div>

      {testMode && videoId && testMetrics && (
        <div className="mb-4 p-3 bg-amber-50 rounded-lg border border-amber-200">
          <div className="flex items-center justify-between mb-2">
            <div className="text-sm text-amber-800">
              <strong>Test Mode:</strong> Verify bboxes above, then click Save to save accuracy metrics.
            </div>
            <button
              onClick={handleSaveAccuracyMetrics}
              disabled={savingMetrics}
              className="flex items-center space-x-2 px-4 py-2 bg-amber-600 text-white rounded-lg hover:bg-amber-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              <Save className="h-4 w-4" />
              <span>{savingMetrics ? 'Saving...' : 'Save Accuracy Metrics'}</span>
            </button>
          </div>
          <div className="text-xs text-amber-700">
            <strong>Note:</strong> Metrics saved to <code className="bg-amber-100 px-1 rounded">test/&#123;video_id&#125;/accuracy_metrics.json</code> on server.
            {results.some(r => r.bboxVerification !== undefined) && (
              <span className="ml-2 font-medium">
                ({results.filter(r => r.bboxVerification !== undefined).length} / {results.length} verified)
              </span>
            )}
          </div>
        </div>
      )}

      {saveMessage && (
        <div className={`mb-4 p-3 rounded-lg ${saveMessage.includes('Error') ? 'bg-red-50 text-red-800 border border-red-200' : 'bg-green-50 text-green-800 border border-green-200'}`}>
          {saveMessage}
        </div>
      )}

      {results.length === 0 ? (
        <div className="text-center py-8">
          <div className="text-gray-400 mb-4">
            <CheckCircle className="mx-auto h-12 w-12" />
          </div>
          <p className="text-gray-500">No results available yet</p>
        </div>
      ) : (
        <>
          <div className="space-y-6">
            <div className="flex items-center justify-between">
              <h3 className="text-lg font-semibold text-gray-900">
                {shouldPaginate ? `Steps ${startIndex + 1}-${Math.min(endIndex, results.length)} of ${results.length}` : `${results.length} Step${results.length !== 1 ? 's' : ''}`}
              </h3>
              {shouldPaginate && totalPages > 1 && (
                <div className="flex items-center space-x-2">
                  <button
                    onClick={goToPreviousPage}
                    disabled={currentPage === 0}
                    className="p-2 rounded-full bg-gray-100 hover:bg-gray-200 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                  >
                    <ChevronLeft className="h-4 w-4" />
                  </button>
                  <span className="text-sm text-gray-600">
                    Page {currentPage + 1} of {totalPages}
                  </span>
                  <button
                    onClick={goToNextPage}
                    disabled={currentPage === totalPages - 1}
                    className="p-2 rounded-full bg-gray-100 hover:bg-gray-200 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                  >
                    <ChevronRight className="h-4 w-4" />
                  </button>
                </div>
              )}
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6 sm:gap-8 items-stretch">
              {currentResults.map((result, index) => (
                <div 
                  key={startIndex + index} 
                  className="border border-gray-200 rounded-lg bg-white shadow-sm hover:shadow-md transition-all cursor-pointer flex flex-col"
                  onClick={() => setSelectedStep(startIndex + index)}
                >
                  <div className="p-5 sm:p-6 flex flex-col flex-1">
                    <div className="flex items-start justify-between mb-4">
                      <div className="flex items-center space-x-3 flex-1">
                        <div className="flex items-center justify-center min-w-[2.75rem] h-11 bg-primary-600 text-white rounded-lg font-semibold text-base px-3">
                          Step {result.step}
                        </div>
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center space-x-2 mb-2">
                            <div className="text-primary-600 flex-shrink-0">
                              {getActionIcon(result.action)}
                            </div>
                            <span className="text-base sm:text-lg font-semibold text-gray-900">{formatAction(result.action)}</span>
                          </div>
                          {result.thought && (
                            <p className="text-sm sm:text-base text-gray-700 leading-relaxed">"{result.thought}"</p>
                          )}
                        </div>
                      </div>
                      <div className="flex items-center space-x-1 text-primary-600 ml-3 flex-shrink-0">
                      <ZoomIn className="h-5 w-5" />
                        <span className="text-xs font-medium hidden sm:inline">Tap to enlarge</span>
                    </div>
                  </div>
                  
                    <div className={`mt-auto rounded-lg border-2 overflow-hidden ${testMode ? getVerificationColor(result.bboxVerification) : 'border-gray-200'}`}>
                       {result.image ? (
                         <img 
                           src={`https://compaasgold06.evl.uic.edu${result.image}`}
                           alt={`Step ${result.step} visualization`}
                           className="w-full h-auto object-contain max-h-80"
                           onError={(e) => {
                             e.currentTarget.style.display = 'none'
                             if (e.currentTarget.nextElementSibling instanceof HTMLElement) {
                               e.currentTarget.nextElementSibling.style.display = 'flex'
                             }
                           }}
                         />
                       ) : null}
                       <div className="w-full h-32 bg-gray-100 flex flex-col items-center justify-center p-2" style={{ display: result.image ? 'none' : 'flex' }}>
                         <div className="text-gray-500 text-sm text-center">
                           <div className="font-medium">Step {result.step}</div>
                           <div className="mt-1">No image available</div>
                         </div>
                       </div>
                     </div>
                     {testMode && (
                       <div className="mt-4 px-4 pb-4 space-y-4">
                         <div>
                           <div className="text-xs font-medium text-gray-700 mb-2">Step Quality Assessment:</div>
                           <div className="grid grid-cols-2 gap-2">
                             <button
                               onClick={(e) => {
                                 e.stopPropagation()
                                 handleVerifyStepQuality(result.step, 'good')
                               }}
                               className={`px-2 py-1.5 text-xs rounded border transition-colors ${
                                 result.stepQuality === 'good'
                                   ? 'bg-green-500 text-white border-green-600'
                                   : 'bg-white text-green-700 border-green-300 hover:bg-green-50'
                               }`}
                             >
                               <CheckCircle2 className="h-3 w-3 inline mr-1" />
                               Good Step
                             </button>
                             <button
                               onClick={(e) => {
                                 e.stopPropagation()
                                 handleVerifyStepQuality(result.step, 'bad')
                               }}
                               className={`px-2 py-1.5 text-xs rounded border transition-colors ${
                                 result.stepQuality === 'bad'
                                   ? 'bg-red-500 text-white border-red-600'
                                   : 'bg-white text-red-700 border-red-300 hover:bg-red-50'
                               }`}
                             >
                               <XCircle className="h-3 w-3 inline mr-1" />
                               Bad Step
                             </button>
                             <button
                               onClick={(e) => {
                                 e.stopPropagation()
                                 handleVerifyStepQuality(result.step, 'repeated')
                               }}
                               className={`px-2 py-1.5 text-xs rounded border transition-colors ${
                                 result.stepQuality === 'repeated'
                                   ? 'bg-yellow-500 text-white border-yellow-600'
                                   : 'bg-white text-yellow-700 border-yellow-300 hover:bg-yellow-50'
                               }`}
                             >
                               <AlertCircle className="h-3 w-3 inline mr-1" />
                               Repeated
                             </button>
                             <button
                               onClick={(e) => {
                                 e.stopPropagation()
                                 handleVerifyStepQuality(result.step, 'not_relevant')
                               }}
                               className={`px-2 py-1.5 text-xs rounded border transition-colors ${
                                 result.stepQuality === 'not_relevant'
                                   ? 'bg-purple-500 text-white border-purple-600'
                                   : 'bg-white text-purple-700 border-purple-300 hover:bg-purple-50'
                               }`}
                             >
                               <AlertCircle className="h-3 w-3 inline mr-1" />
                               Not Relevant
                             </button>
                           </div>
                           {result.stepQuality && (
                             <div className="text-xs text-gray-500 mt-1">
                               Quality: <span className="font-medium">{getStepQualityLabel(result.stepQuality)}</span>
                             </div>
                           )}
                         </div>
                         
                         <div>
                           <div className="text-xs font-medium text-gray-700 mb-2">Verify Bounding Box:</div>
                           <div className="grid grid-cols-2 gap-2">
                           <button
                             onClick={(e) => {
                               e.stopPropagation()
                               handleVerify(result.step, 'correct')
                             }}
                             className={`px-2 py-1.5 text-xs rounded border transition-colors ${
                               result.bboxVerification === 'correct'
                                 ? 'bg-green-500 text-white border-green-600'
                                 : 'bg-white text-green-700 border-green-300 hover:bg-green-50'
                             }`}
                           >
                             <CheckCircle2 className="h-3 w-3 inline mr-1" />
                             Correct
                           </button>
                           <button
                             onClick={(e) => {
                               e.stopPropagation()
                               handleVerify(result.step, 'incorrect')
                             }}
                             className={`px-2 py-1.5 text-xs rounded border transition-colors ${
                               result.bboxVerification === 'incorrect'
                                 ? 'bg-red-500 text-white border-red-600'
                                 : 'bg-white text-red-700 border-red-300 hover:bg-red-50'
                             }`}
                           >
                             <XCircle className="h-3 w-3 inline mr-1" />
                             Incorrect
                           </button>
                           <button
                             onClick={(e) => {
                               e.stopPropagation()
                               handleVerify(result.step, 'not_needed')
                             }}
                             className={`px-2 py-1.5 text-xs rounded border transition-colors ${
                               result.bboxVerification === 'not_needed'
                                 ? 'bg-blue-500 text-white border-blue-600'
                                 : 'bg-white text-blue-700 border-blue-300 hover:bg-blue-50'
                             }`}
                           >
                             <AlertCircle className="h-3 w-3 inline mr-1" />
                             Not Needed
                           </button>
                           <button
                             onClick={(e) => {
                               e.stopPropagation()
                               handleVerify(result.step, 'missing')
                             }}
                             className={`px-2 py-1.5 text-xs rounded border transition-colors ${
                               result.bboxVerification === 'missing'
                                 ? 'bg-orange-500 text-white border-orange-600'
                                 : 'bg-white text-orange-700 border-orange-300 hover:bg-orange-50'
                             }`}
                           >
                             <AlertCircle className="h-3 w-3 inline mr-1" />
                             Missing
                           </button>
                         </div>
                         {result.bboxVerification && (
                           <div className="text-xs text-gray-500 mt-1">
                             Status: <span className="font-medium">{getVerificationLabel(result.bboxVerification)}</span>
                           </div>
                         )}
                         </div>
                       </div>
                     )}
                   </div>
                </div>
              ))}
            </div>

            {shouldPaginate && totalPages > 1 && (
              <div className="flex justify-center space-x-2 pt-4">
                {Array.from({ length: totalPages }, (_, i) => (
                  <button
                    key={i}
                    onClick={() => setCurrentPage(i)}
                    className={`w-8 h-8 rounded-full text-sm font-medium transition-colors ${
                      i === currentPage
                        ? 'bg-primary-100 text-primary-600'
                        : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                    }`}
                  >
                    {i + 1}
                  </button>
                ))}
              </div>
            )}
          </div>

          <div className="mt-6 p-4 bg-success-50 rounded-lg">
            <div className="flex items-center space-x-2">
              <CheckCircle className="h-5 w-5 text-success-500" />
              <p className="text-sm text-success-700">
                Analysis completed! Found {results.length} step{results.length !== 1 ? 's' : ''} in the process.
              </p>
            </div>
          </div>
        </>
      )}

      {selectedStep !== null && results[selectedStep] && (
        <div 
          className="fixed inset-0 bg-black bg-opacity-75 z-50 flex items-center justify-center p-4"
          onClick={() => setSelectedStep(null)}
        >
          <div 
            className="bg-white rounded-2xl max-w-4xl w-full max-h-[90vh] overflow-y-auto"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="sticky top-0 bg-white border-b border-gray-200 px-6 py-4 flex items-center justify-between">
              <h3 className="text-xl font-bold text-gray-900">
                Step {results[selectedStep].step}: {formatAction(results[selectedStep].action)}
              </h3>
              <button
                onClick={() => setSelectedStep(null)}
                className="p-2 rounded-full hover:bg-gray-100 transition-colors"
              >
                <X className="h-6 w-6 text-gray-600" />
              </button>
            </div>
            
            <div className="p-6">
              {results[selectedStep].thought && (
                <p className="text-lg text-gray-700 mb-6 italic">"{results[selectedStep].thought}"</p>
              )}
              
              <div className="relative">
                <div className="text-center mb-4">
                  <span className="text-lg font-semibold text-gray-700 px-4 py-2">
                    Step {results[selectedStep].step} of {results.length}
                  </span>
                </div>
                
                <div className="relative rounded-lg border-4 border-primary-200 overflow-hidden flex justify-center bg-gray-50">
                  {selectedStep > 0 && (
                    <button
                      onClick={(e) => {
                        e.stopPropagation()
                        setSelectedStep(selectedStep - 1)
                      }}
                      className="absolute left-2 sm:left-4 top-1/2 -translate-y-1/2 z-10 bg-primary-600 text-white rounded-full p-3 sm:p-4 hover:bg-primary-700 transition-colors shadow-lg hover:shadow-xl"
                      aria-label="Previous step"
                    >
                      <ChevronLeft className="h-6 w-6 sm:h-8 sm:w-8" />
                    </button>
                  )}
                  
                  {results[selectedStep].image ? (
                    <img 
                      src={`https://compaasgold06.evl.uic.edu${results[selectedStep].image}`}
                      alt={`Step ${results[selectedStep].step} detailed view`}
                      className="max-w-full h-auto max-h-[50vh] sm:max-h-[60vh] object-contain"
                    />
                  ) : (
                    <div className="w-full h-64 bg-gray-100 flex flex-col items-center justify-center">
                      <div className="text-gray-500 text-center">
                        <div className="font-medium text-xl">Step {results[selectedStep].step}</div>
                        <div className="mt-2">No image available</div>
                      </div>
                    </div>
                  )}
                  
                  {selectedStep < results.length - 1 && (
                    <button
                      onClick={(e) => {
                        e.stopPropagation()
                        setSelectedStep(selectedStep + 1)
                      }}
                      className="absolute right-2 sm:right-4 top-1/2 -translate-y-1/2 z-10 bg-primary-600 text-white rounded-full p-3 sm:p-4 hover:bg-primary-700 transition-colors shadow-lg hover:shadow-xl"
                      aria-label="Next step"
                    >
                      <ChevronRight className="h-6 w-6 sm:h-8 sm:w-8" />
                    </button>
                  )}
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default ResultsDisplay
