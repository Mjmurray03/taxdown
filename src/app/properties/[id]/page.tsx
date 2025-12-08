import { MainLayout } from '@/components/layout/main-layout';
import { PropertyDetailPage } from '@/components/properties/property-detail-page';

export default function PropertyPage({ params }: { params: { id: string } }) {
  return (
    <MainLayout>
      <PropertyDetailPage propertyId={params.id} />
    </MainLayout>
  );
}
