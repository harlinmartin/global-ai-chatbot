import { cookies } from 'next/headers';

const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8001';

export async function fetchWithAuth(endpoint: string, options: RequestInit = {}) {
  const cookieStore = await cookies();
  const token = cookieStore.get('token')?.value;

  const headers = new Headers(options.headers);
  if (token) {
    headers.set('Authorization', `Bearer ${token}`);
  }

  const response = await fetch(`${BACKEND_URL}${endpoint}`, {
    ...options,
    headers,
  });

  return response;
}

export async function getChats() {
  const res = await fetchWithAuth('/api/chats');
  if (!res.ok) return [];
  return res.json();
}

export async function getChatMessages(chatId: string) {
  const res = await fetchWithAuth(`/api/chats/${chatId}/messages`);
  if (!res.ok) return [];
  return res.json();
}

export async function createChat(title: string, workspaceId?: string) {
  const body: any = { title };
  if (workspaceId) body.workspace_id = workspaceId;
  
  const res = await fetchWithAuth('/api/chats', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error('Failed to create chat');
  return res.json();
}

export async function deleteChat(chatId: string) {
  const res = await fetchWithAuth(`/api/chats/${chatId}`, {
    method: 'DELETE',
  });
  if (!res.ok) throw new Error('Failed to delete chat');
}

export async function getEvaluations() {
  const res = await fetchWithAuth('/api/admin/evaluations');
  if (!res.ok) throw new Error('Failed to fetch evaluations');
  return res.json();
}

export async function getMemories() {
  const res = await fetchWithAuth('/api/admin/memories');
  if (!res.ok) throw new Error('Failed to fetch memories');
  return res.json();
}

export async function deleteMemory(memoryId: string) {
  const res = await fetchWithAuth(`/api/admin/memories/${memoryId}`, {
    method: 'DELETE',
  });
  if (!res.ok) throw new Error('Failed to delete memory');
}
