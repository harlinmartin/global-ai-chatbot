import { Sparkles, RotateCw } from "lucide-react";

interface WidgetHeaderProps {
  activeTab: 'chat' | 'history';
  setActiveTab: (tab: 'chat' | 'history') => void;
  onNewChat: () => void;
  status: 'active' | 'closed';
  historyCount: number;
}

export default function WidgetHeader({ activeTab, setActiveTab, onNewChat, status, historyCount }: WidgetHeaderProps) {
  return (
    <div className="flex flex-col w-full bg-white border-b border-gray-200">
      {/* Top Branding Row */}
      <div className="flex items-center justify-between px-4 py-3">
        <div className="flex items-center gap-2">
          <div className="bg-purple-600 text-white p-1.5 rounded-md">
            <Sparkles className="w-5 h-5" />
          </div>
          <span className="font-semibold text-gray-800 tracking-tight">Ask AI</span>
        </div>
        
        <div className="flex items-center gap-2">
          {status === 'active' && (
            <span className="flex items-center gap-1 text-xs text-green-600 bg-green-50 px-2 py-1 rounded-full font-medium">
              <span className="w-1.5 h-1.5 rounded-full bg-green-500 animate-pulse"></span>
              Active
            </span>
          )}
          {status === 'closed' && (
            <span className="flex items-center gap-1 text-xs text-gray-500 bg-gray-100 px-2 py-1 rounded-full font-medium">
              <span className="w-1.5 h-1.5 rounded-full bg-gray-400"></span>
              Closed
            </span>
          )}
          <button 
            onClick={onNewChat}
            className="p-1.5 text-gray-500 hover:text-purple-600 hover:bg-purple-50 rounded-md transition-colors"
            title="Start new chat"
          >
            <RotateCw className="w-5 h-5" />
          </button>
        </div>
      </div>

      {/* Tabs Row */}
      <div className="flex px-4 gap-6">
        <button
          onClick={() => setActiveTab('chat')}
          className={`pb-3 text-sm font-medium transition-colors relative ${
            activeTab === 'chat' ? 'text-purple-600' : 'text-gray-500 hover:text-gray-800'
          }`}
        >
          Chat
          {activeTab === 'chat' && (
            <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-purple-600 rounded-t-full"></div>
          )}
        </button>
        
        <button
          onClick={() => setActiveTab('history')}
          className={`pb-3 text-sm font-medium transition-colors relative flex items-center gap-1.5 ${
            activeTab === 'history' ? 'text-purple-600' : 'text-gray-500 hover:text-gray-800'
          }`}
        >
          History
          {historyCount > 0 && (
            <span className="bg-pink-500 text-white text-[10px] font-bold px-1.5 py-0.5 rounded-full leading-none">
              {historyCount}
            </span>
          )}
          {activeTab === 'history' && (
            <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-purple-600 rounded-t-full"></div>
          )}
        </button>
      </div>
    </div>
  );
}
