"use client";

import React, { useState, useEffect, useRef } from "react";
import {
  Sparkles,
  X,
  Send,
  RotateCcw,
  AlertCircle,
  User,
  ShieldAlert,
  Loader2,
} from "lucide-react";
import { sendChatMessage, type ChatMessage } from "@/services/chat";

interface ChatDrawerProps {
  isOpen: boolean;
  onClose: () => void;
}

const INITIAL_MESSAGE: ChatMessage = {
  id: "welcome-msg",
  role: "assistant",
  content:
    "Hello! I am your **SkinWise AI Assistant** ✨\n\nI can help you understand your personalized skincare profile, evaluate routine products, explain ingredient safety, and review your latest skin analysis.\n\n*SkinWise evaluations (KEEP / CAUTION / REJECT) are backed by scientific evidence and your profile.*",
  suggested_actions: [
    "Explain my current routine",
    "Why was my product cautioned?",
    "Explain glycolic acid for my skin",
    "What does my skin analysis mean?",
  ],
};

const QUICK_STARTERS = [
  "Explain my current routine",
  "Why was my product cautioned?",
  "What is my skin type and concerns?",
  "Explain glycolic acid",
  "What does my latest skin analysis mean?",
  "When should I see a dermatologist?",
];

/**
 * Lightweight, safe Markdown renderer for chat messages.
 * Handles bold (**text**), bullet points (- / *), code (`code`), headers (###), and line breaks.
 */
