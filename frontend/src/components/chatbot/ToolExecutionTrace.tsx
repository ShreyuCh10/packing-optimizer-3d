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

const CATEGORY_COLORS: Record<string, { bg: string; text: string; border: string }> = {
  requirement: { bg: 'bg-sky-50', text: 'text-sky-700', border: 'border-sky-200' },
  retrieval: { bg: 'bg-indigo-50', text: 'text-indigo-700', border: 'border-indigo-200' },
  optimization: { bg: 'bg-emerald-50', text: 'text-emerald-700', border: 'border-emerald-200' },
}

export default function ToolExecutionTrace({
  steps = [],
  defaultOpenIndex = -1,
}: ToolExecutionTraceProps) {
  // Set default: if only 1-2 steps or if warning, open them; otherwise collapsed by default
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
    <div className="w-full bg-slate-50/70 border border-slate-200 rounded-xl overflow-hidden shadow-2xs my-3">
      {/* Major Heading Toolbar */}
      <div className="px-3.5 py-2.5 bg-slate-100/90 border-b border-slate-200 flex items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-sky-500 animate-pulse" />
          <h3 className="text-xs font-bold text-slate-800 uppercase tracking-wider">
            Tool Use & Granular Execution Steps ({steps.length} Steps)
          </h3>
        </div>

        <button
          type="button"
          onClick={toggleAll}
          className="text-[11px] font-semibold text-sky-700 hover:text-sky-900 px-2 py-0.5 rounded hover:bg-slate-200/80 transition-colors cursor-pointer"
        >
          {allOpen ? 'Collapse All' : 'Expand All Steps'}
        </button>
      </div>

      {/* Accordion List of Tool Calls */}
      <div className="divide-y divide-slate-200">
        {steps.map((step, idx) => {
          const isOpen = Boolean(openMap[step.id])
          const isRaw = Boolean(rawViewMap[step.id])
          const icon = TOOL_ICONS[step.id] || '🔧'
          const catStyle = CATEGORY_COLORS[step.category] || CATEGORY_COLORS.requirement

          return (
            <div key={step.id} className="bg-white transition-colors">
              {/* Collapsed / Header Bar */}
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
                className="w-full px-3.5 py-2.5 flex items-center justify-between gap-3 text-left hover:bg-slate-50/80 active:bg-slate-100/60 cursor-pointer select-none transition-colors"
              >
                <div className="flex items-center gap-2.5 min-w-0">
                  {/* Step Number & Icon */}
                  <div className="flex items-center gap-1 shrink-0">
                    <span className="text-xs font-bold text-slate-400">#{idx + 1}</span>
                    <span className="text-base" role="img" aria-label="tool icon">
                      {icon}
                    </span>
                  </div>

                  {/* Tool Name & Method Badge */}
                  <div className="min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="text-xs font-bold text-slate-900 truncate">
                        {step.tool_name}
                      </span>

                      {step.category && (
                        <span className={`text-[10px] font-semibold uppercase tracking-wider px-1.5 py-0.2 rounded border ${catStyle.bg} ${catStyle.text} ${catStyle.border}`}>
                          {step.category}
                        </span>
                      )}

                      {step.method && (
                        <span className="text-[10px] font-medium font-mono px-1.5 py-0.2 rounded bg-slate-100 text-slate-600 border border-slate-200">
                          {step.method}
                        </span>
                      )}

                      {typeof step.confidence === 'number' && (
                        <span className="text-[10px] font-semibold px-1.5 py-0.2 rounded bg-emerald-50 text-emerald-700 border border-emerald-200">
                          Confidence: {step.confidence}%
                        </span>
                      )}
                    </div>

                    <div className="text-[11px] text-slate-500 truncate mt-0.5">
                      {step.summary}
                    </div>
                  </div>
                </div>

                {/* Right Status Badge & Chevron */}
                <div className="flex items-center gap-2 shrink-0">
                  <span
                    className={`text-[10px] font-semibold px-2 py-0.5 rounded-full border ${
                      step.status === 'success'
                        ? 'bg-emerald-50 text-emerald-800 border-emerald-200'
                        : step.status === 'warning'
                        ? 'bg-amber-50 text-amber-800 border-amber-200'
                        : 'bg-rose-50 text-rose-800 border-rose-200'
                    }`}
                  >
                    {step.status === 'success' ? 'Completed' : 'Clarification'}
                  </span>

                  <svg
                    className={`w-4 h-4 text-slate-400 transition-transform duration-200 ${
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

              {/* Expanded Tool Details */}
              {isOpen && (
                <div className="px-3.5 pb-3.5 pt-1 border-t border-slate-100 bg-slate-50/50 space-y-3">
                  <div className="flex items-center justify-between text-[11px] text-slate-500 pt-1">
                    <span className="font-medium text-slate-700">
                      Execution Parameters & Results:
                    </span>
                    <button
                      type="button"
                      onClick={(e) => toggleRaw(step.id, e)}
                      className="text-sky-700 hover:text-sky-900 font-semibold underline cursor-pointer"
                    >
                      {isRaw ? 'Formatted View' : 'Raw JSON'}
                    </button>
                  </div>

                  {isRaw ? (
                    <pre className="p-2.5 bg-slate-900 text-slate-100 rounded-lg text-[11px] font-mono overflow-x-auto leading-relaxed max-h-60">
                      {JSON.stringify({ inputs: step.inputs, outputs: step.outputs }, null, 2)}
                    </pre>
                  ) : (
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
                      {/* Left: Tool Inputs */}
                      <div className="bg-white p-3 rounded-lg border border-slate-200 space-y-2">
                        <div className="text-[10px] font-bold text-slate-500 uppercase tracking-wider flex items-center gap-1">
                          <span className="w-1.5 h-1.5 rounded-full bg-sky-500" />
                          Parameters Passed to Tool:
                        </div>
                        {step.inputs && Object.keys(step.inputs).length > 0 ? (
                          <div className="space-y-1.5">
                            {Object.entries(step.inputs).map(([k, v]) => (
                              <div key={k} className="flex flex-col sm:flex-row sm:justify-between text-slate-700">
                                <span className="font-medium text-slate-600 capitalize">
                                  {k.replace(/_/g, ' ')}:
                                </span>
                                <span className="font-mono text-slate-900 break-all sm:text-right">
                                  {typeof v === 'object' ? JSON.stringify(v) : String(v)}
                                </span>
                              </div>
                            ))}
                          </div>
                        ) : (
                          <div className="text-slate-400 italic">No input parameters logged</div>
                        )}
                      </div>

                      {/* Right: Tool Outputs */}
                      <div className="bg-white p-3 rounded-lg border border-slate-200 space-y-2">
                        <div className="text-[10px] font-bold text-slate-500 uppercase tracking-wider flex items-center gap-1">
                          <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
                          Tool Execution Outputs:
                        </div>
                        {step.outputs && Object.keys(step.outputs).length > 0 ? (
                          <div className="space-y-1.5">
                            {Object.entries(step.outputs).map(([k, v]) => (
                              <div key={k} className="flex flex-col sm:flex-row sm:justify-between text-slate-700">
                                <span className="font-medium text-slate-600 capitalize">
                                  {k.replace(/_/g, ' ')}:
                                </span>
                                <span className="font-mono text-slate-900 break-all sm:text-right font-semibold">
                                  {typeof v === 'object' ? JSON.stringify(v) : String(v)}
                                </span>
                              </div>
                            ))}
                          </div>
                        ) : (
                          <div className="text-slate-400 italic">No output payload logged</div>
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
