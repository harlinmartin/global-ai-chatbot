export interface Source {
  name: string;
  type: string;
  page?: number;
}

export interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  isStreaming?: boolean;
  sources?: Source[];
  image_base64?: string;
}

export interface StatusStep {
  step: string;
  label: string;
  state: "pending" | "active" | "done";
}

interface StreamCallbacks {
  onStatus: (step: string, label: string, state: string) => void;
  onToken: (token: string) => void;
  onDone: (sources?: Source[]) => void;
  onError: (msg: string) => void;
}

export async function streamChat(
  messages: { role: string; content: string; image_base64?: string }[],
  callbacks: StreamCallbacks,
  chatId?: string,
  provider?: string,
  signal?: AbortSignal
) {
  try {
    const response = await fetch("/api/chat/stream", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ messages, chat_id: chatId, provider }),
      signal,
    });

    if (!response.ok || !response.body) {
      callbacks.onError("Failed to connect to AI backend.");
      return;
    }

    const reader = response.body.getReader();
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
            callbacks.onStatus(data.step, data.label, data.state);
          } else if (currentEvent === "token") {
            callbacks.onToken(data.token);
          } else if (currentEvent === "done") {
            callbacks.onDone(data.sources);
          } else if (currentEvent === "error") {
            callbacks.onError(data.message ?? "Unknown error");
          }
        } catch {
          // ignore malformed lines
        }
      }
    }
  }
  } catch (error: any) {
    if (error.name === "AbortError") {
      // Chat was intentionally stopped by the user, not an error
      return;
    }
    callbacks.onError(error.message || "Unknown error occurred");
  }
}
