// Product record from SQLite database (table: products / prodcuts)
export interface Product {
  id?: number;
  part_name: string;
  part_length: number;
  part_breadth: number;
  part_height: number;
  part_weight: number;
  part_type: string;
  standard_no_of_parts: number;
  domestic_or_international: 'Domestic' | 'International' | string;
  per_day_requirement: number;
  minimum_order_quantity: number;
  line_feeding_method: string;
  created_at?: string;
}

export interface ProductsResponse {
  products: Product[];
  total: number;
  source: 'sqlite' | 'csv';
}

// Packaging Material specification
export interface PackagingMaterial {
  id: string;
  name: string;
  wall_thickness_mm: number;
  max_weight_kg: number;
  density_kg_m3: number;
  burst_strength_kpa: number;
  cost_per_sqm: number;
}

// Padding rule specification
export interface PaddingRule {
  part_type: string;
  recommended_padding: string;
  thickness_mm: number;
  min_clearance_mm: number;
  fragility: 'low' | 'medium' | 'high' | string;
}

// Custom Box calculation request and response
export interface CustomBoxCalculationRequest {
  part_length: number;
  part_width: number;
  part_height: number;
  part_weight: number;
  part_type?: string;
  quantity?: number;
  material_id?: string;
  custom_padding_thickness_mm?: number;
}

export interface Dimensions3D {
  length: number;
  width: number;
  height: number;
}

export interface BoxSizingResult {
  internal_dimensions_mm: Dimensions3D;
  external_dimensions_mm: Dimensions3D;
  volumes_liters: {
    content: number;
    internal: number;
    external: number;
  };
  surface_area_sqm: number;
  weights_kg: {
    content: number;
    tare_box: number;
    padding: number;
    gross: number;
    volumetric: number;
  };
  estimated_material_cost: number;
}

export interface ConstraintsValidationResult {
  valid: boolean;
  violations: string[];
  warnings: string[];
  metrics: {
    longest_edge_mm: number;
    length_plus_girth_mm: number;
    gross_weight_kg: number;
    material_capacity_utilization_pct: number;
  };
}

export interface MultiUnitArrangement {
  quantity: number;
  grid: { nx: number; ny: number; nz: number };
  content_dimensions_mm: Dimensions3D;
  total_part_weight_kg: number;
  divider_thickness_mm: number;
  alternative_layouts_count: number;
}

export interface CustomBoxCalculationResponse {
  part_specification: {
    dimensions_mm: Dimensions3D;
    weight_kg: number;
    type: string;
    quantity: number;
  };
  multi_unit_arrangement: MultiUnitArrangement;
  padding: {
    applied_thickness_mm: number;
    recommended_material: string;
    fragility: string;
  };
  material: PackagingMaterial;
  box_sizing: BoxSizingResult;
  constraints_validation: ConstraintsValidationResult;
}

// 3D Packing Optimization interfaces
export interface PackingItemInput {
  id?: string;
  length: number;
  width: number;
  height: number;
  weight?: number;
  allow_rotation?: boolean;
  keep_upright?: boolean;
}

export interface PlacedItem {
  item_id: string;
  position: { x: number; y: number; z: number };
  dimensions: Dimensions3D;
  weight_kg: number;
}

export interface Scene3DItem {
  id: string;
  color: string;
  position: { x: number; y: number; z: number };
  dimensions: Dimensions3D;
  weight_kg: number;
}

export interface Scene3DData {
  container: {
    dimensions: Dimensions3D & { volume_liters?: number };
    center: { x: number; y: number; z: number };
  };
  items: Scene3DItem[];
  metrics: {
    volume_utilization_pct: number;
    placed_count: number;
  };
}

export interface PackingResult {
  container_dimensions: Dimensions3D & { volume_liters: number };
  placed_count: number;
  unplaced_count: number;
  total_items: number;
  volume_utilization_pct: number;
  total_packed_weight_kg: number;
  placed_items: PlacedItem[];
  unplaced_items: Array<{
    item_id: string;
    dimensions: Dimensions3D;
    weight_kg: number;
    reason: string;
  }>;
}

export interface PackResponse {
  packing_result: PackingResult;
  scene_3d: Scene3DData;
}

