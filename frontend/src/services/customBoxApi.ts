import type {
  Product,
  ProductsResponse,
  PackagingMaterial,
  PaddingRule,
  CustomBoxCalculationRequest,
  CustomBoxCalculationResponse,
  PackingItemInput,
  PackResponse,
} from '../types/customBox';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';

/**
 * Fetch all products from SQLite database (table: products / prodcuts).
 */
export async function getProducts(): Promise<ProductsResponse> {
  const res = await fetch(`${API_BASE}/custom-box/products`);
  if (!res.ok) throw new Error(`Failed to load products: ${res.statusText}`);
  return res.json();
}

/**
 * Fetch a single product by part name.
 */
export async function getProductByName(partName: string): Promise<Product> {
  const res = await fetch(`${API_BASE}/custom-box/products/${encodeURIComponent(partName)}`);
  if (!res.ok) throw new Error(`Product not found: ${res.statusText}`);
  return res.json();
}

/**
 * List available packaging box materials.
 */
export async function getMaterials(): Promise<{ materials: PackagingMaterial[]; total: number }> {
  const res = await fetch(`${API_BASE}/custom-box/materials`);
  if (!res.ok) throw new Error(`Failed to load materials: ${res.statusText}`);
  return res.json();
}

/**
 * List padding and clearance rules.
 */
export async function getPaddingRules(): Promise<{ rules: PaddingRule[]; default_rule: PaddingRule }> {
  const res = await fetch(`${API_BASE}/custom-box/padding-rules`);
  if (!res.ok) throw new Error(`Failed to load padding rules: ${res.statusText}`);
  return res.json();
}

/**
 * Calculate custom box sizing, padding, and constraints.
 */
export async function calculateCustomBox(
  payload: CustomBoxCalculationRequest
): Promise<CustomBoxCalculationResponse> {
  const res = await fetch(`${API_BASE}/custom-box/calculate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error(`Custom box calculation failed: ${res.statusText}`);
  return res.json();
}

/**
 * Pack items into a specific 3D container.
 */
export async function packItems(
  container: { length: number; width: number; height: number; max_weight_kg?: number },
  items: PackingItemInput[],
  options?: { allow_rotation?: boolean; keep_upright?: boolean }
): Promise<PackResponse> {
  const res = await fetch(`${API_BASE}/packing/pack`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      container,
      items,
      allow_rotation: options?.allow_rotation ?? true,
      keep_upright: options?.keep_upright ?? false,
    }),
  });
  if (!res.ok) throw new Error(`3D packing failed: ${res.statusText}`);
  return res.json();
}

