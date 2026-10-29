import { useState, useRef, useEffect } from 'react'

interface ChatMessage {
  id: string
  sender: 'user' | 'assistant'
  text: string
  timestamp?: string
}

const QUICK_PROMPTS = [
  {
    title: 'Find standard package',
    subtitle: 'Find inventory box for 140x90x60mm steel bracket',
    prompt: 'Find a suitable inventory package for a steel bracket measuring 140x90x60mm with quantity 4.',
  },
  {
    title: 'Calculate custom box',
    subtitle: 'Compute sizing & foam padding for 12 units',
    prompt: 'Calculate custom box dimensions and recommended padding for 12 units of 180x120x80mm aluminum parts.',
  },
  {
    title: 'Padding recommendations',
    subtitle: 'Check cushion rules for fragile glass or acrylic',
    prompt: 'What padding material and clearance thickness are required for high fragility glass components?',
  },
  {
    title: '3D Container optimization',
    subtitle: 'Check loading volume efficiency and waste',
    prompt: 'How can I maximize carton volume utilization when shipping multiple mixed-size items?',
  },
]

export default function ChatbotView() {
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [inputValue, setInputValue] = useState('')
  const [isTyping, setIsTyping] = useState(false)
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

  const handleSendMessage = (textToSend?: string) => {
    const text = (textToSend ?? inputValue).trim()
    if (!text) return

    const userMessage: ChatMessage = {
      id: `user-${Date.now()}`,
      sender: 'user',
      text,
    }

    setMessages((prev) => [...prev, userMessage])
    setInputValue('')
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto'
    }
    setIsTyping(true)

    // Simulate mock assistant response (standalone UI preview)
    setTimeout(() => {
      const mockReply: ChatMessage = {
        id: `assistant-${Date.now()}`,
        sender: 'assistant',
        text: `I received your packaging requirement: "${text}".\n\nThe backend Requirement & Retrieval agents are ready to be connected to parse geometric metrics, evaluate SNP, and return matching packages.`,
      }
      setMessages((prev) => [...prev, mockReply])
      setIsTyping(false)
    }, 600)
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

  return (
    <div className="flex-1 flex flex-col h-full bg-white relative">
      {/* Top Bar (ChatGPT Style: clean, minimal, non-intrusive) */}
      <div className="h-12 border-b border-slate-100 px-4 flex items-center justify-between shrink-0 bg-white z-10">
        <div className="flex items-center gap-2">
          <span className="font-semibold text-slate-800 text-sm">
            Packing Assistant
          </span>
          <span className="inline-flex items-center gap-1 text-[11px] font-medium text-sky-700 bg-sky-50 border border-sky-200/80 px-2 py-0.5 rounded-full">
            <span className="w-1.5 h-1.5 rounded-full bg-sky-500" />
            Standalone Preview
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
          /* Empty / Welcome State (ChatGPT style) */
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
              Ask questions about custom box dimensions, padding rules, or evaluate candidate packages from inventory.
            </p>

            {/* Prompt Suggestion Cards (2x2 grid) with Subtle Hover */}
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
          /* Messages Stream (ChatGPT style) */
          <div className="max-w-3xl mx-auto w-full space-y-6 pb-6">
            {messages.map((msg) => {
              const isUser = msg.sender === 'user'

              return isUser ? (
                /* User Message (Right-aligned rounded pill) */
                <div key={msg.id} className="flex justify-end">
                  <div className="bg-slate-100 text-slate-900 rounded-3xl px-5 py-3 max-w-[80%] text-sm sm:text-base leading-relaxed whitespace-pre-wrap">
                    {msg.text}
                  </div>
                </div>
              ) : (
                /* Assistant Message (Left-aligned clean block with icon) */
                <div key={msg.id} className="flex gap-4 items-start">
                  <div className="w-8 h-8 rounded-full bg-sky-600 text-white flex items-center justify-center shrink-0 text-xs font-bold mt-0.5 shadow-2xs">
                    AI
                  </div>
                  <div className="flex-1 text-slate-800 text-sm sm:text-base leading-relaxed whitespace-pre-wrap pt-1">
                    {msg.text}
                  </div>
                </div>
              )
            })}

            {/* Assistant Typing Indicator */}
            {isTyping && (
              <div className="flex gap-4 items-center">
                <div className="w-8 h-8 rounded-full bg-sky-600 text-white flex items-center justify-center shrink-0 text-xs font-bold shadow-2xs">
                  AI
                </div>
                <div className="flex items-center gap-1.5 py-2">
                  <span className="w-2 h-2 rounded-full bg-sky-400 animate-pulse" />
                  <span
                    className="w-2 h-2 rounded-full bg-sky-400 animate-pulse"
                    style={{ animationDelay: '150ms' }}
                  />
                  <span
                    className="w-2 h-2 rounded-full bg-sky-400 animate-pulse"
                    style={{ animationDelay: '300ms' }}
                  />
                </div>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>
        )}
      </div>

      {/* ChatGPT Style Bottom Input Bar (Centered floating pill dock) */}
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
            placeholder="Message Packaging Assistant..."
            className="flex-1 bg-transparent border-0 focus:ring-0 focus:outline-none resize-none text-sm sm:text-base px-3 py-1.5 text-slate-900 placeholder-slate-400 max-h-36 leading-normal"
          />

          {/* Primary Action Circular Send Button (Up Arrow) */}
          <button
            type="submit"
            disabled={!inputValue.trim()}
            aria-label="Send message"
            className={`w-8 h-8 rounded-full flex items-center justify-center shrink-0 transition-all duration-150 cursor-pointer ${
              inputValue.trim()
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
          Packaging Assistant interface preview. Responses are currently not connected to the live agent backend.
        </p>
      </div>
    </div>
  )
}
