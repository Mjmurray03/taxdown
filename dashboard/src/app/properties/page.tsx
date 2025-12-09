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
  MoreHorizontal,
  TrendingUp,
  FileText,
  Briefcase,
  ChevronUp,
  ChevronDown,
} from 'lucide-react';
import { propertyApi, analysisApi, PropertySearchParams, PropertySearchResponse, AddressSuggestion } from '@/lib/api';
import { AddToPortfolioDialog } from '@/components/portfolio/add-to-portfolio-dialog';
import { toast } from 'sonner';
import { useDebounce } from '@/lib/hooks';

type SortField = 'address' | 'value' | 'assessed_value' | 'fairness_score';

function PropertiesPageContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const queryClient = useQueryClient();

  // State
  const [searchQuery, setSearchQuery] = useState(searchParams.get('query') || '');
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [page, setPage] = useState(1);
  const [pageSize] = useState(20);
  const [onlyAppealCandidates, setOnlyAppealCandidates] = useState(
    searchParams.get('filter') === 'appeal'
  );
  const [showFilters, setShowFilters] = useState(false);
  const [sortBy, setSortBy] = useState<SortField>('address');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('asc');
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

  // Debounced search for autocomplete
  const debouncedSearchQuery = useDebounce(searchQuery, 300);

  // Fetch autocomplete suggestions
  const { data: suggestions } = useQuery<AddressSuggestion[]>({
    queryKey: ['autocomplete', debouncedSearchQuery],
    queryFn: () => propertyApi.autocomplete(debouncedSearchQuery),
    enabled: debouncedSearchQuery.length >= 3 && showSuggestions,
  });

  // Analysis mutation
  const analyzeMutation = useMutation({
    mutationFn: (propertyId: string) => analysisApi.analyze(propertyId, { force_refresh: true }),
    onSuccess: () => {
      toast.success('Analysis completed');
      queryClient.invalidateQueries({ queryKey: ['properties'] });
    },
    onError: (error: any) => {
      // Extract error message from Axios error response
      const message = error?.response?.data?.detail || error?.message || 'Unknown error';
      toast.error(message);
    },
  });

  // Handle search submit
  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    setPage(1);
    setShowSuggestions(false);
    refetch();
  };

  // Handle clear search
  const handleClearSearch = () => {
    setSearchQuery('');
    setPage(1);
    setShowSuggestions(false);
  };

  // Handle suggestion select
  const handleSuggestionSelect = (suggestion: AddressSuggestion) => {
    setSearchQuery(suggestion.address);
    setShowSuggestions(false);
    setPage(1);
  };

  // Handle filter reset
  const handleResetFilters = () => {
    setSearchQuery('');
    setOnlyAppealCandidates(false);
    setMinValue('');
    setMaxValue('');
    setCity('');
    setSortBy('value');
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
      <ChevronUp className="h-3 w-3 ml-1 inline" />
    ) : (
      <ChevronDown className="h-3 w-3 ml-1 inline" />
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
      <div className="space-y-8">
        {/* Page Header */}
        <div className="flex items-end justify-between">
          <div>
            <h1 className="text-4xl font-semibold tracking-tight text-[#09090B]">Properties</h1>
            <p className="mt-1 text-sm text-[#71717A]">
              Search and analyze property assessments
            </p>
          </div>
        </div>

        {/* Search Bar */}
        <div className="flex gap-4">
          <div className="flex-1 relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-[#71717A]" />
            <Input
              placeholder="Search by address, owner, or parcel ID..."
              value={searchQuery}
              onChange={(e) => {
                setSearchQuery(e.target.value);
                setShowSuggestions(true);
              }}
              onKeyDown={(e) => e.key === 'Enter' && handleSearch(e as any)}
              onFocus={() => setShowSuggestions(true)}
              onBlur={() => setTimeout(() => setShowSuggestions(false), 200)}
              className="pl-10 pr-10 h-10"
            />
            {searchQuery && (
              <button
                type="button"
                onClick={handleClearSearch}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-[#71717A] hover:text-[#18181B]"
              >
                <X className="h-4 w-4" />
              </button>
            )}

            {/* Autocomplete Suggestions */}
            {showSuggestions && suggestions && suggestions.length > 0 && (
              <div className="absolute top-full left-0 right-0 mt-1 bg-white border border-[#E4E4E7] rounded-md shadow-lg z-50 max-h-60 overflow-y-auto">
                {suggestions.map((suggestion) => (
                  <button
                    key={suggestion.property_id}
                    type="button"
                    onClick={() => handleSuggestionSelect(suggestion)}
                    className="w-full px-4 py-3 text-left hover:bg-[#FAFAF9] transition-standard border-b border-[#E4E4E7] last:border-b-0"
                  >
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="text-sm font-medium text-[#09090B]">{suggestion.address}</p>
                        <p className="text-xs text-[#71717A]">
                          {suggestion.city || 'Unknown City'} | {suggestion.parcel_id}
                        </p>
                      </div>
                      <Badge variant="outline" className="text-xs">
                        {Math.round(suggestion.match_score * 100)}% match
                      </Badge>
                    </div>
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Filter Bar */}
        <div className="flex items-center gap-4">
          <Select
            value={onlyAppealCandidates ? 'appeal' : 'all'}
            onValueChange={(value) => {
              setOnlyAppealCandidates(value === 'appeal');
              setPage(1);
            }}
          >
            <SelectTrigger className="w-[180px]">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Properties</SelectItem>
              <SelectItem value="appeal">Appeal Candidates</SelectItem>
            </SelectContent>
          </Select>

          <Select
            value={`${minValue || '0'}-${maxValue || 'max'}`}
            onValueChange={(value) => {
              if (value === 'all') {
                setMinValue('');
                setMaxValue('');
              } else if (value === '0-250000') {
                setMinValue('0');
                setMaxValue('250000');
              } else if (value === '250000-500000') {
                setMinValue('250000');
                setMaxValue('500000');
              } else if (value === '500000-max') {
                setMinValue('500000');
                setMaxValue('');
              }
              setPage(1);
            }}
          >
            <SelectTrigger className="w-[180px]">
              <SelectValue placeholder="Value Range" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Values</SelectItem>
              <SelectItem value="0-250000">Under $250K</SelectItem>
              <SelectItem value="250000-500000">$250K - $500K</SelectItem>
              <SelectItem value="500000-max">Over $500K</SelectItem>
            </SelectContent>
          </Select>

          {activeFilterCount > 0 && (
            <Button variant="ghost" onClick={handleResetFilters}>
              Clear Filters
            </Button>
          )}

          <div className="ml-auto text-sm text-[#71717A]">
            {data && <span className="font-medium tabular-nums">{data.total_count.toLocaleString()}</span>} properties
          </div>
        </div>

        {/* Results Table */}
        <Card>
          <CardContent className="p-0">
            {/* Loading State */}
            {isLoading && (
              <div className="p-6 space-y-4">
                {[...Array(8)].map((_, i) => (
                  <div key={i} className="flex items-center gap-4">
                    <Skeleton className="h-4 w-48" />
                    <Skeleton className="h-4 w-32" />
                    <Skeleton className="h-4 w-24 ml-auto" />
                  </div>
                ))}
              </div>
            )}

            {/* Error State */}
            {error && (
              <div className="text-center py-16">
                <AlertTriangle className="h-12 w-12 text-[#991B1B] mx-auto mb-4" />
                <h3 className="text-lg font-semibold text-[#09090B]">Error loading properties</h3>
                <p className="text-sm text-[#71717A] mt-2">
                  {error instanceof Error ? error.message : 'Something went wrong'}
                </p>
                <Button onClick={() => refetch()} variant="secondary" className="mt-6">
                  Try Again
                </Button>
              </div>
            )}

            {/* Empty State */}
            {data && data.properties.length === 0 && (
              <div className="text-center py-16">
                <Home className="h-12 w-12 text-[#D4D4D8] mx-auto mb-4" />
                <h3 className="text-lg font-semibold text-[#09090B]">No properties found</h3>
                <p className="text-sm text-[#71717A] mt-2">
                  Try adjusting your search or filters
                </p>
                <Button variant="secondary" onClick={handleResetFilters} className="mt-6">
                  Reset Filters
                </Button>
              </div>
            )}

            {/* Table View */}
            {data && data.properties.length > 0 && (
              <>
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead
                        className="cursor-pointer select-none"
                        onClick={() => handleSort('address')}
                      >
                        Address <SortIcon field="address" />
                      </TableHead>
                      <TableHead>Parcel ID</TableHead>
                      <TableHead>
                        Owner
                      </TableHead>
                      <TableHead
                        className="text-right cursor-pointer select-none"
                        onClick={() => handleSort('value')}
                      >
                        Market Value <SortIcon field="value" />
                      </TableHead>
                      <TableHead
                        className="text-right cursor-pointer select-none"
                        onClick={() => handleSort('assessed_value')}
                      >
                        Assessed Value <SortIcon field="assessed_value" />
                      </TableHead>
                      <TableHead>Status</TableHead>
                      <TableHead className="w-12"></TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {data.properties.map((property) => (
                      <TableRow key={property.id} className="group">
                        <TableCell className="font-medium">
                          <Link
                            href={`/properties/${property.id}`}
                            className="text-[#1E40AF] hover:underline"
                          >
                            {property.address || 'N/A'}
                          </Link>
                        </TableCell>
                        <TableCell className="text-[#71717A] font-mono text-xs">
                          {property.parcel_id}
                        </TableCell>
                        <TableCell className="max-w-[200px] truncate text-[#71717A]">
                          {property.owner_name || 'N/A'}
                        </TableCell>
                        <TableCell className="text-right font-mono tabular-nums">
                          {formatCurrency(property.total_value)}
                        </TableCell>
                        <TableCell className="text-right font-mono tabular-nums">
                          {formatCurrency(property.assessed_value)}
                        </TableCell>
                        <TableCell>
                          {property.is_appeal_candidate && (
                            <Badge variant="warning" className="text-xs">
                              Appeal Candidate
                            </Badge>
                          )}
                        </TableCell>
                        <TableCell>
                          <DropdownMenu>
                            <DropdownMenuTrigger asChild>
                              <Button variant="ghost" size="icon-sm" className="opacity-0 group-hover:opacity-100 transition-opacity">
                                <MoreHorizontal className="h-4 w-4" />
                              </Button>
                            </DropdownMenuTrigger>
                            <DropdownMenuContent align="end" className="w-48">
                              <DropdownMenuItem asChild>
                                <Link href={`/properties/${property.id}`} className="cursor-pointer">
                                  View Details
                                </Link>
                              </DropdownMenuItem>
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
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>

                {/* Pagination */}
                <div className="flex items-center justify-between px-6 py-4 border-t border-[#E4E4E7]">
                  <p className="text-sm text-[#71717A]">
                    Page <span className="font-medium tabular-nums">{data.page}</span> of <span className="font-medium tabular-nums">{data.total_pages}</span>
                  </p>
                  <div className="flex gap-2">
                    <Button
                      variant="secondary"
                      size="sm"
                      onClick={() => setPage((p) => Math.max(1, p - 1))}
                      disabled={page === 1 || isFetching}
                    >
                      <ChevronLeft className="h-4 w-4 mr-1" />
                      Previous
                    </Button>
                    <Button
                      variant="secondary"
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
      <div className="space-y-8">
        <div className="flex items-end justify-between">
          <div>
            <Skeleton className="h-10 w-48" />
            <Skeleton className="h-4 w-64 mt-2" />
          </div>
        </div>
        <Skeleton className="h-10 w-full" />
        <Card>
          <CardContent className="p-6">
            <div className="space-y-4">
              {[...Array(8)].map((_, i) => (
                <div key={i} className="flex items-center gap-4">
                  <Skeleton className="h-4 w-48" />
                  <Skeleton className="h-4 w-32" />
                  <Skeleton className="h-4 w-24 ml-auto" />
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
