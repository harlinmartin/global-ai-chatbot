import ChatContainer from '@/components/chat/ChatContainer';
import { getChatMessages } from '@/lib/api';

export default async function ChatDetailPage({ params }: { params: { id: string } }) {
  const messages = await getChatMessages(params.id);

  // Map backend format to frontend format
  const initialMessages = messages.map((m: any) => ({
    id: m.id,
    role: m.role,
    content: m.content,
  }));

  return <ChatContainer initialMessages={initialMessages} chatId={params.id} />;
}
