import { useState } from 'react'
import type { PlacedItem, SceneItem, OrientationBreakdown, BestOrientation } from '../../types/workflow'

interface PlacedPartsManifestProps {
  placedItems?: PlacedItem[]
  sceneItems?: SceneItem[]
  orientationsBreakdown?: OrientationBreakdown[]
  bestOrientation?: BestOrientation | null
}

export default function PlacedPartsManifest({
  placedItems = [],
  sceneItems = [],
  orientationsBreakdown = [],
  bestOrientation,
}: PlacedPartsManifestProps) {
  const [isExpanded, setIsExpanded] = useState(false)
  const [showAllItems, setShowAllItems] = useState(false)

  const totalItems = placedItems.length
  if (totalItems === 0) return null

  // Fallback if orientationsBreakdown not provided
  const breakdowns: OrientationBreakdown[] =
    orientationsBreakdown.length > 0
      ? orientationsBreakdown
      : bestOrientation
      ? [
          {
            dimensions: {
              length: bestOrientation.length,
              width: bestOrientation.width,
              height: bestOrientation.height,
            },
            count: bestOrientation.count_at_this_orientation,
            percentage: Math.round((bestOrientation.count_at_this_orientation / totalItems) * 100),
          },
        ]
      : []

  const isUniform = breakdowns.length <= 1
  const displayedItems = showAllItems ? placedItems : placedItems.slice(0, 8)

  return (
    <div className="bg-slate-50 border border-slate-200 rounded-xl overflow-hidden shadow-2xs space-y-0">
      {/* 1. Orientations Breakdown Header */}
      <div className="p-3 bg-white border-b border-slate-200">
        <div className="flex flex-wrap items-center justify-between gap-2 mb-2">
          <div className="flex items-center gap-1.5">
            <span className="text-xs font-bold text-slate-800 uppercase tracking-wider">
              Part Orientations ({breakdowns.length} Rotation{breakdowns.length > 1 ? 's' : ''} Used)
            </span>
            <span
              className={`text-[10px] font-semibold px-2 py-0.5 rounded-full border ${
                isUniform
                  ? 'bg-emerald-50 text-emerald-800 border-emerald-200'
                  : 'bg-amber-50 text-amber-800 border-amber-200'
              }`}
            >
              {isUniform ? 'Uniform Batch Orientation' : 'Mixed / Multi-Angle Orientations'}
            </span>
          </div>

          <button
            type="button"
            onClick={() => setIsExpanded((prev) => !prev)}
            className="text-xs font-semibold text-sky-700 hover:text-sky-900 transition-colors cursor-pointer flex items-center gap-1"
          >
            <span>{isExpanded ? 'Hide Part Manifest' : `View All ${totalItems} Parts`}</span>
            <svg
              className={`w-3.5 h-3.5 transition-transform duration-200 ${isExpanded ? 'rotate-180' : ''}`}
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
              strokeWidth={2}
            >
              <path strokeLinecap="round" strokeLinejoin="round" d="m19.5 8.25-7.5 7.5-7.5-7.5" />
            </svg>
          </button>
        </div>

        {/* Orientation Badges Grid */}
        <div className="flex flex-wrap gap-2 pt-0.5">
          {breakdowns.map((ob, idx) => (
            <div
              key={idx}
              className="inline-flex items-center gap-2 bg-slate-50 border border-slate-200 px-2.5 py-1.5 rounded-lg text-xs"
            >
              <span className="w-2 h-2 rounded-full bg-sky-500" />
              <span className="font-mono font-bold text-slate-900">
                {ob.dimensions.length} × {ob.dimensions.width} × {ob.dimensions.height} mm
              </span>
              <span className="text-slate-500 font-medium">
                • {ob.count} unit{ob.count > 1 ? 's' : ''} ({ob.percentage}%)
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* 2. Collapsible Detailed Parts Placement Manifest */}
      {isExpanded && (
        <div className="p-3 bg-slate-50/70 border-t border-slate-100 space-y-2">
          <div className="text-[11px] text-slate-500 flex items-center justify-between">
            <span>
              Coordinates $(X, Y, Z)$ represent the front-bottom-left corner of each part inside the container.
            </span>
            <span className="font-medium text-slate-700">{totalItems} Placed Parts</span>
          </div>

          <div className="overflow-x-auto rounded-lg border border-slate-200 bg-white">
            <table className="w-full text-left text-xs text-slate-700 border-collapse">
              <thead>
                <tr className="bg-slate-100 text-[10px] uppercase tracking-wider text-slate-500 border-b border-slate-200">
                  <th className="py-2 px-2.5 font-bold">#</th>
                  <th className="py-2 px-2.5 font-bold">Part ID</th>
                  <th className="py-2 px-2.5 font-bold">Orientation (L × W × H)</th>
                  <th className="py-2 px-2.5 font-bold">3D Position (X, Y, Z mm)</th>
                  <th className="py-2 px-2.5 font-bold text-right">Weight</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 font-mono text-[11px]">
                {displayedItems.map((item, idx) => {
                  const dims = item.dimensions || { length: item.dx ?? 0, width: item.dy ?? 0, height: item.dz ?? 0 }
                  const pos = item.position || { x: item.x ?? 0, y: item.y ?? 0, z: item.z ?? 0 }
                  const color = sceneItems[idx]?.color || '#0284c7'

                  return (
                    <tr key={item.item_id || idx} className="hover:bg-sky-50/40 transition-colors">
                      <td className="py-1.5 px-2.5 flex items-center gap-1.5">
                        <span
                          className="w-2.5 h-2.5 rounded-full shrink-0 shadow-2xs border border-black/10"
                          style={{ backgroundColor: color }}
                          title={`Color in 3D: ${color}`}
                        />
                        <span className="font-sans font-bold text-slate-400">{idx + 1}</span>
                      </td>
                      <td className="py-1.5 px-2.5 font-sans font-medium text-slate-900 truncate max-w-[120px]">
                        {item.item_id || `item_${idx + 1}`}
                      </td>
                      <td className="py-1.5 px-2.5 text-sky-800 font-bold">
                        {dims.length} × {dims.width} × {dims.height} mm
                      </td>
                      <td className="py-1.5 px-2.5 text-slate-600">
                        ({pos.x}, {pos.y}, {pos.z})
                      </td>
                      <td className="py-1.5 px-2.5 text-right font-sans text-slate-700">
                        {item.weight_kg ?? 0} kg
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>

          {/* Toggle for large batches (> 8 items) */}
          {totalItems > 8 && (
            <div className="text-center pt-1">
              <button
                type="button"
                onClick={() => setShowAllItems((prev) => !prev)}
                className="text-xs font-semibold text-sky-700 hover:text-sky-900 px-3 py-1 rounded border border-sky-200 bg-white hover:bg-sky-50 transition-colors cursor-pointer"
              >
                {showAllItems ? 'Show Fewer Items' : `Show All ${totalItems} Parts`}
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

