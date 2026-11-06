import type { WorkflowResult } from '../types/workflow'

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000/api'

export interface WorkflowRequest {
  user_input: string | Record<string, any>
  conversation_id?: string
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
  request: WorkflowRequest | string,
  onProgress?: (label: string) => void,
): Promise<WorkflowResult> {
  const payload = typeof request === 'string' ? { user_input: request } : request

  const res = await fetch(`${API_BASE}/requirements/workflow/stream`, {
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

  if (!res.body) return res.json()

  const reader = res.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  let finalResult: WorkflowResult | undefined

  const handleEvent = (line: string) => {
    if (!line.startsWith('data:')) return
    const event = JSON.parse(line.slice(5).trim())
    if (event.type === 'progress') onProgress?.(event.label)
    if (event.type === 'result') finalResult = event.result as WorkflowResult
    if (event.type === 'error') throw new Error(event.message || 'Workflow failed')
  }

  while (true) {
    const { value, done } = await reader.read()
    buffer += decoder.decode(value, { stream: !done })
    const lines = buffer.split(/\r?\n/)
    buffer = lines.pop() ?? ''
    lines.forEach(handleEvent)
    if (done) break
  }
  if (buffer.trim()) handleEvent(buffer.trim())
  if (!finalResult) throw new Error('The workflow stream ended without a result')
  return finalResult
}

/** Run cart selections as one structured manifest through catalog validation and optimization. */
export async function runCartWorkflow(
  items: Array<Record<string, unknown>>,
): Promise<WorkflowResult> {
  const res = await fetch(`${API_BASE}/requirements/workflow/execute`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ user_input: { items } }),
  })

  if (!res.ok) {
    let message = `Cart optimization failed with status ${res.status}`
    try {
      const body = await res.json()
      if (body.detail) message = typeof body.detail === 'string' ? body.detail : JSON.stringify(body.detail)
    } catch {
      // Keep the status message when the server response is not JSON.
    }
    throw new Error(message)
  }
  return res.json()
}

