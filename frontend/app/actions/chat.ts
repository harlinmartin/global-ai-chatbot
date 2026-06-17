'use server'

import { createChat as apiCreateChat } from '@/lib/api';

export async function createChatAction(title: string) {
  try {
    const chat = await apiCreateChat(title);
    return { chat };
  } catch (error) {
    console.error("Server Action createChatAction failed", error);
    return { error: 'Failed to create chat' };
  }
}
