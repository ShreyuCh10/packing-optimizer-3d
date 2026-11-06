import type { CartSummary, CartItem, AddToCartPayload } from '../types/cart'

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000/api'

function notifyCartUpdated(cart?: CartSummary) {
  if (typeof window !== 'undefined') {
    window.dispatchEvent(new CustomEvent('cart-updated', { detail: cart }))
  }
}

export async function fetchCart(): Promise<CartSummary> {
  const res = await fetch(`${API_BASE}/cart`)
  if (!res.ok) {
    throw new Error(`Failed to fetch cart: ${res.statusText}`)
  }
  return res.json()
}

export async function addToCart(payload: AddToCartPayload): Promise<{
  status: string
  message: string
  item: CartItem
  cart: CartSummary
}> {
  const res = await fetch(`${API_BASE}/cart`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(payload),
  })
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}))
    throw new Error(errorData.detail || `Failed to add product to cart: ${res.statusText}`)
  }
  const data = await res.json()
  notifyCartUpdated(data.cart)
  return data
}

export async function updateCartItemQuantity(
  itemId: number,
  numberOfParts: number
): Promise<{
  status: string
  message: string
  item: CartItem | null
  cart: CartSummary
}> {
  const res = await fetch(`${API_BASE}/cart/${itemId}`, {
    method: 'PUT',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ number_of_parts: numberOfParts }),
  })
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}))
    throw new Error(errorData.detail || `Failed to update cart item: ${res.statusText}`)
  }
  const data = await res.json()
  notifyCartUpdated(data.cart)
  return data
}

export async function removeCartItem(itemId: number): Promise<{
  status: string
  message: string
  cart: CartSummary
}> {
  const res = await fetch(`${API_BASE}/cart/${itemId}`, {
    method: 'DELETE',
  })
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}))
    throw new Error(errorData.detail || `Failed to delete cart item: ${res.statusText}`)
  }
  const data = await res.json()
  notifyCartUpdated(data.cart)
  return data
}

export async function clearCart(): Promise<{
  status: string
  message: string
  cart: CartSummary
}> {
  const res = await fetch(`${API_BASE}/cart`, {
    method: 'DELETE',
  })
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}))
    throw new Error(errorData.detail || `Failed to clear cart: ${res.statusText}`)
  }
  const data = await res.json()
  notifyCartUpdated(data.cart)
  return data
}
