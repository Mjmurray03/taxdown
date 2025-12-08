'use client';

import { useQuery } from '@tanstack/react-query';
import { portfolioApi } from '@/lib/api';
import { MetricsCards } from './metrics-cards';
import { SavingsChart } from './savings-chart';
import { TopOpportunities } from './top-opportunities';
import { DeadlineAlert } from './deadline-alert';
import { RecentActivity } from './recent-activity';
import { Skeleton } from '@/components/ui/skeleton';

// For MVP, use a default portfolio ID or the first one
const DEFAULT_PORTFOLIO_ID = process.env.NEXT_PUBLIC_DEFAULT_PORTFOLIO_ID;

export function DashboardPage() {
  const { data, isLoading, error } = useQuery({
    queryKey: ['dashboard', DEFAULT_PORTFOLIO_ID],
    queryFn: () => portfolioApi.getDashboard(DEFAULT_PORTFOLIO_ID!),
    enabled: !!DEFAULT_PORTFOLIO_ID,
  });

  if (!DEFAULT_PORTFOLIO_ID) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Dashboard</h1>
          <p className="text-muted-foreground">
            Welcome to Taxdown. Search for properties to get started.
          </p>
        </div>
        <QuickStartGuide />
      </div>
    );
  }

  if (isLoading) {
    return <DashboardSkeleton />;
  }

  if (error || !data?.data) {
    return (
      <div className="text-center py-12">
        <p className="text-red-500">Failed to load dashboard data</p>
      </div>
    );
  }

  const dashboard = data.data;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Dashboard</h1>
          <p className="text-muted-foreground">
            {dashboard.portfolio_name} • {dashboard.metrics.total_properties} properties
          </p>
        </div>

        {dashboard.days_until_deadline !== null && (
          <DeadlineAlert
            deadline={dashboard.appeal_deadline}
            daysRemaining={dashboard.days_until_deadline}
          />
        )}
      </div>

      {/* Metrics Cards */}
      <MetricsCards metrics={dashboard.metrics} />

      {/* Charts Row */}
      <div className="grid gap-6 md:grid-cols-2">
        <SavingsChart
          totalSavings={dashboard.metrics.total_potential_savings}
          appealCandidates={dashboard.metrics.appeal_candidates}
        />
        <TopOpportunities
          opportunities={dashboard.top_savings_opportunities}
        />
      </div>

      {/* Recent Activity */}
      <RecentActivity />
    </div>
  );
}

function QuickStartGuide() {
  return (
    <div className="rounded-lg border bg-card p-6">
      <h2 className="text-lg font-semibold mb-4">Get Started</h2>
      <div className="grid gap-4 md:grid-cols-3">
        <div className="p-4 rounded-lg bg-blue-50">
          <div className="text-2xl mb-2">1</div>
          <h3 className="font-medium">Search Properties</h3>
          <p className="text-sm text-muted-foreground">
            Find properties in Bella Vista by address, parcel ID, or owner name.
          </p>
        </div>
        <div className="p-4 rounded-lg bg-green-50">
          <div className="text-2xl mb-2">2</div>
          <h3 className="font-medium">Analyze Assessment</h3>
          <p className="text-sm text-muted-foreground">
            Our AI compares your property to similar ones to find over-assessments.
          </p>
        </div>
        <div className="p-4 rounded-lg bg-purple-50">
          <div className="text-2xl mb-2">3</div>
          <h3 className="font-medium">Generate Appeal</h3>
          <p className="text-sm text-muted-foreground">
            Get a ready-to-file appeal letter with supporting evidence.
          </p>
        </div>
      </div>
    </div>
  );
}

function DashboardSkeleton() {
  return (
    <div className="space-y-6">
      <Skeleton className="h-10 w-48" />
      <div className="grid gap-4 md:grid-cols-4">
        {[...Array(4)].map((_, i) => (
          <Skeleton key={i} className="h-32" />
        ))}
      </div>
      <div className="grid gap-6 md:grid-cols-2">
        <Skeleton className="h-80" />
        <Skeleton className="h-80" />
      </div>
    </div>
  );
}
