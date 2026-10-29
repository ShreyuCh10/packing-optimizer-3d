import { useState } from 'react'
import ProductsView from './components/products/ProductsView'
import ChatbotView from './components/chatbot/ChatbotView'

type PageKey = 'products' | 'packages' | 'optimiser' | 'chatbot'

interface NavItem {
  key: PageKey
  label: string
  description: string
}

const NAV_ITEMS: NavItem[] = [
  {
    key: 'products',
    label: 'Products',
    description: 'Product catalog, CAD geometric parameters, and part attributes loaded from SQLite database.',
  },
  {
    key: 'packages',
    label: 'Packages',
    description: 'Carton and box inventory, stock levels, and weight capacities.',
  },
  {
    key: 'optimiser',
    label: 'Optimiser',
    description: '3D container loading optimizer, spatial packing, and custom box generator.',
  },
  {
    key: 'chatbot',
    label: 'Chatbot',
    description: 'AI assistant for natural language requirement gathering and package matching.',
  },
]

export default function App() {
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [activePage, setActivePage] = useState<PageKey>('products')

  const currentPage = NAV_ITEMS.find((item) => item.key === activePage) ?? NAV_ITEMS[0]

  const handleSelectPage = (key: PageKey) => {
    setActivePage(key)
    setSidebarOpen(false)
  }

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900 flex flex-col">
      {/* Top Header */}
      <header className="sticky top-0 z-20 bg-white border-b border-slate-200 px-4 py-3 flex items-center justify-between">
        <div className="flex items-center gap-3">
          {/* Hamburger Button */}
          <button
            type="button"
            onClick={() => setSidebarOpen((prev) => !prev)}
            aria-label="Toggle navigation menu"
            className="p-2 rounded-md text-slate-700 hover:text-slate-900 hover:bg-slate-100 focus:outline-none focus:ring-2 focus:ring-slate-400 cursor-pointer"
          >
            <svg
              className="w-6 h-6"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
              strokeWidth={2}
            >
              <path strokeLinecap="round" strokeLinejoin="round" d="M4 6h16M4 12h16M4 18h16" />
            </svg>
          </button>

          <div>
            <span className="text-lg font-bold tracking-tight text-slate-900">
              Packing Optimizer 3D
            </span>
            <span className="hidden sm:inline-block ml-3 text-xs font-medium text-slate-500 bg-slate-100 px-2.5 py-0.5 rounded">
              {currentPage.label}
            </span>
          </div>
        </div>

        <div className="text-xs text-slate-500 font-medium">v1.0.0</div>
      </header>

      {/* Backdrop for Sidebar */}
      {sidebarOpen && (
        <div
          role="presentation"
          onClick={() => setSidebarOpen(false)}
          className="fixed inset-0 bg-slate-900/40 z-30 transition-opacity"
        />
      )}

      {/* Sidebar Drawer */}
      <aside
        className={`fixed top-0 left-0 bottom-0 w-72 bg-white border-r border-slate-200 z-40 flex flex-col transition-transform duration-200 ease-in-out ${
          sidebarOpen ? 'translate-x-0' : '-translate-x-full'
        }`}
      >
        {/* Sidebar Header */}
        <div className="px-5 py-4 border-b border-slate-200 flex items-center justify-between">
          <span className="text-base font-semibold text-slate-800">Navigation</span>
          <button
            type="button"
            onClick={() => setSidebarOpen(false)}
            aria-label="Close sidebar"
            className="p-1.5 rounded-md text-slate-500 hover:text-slate-800 hover:bg-slate-100 cursor-pointer"
          >
            <svg
              className="w-5 h-5"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
              strokeWidth={2}
            >
              <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Sidebar Menu Options */}
        <nav className="flex-1 px-3 py-4 space-y-1">
          {NAV_ITEMS.map((item) => {
            const isActive = item.key === activePage
            return (
              <button
                key={item.key}
                type="button"
                onClick={() => handleSelectPage(item.key)}
                className={`w-full text-left px-3.5 py-2.5 rounded-md text-sm font-medium transition-colors cursor-pointer flex items-center justify-between ${
                  isActive
                    ? 'bg-slate-900 text-white'
                    : 'text-slate-700 hover:bg-slate-100 hover:text-slate-900'
                }`}
              >
                <span>{item.label}</span>
                {isActive && (
                  <span className="w-1.5 h-1.5 rounded-full bg-white" />
                )}
              </button>
            )
          })}
        </nav>

        {/* Sidebar Footer */}
        <div className="p-4 border-t border-slate-200 text-xs text-slate-500">
          Packing Optimizer Suite
        </div>
      </aside>

      {/* Main Page Content */}
      {activePage === 'chatbot' ? (
        <main className="flex-1 flex flex-col w-full h-[calc(100vh-57px)] overflow-hidden bg-white">
          <ChatbotView />
        </main>
      ) : (
        <main className="flex-1 max-w-7xl w-full mx-auto p-4 sm:p-6 lg:p-8">
          {activePage === 'products' ? (
            <ProductsView />
          ) : (
            <div className="max-w-2xl mx-auto my-12 bg-white border border-slate-200 rounded-lg p-8 sm:p-12 text-center shadow-xs">
              <span className="inline-block px-3 py-1 text-xs font-semibold uppercase tracking-wider text-slate-700 bg-slate-100 rounded-full mb-4">
                {currentPage.label}
              </span>
              <h1 className="text-3xl sm:text-4xl font-bold text-slate-900 mb-3">
                Coming Soon
              </h1>
              <p className="text-slate-600 max-w-md mx-auto text-sm sm:text-base mb-6">
                {currentPage.description}
              </p>
              <div className="inline-flex items-center gap-2 text-xs font-medium text-slate-500 bg-slate-50 border border-slate-200 px-3 py-1.5 rounded-md">
                <span className="w-2 h-2 rounded-full bg-amber-500" />
                Under Development
              </div>
            </div>
          )}
        </main>
      )}
    </div>
  )
}
