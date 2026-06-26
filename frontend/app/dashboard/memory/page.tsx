import { getMemories } from '@/lib/api';
import MemoryList from '@/components/MemoryList';

export default async function MemoryDashboardPage() {
  const data = await getMemories();

  return (
    <div className="p-8 max-w-4xl mx-auto w-full text-neutral-100">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">AI Memory</h1>
          <p className="text-neutral-400 mt-2">
            View and manage facts the AI has learned about you or your workspace across chats.
          </p>
        </div>
      </div>
      
      <div className="bg-neutral-900 border border-neutral-800 rounded-xl p-6">
        <MemoryList initialMemories={data.memories} />
      </div>
    </div>
  );
}
