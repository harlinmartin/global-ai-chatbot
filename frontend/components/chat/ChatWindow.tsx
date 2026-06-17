"use client";
import { useEffect, useRef } from "react";
import MessageBubble from "./MessageBubble";
import type { Message } from "@/hooks/useStream";

const WELCOME_PROMPTS = [
  "How does this AI assistant work?",
  "What can you help me with?",
  "Summarize a topic for me",
  "Help me write something",
];

interface Props {
  messages: Message[];
  onPromptClick: (prompt: string) => void;
}

export default function ChatWindow({ messages, onPromptClick }: Props) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  if (messages.length === 0) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center px-6 pb-8">
        {/* Logo */}
        <div
          className="w-16 h-16 rounded-2xl flex items-center justify-center text-3xl mb-6"
          style={{
            background: "linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%)",
            boxShadow: "0 8px 32px rgba(99, 102, 241, 0.3)",
          }}
        >
          ✦
        </div>

        <h1
          className="text-2xl font-semibold mb-2 text-center"
          style={{ color: "var(--text-primary)" }}
        >
          How can I help you today?
        </h1>
        <p
          className="text-sm text-center mb-8 max-w-sm"
          style={{ color: "var(--text-muted)" }}
        >
          Ask me anything — I can answer questions, explain concepts, write
          content, and more.
        </p>

        {/* Example prompts */}
        <div className="grid grid-cols-2 gap-2 w-full max-w-md">
          {WELCOME_PROMPTS.map((prompt) => (
            <button
              key={prompt}
              onClick={() => onPromptClick(prompt)}
              className="text-left px-4 py-3 rounded-xl text-sm transition-all duration-150"
              style={{
                background: "var(--bg-elevated)",
                border: "1px solid var(--border)",
                color: "var(--text-secondary)",
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.borderColor = "var(--accent)";
                e.currentTarget.style.color = "var(--text-primary)";
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.borderColor = "var(--border)";
                e.currentTarget.style.color = "var(--text-secondary)";
              }}
            >
              {prompt}
            </button>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-y-auto py-6 flex flex-col gap-5">
      {messages.map((msg) => (
        <MessageBubble key={msg.id} message={msg} />
      ))}
      <div ref={bottomRef} />
    </div>
  );
}
