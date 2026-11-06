import { useState } from 'react'
import type { WorkflowResult } from '../../types/workflow'
import PackingSceneViewer from './PackingSceneViewer'
import ToolExecutionTrace from './ToolExecutionTrace'
import PlacedPartsManifest from './PlacedPartsManifest'

interface WorkflowMessageCardProps {
  result: WorkflowResult
  onApplyPrompt?: (promptText: string) => void
  onConfirmProduct?: (product: any, quantity: number) => void
}

export default function WorkflowMessageCard({
  result,
  onApplyPrompt,
  onConfirmProduct,
}: WorkflowMessageCardProps) {
  const [activeTab, setActiveTab] = useState<'3d' | 'candidates' | 'specs'>('3d')
  const [selectedContainerName, setSelectedContainerName] = useState<string | null>(null)
  const [confirmQuantity, setConfirmQuantity] = useState<number>(
    result.requested_quantity || result.matched_product?.standard_no_of_parts || 1
  )
  const [activeMatchedProduct, setActiveMatchedProduct] = useState<any>(
    result.matched_product || null
  )
  const matchedProducts = result.matched_products ?? []

  const req = result.requirements ?? {}
  const metrics = result.metrics ?? {}
  const candidates = result.candidate_packages ?? []
  const allEvals = result.all_evaluations ?? []
  const recommendation = result.ai_recommendation
  const util = result.utilization_metrics
  const bestCont = result.best_container

  // If user selected a specific container, find its Extreme Point evaluation
  const activeEval =
    (selectedContainerName && allEvals.find((e) => e.container_name === selectedContainerName)) ||
    (bestCont && allEvals.find((e) => e.container_name === bestCont.name)) ||
    allEvals[0] ||
    null

  const isWinner = Boolean(activeEval && bestCont && activeEval.container_name === bestCont.name)
  const activeContName = activeEval?.container_name || bestCont?.name || 'Container'
  const activeCategory = activeEval?.category || bestCont?.category || 'carton'

  const activeDims =
    activeEval?.container_dimensions ||
    bestCont?.inner_dimensions_mm ||
    bestCont?.dimensions ||
    result.scene_data?.container?.dimensions || {
      length: 0,
      width: 0,
      height: 0,
    }

  const activeMaxWeight = activeEval?.max_weight_capacity_kg ?? bestCont?.max_weight_capacity_kg ?? 0
  const activeSceneData = activeEval?.scene_data || result.scene_data
  const hasScene = Boolean(activeSceneData?.container?.dimensions)

  const activeUtil = activeEval
    ? {
        total_items: activeEval.total_items,
        placed_count: activeEval.placed_count,
        unplaced_count: activeEval.unplaced_count,
        container_volume_liters: activeEval.container_dimensions?.volume_liters || 0,
        items_volume_liters:
          Math.round(
            ((activeEval.container_dimensions?.volume_liters || 0) * (activeEval.volume_utilization_pct / 100)) * 100
          ) / 100,
        volume_utilization_pct: activeEval.volume_utilization_pct,
        wasted_volume_liters: activeEval.wasted_volume_liters,
        total_packed_weight_kg: activeEval.total_packed_weight_kg || 0,
        max_utilization: activeEval.max_utilization || util?.max_utilization,
      }
    : util

  const activePlacedItems = activeEval?.placed_items || result.placed_items
  const activeUnplacedItems = activeEval?.unplaced_items || result.unplaced_items
  const activeOrientationsBreakdown = activeEval?.orientations_breakdown || result.orientations_breakdown
  const activeBestOrientation = activeEval?.best_orientation || result.best_orientation
  const isHitl = result.hitl_required

  const partName = req.name || metrics.part_name || 'Part'
  const snp = req.snp || metrics.snp || 1
  const foamMaterial = metrics.recommended_padding_material || 'Polyethylene Foam'
  const foamThickness = metrics.recommended_padding_thickness_mm ?? 15
  const productMeshIdentifier = req.product_id ?? req.matched_product_id ?? req.name ?? metrics.part_name
  const productMeshUrl = productMeshIdentifier
    ? `${import.meta.env.VITE_API_URL || 'http://localhost:8000/api'}/products/${encodeURIComponent(String(productMeshIdentifier))}/mesh`
    : undefined
  const taskProducts = result.task_manifest?.length
    ? result.task_manifest
    : req.product_id
      ? [{ product_id: req.product_id, part_name: partName, quantity: Number(snp) || 1 }]
      : []

  return (
    <div className="w-full space-y-3.5">

      {/* 3. Human-In-The-Loop Clarification Banner (if HITL required and not product_not_found) */}
      {isHitl && !result.product_not_found && (
        <div className="bg-amber-50 border border-amber-200 rounded-xl p-4 shadow-2xs">
          <div className="flex items-start gap-3">
            <div className="w-7 h-7 rounded-lg bg-amber-500 text-white flex items-center justify-center shrink-0 font-bold text-sm shadow-xs">
              !
            </div>
            <div className="flex-1">
              <h4 className="text-sm font-semibold text-amber-900">
                Tell me a little more about the part
              </h4>
              <p className="text-xs text-amber-800 mt-1 leading-relaxed">
                {result.summary || result.hitl_reason ||
                  'Share the part dimensions, unit weight, and quantity so I can work out a package.'}
              </p>

              {/* Quick Prompt Suggestion Chips for User Convenience */}
              {onApplyPrompt && (
                <div className="mt-3 pt-3 border-t border-amber-200/80">
                  <div className="text-[11px] font-semibold text-amber-900 uppercase tracking-wider mb-2">
                    Quick suggestions to provide:
                  </div>
                  <div className="flex flex-wrap gap-1.5">
                    <button
                      type="button"
                      onClick={() =>
                        onApplyPrompt(
                          'Pack 4 steel brackets measuring 140x90x60mm with weight 1.2kg each.'
                        )
                      }
                      className="text-xs bg-white text-amber-900 border border-amber-300 hover:bg-amber-100/70 px-2.5 py-1 rounded-md font-medium transition-colors cursor-pointer"
                    >
                      Steel bracket (140×90×60mm, 4 units)
                    </button>
                    <button
                      type="button"
                      onClick={() =>
                        onApplyPrompt('Lookup product 1 and pack 64 units.')
                      }
                      className="text-xs bg-white text-amber-900 border border-amber-300 hover:bg-amber-100/70 px-2.5 py-1 rounded-md font-medium transition-colors cursor-pointer"
                    >
                      Micro Terminal Block (Product 1)
                    </button>
                    <button
                      type="button"
                      onClick={() =>
                        onApplyPrompt(
                          'Add dimensions: length 220mm, width 140mm, height 85mm, weight 2.5kg, quantity 6.'
                        )
                      }
                      className="text-xs bg-white text-amber-900 border border-amber-300 hover:bg-amber-100/70 px-2.5 py-1 rounded-md font-medium transition-colors cursor-pointer"
                    >
                      Custom Dimensions (220×140×85mm)
                    </button>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* 2.5 Product Confirmation Dialogue */}
      {result.confirmation_required && matchedProducts.length > 0 && (
        <div className="bg-sky-50/60 border-2 border-sky-300 rounded-2xl p-5 shadow-sm">
          <h3 className="text-base font-bold text-slate-900">Please confirm this packing list</h3>
          <p className="text-xs text-slate-600 mt-1">I found these products in the catalog. Confirm to add them to your optimization cart; you can add more products before running the optimizer.</p>
          <div className="mt-3 space-y-2">
            {matchedProducts.map((product, index) => (
              <div key={`${product.product_id}-${index}`} className="bg-white border border-sky-200 rounded-xl p-3 flex flex-wrap items-center justify-between gap-2">
                <div>
                  <div className="text-sm font-semibold text-slate-900">{product.part_name}</div>
                  <div className="text-xs text-slate-500">Product ID #{product.product_id} · {product.part_length} × {product.part_width} × {product.part_height} mm · {product.part_weight} kg each</div>
                </div>
                <div className="text-sm font-semibold text-sky-800">Quantity: {product.quantity}</div>
              </div>
            ))}
          </div>
          <button
            type="button"
            onClick={() => onConfirmProduct?.(matchedProducts, result.requested_quantity ?? matchedProducts.reduce((total, product) => total + product.quantity, 0))}
            className="mt-4 bg-emerald-600 hover:bg-emerald-700 active:scale-[0.98] text-white font-semibold text-xs py-2 px-4 rounded-xl shadow-xs transition-all cursor-pointer"
          >
            Add confirmed products
          </button>
        </div>
      )}
      {result.confirmation_required && matchedProducts.length === 0 && activeMatchedProduct && (
        <div className="bg-sky-50/60 border-2 border-sky-300 rounded-2xl p-5 shadow-sm">
          <div className="flex items-start gap-3.5">
            <div className="w-9 h-9 rounded-xl bg-sky-600 text-white flex items-center justify-center shrink-0 shadow-xs">
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="m21 21-5.197-5.197m0 0A7.5 7.5 0 1 0 5.196 5.196a7.5 7.5 0 0 0 10.607 10.607Z" />
              </svg>
            </div>
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2">
                <span className="text-[11px] font-bold uppercase tracking-wider text-sky-700 bg-sky-100 px-2 py-0.5 rounded-full">
                  Database Catalog Match
                </span>
                <span className="text-xs text-slate-500 font-mono">
                  Product ID #{activeMatchedProduct.id}
                </span>
              </div>
              <h3 className="text-base font-bold text-slate-900 mt-1">
                Is this the product you want to pack?
              </h3>
              <p className="text-xs text-slate-600 mt-0.5">
                The optimization agent validated your prompt against our SQLite database. Please confirm the product and quantity to proceed with 3D packing.
              </p>

              {/* Matched Product Specs Card */}
              <div className="mt-3.5 bg-white border border-sky-200 rounded-xl p-3.5 shadow-2xs">
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <h4 className="text-sm font-bold text-slate-900">
                      {activeMatchedProduct.part_name}
                    </h4>
                    <span className="text-xs text-sky-700 font-medium">
                      {activeMatchedProduct.part_type || 'Standard Part'}
                    </span>
                  </div>
                  <span className="text-[11px] font-medium bg-slate-100 text-slate-600 px-2 py-0.5 rounded">
                    SNP: {activeMatchedProduct.standard_no_of_parts || 1}
                  </span>
                </div>

                <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 mt-3 pt-3 border-t border-slate-100 text-xs">
                  <div>
                    <span className="text-slate-400 block text-[10px] uppercase font-semibold">Dimensions</span>
                    <span className="font-semibold text-slate-800">
                      {activeMatchedProduct.part_length} × {activeMatchedProduct.part_breadth || activeMatchedProduct.part_width} × {activeMatchedProduct.part_height} mm
                    </span>
                  </div>
                  <div>
                    <span className="text-slate-400 block text-[10px] uppercase font-semibold">Unit Weight</span>
                    <span className="font-semibold text-slate-800">
                      {activeMatchedProduct.part_weight} kg
                    </span>
                  </div>
                  <div>
                    <span className="text-slate-400 block text-[10px] uppercase font-semibold">Total Est. Weight</span>
                    <span className="font-semibold text-slate-800">
                      {(confirmQuantity * (activeMatchedProduct.part_weight || 0.1)).toFixed(2)} kg
                    </span>
                  </div>
                  <div>
                    <span className="text-slate-400 block text-[10px] uppercase font-semibold">Feed Method</span>
                    <span className="font-semibold text-slate-800 truncate block">
                      {activeMatchedProduct.line_feeding_method || 'Two-Bin'}
                    </span>
                  </div>
                </div>
              </div>

              {/* Other candidate options if user meant something else */}
              {result.other_candidates && result.other_candidates.length > 0 && (
                <div className="mt-3">
                  <span className="text-[11px] font-medium text-slate-500 block mb-1">
                    Or did you mean:
                  </span>
                  <div className="flex flex-wrap gap-1.5">
                    {result.other_candidates.map((cand) => (
                      <button
                        key={cand.id}
                        type="button"
                        onClick={() => setActiveMatchedProduct(cand)}
                        className={`text-xs px-2.5 py-1 rounded-lg border font-medium transition-colors cursor-pointer ${
                          activeMatchedProduct.id === cand.id
                            ? 'bg-sky-600 text-white border-sky-600'
                            : 'bg-white text-slate-700 border-slate-200 hover:bg-slate-50'
                        }`}
                      >
                        {cand.part_name} (ID #{cand.id})
                      </button>
                    ))}
                  </div>
                </div>
              )}

              {/* Quantity Stepper and Confirm Button */}
              <div className="mt-4 pt-3.5 border-t border-sky-200/80 flex flex-wrap items-center justify-between gap-3">
                <div className="flex items-center gap-2">
                  <span className="text-xs font-semibold text-slate-700">Quantity to Pack:</span>
                  <div className="flex items-center border border-slate-300 rounded-lg overflow-hidden bg-white shadow-2xs">
                    <button
                      type="button"
                      onClick={() => setConfirmQuantity((prev) => Math.max(1, prev - 1))}
                      disabled={confirmQuantity <= 1}
                      className="px-2.5 py-1 text-slate-600 hover:bg-slate-100 disabled:opacity-40 disabled:cursor-not-allowed text-xs font-bold transition-colors cursor-pointer"
                    >
                      -
                    </button>
                    <input
                      type="number"
                      min={1}
                      value={confirmQuantity}
                      onChange={(e) => {
                        const val = parseInt(e.target.value, 10)
                        if (!isNaN(val) && val >= 1) setConfirmQuantity(val)
                      }}
                      className="w-12 text-center text-xs font-semibold text-slate-800 border-x border-slate-200 py-1 focus:outline-none"
                    />
                    <button
                      type="button"
                      onClick={() => setConfirmQuantity((prev) => prev + 1)}
                      className="px-2.5 py-1 text-slate-600 hover:bg-slate-100 text-xs font-bold transition-colors cursor-pointer"
                    >
                      +
                    </button>
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    onClick={() => {
                      if (onConfirmProduct) {
                        onConfirmProduct(activeMatchedProduct, confirmQuantity)
                      }
                    }}
                    className="bg-emerald-600 hover:bg-emerald-700 active:scale-[0.98] text-white font-semibold text-xs py-2 px-4 rounded-xl shadow-xs transition-all flex items-center gap-1.5 cursor-pointer"
                  >
                    <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2.5}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="m4.5 12.75 6 6 9-13.5" />
                    </svg>
                    <span>Yes, Confirm & Optimize Package</span>
                  </button>
                </div>
              </div>

            </div>
          </div>
        </div>
      )}

      {/* 2.6 Product Not Found Banner (Anti-Hallucination Guardrail) */}
      {result.product_not_found && (
        <div className="bg-rose-50 border-2 border-rose-200 rounded-2xl p-5 shadow-2xs">
          <div className="flex items-start gap-3.5">
            <div className="w-9 h-9 rounded-xl bg-rose-600 text-white flex items-center justify-center shrink-0 font-bold text-base shadow-xs">
              ✕
            </div>
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2">
                <span className="text-[11px] font-bold uppercase tracking-wider text-rose-700 bg-rose-100 px-2 py-0.5 rounded-full">
                  Unverified Product Blocked
                </span>
                <span className="text-xs text-rose-600 font-medium">
                  Catalog Strictness Enforced
                </span>
              </div>
              <h4 className="text-base font-bold text-rose-950 mt-1">
                Product Not Found in Database Catalog
              </h4>
              <p className="text-xs text-rose-800 mt-1 leading-relaxed">
                The optimization agent strictly avoids reasoning about or optimizing for made-up products.
                All packaging recommendations require verified CAD specifications and weight ratings from our SQLite catalog.
              </p>

              {result.available_products_sample && result.available_products_sample.length > 0 && onApplyPrompt && (
                <div className="mt-4 pt-3 border-t border-rose-200/80">
                  <div className="text-[11px] font-bold text-rose-900 uppercase tracking-wider mb-2">
                    Select a verified catalog product to optimize:
                  </div>
                  <div className="flex flex-wrap gap-2">
                    {result.available_products_sample.map((prod) => (
                      <button
                        key={prod.id}
                        type="button"
                        onClick={() =>
                          onApplyPrompt(
                            `Pack ${prod.standard_no_of_parts || 4} units of ${prod.part_name}`
                          )
                        }
                        className="text-xs bg-white text-slate-800 hover:text-rose-950 border border-rose-300 hover:border-rose-400 hover:bg-rose-100/50 px-3 py-1.5 rounded-lg font-medium transition-colors shadow-2xs cursor-pointer flex items-center gap-1.5"
                      >
                        <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
                        <span>{prod.part_name}</span>
                        <span className="text-[10px] text-slate-400 font-mono">#{prod.id}</span>
                      </button>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* 3.5 Major Heading: Granular Agent Tool Use Trace */}
      <ToolExecutionTrace steps={result.steps} />

      {taskProducts.length > 0 && result.action === 'optimized' && (
        <section className="rounded-xl border-2 border-sky-200 bg-sky-50/70 p-4 shadow-2xs">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div>
              <h3 className="text-sm font-bold text-slate-900">Products in this packing result</h3>
              <p className="mt-0.5 text-xs text-slate-600">Catalog products and quantities sent to the 3D placement optimizer.</p>
            </div>
            <span className="rounded-full border border-sky-200 bg-white px-2.5 py-1 text-xs font-semibold text-sky-800">
              {taskProducts.reduce((total, product) => total + (Number(product.quantity ?? product.snp) || 1), 0)} units requested
            </span>
          </div>
          <ul className="mt-3 grid gap-2 sm:grid-cols-2">
            {taskProducts.map((product, index) => {
              const productName = String(product.part_name ?? product.name ?? 'Catalog product')
              const placedCount = (activePlacedItems ?? []).filter((item) => (item.name ?? item.item_name) === productName).length
              const unplacedCount = (activeUnplacedItems ?? []).filter((item) => (item.name ?? item.item_name) === productName).length
              return (
                <li key={`${product.product_id ?? productName}-${index}`} className="flex items-center justify-between gap-3 rounded-lg border border-sky-100 bg-white px-3 py-2.5">
                  <div className="min-w-0">
                    <div className="truncate text-sm font-semibold text-slate-900">{productName}</div>
                    <div className="text-[11px] text-slate-500">{product.product_id != null ? `Product ID #${product.product_id}` : 'Catalog product'}</div>
                  </div>
                  <div className="shrink-0 text-right">
                    <div className="text-xs font-bold text-slate-800">{placedCount} / {Number(product.quantity ?? product.snp) || 1} placed</div>
                    {unplacedCount > 0 && <div className="text-[10px] font-medium text-amber-700">{unplacedCount} unplaced</div>}
                  </div>
                </li>
              )
            })}
          </ul>
        </section>
      )}

      {/* 4. Multi-Agent Process Results (Only shown when confirmed and not blocked by HITL) */}
      {!isHitl && !result.confirmation_required && !result.product_not_found && (
        <div className="bg-white border border-slate-200 rounded-xl overflow-hidden shadow-2xs">
          {/* Tabs Navigation Header */}
          <div className="border-b border-slate-200 bg-slate-50/70 px-3 py-2 flex items-center justify-between gap-2">
            <div className="flex items-center gap-1.5">
              <button
                type="button"
                onClick={() => setActiveTab('3d')}
                className={`px-3 py-1.5 text-xs font-semibold rounded-lg transition-colors cursor-pointer flex items-center gap-1.5 ${
                  activeTab === '3d'
                    ? 'bg-sky-600 text-white shadow-2xs'
                    : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'
                }`}
              >
                <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="m21 7.5-9-5.25L3 7.5m18 0-9 5.25m9-5.25v9l-9 5.25M3 7.5l9 5.25M3 7.5v9l9 5.25m0-9v9" />
                </svg>
                <span>3D Packing Solution</span>
                {activeUtil && (
                  <span className="ml-1 text-[10px] font-bold px-1.5 py-0.2 bg-white/20 rounded">
                    {activeUtil.volume_utilization_pct}%
                  </span>
                )}
              </button>

              <button
                type="button"
                onClick={() => setActiveTab('candidates')}
                className={`px-3 py-1.5 text-xs font-semibold rounded-lg transition-colors cursor-pointer flex items-center gap-1.5 ${
                  activeTab === 'candidates'
                    ? 'bg-sky-600 text-white shadow-2xs'
                    : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'
                }`}
              >
                <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M20.25 7.5l-.625 10.632a2.25 2.25 0 01-2.247 2.118H6.622a2.25 2.25 0 01-2.247-2.118L3.75 7.5M10 11.25h4M3.375 7.5h17.25c.621 0 1.125-.504 1.125-1.125v-1.5c0-.621-.504-1.125-1.125-1.125H3.375c-.621 0-1.125.504-1.125 1.125v1.5c0 .621.504 1.125 1.125 1.125z" />
                </svg>
                <span>Retrieved Containers</span>
                <span className="text-[10px] px-1.5 py-0.2 rounded bg-slate-200 text-slate-700">
                  {candidates.length}
                </span>
              </button>

              <button
                type="button"
                onClick={() => setActiveTab('specs')}
                className={`px-3 py-1.5 text-xs font-semibold rounded-lg transition-colors cursor-pointer flex items-center gap-1.5 ${
                  activeTab === 'specs'
                    ? 'bg-sky-600 text-white shadow-2xs'
                    : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'
                }`}
              >
                <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M9 12h3.75M9 15h3.75M9 18h3.75m3 .75H18a2.25 2.25 0 002.25-2.25V6.108c0-1.135-.845-2.098-1.976-2.192a48.424 48.424 0 00-1.123-.08m-5.801 0c-.065.21-.1.433-.1.664 0 .414.336.75.75.75h4.5a.75.75 0 00.75-.75 2.25 2.25 0 00-.1-.664m-5.8 0A2.251 2.251 0 0113.5 2.25H15c1.012 0 1.867.668 2.15 1.586m-5.8 0c-.376.023-.75.05-1.124.08C9.095 4.01 8.25 4.973 8.25 6.108V8.25m0 0H4.875c-.621 0-1.125.504-1.125 1.125v11.25c0 .621.504 1.125 1.125 1.125h9.75c.621 0 1.125-.504 1.125-1.125V9.375c0-.621-.504-1.125-1.125-1.125H8.25zM6.75 12h.008v.008H6.75V12zm0 3h.008v.008H6.75V15zm0 3h.008v.008H6.75V18z" />
                </svg>
                <span>Requirements & Padding</span>
              </button>
            </div>

            {activeContName && (
              <span className="hidden sm:inline-flex items-center gap-1 text-[11px] font-semibold text-sky-800 bg-sky-50 border border-sky-200/80 px-2 py-0.5 rounded-full">
                <span className="w-1.5 h-1.5 rounded-full bg-sky-500" />
                Active View: {activeContName}
              </span>
            )}
          </div>

          {/* TAB 1: 3D Extreme Point Packing Viewer & Metrics */}
          {activeTab === '3d' && (
            <div className="p-4 space-y-4">

              {/* Partial Fit / Weight Violation Warning Banner */}
              {activeEval && !activeEval.fits && (
                <div className="bg-amber-50 border border-amber-200 rounded-xl p-3 flex items-start gap-2.5 text-xs text-amber-900">
                  <span className="text-base leading-none mt-0.5">⚠️</span>
                  <div className="space-y-0.5">
                    <div className="font-bold">
                      Partial Fit in {activeContName}: Placed {activeEval.placed_count} of {activeEval.total_items} items
                    </div>
                    <div className="text-[11px] text-amber-800">
                      {activeEval.unplaced_count} item(s) could not fit inside this container due to dimension limits or extreme point collision.
                      {!activeEval.weight_within_limit && (
                        <span className="ml-1 text-rose-700 font-semibold">
                          (Exceeded max payload capacity of {activeMaxWeight} kg).
                        </span>
                      )}
                    </div>
                  </div>
                </div>
              )}

              {/* Active Container Header Banner */}
              {activeContName && (
                <div className="bg-sky-50 border border-sky-200 rounded-xl p-3 flex flex-wrap items-center justify-between gap-3">
                  <div className="flex items-center gap-2.5">
                    <div className="w-9 h-9 rounded-lg bg-sky-600 text-white flex items-center justify-center font-bold text-base shadow-xs shrink-0">
                      {isWinner ? '🏆' : '📦'}
                    </div>
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-bold text-slate-900">
                          {activeContName}
                        </span>
                        <span className="text-[10px] font-semibold uppercase tracking-wider text-sky-800 bg-sky-100 px-2 py-0.5 rounded-full">
                          {activeCategory}
                        </span>
                        {isWinner && (
                          <span className="text-[10px] font-semibold text-emerald-800 bg-emerald-100 px-2 py-0.5 rounded-full">
                            Recommended Winner
                          </span>
                        )}
                      </div>
                      <div className="text-xs text-slate-600 mt-0.5">
                        Inner:{' '}
                        {activeDims.length}×{activeDims.width}×{activeDims.height} mm • Max Payload:{' '}
                        {activeMaxWeight} kg
                      </div>
                    </div>
                  </div>

                  {activeUtil && (
                    <div className="text-right">
                      <div className="text-xs font-semibold text-slate-500">Item-Volume Utilization</div>
                      <div className="text-lg font-bold text-sky-700">
                        {activeUtil.volume_utilization_pct}%
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* Interactive Three.js 3D Viewer */}
              {hasScene ? (
                <div>
                  {recommendation && (
                    <div className="mb-3 rounded-xl border border-emerald-200 bg-emerald-50 p-3.5">
                      <div className="flex flex-wrap items-center justify-between gap-2">
                        <div className="text-sm font-bold text-emerald-950">
                          {recommendation.model
                            ? 'GPT package recommendation'
                            : 'Model is not configured'}
                        </div>
                        <span className="rounded-full bg-white px-2 py-1 text-[10px] font-semibold text-emerald-800 border border-emerald-200">
                          {recommendation.model || recommendation.status}
                        </span>
                      </div>
                      <p className="mt-1.5 text-xs leading-relaxed text-emerald-900">
                        {recommendation.reasoning}
                      </p>
                      {recommendation.selection_factors.length > 0 && (
                        <div className="mt-2 flex flex-wrap gap-1.5">
                          {recommendation.selection_factors.map((factor) => (
                            <span
                              key={factor}
                              className="rounded-md bg-white/80 px-2 py-1 text-[10px] text-emerald-900 border border-emerald-100"
                            >
                              {factor}
                            </span>
                          ))}
                        </div>
                      )}
                    </div>
                  )}
                  <div className="flex items-center justify-between mb-1.5 px-0.5">
                    <span className="text-xs font-bold text-slate-700 uppercase tracking-wider">
                      Interactive 3D Packing View (Three.js) — {activeContName}
                    </span>
                    <span className="text-[11px] text-slate-500">
                      Left drag: rotate • Scroll: zoom • Right drag: pan
                    </span>
                  </div>
                  <PackingSceneViewer
                    sceneData={activeSceneData}
                    containerName={activeContName}
                    productMeshUrl={productMeshUrl}
                  />
                </div>
              ) : (
                <div className="text-center py-6 text-sm text-slate-500 bg-slate-50 rounded-xl border border-dashed border-slate-200">
                  {result.fits
                    ? 'No 3D scene data was generated for this recommendation.'
                    : 'No package passed the complete 3D fit and weight checks, so there is no recommended package to display.'}
                </div>
              )}

              {/* Packing Analysis Metrics Grid */}
              {activeUtil && (
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5 pt-1">
                  <div className="bg-slate-50 border border-slate-200 rounded-lg p-2.5">
                    <div className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">
                      Placed Items
                    </div>
                    <div className="text-sm font-bold text-slate-900 mt-0.5">
                      {activeUtil.placed_count} / {activeUtil.total_items}
                    </div>
                    <div className={`text-[10px] font-medium mt-0.5 ${activeUtil.placed_count === activeUtil.total_items ? 'text-emerald-600' : 'text-amber-600'}`}>
                      {activeUtil.placed_count === activeUtil.total_items ? '0 Clashes detected' : `${activeUtil.unplaced_count ?? 0} Unplaced`}
                    </div>
                  </div>

                  <div className="bg-slate-50 border border-slate-200 rounded-lg p-2.5">
                    <div className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">
                      Product Volume Occupancy
                    </div>
                    <div className="text-sm font-bold text-sky-700 mt-0.5">
                      {activeUtil.volume_utilization_pct}%
                    </div>
                    <div className="text-[10px] text-slate-500 mt-0.5">
                      {activeUtil.items_volume_liters} L / {activeUtil.container_volume_liters} L
                    </div>
                  </div>

                  <div className="bg-slate-50 border border-slate-200 rounded-lg p-2.5">
                    <div className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">
                      Remaining Container Volume
                    </div>
                    <div className="text-sm font-bold text-slate-800 mt-0.5">
                      {activeUtil.wasted_volume_liters} L
                    </div>
                    <div className="text-[10px] text-slate-500 mt-0.5">
                      Unoccupied by products; not a cushioning measurement
                    </div>
                  </div>

                  <div className="bg-slate-50 border border-slate-200 rounded-lg p-2.5">
                    <div className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">
                      Packed Weight
                    </div>
                    <div className="text-sm font-bold text-slate-900 mt-0.5">
                      {activeUtil.total_packed_weight_kg} kg
                    </div>
                    <div className="text-[10px] text-slate-500 mt-0.5">
                      Payload weight
                    </div>
                  </div>
                </div>
              )}

              {/* Row 2: Maximum Container Utilisation Grid */}
              {activeUtil?.max_utilization && (
                <div className="space-y-1.5 pt-1">
                  <div className="flex items-center justify-between px-0.5">
                    <span className="text-[11px] font-bold text-slate-700 uppercase tracking-wider flex items-center gap-1.5">
                      <span className="w-1.5 h-1.5 rounded-full bg-indigo-500" />
                      Maximum Container Utilisation (Full Capacity)
                    </span>
                    <span className="text-[10px] text-slate-400">
                      Density & full load metrics
                    </span>
                  </div>

                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5">
                    <div className="bg-indigo-50/40 border border-indigo-100 rounded-lg p-2.5">
                      <div className="text-[10px] font-semibold uppercase tracking-wider text-indigo-700">
                        Max Part Capacity
                      </div>
                      <div className="text-sm font-bold text-indigo-950 mt-0.5">
                        {activeUtil.max_utilization.max_parts} units
                      </div>
                      <div className="text-[10px] font-medium text-indigo-600 mt-0.5">
                        Maximum physical fit
                      </div>
                    </div>

                    <div className="bg-indigo-50/40 border border-indigo-100 rounded-lg p-2.5">
                      <div className="text-[10px] font-semibold uppercase tracking-wider text-indigo-700">
                        Max Volume Occupancy
                      </div>
                      <div className="text-sm font-bold text-indigo-950 mt-0.5">
                        {activeUtil.max_utilization.max_volume_utilization_pct}%
                      </div>
                      <div className="text-[10px] text-indigo-600 mt-0.5">
                        {activeUtil.max_utilization.max_items_volume_liters} L / {activeUtil.max_utilization.container_volume_liters || activeUtil.container_volume_liters} L
                      </div>
                    </div>

                    <div className="bg-indigo-50/40 border border-indigo-100 rounded-lg p-2.5">
                      <div className="text-[10px] font-semibold uppercase tracking-wider text-indigo-700">
                        Remaining Volume at Max
                      </div>
                      <div className="text-sm font-bold text-indigo-950 mt-0.5">
                        {activeUtil.max_utilization.max_wasted_volume_liters} L
                      </div>
                      <div className="text-[10px] text-indigo-600 mt-0.5">
                        Unoccupied at max density
                      </div>
                    </div>

                    <div className="bg-indigo-50/40 border border-indigo-100 rounded-lg p-2.5">
                      <div className="text-[10px] font-semibold uppercase tracking-wider text-indigo-700">
                        Max Packed Weight
                      </div>
                      <div className="text-sm font-bold text-indigo-950 mt-0.5">
                        {activeUtil.max_utilization.max_packed_weight_kg} kg
                      </div>
                      <div className={`text-[10px] font-medium mt-0.5 ${activeUtil.max_utilization.weight_within_limit ? 'text-emerald-600' : 'text-amber-700'}`}>
                        {activeUtil.max_utilization.weight_within_limit ? 'Within payload limit' : `Payload limit: ${activeUtil.max_utilization.max_weight_capacity_kg || activeMaxWeight} kg`}
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {/* Placed Parts Manifest & All Orientations Breakdown */}
              <PlacedPartsManifest
                placedItems={activePlacedItems}
                sceneItems={activeSceneData?.items}
                orientationsBreakdown={activeOrientationsBreakdown}
                bestOrientation={activeBestOrientation}
              />
            </div>
          )}

          {/* TAB 2: Retrieved Candidates from Database */}
          {activeTab === 'candidates' && (
            <div className="p-4 space-y-3">
              <div className="text-xs text-slate-600 mb-1">
                Compared dataset package dimensions and rated payloads across {candidates.length} candidate
                container(s). Package construction, protection ratings, and stock counts are not specified
                in the source dataset.
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
                {candidates.map((cand, idx) => {
                  const candidateId = cand.package_code || cand.package_id || cand.name
                  const isWinner = candidateId === bestCont?.candidate_id || cand.name === bestCont?.name

                  return (
                    <div
                      key={cand.name || idx}
                      className={`rounded-xl border p-3 transition-all ${
                        isWinner
                          ? 'border-sky-500 bg-sky-50/50 ring-1 ring-sky-400'
                          : 'border-slate-200 bg-white hover:border-slate-300'
                      }`}
                    >
                      <div className="flex items-start justify-between gap-2">
                        <div>
                          <div className="flex items-center gap-1.5">
                            <span className="text-xs font-bold text-slate-900">
                              {cand.name}
                            </span>
                            {isWinner && (
                              <span className="text-[10px] font-bold text-emerald-700 bg-emerald-100 px-1.5 py-0.2 rounded-full">
                                Winner
                              </span>
                            )}
                          </div>
                          <div className="text-[11px] text-slate-500 capitalize">
                            Category: {cand.category}
                          </div>
                        </div>

                        {cand.tier_label && (
                          <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full bg-slate-100 text-slate-700 shrink-0">
                            {cand.tier_label}
                          </span>
                        )}
                      </div>

                      <div className="mt-2 pt-2 border-t border-slate-100 text-xs space-y-1">
                        <div className="flex justify-between text-slate-600">
                          <span>Inner Dimensions:</span>
                          <span className="font-mono text-slate-900">
                            {(cand.inner_dimensions_mm || cand.dimensions)?.length ?? '—'}×
                            {(cand.inner_dimensions_mm || cand.dimensions)?.width ?? '—'}×
                            {(cand.inner_dimensions_mm || cand.dimensions)?.height ?? '—'} mm
                          </span>
                        </div>
                        <div className="flex justify-between text-slate-600">
                          <span>Max Weight Capacity:</span>
                          <span className="text-slate-900">
                            {cand.max_weight_capacity_kg} kg
                          </span>
                        </div>
                        {cand.volume_utilization_pct !== undefined && (
                          <div className="flex justify-between text-slate-600">
                            <span>Item-volume utilization:</span>
                            <span className="font-bold text-sky-700">
                              {cand.volume_utilization_pct}%
                            </span>
                          </div>
                        )}
                        {cand.padded_bbox_utilization_pct !== undefined && (
                          <div className="flex justify-between text-slate-600">
                            <span>Padded-bounds estimate:</span>
                            <span className="font-mono text-slate-700">
                              {cand.padded_bbox_utilization_pct}%
                            </span>
                          </div>
                        )}
                      </div>

                      {/* Action Button: Perform / View 3D Extreme Point Packing */}
                      <button
                        type="button"
                        onClick={() => {
                          setSelectedContainerName(cand.name)
                          setActiveTab('3d')
                        }}
                        className="w-full mt-2.5 text-xs font-semibold py-1.5 px-3 rounded-lg border border-sky-300 bg-sky-50/80 text-sky-800 hover:bg-sky-100 hover:border-sky-400 transition-colors flex items-center justify-center gap-1.5 cursor-pointer shadow-2xs"
                      >
                        <span>View 3D Extreme Point Packing</span>
                        <span aria-hidden="true">→</span>
                      </button>
                    </div>
                  )
                })}
              </div>
            </div>
          )}

          {/* TAB 3: Extracted Requirements & Cushioning Specifications */}
          {activeTab === 'specs' && (
            <div className="p-4 space-y-3">
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-2.5">
                <div className="bg-slate-50 border border-slate-200 rounded-lg p-2.5">
                  <div className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">
                    Part Name
                  </div>
                  <div className="text-xs font-bold text-slate-900 mt-1 truncate">
                    {partName}
                  </div>
                </div>

                <div className="bg-slate-50 border border-slate-200 rounded-lg p-2.5">
                  <div className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">
                    Single Dimensions
                  </div>
                  <div className="text-xs font-bold text-slate-900 mt-1 font-mono">
                    {req.part_length || metrics.part_dimensions_mm?.length || '—'} ×{' '}
                    {req.part_width || metrics.part_dimensions_mm?.width || '—'} ×{' '}
                    {req.part_height || metrics.part_dimensions_mm?.height || '—'} mm
                  </div>
                </div>

                <div className="bg-slate-50 border border-slate-200 rounded-lg p-2.5">
                  <div className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">
                    SNP (Pack Quantity)
                  </div>
                  <div className="text-xs font-bold text-sky-700 mt-1">
                    {snp} units
                  </div>
                </div>

                <div className="bg-slate-50 border border-slate-200 rounded-lg p-2.5">
                  <div className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">
                    Unit Weight / Total
                  </div>
                  <div className="text-xs font-bold text-slate-900 mt-1">
                    {req.part_weight || metrics.single_item_weight_kg || '—'} kg /{' '}
                    {metrics.total_payload_weight_kg || '—'} kg
                  </div>
                </div>

                <div className="bg-slate-50 border border-slate-200 rounded-lg p-2.5">
                  <div className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">
                    Padding Material
                  </div>
                  <div className="text-xs font-bold text-slate-900 mt-1">
                    {foamMaterial}
                  </div>
                </div>

                <div className="bg-slate-50 border border-slate-200 rounded-lg p-2.5">
                  <div className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">
                    Padding Thickness
                  </div>
                  <div className="text-xs font-bold text-slate-900 mt-1">
                    {foamThickness} mm clearance
                  </div>
                </div>
              </div>

              {metrics.effective_bounding_box_mm && (
                <div className="mt-3 p-3 bg-slate-50 border border-slate-200 rounded-xl text-xs space-y-1">
                  <div className="font-semibold text-slate-800">
                    Effective Multi-Unit Bounding Box (Including Cushioning):
                  </div>
                  <div className="font-mono text-slate-700">
                    {metrics.effective_bounding_box_mm.length} mm (L) ×{' '}
                    {metrics.effective_bounding_box_mm.width} mm (W) ×{' '}
                    {metrics.effective_bounding_box_mm.height} mm (H)
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
