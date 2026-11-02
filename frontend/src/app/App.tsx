import { Link } from 'react-router-dom'

export function App() {
  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 text-gray-900 dark:text-gray-100 font-sans transition-colors duration-300">
      {/* Header */}
      <header className="glass sticky top-0 z-40 backdrop-blur-xl border-b border-white/20 px-6 py-4">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center text-white font-bold text-xl">
              $
            </div>
            <h1 className="text-xl font-bold bg-gradient-to-r from-indigo-600 to-purple-600 bg-clip-text text-transparent hidden md:block">
              BudgetTracker
            </h1>
          </div>
          
          <nav className="flex items-center gap-2">
            <Link to="/" className="glass px-4 py-2 rounded-xl font-medium text-sm hover:bg-gray-500/10 transition-colors">Dashboard</Link>
            <Link to="/accounts" className="glass px-4 py-2 rounded-xl font-medium text-sm hover:bg-gray-500/10 transition-colors">Accounts</Link>
            <Link to="/transactions" className="glass px-4 py-2 rounded-xl font-medium text-sm hover:bg-gray-500/10 transition-colors">Transactions</Link>
            <Link to="/categories" className="glass px-4 py-2 rounded-xl font-medium text-sm hover:bg-gray-500/10 transition-colors">Categories</Link>
            <Link to="/subscriptions" className="glass px-4 py-2 rounded-xl font-medium text-sm hover:bg-gray-500/10 transition-colors">Subscriptions</Link>
          </nav>
          
          <div className="flex items-center gap-3">
            <div className="hidden md:flex items-center gap-2 glass px-3 py-1.5 rounded-full">
              <div className="w-8 h-8 rounded-full bg-gradient-to-br from-emerald-500 to-teal-600 flex items-center justify-center text-white font-medium text-xs">
                JD
              </div>
              <span className="text-sm font-medium">John Doe</span>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-6 py-8">
        <div id="app-content">
          {/* Content will be rendered here */}
        </div>
      </main>
    </div>
  )
}