"use client";
import { useState, useCallback } from "react";
import { useChat } from "@/hooks/useChat";
import { type Message } from "@/hooks/useStream";
import ChatWindow from "@/components/chat/ChatWindow";
import InputBar from "@/components/chat/InputBar";
import AIProcessPanel from "@/components/chat/AIProcessPanel";

interface ChatContainerProps {
  initialMessages?: Message[];
  chatId?: string;
}

export default function ChatContainer({ initialMessages = [], chatId }: ChatContainerProps) {
  const [provider, setProvider] = useState<string>("groq");
  const { messages, steps, isLoading, sendMessage, clearChat } = useChat(initialMessages, chatId, provider);

  const handlePromptClick = useCallback(
    (prompt: string) => {
      sendMessage(prompt);
    },
    [sendMessage]
  );

  return (
    <div
      className="flex flex-col h-full w-full"
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
          <select
            value={provider}
            onChange={(e) => setProvider(e.target.value)}
            className="text-xs px-2 py-0.5 rounded-full cursor-pointer focus:outline-none focus:ring-2 focus:ring-blue-500/50"
            style={{
              background: "var(--accent-glow)",
              color: "var(--accent)",
              border: "1px solid rgba(99,102,241,0.3)",
              appearance: "none",
            }}
          >
            <option value="groq">Groq · Llama 3.1</option>
            <option value="ollama">Ollama · Local</option>
          </select>
        </div>

        {!chatId && (
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
            Clear chat
          </button>
        )}
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
