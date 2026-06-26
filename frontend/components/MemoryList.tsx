"use client";
import { useState } from "react";
import { deleteMemoryAction } from "@/app/dashboard/memory/actions";

interface Memory {
  id: string;
  fact: string;
  created_at: string;
}

interface Props {
  initialMemories: Memory[];
}

export default function MemoryList({ initialMemories }: Props) {
  const [memories, setMemories] = useState<Memory[]>(initialMemories);
  const [isDeleting, setIsDeleting] = useState<string | null>(null);

  const handleDelete = async (id: string) => {
    try {
      setIsDeleting(id);
      await deleteMemoryAction(id);
      setMemories(prev => prev.filter(m => m.id !== id));
    } catch (e) {
      console.error(e);
      alert("Failed to delete memory.");
    } finally {
      setIsDeleting(null);
    }
  };

  if (memories.length === 0) {
    return (
      <div className="text-center py-12">
        <div className="w-16 h-16 mx-auto mb-4 bg-neutral-800 rounded-full flex items-center justify-center">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" className="text-neutral-500" strokeWidth="2">
            <path d="M12 22C17.5228 22 22 17.5228 22 12C22 6.47715 17.5228 2 12 2C6.47715 2 2 6.47715 2 12C2 17.5228 6.47715 22 12 22Z" />
            <path d="M12 8V12L15 15" />
          </svg>
        </div>
        <h3 className="text-lg font-medium text-white mb-2">No memories yet</h3>
        <p className="text-neutral-400 max-w-sm mx-auto text-sm">
          The AI will automatically learn facts about you and your workspace as you chat with it. Check back later!
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {memories.map((memory) => (
        <div key={memory.id} className="flex items-center justify-between bg-neutral-800/50 p-4 rounded-xl border border-neutral-700/50 hover:border-neutral-600 transition-colors">
          <div className="flex-1 pr-4">
            <p className="text-neutral-200">{memory.fact}</p>
            <p className="text-xs text-neutral-500 mt-1.5">
              Learned on {new Date(memory.created_at).toLocaleDateString()} at {new Date(memory.created_at).toLocaleTimeString()}
            </p>
          </div>
          <button
            onClick={() => handleDelete(memory.id)}
            disabled={isDeleting === memory.id}
            className="flex-shrink-0 w-8 h-8 flex items-center justify-center rounded-lg bg-neutral-800 hover:bg-red-500/20 text-neutral-400 hover:text-red-400 transition-all"
            title="Forget this fact"
          >
            {isDeleting === memory.id ? (
              <svg className="animate-spin w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <circle cx="12" cy="12" r="10" strokeOpacity="0.25" />
                <path d="M12 2a10 10 0 0 1 10 10" />
              </svg>
            ) : (
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M3 6h18" />
                <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
              </svg>
            )}
          </button>
        </div>
      ))}
    </div>
  );
}
