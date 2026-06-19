import ReactMarkdown from "react-markdown";
import { type Message } from "@/hooks/useStream";
import { Sparkles, ThumbsUp, ThumbsDown } from "lucide-react";
import { useState } from "react";

interface WidgetMessageBubbleProps {
  message: Message;
  onFeedback?: (messageId: string, feedback: 'up' | 'down') => void;
}

export default function WidgetMessageBubble({ message, onFeedback }: WidgetMessageBubbleProps) {
  const isUser = message.role === "user";
  const [feedback, setFeedback] = useState<'up' | 'down' | null>(null);

  const handleFeedback = (type: 'up' | 'down') => {
    if (feedback === type) {
      setFeedback(null); // toggle off
    } else {
      setFeedback(type);
      if (onFeedback) onFeedback(message.id, type);
    }
  };

  if (isUser) {
    return (
      <div className="flex w-full justify-end my-4 px-4">
        <div className="bg-gray-100 text-gray-900 rounded-2xl rounded-tr-sm px-4 py-3 max-w-[85%] shadow-sm text-sm">
          {message.content}
        </div>
      </div>
    );
  }

  return (
    <div className="flex w-full flex-col my-4 px-4">
      <div className="flex items-center gap-2 mb-2">
        <div className="w-6 h-6 rounded bg-purple-100 flex items-center justify-center text-purple-600">
          <Sparkles className="w-4 h-4" />
        </div>
        <span className="font-semibold text-gray-800 text-sm">AI Assistant</span>
      </div>
      
      <div className="pl-8 text-gray-700 text-sm prose prose-sm prose-p:leading-relaxed prose-pre:bg-gray-50 prose-pre:text-gray-800 max-w-none">
        <ReactMarkdown>{message.content}</ReactMarkdown>
        {message.sources && message.sources.length > 0 && (
          <div className="mt-4 pt-3 border-t border-gray-100">
            <p className="text-xs text-gray-500 mb-2 font-medium uppercase tracking-wider">Sources</p>
            <div className="flex flex-wrap gap-2">
              {message.sources.map((source, i) => (
                source.type === "url" ? (
                  <a key={i} href={source.name} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-white border border-gray-200 text-xs text-purple-600 hover:text-purple-700 hover:border-purple-300 transition-colors shadow-sm">
                    <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1" /></svg>
                    <span className="truncate max-w-[150px]">{source.name.replace(/^https?:\/\//, '')}</span>
                  </a>
                ) : (
                  <span key={i} className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-white border border-gray-200 text-xs text-gray-600 shadow-sm">
                    <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z" /></svg>
                    <span className="truncate max-w-[150px]">{source.name}</span>
                    {source.page != null && <span className="text-gray-400 flex-shrink-0">· p.{source.page}</span>}
                  </span>
                )
              ))}
            </div>
          </div>
        )}
      </div>

      {!message.isStreaming && (
        <div className="pl-8 mt-3 flex items-center gap-2">
          <button 
            onClick={() => handleFeedback('up')}
            className={`p-1.5 rounded-md transition-colors ${feedback === 'up' ? 'text-purple-600 bg-purple-50' : 'text-gray-400 hover:text-gray-600 hover:bg-gray-100'}`}
          >
            {feedback === 'up' ? <ThumbsUp className="w-4 h-4" fill="currentColor" /> : <ThumbsUp className="w-4 h-4" />}
          </button>
          <button 
            onClick={() => handleFeedback('down')}
            className={`p-1.5 rounded-md transition-colors ${feedback === 'down' ? 'text-purple-600 bg-purple-50' : 'text-gray-400 hover:text-gray-600 hover:bg-gray-100'}`}
          >
            {feedback === 'down' ? <ThumbsDown className="w-4 h-4" fill="currentColor" /> : <ThumbsDown className="w-4 h-4" />}
          </button>
        </div>
      )}
    </div>
  );
}
