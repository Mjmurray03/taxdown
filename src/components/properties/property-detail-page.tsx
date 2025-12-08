'use client';

import { useQuery } from '@tanstack/react-query';
import Link from 'next/link';
import { propertyApi, analysisApi } from '@/lib/api';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { Separator } from '@/components/ui/separator';
import {
  ArrowLeft,
  Home,
  MapPin,
  User,
  DollarSign,
  BarChart2,
  FileText,
  Calendar,
  Ruler,
  Building
} from 'lucide-react';

interface PropertyDetailPageProps {
  propertyId: string;
}

export function PropertyDetailPage({ propertyId }: PropertyDetailPageProps) {
  const { data: propertyData, isLoading, error } = useQuery({
    queryKey: ['property', propertyId],
    queryFn: () => propertyApi.getById(propertyId),
  });

  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 0,
    }).format(value);
  };

  if (isLoading) {
    return <PropertyDetailSkeleton />;
  }

  if (error || !propertyData?.data) {
    return (
      <div className="text-center py-12">
        <p className="text-red-500 mb-4">Property not found</p>
        <Link href="/properties">
          <Button variant="outline">
            <ArrowLeft className="mr-2 h-4 w-4" /> Back to Properties
          </Button>
        </Link>
      </div>
    );
  }

  const property = propertyData.data;
  const analysis = property.latest_analysis;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Link href="/properties">
            <Button variant="ghost" size="sm">
              <ArrowLeft className="mr-2 h-4 w-4" /> Back
            </Button>
          </Link>
          <div>
            <h1 className="text-2xl font-bold">{property.address}</h1>
            <p className="text-muted-foreground">
              {property.city}, {property.state} {property.zip_code}
            </p>
          </div>
        </div>
        <div className="flex gap-2">
          <Link href={`/analysis/${propertyId}`}>
            <Button>
              <BarChart2 className="mr-2 h-4 w-4" /> Analyze
            </Button>
          </Link>
        </div>
      </div>

      {/* Main Content Grid */}
      <div className="grid gap-6 md:grid-cols-3">
        {/* Property Details */}
        <Card className="md:col-span-2">
          <CardHeader>
            <CardTitle>Property Details</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <InfoItem icon={MapPin} label="Parcel ID" value={property.parcel_id} />
              <InfoItem icon={User} label="Owner" value={property.owner_name} />
              <InfoItem icon={Building} label="Type" value={property.property_type} />
              <InfoItem icon={Calendar} label="Year Built" value={property.year_built?.toString() || 'N/A'} />
              <InfoItem icon={Ruler} label="Building" value={property.building_area_sqft ? `${property.building_area_sqft.toLocaleString()} sqft` : 'N/A'} />
              <InfoItem icon={Ruler} label="Land" value={property.land_area_sqft ? `${property.land_area_sqft.toLocaleString()} sqft` : 'N/A'} />
            </div>

            {property.subdivision && (
              <div className="pt-2">
                <p className="text-sm text-muted-foreground">Subdivision</p>
                <p className="font-medium">{property.subdivision}</p>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Valuation Card */}
        <Card>
          <CardHeader>
            <CardTitle>Valuation</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <p className="text-sm text-muted-foreground">Market Value</p>
              <p className="text-2xl font-bold">{formatCurrency(property.market_value)}</p>
            </div>
            <div>
              <p className="text-sm text-muted-foreground">Assessed Value</p>
              <p className="text-xl font-semibold">{formatCurrency(property.assessed_value)}</p>
            </div>
            <Separator />
            <div>
              <p className="text-sm text-muted-foreground">Est. Annual Tax</p>
              <p className="text-lg font-medium text-orange-600">
                {formatCurrency(property.estimated_annual_tax)}
              </p>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Analysis Card */}
      {analysis && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center justify-between">
              <span>Assessment Analysis</span>
              <Badge
                variant={analysis.recommended_action === 'APPEAL' ? 'destructive' : 'secondary'}
              >
                {analysis.recommended_action}
              </Badge>
            </CardTitle>
            <CardDescription>
              Last analyzed: {new Date(analysis.analysis_date).toLocaleDateString()}
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid gap-4 md:grid-cols-4">
              <div>
                <p className="text-sm text-muted-foreground">Fairness Score</p>
                <p className="text-2xl font-bold">
                  {analysis.fairness_score}
                  <span className="text-sm font-normal text-muted-foreground">/100</span>
                </p>
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Confidence</p>
                <p className="text-2xl font-bold">{analysis.confidence_level}%</p>
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Fair Value</p>
                <p className="text-2xl font-bold">{formatCurrency(analysis.fair_assessed_value)}</p>
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Potential Savings</p>
                <p className="text-2xl font-bold text-green-600">
                  {formatCurrency(analysis.estimated_savings)}/yr
                </p>
              </div>
            </div>

            {analysis.recommended_action === 'APPEAL' && (
              <div className="mt-4 pt-4 border-t">
                <Link href={`/appeals/generate/${propertyId}`}>
                  <Button className="w-full">
                    <FileText className="mr-2 h-4 w-4" /> Generate Appeal Letter
                  </Button>
                </Link>
              </div>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
}

function InfoItem({ icon: Icon, label, value }: { icon: any; label: string; value: string }) {
  return (
    <div className="flex items-start gap-3">
      <div className="p-2 rounded-lg bg-gray-100">
        <Icon className="h-4 w-4 text-gray-600" />
      </div>
      <div>
        <p className="text-sm text-muted-foreground">{label}</p>
        <p className="font-medium">{value}</p>
      </div>
    </div>
  );
}

function PropertyDetailSkeleton() {
  return (
    <div className="space-y-6">
      <Skeleton className="h-12 w-96" />
      <div className="grid gap-6 md:grid-cols-3">
        <Skeleton className="h-64 md:col-span-2" />
        <Skeleton className="h-64" />
      </div>
    </div>
  );
}
