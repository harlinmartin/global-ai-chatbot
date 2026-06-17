import Sidebar from '@/components/Sidebar';
import { cookies } from 'next/headers';
import { redirect } from 'next/navigation';

export default async function ChatLayout({ children }: { children: React.ReactNode }) {
  const cookieStore = await cookies();
  const token = cookieStore.get('token');

  if (!token) {
    redirect('/login');
  }

  return (
    <div className="flex h-screen bg-neutral-950 overflow-hidden">
      <Sidebar />
      <div className="flex-1 flex flex-col min-w-0">
        {children}
      </div>
    </div>
  );
}