function MarkdownRenderer({ text }: { text: string }) {
  const lines = text.split("\n");

  const renderInline = (str: string): React.ReactNode[] => {
    // Split by bold (**...**) and inline code (`...`)
    const parts = str.split(/(\*\*[^*]+\*\*|`[^`]+`)/g);
    return parts.map((part, idx) => {
      if (part.startsWith("**") && part.endsWith("**")) {
        return (
          <strong key={idx} className="font-semibold text-gray-900">
            {part.slice(2, -2)}
          </strong>
        );
      }
      if (part.startsWith("`") && part.endsWith("`")) {
        return (
          <code
            key={idx}
            className="px-1.5 py-0.5 rounded bg-pink-50 text-[#DE688E] text-xs font-mono"
          >
            {part.slice(1, -1)}
          </code>
        );
      }
      return <span key={idx}>{part}</span>;
    });
  };

  return (
    <div className="space-y-1.5 leading-relaxed">
      {lines.map((line, idx) => {
        const trimmed = line.trim();
        if (!trimmed) {
          return <div key={idx} className="h-2" />;
        }
        if (trimmed.startsWith("### ")) {
          return (
            <h4 key={idx} className="font-bold text-[#DE688E] text-sm mt-2 mb-1">
              {renderInline(trimmed.slice(4))}
            </h4>
          );
        }
        if (trimmed.startsWith("## ")) {
          return (
            <h3 key={idx} className="font-bold text-[#DE688E] text-base mt-2.5 mb-1">
              {renderInline(trimmed.slice(3))}
            </h3>
          );
        }
        if (trimmed.startsWith("- ") || trimmed.startsWith("* ")) {
          return (
            <div key={idx} className="flex items-start gap-2 pl-1 my-0.5">
              <span className="text-[#DE688E] font-bold text-xs mt-1.5 shrink-0">•</span>
              <span className="flex-1">{renderInline(trimmed.slice(2))}</span>
            </div>
          );
        }
        return <p key={idx}>{renderInline(trimmed)}</p>;
      })}
    </div>
  );
}

export default function ChatDrawer({ isOpen, onClose }: ChatDrawerProps) {
  const [messages, setMessages] = useState<ChatMessage[]>([INITIAL_MESSAGE]);
  const [input, setInput] = useState<string>("");
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  // Auto-scroll on new message
  useEffect(() => {
    if (isOpen) {
      messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }
  }, [messages, isOpen, loading]);

  // Focus input when opened
  useEffect(() => {
    if (isOpen) {
      setTimeout(() => inputRef.current?.focus(), 150);
    }
  }, [isOpen]);

  // Keyboard escape handler
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape" && isOpen) {
        onClose();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, onClose]);

  const handleSendMessage = async (textToSend?: string) => {
    const query = (textToSend || input).trim();
    if (!query || loading) return;

    setError(null);
    setInput("");

    const userMsg: ChatMessage = {
      id: `user-${Date.now()}`,
      role: "user",
      content: query,
      timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
    };

    // Keep history excluding the welcome message for API payload
    const updatedHistory = [...messages, userMsg];
    setMessages(updatedHistory);
    setLoading(true);

    try {
      const historyForApi = updatedHistory
        .filter((m) => m.id !== "welcome-msg")
        .slice(-6);

      const response = await sendChatMessage(query, historyForApi);

      const assistantMsg: ChatMessage = {
        id: `assistant-${Date.now()}`,
        role: "assistant",
        content: response.reply,
        suggested_actions: response.suggested_actions,
        timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
      };

      setMessages((prev) => [...prev, assistantMsg]);
    } catch (err: any) {
      console.error("[ChatDrawer] sendChatMessage error:", err);
      setError(err?.message || "Failed to reach SkinWise Assistant. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  const handleResetChat = () => {
    setMessages([INITIAL_MESSAGE]);
    setError(null);
    setInput("");
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex justify-end">
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black/40 backdrop-blur-xs transition-opacity animate-in fade-in duration-200"
        onClick={onClose}
        aria-hidden="true"
      />

      {/* Slide-over Drawer Panel */}
      <aside
        className="relative w-full sm:w-[460px] bg-[#FCFBF9] h-full shadow-2xl flex flex-col z-10 animate-in slide-in-from-right duration-300 border-l border-gray-100"
        role="dialog"
        aria-modal="true"
        aria-label="SkinWise AI Assistant"
      >
        {/* Header */}
        <header className="px-5 py-4 border-b border-gray-100 bg-white/95 backdrop-blur-sm flex items-center justify-between shrink-0">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-[#DE688E] to-[#F48FB1] text-white flex items-center justify-center shadow-xs">
              <Sparkles size={18} />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 className="font-bold text-gray-900 text-base leading-tight">
                  SkinWise Assistant
                </h3>
                <span className="text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 rounded-full bg-pink-50 text-[#DE688E] border border-pink-100">
                  AI
                </span>
              </div>
              <p className="text-xs text-gray-500">Personalized skincare & routine guide</p>
            </div>
          </div>

          <div className="flex items-center gap-1">
            <button
              type="button"
              onClick={handleResetChat}
              title="Reset conversation"
              className="p-2 rounded-lg text-gray-400 hover:text-gray-700 hover:bg-gray-100 transition cursor-pointer"
            >
              <RotateCcw size={17} />
            </button>
            <button
              type="button"
              onClick={onClose}
              title="Close assistant"
              className="p-2 rounded-lg text-gray-400 hover:text-gray-700 hover:bg-gray-100 transition cursor-pointer"
            >
              <X size={20} />
            </button>
          </div>
        </header>

        {/* Safety Disclaimer Banner */}
        <div className="bg-amber-50/80 border-b border-amber-100 px-4 py-2 flex items-start gap-2.5 text-xs text-amber-900/90 shrink-0">
          <ShieldAlert size={14} className="text-amber-600 mt-0.5 shrink-0" />
          <p className="leading-snug">
            Educational assistant only. Not medical advice. For skin conditions, please consult a dermatologist.
          </p>
        </div>

        {/* Messages Body */}
        <div className="flex-1 overflow-y-auto px-4 py-4 space-y-4">
          {messages.map((msg, index) => {
            const isUser = msg.role === "user";
            const isLast = index === messages.length - 1;

            return (
              <div
                key={msg.id || index}
                className={`flex flex-col ${isUser ? "items-end" : "items-start"}`}
              >
                <div
                  className={`max-w-[88%] rounded-2xl p-4 text-sm shadow-xs ${
                    isUser
                      ? "bg-[#DE688E] text-white rounded-br-xs font-medium"
                      : "bg-white text-gray-800 border border-gray-100/80 rounded-bl-xs"
                  }`}
                >
                  {isUser ? (
                    <p className="whitespace-pre-wrap leading-relaxed">{msg.content}</p>
                  ) : (
                    <MarkdownRenderer text={msg.content} />
                  )}
                </div>

                {/* Timestamp */}
                {msg.timestamp && (
                  <span className="text-[10px] text-gray-400 mt-1 px-1">
                    {msg.timestamp}
                  </span>
                )}

                {/* Suggested actions chips (shown under assistant messages) */}
                {!isUser && isLast && !loading && msg.suggested_actions && msg.suggested_actions.length > 0 && (
                  <div className="mt-3 w-full pl-1">
                    <p className="text-[11px] font-semibold text-gray-400 uppercase tracking-wider mb-2">
                      Suggested Questions
                    </p>
                    <div className="flex flex-wrap gap-1.5">
                      {msg.suggested_actions.map((action, aIdx) => (
                        <button
                          key={aIdx}
                          type="button"
                          onClick={() => handleSendMessage(action)}
                          className="text-xs bg-white hover:bg-pink-50 text-[#DE688E] border border-pink-200/90 rounded-full px-3 py-1.5 font-medium transition shadow-xs hover:border-[#DE688E] cursor-pointer text-left"
                        >
                          {action}
                        </button>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            );
          })}

          {/* Quick Starters (if only initial message present) */}
          {messages.length === 1 && !loading && (
            <div className="pt-2">
              <p className="text-[11px] font-semibold text-gray-400 uppercase tracking-wider mb-2 px-1">
                Frequently Asked
              </p>
              <div className="grid grid-cols-1 gap-2">
                {QUICK_STARTERS.map((starter, sIdx) => (
                  <button
                    key={sIdx}
                    type="button"
                    onClick={() => handleSendMessage(starter)}
                    className="w-full text-left text-xs bg-white hover:bg-pink-50/70 text-gray-700 hover:text-[#DE688E] border border-gray-200/80 hover:border-pink-200 rounded-xl px-3.5 py-2.5 transition flex items-center justify-between group cursor-pointer shadow-xs"
                  >
                    <span>{starter}</span>
                    <span className="text-gray-300 group-hover:text-[#DE688E] transition">→</span>
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Loading Indicator */}
          {loading && (
            <div className="flex items-center gap-2.5 bg-white border border-gray-100 rounded-2xl rounded-bl-xs p-3.5 max-w-[70%] shadow-xs text-xs text-gray-500">
              <Loader2 size={16} className="animate-spin text-[#DE688E]" />
              <span>Checking your profile and formulation data...</span>
            </div>
          )}

          {/* Error Banner with Retry */}
          {error && (
            <div className="bg-red-50 border border-red-200 rounded-xl p-3 flex items-start gap-2.5 text-xs text-red-800">
              <AlertCircle size={16} className="text-red-600 mt-0.5 shrink-0" />
              <div className="flex-1">
                <p className="font-semibold">Unable to complete response</p>
                <p className="mt-0.5">{error}</p>
                <button
                  type="button"
                  onClick={() => handleSendMessage(messages[messages.length - 1]?.content)}
                  className="mt-2 text-xs font-semibold text-red-700 hover:underline cursor-pointer"
                >
                  Retry request
                </button>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Input Footer */}
        <footer className="p-4 border-t border-gray-100 bg-white/95 backdrop-blur-sm shrink-0">
          <form
            onSubmit={(e) => {
              e.preventDefault();
              handleSendMessage();
            }}
            className="flex items-end gap-2"
          >
            <div className="flex-1 relative bg-gray-50 rounded-2xl border border-gray-200 focus-within:border-[#DE688E] focus-within:ring-2 focus-within:ring-pink-100 transition">
              <textarea
                ref={inputRef}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && !e.shiftKey) {
                    e.preventDefault();
                    handleSendMessage();
                  }
                }}
                rows={1}
                placeholder="Ask about your skin, routine, or ingredients..."
                className="w-full bg-transparent px-3.5 py-3 text-sm text-gray-800 placeholder-gray-400 focus:outline-none resize-none max-h-32 min-h-[44px]"
                disabled={loading}
              />
            </div>

            <button
              type="submit"
              disabled={loading || !input.trim()}
              aria-label="Send message"
              className="w-11 h-11 rounded-2xl bg-[#DE688E] text-white flex items-center justify-center hover:bg-[#C9547A] active:scale-95 transition disabled:opacity-40 disabled:cursor-not-allowed shadow-xs cursor-pointer shrink-0"
            >
              <Send size={18} />
            </button>
          </form>
          <p className="text-[10px] text-center text-gray-400 mt-2">
            SkinWise AI Assistant gives personalized explanations • Never overrides safety rules
          </p>
        </footer>
      </aside>
    </div>
  );
}
