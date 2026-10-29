import { useState, useEffect, useMemo } from 'react'
import type { Product } from '../../types/customBox'
import { fetchProducts } from '../../services/productsApi'
import ProductCard from './ProductCard'
import ProductModal from './ProductModal'

export default function ProductsView() {
  const [products, setProducts] = useState<Product[]>([])
  const [loading, setLoading] = useState<boolean>(true)
  const [error, setError] = useState<string | null>(null)
  const [searchQuery, setSearchQuery] = useState<string>('')
  const [selectedType, setSelectedType] = useState<string>('All')
  const [selectedProduct, setSelectedProduct] = useState<Product | null>(null)

  const loadProducts = async () => {
    setLoading(true)
    setError(null)
    try {
      const response = await fetchProducts()
      setProducts(response.products || [])
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to connect to backend'
      setError(msg)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadProducts()
  }, [])

  // Collect unique part types for category filtering
  const availableTypes = useMemo(() => {
    const types = new Set<string>()
    products.forEach((p) => {
      if (p.part_type) types.add(p.part_type)
    })
    return ['All', ...Array.from(types).sort()]
  }, [products])

  // Filter products based on search and category
  const filteredProducts = useMemo(() => {
    return products.filter((p) => {
      const matchesSearch =
        searchQuery.trim() === '' ||
        p.part_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        p.part_type.toLowerCase().includes(searchQuery.toLowerCase()) ||
        p.line_feeding_method.toLowerCase().includes(searchQuery.toLowerCase())

      const matchesType =
        selectedType === 'All' ||
        p.part_type.toLowerCase() === selectedType.toLowerCase()

      return matchesSearch && matchesType
    })
  }, [products, searchQuery, selectedType])

  return (
    <div className="space-y-6">
      {/* Section Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 pb-4 border-b border-slate-200">
        <div>
          <h1 className="text-2xl sm:text-3xl font-bold text-slate-900 tracking-tight">
            Products Catalog
          </h1>
          <p className="text-sm text-slate-500 mt-1">
            Physical dimensions, weights, and SNP constraints loaded from SQLite database.
          </p>
        </div>

        {/* Primary Interactive Refresh Button */}
        <button
          type="button"
          onClick={loadProducts}
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

      {/* Search & Filter Toolbar */}
      <div className="flex flex-col md:flex-row gap-3 items-stretch md:items-center justify-between">
        {/* Search Bar with Blue/Teal Focus Ring */}
        <div className="relative flex-1 max-w-md">
          <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-400">
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="m21 21-5.197-5.197m0 0A7.5 7.5 0 1 0 5.196 5.196a7.5 7.5 0 0 0 10.607 10.607Z" />
            </svg>
          </div>
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search by part name or material..."
            className="w-full pl-9 pr-8 py-2 text-sm bg-white border border-slate-300 rounded-md text-slate-900 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-sky-500 focus:border-sky-500 transition duration-150"
          />
          {searchQuery && (
            <button
              type="button"
              onClick={() => setSearchQuery('')}
              className="absolute inset-y-0 right-0 pr-3 flex items-center text-slate-400 hover:text-slate-600 transition-colors cursor-pointer"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          )}
        </div>

        {/* Selected Filter Pills - Teal/Blue Primary Action */}
        <div className="flex items-center gap-1.5 overflow-x-auto pb-1 md:pb-0 text-xs">
          {availableTypes.slice(0, 7).map((t) => {
            const isSelected = selectedType.toLowerCase() === t.toLowerCase()
            return (
              <button
                key={t}
                type="button"
                onClick={() => setSelectedType(t)}
                className={`px-3 py-1.5 rounded-md font-medium whitespace-nowrap active:scale-[0.98] transition-all duration-150 cursor-pointer ${
                  isSelected
                    ? 'bg-sky-600 text-white shadow-2xs'
                    : 'bg-white border border-slate-200 text-slate-600 hover:border-slate-300 hover:bg-slate-50 hover:text-slate-900'
                }`}
              >
                {t}
              </button>
            )
          })}
        </div>
      </div>

      {/* Results Count & Source Meta */}
      <div className="flex items-center justify-between text-xs text-slate-500">
        <span>
          Showing <strong className="text-slate-800">{filteredProducts.length}</strong> of{' '}
          <strong className="text-slate-800">{products.length}</strong> products
        </span>
        <span className="hidden sm:inline-block bg-sky-50 text-sky-800 border border-sky-200/80 px-2.5 py-0.5 rounded text-[11px] font-mono">
          Source: SQLite (table: products)
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
            <strong className="font-semibold">Unable to fetch products:</strong> {error}
            <p className="text-xs text-red-600 mt-0.5">
              Ensure the backend server is running on <code>http://localhost:8000</code>.
            </p>
          </div>
          <button
            type="button"
            onClick={loadProducts}
            className="px-3.5 py-1.5 bg-sky-600 text-white rounded-md text-xs font-semibold hover:bg-sky-700 active:scale-[0.98] transition cursor-pointer self-start sm:self-auto shadow-xs"
          >
            Retry
          </button>
        </div>
      )}

      {/* Empty State */}
      {!loading && !error && filteredProducts.length === 0 && (
        <div className="bg-white border border-slate-200 rounded-lg p-10 text-center">
          <svg
            className="w-12 h-12 mx-auto stroke-slate-400 mb-3"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
            strokeWidth={1.5}
          >
            <path strokeLinecap="round" strokeLinejoin="round" d="m21 21-5.197-5.197m0 0A7.5 7.5 0 1 0 5.196 5.196a7.5 7.5 0 0 0 10.607 10.607Z" />
          </svg>
          <h3 className="text-base font-semibold text-slate-800 mb-1">No products found</h3>
          <p className="text-sm text-slate-500 max-w-sm mx-auto mb-4">
            No items matched your search query &ldquo;{searchQuery}&rdquo;.
          </p>
          <button
            type="button"
            onClick={() => {
              setSearchQuery('')
              setSelectedType('All')
            }}
            className="px-3.5 py-2 bg-sky-600 text-white rounded-md text-xs font-semibold hover:bg-sky-700 active:scale-[0.98] transition cursor-pointer shadow-xs"
          >
            Reset Filters
          </button>
        </div>
      )}

      {/* Products Grid */}
      {!loading && !error && filteredProducts.length > 0 && (
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-5">
          {filteredProducts.map((product) => (
            <ProductCard
              key={product.id ?? product.part_name}
              product={product}
              onClick={(p) => setSelectedProduct(p)}
            />
          ))}
        </div>
      )}

      {/* Product Details Modal */}
      <ProductModal
        product={selectedProduct}
        onClose={() => setSelectedProduct(null)}
      />
    </div>
  )
}
