export interface CartItem {
  id: number
  product_id?: number | null
  part_name: string
  part_type: string
  part_length: number
  part_breadth: number
  part_height: number
  part_weight: number
  number_of_parts: number
  model_file?: string | null
  product_snp?: number | null
  line_weight_kg: number
  unit_volume_liters: number
  total_volume_liters: number
  created_at?: string
  updated_at?: string
}

export interface CartSummary {
  items: CartItem[]
  total_items: number
  total_parts: number
  total_weight_kg: number
  total_volume_liters: number
}

export interface AddToCartPayload {
  product_id?: number | null
  part_name?: string
  number_of_parts: number
  part_type?: string
  part_length?: number
  part_breadth?: number
  part_height?: number
  part_weight?: number
  mode?: 'increment' | 'set'
}

