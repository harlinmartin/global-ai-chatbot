"use client";
import { useCallback } from "react";
import { useChat } from "@/hooks/useChat";
import ChatWindow from "@/components/chat/ChatWindow";
import InputBar from "@/components/chat/InputBar";
import AIProcessPanel from "@/components/chat/AIProcessPanel";

export default function ChatPage() {
  const { messages, steps, isLoading, sendMessage, clearChat } = useChat();

  const handlePromptClick = useCallback(
    (prompt: string) => {
      sendMessage(prompt);
    },
    [sendMessage]
  );

  return (
    <div
      className="flex flex-col h-screen"
      style={{ background: "var(--bg-base)" }}
    >
      {/* Header */}
      <header
        className="flex items-center justify-between px-5 py-3 border-b flex-shrink-0"
        style={{
          borderColor: "var(--border)",
          background: "var(--bg-surface)",
        }}
      >
        <div className="flex items-center gap-3">
          <div
            className="w-7 h-7 rounded-lg flex items-center justify-center text-sm"
            style={{
              background: "linear-gradient(135deg, #6366f1, #8b5cf6)",
            }}
          >
            ✦
          </div>
          <span
            className="font-semibold text-sm tracking-tight"
            style={{ color: "var(--text-primary)" }}
          >
            AI Assistant
          </span>
          <span
            className="text-xs px-2 py-0.5 rounded-full"
            style={{
              background: "var(--accent-glow)",
              color: "var(--accent)",
              border: "1px solid rgba(99,102,241,0.3)",
            }}
          >
            Groq · Llama 3.1
          </span>
        </div>

        <button
          onClick={clearChat}
          className="text-xs px-3 py-1.5 rounded-lg transition-all duration-150"
          style={{
            color: "var(--text-muted)",
            border: "1px solid var(--border)",
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.color = "var(--text-primary)";
            e.currentTarget.style.borderColor = "var(--border-strong)";
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.color = "var(--text-muted)";
            e.currentTarget.style.borderColor = "var(--border)";
          }}
        >
          New chat
        </button>
      </header>

      {/* Messages */}
      <ChatWindow messages={messages} onPromptClick={handlePromptClick} />

      {/* AI Process Panel */}
      <AIProcessPanel steps={steps} visible={isLoading} />

      {/* Input */}
      <InputBar onSend={sendMessage} disabled={isLoading} />
    </div>
  );
}
