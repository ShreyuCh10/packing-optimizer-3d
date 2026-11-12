import type { Product } from '../types/customBox'

const API_URL = 'http://localhost:8000'

export interface ProductsResponse {
  products: Product[]
}

export async function fetchProducts(): Promise<ProductsResponse> {
  const response = await fetch(`${API_URL}/products`)

  if (!response.ok) {
    throw new Error(`Unable to load products (${response.status})`)
  }

  const data: Product[] = await response.json()

  return {
    products: data,
  }
}