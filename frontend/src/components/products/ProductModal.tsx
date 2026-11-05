import { useEffect, useState } from 'react'
import type { Product } from '../../types/customBox'
import { getMaterialBadgeStyle } from '../../utils/materialBadges'
import ProductMeshViewer from './ProductMeshViewer'
import { addToCart } from '../../services/cartApi'

interface ProductModalProps {
  product: Product | null
  onClose: () => void
  onCartUpdated?: () => void
}

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000/api'

export default function ProductModal({
  product,
  onClose,
  onCartUpdated,
}: ProductModalProps) {
  const [quantity, setQuantity] = useState<number>(1)
  const [addingToCart, setAddingToCart] = useState<boolean>(false)
  const [addedFeedback, setAddedFeedback] = useState<boolean>(false)

  useEffect(() => {
    if (product) {
      setQuantity(product.standard_no_of_parts || 1)
      setAddedFeedback(false)
    }
  }, [product])

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

  const handleAddToCart = async () => {
    setAddingToCart(true)
    try {
      await addToCart({
        product_id: product.id,
        part_name: product.part_name,
        number_of_parts: quantity,
        part_type: product.part_type,
        part_length: product.part_length,
        part_breadth: product.part_breadth,
        part_height: product.part_height,
        part_weight: product.part_weight,
      })
      setAddedFeedback(true)
      onCartUpdated?.()
      setTimeout(() => {
        setAddedFeedback(false)
      }, 1500)
    } catch (err) {
      console.error('Failed to add to cart:', err)
    } finally {
      setAddingToCart(false)
    }
  }

  const badgeStyle = getMaterialBadgeStyle(product.part_type)
  const hasModel = Boolean(product.model_file)
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
        <div className="px-6 py-4 border-b border-slate-200 flex items-center justify-between sticky top-0 bg-white z-20">
          <div>
            <div className="flex items-center gap-2">
              <span
                className={`text-xs font-semibold px-2.5 py-0.5 rounded border capitalize ${badgeStyle.bg} ${badgeStyle.text} ${badgeStyle.border}`}
              >
                {product.part_type}
              </span>
              {hasModel && (
                <span className="text-xs font-semibold px-2 py-0.5 rounded bg-sky-600 text-white shadow-2xs">
                  3D CAD (.STEP)
                </span>
              )}
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
          {/* Interactive 3D Mesh Viewer powered by Python Trimesh */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-slate-700 uppercase tracking-wider flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
                Live 3D Mesh Viewer
              </span>

              {hasModel && (
                <a
                  href={`${API_BASE}/products/${product.id ?? encodeURIComponent(product.part_name)}/model`}
                  download
                  target="_blank"
                  rel="noreferrer"
                  className="text-xs font-semibold text-sky-700 hover:text-sky-900 bg-sky-50 border border-sky-200 hover:bg-sky-100 px-2.5 py-1 rounded transition flex items-center gap-1.5 shadow-2xs"
                >
                  <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M3 16.5v2.25A2.25 2.25 0 0 0 5.25 21h13.5A2.25 2.25 0 0 0 21 18.75V16.5M16.5 12 12 16.5m0 0L7.5 12m4.5 4.5V3" />
                  </svg>
                  <span>Download .STEP</span>
                </a>
              )}
            </div>

            <ProductMeshViewer
              productIdOrName={product.id ?? product.part_name}
              hasCadModel={hasModel}
              height="h-64 sm:h-72"
            />
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

              {product.model_file && (
                <div className="px-4 py-3 sm:grid sm:grid-cols-3 sm:gap-4 bg-sky-50/30">
                  <dt className="text-sky-900 font-medium">Associated 3D Model</dt>
                  <dd className="mt-1 sm:mt-0 sm:col-span-2 text-sky-800 font-mono text-xs flex items-center gap-2">
                    <span className="px-2 py-0.5 rounded bg-white border border-sky-200 font-medium">
                      {product.model_file}
                    </span>
                  </dd>
                </div>
              )}

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

        {/* Footer with Add to Cart controls & Close button */}
        <div className="px-6 py-3.5 border-t border-slate-200 bg-slate-50 flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3 sticky bottom-0 z-20">
          {/* Quantity Stepper & Add to Cart Button */}
          <div className="flex items-center gap-2.5">
            {/* Number Stepper: [-] [ quantity ] [+] */}
            <div className="inline-flex items-center border border-slate-300 rounded-lg overflow-hidden bg-white shadow-2xs">
              <button
                type="button"
                onClick={() => setQuantity((q) => Math.max(1, q - 1))}
                aria-label="Decrease parts quantity"
                className="px-3 py-1.5 text-slate-600 hover:bg-slate-100 active:bg-slate-200 transition-colors cursor-pointer text-sm font-bold select-none"
              >
                −
              </button>
              <input
                type="number"
                min="1"
                value={quantity}
                onChange={(e) => setQuantity(Math.max(1, parseInt(e.target.value) || 1))}
                aria-label="Quantity of parts"
                className="w-14 py-1.5 text-center text-xs font-bold text-slate-900 border-x border-slate-200 focus:outline-none font-mono"
              />
              <button
                type="button"
                onClick={() => setQuantity((q) => q + 1)}
                aria-label="Increase parts quantity"
                className="px-3 py-1.5 text-slate-600 hover:bg-slate-100 active:bg-slate-200 transition-colors cursor-pointer text-sm font-bold select-none"
              >
                +
              </button>
            </div>

            {/* Add to Cart Button */}
            <button
              type="button"
              onClick={handleAddToCart}
              disabled={addingToCart}
              className={`inline-flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-semibold shadow-xs transition-all active:scale-[0.98] cursor-pointer disabled:opacity-50 ${
                addedFeedback
                  ? 'bg-emerald-600 text-white hover:bg-emerald-700'
                  : 'bg-sky-600 text-white hover:bg-sky-700'
              }`}
            >
              {addedFeedback ? (
                <>
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
                  </svg>
                  <span>Added {quantity} to Cart!</span>
                </>
              ) : (
                <>
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}>
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      d="M2.25 3h1.386c.51 0 .955.343 1.087.835l.383 1.437M7.5 14.25a3 3 0 00-3 3h15.75m-12.75-3h11.218c1.121-2.3 2.1-4.684 2.924-7.138a60.114 60.114 0 00-16.536-1.84M7.5 14.25L5.106 5.272M6 20.25a.75.75 0 11-1.5 0 .75.75 0 011.5 0zm12.75 0a.75.75 0 11-1.5 0 .75.75 0 011.5 0z"
                    />
                  </svg>
                  <span>{addingToCart ? 'Adding…' : 'Add to Cart'}</span>
                </>
              )}
            </button>
          </div>

          {/* Close Dialog Button */}
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 bg-white border border-slate-300 text-slate-700 hover:bg-slate-100 rounded-lg text-xs font-semibold active:scale-[0.98] transition cursor-pointer"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  )
}
