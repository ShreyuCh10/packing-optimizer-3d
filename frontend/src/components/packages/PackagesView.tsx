import { useState, useEffect, useMemo } from 'react'
import type { PackagingItem, PackagingCategory, PackageCounts } from '../../types/packages'
import { fetchPackages } from '../../services/packagesApi'
import PackageCard from './PackageCard'
import PackageModal from './PackageModal'

const CATEGORY_TABS: { key: PackagingCategory; label: string }[] = [
  { key: 'all', label: 'All Packages' },
  { key: 'carton', label: 'Cartons' },
  { key: 'base_pallet', label: 'Base Pallets' },
  { key: 'metal_pallet', label: 'Metal Pallets' },
  { key: 'metal_stillage', label: 'Metal Stillages' },
]

export default function PackagesView() {
  const [packages, setPackages] = useState<PackagingItem[]>([])
  const [counts, setCounts] = useState<PackageCounts | null>(null)
  const [loading, setLoading] = useState<boolean>(true)
  const [error, setError] = useState<string | null>(null)
  const [searchQuery, setSearchQuery] = useState<string>('')
  const [selectedCategory, setSelectedCategory] = useState<PackagingCategory>('all')
  const [selectedPackage, setSelectedPackage] = useState<PackagingItem | null>(null)

  const loadPackages = async () => {
    setLoading(true)
    setError(null)
    try {
      const response = await fetchPackages()
      setPackages(response.packages || [])
      setCounts(response.counts || null)
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to connect to backend'
      setError(msg)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadPackages()
  }, [])

  // Filter packages based on active category tab and search query
  const filteredPackages = useMemo(() => {
    return packages.filter((pkg) => {
      const matchesCategory =
        selectedCategory === 'all' || pkg.category === selectedCategory

      const matchesSearch =
        searchQuery.trim() === '' ||
        pkg.package.toLowerCase().includes(searchQuery.toLowerCase()) ||
        pkg.category_label.toLowerCase().includes(searchQuery.toLowerCase()) ||
        `${pkg.outer_length_mm}x${pkg.outer_width_mm}x${pkg.outer_height_mm}`.includes(
          searchQuery.toLowerCase().replace(/\s+/g, '')
        )

      return matchesCategory && matchesSearch
    })
  }, [packages, selectedCategory, searchQuery])

  return (
    <div className="space-y-6">
      {/* Section Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 pb-4 border-b border-slate-200">
        <div>
          <h1 className="text-2xl sm:text-3xl font-bold text-slate-900 tracking-tight">
            Packaging Inventory
          </h1>
          <p className="text-sm text-slate-500 mt-1">
            Standard cartons, base pallets, and metal stillages loaded from SQLite database.
          </p>
        </div>

        {/* Refresh Button */}
        <button
          type="button"
          onClick={loadPackages}
          disabled={loading}
          className="inline-flex items-center gap-2 px-3.5 py-2 text-xs font-semibold text-sky-700 bg-sky-50/70 border border-sky-200 rounded-md hover:bg-sky-100 hover:text-sky-900 active:scale-[0.98] transition-all duration-150 cursor-pointer self-start sm:self-auto disabled:opacity-50 shadow-2xs"
        >
          <svg
            className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`}
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
            strokeWidth={2}
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0 3.181 3.183a8.25 8.25 0 0 0 13.803-3.7M4.031 9.865a8.25 8.25 0 0 1 13.803-3.7l3.181 3.182m0-4.991v4.99"
            />
          </svg>
          Refresh Data
        </button>
      </div>

      {/* Search & Category Filter Toolbar */}
      <div className="flex flex-col md:flex-row gap-3 items-stretch md:items-center justify-between">
        {/* Search Bar */}
        <div className="relative flex-1 max-w-md">
          <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-400">
            <svg
              className="w-4 h-4"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
              strokeWidth={2}
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="m21 21-5.197-5.197m0 0A7.5 7.5 0 1 0 5.196 5.196a7.5 7.5 0 0 0 10.607 10.607Z"
              />
            </svg>
          </div>
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search by package name or dimensions..."
            className="w-full pl-9 pr-8 py-2 text-sm bg-white border border-slate-300 rounded-md text-slate-900 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-sky-500 focus:border-sky-500 transition duration-150"
          />
          {searchQuery && (
            <button
              type="button"
              onClick={() => setSearchQuery('')}
              className="absolute inset-y-0 right-0 pr-3 flex items-center text-slate-400 hover:text-slate-600 transition-colors cursor-pointer"
            >
              <svg
                className="w-4 h-4"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
                strokeWidth={2}
              >
                <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          )}
        </div>

        {/* Category Filter Pills */}
        <div className="flex items-center gap-1.5 overflow-x-auto pb-1 md:pb-0 text-xs">
          {CATEGORY_TABS.map((tab) => {
            const isSelected = selectedCategory === tab.key
            const count = counts ? counts[tab.key] : null
            return (
              <button
                key={tab.key}
                type="button"
                onClick={() => setSelectedCategory(tab.key)}
                className={`px-3 py-1.5 rounded-md font-medium whitespace-nowrap active:scale-[0.98] transition-all duration-150 cursor-pointer flex items-center gap-1.5 ${
                  isSelected
                    ? 'bg-sky-600 text-white shadow-2xs'
                    : 'bg-white border border-slate-200 text-slate-600 hover:border-slate-300 hover:bg-slate-50 hover:text-slate-900'
                }`}
              >
                <span>{tab.label}</span>
                {count !== null && (
                  <span
                    className={`text-[11px] px-1.5 py-0.2 rounded-full font-semibold ${
                      isSelected
                        ? 'bg-sky-700 text-sky-100'
                        : 'bg-slate-100 text-slate-600'
                    }`}
                  >
                    {count}
                  </span>
                )}
              </button>
            )
          })}
        </div>
      </div>

      {/* Results Count & Source Meta */}
      <div className="flex items-center justify-between text-xs text-slate-500">
        <span>
          Showing <strong className="text-slate-800">{filteredPackages.length}</strong> of{' '}
          <strong className="text-slate-800">{packages.length}</strong> packages
        </span>
        <span className="hidden sm:inline-block bg-sky-50 text-sky-800 border border-sky-200/80 px-2.5 py-0.5 rounded text-[11px] font-mono">
          Source: SQLite (tables: packages, base_pallets, metal_pallets, metal_stillages)
        </span>
      </div>

      {/* Loading Skeleton */}
      {loading && (
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-5">
          {Array.from({ length: 8 }).map((_, idx) => (
            <div
              key={idx}
              className="bg-white border border-slate-200 rounded-lg overflow-hidden animate-pulse flex flex-col"
            >
              <div className="h-44 bg-sky-50/50" />
              <div className="p-4 space-y-3">
                <div className="h-4 bg-slate-200 rounded w-3/4" />
                <div className="h-3 bg-slate-200 rounded w-1/2" />
                <div className="pt-2 border-t border-slate-100 flex justify-between">
                  <div className="h-3 bg-slate-200 rounded w-1/3" />
                  <div className="h-3 bg-slate-200 rounded w-1/4" />
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Error Banner */}
      {!loading && error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-5 py-4 rounded-lg flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-sm">
          <div>
            <strong className="font-semibold">Unable to fetch packages:</strong> {error}
            <p className="text-xs text-red-600 mt-0.5">
              Ensure the backend server is running on <code>http://localhost:8000</code>.
            </p>
          </div>
          <button
            type="button"
            onClick={loadPackages}
            className="px-3.5 py-1.5 bg-sky-600 text-white rounded-md text-xs font-semibold hover:bg-sky-700 active:scale-[0.98] transition cursor-pointer self-start sm:self-auto shadow-xs"
          >
            Retry
          </button>
        </div>
      )}

      {/* Empty State */}
      {!loading && !error && filteredPackages.length === 0 && (
        <div className="bg-white border border-slate-200 rounded-lg p-10 text-center">
          <svg
            className="w-12 h-12 mx-auto stroke-slate-400 mb-3"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
            strokeWidth={1.5}
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="m21 21-5.197-5.197m0 0A7.5 7.5 0 1 0 5.196 5.196a7.5 7.5 0 0 0 10.607 10.607Z"
            />
          </svg>
          <h3 className="text-base font-semibold text-slate-800 mb-1">No packages found</h3>
          <p className="text-sm text-slate-500 max-w-sm mx-auto mb-4">
            No packaging items matched your search query &ldquo;{searchQuery}&rdquo;.
          </p>
          <button
            type="button"
            onClick={() => {
              setSearchQuery('')
              setSelectedCategory('all')
            }}
            className="px-3.5 py-2 bg-sky-600 text-white rounded-md text-xs font-semibold hover:bg-sky-700 active:scale-[0.98] transition cursor-pointer shadow-xs"
          >
            Reset Filters
          </button>
        </div>
      )}

      {/* Packages Grid */}
      {!loading && !error && filteredPackages.length > 0 && (
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-5">
          {filteredPackages.map((pkg) => (
            <PackageCard
              key={`${pkg.category}-${pkg.id ?? pkg.package}`}
              pkg={pkg}
              onClick={(p) => setSelectedPackage(p)}
            />
          ))}
        </div>
      )}

      {/* Package Details Modal */}
      <PackageModal
        pkg={selectedPackage}
        onClose={() => setSelectedPackage(null)}
      />
    </div>
  )
}

