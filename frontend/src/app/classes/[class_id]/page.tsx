import dynamic from 'next/dynamic';

const ClassDashboardClient = dynamic(() => import('./ClassDashboardClient'), { ssr: false });

export default function ClassDashboardPage({
  params,
}: {
  params: { class_id: string };
}) {
  return <ClassDashboardClient classId={params.class_id} />;
}

