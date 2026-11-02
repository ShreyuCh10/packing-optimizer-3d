import { useState, useRef, useEffect } from 'react'
import type { ChatMessage, WorkflowResult } from '../../types/workflow'
import { runWorkflow } from '../../services/workflowApi'
import WorkflowMessageCard from './WorkflowMessageCard'

const QUICK_PROMPTS = [
  {
    title: 'Standard Part Packaging',
    subtitle: '4 steel brackets measuring 140×90×60mm, 1.2kg',
    prompt:
      'Find a suitable inventory package for 4 steel brackets measuring 140x90x60mm with weight 1.2kg each.',
  },
  {
    title: 'Catalog Product Auto-Lookup',
    subtitle: 'Micro Terminal Block (Product 1, 64 units)',
    prompt: 'Lookup product 1 and pack all units according to its catalog SNP.',
  },
  {
    title: 'Heavy Industrial Stillage',
    subtitle: 'Solid Counterweight Ingot (Product 45, 38kg payload)',
    prompt:
      'Pack product 45 (Solid Counterweight Ingot). This part is heavy and will require industrial packaging.',
  },
  {
    title: 'Ambiguous Spec (Test HITL)',
    subtitle: 'Missing dimensions triggers Human-In-The-Loop',
    prompt: 'I have some metal brackets that need packaging for shipment.',
  },
]

