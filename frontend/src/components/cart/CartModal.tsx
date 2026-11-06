import { useEffect, useState } from 'react'
import type { CartSummary, CartItem } from '../../types/cart'
import type { WorkflowResult } from '../../types/workflow'
import {
  fetchCart,
  updateCartItemQuantity,
  removeCartItem,
  clearCart,
} from '../../services/cartApi'
import { runCartWorkflow } from '../../services/workflowApi'
import { getMaterialBadgeStyle } from '../../utils/materialBadges'
import WorkflowMessageCard from '../chatbot/WorkflowMessageCard'

interface CartModalProps {
  isOpen: boolean
  onClose: () => void
  onCartUpdated?: (cart: CartSummary) => void
}

export default function CartModal({
  isOpen,
  onClose,
  onCartUpdated,
}: CartModalProps) {
  const [cart, setCart] = useState<CartSummary | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [updatingItemId, setUpdatingItemId] = useState<number | null>(null)

  // Optimization workflow state
  const [optimizing, setOptimizing] = useState(false)
  const [optimizationError, setOptimizationError] = useState<string | null>(null)
  const [workflowResult, setWorkflowResult] = useState<WorkflowResult | null>(null)

  const loadCartData = async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await fetchCart()
      setCart(data)
      onCartUpdated?.(data)
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to fetch cart'
      setError(msg)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (isOpen) {
      loadCartData()
    } else {
      // Reset view when closed
      setWorkflowResult(null)
      setOptimizationError(null)
    }
  }, [isOpen])

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isOpen) {
        onClose()
      }
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [isOpen, onClose])

  if (!isOpen) return null

  const items = cart?.items || []

  const handleUpdateQuantity = async (item: CartItem, delta: number) => {
    const newQty = item.number_of_parts + delta
    if (newQty <= 0) {
      handleRemoveItem(item.id)
      return
    }
    setUpdatingItemId(item.id)
    try {
      const res = await updateCartItemQuantity(item.id, newQty)
      setCart(res.cart)
      onCartUpdated?.(res.cart)
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to update quantity'
      setError(msg)
    } finally {
      setUpdatingItemId(null)
    }
  }

  const handleRemoveItem = async (itemId: number) => {
    setUpdatingItemId(itemId)
    try {
      const res = await removeCartItem(itemId)
      setCart(res.cart)
      onCartUpdated?.(res.cart)
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to remove item'
      setError(msg)
    } finally {
      setUpdatingItemId(null)
    }
  }

  const handleClearCart = async () => {
    if (!window.confirm('Are you sure you want to remove all items from the cart?')) {
      return
    }
    setLoading(true)
    try {
      const res = await clearCart()
      setCart(res.cart)
      onCartUpdated?.(res.cart)
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to clear cart'
      setError(msg)
    } finally {
      setLoading(false)
    }
  }

  const handleOptimizePackage = async () => {
    if (!items || items.length === 0) return
    setOptimizing(true)
    setOptimizationError(null)

    try {
      // Pass only product name/id along with product number (quantity) only
      const payloadItems = items.map((it) => ({
        product_id: it.product_id,
        part_name: it.part_name,
        number_of_parts: it.number_of_parts,
      }))

      const res: WorkflowResult = await runCartWorkflow(payloadItems)
      setWorkflowResult(res)
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to run optimization workflow'
      setOptimizationError(msg)
    } finally {
      setOptimizing(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-2 sm:p-4">
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
        aria-labelledby="cart-modal-title"
        className={`relative bg-white rounded-2xl shadow-2xl transition-all duration-200 overflow-hidden border border-slate-200 z-10 flex flex-col ${
          workflowResult
            ? 'max-w-5xl w-full max-h-[94vh]'
            : 'max-w-2xl w-full max-h-[90vh]'
        }`}
      >
        {/* Header */}
        <div className="px-6 py-4 border-b border-slate-200 flex items-center justify-between bg-white shrink-0">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-sky-100 text-sky-700 flex items-center justify-center shrink-0">
              {workflowResult ? (
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="m21 7.5-9-5.25L3 7.5m18 0-9 5.25m9-5.25v9l-9 5.25M3 7.5l9 5.25M3 7.5v9l9 5.25m0-9v9" />
                </svg>
              ) : (
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}>
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    d="M2.25 3h1.386c.51 0 .955.343 1.087.835l.383 1.437M7.5 14.25a3 3 0 00-3 3h15.75m-12.75-3h11.218c1.121-2.3 2.1-4.684 2.924-7.138a60.114 60.114 0 00-16.536-1.84M7.5 14.25L5.106 5.272M6 20.25a.75.75 0 11-1.5 0 .75.75 0 011.5 0zm12.75 0a.75.75 0 11-1.5 0 .75.75 0 011.5 0z"
                  />
                </svg>
              )}
            </div>

            <div>
              <div className="flex items-center gap-2">
                <h2 id="cart-modal-title" className="text-lg font-bold text-slate-900">
                  {workflowResult ? 'Package Optimization Results' : 'Products Cart'}
                </h2>
                {!workflowResult && cart && cart.total_parts > 0 && (
                  <span className="text-xs font-semibold px-2 py-0.5 rounded-full bg-sky-100 text-sky-800 border border-sky-200">
                    {cart.total_parts} {cart.total_parts === 1 ? 'part' : 'parts'}
                  </span>
                )}
                {workflowResult && (
                  <span className={`text-xs font-semibold px-2 py-0.5 rounded-full border ${workflowResult.fits ? 'bg-emerald-100 text-emerald-800 border-emerald-200' : 'bg-amber-100 text-amber-800 border-amber-200'}`}>
                    {workflowResult.fits ? 'Optimization Complete' : 'No Complete Fit'}
                  </span>
                )}
              </div>
              <p className="text-xs text-slate-500 mt-0.5">
                {workflowResult
                  ? '3D container loading simulation and multi-agent recommendations.'
                  : 'Review products and quantities selected for container packaging.'}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            {workflowResult && (
              <button
                type="button"
                onClick={() => setWorkflowResult(null)}
                className="px-3 py-1.5 text-xs font-semibold text-sky-700 bg-sky-50 border border-sky-200 rounded-lg hover:bg-sky-100 active:scale-[0.98] transition cursor-pointer"
              >
                ← Back to Cart
              </button>
            )}

            <button
              type="button"
              onClick={onClose}
              aria-label="Close dialog"
              className="p-1.5 rounded-lg text-slate-400 hover:text-slate-600 hover:bg-slate-100 transition-colors cursor-pointer"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        </div>

        {/* Body Content */}
        <div className="p-5 sm:p-6 overflow-y-auto space-y-4 flex-1">
          {/* Workflow Results View */}
          {workflowResult && (
            <div className="space-y-4">
              <WorkflowMessageCard result={workflowResult} />
            </div>
          )}

          {/* Normal Cart View (when not viewing workflow results) */}
          {!workflowResult && (
            <>
              {(error || optimizationError) && (
                <div className="p-3 bg-red-50 border border-red-200 rounded-xl text-xs text-red-700 flex items-center justify-between">
                  <span>{error || optimizationError}</span>
                  <button
                    type="button"
                    onClick={() => {
                      setError(null)
                      setOptimizationError(null)
                      loadCartData()
                    }}
                    className="font-semibold underline hover:text-red-900 cursor-pointer ml-3"
                  >
                    Retry
                  </button>
                </div>
              )}

              {loading && !cart && (
                <div className="py-12 text-center text-slate-400 space-y-2">
                  <div className="w-8 h-8 border-2 border-sky-600 border-t-transparent rounded-full animate-spin mx-auto" />
                  <p className="text-xs">Loading cart items...</p>
                </div>
              )}

              {!loading && items.length === 0 && (
                <div className="py-12 px-4 text-center border-2 border-dashed border-slate-200 rounded-xl bg-slate-50/50">
                  <div className="w-12 h-12 rounded-full bg-slate-100 text-slate-400 flex items-center justify-center mx-auto mb-3">
                    <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={1.5}>
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        d="M15.75 10.5V6a3.75 3.75 0 10-7.5 0v4.5m11.356-1.993l1.263 12c.07.665-.45 1.243-1.119 1.243H4.25a1.125 1.125 0 01-1.12-1.243l1.264-12A1.125 1.125 0 015.513 7.5h12.974c.576 0 1.059.435 1.119 1.007zM8.625 10.5a.375.375 0 11-.75 0 .375.375 0 01.75 0zm7.5 0a.375.375 0 11-.75 0 .375.375 0 01.75 0z"
                      />
                    </svg>
                  </div>
                  <h3 className="text-sm font-semibold text-slate-800">Your cart is empty</h3>
                  <p className="text-xs text-slate-500 max-w-xs mx-auto mt-1">
                    Open any product in the catalog and click &ldquo;Add to Cart&rdquo; to begin assembling your packaging manifest.
                  </p>
                </div>
              )}

              {items.length > 0 && (
                <div className="space-y-3">
                  {items.map((item) => {
                    const badge = getMaterialBadgeStyle(item.part_type)
                    const isUpdating = updatingItemId === item.id

                    return (
                      <div
                        key={item.id}
                        className="p-4 bg-white border border-slate-200 rounded-xl hover:border-slate-300 transition-all flex flex-col sm:flex-row sm:items-center justify-between gap-3 shadow-2xs"
                      >
                        {/* Item Info */}
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2">
                            <h4 className="text-sm font-bold text-slate-900 truncate">
                              {item.part_name}
                            </h4>
                            <span
                              className={`text-[10px] font-semibold px-2 py-0.5 rounded border capitalize ${badge.bg} ${badge.text} ${badge.border}`}
                            >
                              {item.part_type}
                            </span>
                          </div>

                          <div className="mt-1 flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-slate-500">
                            <span>
                              {item.part_length} &times; {item.part_breadth} &times; {item.part_height} mm
                            </span>
                            <span>•</span>
                            <span>{item.part_weight} kg / unit</span>
                            <span>•</span>
                            <span className="font-semibold text-slate-700">
                              Total: {item.line_weight_kg} kg
                            </span>
                          </div>
                        </div>

                        {/* Stepper & Delete */}
                        <div className="flex items-center justify-between sm:justify-end gap-3 shrink-0">
                          <div className="inline-flex items-center border border-slate-300 rounded-lg overflow-hidden bg-white shadow-2xs">
                            <button
                              type="button"
                              onClick={() => handleUpdateQuantity(item, -1)}
                              disabled={isUpdating || optimizing}
                              aria-label="Decrease quantity"
                              className="px-2.5 py-1 text-slate-600 hover:bg-slate-100 active:bg-slate-200 transition-colors cursor-pointer text-sm font-bold disabled:opacity-50 select-none"
                            >
                              −
                            </button>

                            <span className="px-3 py-1 text-xs font-bold text-slate-900 min-w-8 text-center font-mono">
                              {item.number_of_parts}
                            </span>

                            <button
                              type="button"
                              onClick={() => handleUpdateQuantity(item, 1)}
                              disabled={isUpdating || optimizing}
                              aria-label="Increase quantity"
                              className="px-2.5 py-1 text-slate-600 hover:bg-slate-100 active:bg-slate-200 transition-colors cursor-pointer text-sm font-bold disabled:opacity-50 select-none"
                            >
                              +
                            </button>
                          </div>

                          <button
                            type="button"
                            onClick={() => handleRemoveItem(item.id)}
                            disabled={isUpdating || optimizing}
                            aria-label={`Remove ${item.part_name}`}
                            className="p-1.5 rounded-lg text-slate-400 hover:text-rose-600 hover:bg-rose-50 transition-colors cursor-pointer disabled:opacity-50"
                            title="Remove from cart"
                          >
                            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}>
                              <path
                                strokeLinecap="round"
                                strokeLinejoin="round"
                                d="M14.74 9l-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 01-2.244 2.077H8.084a2.25 2.25 0 01-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 00-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 013.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 00-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 00-7.5 0"
                              />
                            </svg>
                          </button>
                        </div>
                      </div>
                    )
                  })}
                </div>
              )}

              {/* Aggregated Totals Card */}
              {cart && items.length > 0 && (
                <div className="p-4 bg-sky-50/70 border border-sky-100 rounded-xl grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
                  <div>
                    <span className="text-sky-600 block">Total Items</span>
                    <span className="text-sm font-bold text-sky-950 font-mono">
                      {cart.total_items} {cart.total_items === 1 ? 'part type' : 'part types'}
                    </span>
                  </div>
                  <div>
                    <span className="text-sky-600 block">Total Parts</span>
                    <span className="text-sm font-bold text-sky-950 font-mono">
                      {cart.total_parts} units
                    </span>
                  </div>
                  <div>
                    <span className="text-sky-600 block">Total Weight</span>
                    <span className="text-sm font-bold text-sky-950 font-mono">
                      {cart.total_weight_kg} kg
                    </span>
                  </div>
                  <div>
                    <span className="text-sky-600 block">Total Volume</span>
                    <span className="text-sm font-bold text-sky-950 font-mono">
                      {cart.total_volume_liters} L
                    </span>
                  </div>
                </div>
              )}
            </>
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-3.5 border-t border-slate-200 bg-slate-50 flex items-center justify-between shrink-0">
          <div>
            {!workflowResult && items.length > 0 && (
              <button
                type="button"
                onClick={handleClearCart}
                disabled={loading || optimizing}
                className="text-xs font-semibold text-rose-600 hover:text-rose-800 transition-colors cursor-pointer disabled:opacity-50"
              >
                Clear Cart
              </button>
            )}

            {workflowResult && (
              <button
                type="button"
                onClick={() => setWorkflowResult(null)}
                className="text-xs font-semibold text-slate-600 hover:text-slate-900 transition-colors cursor-pointer"
              >
                ← Back to Cart
              </button>
            )}
          </div>

          <div className="flex items-center gap-2.5">
            {!workflowResult && items.length > 0 && (
              <button
                type="button"
                onClick={handleOptimizePackage}
                disabled={optimizing}
                className="px-4 py-2 bg-sky-600 hover:bg-sky-700 text-white rounded-lg text-xs font-semibold shadow-xs active:scale-[0.98] transition flex items-center gap-2 cursor-pointer disabled:opacity-50"
              >
                {optimizing ? (
                  <>
                    <div className="w-3.5 h-3.5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                    <span>Optimising Package…</span>
                  </>
                ) : (
                  <>
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="m21 7.5-9-5.25L3 7.5m18 0-9 5.25m9-5.25v9l-9 5.25M3 7.5l9 5.25M3 7.5v9l9 5.25m0-9v9" />
                    </svg>
                    <span>Optimise Package</span>
                  </>
                )}
              </button>
            )}

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
    </div>
  )
}
