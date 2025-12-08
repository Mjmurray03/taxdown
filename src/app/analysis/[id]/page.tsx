import { MainLayout } from '@/components/layout/main-layout';
import { AnalysisPage } from '@/components/analysis/analysis-page';

export default function AnalysisRoute({ params }: { params: { id: string } }) {
  return (
    <MainLayout>
      <AnalysisPage propertyId={params.id} />
    </MainLayout>
  );
}
