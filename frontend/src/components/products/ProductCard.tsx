import type { Product } from '../../types/customBox'

interface ProductCardProps {
  product: Product
  onClick: (product: Product) => void
}

export default function ProductCard({ product, onClick }: ProductCardProps) {
  return (
    <div
      onClick={() => onClick(product)}
      className="bg-white border border-slate-200 rounded-lg overflow-hidden hover:border-slate-400 hover:shadow-xs transition cursor-pointer flex flex-col group text-left"
    >
      {/* 3D Model / Image Placeholder Area */}
      <div className="relative h-44 bg-slate-100 border-b border-slate-200 flex flex-col items-center justify-center text-slate-400 p-4 select-none group-hover:bg-slate-200/60 transition-colors">
        {/* Placeholder Icon */}
        <svg
          className="w-10 h-10 mb-2 stroke-slate-400"
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
        <span className="text-xs font-medium text-slate-500">
          Image not available
        </span>

        {/* Part Type Badge */}
        <span className="absolute top-2.5 right-2.5 text-[11px] font-medium px-2 py-0.5 rounded bg-white border border-slate-200 text-slate-600 shadow-2xs capitalize">
          {product.part_type}
        </span>
      </div>

      {/* Card Content */}
      <div className="p-4 flex-1 flex flex-col justify-between">
        <div>
          {/* Part Name */}
          <h3
            className="text-base font-semibold text-slate-900 line-clamp-1 group-hover:text-blue-600 transition-colors"
            title={product.part_name}
          >
            {product.part_name}
          </h3>

          {/* Standard Number of Parts (SNP) */}
          <div className="mt-2 flex items-center justify-between text-sm">
            <span className="text-slate-500 font-normal">SNP:</span>
            <span className="font-semibold text-slate-800 bg-slate-100 px-2 py-0.5 rounded text-xs">
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

