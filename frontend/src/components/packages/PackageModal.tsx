import { useEffect } from 'react'
import type { PackagingItem } from '../../types/packages'
import { getPackageBadgeStyle } from '../../utils/materialBadges'
import ProductMeshViewer from '../products/ProductMeshViewer'

interface PackageModalProps {
  pkg: PackagingItem | null
  onClose: () => void
}

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000/api'

export default function PackageModal({ pkg, onClose }: PackageModalProps) {
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onClose()
      }
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [onClose])

  if (!pkg) return null

  const badgeStyle = getPackageBadgeStyle(pkg.category)
  const isCarton = pkg.category === 'carton'

  // Outer volume in liters
  const outerVolumeLiters = (
    (pkg.outer_length_mm * pkg.outer_width_mm * pkg.outer_height_mm) /
    1000000
  ).toFixed(2)

  // Inner volume in liters
  const innerVolumeLiters =
    pkg.inner_length_mm && pkg.inner_width_mm && pkg.inner_height_mm
      ? (
          (pkg.inner_length_mm * pkg.inner_width_mm * pkg.inner_height_mm) /
          1000000
        ).toFixed(2)
      : outerVolumeLiters

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
        aria-labelledby="modal-package-title"
        className="relative bg-white rounded-xl shadow-2xl max-w-2xl w-full max-h-[90vh] overflow-y-auto border border-slate-200 z-10 flex flex-col"
      >
        {/* Header */}
        <div className="px-6 py-4 border-b border-slate-200 flex items-center justify-between sticky top-0 bg-white z-20">
          <div>
            <div className="flex items-center gap-2">
              <span
                className={`text-xs font-semibold px-2.5 py-0.5 rounded border capitalize ${badgeStyle.bg} ${badgeStyle.text} ${badgeStyle.border}`}
              >
                {pkg.category_label}
              </span>
              <span className="text-xs font-semibold px-2 py-0.5 rounded bg-sky-600 text-white shadow-2xs">
                3D Container Model
              </span>
              {pkg.id && (
                <span className="text-xs text-slate-400">ID #{pkg.id}</span>
              )}
            </div>
            <h2
              id="modal-package-title"
              className="text-xl font-bold text-slate-900 mt-1"
            >
              {pkg.package}
            </h2>
          </div>

          <button
            type="button"
            onClick={onClose}
            aria-label="Close details"
            className="p-2 rounded-md text-slate-400 hover:text-slate-700 hover:bg-slate-100 transition cursor-pointer"
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

        {/* Modal Body */}
        <div className="p-6 space-y-6">
          {/* Interactive 3D Mesh Viewer */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-slate-700 uppercase tracking-wider flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
                Live 3D Box Mesh Viewer
              </span>

              <span className="text-xs font-medium text-slate-500 font-mono">
                {pkg.outer_length_mm} &times; {pkg.outer_width_mm} &times; {pkg.outer_height_mm} mm
              </span>
            </div>

            <ProductMeshViewer
              meshUrl={`${API_BASE}/packages/${encodeURIComponent(pkg.package)}/mesh`}
              height="h-64 sm:h-72"
            />
          </div>

          {/* Key Metric Highlights */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-center">
            <div className="bg-sky-50/50 border border-sky-100 rounded-lg p-3">
              <span className="text-xs text-slate-500 block mb-1">Usable Volume</span>
              <span className="text-lg font-bold text-sky-900">{innerVolumeLiters}</span>
              <span className="text-xs text-sky-600 block">liters</span>
            </div>

            <div className="bg-slate-50 border border-slate-200 rounded-lg p-3">
              <span className="text-xs text-slate-500 block mb-1">Tare / Empty</span>
              <span className="text-lg font-bold text-slate-900">{pkg.empty_weight_kg}</span>
              <span className="text-xs text-slate-400 block">kg</span>
            </div>

            <div className="bg-sky-50/50 border border-sky-100 rounded-lg p-3">
              <span className="text-xs text-slate-500 block mb-1">
                {isCarton ? 'Max Part Weight' : 'Load Rating'}
              </span>
              <span className="text-lg font-bold text-sky-900">
                {pkg.part_weight_kg ?? pkg.total_weight_kg ?? '—'}
              </span>
              <span className="text-xs text-sky-600 block">kg</span>
            </div>

            <div className="bg-slate-50 border border-slate-200 rounded-lg p-3">
              <span className="text-xs text-slate-500 block mb-1">Pallet Units</span>
              <span className="text-lg font-bold text-slate-900">
                {pkg.bins_per_pallet ?? '1'}
              </span>
              <span className="text-xs text-slate-400 block">
                {pkg.layers_per_pallet ? `${pkg.layers_per_pallet} layers` : 'unit'}
              </span>
            </div>
          </div>

          {/* Full Specifications Table */}
          <div className="border border-slate-200 rounded-lg overflow-hidden">
            <div className="bg-slate-50 px-4 py-2.5 border-b border-slate-200 text-xs font-semibold text-slate-700 uppercase tracking-wider">
              Package Specifications
            </div>
            <dl className="divide-y divide-slate-200 text-sm">
              <div className="px-4 py-3 sm:grid sm:grid-cols-3 sm:gap-4">
                <dt className="text-slate-500 font-medium">Outer Dimensions</dt>
                <dd className="mt-1 sm:mt-0 sm:col-span-2 text-slate-900 font-mono">
                  {pkg.outer_length_mm} &times; {pkg.outer_width_mm} &times; {pkg.outer_height_mm} mm
                </dd>
              </div>

              {pkg.inner_length_mm && (
                <div className="px-4 py-3 sm:grid sm:grid-cols-3 sm:gap-4">
                  <dt className="text-slate-500 font-medium">Inner Dimensions (Usable)</dt>
                  <dd className="mt-1 sm:mt-0 sm:col-span-2 text-slate-900 font-mono">
                    {pkg.inner_length_mm} &times; {pkg.inner_width_mm} &times; {pkg.inner_height_mm} mm
                  </dd>
                </div>
              )}

              <div className="px-4 py-3 sm:grid sm:grid-cols-3 sm:gap-4">
                <dt className="text-slate-500 font-medium">Packaging Category</dt>
                <dd className="mt-1 sm:mt-0 sm:col-span-2 text-slate-900">
                  <span
                    className={`inline-block px-2 py-0.5 rounded text-xs font-medium border ${badgeStyle.bg} ${badgeStyle.text} ${badgeStyle.border}`}
                  >
                    {pkg.category_label}
                  </span>
                </dd>
              </div>

              {pkg.pallet_length_mm && (
                <div className="px-4 py-3 sm:grid sm:grid-cols-3 sm:gap-4">
                  <dt className="text-slate-500 font-medium">Pallet Footprint</dt>
                  <dd className="mt-1 sm:mt-0 sm:col-span-2 text-slate-900 font-mono">
                    {pkg.pallet_length_mm} &times; {pkg.pallet_width_mm} &times; {pkg.pallet_height_mm} mm
                  </dd>
                </div>
              )}

              {pkg.bins_per_row != null && pkg.bins_per_column != null && (
                <div className="px-4 py-3 sm:grid sm:grid-cols-3 sm:gap-4">
                  <dt className="text-slate-500 font-medium">Pallet Grid Stacking</dt>
                  <dd className="mt-1 sm:mt-0 sm:col-span-2 text-slate-900">
                    {pkg.bins_per_row} bins/row &times; {pkg.bins_per_column} bins/col ({pkg.layers_per_pallet} layers) &rarr;{' '}
                    <strong className="text-sky-900 font-semibold">{pkg.bins_per_pallet} total units</strong>
                  </dd>
                </div>
              )}

              {pkg.stack_height_mm != null && (
                <div className="px-4 py-3 sm:grid sm:grid-cols-3 sm:gap-4">
                  <dt className="text-slate-500 font-medium">Full Stack Height</dt>
                  <dd className="mt-1 sm:mt-0 sm:col-span-2 text-slate-900 font-mono">
                    {pkg.stack_height_mm} mm
                  </dd>
                </div>
              )}

              {pkg.pallet_load_weight_kg != null && (
                <div className="px-4 py-3 sm:grid sm:grid-cols-3 sm:gap-4">
                  <dt className="text-slate-500 font-medium">Total Pallet Load Weight</dt>
                  <dd className="mt-1 sm:mt-0 sm:col-span-2 text-slate-900 font-semibold text-sky-900">
                    {pkg.pallet_load_weight_kg} kg
                  </dd>
                </div>
              )}

              <div className="px-4 py-3 sm:grid sm:grid-cols-3 sm:gap-4">
                <dt className="text-slate-500 font-medium">Inventory Status</dt>
                <dd className="mt-1 sm:mt-0 sm:col-span-2 text-emerald-700 font-medium flex items-center gap-2">
                  <span className="w-2 h-2 rounded-full bg-emerald-500" />
                  {pkg.inventory ?? 25} units available in warehouse
                </dd>
              </div>
            </dl>
          </div>
        </div>

        {/* Modal Footer */}
        <div className="px-6 py-4 bg-slate-50 border-t border-slate-200 flex items-center justify-between sticky bottom-0 z-20">
          <div className="text-xs text-slate-500 font-mono">
            Table: {pkg.category === 'carton' ? 'packages' : `${pkg.category}s`}
          </div>
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 bg-white border border-slate-300 text-slate-700 hover:bg-slate-100 rounded-md text-xs font-semibold active:scale-[0.98] transition cursor-pointer shadow-2xs"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  )
}