export default function ChatbotView() {
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [inputValue, setInputValue] = useState('')
  const [isTyping, setIsTyping] = useState(false)
  const [currentRunningStage, setCurrentRunningStage] = useState<string>('requirement_gathering')
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages, isTyping])

  // Auto-resize textarea height as user types
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto'
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 160)}px`
    }
  }, [inputValue])

  // Animated pipeline progress simulation while awaiting backend response
  useEffect(() => {
    if (!isTyping) {
      setCurrentRunningStage('laya')
      return
    }

    const t1 = setTimeout(() => setCurrentRunningStage('extractor'), 400)
    const t2 = setTimeout(() => setCurrentRunningStage('cushioning'), 800)
    const t3 = setTimeout(() => setCurrentRunningStage('sqlite'), 1300)
    const t4 = setTimeout(() => setCurrentRunningStage('optimizer'), 1800)

    return () => {
      clearTimeout(t1)
      clearTimeout(t2)
      clearTimeout(t3)
      clearTimeout(t4)
    }
  }, [isTyping])

  const handleSendMessage = async (textToSend?: string) => {
    const text = (textToSend ?? inputValue).trim()
    if (!text || isTyping) return

    const userMessage: ChatMessage = {
      id: `user-${Date.now()}`,
      sender: 'user',
      text,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    }

    setMessages((prev) => [...prev, userMessage])
    setInputValue('')
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto'
    }
    setIsTyping(true)

    try {
      // Check if user is referencing a product by ID directly (e.g. "product 1" or "product id 1")
      let workflowPayload: any = text
      const prodMatch = text.match(/\bproduct\s*(?:id)?\s*[:#]?\s*(\d+)\b/i)
      if (prodMatch) {
        workflowPayload = {
          product_id: parseInt(prodMatch[1], 10),
          user_input: text,
        }
      }

      const result: WorkflowResult = await runWorkflow(workflowPayload)

      const assistantMessage: ChatMessage = {
        id: `assistant-${Date.now()}`,
        sender: 'assistant',
        text: result.summary || 'Unified packaging workflow completed.',
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        workflowResult: result,
      }

      setMessages((prev) => [...prev, assistantMessage])
    } catch (err: any) {
      console.error('Unified workflow API call failed:', err)
      const errorMessage: ChatMessage = {
        id: `assistant-err-${Date.now()}`,
        sender: 'assistant',
        text: `Error executing workflow: ${err.message || 'Unknown network or backend failure'}. Please verify that the FastAPI backend server is running at http://localhost:8000.`,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        isError: true,
      }
      setMessages((prev) => [...prev, errorMessage])
    } finally {
      setIsTyping(false)
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSendMessage()
    }
  }

  const handleNewChat = () => {
    setMessages([])
    setInputValue('')
    setIsTyping(false)
  }

  const handleApplyPrompt = (promptText: string) => {
    handleSendMessage(promptText)
  }

  return (
    <div className="flex-1 flex flex-col h-full bg-white relative">
      {/* Top Bar */}
      <div className="h-12 border-b border-slate-100 px-4 flex items-center justify-between shrink-0 bg-white z-10">
        <div className="flex items-center gap-2">
          <span className="font-semibold text-slate-800 text-sm">
            Packaging Workflow Assistant
          </span>
          <span className="inline-flex items-center gap-1.5 text-[11px] font-medium text-emerald-800 bg-emerald-50 border border-emerald-200/80 px-2 py-0.5 rounded-full">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
            3-Agent Pipeline Connected
          </span>
        </div>

        {messages.length > 0 && (
          <button
            type="button"
            onClick={handleNewChat}
            className="flex items-center gap-1.5 px-3 py-1 text-xs font-semibold text-sky-700 hover:text-sky-900 rounded-lg hover:bg-sky-50 active:scale-[0.98] transition-all duration-150 cursor-pointer"
            title="Start new chat"
          >
            <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
            </svg>
            <span>New chat</span>
          </button>
        )}
      </div>

      {/* Main Messages & Center Stage */}
      <div className="flex-1 overflow-y-auto px-4 py-4 md:py-6">
        {messages.length === 0 ? (
          /* Empty / Welcome State */
          <div className="h-full flex flex-col justify-center items-center max-w-2xl mx-auto text-center px-4">
            <div className="w-12 h-12 rounded-full bg-sky-50 text-sky-700 border border-sky-200/80 flex items-center justify-center font-bold text-lg mb-4">
              <svg className="w-6 h-6 stroke-sky-600" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={1.75}>
                <path strokeLinecap="round" strokeLinejoin="round" d="m21 7.5-9-5.25L3 7.5m18 0-9 5.25m9-5.25v9l-9 5.25M3 7.5l9 5.25M3 7.5v9l9 5.25m0-9v9" />
              </svg>
            </div>
            <h1 className="text-2xl sm:text-3xl font-semibold text-slate-900 mb-2">
              What are you packing today?
            </h1>
            <p className="text-sm text-slate-500 mb-8 max-w-md">
              Chat with our autonomous 3-agent pipeline: gathers specifications, evaluates real SQLite packaging inventory, and performs 3D Extreme Point packing.
            </p>

            {/* Prompt Suggestion Cards (2x2 grid) */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 w-full text-left">
              {QUICK_PROMPTS.map((item) => (
                <button
                  key={item.title}
                  type="button"
                  onClick={() => handleSendMessage(item.prompt)}
                  className="p-3.5 rounded-xl border border-slate-200 bg-white hover:border-sky-300 hover:bg-sky-50/40 active:scale-[0.99] transition-all duration-150 cursor-pointer text-left group shadow-2xs"
                >
                  <div className="text-xs font-semibold text-slate-800 group-hover:text-sky-900 transition-colors">
                    {item.title}
                  </div>
                  <div className="text-xs text-slate-500 mt-1 line-clamp-1">
                    {item.subtitle}
                  </div>
                </button>
              ))}
            </div>
          </div>
        ) : (
          /* Messages Stream */
          <div className="max-w-3xl mx-auto w-full space-y-6 pb-6">
            {messages.map((msg) => {
              const isUser = msg.sender === 'user'

              return isUser ? (
                /* User Message */
                <div key={msg.id} className="flex justify-end">
                  <div className="bg-slate-100 text-slate-900 rounded-3xl px-5 py-3 max-w-[80%] text-sm sm:text-base leading-relaxed whitespace-pre-wrap shadow-2xs">
                    {msg.text}
                  </div>
                </div>
              ) : (
                /* Assistant Message */
                <div key={msg.id} className="flex gap-3 sm:gap-4 items-start">
                  <div
                    className={`w-8 h-8 rounded-full flex items-center justify-center shrink-0 text-xs font-bold mt-0.5 shadow-2xs ${
                      msg.isError
                        ? 'bg-rose-600 text-white'
                        : 'bg-sky-600 text-white'
                    }`}
                  >
                    {msg.isError ? '!' : 'AI'}
                  </div>

                  <div className="flex-1 min-w-0">
                    {msg.workflowResult ? (
                      <WorkflowMessageCard
                        result={msg.workflowResult}
                        onApplyPrompt={handleApplyPrompt}
                      />
                    ) : (
                      <div
                        className={`text-sm sm:text-base leading-relaxed whitespace-pre-wrap pt-1 ${
                          msg.isError ? 'text-rose-700 bg-rose-50 border border-rose-200 rounded-xl p-3' : 'text-slate-800'
                        }`}
                      >
                        {msg.text}
                      </div>
                    )}
                  </div>
                </div>
              )
            })}

            {/* Real-time Multi-Agent Progress Indicator */}
            {isTyping && (
              <div className="flex gap-3 sm:gap-4 items-start animate-fade-in">
                <div className="w-8 h-8 rounded-full bg-sky-600 text-white flex items-center justify-center shrink-0 text-xs font-bold shadow-2xs">
                  AI
                </div>
                <div className="flex-1 bg-slate-50 border border-slate-200/90 rounded-2xl p-4 shadow-2xs">
                  <div className="flex items-center gap-2 mb-3">
                    <span className="w-2 h-2 rounded-full bg-sky-500 animate-ping" />
                    <span className="text-xs font-bold text-slate-800 uppercase tracking-wider">
                      Executing Multi-Agent Tool Trace
                    </span>
                  </div>

                  {/* Visual 5-step tool progression mini-stepper */}
                  <div className="space-y-2 text-xs">
                    <div className="flex items-center gap-2 text-slate-700">
                      <span
                        className={`w-4 h-4 rounded-full flex items-center justify-center text-[10px] font-bold ${
                          currentRunningStage === 'laya'
                            ? 'bg-sky-600 text-white animate-pulse'
                            : 'bg-emerald-500 text-white'
                        }`}
                      >
                        {currentRunningStage === 'laya' ? '1' : '✓'}
                      </span>
                      <span className={currentRunningStage === 'laya' ? 'font-semibold text-sky-900' : 'text-slate-500'}>
                        Step 1: Laya Semantic Gating Router (evaluating confidence & completeness)
                      </span>
                    </div>

                    <div className="flex items-center gap-2 text-slate-700">
                      <span
                        className={`w-4 h-4 rounded-full flex items-center justify-center text-[10px] font-bold ${
                          currentRunningStage === 'extractor'
                            ? 'bg-sky-600 text-white animate-pulse'
                            : currentRunningStage === 'laya'
                            ? 'bg-slate-200 text-slate-500'
                            : 'bg-emerald-500 text-white'
                        }`}
                      >
                        {currentRunningStage === 'extractor' ? '2' : currentRunningStage === 'laya' ? '2' : '✓'}
                      </span>
                      <span className={currentRunningStage === 'extractor' ? 'font-semibold text-sky-900' : 'text-slate-500'}>
                        Step 2: Specification Extractor (extracting geometries, weight, SNP & material)
                      </span>
                    </div>

                    <div className="flex items-center gap-2 text-slate-700">
                      <span
                        className={`w-4 h-4 rounded-full flex items-center justify-center text-[10px] font-bold ${
                          currentRunningStage === 'cushioning'
                            ? 'bg-sky-600 text-white animate-pulse'
                            : ['laya', 'extractor'].includes(currentRunningStage)
                            ? 'bg-slate-200 text-slate-500'
                            : 'bg-emerald-500 text-white'
                        }`}
                      >
                        {currentRunningStage === 'cushioning' ? '3' : ['laya', 'extractor'].includes(currentRunningStage) ? '3' : '✓'}
                      </span>
                      <span className={currentRunningStage === 'cushioning' ? 'font-semibold text-sky-900' : 'text-slate-500'}>
                        Step 3: Cushioning Engine (calculating foam clearance & multi-unit bounding box)
                      </span>
                    </div>

                    <div className="flex items-center gap-2 text-slate-700">
                      <span
                        className={`w-4 h-4 rounded-full flex items-center justify-center text-[10px] font-bold ${
                          currentRunningStage === 'sqlite'
                            ? 'bg-sky-600 text-white animate-pulse'
                            : currentRunningStage === 'optimizer'
                            ? 'bg-emerald-500 text-white'
                            : 'bg-slate-200 text-slate-500'
                        }`}
                      >
                        {currentRunningStage === 'sqlite' ? '4' : currentRunningStage === 'optimizer' ? '✓' : '4'}
                      </span>
                      <span className={currentRunningStage === 'sqlite' ? 'font-semibold text-sky-900' : 'text-slate-500'}>
                        Step 4: SQLite Database Query (scanning cartons, stillages & pallets)
                      </span>
                    </div>

                    <div className="flex items-center gap-2 text-slate-700">
                      <span
                        className={`w-4 h-4 rounded-full flex items-center justify-center text-[10px] font-bold ${
                          currentRunningStage === 'optimizer'
                            ? 'bg-sky-600 text-white animate-pulse'
                            : 'bg-slate-200 text-slate-500'
                        }`}
                      >
                        5
                      </span>
                      <span className={currentRunningStage === 'optimizer' ? 'font-semibold text-sky-900' : 'text-slate-500'}>
                        Step 5: 3D Extreme Point Optimizer (evaluating 6-DOF rotations & stability)
                      </span>
                    </div>
                  </div>
                </div>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>
        )}
      </div>

      {/* Bottom Input Dock */}
      <div className="shrink-0 max-w-3xl mx-auto w-full px-4 pb-3 sm:pb-4 pt-1 bg-white">
        <form
          onSubmit={(e) => {
            e.preventDefault()
            handleSendMessage()
          }}
          className="relative bg-slate-100 focus-within:bg-white focus-within:ring-2 focus-within:ring-sky-500 focus-within:border-sky-500 border border-slate-200 rounded-3xl p-2 sm:p-2.5 flex items-end gap-2 transition-all duration-150 shadow-2xs"
        >
          <textarea
            ref={textareaRef}
            rows={1}
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={isTyping}
            placeholder={isTyping ? 'Pipeline is running...' : 'Describe parts or enter product ID (e.g. "Pack 4 steel brackets 140x90x60mm 1.2kg")...'}
            className="flex-1 bg-transparent border-0 focus:ring-0 focus:outline-none resize-none text-sm sm:text-base px-3 py-1.5 text-slate-900 placeholder-slate-400 max-h-36 leading-normal disabled:opacity-60"
          />

          {/* Send Button */}
          <button
            type="submit"
            disabled={!inputValue.trim() || isTyping}
            aria-label="Send message"
            className={`w-8 h-8 rounded-full flex items-center justify-center shrink-0 transition-all duration-150 cursor-pointer ${
              inputValue.trim() && !isTyping
                ? 'bg-sky-600 text-white hover:bg-sky-700 active:scale-[0.95] shadow-xs'
                : 'bg-slate-300 text-slate-100 cursor-not-allowed'
            }`}
          >
            <svg
              className="w-4 h-4"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
              strokeWidth={2.5}
            >
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 19.5v-15m0 0l-6 6m6-6l6 6" />
            </svg>
          </button>
        </form>

        <p className="text-[11px] text-slate-400 text-center mt-2">
          Connected to LangGraph Unified Packaging Workflow: Requirement Gathering • SQLite Candidate Retrieval • 3D Extreme Point Optimizer.
        </p>
      </div>
    </div>
  )
}
