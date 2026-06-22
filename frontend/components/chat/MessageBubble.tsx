"use client";
import { motion } from "framer-motion";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import type { Message } from "@/hooks/useStream";

interface Props {
  message: Message;
}

export default function MessageBubble({ message }: Props) {
  const isUser = message.role === "user";

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.25, ease: "easeOut" }}
      className={`flex gap-3 px-4 ${isUser ? "justify-end" : "justify-start"}`}
    >
      {/* AI Avatar */}
      {!isUser && (
        <div
          className="w-8 h-8 rounded-lg flex items-center justify-center text-sm flex-shrink-0 mt-1"
          style={{
            background: "linear-gradient(135deg, #6366f1, #8b5cf6)",
          }}
        >
          ✦
        </div>
      )}

      {/* Bubble */}
      <div
        className="max-w-[75%] rounded-2xl px-4 py-3 text-sm leading-relaxed"
        style={
          isUser
            ? {
                background: "linear-gradient(135deg, #6366f1, #7c3aed)",
                color: "#fff",
                borderBottomRightRadius: "4px",
              }
            : {
                background: "var(--bg-elevated)",
                border: "1px solid var(--border)",
                color: "var(--text-primary)",
                borderBottomLeftRadius: "4px",
              }
        }
      >
        {isUser ? (
          <div className="flex flex-col gap-2">
            {message.image_base64 && (
              <img 
                src={`data:image/jpeg;base64,${message.image_base64}`} 
                alt="Uploaded by user" 
                className="w-full max-w-sm rounded-lg object-contain"
              />
            )}
            {message.content && <p className="whitespace-pre-wrap">{message.content}</p>}
          </div>
        ) : (
          <div
            className={`prose-ai ${message.isStreaming && message.content ? "streaming-cursor" : ""}`}
          >
            {message.content ? (
              <ReactMarkdown remarkPlugins={[remarkGfm]}>
                {message.content}
              </ReactMarkdown>
            ) : message.isStreaming ? (
              <div className="flex items-center gap-1.5 h-6 px-1">
                <span className="w-2 h-2 bg-indigo-400 rounded-full animate-bounce [animation-delay:-0.3s]"></span>
                <span className="w-2 h-2 bg-indigo-400 rounded-full animate-bounce [animation-delay:-0.15s]"></span>
                <span className="w-2 h-2 bg-indigo-400 rounded-full animate-bounce"></span>
              </div>
            ) : (
              " "
            )}
            {message.sources && message.sources.length > 0 && (
              <div className="mt-4 pt-3 border-t border-[var(--border)]">
                <p className="text-xs text-[var(--text-secondary)] mb-2 font-medium uppercase tracking-wider">Sources</p>
                <div className="flex flex-wrap gap-2">
                  {message.sources.map((source, i) => (
                    source.type === "url" ? (
                      <a key={i} href={source.name} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-[var(--bg-card)] border border-[var(--border)] text-xs text-indigo-400 hover:text-indigo-300 hover:border-indigo-500/50 transition-colors">
                        <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1" /></svg>
                        <span className="truncate max-w-[150px]">{source.name.replace(/^https?:\/\//, '')}</span>
                      </a>
                    ) : (
                      <span key={i} className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-[var(--bg-card)] border border-[var(--border)] text-xs text-[var(--text-secondary)]">
                        <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z" /></svg>
                        <span className="truncate max-w-[150px]">{source.name}</span>
                        {source.page != null && <span className="text-[var(--text-tertiary,#9ca3af)] flex-shrink-0">· p.{source.page}</span>}
                      </span>
                    )
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      {/* User Avatar */}
      {isUser && (
        <div
          className="w-8 h-8 rounded-lg flex items-center justify-center text-xs font-bold flex-shrink-0 mt-1"
          style={{
            background: "var(--bg-elevated)",
            border: "1px solid var(--border)",
            color: "var(--text-secondary)",
          }}
        >
          U
        </div>
      )}
    </motion.div>
  );
}
