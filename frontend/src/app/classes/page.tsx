import dynamic from 'next/dynamic';

const ClassesIndexClient = dynamic(() => import('./ClassesIndexClient'), { ssr: false });

export default function ClassesPage() {
  return <ClassesIndexClient />;
}

