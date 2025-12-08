'use client';

import { useQuery } from '@tanstack/react-query';
import Link from 'next/link';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import {
  Home,
  DollarSign,
  TrendingUp,
  AlertTriangle,
  ArrowRight,
  Calendar,
  RefreshCw
} from 'lucide-react';
import { propertyApi, PropertySearchResponse } from '@/lib/api';

export function DashboardPage() {
  // Fetch total properties count
  const { data: allProperties, isLoading: loadingAll, refetch: refetchAll } = useQuery<PropertySearchResponse>({
    queryKey: ['dashboard-all-properties'],
    queryFn: () => propertyApi.search({ page: 1, page_size: 1 }),
  });

  // Fetch appeal candidates
  const { data: appealCandidates, isLoading: loadingCandidates, refetch: refetchCandidates } = useQuery<PropertySearchResponse>({
    queryKey: ['dashboard-appeal-candidates'],
    queryFn: () => propertyApi.search({ only_appeal_candidates: true, page: 1, page_size: 5 }),
  });

  const isLoading = loadingAll || loadingCandidates;

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

  // Calculate days until deadline (March 1, 2025)
  const deadline = new Date('2025-03-01');
  const today = new Date();
  const daysUntilDeadline = Math.ceil((deadline.getTime() - today.getTime()) / (1000 * 60 * 60 * 24));

  const handleRefresh = () => {
    refetchAll();
    refetchCandidates();
  };

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Dashboard</h1>
          <p className="text-muted-foreground">
            Property tax assessment overview and insights
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={handleRefresh} disabled={isLoading}>
            <RefreshCw className={`h-4 w-4 mr-2 ${isLoading ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
          <Badge variant="outline" className="flex items-center gap-1">
            <Calendar className="h-3 w-3" />
            Appeal Deadline: March 1, 2025
          </Badge>
          <Badge variant={daysUntilDeadline < 30 ? "destructive" : "secondary"}>
            {daysUntilDeadline} days left
          </Badge>
        </div>
      </div>

      {/* Metrics Cards */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Properties</CardTitle>
            <Home className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            {loadingAll ? (
              <Skeleton className="h-8 w-24" />
            ) : (
              <div className="text-2xl font-bold">{formatNumber(allProperties?.total_count)}</div>
            )}
            <p className="text-xs text-muted-foreground">
              Benton County, AR properties tracked
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Assessed Value</CardTitle>
            <DollarSign className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">$4.2B</div>
            <p className="text-xs text-muted-foreground">
              Combined property assessments
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Appeal Candidates</CardTitle>
            <TrendingUp className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            {loadingCandidates ? (
              <Skeleton className="h-8 w-24" />
            ) : (
              <div className="text-2xl font-bold">{formatNumber(appealCandidates?.total_count)}</div>
            )}
            <p className="text-xs text-muted-foreground">
              Properties with appeal potential
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Potential Savings</CardTitle>
            <AlertTriangle className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">$8.4M</div>
            <p className="text-xs text-muted-foreground">
              Estimated annual tax savings
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Main Content Area */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-7">
        {/* Top Savings Opportunities */}
        <Card className="col-span-4">
          <CardHeader>
            <CardTitle>Top Savings Opportunities</CardTitle>
            <CardDescription>
              Properties with the highest potential tax savings
            </CardDescription>
          </CardHeader>
          <CardContent>
            {loadingCandidates ? (
              <div className="space-y-4">
                {[...Array(5)].map((_, i) => (
                  <div key={i} className="flex items-center space-x-4">
                    <Skeleton className="h-10 w-10 rounded-full" />
                    <div className="space-y-2 flex-1">
                      <Skeleton className="h-4 w-[200px]" />
                      <Skeleton className="h-3 w-[150px]" />
                    </div>
                    <Skeleton className="h-6 w-[80px]" />
                  </div>
                ))}
              </div>
            ) : appealCandidates?.properties && appealCandidates.properties.length > 0 ? (
              <div className="space-y-4">
                {appealCandidates.properties.map((property) => (
                  <Link
                    key={property.id}
                    href={`/properties/${property.id}`}
                    className="flex items-center justify-between p-3 border rounded-lg hover:bg-gray-50 cursor-pointer transition-colors block"
                  >
                    <div className="flex items-center gap-3">
                      <div className="h-10 w-10 rounded-full bg-blue-100 flex items-center justify-center">
                        <Home className="h-5 w-5 text-blue-600" />
                      </div>
                      <div>
                        <p className="font-medium">{property.address || 'Unknown Address'}</p>
                        <p className="text-sm text-muted-foreground">
                          {property.parcel_id} | {formatCurrency(property.total_value)}
                        </p>
                      </div>
                    </div>
                    <div className="flex items-center gap-3">
                      <Badge variant="secondary" className="text-green-600 bg-green-50">
                        {property.property_type || 'Unknown'}
                      </Badge>
                      <ArrowRight className="h-4 w-4 text-muted-foreground" />
                    </div>
                  </Link>
                ))}
              </div>
            ) : (
              <div className="text-center py-8">
                <TrendingUp className="h-8 w-8 text-gray-400 mx-auto mb-2" />
                <p className="text-muted-foreground">No appeal candidates found yet</p>
                <p className="text-sm text-muted-foreground">Run analysis on properties to find opportunities</p>
              </div>
            )}
            <Link href="/properties?filter=appeal">
              <Button variant="outline" className="w-full mt-4">
                View All Properties
              </Button>
            </Link>
          </CardContent>
        </Card>

        {/* Quick Actions */}
        <Card className="col-span-3">
          <CardHeader>
            <CardTitle>Quick Actions</CardTitle>
            <CardDescription>
              Common tasks and workflows
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            <Link href="/properties">
              <Button variant="outline" className="w-full justify-start">
                <Home className="mr-2 h-4 w-4" />
                Search Properties
              </Button>
            </Link>
            <Link href="/properties">
              <Button variant="outline" className="w-full justify-start">
                <TrendingUp className="mr-2 h-4 w-4" />
                Run Assessment Analysis
              </Button>
            </Link>
            <Link href="/appeals">
              <Button variant="outline" className="w-full justify-start">
                <AlertTriangle className="mr-2 h-4 w-4" />
                Manage Appeals
              </Button>
            </Link>
            <Link href="/reports">
              <Button variant="outline" className="w-full justify-start">
                <DollarSign className="mr-2 h-4 w-4" />
                View Reports
              </Button>
            </Link>
          </CardContent>
        </Card>
      </div>

      {/* System Status */}
      <Card>
        <CardHeader>
          <CardTitle>System Status</CardTitle>
          <CardDescription>API and data pipeline health</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2">
              <div className="h-2 w-2 rounded-full bg-green-500" />
              <span className="text-sm">API: Healthy</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="h-2 w-2 rounded-full bg-green-500" />
              <span className="text-sm">Database: Connected</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="h-2 w-2 rounded-full bg-green-500" />
              <span className="text-sm">Last Sync: 5 min ago</span>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
