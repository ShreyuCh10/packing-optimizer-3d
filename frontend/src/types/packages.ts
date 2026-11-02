export type PackagingCategory =
  | 'all'
  | 'carton'
  | 'base_pallet'
  | 'metal_pallet'
  | 'metal_stillage'

export interface PackagingItem {
  id: number
  package: string
  category: 'carton' | 'base_pallet' | 'metal_pallet' | 'metal_stillage'
  category_label: string
  outer_length_mm: number
  outer_width_mm: number
  outer_height_mm: number
  inner_length_mm?: number | null
  inner_width_mm?: number | null
  inner_height_mm?: number | null
  empty_weight_kg: number
  part_weight_kg?: number | null
  total_weight_kg?: number | null
  pallet_length_mm?: number | null
  pallet_width_mm?: number | null
  pallet_height_mm?: number | null
  bins_per_row?: number | null
  bins_per_column?: number | null
  layers_per_pallet?: number | null
  bins_per_pallet?: number | null
  stack_height_mm?: number | null
  pallet_load_weight_kg?: number | null
  inventory: number
  created_at?: string
}

export interface PackageCounts {
  all: number
  carton: number
  base_pallet: number
  metal_pallet: number
  metal_stillage: number
}

export interface PackageListResponse {
  packages: PackagingItem[]
  total: number
  counts: PackageCounts
  source: string
}

