import { useState, useRef, useEffect } from 'react'
import type { ChatMessage, WorkflowResult } from '../../types/workflow'
import { runWorkflow } from '../../services/workflowApi'
import WorkflowMessageCard from './WorkflowMessageCard'

const QUICK_PROMPTS = [
  {
    title: 'Look Up a Catalog Product',
    subtitle: 'Search by product name or ID',
    prompt:
      'Can you help me find a product in the catalog?',
  },
  {
    title: 'Catalog Product Auto-Lookup',
    subtitle: 'Micro Terminal Block (Product 1, 64 units)',
    prompt: 'Lookup product 1 and pack all units according to its catalog SNP.',
  },
  {
    title: 'Heavy Payload Rating Check',
    subtitle: 'Solid Counterweight Ingot (Product 45, 38kg)',
    prompt:
      'Pack product 45 (Solid Counterweight Ingot). This part is heavy and will require industrial packaging.',
  },
]

const isDoneIntent = (text: string) => {
  if (/\b(?:add another|another (?:product|item)|one more)\b/i.test(text)) return false
  return /^\s*(?:no|nope|done|finished|complete|proceed|that's all|that is all|all set|nothing else|optimi[sz]e|start packing|start optimi[sz]ation)\b/i.test(text)
}

export default function ChatbotView() {
  const [conversationId, setConversationId] = useState(() => {
    try {
      const saved = localStorage.getItem('packing-optimizer-conversation-id')
      if (saved) return saved
      const created = crypto.randomUUID()
      localStorage.setItem('packing-optimizer-conversation-id', created)
      return created
    } catch {
      return `${Date.now()}-${Math.random().toString(36).slice(2)}`
    }
  })
  const [messages, setMessages] = useState<ChatMessage[]>(() => {
    try {
      const saved = localStorage.getItem('packing-optimizer-chat-messages')
      return saved ? JSON.parse(saved) as ChatMessage[] : []
    } catch {
      return []
    }
  })
  const [taskItems, setTaskItems] = useState<Array<Record<string, any>>>(() => {
    try {
      const saved = localStorage.getItem('packing-optimizer-chat-task-manifest')
      if (saved) return JSON.parse(saved) as Array<Record<string, any>>
      const previousManifest = [...messages].reverse().find(
        (message) => message.sender === 'assistant' && Array.isArray(message.taskManifest),
      )?.taskManifest
      return previousManifest ?? []
    } catch {
      return []
    }
  })
  const [taskCartOpen, setTaskCartOpen] = useState(false)
  const [inputValue, setInputValue] = useState('')
  const [isTyping, setIsTyping] = useState(false)
  const [isWorkflowRunning, setIsWorkflowRunning] = useState(false)
  const [currentWorkflowStep, setCurrentWorkflowStep] = useState<string>('')
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  useEffect(() => {
    try {
      localStorage.setItem('packing-optimizer-chat-messages', JSON.stringify(messages))
    } catch {
      // Keep the in-memory conversation usable if browser storage is unavailable.
    }
  }, [messages])

  useEffect(() => {
    try {
      localStorage.setItem('packing-optimizer-chat-task-manifest', JSON.stringify(taskItems))
    } catch {
      // Keep the in-memory packing list usable if browser storage is unavailable.
    }
    if (taskItems.length > 0) setTaskCartOpen(true)
  }, [taskItems])

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

  const handleSendMessage = async (textToSend?: string, action?: 'optimize') => {
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
    const lastAssistant = [...messages].reverse().find((message) => message.sender === 'assistant')
    const shouldRunWorkflow = action === 'optimize' || (lastAssistant?.workflowStatus === 'awaiting_more_items' && isDoneIntent(text))
    setIsWorkflowRunning(shouldRunWorkflow)
    setCurrentWorkflowStep(shouldRunWorkflow ? 'Starting the confirmed optimization task' : 'Connecting to the requirement agent')
    setIsTyping(true)

    try {
      const result: WorkflowResult = await runWorkflow({
        user_input: action ? { action, text } : text,
        conversation_id: conversationId,
      }, setCurrentWorkflowStep)

      if (result.task_manifest) setTaskItems(result.task_manifest)

      const assistantMessage: ChatMessage = {
        id: `assistant-${Date.now()}`,
        sender: 'assistant',
        text: result.summary || 'Unified packaging workflow completed.',
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        workflowResult: result.action === 'conversation' ? undefined : result,
        taskManifest: result.task_manifest,
        workflowStatus: result.status,
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
      setIsWorkflowRunning(false)
      setCurrentWorkflowStep('')
    }
  }

  const handleOptimizeTask = () => {
    if (!taskItems.length || isTyping) return
    handleSendMessage('Optimize confirmed products', 'optimize')
  }

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSendMessage()
    }
  }

  const handleNewChat = () => {
    setMessages([])
    setTaskItems([])
    setTaskCartOpen(false)
    localStorage.removeItem('packing-optimizer-chat-messages')
    localStorage.removeItem('packing-optimizer-chat-task-manifest')
    const nextConversationId = crypto.randomUUID()
    setConversationId(nextConversationId)
    localStorage.setItem('packing-optimizer-conversation-id', nextConversationId)
    setInputValue('')
    setIsTyping(false)
    setIsWorkflowRunning(false)
    setCurrentWorkflowStep('')
  }

  const handleApplyPrompt = (promptText: string) => {
    handleSendMessage(promptText)
  }

  const handleConfirmProduct = async (product: any, quantity: number) => {
    if (isTyping) return

    const isManifest = Array.isArray(product)
    const confirmText = isManifest
      ? `Confirmed packing list: ${product.map((item: any) => `${item.quantity} Ã— ${item.part_name}`).join(', ')}.`
      : `Confirmed: Pack ${quantity} unit(s) of "${product.part_name}" (Product ID #${product.id}).`
    const userMessage: ChatMessage = {
      id: `user-${Date.now()}`,
      sender: 'user',
      text: confirmText,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    }

    setMessages((prev) => [...prev, userMessage])
    setIsWorkflowRunning(false)
    setCurrentWorkflowStep('Adding the confirmed products to your task')
    setIsTyping(true)

    try {
      const payload = {
        conversation_id: conversationId,
        user_input: isManifest
          ? {
              items: product.map((item: any) => ({ ...item, number_of_parts: item.quantity })),
              text: confirmText,
              confirmed: true,
            }
          : {
              product_id: product.id,
              part_name: product.part_name,
              quantity: quantity,
              snp: quantity,
              text: confirmText,
              confirmed: true,
            },
      }
      const result: WorkflowResult = await runWorkflow(payload, setCurrentWorkflowStep)

      if (result.task_manifest) setTaskItems(result.task_manifest)

      const assistantMessage: ChatMessage = {
        id: `assistant-${Date.now()}`,
        sender: 'assistant',
        text: result.summary || 'Unified packaging workflow completed.',
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        workflowResult: result.action === 'conversation' ? undefined : result,
        taskManifest: result.task_manifest,
        workflowStatus: result.status,
      }

      setMessages((prev) => [...prev, assistantMessage])
    } catch (err: any) {
      console.error('Unified workflow API call failed on confirm:', err)
      const errorMessage: ChatMessage = {
        id: `assistant-err-${Date.now()}`,
        sender: 'assistant',
        text: `Error optimizing confirmed product: ${err.message || 'Unknown network or backend failure'}.`,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        isError: true,
      }
      setMessages((prev) => [...prev, errorMessage])
    } finally {
      setIsTyping(false)
      setIsWorkflowRunning(false)
      setCurrentWorkflowStep('')
    }
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
            Packaging Workflow
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
              Chat with our 3-agent pipeline: gathers specifications, checks package dimensions and rated payloads, then performs 3D packing.
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
                        onConfirmProduct={handleConfirmProduct}
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
                    {msg.taskManifest && msg.taskManifest.length > 0 && (
                      <div className="mt-3 rounded-xl border border-slate-200 bg-slate-50 px-3.5 py-3">
                        <div className="text-[10px] font-bold uppercase tracking-wider text-slate-500 mb-2">Current optimization task</div>
                        <ul className="space-y-1.5 text-xs text-slate-700">
                          {msg.taskManifest.map((item, index) => (
                            <li key={`${item.product_id ?? item.name ?? item.part_name ?? 'item'}-${index}`}>
                              {item.quantity ?? item.snp ?? 1} Ã— {item.part_name ?? item.name ?? 'Part'}
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>
                </div>
              )
            })}

            {isTyping && (
              <div className="flex gap-3 sm:gap-4 items-start animate-fade-in">
                <div className="w-8 h-8 rounded-full bg-sky-600 text-white flex items-center justify-center shrink-0 text-xs font-bold shadow-2xs">AI</div>
                <div className="flex-1 rounded-2xl border border-sky-200 bg-sky-50 px-4 py-3">
                  <div className="flex items-center gap-2 text-sm font-semibold text-sky-950">
                    <span className="h-2 w-2 rounded-full bg-sky-500 animate-pulse" />
                    {currentWorkflowStep || (isWorkflowRunning ? 'Running the confirmed optimization task' : 'Working on your message')}
                  </div>
                  {isWorkflowRunning && <div className="mt-1.5 text-xs text-sky-800">The backend will update this label as each workflow stage begins.</div>}
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>
        )}
      </div>

      {/* Conversation-scoped optimization cart */}
      <div className="fixed bottom-20 right-4 z-40 flex flex-col items-end gap-2">
        {taskCartOpen && (
          <section className="w-[min(21rem,calc(100vw-2rem))] max-h-[55vh] overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-xl">
            <div className="flex items-center justify-between border-b border-slate-100 px-4 py-3">
              <div>
                <h2 className="text-sm font-bold text-slate-900">Optimization cart</h2>
                <p className="text-[11px] text-slate-500">Confirmed catalog products for this chat</p>
              </div>
              <span className="rounded-full bg-sky-100 px-2 py-1 text-xs font-bold text-sky-800">
                {taskItems.reduce((total, item) => total + (Number(item.quantity ?? item.snp) || 1), 0)}
              </span>
            </div>
            {taskItems.length ? (
              <>
                <ul className="max-h-[32vh] space-y-2 overflow-y-auto px-4 py-3">
                  {taskItems.map((item, index) => (
                    <li key={`${item.product_id ?? item.part_name ?? item.name ?? 'product'}-${index}`} className="flex items-start justify-between gap-3 text-xs">
                      <div className="min-w-0">
                        <div className="truncate font-semibold text-slate-800">{item.part_name ?? item.name ?? 'Catalog product'}</div>
                        {item.product_id != null && <div className="text-[10px] text-slate-500">Product ID #{item.product_id}</div>}
                      </div>
                      <span className="shrink-0 font-bold text-slate-700">× {Number(item.quantity ?? item.snp) || 1}</span>
                    </li>
                  ))}
                </ul>
                <div className="border-t border-slate-100 p-3">
                  <button
                    type="button"
                    onClick={handleOptimizeTask}
                    disabled={isTyping}
                    className="w-full rounded-xl bg-sky-600 px-3 py-2.5 text-xs font-bold text-white shadow-sm transition hover:bg-sky-700 disabled:cursor-not-allowed disabled:opacity-50"
                  >
                    {isWorkflowRunning ? currentWorkflowStep || 'Optimizing packing list…' : 'Optimize packing list'}
                  </button>
                </div>
              </>
            ) : (
              <p className="px-4 py-4 text-xs leading-relaxed text-slate-500">Confirmed products will appear here. Look up and confirm a catalog product to add it.</p>
            )}
          </section>
        )}
        <button
          type="button"
          onClick={() => setTaskCartOpen((open) => !open)}
          aria-label={taskCartOpen ? 'Close optimization cart' : 'Open optimization cart'}
          className="flex items-center gap-2 rounded-full border border-sky-700 bg-sky-600 px-4 py-2.5 text-xs font-bold text-white shadow-lg transition hover:bg-sky-700"
        >
          <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M2.25 3h1.5l1.8 12.1a2 2 0 002 1.7h10.9a2 2 0 002-1.6L22 8H5" />
            <circle cx="9" cy="20" r="1" /><circle cx="18" cy="20" r="1" />
          </svg>
          <span>Task cart</span>
          <span className="rounded-full bg-white/20 px-1.5 py-0.5">{taskItems.length}</span>
        </button>
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
          Connected to requirement extraction, SQLite package retrieval, deterministic 3D validation, and GPT-5.1 package recommendation.
        </p>
      </div>
    </div>
  )
}
