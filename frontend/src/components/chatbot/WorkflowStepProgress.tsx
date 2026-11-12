interface WorkflowStepProgressProps {
  currentStage?: string
  status?: string
  hitlRequired?: boolean
  isLoading?: boolean
}

interface StepDef {
  id: string
  num: number
  title: string
  subtitle: string
  agentName: string
}

const STEPS: StepDef[] = [
  {
    id: 'requirement_gathering',
    num: 1,
    title: 'Requirements',
    subtitle: 'Dimensions, SNP & Padding',
    agentName: 'Requirement Gathering Agent',
  },
  {
    id: 'retrieval_gathering',
    num: 2,
    title: 'Retrieval',
    subtitle: 'Database Inventory Match',
    agentName: 'Retrieval & Gathering Agent',
  },
  {
    id: 'packing_optimization',
    num: 3,
    title: '3D Optimizer',
    subtitle: 'Extreme Point Placement',
    agentName: 'Packing Optimizer Agent',
  },
]

export default function WorkflowStepProgress({
  currentStage = 'packing_optimization',
  status,
  hitlRequired = false,
  isLoading = false,
}: WorkflowStepProgressProps) {
  const getStepStatus = (index: number) => {
    if (isLoading) {
      return 'active'
    }

    if (hitlRequired) {
      if (index === 0) return 'hitl'
      return 'pending'
    }

    // Normal workflow progression
    if (currentStage === 'packing_optimization') {
      return 'completed'
    }

    if (currentStage === 'retrieval_gathering') {
      if (index < 2) return 'completed'
      return 'pending'
    }

    if (currentStage === 'requirement_gathering') {
      if (index === 0) return 'completed'
      return 'pending'
    }

    return 'completed'
  }

  return (
    <div className="w-full bg-slate-50 border border-slate-200 rounded-xl p-3 my-2 shadow-2xs">
      <div className="flex items-center justify-between gap-1 sm:gap-2">
        {STEPS.map((step, idx) => {
          const stepStatus = getStepStatus(idx)
          const isLast = idx === STEPS.length - 1

          return (
            <div key={step.id} className="flex-1 flex items-center">
              {/* Step Pill */}
              <div className="flex items-center gap-2 min-w-0">
                {/* Circle Icon Badge */}
                <div
                  className={`w-6 h-6 rounded-full flex items-center justify-center text-[11px] font-bold shrink-0 transition-colors ${
                    stepStatus === 'completed'
                      ? 'bg-emerald-600 text-white'
                      : stepStatus === 'hitl'
                      ? 'bg-amber-500 text-white'
                      : stepStatus === 'active'
                      ? 'bg-sky-600 text-white animate-pulse'
                      : 'bg-slate-200 text-slate-500'
                  }`}
                >
                  {stepStatus === 'completed' ? (
                    <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={3}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="m4.5 12.75 6 6 9-13.5" />
                    </svg>
                  ) : stepStatus === 'hitl' ? (
                    '!'
                  ) : (
                    step.num
                  )}
                </div>

                {/* Step Labels */}
                <div className="min-w-0 pr-1">
                  <div className="text-xs font-semibold text-slate-800 truncate leading-tight">
                    {step.title}
                  </div>
                  <div className="text-[10px] text-slate-500 truncate hidden sm:block leading-tight">
                    {step.subtitle}
                  </div>
                </div>
              </div>

              {/* Connecting Line */}
              {!isLast && (
                <div
                  className={`flex-1 h-0.5 mx-1 sm:mx-2 rounded transition-colors ${
                    stepStatus === 'completed' ? 'bg-emerald-400' : 'bg-slate-200'
                  }`}
                />
              )}
            </div>
          )
        })}
      </div>

      {/* Real-time Subtext / Process Label */}
      <div className="mt-2 pt-2 border-t border-slate-200/80 flex items-center justify-between text-[11px]">
        <div className="flex items-center gap-1.5 text-slate-600">
          <span className="font-medium text-slate-700">Multi-Agent State:</span>
          {isLoading ? (
            <span className="text-sky-700 font-semibold animate-pulse flex items-center gap-1">
              <span className="w-1.5 h-1.5 rounded-full bg-sky-500" />
              Running multi-agent pipeline...
            </span>
          ) : hitlRequired ? (
            <span className="text-amber-700 font-semibold flex items-center gap-1">
              <span className="w-1.5 h-1.5 rounded-full bg-amber-500" />
              Paused for Human-In-The-Loop Clarification
            </span>
          ) : status === 'workflow_completed_optimal_fit' ? (
            <span className="text-emerald-700 font-semibold flex items-center gap-1">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
              Optimal 3D Fit Confirmed
            </span>
          ) : (
            <span className="text-slate-700 font-medium">Pipeline Executed</span>
          )}
        </div>

        <span className="text-[10px] text-slate-400 font-mono hidden md:inline">
          LangGraph • Extreme Point 3D
        </span>
      </div>
    </div>
  )
}
