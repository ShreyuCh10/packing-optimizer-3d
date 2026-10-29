import { useEffect } from 'react'
import type { Product } from '../../types/customBox'
import { getMaterialBadgeStyle } from '../../utils/materialBadges'

interface ProductModalProps {
  product: Product | null
  onClose: () => void
}

export default function ProductModal({ product, onClose }: ProductModalProps) {
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onClose()
      }
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [onClose])

  if (!product) return null

  const badgeStyle = getMaterialBadgeStyle(product.part_type)
  const volumeCm3 = ((product.part_length * product.part_breadth * product.part_height) / 1000).toFixed(1)
  const volumeLiters = ((product.part_length * product.part_breadth * product.part_height) / 1000000).toFixed(3)
  const totalPackWeight = (product.part_weight * product.standard_no_of_parts).toFixed(2)

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-slate-900/60 backdrop-blur-xs transition-opacity"
        onClick={onClose}
        aria-hidden="true"
      />

      {/* Modal Dialog */}
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="modal-product-title"
        className="relative bg-white rounded-xl shadow-2xl max-w-2xl w-full max-h-[90vh] overflow-y-auto border border-slate-200 z-10 flex flex-col"
      >
        {/* Header */}
        <div className="px-6 py-4 border-b border-slate-200 flex items-center justify-between sticky top-0 bg-white z-10">
          <div>
            <div className="flex items-center gap-2">
              <span
                className={`text-xs font-semibold px-2.5 py-0.5 rounded border capitalize ${badgeStyle.bg} ${badgeStyle.text} ${badgeStyle.border}`}
              >
                {product.part_type}
              </span>
              {product.id && (
                <span className="text-xs text-slate-400">ID #{product.id}</span>
              )}
            </div>
            <h2
              id="modal-product-title"
              className="text-xl font-bold text-slate-900 mt-1"
            >
              {product.part_name}
            </h2>
          </div>

          <button
            type="button"
            onClick={onClose}
            aria-label="Close details"
            className="p-2 rounded-md text-slate-400 hover:text-slate-700 hover:bg-slate-100 transition cursor-pointer"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Modal Body */}
        <div className="p-6 space-y-6">
          {/* Placeholder for 3D Model / Image - Very Light Blue-Tinted Background */}
          <div className="h-48 bg-sky-50/65 rounded-lg border border-dashed border-sky-200 flex flex-col items-center justify-center text-sky-700/80 p-4">
            <svg
              className="w-12 h-12 mb-2 stroke-sky-400"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
              strokeWidth={1.5}
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="m21 7.5-9-5.25L3 7.5m18 0-9 5.25m9-5.25v9l-9 5.25M3 7.5l9 5.25M3 7.5v9l9 5.25m0-9v9"
              />
            </svg>
            <span className="text-sm font-semibold text-sky-950">
              3D CAD / Interactive Model Viewer
            </span>
            <span className="text-xs text-sky-600/80 mt-1">
              Image not available
            </span>
          </div>

          {/* Key Metric Highlights */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-center">
            <div className="bg-sky-50/50 border border-sky-100 rounded-lg p-3">
              <span className="text-xs text-slate-500 block mb-1">Standard Pack (SNP)</span>
              <span className="text-lg font-bold text-sky-900">{product.standard_no_of_parts}</span>
              <span className="text-xs text-sky-600 block">units/box</span>
            </div>

            <div className="bg-slate-50 border border-slate-200 rounded-lg p-3">
              <span className="text-xs text-slate-500 block mb-1">Unit Weight</span>
              <span className="text-lg font-bold text-slate-900">{product.part_weight}</span>
              <span className="text-xs text-slate-400 block">kg</span>
            </div>

            <div className="bg-sky-50/50 border border-sky-100 rounded-lg p-3">
              <span className="text-xs text-slate-500 block mb-1">Total Pack Weight</span>
              <span className="text-lg font-bold text-sky-900">{totalPackWeight}</span>
              <span className="text-xs text-sky-600 block">kg (weight &times; SNP)</span>
            </div>

            <div className="bg-slate-50 border border-slate-200 rounded-lg p-3">
              <span className="text-xs text-slate-500 block mb-1">Unit Volume</span>
              <span className="text-lg font-bold text-slate-900">{volumeLiters}</span>
              <span className="text-xs text-slate-400 block">liters</span>
            </div>
          </div>

          {/* Full Specifications Table */}
          <div className="border border-slate-200 rounded-lg overflow-hidden">
            <div className="bg-slate-50 px-4 py-2.5 border-b border-slate-200 text-xs font-semibold text-slate-700 uppercase tracking-wider">
              Product Specifications
            </div>
            <dl className="divide-y divide-slate-200 text-sm">
              <div className="px-4 py-3 sm:grid sm:grid-cols-3 sm:gap-4">
                <dt className="text-slate-500 font-medium">Dimensions (L &times; B &times; H)</dt>
                <dd className="mt-1 sm:mt-0 sm:col-span-2 text-slate-900 font-mono">
                  {product.part_length} &times; {product.part_breadth} &times; {product.part_height} mm
                </dd>
              </div>

              <div className="px-4 py-3 sm:grid sm:grid-cols-3 sm:gap-4">
                <dt className="text-slate-500 font-medium">Calculated Volume</dt>
                <dd className="mt-1 sm:mt-0 sm:col-span-2 text-slate-900">
                  {volumeCm3} cm&sup3; ({volumeLiters} Liters)
                </dd>
              </div>

              <div className="px-4 py-3 sm:grid sm:grid-cols-3 sm:gap-4">
                <dt className="text-slate-500 font-medium">Material / Category</dt>
                <dd className="mt-1 sm:mt-0 sm:col-span-2 text-slate-900 capitalize">
                  <span className={`inline-block px-2 py-0.5 rounded text-xs font-medium border ${badgeStyle.bg} ${badgeStyle.text} ${badgeStyle.border}`}>
                    {product.part_type}
                  </span>
                </dd>
              </div>

              <div className="px-4 py-3 sm:grid sm:grid-cols-3 sm:gap-4">
                <dt className="text-slate-500 font-medium">Supply Scope</dt>
                <dd className="mt-1 sm:mt-0 sm:col-span-2 text-slate-900">
                  <span className={`inline-block px-2 py-0.5 rounded text-xs font-medium ${
                    product.domestic_or_international === 'Domestic'
                      ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                      : 'bg-sky-50 text-sky-700 border border-sky-200'
                  }`}>
                    {product.domestic_or_international}
                  </span>
                </dd>
              </div>

              <div className="px-4 py-3 sm:grid sm:grid-cols-3 sm:gap-4">
                <dt className="text-slate-500 font-medium">Per Day Requirement</dt>
                <dd className="mt-1 sm:mt-0 sm:col-span-2 text-slate-900">
                  {product.per_day_requirement.toLocaleString()} units / day
                </dd>
              </div>

              <div className="px-4 py-3 sm:grid sm:grid-cols-3 sm:gap-4">
                <dt className="text-slate-500 font-medium">Minimum Order Quantity (MOQ)</dt>
                <dd className="mt-1 sm:mt-0 sm:col-span-2 text-slate-900">
                  {product.minimum_order_quantity.toLocaleString()} units
                </dd>
              </div>

              <div className="px-4 py-3 sm:grid sm:grid-cols-3 sm:gap-4">
                <dt className="text-slate-500 font-medium">Line Feeding Method</dt>
                <dd className="mt-1 sm:mt-0 sm:col-span-2 text-slate-900">
                  {product.line_feeding_method}
                </dd>
              </div>

              {product.created_at && (
                <div className="px-4 py-3 sm:grid sm:grid-cols-3 sm:gap-4">
                  <dt className="text-slate-500 font-medium">Record Created</dt>
                  <dd className="mt-1 sm:mt-0 sm:col-span-2 text-slate-600 text-xs">
                    {product.created_at}
                  </dd>
                </div>
              )}
            </dl>
          </div>
        </div>

        {/* Footer */}
        <div className="px-6 py-4 border-t border-slate-200 bg-slate-50 flex items-center justify-end gap-3 sticky bottom-0">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 bg-sky-600 text-white rounded-md text-sm font-medium hover:bg-sky-700 active:scale-[0.98] transition cursor-pointer shadow-xs"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  )
}
