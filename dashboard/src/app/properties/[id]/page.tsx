'use client';

import { useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { useQuery, useMutation } from '@tanstack/react-query';
import { MainLayout } from '@/components/layout/main-layout';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Separator } from '@/components/ui/separator';
import {
  ArrowLeft,
  Home,
  DollarSign,
  TrendingUp,
  FileText,
  AlertTriangle,
  RefreshCw,
  Download,
} from 'lucide-react';
import { propertyApi, analysisApi, appealApi, PropertyDetail, AnalysisResult, AppealPackage, APIResponse } from '@/lib/api';
import { toast } from 'sonner';

export default function PropertyDetailPage() {
  const params = useParams();
  const router = useRouter();
  const propertyId = params.id as string;

  const { data: propertyResponse, isLoading: propertyLoading, error: propertyError } = useQuery<APIResponse<PropertyDetail>>({
    queryKey: ['property', propertyId],
    queryFn: () => propertyApi.getById(propertyId),
  });

  const property = propertyResponse?.data;

  const analyzeMutation = useMutation({
    mutationFn: () => analysisApi.analyze(propertyId, { force_refresh: true }),
    onSuccess: (data) => {
      toast.success('Analysis completed successfully');
    },
    onError: (error) => {
      toast.error('Analysis failed: ' + (error instanceof Error ? error.message : 'Unknown error'));
    },
  });

  const appealMutation = useMutation({
    mutationFn: () => appealApi.generate(propertyId, 'formal'),
    onSuccess: (data) => {
      toast.success('Appeal generated successfully');
    },
    onError: (error) => {
      toast.error('Appeal generation failed: ' + (error instanceof Error ? error.message : 'Unknown error'));
    },
  });

  const formatCurrency = (value: number | null | undefined) => {
    if (value === null || value === undefined) return 'N/A';
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      maximumFractionDigits: 0,
    }).format(value);
  };

  const getRecommendationBadge = (action: string | null | undefined) => {
    if (!action) return null;
    switch (action) {
      case 'APPEAL':
        return <Badge className="bg-green-100 text-green-800">Appeal Recommended</Badge>;
      case 'MONITOR':
        return <Badge className="bg-yellow-100 text-yellow-800">Monitor</Badge>;
      default:
        return <Badge variant="secondary">No Action Needed</Badge>;
    }
  };

  // Loading state
  if (propertyLoading) {
    return (
      <MainLayout>
        <div className="space-y-6">
          <div className="flex items-center gap-4">
            <Skeleton className="h-10 w-10" />
            <div className="space-y-2">
              <Skeleton className="h-8 w-[300px]" />
              <Skeleton className="h-4 w-[200px]" />
            </div>
          </div>
          <div className="grid gap-4 md:grid-cols-3">
            {[...Array(3)].map((_, i) => (
              <Card key={i}>
                <CardHeader>
                  <Skeleton className="h-4 w-[100px]" />
                </CardHeader>
                <CardContent>
                  <Skeleton className="h-8 w-[150px]" />
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      </MainLayout>
    );
  }

  // Error state
  if (propertyError) {
    return (
      <MainLayout>
        <div className="text-center py-20">
          <AlertTriangle className="h-12 w-12 text-red-500 mx-auto mb-4" />
          <h2 className="text-2xl font-bold text-gray-900">Property Not Found</h2>
          <p className="text-gray-500 mt-2">
            {propertyError instanceof Error ? propertyError.message : 'Could not load property details'}
          </p>
          <Button onClick={() => router.back()} variant="outline" className="mt-4">
            <ArrowLeft className="h-4 w-4 mr-2" />
            Go Back
          </Button>
        </div>
      </MainLayout>
    );
  }

  if (!property) {
    return (
      <MainLayout>
        <div className="text-center py-20">
          <Home className="h-12 w-12 text-gray-400 mx-auto mb-4" />
          <h2 className="text-2xl font-bold text-gray-900">Property Not Found</h2>
          <Button onClick={() => router.back()} variant="outline" className="mt-4">
            <ArrowLeft className="h-4 w-4 mr-2" />
            Go Back
          </Button>
        </div>
      </MainLayout>
    );
  }

  return (
    <MainLayout>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-4">
            <Button variant="ghost" size="icon" onClick={() => router.back()}>
              <ArrowLeft className="h-5 w-5" />
            </Button>
            <div>
              <h1 className="text-2xl font-bold tracking-tight">{property.address || 'Unknown Address'}</h1>
              <p className="text-muted-foreground">
                Parcel ID: {property.parcel_id} | {property.city || 'Unknown City'}, {property.county || 'Benton'} County
              </p>
            </div>
          </div>
          <div className="flex gap-2">
            <Button
              variant="outline"
              onClick={() => analyzeMutation.mutate()}
              disabled={analyzeMutation.isPending}
            >
              <RefreshCw className={`h-4 w-4 mr-2 ${analyzeMutation.isPending ? 'animate-spin' : ''}`} />
              Run Analysis
            </Button>
            {property.fairness_score && property.fairness_score >= 50 && (
              <Button
                onClick={() => appealMutation.mutate()}
                disabled={appealMutation.isPending}
              >
                <FileText className="h-4 w-4 mr-2" />
                Generate Appeal
              </Button>
            )}
          </div>
        </div>

        {/* Value Cards */}
        <div className="grid gap-4 md:grid-cols-4">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Market Value</CardTitle>
              <Home className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{formatCurrency(property.total_value)}</div>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Assessed Value</CardTitle>
              <DollarSign className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{formatCurrency(property.assessed_value)}</div>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Est. Annual Tax</CardTitle>
              <DollarSign className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{formatCurrency(property.estimated_annual_tax)}</div>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Fairness Score</CardTitle>
              <TrendingUp className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">
                {property.fairness_score ? `${property.fairness_score}%` : 'Not Analyzed'}
              </div>
              {getRecommendationBadge(property.recommended_action)}
            </CardContent>
          </Card>
        </div>

        {/* Detailed Info Tabs */}
        <Tabs defaultValue="details" className="space-y-4">
          <TabsList>
            <TabsTrigger value="details">Property Details</TabsTrigger>
            <TabsTrigger value="analysis">Analysis</TabsTrigger>
            <TabsTrigger value="appeal">Appeal</TabsTrigger>
          </TabsList>

          <TabsContent value="details">
            <Card>
              <CardHeader>
                <CardTitle>Property Information</CardTitle>
              </CardHeader>
              <CardContent className="space-y-6">
                <div className="grid md:grid-cols-2 gap-6">
                  <div className="space-y-4">
                    <h4 className="font-semibold text-sm text-muted-foreground uppercase tracking-wide">Owner Information</h4>
                    <div className="space-y-2">
                      <div className="flex justify-between">
                        <span className="text-muted-foreground">Owner Name</span>
                        <span className="font-medium">{property.owner_name || 'N/A'}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-muted-foreground">Owner Address</span>
                        <span className="font-medium text-right max-w-[250px]">{property.owner_address || 'N/A'}</span>
                      </div>
                    </div>
                  </div>
                  <div className="space-y-4">
                    <h4 className="font-semibold text-sm text-muted-foreground uppercase tracking-wide">Property Characteristics</h4>
                    <div className="space-y-2">
                      <div className="flex justify-between">
                        <span className="text-muted-foreground">Property Type</span>
                        <span className="font-medium">{property.property_type || 'N/A'}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-muted-foreground">Subdivision</span>
                        <span className="font-medium">{property.subdivision || 'N/A'}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-muted-foreground">Tax Area (Acres)</span>
                        <span className="font-medium">{property.tax_area_acres?.toFixed(2) || 'N/A'}</span>
                      </div>
                    </div>
                  </div>
                </div>
                <Separator />
                <div className="space-y-4">
                  <h4 className="font-semibold text-sm text-muted-foreground uppercase tracking-wide">Value Breakdown</h4>
                  <div className="grid md:grid-cols-2 gap-4">
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">Land Value</span>
                      <span className="font-medium">{formatCurrency(property.land_value)}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">Improvement Value</span>
                      <span className="font-medium">{formatCurrency(property.improvement_value)}</span>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="analysis">
            <Card>
              <CardHeader>
                <CardTitle>Assessment Analysis</CardTitle>
                <CardDescription>
                  Fairness analysis comparing this property to similar properties
                </CardDescription>
              </CardHeader>
              <CardContent>
                {property.fairness_score ? (
                  <div className="space-y-6">
                    <div className="grid md:grid-cols-3 gap-4">
                      <div className="text-center p-4 bg-gray-50 rounded-lg">
                        <div className="text-3xl font-bold text-blue-600">{property.fairness_score}%</div>
                        <div className="text-sm text-muted-foreground">Fairness Score</div>
                      </div>
                      <div className="text-center p-4 bg-gray-50 rounded-lg">
                        <div className="text-3xl font-bold text-green-600">{formatCurrency(property.estimated_savings)}</div>
                        <div className="text-sm text-muted-foreground">Potential Savings</div>
                      </div>
                      <div className="text-center p-4 bg-gray-50 rounded-lg">
                        <div className="text-3xl font-bold">{property.recommended_action || 'N/A'}</div>
                        <div className="text-sm text-muted-foreground">Recommendation</div>
                      </div>
                    </div>
                    {property.last_analyzed && (
                      <p className="text-sm text-muted-foreground">
                        Last analyzed: {new Date(property.last_analyzed).toLocaleDateString()}
                      </p>
                    )}
                  </div>
                ) : (
                  <div className="text-center py-10">
                    <TrendingUp className="h-10 w-10 text-gray-400 mx-auto mb-4" />
                    <h3 className="text-lg font-medium text-gray-900">No Analysis Available</h3>
                    <p className="text-gray-500 mt-2">
                      Run an analysis to see fairness score and recommendations
                    </p>
                    <Button
                      onClick={() => analyzeMutation.mutate()}
                      disabled={analyzeMutation.isPending}
                      className="mt-4"
                    >
                      <RefreshCw className={`h-4 w-4 mr-2 ${analyzeMutation.isPending ? 'animate-spin' : ''}`} />
                      Run Analysis
                    </Button>
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="appeal">
            <Card>
              <CardHeader>
                <CardTitle>Appeal Generation</CardTitle>
                <CardDescription>
                  Generate a formal appeal letter for this property
                </CardDescription>
              </CardHeader>
              <CardContent>
                {appealMutation.data?.data ? (
                  <div className="space-y-4">
                    <div className="p-4 bg-green-50 rounded-lg">
                      <h4 className="font-semibold text-green-800">Appeal Generated Successfully</h4>
                      <p className="text-sm text-green-700 mt-1">
                        Your appeal letter has been generated and is ready for download.
                      </p>
                    </div>
                    <div className="prose max-w-none">
                      <pre className="whitespace-pre-wrap text-sm bg-gray-50 p-4 rounded-lg">
                        {appealMutation.data.data.appeal_letter}
                      </pre>
                    </div>
                  </div>
                ) : property.fairness_score && property.fairness_score >= 50 ? (
                  <div className="text-center py-10">
                    <FileText className="h-10 w-10 text-blue-500 mx-auto mb-4" />
                    <h3 className="text-lg font-medium text-gray-900">Property Qualifies for Appeal</h3>
                    <p className="text-gray-500 mt-2">
                      Based on the analysis, this property may benefit from an appeal.
                    </p>
                    <Button
                      onClick={() => appealMutation.mutate()}
                      disabled={appealMutation.isPending}
                      className="mt-4"
                    >
                      <FileText className="h-4 w-4 mr-2" />
                      {appealMutation.isPending ? 'Generating...' : 'Generate Appeal Letter'}
                    </Button>
                  </div>
                ) : (
                  <div className="text-center py-10">
                    <AlertTriangle className="h-10 w-10 text-yellow-500 mx-auto mb-4" />
                    <h3 className="text-lg font-medium text-gray-900">Appeal Not Recommended</h3>
                    <p className="text-gray-500 mt-2">
                      {property.fairness_score
                        ? 'The fairness score is below 50%, indicating the assessment is fair.'
                        : 'Run an analysis first to determine if an appeal is recommended.'}
                    </p>
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </div>
    </MainLayout>
  );
}
