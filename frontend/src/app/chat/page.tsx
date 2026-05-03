import dynamic from 'next/dynamic';

const ChatClient = dynamic(() => import('./ChatClient'), { ssr: false });

export default function ChatPage() {
  return <ChatClient />;
}

