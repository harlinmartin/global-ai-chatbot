"use client";

import { useSearchParams } from 'next/navigation';
import { useState, useCallback, useRef, useEffect } from 'react';
import { type Message, type StatusStep } from '@/hooks/useStream';
import ChatWindow from '@/components/chat/ChatWindow';
import InputBar from '@/components/chat/InputBar';
import AIProcessPanel from '@/components/chat/AIProcessPanel';

import { Suspense } from 'react';

function EmbedChatContent() {
  const searchParams = useSearchParams();
  const apiKey = searchParams.get('api_key');
  const sessionId = searchParams.get('session_id') || Math.random().toString(36).slice(2, 10);
  
  const [messages, setMessages] = useState<Message[]>([]);
  const [steps, setSteps] = useState<StatusStep[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const abortRef = useRef(false);

  useEffect(() => {
    if (!apiKey) {
      setError("Missing api_key in URL parameters.");
    }
  }, [apiKey]);

  const updateStepState = useCallback((step: string, label: string, state: string) => {
    setSteps((prev) => {
      const existing = prev.find((s) => s.step === step);
      if (existing) {
        return prev.map((s) => s.step === step ? { ...s, state: state as StatusStep["state"] } : s);
      }
      return [...prev, { step, label, state: state as StatusStep["state"] }];
    });
  }, []);

  const sendMessage = useCallback(async (content: string) => {
    if (!content.trim() || isLoading || !apiKey) return;

    const userMsg: Message = { id: Math.random().toString(36).slice(2, 10), role: "user", content };
    const assistantId = Math.random().toString(36).slice(2, 10);

    setMessages((prev) => [...prev, userMsg, { id: assistantId, role: "assistant", content: "", isStreaming: true }]);
    setSteps([]);
    setIsLoading(true);
    abortRef.current = false;

    const history = [...messages, userMsg].map((m) => ({ role: m.role, content: m.content }));

    try {
      const BACKEND_URL = 'http://localhost:8001';
      const searchParams = new URL(window.location.href).searchParams;
      const origin = searchParams.get('origin');
      
      const response = await fetch(`${BACKEND_URL}/api/widget/stream`, {
        method: "POST",
        headers: { 
          "Content-Type": "application/json",
          "Authorization": `Bearer ${apiKey}`
        },
        body: JSON.stringify({ session_id: sessionId, messages: history, origin }),
      });

      if (!response.ok) {
        throw new Error(`Failed to connect to AI backend. Status: ${response.status} ${response.statusText}`);
      }

      const reader = response.body?.getReader();
      if (!reader) throw new Error("No response body");
      
      const decoder = new TextDecoder();
      let buffer = "";
      let currentEvent = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() ?? "";

        for (const line of lines) {
          const trimmed = line.trim();
          if (trimmed.startsWith("event:")) {
            currentEvent = trimmed.slice(6).trim();
          } else if (trimmed.startsWith("data:")) {
            try {
              const data = JSON.parse(trimmed.slice(5).trim());
              if (currentEvent === "status") {
                updateStepState(data.step, data.label, data.state);
              } else if (currentEvent === "token") {
                if (abortRef.current) break;
                setMessages((prev) => prev.map((m) => m.id === assistantId ? { ...m, content: m.content + data.token } : m));
              } else if (currentEvent === "done") {
                setMessages((prev) => prev.map((m) => m.id === assistantId ? { ...m, isStreaming: false } : m));
                setSteps([]);
                setIsLoading(false);
              } else if (currentEvent === "error") {
                setMessages((prev) => prev.map((m) => m.id === assistantId ? { ...m, content: `⚠️ Error: ${data.message}`, isStreaming: false } : m));
                setSteps([]);
                setIsLoading(false);
              }
            } catch {
              // ignore malformed
            }
          }
        }
      }
    } catch (err: any) {
      setMessages((prev) => prev.map((m) => m.id === assistantId ? { ...m, content: `⚠️ Error: ${err.message}`, isStreaming: false } : m));
      setSteps([]);
      setIsLoading(false);
    }
  }, [messages, isLoading, apiKey, sessionId, updateStepState]);

  if (error) {
    return <div className="p-4 text-red-500 bg-neutral-950 h-screen">{error}</div>;
  }

  return (
    <div className="flex flex-col h-screen w-full" style={{ background: "transparent" }}>
      <ChatWindow messages={messages} onPromptClick={sendMessage} />
      <AIProcessPanel steps={steps} visible={isLoading} />
      <InputBar onSend={sendMessage} disabled={isLoading} />
    </div>
  );
}

export default function EmbedChatPage() {
  return (
    <Suspense fallback={<div className="p-4 bg-neutral-950 h-screen text-neutral-400">Loading chat...</div>}>
      <EmbedChatContent />
    </Suspense>
  );
}
