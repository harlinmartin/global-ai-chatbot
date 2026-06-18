import ChatContainer from '@/components/chat/ChatContainer';
import { getChatMessages } from '@/lib/api';

export default async function ChatDetailPage({ params }: { params: { id: string } }) {
  const messages = await getChatMessages(params.id);

  // Map backend format to frontend format. Sources are persisted in the
  // message metadata so citation cards survive a refresh / history reload.
  const initialMessages = messages.map((m: any) => ({
    id: m.id,
    role: m.role,
    content: m.content,
    sources: (m.metadata_ ?? m.metadata)?.sources,
  }));

  return <ChatContainer initialMessages={initialMessages} chatId={params.id} />;
}
