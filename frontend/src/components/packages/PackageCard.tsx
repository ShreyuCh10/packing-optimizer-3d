import type { PackagingItem } from '../../types/packages'
import { getPackageBadgeStyle } from '../../utils/materialBadges'

interface PackageCardProps {
  pkg: PackagingItem
  onClick: (pkg: PackagingItem) => void
}

export default function PackageCard({ pkg, onClick }: PackageCardProps) {
  const badgeStyle = getPackageBadgeStyle(pkg.category)
  const isCarton = pkg.category === 'carton'

  return (
    <div
      onClick={() => onClick(pkg)}
      className="bg-white border border-slate-200 rounded-lg overflow-hidden hover:border-sky-300 hover:shadow-md hover:-translate-y-0.5 transition-all duration-200 cursor-pointer flex flex-col group text-left"
    >
      {/* 3D Model / Package Area - Light Blue-Tinted Background */}
      <div className="relative h-44 bg-sky-50/65 border-b border-sky-100/80 flex flex-col items-center justify-center text-sky-600/75 p-4 select-none group-hover:bg-sky-100/60 transition-colors duration-200">
        {/* Isometric Box / Package SVG Icon */}
        <svg
          className="w-10 h-10 mb-2 stroke-sky-600 group-hover:stroke-sky-700 transition-colors"
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

        <div className="text-center">
          <span className="text-xs font-semibold text-sky-800 block">
            {pkg.package}
          </span>
          <span className="text-[11px] font-mono text-sky-600 mt-0.5 block">
            {pkg.outer_length_mm} &times; {pkg.outer_width_mm} &times; {pkg.outer_height_mm} mm
          </span>
        </div>

        {/* 3D Container Badge (Top Left) */}
        <span className="absolute top-2.5 left-2.5 text-[10px] font-semibold px-2 py-0.5 rounded bg-sky-600 text-white shadow-2xs">
          3D Box
        </span>

        {/* Category Badge (Top Right) */}
        <span
          className={`absolute top-2.5 right-2.5 text-[11px] font-medium px-2 py-0.5 rounded border shadow-2xs ${badgeStyle.bg} ${badgeStyle.text} ${badgeStyle.border}`}
        >
          {pkg.category_label}
        </span>
      </div>

      {/* Card Body */}
      <div className="p-4 flex-1 flex flex-col justify-between">
        <div>
          {/* Package Name */}
          <h3
            className="text-base font-semibold text-slate-900 line-clamp-1 group-hover:text-sky-700 transition-colors duration-150"
            title={pkg.package}
          >
            {pkg.package}
          </h3>

          {/* Key Packaging Metric */}
          <div className="mt-2.5 flex items-center justify-between text-sm">
            <span className="text-slate-500 font-normal">
              {isCarton ? 'Pallet Load:' : 'Tare Weight:'}
            </span>
            <span className="font-semibold text-sky-900 bg-sky-50 border border-sky-200/70 px-2 py-0.5 rounded text-xs">
              {isCarton && pkg.bins_per_pallet
                ? `${pkg.bins_per_pallet} units / pallet`
                : `${pkg.empty_weight_kg} kg`}
            </span>
          </div>

          {/* Inner usable dimensions if available */}
          {pkg.inner_length_mm && (
            <div className="mt-1.5 flex items-center justify-between text-xs text-slate-500">
              <span className="text-slate-400">Usable (Inner):</span>
              <span className="font-mono text-slate-600">
                {pkg.inner_length_mm} &times; {pkg.inner_width_mm} &times; {pkg.inner_height_mm} mm
              </span>
            </div>
          )}
        </div>

        {/* Bottom Specs & Stock Level */}
        <div className="mt-3 pt-3 border-t border-slate-100 flex items-center justify-between text-xs">
          <span className="text-slate-500">
            {isCarton && pkg.part_weight_kg ? (
              <>Max part: <strong className="text-slate-700 font-medium">{pkg.part_weight_kg} kg</strong></>
            ) : (
              <>Empty: <strong className="text-slate-700 font-medium">{pkg.empty_weight_kg} kg</strong></>
            )}
          </span>

          <span className="inline-flex items-center gap-1.5 font-medium text-emerald-700 bg-emerald-50 border border-emerald-200/70 px-2 py-0.5 rounded text-[11px]">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
            {pkg.inventory ?? 25} in stock
          </span>
        </div>
      </div>
    </div>
  )
}

