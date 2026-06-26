"use server";

import { deleteMemory as apiDeleteMemory } from '@/lib/api';
import { revalidatePath } from 'next/cache';

export async function deleteMemoryAction(memoryId: string) {
  await apiDeleteMemory(memoryId);
  revalidatePath('/dashboard/memory');
}
