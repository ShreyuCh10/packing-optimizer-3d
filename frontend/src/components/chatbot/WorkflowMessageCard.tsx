import { useState } from 'react'
import type { WorkflowResult } from '../../types/workflow'
import WorkflowStepProgress from './WorkflowStepProgress'
import PackingSceneViewer from './PackingSceneViewer'
import ToolExecutionTrace from './ToolExecutionTrace'
import PlacedPartsManifest from './PlacedPartsManifest'

interface WorkflowMessageCardProps {
  result: WorkflowResult
  onApplyPrompt?: (promptText: string) => void
}

export default function WorkflowMessageCard({
  result,
  onApplyPrompt,
}: WorkflowMessageCardProps) {
  const [activeTab, setActiveTab] = useState<'3d' | 'candidates' | 'specs'>('3d')
  const [selectedContainerName, setSelectedContainerName] = useState<string | null>(null)

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
      }
    : util

  const activePlacedItems = activeEval?.placed_items || result.placed_items
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

  return (
    <div className="w-full space-y-3.5">
      {/* 1. Multi-Agent Step Progress Pipeline */}
      <WorkflowStepProgress
        currentStage={result.stage}
        status={result.status}
        hitlRequired={isHitl}
      />

      {/* 2. Executive Summary / Conversational Narrative */}
      <div className="text-sm text-slate-800 leading-relaxed bg-white border border-slate-200/90 rounded-xl p-3.5 shadow-2xs">
        <div className="flex items-start gap-2.5">
          <div className="w-6 h-6 rounded-full bg-sky-100 text-sky-700 flex items-center justify-center shrink-0 mt-0.5 font-bold text-xs">
            🤖
          </div>
          <div className="flex-1 whitespace-pre-wrap">
            {result.assistant_response || result.summary || 'Unified packaging workflow executed.'}
          </div>
        </div>
      </div>

      {/* 3. Human-In-The-Loop Clarification Banner (if HITL required) */}
      {isHitl && (
        <div className="bg-amber-50 border border-amber-200 rounded-xl p-4 shadow-2xs">
          <div className="flex items-start gap-3">
            <div className="w-7 h-7 rounded-lg bg-amber-500 text-white flex items-center justify-center shrink-0 font-bold text-sm shadow-xs">
              !
            </div>
            <div className="flex-1">
              <h4 className="text-sm font-semibold text-amber-900">
                Action Required: Incomplete Part Specifications
              </h4>
              <p className="text-xs text-amber-800 mt-1 leading-relaxed">
                {result.hitl_reason ||
                  'The Requirement Gathering Agent requires additional physical details to query the database and pack.'}
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

      {/* 3.5 Major Heading: Granular Agent Tool Use Trace */}
      <ToolExecutionTrace steps={result.steps} />

      {/* 4. Multi-Agent Process Results (Only shown when not blocked by HITL) */}
      {!isHitl && (
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
              {/* Target Box Selector Pill Buttons */}
              {allEvals.length > 1 && (
                <div className="bg-slate-50 border border-slate-200 rounded-xl p-2.5 space-y-1.5">
                  <div className="flex items-center justify-between text-[11px] text-slate-600 font-semibold uppercase tracking-wider">
                    <span>Extreme Point Target Box (Switch 3D View):</span>
                    <span className="text-[10px] text-slate-400 font-normal lowercase">
                      {allEvals.length} evaluated containers
                    </span>
                  </div>

                  <div className="flex flex-wrap gap-1.5">
                    {allEvals.map((ev) => {
                      const isSelected = ev.container_name === activeContName
                      const isOptWinner = ev.container_name === bestCont?.name

                      return (
                        <button
                          key={ev.container_name}
                          type="button"
                          onClick={() => setSelectedContainerName(ev.container_name)}
                          className={`text-xs px-2.5 py-1 rounded-lg font-medium cursor-pointer transition-all flex items-center gap-1.5 border ${
                            isSelected
                              ? 'bg-sky-600 text-white border-sky-600 shadow-xs ring-2 ring-sky-200'
                              : 'bg-white text-slate-700 border-slate-200 hover:bg-slate-100 hover:border-slate-300'
                          }`}
                        >
                          {isOptWinner && <span title="Recommended Winner">🏆</span>}
                          <span>{ev.container_name}</span>
                          <span
                            className={`text-[10px] font-semibold px-1.5 py-0.2 rounded-full ${
                              isSelected
                                ? 'bg-sky-700 text-sky-100'
                                : ev.fits
                                ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                                : 'bg-amber-50 text-amber-700 border border-amber-200'
                            }`}
                          >
                            {ev.fits ? `${ev.volume_utilization_pct}%` : `${ev.placed_count}/${ev.total_items} fit`}
                          </span>
                        </button>
                      )
                    })}
                  </div>
                </div>
              )}

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
                            : 'Package recommendation (deterministic fallback)'}
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
