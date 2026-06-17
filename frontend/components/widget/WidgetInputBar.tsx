import { useState, useRef, useEffect } from "react";
import { Paperclip, Send, X } from "lucide-react";

interface WidgetInputBarProps {
  onSend: (message: string, imageBase64?: string) => void;
  disabled: boolean;
}

export default function WidgetInputBar({ onSend, disabled }: WidgetInputBarProps) {
  const [input, setInput] = useState("");
  const [imageBase64, setImageBase64] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 150)}px`;
    }
  }, [input]);

  const handleSend = () => {
    if (!input.trim() && !imageBase64) return;
    onSend(input.trim(), imageBase64 || undefined);
    setInput("");
    setImageBase64(null);
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      if (!disabled) handleSend();
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      const reader = new FileReader();
      reader.onloadend = () => {
        setImageBase64(reader.result as string);
      };
      reader.readAsDataURL(file);
    }
  };

  return (
    <div className="flex flex-col w-full border-t border-gray-200 bg-white p-3">
      {imageBase64 && (
        <div className="relative inline-block w-16 h-16 mb-2">
          <img src={imageBase64} alt="Upload preview" className="w-full h-full object-cover rounded-md border border-gray-200" />
          <button 
            onClick={() => setImageBase64(null)}
            className="absolute -top-2 -right-2 bg-white rounded-full p-0.5 shadow-sm border border-gray-200 text-gray-500 hover:text-red-500"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      )}
      <div className="flex items-end gap-2 bg-gray-50 border border-gray-200 rounded-xl p-1 shadow-sm transition-all focus-within:ring-2 focus-within:ring-purple-500 focus-within:border-transparent">
        <button
          onClick={() => fileInputRef.current?.click()}
          className="p-2 text-gray-400 hover:text-purple-600 transition-colors shrink-0 rounded-lg hover:bg-gray-100"
          disabled={disabled}
        >
          <Paperclip className="w-5 h-5" />
          <input 
            type="file" 
            ref={fileInputRef} 
            onChange={handleFileChange} 
            accept="image/*" 
            className="hidden" 
          />
        </button>

        <textarea
          ref={textareaRef}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Ask a question..."
          className="flex-1 max-h-32 bg-transparent text-gray-800 placeholder-gray-400 focus:outline-none resize-none py-2 text-sm"
          rows={1}
          disabled={disabled}
        />

        <button
          onClick={handleSend}
          disabled={disabled || (!input.trim() && !imageBase64)}
          className="p-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors shrink-0 shadow-sm mb-0.5 mr-0.5"
        >
          <Send className="w-4 h-4" />
        </button>
      </div>
      <div className="text-center mt-2">
        <span className="text-[10px] text-gray-400">AI can make mistakes. Double-check replies.</span>
      </div>
    </div>
  );
}
