import type { Product } from '../../types/customBox'
import { getMaterialBadgeStyle } from '../../utils/materialBadges'

interface ProductCardProps {
  product: Product
  onClick: (product: Product) => void
}

export default function ProductCard({ product, onClick }: ProductCardProps) {
  const badgeStyle = getMaterialBadgeStyle(product.part_type)

  return (
    <div
      onClick={() => onClick(product)}
      className="bg-white border border-slate-200 rounded-lg overflow-hidden hover:border-sky-300 hover:shadow-md hover:-translate-y-0.5 transition-all duration-200 cursor-pointer flex flex-col group text-left"
    >
      {/* 3D Model / Image Placeholder Area - Very Light Blue-Tinted Background */}
      <div className="relative h-44 bg-sky-50/65 border-b border-sky-100/80 flex flex-col items-center justify-center text-sky-600/75 p-4 select-none group-hover:bg-sky-100/60 transition-colors duration-200">
        {/* Placeholder Icon */}
        <svg
          className="w-10 h-10 mb-2 stroke-sky-400 group-hover:stroke-sky-500 transition-colors"
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
        <span className="text-xs font-medium text-sky-700/80">
          Image not available
        </span>

        {/* Soft Colored Material Badge */}
        <span
          className={`absolute top-2.5 right-2.5 text-[11px] font-medium px-2 py-0.5 rounded border shadow-2xs capitalize ${badgeStyle.bg} ${badgeStyle.text} ${badgeStyle.border}`}
        >
          {product.part_type}
        </span>
      </div>

      {/* Card Content */}
      <div className="p-4 flex-1 flex flex-col justify-between">
        <div>
          {/* Part Name */}
          <h3
            className="text-base font-semibold text-slate-900 line-clamp-1 group-hover:text-sky-700 transition-colors duration-150"
            title={product.part_name}
          >
            {product.part_name}
          </h3>

          {/* Standard Number of Parts (SNP) */}
          <div className="mt-2.5 flex items-center justify-between text-sm">
            <span className="text-slate-500 font-normal">SNP:</span>
            <span className="font-semibold text-sky-900 bg-sky-50 border border-sky-200/70 px-2 py-0.5 rounded text-xs">
              {product.standard_no_of_parts} units
            </span>
          </div>
        </div>

        {/* Quick Dimensions & Weight summary */}
        <div className="mt-3 pt-3 border-t border-slate-100 flex items-center justify-between text-xs text-slate-500">
          <span>
            {product.part_length} &times; {product.part_breadth} &times; {product.part_height} mm
          </span>
          <span className="font-medium text-slate-700">{product.part_weight} kg</span>
        </div>
      </div>
    </div>
  )
}
