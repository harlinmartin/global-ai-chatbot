"use client";
import { useState, useCallback, useRef } from "react";
import { streamChat, type Message, type StatusStep } from "./useStream";

function uid() {
  return Math.random().toString(36).slice(2, 10);
}

export function useChat(initialMessages: Message[] = [], chatId?: string, provider?: string) {
  const [messages, setMessages] = useState<Message[]>(initialMessages);
  const [steps, setSteps] = useState<StatusStep[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const abortRef = useRef(false);
  const abortControllerRef = useRef<AbortController | null>(null);

  const updateStepState = useCallback(
    (step: string, label: string, state: string) => {
      setSteps((prev) => {
        const existing = prev.find((s) => s.step === step);
        if (existing) {
          return prev.map((s) =>
            s.step === step ? { ...s, state: state as StatusStep["state"] } : s
          );
        }
        return [...prev, { step, label, state: state as StatusStep["state"] }];
      });
    },
    []
  );

  const sendMessage = useCallback(
    async (content: string, imageBase64?: string) => {
      if ((!content.trim() && !imageBase64) || isLoading) return;

      const userMsg: Message = { id: uid(), role: "user", content, image_base64: imageBase64 };
      const assistantId = uid();

      setMessages((prev) => [
        ...prev,
        userMsg,
        { id: assistantId, role: "assistant", content: "", isStreaming: true },
      ]);
      setSteps([]);
      setIsLoading(true);
      abortRef.current = false;
      abortControllerRef.current = new AbortController();

      const history = [...messages, userMsg].map((m) => ({
        role: m.role,
        content: m.content,
        image_base64: m.image_base64,
      }));

      let currentChatId = chatId;
      if (!currentChatId) {
        try {
          const { createChatAction } = await import("@/app/actions/chat");
          const title = content.slice(0, 40) + (content.length > 40 ? "..." : "");
          const result = await createChatAction(title);
          if (result.chat) {
            currentChatId = result.chat.id;
            window.history.replaceState(null, '', `/chat/${currentChatId}`);
          } else {
            console.error(result.error);
          }
        } catch (e) {
          console.error("Failed to create chat", e);
        }
      }

      await streamChat(
        history,
        {
          onStatus: (step, label, state) => updateStepState(step, label, state),
          onToken: (token) => {
            if (abortRef.current) return;
            setMessages((prev) =>
              prev.map((m) =>
                m.id === assistantId
                  ? { ...m, content: m.content + token }
                  : m
              )
            );
          },
          onDone: (sources) => {
            setMessages((prev) =>
              prev.map((m) =>
                m.id === assistantId ? { ...m, isStreaming: false, sources } : m
              )
            );
            setSteps([]);
            setIsLoading(false);
          },
          onError: (msg) => {
            if (abortRef.current) return;
            setMessages((prev) =>
              prev.map((m) =>
                m.id === assistantId
                  ? {
                      ...m,
                      content: `⚠️ Error: ${msg}`,
                      isStreaming: false,
                    }
                  : m
              )
            );
            setSteps([]);
            setIsLoading(false);
          },
        },
        currentChatId,
        provider,
        abortControllerRef.current.signal
      );
    },
    [messages, isLoading, updateStepState, provider]
  );

  const clearChat = useCallback(() => {
    abortRef.current = true;
    if (abortControllerRef.current) abortControllerRef.current.abort();
    setMessages([]);
    setSteps([]);
    setIsLoading(false);
  }, []);

  const stopChat = useCallback(() => {
    abortRef.current = true;
    if (abortControllerRef.current) abortControllerRef.current.abort();
    setMessages((prev) =>
      prev.map((m) =>
        m.isStreaming ? { ...m, isStreaming: false } : m
      )
    );
    setSteps([]);
    setIsLoading(false);
  }, []);

  return { messages, steps, isLoading, sendMessage, clearChat, stopChat };
}
