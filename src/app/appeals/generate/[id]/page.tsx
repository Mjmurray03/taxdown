import { MainLayout } from '@/components/layout/main-layout';
import { AppealGeneratePage } from '@/components/appeals/appeal-generate-page';

export default function AppealGenerateRoute({ params }: { params: { id: string } }) {
  return (
    <MainLayout>
      <AppealGeneratePage propertyId={params.id} />
    </MainLayout>
  );
}
