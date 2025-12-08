'use client';

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import Link from 'next/link';
import { MainLayout } from '@/components/layout/main-layout';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { Input } from '@/components/ui/input';
import {
  Briefcase,
  Plus,
  Home,
  DollarSign,
  TrendingUp,
  AlertTriangle,
  Search,
} from 'lucide-react';
import { portfolioApi, PortfolioSummary, APIResponse } from '@/lib/api';

export default function PortfolioPage() {
  const [searchQuery, setSearchQuery] = useState('');

  // For now we'll use a demo user ID - in production this would come from auth
  const userId = 'demo-user';

  const { data, isLoading, error, refetch } = useQuery<APIResponse<PortfolioSummary[]>>({
    queryKey: ['portfolios', userId],
    queryFn: () => portfolioApi.list(userId),
  });

  const portfolios = data?.data || [];

  const filteredPortfolios = portfolios.filter(p =>
    p.name.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const formatCurrency = (value: number | null | undefined) => {
    if (value === null || value === undefined) return 'N/A';
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      maximumFractionDigits: 0,
    }).format(value);
  };

  const formatDate = (dateString: string | undefined) => {
    if (!dateString) return 'N/A';
    return new Date(dateString).toLocaleDateString();
  };

  return (
    <MainLayout>
      <div className="space-y-6">
        {/* Page Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold tracking-tight">Portfolio</h1>
            <p className="text-muted-foreground">
              Manage your property portfolios
            </p>
          </div>
          <Button>
            <Plus className="h-4 w-4 mr-2" />
            Create Portfolio
          </Button>
        </div>

        {/* Search */}
        <Card>
          <CardContent className="pt-6">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder="Search portfolios..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-10"
              />
            </div>
          </CardContent>
        </Card>

        {/* Loading State */}
        {isLoading && (
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {[...Array(3)].map((_, i) => (
              <Card key={i}>
                <CardHeader>
                  <Skeleton className="h-6 w-[150px]" />
                  <Skeleton className="h-4 w-[100px]" />
                </CardHeader>
                <CardContent>
                  <Skeleton className="h-8 w-[120px]" />
                </CardContent>
              </Card>
            ))}
          </div>
        )}

        {/* Error State */}
        {error && (
          <Card>
            <CardContent className="py-10">
              <div className="text-center">
                <AlertTriangle className="h-10 w-10 text-red-500 mx-auto mb-4" />
                <h3 className="text-lg font-medium text-gray-900">Error loading portfolios</h3>
                <p className="text-gray-500 mt-2">
                  {error instanceof Error ? error.message : 'Something went wrong'}
                </p>
                <Button onClick={() => refetch()} variant="outline" className="mt-4">
                  Try Again
                </Button>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Empty State */}
        {!isLoading && !error && filteredPortfolios.length === 0 && (
          <Card>
            <CardContent className="py-10">
              <div className="text-center">
                <Briefcase className="h-10 w-10 text-gray-400 mx-auto mb-4" />
                <h3 className="text-lg font-medium text-gray-900">No portfolios found</h3>
                <p className="text-gray-500 mt-2">
                  {searchQuery
                    ? 'Try adjusting your search'
                    : 'Create a portfolio to start tracking properties'}
                </p>
                {!searchQuery && (
                  <Button className="mt-4">
                    <Plus className="h-4 w-4 mr-2" />
                    Create Your First Portfolio
                  </Button>
                )}
              </div>
            </CardContent>
          </Card>
        )}

        {/* Portfolio Cards */}
        {!isLoading && !error && filteredPortfolios.length > 0 && (
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {filteredPortfolios.map((portfolio) => (
              <Card key={portfolio.id} className="hover:shadow-md transition-shadow">
                <CardHeader>
                  <div className="flex items-start justify-between">
                    <div>
                      <CardTitle className="text-lg">{portfolio.name}</CardTitle>
                      <CardDescription>
                        Created {formatDate(portfolio.created_at)}
                      </CardDescription>
                    </div>
                    <div className="h-10 w-10 rounded-lg bg-blue-100 flex items-center justify-center">
                      <Briefcase className="h-5 w-5 text-blue-600" />
                    </div>
                  </div>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <div className="flex items-center gap-1 text-sm text-muted-foreground">
                        <Home className="h-3 w-3" />
                        Properties
                      </div>
                      <div className="text-xl font-bold">{portfolio.property_count}</div>
                    </div>
                    <div>
                      <div className="flex items-center gap-1 text-sm text-muted-foreground">
                        <DollarSign className="h-3 w-3" />
                        Total Value
                      </div>
                      <div className="text-xl font-bold">{formatCurrency(portfolio.total_value)}</div>
                    </div>
                  </div>
                  <Link href={`/portfolio/${portfolio.id}`}>
                    <Button variant="outline" className="w-full">
                      View Portfolio
                    </Button>
                  </Link>
                </CardContent>
              </Card>
            ))}
          </div>
        )}

        {/* Quick Stats */}
        {!isLoading && !error && portfolios.length > 0 && (
          <Card>
            <CardHeader>
              <CardTitle>Portfolio Summary</CardTitle>
              <CardDescription>
                Overview of all your portfolios
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="grid gap-4 md:grid-cols-4">
                <div className="text-center p-4 bg-gray-50 rounded-lg">
                  <div className="text-2xl font-bold">{portfolios.length}</div>
                  <div className="text-sm text-muted-foreground">Total Portfolios</div>
                </div>
                <div className="text-center p-4 bg-gray-50 rounded-lg">
                  <div className="text-2xl font-bold">
                    {portfolios.reduce((sum, p) => sum + p.property_count, 0)}
                  </div>
                  <div className="text-sm text-muted-foreground">Total Properties</div>
                </div>
                <div className="text-center p-4 bg-gray-50 rounded-lg">
                  <div className="text-2xl font-bold text-blue-600">
                    {formatCurrency(portfolios.reduce((sum, p) => sum + p.total_value, 0))}
                  </div>
                  <div className="text-sm text-muted-foreground">Total Value</div>
                </div>
                <div className="text-center p-4 bg-gray-50 rounded-lg">
                  <div className="text-2xl font-bold text-green-600">
                    <TrendingUp className="h-6 w-6 mx-auto" />
                  </div>
                  <div className="text-sm text-muted-foreground">Performance</div>
                </div>
              </div>
            </CardContent>
          </Card>
        )}
      </div>
    </MainLayout>
  );
}
