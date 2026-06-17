import Link from 'next/link';
import { getChats } from '@/lib/api';
import { logout } from '@/lib/auth';

export default async function Sidebar() {
  const chats = await getChats();

  return (
    <div className="w-64 h-screen bg-neutral-900 border-r border-neutral-800 flex flex-col">
      <div className="p-4 flex flex-col gap-4 border-b border-neutral-800">
        <h2 className="text-xl font-bold text-neutral-100 tracking-tight">AI Assistant</h2>
        <Link 
          href="/chat"
          className="w-full flex items-center justify-center gap-2 bg-blue-600 hover:bg-blue-500 text-white font-medium py-2 px-4 rounded-lg transition-colors"
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
          </svg>
          New Chat
        </Link>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-2">
        <p className="text-xs font-semibold text-neutral-500 uppercase tracking-wider mb-3 px-2">Recent Chats</p>
        {chats.length === 0 ? (
          <p className="text-sm text-neutral-500 px-2">No chats yet.</p>
        ) : (
          chats.map((chat: any) => (
            <Link 
              key={chat.id} 
              href={`/chat/${chat.id}`}
              className="block px-3 py-2 text-sm text-neutral-300 hover:text-neutral-100 hover:bg-neutral-800/50 rounded-lg transition-colors truncate"
            >
              {chat.title}
            </Link>
          ))
        )}
      </div>

      <div className="p-4 border-t border-neutral-800">
        <form action={logout}>
          <button type="submit" className="w-full flex items-center gap-2 text-sm text-neutral-400 hover:text-neutral-200 transition-colors px-3 py-2 rounded-lg hover:bg-neutral-800/50">
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
            </svg>
            Sign out
          </button>
        </form>
      </div>
    </div>
  );
}
