import { useState } from 'react'
import type { ToolExecutionStep } from '../../types/workflow'

interface ToolExecutionTraceProps {
  steps?: ToolExecutionStep[]
  defaultOpenIndex?: number
}

const TOOL_ICONS: Record<string, string> = {
  step_1_laya: '🧠',
  step_2_extractor: '⚙️',
  step_3_cushioning: '🛡️',
  step_4_sqlite: '🗄️',
  step_5_optimizer: '📦',
}

export default function ToolExecutionTrace({
  steps = [],
  defaultOpenIndex = -1,
}: ToolExecutionTraceProps) {
  const [openMap, setOpenMap] = useState<Record<string, boolean>>(() => {
    const initial: Record<string, boolean> = {}
    steps.forEach((step, idx) => {
      if (defaultOpenIndex === idx || step.status === 'warning') {
        initial[step.id] = true
      }
    })
    return initial
  })

  const [rawViewMap, setRawViewMap] = useState<Record<string, boolean>>({})

  if (!steps || steps.length === 0) return null

  const toggleStep = (id: string) => {
    setOpenMap((prev) => ({ ...prev, [id]: !prev[id] }))
  }

  const toggleAll = () => {
    const allOpen = steps.every((s) => openMap[s.id])
    const next: Record<string, boolean> = {}
    steps.forEach((s) => {
      next[s.id] = !allOpen
    })
    setOpenMap(next)
  }

  const toggleRaw = (id: string, e: React.MouseEvent) => {
    e.stopPropagation()
    setRawViewMap((prev) => ({ ...prev, [id]: !prev[id] }))
  }

  const allOpen = steps.every((s) => openMap[s.id])

  return (
    <div className="w-full bg-white border border-slate-200 rounded-lg overflow-hidden shadow-2xs my-2.5">
      {/* Header Toolbar */}
      <div className="px-3 py-1.5 bg-slate-50 border-b border-slate-200 flex items-center justify-between gap-2">
        <div className="flex items-center gap-1.5">
          <span className="w-1.5 h-1.5 rounded-full bg-sky-500" />
          <span className="text-[10px] font-bold text-slate-700 uppercase tracking-wider">
            Tool Execution Steps ({steps.length})
          </span>
        </div>

        <button
          type="button"
          onClick={toggleAll}
          className="text-[10px] font-semibold text-sky-700 hover:text-sky-900 px-1.5 py-0.5 rounded hover:bg-slate-200/60 transition-colors cursor-pointer"
        >
          {allOpen ? 'Collapse All' : 'Expand All'}
        </button>
      </div>

      {/* Singular Line Steps */}
      <div className="divide-y divide-slate-100">
        {steps.map((step) => {
          const isOpen = Boolean(openMap[step.id])
          const isRaw = Boolean(rawViewMap[step.id])
          const icon = TOOL_ICONS[step.id] || '🔧'
          const isSuccess = step.status === 'success'

          return (
            <div key={step.id} className="transition-colors">
              {/* Single Compact Line */}
              <div
                role="button"
                tabIndex={0}
                onClick={() => toggleStep(step.id)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault()
                    toggleStep(step.id)
                  }
                }}
                className="w-full px-3 py-1.5 flex items-center justify-between gap-2 text-left hover:bg-slate-50 active:bg-slate-100 cursor-pointer select-none transition-colors"
              >
                {/* Left: Icon & Tool Name Only */}
                <div className="flex items-center gap-2 min-w-0">
                  <span className="text-xs shrink-0 select-none" role="img" aria-label="tool icon">
                    {icon}
                  </span>
                  <span className="text-xs font-medium text-slate-800 truncate">
                    {step.tool_name}
                  </span>
                </div>

                {/* Right: Tick/Cross & Dropdown Arrow */}
                <div className="flex items-center gap-2 shrink-0">
                  {isSuccess ? (
                    <span title="Completed" className="inline-flex items-center justify-center">
                      <svg
                        className="w-3.5 h-3.5 text-emerald-600"
                        fill="none"
                        viewBox="0 0 24 24"
                        strokeWidth={2.5}
                        stroke="currentColor"
                      >
                        <path strokeLinecap="round" strokeLinejoin="round" d="m4.5 12.75 6 6 9-13.5" />
                      </svg>
                    </span>
                  ) : (
                    <span title={step.status || 'Failed / Warning'} className="inline-flex items-center justify-center">
                      <svg
                        className="w-3.5 h-3.5 text-rose-500"
                        fill="none"
                        viewBox="0 0 24 24"
                        strokeWidth={2.5}
                        stroke="currentColor"
                      >
                        <path strokeLinecap="round" strokeLinejoin="round" d="M6 18 18 6M6 6l12 12" />
                      </svg>
                    </span>
                  )}

                  <svg
                    className={`w-3.5 h-3.5 text-slate-400 transition-transform duration-200 ${
                      isOpen ? 'rotate-180' : ''
                    }`}
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                    strokeWidth={2}
                  >
                    <path strokeLinecap="round" strokeLinejoin="round" d="m19.5 8.25-7.5 7.5-7.5-7.5" />
                  </svg>
                </div>
              </div>

              {/* Expandable Details on Click */}
              {isOpen && (
                <div className="px-3 pb-2.5 pt-1 border-t border-slate-100 bg-slate-50/70 space-y-2 text-[11px]">
                  {step.summary && (
                    <div className="text-slate-600 text-[11px] leading-relaxed pt-0.5">
                      {step.summary}
                      {typeof step.confidence === 'number' && (
                        <span className="ml-2 font-mono text-emerald-700 font-semibold">
                          (Confidence: {step.confidence}%)
                        </span>
                      )}
                    </div>
                  )}

                  <div className="flex items-center justify-between text-[10px] text-slate-500 pt-0.5">
                    <span className="font-semibold uppercase tracking-wider text-slate-500">
                      Parameters & Output:
                    </span>
                    <button
                      type="button"
                      onClick={(e) => toggleRaw(step.id, e)}
                      className="text-sky-700 hover:text-sky-900 font-semibold underline cursor-pointer"
                    >
                      {isRaw ? 'Formatted' : 'Raw JSON'}
                    </button>
                  </div>

                  {isRaw ? (
                    <pre className="p-2 bg-slate-900 text-slate-100 rounded text-[10px] font-mono overflow-x-auto leading-relaxed max-h-48">
                      {JSON.stringify({ inputs: step.inputs, outputs: step.outputs }, null, 2)}
                    </pre>
                  ) : (
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-[11px]">
                      {/* Inputs */}
                      <div className="bg-white p-2 rounded border border-slate-200 space-y-1">
                        <div className="text-[10px] font-bold text-slate-500 uppercase tracking-wider">
                          Inputs:
                        </div>
                        {step.inputs && Object.keys(step.inputs).length > 0 ? (
                          <div className="space-y-0.5">
                            {Object.entries(step.inputs).map(([k, v]) => (
                              <div key={k} className="flex justify-between gap-2 text-slate-700">
                                <span className="font-medium text-slate-500 capitalize shrink-0">
                                  {k.replace(/_/g, ' ')}:
                                </span>
                                <span className="font-mono text-slate-800 break-all text-right">
                                  {typeof v === 'object' ? JSON.stringify(v) : String(v)}
                                </span>
                              </div>
                            ))}
                          </div>
                        ) : (
                          <div className="text-slate-400 italic text-[10px]">No inputs logged</div>
                        )}
                      </div>

                      {/* Outputs */}
                      <div className="bg-white p-2 rounded border border-slate-200 space-y-1">
                        <div className="text-[10px] font-bold text-slate-500 uppercase tracking-wider">
                          Outputs:
                        </div>
                        {step.outputs && Object.keys(step.outputs).length > 0 ? (
                          <div className="space-y-0.5">
                            {Object.entries(step.outputs).map(([k, v]) => (
                              <div key={k} className="flex justify-between gap-2 text-slate-700">
                                <span className="font-medium text-slate-500 capitalize shrink-0">
                                  {k.replace(/_/g, ' ')}:
                                </span>
                                <span className="font-mono text-slate-900 break-all text-right font-medium">
                                  {typeof v === 'object' ? JSON.stringify(v) : String(v)}
                                </span>
                              </div>
                            ))}
                          </div>
                        ) : (
                          <div className="text-slate-400 italic text-[10px]">No outputs logged</div>
                        )}
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}
