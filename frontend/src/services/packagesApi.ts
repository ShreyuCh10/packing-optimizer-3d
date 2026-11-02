import type { PackagingItem, PackageListResponse } from '../types/packages'

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000/api'

export async function fetchPackages(
  category?: string,
  search?: string
): Promise<PackageListResponse> {
  const url = new URL(`${API_BASE}/packages`)
  if (category && category !== 'all') {
    url.searchParams.set('category', category)
  }
  if (search && search.trim()) {
    url.searchParams.set('search', search.trim())
  }

  const res = await fetch(url.toString())
  if (!res.ok) {
    throw new Error(`Failed to fetch packages (${res.status}): ${res.statusText}`)
  }
  return res.json()
}

export async function fetchPackageByIdOrName(
  idOrName: string | number
): Promise<PackagingItem> {
  const res = await fetch(`${API_BASE}/packages/${encodeURIComponent(idOrName)}`)
  if (!res.ok) {
    throw new Error(
      `Failed to fetch package '${idOrName}' (${res.status}): ${res.statusText}`
    )
  }
  return res.json()
}

