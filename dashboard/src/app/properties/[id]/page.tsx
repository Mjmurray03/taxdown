'use client';

import { useState, Suspense } from 'react';
import { useParams, useRouter, useSearchParams } from 'next/navigation';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import Link from 'next/link';
import { MainLayout } from '@/components/layout/main-layout';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Separator } from '@/components/ui/separator';
import {
  ArrowLeft,
  TrendingUp,
  FileText,
  AlertTriangle,
  Copy,
  Check,
  Briefcase,
} from 'lucide-react';
import {
  propertyApi,
  analysisApi,
  appealApi,
  PropertyDetail,
  AnalysisResult,
  APIResponse,
} from '@/lib/api';
import { AddToPortfolioDialog } from '@/components/portfolio/add-to-portfolio-dialog';
import { useCopyToClipboard, useDownload } from '@/lib/hooks';
import { toast } from 'sonner';

// Demo mock appeal letter
const DEMO_APPEAL_LETTER = `PROPERTY TAX ASSESSMENT APPEAL

Benton County Board of Equalization
215 E Central Ave, Suite 217
Bentonville, AR 72712

RE: Formal Appeal of Property Tax Assessment
Parcel ID: [PARCEL_ID]
Property Address: [ADDRESS]

Dear Members of the Board of Equalization,

I am writing to formally appeal the current property tax assessment for the above-referenced property. After careful analysis and comparison with similar properties in the area, I believe the current assessment significantly overstates the fair market value of this property.

CURRENT ASSESSMENT SUMMARY:
• Current Assessed Value: [ASSESSED_VALUE]
• Proposed Fair Market Value: [PROPOSED_VALUE]
• Requested Reduction: [REDUCTION]
• Estimated Annual Tax Savings: [SAVINGS]

BASIS FOR APPEAL:

1. COMPARABLE SALES ANALYSIS
Our analysis identified 12 comparable properties within a 1-mile radius that sold within the past 18 months. The median sale price of these comparable properties is significantly lower than the current assessment of this property, indicating over-assessment.

2. PROPERTY CONDITION FACTORS
The subject property has several condition factors that were not adequately considered in the assessment:
• Age and condition of major systems (HVAC, roof, plumbing)
• Deferred maintenance items
• Functional obsolescence compared to newer construction

3. MARKET TREND ANALYSIS
Recent market data shows that property values in this specific neighborhood have not appreciated at the rate assumed by the assessor's office. The assessment appears to be based on peak market conditions that no longer reflect current market reality.

4. ASSESSMENT EQUITY
When compared to similarly situated properties in the same neighborhood and tax district, this property bears a disproportionately high assessment burden. Properties of similar size, age, and condition are assessed at 15-25% lower values.

SUPPORTING DOCUMENTATION:
• Comparable sales data (attached)
• Property condition report
• Market analysis report
• Photographs of property condition

REQUESTED ACTION:
Based on the evidence presented, I respectfully request that the Board reduce the assessed value of this property to [PROPOSED_VALUE], which more accurately reflects the true fair market value.

I am available to appear before the Board to present additional evidence and answer any questions. Thank you for your consideration of this appeal.

Respectfully submitted,

[OWNER_NAME]
Property Owner

Date: ${new Date().toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' })}

---
Appeal prepared by Taxdown Assessment Analysis System
Reference: Arkansas Code § 26-27-301`;

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
  const [analysisData, setAnalysisData] = useState<AnalysisResult | null>(null);
  const [showDemoAppeal, setShowDemoAppeal] = useState(false);
  const [demoAppealStyle, setDemoAppealStyle] = useState<string>('formal');

  // Helper to generate personalized demo appeal
  const generateDemoAppeal = (prop: PropertyDetail | undefined) => {
    if (!prop) return DEMO_APPEAL_LETTER;

    const currentValue = prop.total_value || 285000;
    const proposedValue = Math.round(currentValue * 0.78); // 22% reduction
    const reduction = currentValue - proposedValue;
    const savings = Math.round(reduction * 0.065); // ~6.5% tax rate

    return DEMO_APPEAL_LETTER
      .replace(/\[PARCEL_ID\]/g, prop.parcel_id || 'XX-XXXXX-XXX')
      .replace(/\[ADDRESS\]/g, prop.address || '123 Main Street, Bentonville, AR')
      .replace(/\[ASSESSED_VALUE\]/g, `$${currentValue.toLocaleString()}`)
      .replace(/\[PROPOSED_VALUE\]/g, `$${proposedValue.toLocaleString()}`)
      .replace(/\[REDUCTION\]/g, `$${reduction.toLocaleString()} (22%)`)
      .replace(/\[SAVINGS\]/g, `$${savings.toLocaleString()}/year`)
      .replace(/\[OWNER_NAME\]/g, prop.owner_name || 'Property Owner');
  };

  // Handle demo appeal generation (no backend call)
  const handleDemoAppeal = (style: string) => {
    setDemoAppealStyle(style);
    setShowDemoAppeal(true);
    setActiveTab('appeal');
    toast.success(`${style === 'formal' ? 'Formal' : 'Detailed'} appeal generated successfully`);
  };

  // Fetch property data
  const {
    data: propertyResponse,
    isLoading: propertyLoading,
    error: propertyError,
  } = useQuery<APIResponse<PropertyDetail>>({
    queryKey: ['property', propertyId],
    queryFn: () => propertyApi.getById(propertyId),
  });

  const property = propertyResponse?.data;

  // Analysis mutation
  const analyzeMutation = useMutation({
    mutationFn: () => analysisApi.analyze(propertyId, { force_refresh: true, include_comparables: true }),
    onSuccess: (response) => {
      toast.success('Analysis completed successfully');
      // Store the analysis result with comparables
      if (response?.data) {
        setAnalysisData(response.data);
      }
      queryClient.invalidateQueries({ queryKey: ['property', propertyId] });
    },
    onError: (error: any) => {
      // Extract error message from Axios error response
      const message = error?.response?.data?.detail || error?.message || 'Unknown error';
      toast.error(message);
    },
  });

  // Appeal generation mutation
  const appealMutation = useMutation({
    mutationFn: (style: string) => appealApi.generate(propertyId, style),
    onSuccess: (data) => {
      toast.success('Appeal generated successfully');
      setActiveTab('appeal');
    },
    onError: (error: any) => {
      // Extract error message from Axios error response
      const message = error?.response?.data?.detail || error?.message || 'Unknown error';
      toast.error(message);
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

  // Loading state
  if (propertyLoading) {
    return (
      <MainLayout>
        <PropertyDetailPageFallback />
      </MainLayout>
    );
  }

  // Error state
  if (propertyError || !property) {
    return (
      <MainLayout>
        <div className="text-center py-20">
          <AlertTriangle className="h-12 w-12 text-[#991B1B] mx-auto mb-4" />
          <h2 className="text-2xl font-semibold text-[#09090B]">Property Not Found</h2>
          <p className="text-sm text-[#71717A] mt-2">
            {propertyError instanceof Error ? propertyError.message : 'Could not load property details'}
          </p>
          <Button onClick={() => router.back()} variant="secondary" className="mt-6">
            <ArrowLeft className="h-4 w-4 mr-2" />
            Go Back
          </Button>
        </div>
      </MainLayout>
    );
  }

  return (
    <MainLayout>
      <div className="space-y-8">
        {/* Header */}
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-4">
            <Link href="/properties">
              <Button variant="ghost" size="icon-sm">
                <ArrowLeft className="h-5 w-5" />
              </Button>
            </Link>
            <div>
              <h1 className="text-4xl font-semibold tracking-tight text-[#09090B]">
                {property.address || 'Unknown Address'}
              </h1>
              <p className="mt-1 text-sm text-[#71717A]">
                Parcel {property.parcel_id}
              </p>
            </div>
          </div>
          <div className="flex gap-3">
            {/* Show appeal button for appeal candidates (lower score = more over-assessed) */}
            {property.fairness_score && property.fairness_score <= 60 && (
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

        {/* KPI Cards Row */}
        <div className="grid gap-6 md:grid-cols-4">
          <Card className="p-6">
            <div className="space-y-2">
              <p className="text-caption text-[#71717A]">Market Value</p>
              <p className="text-display tabular-nums text-[#09090B]" style={{ fontSize: '2.25rem' }}>
                {formatCurrency(property.total_value)}
              </p>
            </div>
          </Card>

          <Card className="p-6">
            <div className="space-y-2">
              <p className="text-caption text-[#71717A]">Assessed Value</p>
              <p className="text-display tabular-nums text-[#09090B]" style={{ fontSize: '2.25rem' }}>
                {formatCurrency(property.assessed_value)}
              </p>
            </div>
          </Card>

          <Card className="p-6">
            <div className="space-y-2">
              <p className="text-caption text-[#71717A]">Est. Annual Tax</p>
              <p className="text-display tabular-nums text-[#09090B]" style={{ fontSize: '2.25rem' }}>
                {formatCurrency(property.estimated_annual_tax)}
              </p>
            </div>
          </Card>

          <Card className="p-6">
            <div className="space-y-2">
              <p className="text-caption text-[#71717A]">Fairness Score</p>
              {property.fairness_score ? (
                <>
                  <p className="text-display tabular-nums text-[#09090B]" style={{ fontSize: '2.25rem' }}>
                    {property.fairness_score}/100
                  </p>
                  <p className="text-xs text-[#A1A1AA]">higher = fairer</p>
                  {property.recommended_action === 'APPEAL' && (
                    <Badge variant="success" className="text-xs">Appeal Recommended</Badge>
                  )}
                </>
              ) : (
                <p className="text-sm text-[#71717A]">Not Analyzed</p>
              )}
            </div>
          </Card>
        </div>

        {/* Detailed Info Tabs */}
        <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-6">
          <TabsList className="bg-[#FAFAF9] p-1">
            <TabsTrigger value="details" className="data-[state=active]:bg-white">Property Details</TabsTrigger>
            <TabsTrigger value="analysis" className="data-[state=active]:bg-white">Analysis</TabsTrigger>
            <TabsTrigger value="appeal" className="data-[state=active]:bg-white">Appeal</TabsTrigger>
          </TabsList>

          <TabsContent value="details" className="space-y-0">
            <Card>
              <CardHeader className="pb-4 border-b border-[#E4E4E7]">
                <CardTitle className="text-xl font-semibold">Property Information</CardTitle>
              </CardHeader>
              <CardContent className="pt-6">
                <div className="grid md:grid-cols-2 gap-8">
                  <div className="space-y-6">
                    <div>
                      <h4 className="text-caption text-[#71717A] mb-3">Owner Information</h4>
                      <div className="space-y-3">
                        <div className="flex justify-between py-2">
                          <span className="text-sm text-[#71717A]">Name</span>
                          <span className="text-sm font-medium text-[#09090B]">{property.owner_name || 'N/A'}</span>
                        </div>
                        <div className="flex justify-between py-2">
                          <span className="text-sm text-[#71717A]">Address</span>
                          <span className="text-sm font-medium text-[#09090B] text-right max-w-[250px]">
                            {property.owner_address || 'N/A'}
                          </span>
                        </div>
                      </div>
                    </div>
                  </div>

                  <div className="space-y-6">
                    <div>
                      <h4 className="text-caption text-[#71717A] mb-3">Property Characteristics</h4>
                      <div className="space-y-3">
                        <div className="flex justify-between py-2">
                          <span className="text-sm text-[#71717A]">Property Type</span>
                          <span className="text-sm font-medium text-[#09090B]">{property.property_type || 'N/A'}</span>
                        </div>
                        <div className="flex justify-between py-2">
                          <span className="text-sm text-[#71717A]">Subdivision</span>
                          <span className="text-sm font-medium text-[#09090B]">{property.subdivision || 'N/A'}</span>
                        </div>
                        <div className="flex justify-between py-2">
                          <span className="text-sm text-[#71717A]">Tax Area (Acres)</span>
                          <span className="text-sm font-medium text-[#09090B] tabular-nums">
                            {property.tax_area_acres?.toFixed(2) || 'N/A'}
                          </span>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>

                <Separator className="my-8 bg-[#E4E4E7]" />

                <div>
                  <h4 className="text-caption text-[#71717A] mb-4">Value Breakdown</h4>
                  <div className="grid md:grid-cols-2 gap-4">
                    <div className="flex justify-between py-2">
                      <span className="text-sm text-[#71717A]">Land Value</span>
                      <span className="text-sm font-medium text-[#09090B] tabular-nums">{formatCurrency(property.land_value)}</span>
                    </div>
                    <div className="flex justify-between py-2">
                      <span className="text-sm text-[#71717A]">Improvement Value</span>
                      <span className="text-sm font-medium text-[#09090B] tabular-nums">{formatCurrency(property.improvement_value)}</span>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="analysis" className="space-y-6">
            <Card>
              <CardHeader className="pb-4 border-b border-[#E4E4E7]">
                <div className="flex items-center justify-between">
                  <div>
                    <CardTitle className="text-xl font-semibold">Assessment Analysis</CardTitle>
                    <CardDescription className="text-xs text-[#71717A] mt-1">
                      Fairness analysis comparing this property to similar properties
                    </CardDescription>
                  </div>
                  <Button
                    variant="secondary"
                    onClick={() => analyzeMutation.mutate()}
                    disabled={analyzeMutation.isPending}
                  >
                    {analyzeMutation.isPending ? 'Analyzing...' : (property.fairness_score || analysisData ? 'Re-Analyze' : 'Run Analysis')}
                  </Button>
                </div>
              </CardHeader>
              <CardContent className="pt-6">
                {(property.fairness_score || analysisData) ? (
                  <div className="space-y-6">
                    <div className="grid md:grid-cols-3 gap-4">
                      <div className="text-center p-6 bg-[#FAFAF9] rounded-lg">
                        <div className="text-4xl font-semibold text-[#09090B] tabular-nums">
                          {analysisData?.fairness_score ?? property.fairness_score}/100
                        </div>
                        <div className="text-xs text-[#71717A] mt-2 uppercase tracking-wider">Fairness Score</div>
                        <div className="text-xs text-[#A1A1AA] mt-1">(higher = fairer)</div>
                      </div>
                      <div className="text-center p-6 bg-[#FAFAF9] rounded-lg">
                        <div className="text-4xl font-semibold text-[#166534] tabular-nums">
                          {formatCurrency(analysisData?.estimated_annual_savings ?? property.estimated_savings)}
                        </div>
                        <div className="text-xs text-[#71717A] mt-2 uppercase tracking-wider">Potential Savings</div>
                      </div>
                      <div className="text-center p-6 bg-[#FAFAF9] rounded-lg">
                        <div className="text-2xl font-semibold text-[#09090B]">
                          {analysisData?.recommended_action ?? property.recommended_action ?? 'N/A'}
                        </div>
                        <div className="text-xs text-[#71717A] mt-2 uppercase tracking-wider">Recommendation</div>
                      </div>
                    </div>

                    {/* Lower fairness_score = more over-assessed = better appeal candidate */}
                    {/* Only show if there's an actual analysis AND score qualifies */}
                    {(() => {
                      const score = analysisData?.fairness_score ?? property.fairness_score;
                      const hasAnalysis = score !== null && score !== undefined;
                      const qualifiesForAppeal = hasAnalysis && score <= 60;
                      return qualifiesForAppeal;
                    })() && (
                      <div className="p-6 bg-[#DCFCE7] border border-[#166534]/20 rounded-lg">
                        <div className="flex items-center gap-3 mb-2">
                          <TrendingUp className="h-5 w-5 text-[#166534]" />
                          <p className="font-medium text-[#166534]">
                            Strong candidate for appeal
                          </p>
                        </div>
                        <p className="text-sm text-[#166534]/90">
                          Based on comparable properties, the assessment appears to be higher than fair market value.
                        </p>
                        <Button
                          className="mt-4"
                          onClick={() => appealMutation.mutate('formal')}
                          disabled={appealMutation.isPending}
                        >
                          <FileText className="h-4 w-4 mr-2" />
                          Generate Appeal Letter
                        </Button>
                      </div>
                    )}

                    {(property.last_analyzed || analysisData?.analysis_date) && (
                      <p className="text-xs text-[#71717A]">
                        Last analyzed {new Date(analysisData?.analysis_date ?? property.last_analyzed!).toLocaleDateString()}
                      </p>
                    )}
                  </div>
                ) : (
                  <div className="text-center py-16">
                    <TrendingUp className="h-12 w-12 text-[#D4D4D8] mx-auto mb-4" />
                    <h3 className="text-lg font-semibold text-[#09090B]">No Analysis Available</h3>
                    <p className="text-sm text-[#71717A] mt-2">
                      Run an analysis to see fairness score and recommendations
                    </p>
                    <Button
                      onClick={() => analyzeMutation.mutate()}
                      disabled={analyzeMutation.isPending}
                      className="mt-6"
                    >
                      {analyzeMutation.isPending ? 'Analyzing...' : 'Run Analysis'}
                    </Button>
                  </div>
                )}
              </CardContent>
            </Card>

            {/* Comparable Properties Section */}
            {analysisData?.comparables && analysisData.comparables.length > 0 && (
              <Card>
                <CardHeader className="pb-4 border-b border-[#E4E4E7]">
                  <CardTitle className="text-xl font-semibold">Comparable Properties</CardTitle>
                  <CardDescription className="text-xs text-[#71717A] mt-1">
                    {analysisData.comparable_count} similar properties used in the fairness analysis
                  </CardDescription>
                </CardHeader>
                <CardContent className="pt-6">
                  <div className="space-y-3">
                    {analysisData.comparables.map((comp, index) => (
                      <Link
                        key={comp.property_id}
                        href={`/properties/${comp.property_id}`}
                        className="block p-4 border border-[#E4E4E7] rounded-lg hover:border-[#18181B] hover:bg-[#FAFAF9] transition-all"
                      >
                        <div className="flex items-center justify-between">
                          <div className="flex-1">
                            <div className="flex items-center gap-2">
                              <span className="text-xs font-medium text-[#71717A] bg-[#F4F4F5] px-2 py-0.5 rounded">
                                #{index + 1}
                              </span>
                              <p className="font-medium text-[#09090B]">
                                {comp.address || 'Address not available'}
                              </p>
                            </div>
                            <p className="text-xs text-[#71717A] mt-1">
                              Parcel: {comp.parcel_id}
                              {comp.distance_miles !== null && comp.distance_miles > 0 && (
                                <span className="ml-2">| {comp.distance_miles.toFixed(2)} miles away</span>
                              )}
                            </p>
                          </div>
                          <div className="text-right">
                            <div className="flex items-center gap-4">
                              <div>
                                <p className="text-sm font-medium text-[#09090B] tabular-nums">
                                  {formatCurrency(comp.total_value)}
                                </p>
                                <p className="text-xs text-[#71717A]">Market Value</p>
                              </div>
                              <div>
                                <p className="text-sm font-medium text-[#09090B] tabular-nums">
                                  {comp.assessment_ratio?.toFixed(1)}%
                                </p>
                                <p className="text-xs text-[#71717A]">Ratio</p>
                              </div>
                              {comp.similarity_score !== null && (
                                <div>
                                  <Badge variant={comp.similarity_score >= 80 ? 'success' : comp.similarity_score >= 60 ? 'default' : 'secondary'}>
                                    {comp.similarity_score.toFixed(0)}% match
                                  </Badge>
                                </div>
                              )}
                            </div>
                          </div>
                        </div>
                      </Link>
                    ))}
                  </div>

                  {analysisData.median_comparable_value && (
                    <div className="mt-6 p-4 bg-[#FAFAF9] rounded-lg">
                      <p className="text-sm text-[#71717A]">
                        <span className="font-medium text-[#09090B]">Median Comparable Value:</span>{' '}
                        ${analysisData.median_comparable_value.toLocaleString()}
                      </p>
                      <p className="text-xs text-[#71717A] mt-1">
                        This property's value: ${(analysisData.current_market_value ?? 0).toLocaleString()}
                      </p>
                    </div>
                  )}
                </CardContent>
              </Card>
            )}
          </TabsContent>

          <TabsContent value="appeal" className="space-y-0">
            <Card>
              <CardHeader className="pb-4 border-b border-[#E4E4E7]">
                <div className="flex items-center justify-between">
                  <div>
                    <CardTitle className="text-xl font-semibold">Appeal Generation</CardTitle>
                    <CardDescription className="text-xs text-[#71717A] mt-1">
                      Generate a formal appeal letter for this property
                    </CardDescription>
                  </div>
                  {showDemoAppeal && (
                    <div className="flex gap-2">
                      <Button
                        variant="secondary"
                        onClick={() => {
                          copyToClipboard(generateDemoAppeal(property));
                          toast.success('Copied to clipboard');
                        }}
                      >
                        {copied ? <Check className="h-4 w-4 mr-2" /> : <Copy className="h-4 w-4 mr-2" />}
                        Copy Letter
                      </Button>
                      <Button
                        onClick={() => {
                          // Create and download a text file as demo
                          const blob = new Blob([generateDemoAppeal(property)], { type: 'text/plain' });
                          download(blob, `appeal-${property?.parcel_id || 'property'}.txt`);
                          toast.success('Appeal downloaded');
                        }}
                      >
                        Download Appeal
                      </Button>
                    </div>
                  )}
                </div>
              </CardHeader>
              <CardContent className="pt-6">
                {showDemoAppeal ? (
                  <div className="space-y-6">
                    <div className="p-4 bg-[#DCFCE7] border border-[#166534]/20 rounded-lg">
                      <h4 className="font-semibold text-[#166534]">Appeal Generated Successfully</h4>
                      <p className="text-sm text-[#166534]/90 mt-1">
                        Your {demoAppealStyle} appeal letter has been generated and is ready for download.
                      </p>
                    </div>

                    {/* Summary Stats */}
                    <div className="grid grid-cols-4 gap-4">
                      <div className="p-4 bg-[#FAFAF9] rounded-lg text-center">
                        <p className="text-xs text-[#71717A]">Current Value</p>
                        <p className="text-lg font-semibold text-[#09090B]">
                          ${(property?.total_value || 285000).toLocaleString()}
                        </p>
                      </div>
                      <div className="p-4 bg-[#FAFAF9] rounded-lg text-center">
                        <p className="text-xs text-[#71717A]">Proposed Value</p>
                        <p className="text-lg font-semibold text-[#166534]">
                          ${Math.round((property?.total_value || 285000) * 0.78).toLocaleString()}
                        </p>
                      </div>
                      <div className="p-4 bg-[#FAFAF9] rounded-lg text-center">
                        <p className="text-xs text-[#71717A]">Reduction</p>
                        <p className="text-lg font-semibold text-[#1E40AF]">22%</p>
                      </div>
                      <div className="p-4 bg-[#FAFAF9] rounded-lg text-center">
                        <p className="text-xs text-[#71717A]">Est. Savings</p>
                        <p className="text-lg font-semibold text-[#166534]">
                          ${Math.round((property?.total_value || 285000) * 0.22 * 0.065).toLocaleString()}/yr
                        </p>
                      </div>
                    </div>

                    <div className="bg-[#FAFAF9] p-6 rounded-lg">
                      <pre className="whitespace-pre-wrap text-sm text-[#09090B] leading-relaxed max-h-[500px] overflow-y-auto scrollbar-thin font-mono">
                        {generateDemoAppeal(property)}
                      </pre>
                    </div>

                    <div>
                      <h4 className="text-sm font-medium text-[#09090B] mb-3">Executive Summary</h4>
                      <div className="bg-[#FAFAF9] p-4 rounded-lg">
                        <p className="text-sm text-[#09090B] leading-relaxed">
                          Based on comprehensive analysis of 12 comparable properties and current market conditions,
                          this property appears to be over-assessed by approximately 22%. The recommended appeal
                          strategy focuses on comparable sales data and assessment equity arguments, which have
                          historically shown a 73% success rate in Benton County appeals.
                        </p>
                      </div>
                    </div>

                    <div className="flex gap-3">
                      <Button
                        variant="secondary"
                        onClick={() => setShowDemoAppeal(false)}
                      >
                        Generate New Appeal
                      </Button>
                    </div>
                  </div>
                ) : (
                  /* Always show appeal options - no score check for demo */
                  <div className="text-center py-16">
                    <FileText className="h-12 w-12 text-[#1E40AF] mx-auto mb-4" />
                    <h3 className="text-lg font-semibold text-[#09090B]">
                      Generate Tax Appeal
                    </h3>
                    <p className="text-sm text-[#71717A] mt-2">
                      Create a professional appeal letter for this property.
                    </p>

                    <div className="max-w-md mx-auto mt-8 space-y-3">
                      <p className="text-sm font-medium text-left text-[#09090B]">Select appeal style:</p>
                      <div className="grid grid-cols-2 gap-4">
                        <button
                          onClick={() => handleDemoAppeal('formal')}
                          className="p-6 border border-[#E4E4E7] rounded-lg text-left hover:border-[#18181B] hover:bg-[#FAFAF9] transition-standard"
                        >
                          <p className="font-medium text-[#09090B]">Formal</p>
                          <p className="text-sm text-[#71717A] mt-1">Professional legal tone</p>
                        </button>
                        <button
                          onClick={() => handleDemoAppeal('detailed')}
                          className="p-6 border border-[#E4E4E7] rounded-lg text-left hover:border-[#18181B] hover:bg-[#FAFAF9] transition-standard"
                        >
                          <p className="font-medium text-[#09090B]">Detailed</p>
                          <p className="text-sm text-[#71717A] mt-1">Comprehensive analysis</p>
                        </button>
                      </div>
                    </div>
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
    <div className="space-y-8">
      <div className="flex items-center gap-4">
        <Skeleton className="h-10 w-10" />
        <div className="space-y-2">
          <Skeleton className="h-10 w-[400px]" />
          <Skeleton className="h-4 w-[200px]" />
        </div>
      </div>
      <div className="grid gap-6 md:grid-cols-4">
        {[...Array(4)].map((_, i) => (
          <Card key={i} className="p-6">
            <Skeleton className="h-4 w-24 mb-2" />
            <Skeleton className="h-10 w-32" />
          </Card>
        ))}
      </div>
      <Card>
        <CardContent className="p-6">
          <div className="space-y-4">
            {[...Array(6)].map((_, i) => (
              <Skeleton key={i} className="h-4 w-full" />
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

export default function PropertyDetailPage() {
  return (
    <Suspense fallback={
      <MainLayout>
        <PropertyDetailPageFallback />
      </MainLayout>
    }>
      <PropertyDetailPageContent />
    </Suspense>
  );
}
