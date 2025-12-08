'use client';

import { useState, Suspense } from 'react';
import { useParams, useRouter, useSearchParams } from 'next/navigation';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
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
  Copy,
  Check,
  Briefcase,
  ExternalLink,
} from 'lucide-react';
import {
  propertyApi,
  analysisApi,
  appealApi,
  PropertyDetail,
  AnalysisResult,
  AppealPackage,
  APIResponse,
} from '@/lib/api';
import { AddToPortfolioDialog } from '@/components/portfolio/add-to-portfolio-dialog';
import { useCopyToClipboard, useDownload } from '@/lib/hooks';
import { toast } from 'sonner';

function PropertyDetailPageContent() {
  const params = useParams();
  const router = useRouter();
  const searchParams = useSearchParams();
  const queryClient = useQueryClient();
  const propertyId = params.id as string;

  // Get initial tab from URL
  const initialTab = searchParams.get('tab') || 'details';

  // State
  const [activeTab, setActiveTab] = useState(initialTab);
  const [portfolioDialogOpen, setPortfolioDialogOpen] = useState(false);
  const [copied, copyToClipboard] = useCopyToClipboard();
  const download = useDownload();

  // Fetch property data
  const {
    data: propertyResponse,
    isLoading: propertyLoading,
    error: propertyError,
    refetch: refetchProperty,
  } = useQuery<APIResponse<PropertyDetail>>({
    queryKey: ['property', propertyId],
    queryFn: () => propertyApi.getById(propertyId),
  });

  const property = propertyResponse?.data;

  // Analysis mutation
  const analyzeMutation = useMutation({
    mutationFn: () => analysisApi.analyze(propertyId, { force_refresh: true, include_comparables: true }),
    onSuccess: (data) => {
      toast.success('Analysis completed successfully');
      queryClient.invalidateQueries({ queryKey: ['property', propertyId] });
    },
    onError: (error) => {
      toast.error('Analysis failed: ' + (error instanceof Error ? error.message : 'Unknown error'));
    },
  });

  // Appeal generation mutation
  const appealMutation = useMutation({
    mutationFn: (style: string) => appealApi.generate(propertyId, style),
    onSuccess: (data) => {
      toast.success('Appeal generated successfully');
      setActiveTab('appeal');
    },
    onError: (error) => {
      toast.error('Appeal generation failed: ' + (error instanceof Error ? error.message : 'Unknown error'));
    },
  });

  // PDF download mutation
  const downloadPdfMutation = useMutation({
    mutationFn: () => appealApi.downloadPdf(propertyId),
    onSuccess: (blob) => {
      download(blob, `appeal-${property?.parcel_id || propertyId}.pdf`);
      toast.success('PDF downloaded successfully');
    },
    onError: (error) => {
      toast.error('Download failed: ' + (error instanceof Error ? error.message : 'Unknown error'));
    },
  });

  // Format currency
  const formatCurrency = (value: number | null | undefined) => {
    if (value === null || value === undefined) return 'N/A';
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      maximumFractionDigits: 0,
    }).format(value);
  };

  // Get recommendation badge
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

  // Handle copy appeal letter
  const handleCopyAppealLetter = async () => {
    if (appealMutation.data?.data?.appeal_letter) {
      await copyToClipboard(appealMutation.data.data.appeal_letter);
      toast.success('Appeal letter copied to clipboard');
    }
  };

  // Handle copy summary
  const handleCopySummary = async () => {
    if (appealMutation.data?.data?.executive_summary) {
      await copyToClipboard(appealMutation.data.data.executive_summary);
      toast.success('Summary copied to clipboard');
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
          <div className="grid gap-4 md:grid-cols-4">
            {[...Array(4)].map((_, i) => (
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
              <h1 className="text-2xl font-bold tracking-tight">
                {property.address || 'Unknown Address'}
              </h1>
              <p className="text-muted-foreground">
                Parcel ID: {property.parcel_id} | {property.city || 'Unknown City'},{' '}
                {property.county || 'Benton'} County
              </p>
            </div>
          </div>
          <div className="flex gap-2">
            <Button
              variant="outline"
              onClick={() => refetchProperty()}
              disabled={propertyLoading}
            >
              <RefreshCw className={`h-4 w-4 mr-2 ${propertyLoading ? 'animate-spin' : ''}`} />
              Refresh
            </Button>
            <Button
              variant="outline"
              onClick={() => setPortfolioDialogOpen(true)}
            >
              <Briefcase className="h-4 w-4 mr-2" />
              Add to Portfolio
            </Button>
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
                onClick={() => appealMutation.mutate('formal')}
                disabled={appealMutation.isPending}
              >
                <FileText className="h-4 w-4 mr-2" />
                {appealMutation.isPending ? 'Generating...' : 'Generate Appeal'}
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
        <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-4">
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
                    <h4 className="font-semibold text-sm text-muted-foreground uppercase tracking-wide">
                      Owner Information
                    </h4>
                    <div className="space-y-2">
                      <div className="flex justify-between">
                        <span className="text-muted-foreground">Owner Name</span>
                        <span className="font-medium">{property.owner_name || 'N/A'}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-muted-foreground">Owner Address</span>
                        <span className="font-medium text-right max-w-[250px]">
                          {property.owner_address || 'N/A'}
                        </span>
                      </div>
                    </div>
                  </div>
                  <div className="space-y-4">
                    <h4 className="font-semibold text-sm text-muted-foreground uppercase tracking-wide">
                      Property Characteristics
                    </h4>
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
                        <span className="font-medium">
                          {property.tax_area_acres?.toFixed(2) || 'N/A'}
                        </span>
                      </div>
                    </div>
                  </div>
                </div>
                <Separator />
                <div className="space-y-4">
                  <h4 className="font-semibold text-sm text-muted-foreground uppercase tracking-wide">
                    Value Breakdown
                  </h4>
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
                <div className="flex items-center justify-between">
                  <div>
                    <CardTitle>Assessment Analysis</CardTitle>
                    <CardDescription>
                      Fairness analysis comparing this property to similar properties
                    </CardDescription>
                  </div>
                  <Button
                    variant="outline"
                    onClick={() => analyzeMutation.mutate()}
                    disabled={analyzeMutation.isPending}
                  >
                    <RefreshCw className={`h-4 w-4 mr-2 ${analyzeMutation.isPending ? 'animate-spin' : ''}`} />
                    {property.fairness_score ? 'Re-Analyze' : 'Run Analysis'}
                  </Button>
                </div>
              </CardHeader>
              <CardContent>
                {property.fairness_score ? (
                  <div className="space-y-6">
                    <div className="grid md:grid-cols-3 gap-4">
                      <div className="text-center p-4 bg-gray-50 rounded-lg">
                        <div className="text-3xl font-bold text-blue-600">
                          {property.fairness_score}%
                        </div>
                        <div className="text-sm text-muted-foreground">Fairness Score</div>
                      </div>
                      <div className="text-center p-4 bg-gray-50 rounded-lg">
                        <div className="text-3xl font-bold text-green-600">
                          {formatCurrency(property.estimated_savings)}
                        </div>
                        <div className="text-sm text-muted-foreground">Potential Savings</div>
                      </div>
                      <div className="text-center p-4 bg-gray-50 rounded-lg">
                        <div className="text-3xl font-bold">
                          {property.recommended_action || 'N/A'}
                        </div>
                        <div className="text-sm text-muted-foreground">Recommendation</div>
                      </div>
                    </div>

                    {property.fairness_score >= 50 && (
                      <div className="p-4 bg-green-50 border border-green-200 rounded-lg">
                        <div className="flex items-center gap-2">
                          <TrendingUp className="h-5 w-5 text-green-600" />
                          <p className="font-medium text-green-800">
                            This property is a strong candidate for appeal
                          </p>
                        </div>
                        <p className="text-sm text-green-700 mt-1">
                          Based on comparable properties, the assessment appears to be higher than
                          fair market value.
                        </p>
                        <Button
                          className="mt-3"
                          onClick={() => {
                            appealMutation.mutate('formal');
                          }}
                          disabled={appealMutation.isPending}
                        >
                          <FileText className="h-4 w-4 mr-2" />
                          Generate Appeal Letter
                        </Button>
                      </div>
                    )}

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
                      <RefreshCw
                        className={`h-4 w-4 mr-2 ${analyzeMutation.isPending ? 'animate-spin' : ''}`}
                      />
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
                <div className="flex items-center justify-between">
                  <div>
                    <CardTitle>Appeal Generation</CardTitle>
                    <CardDescription>
                      Generate a formal appeal letter for this property
                    </CardDescription>
                  </div>
                  {appealMutation.data?.data && (
                    <div className="flex gap-2">
                      <Button
                        variant="outline"
                        onClick={handleCopyAppealLetter}
                        disabled={copied}
                      >
                        {copied ? (
                          <Check className="h-4 w-4 mr-2" />
                        ) : (
                          <Copy className="h-4 w-4 mr-2" />
                        )}
                        {copied ? 'Copied!' : 'Copy Letter'}
                      </Button>
                      <Button
                        variant="outline"
                        onClick={() => downloadPdfMutation.mutate()}
                        disabled={downloadPdfMutation.isPending}
                      >
                        <Download className="h-4 w-4 mr-2" />
                        {downloadPdfMutation.isPending ? 'Downloading...' : 'Download PDF'}
                      </Button>
                    </div>
                  )}
                </div>
              </CardHeader>
              <CardContent>
                {appealMutation.data?.data ? (
                  <div className="space-y-6">
                    <div className="p-4 bg-green-50 border border-green-200 rounded-lg">
                      <h4 className="font-semibold text-green-800">Appeal Generated Successfully</h4>
                      <p className="text-sm text-green-700 mt-1">
                        Your appeal letter has been generated and is ready for download.
                      </p>
                    </div>

                    {/* Appeal Tabs */}
                    <Tabs defaultValue="letter" className="w-full">
                      <TabsList className="grid w-full grid-cols-3">
                        <TabsTrigger value="letter">Letter</TabsTrigger>
                        <TabsTrigger value="summary">Summary</TabsTrigger>
                        <TabsTrigger value="evidence">Evidence</TabsTrigger>
                      </TabsList>
                      <TabsContent value="letter" className="mt-4">
                        <div className="relative">
                          <Button
                            variant="ghost"
                            size="sm"
                            className="absolute right-2 top-2"
                            onClick={handleCopyAppealLetter}
                          >
                            {copied ? <Check className="h-4 w-4" /> : <Copy className="h-4 w-4" />}
                          </Button>
                          <pre className="whitespace-pre-wrap text-sm bg-gray-50 p-4 rounded-lg max-h-[500px] overflow-y-auto">
                            {appealMutation.data.data.appeal_letter}
                          </pre>
                        </div>
                      </TabsContent>
                      <TabsContent value="summary" className="mt-4">
                        <div className="relative">
                          <Button
                            variant="ghost"
                            size="sm"
                            className="absolute right-2 top-2"
                            onClick={handleCopySummary}
                          >
                            <Copy className="h-4 w-4" />
                          </Button>
                          <div className="bg-gray-50 p-4 rounded-lg">
                            <p className="text-sm">
                              {appealMutation.data.data.executive_summary || 'No summary available'}
                            </p>
                          </div>
                        </div>
                      </TabsContent>
                      <TabsContent value="evidence" className="mt-4">
                        <div className="bg-gray-50 p-4 rounded-lg">
                          <p className="text-sm">
                            {appealMutation.data.data.evidence_summary || 'No evidence summary available'}
                          </p>
                        </div>
                      </TabsContent>
                    </Tabs>

                    {/* Next Steps */}
                    <div className="border rounded-lg p-4">
                      <h4 className="font-semibold mb-3">Next Steps</h4>
                      <div className="space-y-2">
                        <label className="flex items-center gap-2 text-sm">
                          <input type="checkbox" className="rounded" />
                          Review and customize the appeal letter
                        </label>
                        <label className="flex items-center gap-2 text-sm">
                          <input type="checkbox" className="rounded" />
                          Gather supporting documentation
                        </label>
                        <label className="flex items-center gap-2 text-sm">
                          <input type="checkbox" className="rounded" />
                          Submit to Benton County Assessor before March 1, 2025
                        </label>
                      </div>
                    </div>

                    {/* Filing Info */}
                    <div className="grid md:grid-cols-2 gap-4 text-sm">
                      <div>
                        <span className="text-muted-foreground">Jurisdiction:</span>
                        <span className="ml-2 font-medium">
                          {appealMutation.data.data.jurisdiction}
                        </span>
                      </div>
                      <div>
                        <span className="text-muted-foreground">Filing Deadline:</span>
                        <span className="ml-2 font-medium">
                          {appealMutation.data.data.filing_deadline || 'March 1, 2025'}
                        </span>
                      </div>
                    </div>
                  </div>
                ) : property.fairness_score && property.fairness_score >= 50 ? (
                  <div className="text-center py-10">
                    <FileText className="h-10 w-10 text-blue-500 mx-auto mb-4" />
                    <h3 className="text-lg font-medium text-gray-900">
                      Property Qualifies for Appeal
                    </h3>
                    <p className="text-gray-500 mt-2">
                      Based on the analysis, this property may benefit from an appeal.
                    </p>

                    {/* Style Selection */}
                    <div className="max-w-md mx-auto mt-6 space-y-3">
                      <p className="text-sm font-medium text-left">Select appeal style:</p>
                      <div className="grid grid-cols-2 gap-3">
                        <button
                          onClick={() => appealMutation.mutate('formal')}
                          disabled={appealMutation.isPending}
                          className="p-4 border rounded-lg text-left hover:border-blue-500 hover:bg-blue-50 transition-colors"
                        >
                          <p className="font-medium">Formal</p>
                          <p className="text-sm text-gray-500">Professional legal tone</p>
                        </button>
                        <button
                          onClick={() => appealMutation.mutate('persuasive')}
                          disabled={appealMutation.isPending}
                          className="p-4 border rounded-lg text-left hover:border-blue-500 hover:bg-blue-50 transition-colors"
                        >
                          <p className="font-medium">Persuasive</p>
                          <p className="text-sm text-gray-500">Compelling narrative</p>
                        </button>
                      </div>
                    </div>

                    {appealMutation.isPending && (
                      <div className="mt-4 flex items-center justify-center gap-2 text-blue-600">
                        <RefreshCw className="h-4 w-4 animate-spin" />
                        <span>Generating appeal letter...</span>
                      </div>
                    )}
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
                    {!property.fairness_score && (
                      <Button
                        onClick={() => {
                          analyzeMutation.mutate();
                          setActiveTab('analysis');
                        }}
                        disabled={analyzeMutation.isPending}
                        className="mt-4"
                      >
                        Run Analysis First
                      </Button>
                    )}
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </div>

      {/* Add to Portfolio Dialog */}
      <AddToPortfolioDialog
        open={portfolioDialogOpen}
        onOpenChange={setPortfolioDialogOpen}
        propertyId={propertyId}
        parcelId={property.parcel_id}
        propertyAddress={property.address || undefined}
      />
    </MainLayout>
  );
}

// Loading fallback
function PropertyDetailPageFallback() {
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
        <div className="grid gap-4 md:grid-cols-4">
          {[...Array(4)].map((_, i) => (
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

export default function PropertyDetailPage() {
  return (
    <Suspense fallback={<PropertyDetailPageFallback />}>
      <PropertyDetailPageContent />
    </Suspense>
  );
}
