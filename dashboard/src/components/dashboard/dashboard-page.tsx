'use client';

import { useQuery } from '@tanstack/react-query';
import Link from 'next/link';
import { format } from 'date-fns';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { ArrowRight } from 'lucide-react';
import { propertyApi, portfolioApi, PropertySearchResponse, DashboardData, APIResponse, AssessmentDistribution } from '@/lib/api';
import { useLocalStorage } from '@/lib/hooks';

export function DashboardPage() {
  // Get selected portfolio from local storage
  const [selectedPortfolioId] = useLocalStorage<string | null>('selected-portfolio-id', null);

  // Fetch dashboard data from portfolio if available
  const { data: dashboardResponse, isLoading: loadingDashboard } = useQuery<APIResponse<DashboardData>>({
    queryKey: ['dashboard', selectedPortfolioId],
    queryFn: () => portfolioApi.getDashboard(selectedPortfolioId!),
    enabled: !!selectedPortfolioId,
  });

  const dashboardData = dashboardResponse?.data;

  // Fallback: Fetch total properties count if no portfolio selected
  const { data: allProperties, isLoading: loadingAll } = useQuery<PropertySearchResponse>({
    queryKey: ['dashboard-all-properties'],
    queryFn: () => propertyApi.search({ page: 1, page_size: 1 }),
    enabled: !selectedPortfolioId,
  });

  // Fetch appeal candidates
  const { data: appealCandidates, isLoading: loadingCandidates } = useQuery<PropertySearchResponse>({
    queryKey: ['dashboard-appeal-candidates'],
    queryFn: () => propertyApi.search({ only_appeal_candidates: true, page: 1, page_size: 5 }),
  });

  // Fetch assessment distribution stats
  const { data: assessmentStats, isLoading: loadingStats } = useQuery<AssessmentDistribution>({
    queryKey: ['assessment-distribution'],
    queryFn: () => propertyApi.getAssessmentDistribution(),
  });

  const isLoading = loadingDashboard || loadingAll || loadingCandidates || loadingStats;

  const formatCurrency = (value: number | null | undefined) => {
    if (value === null || value === undefined) return '$0';
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      maximumFractionDigits: 0,
    }).format(value);
  };

  const formatNumber = (value: number | null | undefined) => {
    if (value === null || value === undefined) return '0';
    return new Intl.NumberFormat('en-US').format(value);
  };

  // Calculate days until deadline (March 1, 2026)
  const deadline = new Date('2026-03-01');
  const today = new Date();
  const daysUntilDeadline = Math.ceil((deadline.getTime() - today.getTime()) / (1000 * 60 * 60 * 24));

  return (
    <div className="space-y-8">
      {/* Page Header */}
      <div className="flex items-end justify-between">
        <div>
          <h1 className="text-4xl font-semibold tracking-tight text-[#09090B]">Dashboard</h1>
          <p className="mt-1 text-sm text-[#71717A]">
            {format(today, 'MMMM d, yyyy')}
          </p>
        </div>
        <Button size="default">
          Analyze Portfolio
        </Button>
      </div>

      {/* KPI Cards Row */}
      <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-4">
        {/* Total Properties */}
        <Card className="p-6">
          <div className="space-y-2">
            <p className="text-caption text-[#71717A]">Total Properties</p>
            {isLoading ? (
              <Skeleton className="h-10 w-32" />
            ) : (
              <p className="text-display tabular-nums text-[#09090B]" style={{ fontSize: '2.25rem' }}>
                {formatNumber(dashboardData?.metrics.total_properties || allProperties?.total_count)}
              </p>
            )}
          </div>
        </Card>

        {/* Portfolio Value */}
        <Card className="p-6">
          <div className="space-y-2">
            <p className="text-caption text-[#71717A]">Total Market Value</p>
            {isLoading ? (
              <Skeleton className="h-10 w-32" />
            ) : (
              <p className="text-display tabular-nums text-[#09090B]" style={{ fontSize: '2.25rem' }}>
                {dashboardData?.metrics.total_market_value
                  ? formatCurrency(dashboardData.metrics.total_market_value)
                  : 'N/A'}
              </p>
            )}
          </div>
        </Card>

        {/* Potential Savings */}
        <Card className="p-6">
          <div className="space-y-2">
            <p className="text-caption text-[#71717A]">Potential Savings</p>
            {isLoading ? (
              <Skeleton className="h-10 w-32" />
            ) : (
              <p className="text-display tabular-nums text-[#09090B]" style={{ fontSize: '2.25rem' }}>
                {dashboardData?.metrics.total_potential_savings
                  ? formatCurrency(dashboardData.metrics.total_potential_savings)
                  : 'N/A'}
              </p>
            )}
          </div>
        </Card>

        {/* Appeal Candidates */}
        <Card className="p-6">
          <div className="space-y-2">
            <p className="text-caption text-[#71717A]">Appeal Candidates</p>
            {isLoading ? (
              <Skeleton className="h-10 w-32" />
            ) : (
              <p className="text-display tabular-nums text-[#09090B]" style={{ fontSize: '2.25rem' }}>
                {formatNumber(dashboardData?.metrics.appeal_candidates || appealCandidates?.total_count)}
              </p>
            )}
          </div>
        </Card>
      </div>

      {/* Main Content Grid */}
      <div className="grid gap-8 lg:grid-cols-3">
        {/* Appeal Opportunities - Takes 2 columns */}
        <Card className="lg:col-span-2">
          <CardHeader className="pb-4 border-b border-[#E4E4E7]">
            <div className="flex items-center justify-between">
              <CardTitle className="text-xl font-semibold">Top Opportunities</CardTitle>
              <Link href="/properties?filter=appeal" className="text-sm font-medium text-[#1E40AF] hover:underline">
                View All
              </Link>
            </div>
          </CardHeader>
          <CardContent className="pt-6">
            {loadingCandidates ? (
              <div className="space-y-4">
                {[...Array(5)].map((_, i) => (
                  <div key={i} className="flex items-center justify-between py-3">
                    <div className="space-y-2 flex-1">
                      <Skeleton className="h-4 w-48" />
                      <Skeleton className="h-3 w-32" />
                    </div>
                    <Skeleton className="h-4 w-24" />
                  </div>
                ))}
              </div>
            ) : dashboardData?.top_savings_opportunities && dashboardData.top_savings_opportunities.length > 0 ? (
              <div className="space-y-1">
                {dashboardData.top_savings_opportunities.map((property) => (
                  <Link
                    key={property.parcel_id}
                    href={`/properties/${property.property_id}`}
                    className="flex items-center justify-between py-3 px-4 -mx-4 rounded-md hover:bg-[#FAFAF9] transition-standard group"
                  >
                    <div className="flex-1">
                      <p className="text-sm font-medium text-[#09090B]">
                        {property.address || 'Unknown Address'}
                      </p>
                      <p className="text-xs text-[#71717A] mt-0.5 tabular-nums">
                        Parcel: {property.parcel_id}
                      </p>
                    </div>
                    <div className="flex items-center gap-2">
                      <p className="text-sm font-medium text-mono tabular-nums text-[#09090B]">
                        {formatCurrency(property.value)}
                      </p>
                      <ArrowRight className="h-4 w-4 text-[#71717A] group-hover:text-[#18181B] transition-standard" />
                    </div>
                  </Link>
                ))}
              </div>
            ) : appealCandidates?.properties && appealCandidates.properties.length > 0 ? (
              <div className="space-y-1">
                {appealCandidates.properties.map((property) => (
                  <Link
                    key={property.id}
                    href={`/properties/${property.id}`}
                    className="flex items-center justify-between py-3 px-4 -mx-4 rounded-md hover:bg-[#FAFAF9] transition-standard group"
                  >
                    <div className="flex-1">
                      <p className="text-sm font-medium text-[#09090B]">
                        {property.address || 'Unknown Address'}
                      </p>
                      <p className="text-xs text-[#71717A] mt-0.5 tabular-nums">
                        {formatCurrency(property.total_value)}
                      </p>
                    </div>
                    <div className="flex items-center gap-2">
                      <p className="text-sm font-medium text-mono tabular-nums text-[#09090B]">
                        Est. TBD
                      </p>
                      <ArrowRight className="h-4 w-4 text-[#71717A] group-hover:text-[#18181B] transition-standard" />
                    </div>
                  </Link>
                ))}
              </div>
            ) : (
              <div className="text-center py-12">
                <p className="text-sm text-[#71717A]">No appeal candidates found</p>
                <p className="text-xs text-[#A1A1AA] mt-1">Run analysis on properties to find opportunities</p>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Assessment Overview - Takes 1 column */}
        <Card>
          <CardHeader className="pb-4 border-b border-[#E4E4E7]">
            <CardTitle className="text-xl font-semibold">Assessment Overview</CardTitle>
            <CardDescription className="text-xs text-[#71717A]">
              {assessmentStats ? `${formatNumber(assessmentStats.total_analyzed)} analyzed` : 'Loading...'}
            </CardDescription>
          </CardHeader>
          <CardContent className="pt-6">
            {loadingStats ? (
              <div className="space-y-4">
                {[...Array(4)].map((_, i) => (
                  <div key={i}>
                    <div className="flex justify-between mb-1.5">
                      <Skeleton className="h-4 w-24" />
                      <Skeleton className="h-4 w-16" />
                    </div>
                    <Skeleton className="h-2 w-full" />
                  </div>
                ))}
              </div>
            ) : assessmentStats ? (
              <div className="space-y-4">
                {/* Assessment distribution */}
                <div className="space-y-3">
                  <Link href="/properties?assessment_category=fairly_assessed" className="block hover:bg-[#FAFAF9] -mx-2 px-2 py-1 rounded transition-colors">
                    <div className="flex items-center justify-between mb-1.5">
                      <p className="text-sm text-[#09090B]">Fairly Assessed</p>
                      <p className="text-sm font-medium tabular-nums text-[#09090B]">{formatNumber(assessmentStats.fairly_assessed)}</p>
                    </div>
                    <div className="h-2 bg-[#F4F4F5] rounded-full overflow-hidden">
                      <div
                        className="h-full bg-[#22C55E] rounded-full transition-all"
                        style={{ width: `${assessmentStats.total_analyzed > 0 ? (assessmentStats.fairly_assessed / assessmentStats.total_analyzed) * 100 : 0}%` }}
                      />
                    </div>
                  </Link>

                  <Link href="/properties?assessment_category=slightly_over" className="block hover:bg-[#FAFAF9] -mx-2 px-2 py-1 rounded transition-colors">
                    <div className="flex items-center justify-between mb-1.5">
                      <p className="text-sm text-[#09090B]">Slightly Over</p>
                      <p className="text-sm font-medium tabular-nums text-[#09090B]">{formatNumber(assessmentStats.slightly_over)}</p>
                    </div>
                    <div className="h-2 bg-[#F4F4F5] rounded-full overflow-hidden">
                      <div
                        className="h-full bg-[#F59E0B] rounded-full transition-all"
                        style={{ width: `${assessmentStats.total_analyzed > 0 ? (assessmentStats.slightly_over / assessmentStats.total_analyzed) * 100 : 0}%` }}
                      />
                    </div>
                  </Link>

                  <Link href="/properties?assessment_category=moderately_over" className="block hover:bg-[#FAFAF9] -mx-2 px-2 py-1 rounded transition-colors">
                    <div className="flex items-center justify-between mb-1.5">
                      <p className="text-sm text-[#09090B]">Moderately Over</p>
                      <p className="text-sm font-medium tabular-nums text-[#09090B]">{formatNumber(assessmentStats.moderately_over)}</p>
                    </div>
                    <div className="h-2 bg-[#F4F4F5] rounded-full overflow-hidden">
                      <div
                        className="h-full bg-[#F97316] rounded-full transition-all"
                        style={{ width: `${assessmentStats.total_analyzed > 0 ? (assessmentStats.moderately_over / assessmentStats.total_analyzed) * 100 : 0}%` }}
                      />
                    </div>
                  </Link>

                  <Link href="/properties?assessment_category=significantly_over" className="block hover:bg-[#FAFAF9] -mx-2 px-2 py-1 rounded transition-colors">
                    <div className="flex items-center justify-between mb-1.5">
                      <p className="text-sm text-[#09090B]">Significantly Over</p>
                      <p className="text-sm font-medium tabular-nums text-[#09090B]">{formatNumber(assessmentStats.significantly_over)}</p>
                    </div>
                    <div className="h-2 bg-[#F4F4F5] rounded-full overflow-hidden">
                      <div
                        className="h-full bg-[#DC2626] rounded-full transition-all"
                        style={{ width: `${assessmentStats.total_analyzed > 0 ? (assessmentStats.significantly_over / assessmentStats.total_analyzed) * 100 : 0}%` }}
                      />
                    </div>
                  </Link>
                </div>

                <div className="pt-4 border-t border-[#E4E4E7] space-y-2">
                  <p className="text-sm text-[#71717A]">
                    <span className="font-medium text-[#09090B]">{formatNumber(assessmentStats.appeal_candidates)}</span> properties may benefit from appeal
                  </p>
                  {assessmentStats.total_potential_savings > 0 && (
                    <p className="text-sm text-[#166534]">
                      <span className="font-medium">{formatCurrency(assessmentStats.total_potential_savings)}</span> potential annual savings
                    </p>
                  )}
                  {assessmentStats.unanalyzed > 0 && (
                    <Link href="/properties?assessment_category=unanalyzed" className="text-xs text-[#71717A] hover:text-[#09090B] transition-colors">
                      {formatNumber(assessmentStats.unanalyzed)} properties not yet analyzed →
                    </Link>
                  )}
                </div>
              </div>
            ) : (
              <div className="text-center py-8">
                <p className="text-sm text-[#71717A]">No assessment data available</p>
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Deadline Banner */}
      {daysUntilDeadline > 0 && (
        <Card className={`border-[#E4E4E7] ${
          daysUntilDeadline < 14
            ? 'bg-[#FEF2F2]'
            : daysUntilDeadline < 30
            ? 'bg-[#FEF3C7]'
            : 'bg-[#FAFAF9]'
        }`}>
          <CardContent className="py-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className={`h-2 w-2 rounded-full ${
                  daysUntilDeadline < 14
                    ? 'bg-[#991B1B]'
                    : daysUntilDeadline < 30
                    ? 'bg-[#A16207]'
                    : 'bg-[#166534]'
                }`} />
                <p className="text-sm text-[#09090B]">
                  Appeal deadline: <span className="font-medium">
                    {dashboardData?.appeal_deadline
                      ? format(new Date(dashboardData.appeal_deadline), 'MMMM d, yyyy')
                      : 'March 1, 2026'}
                  </span>
                </p>
              </div>
              <p className={`text-sm font-semibold tabular-nums ${
                daysUntilDeadline < 14
                  ? 'text-[#991B1B]'
                  : daysUntilDeadline < 30
                  ? 'text-[#A16207]'
                  : 'text-[#09090B]'
              }`}>
                {dashboardData?.days_until_deadline || daysUntilDeadline} days remaining
              </p>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
