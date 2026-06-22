"use client";
import { useState, useRef, useEffect, KeyboardEvent } from "react";

interface Props {
  onSend: (msg: string, imageBase64?: string) => void;
  disabled: boolean;
  isLoading?: boolean;
  onStop?: () => void;
}

export default function InputBar({ onSend, disabled, isLoading, onStop }: Props) {
  const [value, setValue] = useState("");
  const [imageBase64, setImageBase64] = useState<string | null>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Auto-resize textarea
  useEffect(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = Math.min(el.scrollHeight, 180) + "px";
  }, [value]);

  const handleSend = () => {
    const trimmed = value.trim();
    if ((!trimmed && !imageBase64) || disabled) return;
    onSend(trimmed, imageBase64 || undefined);
    setValue("");
    setImageBase64(null);
    if (textareaRef.current) textareaRef.current.style.height = "auto";
    if (fileInputRef.current) fileInputRef.current.value = "";
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    // Must be image
    if (!file.type.startsWith("image/")) return;

    const reader = new FileReader();
    reader.onload = (event) => {
      const result = event.target?.result as string;
      // Result is data:image/jpeg;base64,..... we want the base64 part
      const base64 = result.split(",")[1];
      setImageBase64(base64);
    };
    reader.readAsDataURL(file);
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
        className="flex flex-col gap-2 rounded-2xl px-4 py-3 transition-all duration-150"
        style={{
          background: "var(--bg-elevated)",
          border: "1px solid var(--border-strong)",
        }}
        onFocusCapture={(e) => {
          (e.currentTarget as HTMLDivElement).style.borderColor = "var(--accent)";
          (e.currentTarget as HTMLDivElement).style.boxShadow = "0 0 0 3px var(--accent-glow)";
        }}
        onBlurCapture={(e) => {
          (e.currentTarget as HTMLDivElement).style.borderColor = "var(--border-strong)";
          (e.currentTarget as HTMLDivElement).style.boxShadow = "none";
        }}
      >
        {imageBase64 && (
          <div className="relative inline-block w-16 h-16 rounded-lg overflow-hidden border border-neutral-700/50 mt-1">
            <img src={`data:image/jpeg;base64,${imageBase64}`} alt="Upload preview" className="w-full h-full object-cover" />
            <button
              onClick={() => setImageBase64(null)}
              className="absolute top-1 right-1 bg-black/60 text-white rounded-full w-5 h-5 flex items-center justify-center text-xs hover:bg-black"
            >
              ×
            </button>
          </div>
        )}
        <div className="flex items-end gap-3 w-full">
          <input 
            type="file" 
            ref={fileInputRef} 
            onChange={handleFileChange} 
            accept="image/*" 
            className="hidden" 
          />
          <button
            onClick={() => fileInputRef.current?.click()}
            disabled={disabled}
            className="flex-shrink-0 mb-0.5 text-neutral-400 hover:text-neutral-200 transition-colors"
            title="Attach image"
          >
            <svg width="20" height="20" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M15.172 7l-6.586 6.586a2 2 0 102.828 2.828l6.414-6.586a4 4 0 00-5.656-5.656l-6.415 6.585a6 6 0 108.486 8.486L20.5 13" />
            </svg>
          </button>
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
        {isLoading ? (
          <button
            onClick={onStop}
            className="flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center transition-all duration-150 mb-0.5"
            style={{ backgroundColor: "var(--text-primary)", color: "var(--bg-elevated)" }}
            title="Stop generating"
          >
            <svg width="12" height="12" viewBox="0 0 24 24" fill="currentColor">
              <rect x="6" y="6" width="12" height="12" rx="2" />
            </svg>
          </button>
        ) : (
          <button
            onClick={handleSend}
            disabled={disabled || (!value.trim() && !imageBase64)}
            className="flex-shrink-0 w-8 h-8 rounded-xl flex items-center justify-center transition-all duration-150 mb-0.5"
            style={{
              background:
                disabled || (!value.trim() && !imageBase64)
                  ? "var(--bg-hover)"
                  : "linear-gradient(135deg, #6366f1, #7c3aed)",
              color: disabled || (!value.trim() && !imageBase64) ? "var(--text-muted)" : "#fff",
              cursor: disabled || (!value.trim() && !imageBase64) ? "not-allowed" : "pointer",
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
        )}
        </div>
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
