"use client";
import { useState, useRef, useEffect, KeyboardEvent } from "react";

interface Props {
  onSend: (msg: string) => void;
  disabled: boolean;
}

export default function InputBar({ onSend, disabled }: Props) {
  const [value, setValue] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Auto-resize textarea
  useEffect(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = Math.min(el.scrollHeight, 180) + "px";
  }, [value]);

  const handleSend = () => {
    const trimmed = value.trim();
    if (!trimmed || disabled) return;
    onSend(trimmed);
    setValue("");
    if (textareaRef.current) textareaRef.current.style.height = "auto";
  };

  const handleKey = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div
      className="px-4 pb-4 pt-2"
    >
      <div
        className="flex items-end gap-3 rounded-2xl px-4 py-3 transition-all duration-150"
        style={{
          background: "var(--bg-elevated)",
          border: "1px solid var(--border-strong)",
        }}
        onFocusCapture={(e) => {
          (e.currentTarget as HTMLDivElement).style.borderColor =
            "var(--accent)";
          (e.currentTarget as HTMLDivElement).style.boxShadow =
            "0 0 0 3px var(--accent-glow)";
        }}
        onBlurCapture={(e) => {
          (e.currentTarget as HTMLDivElement).style.borderColor =
            "var(--border-strong)";
          (e.currentTarget as HTMLDivElement).style.boxShadow = "none";
        }}
      >
        <textarea
          ref={textareaRef}
          rows={1}
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={handleKey}
          disabled={disabled}
          placeholder={
            disabled ? "Generating response..." : "Message AI Assistant..."
          }
          className="flex-1 bg-transparent resize-none outline-none text-sm leading-relaxed py-0.5"
          style={{
            color: "var(--text-primary)",
            maxHeight: "180px",
            caretColor: "var(--accent)",
          }}
        />
        <button
          onClick={handleSend}
          disabled={disabled || !value.trim()}
          className="flex-shrink-0 w-8 h-8 rounded-xl flex items-center justify-center transition-all duration-150"
          style={{
            background:
              disabled || !value.trim()
                ? "var(--bg-hover)"
                : "linear-gradient(135deg, #6366f1, #7c3aed)",
            color: disabled || !value.trim() ? "var(--text-muted)" : "#fff",
            cursor: disabled || !value.trim() ? "not-allowed" : "pointer",
          }}
        >
          <svg
            width="14"
            height="14"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2.5"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <path d="M22 2L11 13" />
            <path d="M22 2L15 22l-4-9-9-4 20-7z" />
          </svg>
        </button>
      </div>
      <p
        className="text-center text-xs mt-2"
        style={{ color: "var(--text-muted)" }}
      >
        Press Enter to send · Shift+Enter for new line
      </p>
    </div>
  );
}
