import Header from './components/Header'
import TabbedInterface from './components/TabbedInterface'

function App() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-primary-50 to-primary-100">
      <Header />
      
      <main className="container mx-auto px-4 sm:px-6 py-6 sm:py-8 max-w-7xl">
        <TabbedInterface />
      </main>
    </div>
  )
}

export default App
