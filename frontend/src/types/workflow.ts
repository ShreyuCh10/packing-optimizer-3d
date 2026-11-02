export interface PartRequirements {
  name?: string
  part_length?: number
  part_width?: number
  part_height?: number
  part_weight?: number
  snp?: number | string
  part_type?: string
  fragility?: string
  nested?: boolean
  product_id?: number | string
  matched_product_id?: number | string
  cad_model_path?: string
  description?: string
  [key: string]: any
}

export interface RetrievalMetrics {
  part_name?: string
  snp?: number
  part_dimensions_mm?: { length: number; width: number; height: number }
  single_item_volume_cm3?: number
  total_items_volume_cm3?: number
  single_item_weight_kg?: number
  total_payload_weight_kg?: number
  effective_bounding_box_mm?: { length: number; width: number; height: number }
  recommended_padding_material?: string
  recommended_padding_thickness_mm?: number
  requires_heavy_duty?: boolean
}

export interface CandidatePackage {
  package_id?: number | string
  package_code?: string
  candidate_id?: string
  name: string
  category: string
  tier_label?: string
  inner_dimensions_mm?: { length: number; width: number; height: number }
  outer_dimensions_mm?: { length: number; width: number; height: number }
  dimensions?: { length: number; width: number; height: number; volume_liters?: number }
  max_weight_capacity_kg: number
  tare_weight_kg?: number
  material?: string | null
  volume_utilization_pct?: number
  padded_bbox_utilization_pct?: number
  fits_multi_unit_bounding_box?: boolean
  description?: string
  inventory?: number | null
}

export interface PackageRecommendation {
  status: string
  model?: string | null
  selected_candidate_id: string
  assistant_response: string
  reasoning: string
  selection_factors: string[]
}

export interface UtilizationMetrics {
  total_items: number
  placed_count: number
  unplaced_count: number
  container_volume_liters: number
  items_volume_liters: number
  volume_utilization_pct: number
  wasted_volume_liters: number
  total_packed_weight_kg: number
  bounding_box_utilization_pct?: number
  packing_density_kg_per_m3?: number
}

export interface PlacedItem {
  item_id?: string
  item_name?: string
  item_index?: number
  position?: { x: number; y: number; z: number }
  dimensions?: { length: number; width: number; height: number }
  weight_kg?: number
  x?: number
  y?: number
  z?: number
  dx?: number
  dy?: number
  dz?: number
}

export interface SceneItem {
  id: string
  color: string
  position: { x: number; y: number; z: number }
  dimensions: { length: number; width: number; height: number }
  weight_kg?: number
}

export interface SceneData {
  container?: {
    dimensions: {
      length: number
      width: number
      height: number
      volume_liters?: number
    }
    center?: { x: number; y: number; z: number }
  }
  items?: SceneItem[]
  metrics?: {
    volume_utilization_pct?: number
    placed_count?: number
  }
}

export interface BestOrientation {
  length: number
  width: number
  height: number
  count_at_this_orientation: number
}

export interface ToolExecutionStep {
  id: string
  tool_name: string
  category: 'requirement' | 'retrieval' | 'optimization' | string
  summary: string
  status: 'success' | 'warning' | 'error' | string
  method?: string
  execution_status?: string
  confidence?: number
  confidence_threshold?: number
  inputs?: Record<string, any>
  outputs?: Record<string, any>
}

export interface WorkflowResult {
  status: string
  stage: 'requirement_gathering' | 'hitl' | 'retrieval_gathering' | 'packing_optimization' | string
  summary: string
  hitl_required: boolean
  hitl_reason?: string | null
  requirements?: PartRequirements
  metrics?: RetrievalMetrics
  candidate_packages?: CandidatePackage[]
  fits: boolean
  best_container?: CandidatePackage | null
  ai_recommendation?: PackageRecommendation | null
  assistant_response?: string
  closest_candidate?: CandidatePackage | null
  best_orientation?: BestOrientation | null
  utilization_metrics?: UtilizationMetrics | null
  placed_items?: PlacedItem[]
  unplaced_items?: any[]
  scene_data?: SceneData
  steps?: ToolExecutionStep[]
}

export interface ChatMessage {
  id: string
  sender: 'user' | 'assistant'
  text: string
  timestamp?: string
  workflowResult?: WorkflowResult
  isError?: boolean
}
