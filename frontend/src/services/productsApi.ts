import type { Product, ProductsResponse } from '../types/customBox';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';

export async function fetchProducts(search?: string): Promise<ProductsResponse> {
  const url = new URL(`${API_BASE}/products`);
  if (search && search.trim()) {
    url.searchParams.set('search', search.trim());
  }

  try {
    const res = await fetch(url.toString());
    if (res.ok) {
      return await res.json();
    }
  } catch (err) {
    // If backend direct endpoint is not yet restarted or has an issue, fallback to custom-box/products
    console.warn('Falling back to /api/custom-box/products:', err);
  }

  const fallbackRes = await fetch(`${API_BASE}/custom-box/products`);
  if (!fallbackRes.ok) {
    throw new Error(`Failed to fetch products: ${fallbackRes.statusText}`);
  }
  return fallbackRes.json();
}

export async function fetchProductByIdOrName(idOrName: string | number): Promise<Product> {
  const res = await fetch(`${API_BASE}/products/${idOrName}`);
  if (!res.ok) {
    // Fallback
    const fallbackRes = await fetch(`${API_BASE}/custom-box/products/${idOrName}`);
    if (!fallbackRes.ok) {
      throw new Error(`Failed to fetch product '${idOrName}': ${fallbackRes.statusText}`);
    }
    return fallbackRes.json();
  }
  return res.json();
}

