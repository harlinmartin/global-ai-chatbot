import { NextRequest } from "next/server";
import { cookies } from "next/headers";

export async function POST(req: NextRequest) {
  const body = await req.json();
  const cookieStore = await cookies();
  const token = cookieStore.get("token")?.value;

  const backendRes = await fetch("http://localhost:8001/api/chat/stream", {
    method: "POST",
    headers: { 
      "Content-Type": "application/json",
      ...(token ? { "Authorization": `Bearer ${token}` } : {})
    },
    body: JSON.stringify(body),
  });

  // Stream the SSE response straight through to the browser
  return new Response(backendRes.body, {
    headers: {
      "Content-Type": "text/event-stream",
      "Cache-Control": "no-cache",
      Connection: "keep-alive",
      "X-Accel-Buffering": "no",
    },
  });
}
