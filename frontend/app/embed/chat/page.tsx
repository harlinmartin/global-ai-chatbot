"use client";

import { useSearchParams } from 'next/navigation';
import { useState, useCallback, useRef, useEffect } from 'react';
import { type Message, type StatusStep } from '@/hooks/useStream';
import WidgetHeader from '@/components/widget/WidgetHeader';
import WidgetChatWindow from '@/components/widget/WidgetChatWindow';
import WidgetInputBar from '@/components/widget/WidgetInputBar';
import AIProcessPanel from '@/components/chat/AIProcessPanel';

import { Suspense } from 'react';

function EmbedChatContent() {
  const searchParams = useSearchParams();
  const apiKey = searchParams.get('api_key');

  // Persist session ID in local storage for anonymous users
  const [sessionId, setSessionId] = useState<string>('');

  useEffect(() => {
    let storedSession = localStorage.getItem('widget_session_id');
    if (!storedSession) {
      storedSession = Math.random().toString(36).slice(2, 10);
      localStorage.setItem('widget_session_id', storedSession);
    }
    setSessionId(searchParams.get('session_id') || storedSession);
  }, [searchParams]);

  const [messages, setMessages] = useState<Message[]>([]);
  const [steps, setSteps] = useState<StatusStep[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // UI States
  const [activeTab, setActiveTab] = useState<'chat' | 'history'>('chat');
  const [status, setStatus] = useState<'active' | 'closed'>('active');
  const abortRef = useRef<AbortController | null>(null);

  const stopChat = useCallback(() => {
    if (abortRef.current) {
      abortRef.current.abort();
      abortRef.current = null;
    }
    setIsLoading(false);
    setMessages((prev) => 
      prev.map(m => m.isStreaming ? { ...m, isStreaming: false } : m)
    );
  }, []);

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

  const handleNewChat = () => {
    const newSession = Math.random().toString(36).slice(2, 10);
    localStorage.setItem('widget_session_id', newSession);
    setSessionId(newSession);
    setMessages([]);
    setSteps([]);
    setStatus('active');
    setActiveTab('chat');
  };

  const handleFeedback = async (messageId: string, type: 'up' | 'down') => {
    if (!apiKey) return;
    try {
      const BACKEND_URL = 'http://localhost:8001';
      await fetch(`${BACKEND_URL}/api/widget/messages/${messageId}/feedback`, {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${apiKey}`
        },
        body: JSON.stringify({ feedback: type }),
      });
    } catch (err) {
      console.error("Failed to submit feedback", err);
    }
  };

  const sendMessage = useCallback(async (content: string, imageBase64?: string) => {
    if (!content.trim() && !imageBase64) return;
    if (isLoading || !apiKey) return;

    // Build user message content (handling image if present)
    let userContent = content;
    if (imageBase64) {
      userContent = `[Image Attached]\n${content}`;
      // Note: Full image base64 handling for AI requires passing it in a specialized payload,
      // but for UI simulation we just prefix the text. The backend will parse the actual imageBase64 field.
    }

    const userMsg: Message = { id: Math.random().toString(36).slice(2, 10), role: "user", content: userContent };
    const assistantId = Math.random().toString(36).slice(2, 10);

    setMessages((prev) => [...prev, userMsg, { id: assistantId, role: "assistant", content: "", isStreaming: true }]);
    setSteps([]);
    setIsLoading(true);
    setStatus('active');
    abortRef.current = false;

    const history = [...messages, userMsg].map((m) => ({ role: m.role, content: m.content }));

    try {
      const BACKEND_URL = 'http://localhost:8001';
      const searchParams = new URL(window.location.href).searchParams;
      const origin = searchParams.get('origin');

      const controller = new AbortController();
      abortRef.current = controller;

      const response = await fetch(`${BACKEND_URL}/api/widget/stream`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${apiKey}`
        },
        body: JSON.stringify({
          session_id: sessionId,
          messages: history,
          origin,
          image_base64: imageBase64
        }),
        signal: controller.signal
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
                setMessages((prev) => prev.map((m) => m.id === assistantId ? { ...m, isStreaming: false, id: data.message_id || assistantId } : m));
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
    return <div className="p-4 text-red-500 bg-white h-screen flex items-center justify-center font-medium">{error}</div>;
  }

  // Ensure sessionId is loaded before rendering
  if (!sessionId) return null;

  return (
    <div className="flex flex-col h-screen w-full bg-white text-gray-900 font-sans">
      <WidgetHeader
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        onNewChat={handleNewChat}
        status={status}
        historyCount={0} // To be implemented
      />

      {activeTab === 'chat' ? (
        <>
          <WidgetChatWindow
            messages={messages}
            status={status}
            onNewChat={handleNewChat}
            onFeedback={handleFeedback}
          />
          {/* We reuse AIProcessPanel but wrap it in a light container if needed, though it's mostly self-contained */}
          <div className="px-4">
            <AIProcessPanel steps={steps} visible={isLoading} />
          </div>
          <WidgetInputBar onSend={sendMessage} onStop={stopChat} isLoading={isLoading} disabled={status === 'closed'} />
        </>
      ) : (
        <div className="flex-1 flex flex-col items-center justify-center bg-gray-50 text-gray-500 p-6 text-center">
          <p className="mb-2">Your past conversations will appear here.</p>
          <button onClick={() => setActiveTab('chat')} className="text-purple-600 font-medium hover:underline">
            Go back to Chat
          </button>
        </div>
      )}
    </div>
  );
}

export default function EmbedChatPage() {
  return (
    <Suspense fallback={<div className="flex items-center justify-center bg-white h-screen text-gray-400">Loading AI Assistant...</div>}>
      <EmbedChatContent />
    </Suspense>
  );
}
