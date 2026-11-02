import type { WorkflowResult } from '../types/workflow'

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000/api'

export interface WorkflowRequest {
  user_input: string | Record<string, any>
  allow_rotation?: boolean
  keep_upright?: boolean
  max_candidate_packages?: number
}

/**
 * Execute the unified 3-agent packaging workflow:
 * 1. Requirement Gathering Agent (Extracts part geometries, weights, SNP, padding rules)
 * 2. Retrieval & Gathering Agent (Queries SQLite database for cartons, stillages, pallets)
 * 3. 3D Packing Optimizer Agent (Deterministic 3D Extreme Point spatial placement & Three.js scene)
 */
export async function runWorkflow(
  request: WorkflowRequest | string
): Promise<WorkflowResult> {
  const payload = typeof request === 'string' ? { user_input: request } : request

  const res = await fetch(`${API_BASE}/requirements/workflow`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(payload),
  })

  if (!res.ok) {
    let errorMessage = `Workflow request failed with status ${res.status}`
    try {
      const errorJson = await res.json()
      if (errorJson.detail) {
        errorMessage = typeof errorJson.detail === 'string' ? errorJson.detail : JSON.stringify(errorJson.detail)
      }
    } catch {
      const text = await res.text()
      if (text) errorMessage = text
    }
    throw new Error(errorMessage)
  }

  return res.json()
}

