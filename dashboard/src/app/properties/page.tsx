'use client';

import { useState, Suspense } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useRouter, useSearchParams } from 'next/navigation';
import Link from 'next/link';
import { MainLayout } from '@/components/layout/main-layout';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import {
  Search,
  ChevronLeft,
  ChevronRight,
  AlertTriangle,
  Home,
  Filter,
  X,
  RefreshCw,
  Grid,
  List,
  MoreHorizontal,
  TrendingUp,
  FileText,
  Briefcase,
  ChevronUp,
  ChevronDown,
} from 'lucide-react';
import { propertyApi, analysisApi, PropertySearchParams, PropertySearchResponse } from '@/lib/api';
import { AddToPortfolioDialog } from '@/components/portfolio/add-to-portfolio-dialog';
import { toast } from 'sonner';

type SortField = 'address' | 'total_value' | 'assessed_value' | 'owner_name';
type ViewMode = 'table' | 'grid';

function PropertiesPageContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const queryClient = useQueryClient();

  // State
  const [searchQuery, setSearchQuery] = useState(searchParams.get('query') || '');
  const [page, setPage] = useState(1);
  const [pageSize] = useState(20);
  const [onlyAppealCandidates, setOnlyAppealCandidates] = useState(
    searchParams.get('filter') === 'appeal'
  );
  const [showFilters, setShowFilters] = useState(false);
  const [viewMode, setViewMode] = useState<ViewMode>('table');
  const [sortBy, setSortBy] = useState<SortField>('total_value');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc');
  const [minValue, setMinValue] = useState('');
  const [maxValue, setMaxValue] = useState('');
  const [city, setCity] = useState('');

  // Portfolio dialog state
  const [portfolioDialogOpen, setPortfolioDialogOpen] = useState(false);
  const [selectedPropertyForPortfolio, setSelectedPropertyForPortfolio] = useState<{
    id: string;
    parcelId: string;
    address: string;
  } | null>(null);

  // Build search params
  const searchApiParams: PropertySearchParams = {
    query: searchQuery || undefined,
    page,
    page_size: pageSize,
    only_appeal_candidates: onlyAppealCandidates,
    sort_by: sortBy,
    sort_order: sortOrder,
    min_value: minValue ? parseInt(minValue) : undefined,
    max_value: maxValue ? parseInt(maxValue) : undefined,
    city: city || undefined,
  };

  // Fetch properties
  const { data, isLoading, error, refetch, isFetching } = useQuery<PropertySearchResponse>({
    queryKey: ['properties', searchApiParams],
    queryFn: () => propertyApi.search(searchApiParams),
  });

  // Analysis mutation
  const analyzeMutation = useMutation({
    mutationFn: (propertyId: string) => analysisApi.analyze(propertyId, { force_refresh: true }),
    onSuccess: () => {
      toast.success('Analysis started');
      queryClient.invalidateQueries({ queryKey: ['properties'] });
    },
    onError: (error) => {
      toast.error('Analysis failed: ' + (error instanceof Error ? error.message : 'Unknown error'));
    },
  });

  // Handle search submit
  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    setPage(1);
    refetch();
  };

  // Handle clear search
  const handleClearSearch = () => {
    setSearchQuery('');
    setPage(1);
  };

  // Handle filter reset
  const handleResetFilters = () => {
    setSearchQuery('');
    setOnlyAppealCandidates(false);
    setMinValue('');
    setMaxValue('');
    setCity('');
    setSortBy('total_value');
    setSortOrder('desc');
    setPage(1);
  };

  // Handle apply filters
  const handleApplyFilters = () => {
    setPage(1);
    refetch();
    setShowFilters(false);
  };

  // Handle sort
  const handleSort = (field: SortField) => {
    if (sortBy === field) {
      setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc');
    } else {
      setSortBy(field);
      setSortOrder('desc');
    }
    setPage(1);
  };

  // Handle add to portfolio
  const handleAddToPortfolio = (propertyId: string, parcelId: string, address: string) => {
    setSelectedPropertyForPortfolio({ id: propertyId, parcelId, address });
    setPortfolioDialogOpen(true);
  };

  // Handle analyze
  const handleAnalyze = (propertyId: string) => {
    analyzeMutation.mutate(propertyId);
  };

  // Format currency
  const formatCurrency = (value: number | null) => {
    if (value === null || value === undefined) return 'N/A';
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      maximumFractionDigits: 0,
    }).format(value);
  };

  // Sort icon component
  const SortIcon = ({ field }: { field: SortField }) => {
    if (sortBy !== field) return null;
    return sortOrder === 'asc' ? (
      <ChevronUp className="h-4 w-4 ml-1 inline" />
    ) : (
      <ChevronDown className="h-4 w-4 ml-1 inline" />
    );
  };

  // Count active filters
  const activeFilterCount = [
    onlyAppealCandidates,
    minValue,
    maxValue,
    city,
  ].filter(Boolean).length;

  return (
    <MainLayout>
      <div className="space-y-6">
        {/* Page Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold tracking-tight">Properties</h1>
            <p className="text-muted-foreground">
              Search and analyze property assessments
            </p>
          </div>
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => refetch()}
              disabled={isFetching}
            >
              <RefreshCw className={`h-4 w-4 mr-2 ${isFetching ? 'animate-spin' : ''}`} />
              Refresh
            </Button>
          </div>
        </div>

        {/* Search and Filters */}
        <Card>
          <CardHeader>
            <CardTitle>Search Properties</CardTitle>
            <CardDescription>
              Search by address, owner name, or parcel ID
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <form onSubmit={handleSearch} className="flex gap-4">
              <div className="flex-1 relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                <Input
                  placeholder="Enter address, owner name, or parcel ID..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="pl-10 pr-10"
                />
                {searchQuery && (
                  <button
                    type="button"
                    onClick={handleClearSearch}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                  >
                    <X className="h-4 w-4" />
                  </button>
                )}
              </div>
              <Select
                value={onlyAppealCandidates ? 'appeal' : 'all'}
                onValueChange={(value) => setOnlyAppealCandidates(value === 'appeal')}
              >
                <SelectTrigger className="w-[200px]">
                  <SelectValue placeholder="Filter" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Properties</SelectItem>
                  <SelectItem value="appeal">Appeal Candidates Only</SelectItem>
                </SelectContent>
              </Select>
              <Button
                type="button"
                variant="outline"
                onClick={() => setShowFilters(!showFilters)}
                className="relative"
              >
                <Filter className="h-4 w-4 mr-2" />
                Filters
                {activeFilterCount > 0 && (
                  <Badge className="ml-2 h-5 w-5 p-0 flex items-center justify-center text-xs">
                    {activeFilterCount}
                  </Badge>
                )}
              </Button>
              <Button type="submit" disabled={isFetching}>
                Search
              </Button>
            </form>

            {/* Advanced Filters Panel */}
            {showFilters && (
              <div className="border rounded-lg p-4 space-y-4 bg-gray-50">
                <div className="grid md:grid-cols-4 gap-4">
                  <div className="space-y-2">
                    <label className="text-sm font-medium">Min Value</label>
                    <Input
                      type="number"
                      placeholder="$0"
                      value={minValue}
                      onChange={(e) => setMinValue(e.target.value)}
                    />
                  </div>
                  <div className="space-y-2">
                    <label className="text-sm font-medium">Max Value</label>
                    <Input
                      type="number"
                      placeholder="No limit"
                      value={maxValue}
                      onChange={(e) => setMaxValue(e.target.value)}
                    />
                  </div>
                  <div className="space-y-2">
                    <label className="text-sm font-medium">City</label>
                    <Input
                      placeholder="Any city"
                      value={city}
                      onChange={(e) => setCity(e.target.value)}
                    />
                  </div>
                  <div className="flex items-end gap-2">
                    <Button onClick={handleApplyFilters} className="flex-1">
                      Apply Filters
                    </Button>
                    <Button variant="outline" onClick={handleResetFilters}>
                      Reset
                    </Button>
                  </div>
                </div>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Results */}
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle>Results</CardTitle>
                {data && (
                  <CardDescription>
                    Showing {data.properties.length} of {data.total_count.toLocaleString()} properties
                  </CardDescription>
                )}
              </div>
              <div className="flex items-center gap-2">
                <Button
                  variant={viewMode === 'table' ? 'default' : 'outline'}
                  size="sm"
                  onClick={() => setViewMode('table')}
                >
                  <List className="h-4 w-4" />
                </Button>
                <Button
                  variant={viewMode === 'grid' ? 'default' : 'outline'}
                  size="sm"
                  onClick={() => setViewMode('grid')}
                >
                  <Grid className="h-4 w-4" />
                </Button>
              </div>
            </div>
          </CardHeader>
          <CardContent>
            {/* Loading State */}
            {isLoading && (
              <div className="space-y-4">
                {[...Array(5)].map((_, i) => (
                  <div key={i} className="flex items-center space-x-4">
                    <Skeleton className="h-12 w-12 rounded-full" />
                    <div className="space-y-2 flex-1">
                      <Skeleton className="h-4 w-[250px]" />
                      <Skeleton className="h-4 w-[200px]" />
                    </div>
                    <Skeleton className="h-8 w-[100px]" />
                  </div>
                ))}
              </div>
            )}

            {/* Error State */}
            {error && (
              <div className="text-center py-10">
                <AlertTriangle className="h-10 w-10 text-red-500 mx-auto mb-4" />
                <h3 className="text-lg font-medium text-gray-900">Error loading properties</h3>
                <p className="text-gray-500 mt-2">
                  {error instanceof Error ? error.message : 'Something went wrong'}
                </p>
                <Button onClick={() => refetch()} variant="outline" className="mt-4">
                  Try Again
                </Button>
              </div>
            )}

            {/* Empty State */}
            {data && data.properties.length === 0 && (
              <div className="text-center py-10">
                <Home className="h-10 w-10 text-gray-400 mx-auto mb-4" />
                <h3 className="text-lg font-medium text-gray-900">No properties found</h3>
                <p className="text-gray-500 mt-2">
                  Try adjusting your search or filters
                </p>
                <Button variant="outline" onClick={handleResetFilters} className="mt-4">
                  Reset Filters
                </Button>
              </div>
            )}

            {/* Table View */}
            {data && data.properties.length > 0 && viewMode === 'table' && (
              <>
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead
                        className="cursor-pointer hover:bg-gray-50"
                        onClick={() => handleSort('address')}
                      >
                        Address <SortIcon field="address" />
                      </TableHead>
                      <TableHead>Parcel ID</TableHead>
                      <TableHead
                        className="cursor-pointer hover:bg-gray-50"
                        onClick={() => handleSort('owner_name')}
                      >
                        Owner <SortIcon field="owner_name" />
                      </TableHead>
                      <TableHead
                        className="text-right cursor-pointer hover:bg-gray-50"
                        onClick={() => handleSort('total_value')}
                      >
                        Market Value <SortIcon field="total_value" />
                      </TableHead>
                      <TableHead
                        className="text-right cursor-pointer hover:bg-gray-50"
                        onClick={() => handleSort('assessed_value')}
                      >
                        Assessed Value <SortIcon field="assessed_value" />
                      </TableHead>
                      <TableHead>Type</TableHead>
                      <TableHead></TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {data.properties.map((property) => (
                      <TableRow key={property.id}>
                        <TableCell className="font-medium">
                          {property.address || 'N/A'}
                        </TableCell>
                        <TableCell className="text-muted-foreground">
                          {property.parcel_id}
                        </TableCell>
                        <TableCell className="max-w-[200px] truncate">
                          {property.owner_name || 'N/A'}
                        </TableCell>
                        <TableCell className="text-right">
                          {formatCurrency(property.total_value)}
                        </TableCell>
                        <TableCell className="text-right">
                          {formatCurrency(property.assessed_value)}
                        </TableCell>
                        <TableCell>
                          <Badge variant="outline">
                            {property.property_type || 'Unknown'}
                          </Badge>
                        </TableCell>
                        <TableCell>
                          <div className="flex items-center gap-1">
                            <Link href={`/properties/${property.id}`}>
                              <Button variant="ghost" size="sm">
                                View
                              </Button>
                            </Link>
                            <DropdownMenu>
                              <DropdownMenuTrigger asChild>
                                <Button variant="ghost" size="sm">
                                  <MoreHorizontal className="h-4 w-4" />
                                </Button>
                              </DropdownMenuTrigger>
                              <DropdownMenuContent align="end">
                                <DropdownMenuItem
                                  onClick={() => handleAnalyze(property.id)}
                                  disabled={analyzeMutation.isPending}
                                >
                                  <TrendingUp className="h-4 w-4 mr-2" />
                                  Run Analysis
                                </DropdownMenuItem>
                                <DropdownMenuItem
                                  onClick={() => router.push(`/properties/${property.id}?tab=appeal`)}
                                >
                                  <FileText className="h-4 w-4 mr-2" />
                                  Generate Appeal
                                </DropdownMenuItem>
                                <DropdownMenuItem
                                  onClick={() =>
                                    handleAddToPortfolio(
                                      property.id,
                                      property.parcel_id,
                                      property.address || ''
                                    )
                                  }
                                >
                                  <Briefcase className="h-4 w-4 mr-2" />
                                  Add to Portfolio
                                </DropdownMenuItem>
                              </DropdownMenuContent>
                            </DropdownMenu>
                          </div>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>

                {/* Pagination */}
                <div className="flex items-center justify-between mt-4">
                  <p className="text-sm text-muted-foreground">
                    Page {data.page} of {data.total_pages}
                  </p>
                  <div className="flex gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setPage((p) => Math.max(1, p - 1))}
                      disabled={page === 1 || isFetching}
                    >
                      <ChevronLeft className="h-4 w-4 mr-1" />
                      Previous
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setPage((p) => p + 1)}
                      disabled={!data.has_more || isFetching}
                    >
                      Next
                      <ChevronRight className="h-4 w-4 ml-1" />
                    </Button>
                  </div>
                </div>
              </>
            )}

            {/* Grid View */}
            {data && data.properties.length > 0 && viewMode === 'grid' && (
              <>
                <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
                  {data.properties.map((property) => (
                    <Card key={property.id} className="hover:shadow-md transition-shadow">
                      <CardHeader className="pb-2">
                        <div className="flex items-start justify-between">
                          <div className="flex items-center gap-2">
                            <div className="h-10 w-10 rounded-lg bg-blue-100 flex items-center justify-center">
                              <Home className="h-5 w-5 text-blue-600" />
                            </div>
                            <div>
                              <CardTitle className="text-sm">
                                {property.address || 'Unknown Address'}
                              </CardTitle>
                              <CardDescription>{property.parcel_id}</CardDescription>
                            </div>
                          </div>
                          <Badge variant="outline">
                            {property.property_type || 'Unknown'}
                          </Badge>
                        </div>
                      </CardHeader>
                      <CardContent className="space-y-3">
                        <div className="grid grid-cols-2 gap-2 text-sm">
                          <div>
                            <p className="text-muted-foreground">Market Value</p>
                            <p className="font-medium">{formatCurrency(property.total_value)}</p>
                          </div>
                          <div>
                            <p className="text-muted-foreground">Assessed</p>
                            <p className="font-medium">{formatCurrency(property.assessed_value)}</p>
                          </div>
                        </div>
                        <p className="text-sm text-muted-foreground truncate">
                          Owner: {property.owner_name || 'N/A'}
                        </p>
                        <div className="flex gap-2">
                          <Link href={`/properties/${property.id}`} className="flex-1">
                            <Button variant="outline" size="sm" className="w-full">
                              View
                            </Button>
                          </Link>
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => handleAnalyze(property.id)}
                            disabled={analyzeMutation.isPending}
                          >
                            <TrendingUp className="h-4 w-4" />
                          </Button>
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() =>
                              handleAddToPortfolio(
                                property.id,
                                property.parcel_id,
                                property.address || ''
                              )
                            }
                          >
                            <Briefcase className="h-4 w-4" />
                          </Button>
                        </div>
                      </CardContent>
                    </Card>
                  ))}
                </div>

                {/* Pagination */}
                <div className="flex items-center justify-between mt-4">
                  <p className="text-sm text-muted-foreground">
                    Page {data.page} of {data.total_pages}
                  </p>
                  <div className="flex gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setPage((p) => Math.max(1, p - 1))}
                      disabled={page === 1 || isFetching}
                    >
                      <ChevronLeft className="h-4 w-4 mr-1" />
                      Previous
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setPage((p) => p + 1)}
                      disabled={!data.has_more || isFetching}
                    >
                      Next
                      <ChevronRight className="h-4 w-4 ml-1" />
                    </Button>
                  </div>
                </div>
              </>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Add to Portfolio Dialog */}
      {selectedPropertyForPortfolio && (
        <AddToPortfolioDialog
          open={portfolioDialogOpen}
          onOpenChange={setPortfolioDialogOpen}
          propertyId={selectedPropertyForPortfolio.id}
          parcelId={selectedPropertyForPortfolio.parcelId}
          propertyAddress={selectedPropertyForPortfolio.address}
        />
      )}
    </MainLayout>
  );
}

// Loading fallback
function PropertiesPageFallback() {
  return (
    <MainLayout>
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <Skeleton className="h-10 w-48" />
            <Skeleton className="h-4 w-64 mt-2" />
          </div>
        </div>
        <Card>
          <CardHeader>
            <Skeleton className="h-6 w-40" />
            <Skeleton className="h-4 w-60" />
          </CardHeader>
          <CardContent>
            <Skeleton className="h-10 w-full" />
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="space-y-4">
              {[...Array(5)].map((_, i) => (
                <div key={i} className="flex items-center space-x-4">
                  <Skeleton className="h-12 w-12 rounded-full" />
                  <div className="space-y-2 flex-1">
                    <Skeleton className="h-4 w-[250px]" />
                    <Skeleton className="h-4 w-[200px]" />
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>
    </MainLayout>
  );
}

export default function PropertiesPage() {
  return (
    <Suspense fallback={<PropertiesPageFallback />}>
      <PropertiesPageContent />
    </Suspense>
  );
}
