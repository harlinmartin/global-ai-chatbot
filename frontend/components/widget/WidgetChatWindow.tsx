import { useEffect, useRef } from "react";
import { type Message } from "@/hooks/useStream";
import WidgetMessageBubble from "./WidgetMessageBubble";
import { Sparkles } from "lucide-react";

interface WidgetChatWindowProps {
  messages: Message[];
  status: 'active' | 'closed';
  onNewChat: () => void;
  onFeedback: (messageId: string, type: 'up' | 'down') => void;
}

export default function WidgetChatWindow({ messages, status, onNewChat, onFeedback }: WidgetChatWindowProps) {
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  if (messages.length === 0) {
    return (
      <div className="flex-1 overflow-y-auto bg-white flex flex-col items-center justify-center p-6 text-center">
        <div className="w-16 h-16 bg-purple-100 rounded-full flex items-center justify-center text-purple-600 mb-4">
          <Sparkles className="w-8 h-8" />
        </div>
        <h2 className="text-xl font-bold text-gray-800 mb-2">How can I help you today?</h2>
        <p className="text-sm text-gray-500 max-w-xs">
          I am your AI assistant. Ask me anything about our products, services, or documentation.
        </p>
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-y-auto bg-white">
      <div className="flex flex-col py-4">
        {messages.map((m) => (
          <WidgetMessageBubble key={m.id} message={m} onFeedback={onFeedback} />
        ))}
        
        {/* End of Chat Actions */}
        {status === 'closed' && messages.length > 0 && (
          <div className="px-6 py-8 flex flex-col items-center border-t border-gray-100 mt-4 bg-gray-50">
            <div className="bg-white p-4 rounded-xl shadow-sm border border-gray-200 w-full text-center mb-6">
              <h3 className="text-sm font-semibold text-gray-800 mb-3">Help Kodee improve. How was your chat with us?</h3>
              <div className="flex justify-center gap-2">
                {[1, 2, 3, 4, 5].map((star) => (
                  <button key={star} className="text-gray-300 hover:text-yellow-400 text-2xl transition-colors">
                    ★
                  </button>
                ))}
              </div>
            </div>
            
            <button 
              onClick={onNewChat}
              className="w-full py-3 bg-purple-600 hover:bg-purple-700 text-white font-semibold rounded-xl shadow-sm transition-colors flex items-center justify-center gap-2"
            >
              <Sparkles className="w-5 h-5" />
              Start new chat
            </button>
          </div>
        )}
        <div ref={endRef} />
      </div>
    </div>
  );
}
