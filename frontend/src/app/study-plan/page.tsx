import dynamic from 'next/dynamic';

const StudyPlanClient = dynamic(() => import('./StudyPlanClient'), {
  ssr: false,
});

export default function StudyPlanPage() {
  return <StudyPlanClient />;
}

