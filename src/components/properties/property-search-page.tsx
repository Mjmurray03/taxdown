'use client';

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { propertyApi, PropertySearchParams } from '@/lib/api';
import { PropertySearchBar } from './property-search-bar';
import { PropertyFilters } from './property-filters';
import { PropertyTable } from './property-table';
import { PropertyGrid } from './property-grid';
import { Button } from '@/components/ui/button';
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { LayoutGrid, List, Filter } from 'lucide-react';

export function PropertySearchPage() {
  const [viewMode, setViewMode] = useState<'table' | 'grid'>('table');
  const [showFilters, setShowFilters] = useState(false);
  const [searchParams, setSearchParams] = useState<PropertySearchParams>({
    page: 1,
    page_size: 20,
  });

  const { data, isLoading, error } = useQuery({
    queryKey: ['properties', searchParams],
    queryFn: () => propertyApi.search(searchParams),
  });

  const handleSearch = (query: string) => {
    setSearchParams((prev) => ({ ...prev, query, page: 1 }));
  };

  const handleFilterChange = (filters: Partial<PropertySearchParams>) => {
    setSearchParams((prev) => ({ ...prev, ...filters, page: 1 }));
  };

  const handlePageChange = (page: number) => {
    setSearchParams((prev) => ({ ...prev, page }));
  };

  const handleSort = (sortBy: string, sortOrder: 'asc' | 'desc') => {
    setSearchParams((prev) => ({ ...prev, sort_by: sortBy, sort_order: sortOrder }));
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Properties</h1>
          <p className="text-muted-foreground">
            Search and analyze properties in Bella Vista
          </p>
        </div>
      </div>

      {/* Search and Controls */}
      <div className="flex flex-col md:flex-row gap-4">
        <div className="flex-1">
          <PropertySearchBar onSearch={handleSearch} />
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant={showFilters ? 'secondary' : 'outline'}
            onClick={() => setShowFilters(!showFilters)}
          >
            <Filter className="h-4 w-4 mr-2" />
            Filters
          </Button>
          <Tabs value={viewMode} onValueChange={(v) => setViewMode(v as 'table' | 'grid')}>
            <TabsList>
              <TabsTrigger value="table">
                <List className="h-4 w-4" />
              </TabsTrigger>
              <TabsTrigger value="grid">
                <LayoutGrid className="h-4 w-4" />
              </TabsTrigger>
            </TabsList>
          </Tabs>
        </div>
      </div>

      {/* Filters */}
      {showFilters && (
        <PropertyFilters
          filters={searchParams}
          onChange={handleFilterChange}
        />
      )}

      {/* Results Count */}
      {data && (
        <div className="text-sm text-muted-foreground">
          Showing {data.properties.length} of {data.total_count.toLocaleString()} properties
        </div>
      )}

      {/* Results */}
      {isLoading ? (
        <div className="flex items-center justify-center py-12">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600" />
        </div>
      ) : error ? (
        <div className="text-center py-12 text-red-500">
          Failed to load properties. Please try again.
        </div>
      ) : viewMode === 'table' ? (
        <PropertyTable
          properties={data?.properties || []}
          onSort={handleSort}
          sortBy={searchParams.sort_by}
          sortOrder={searchParams.sort_order}
        />
      ) : (
        <PropertyGrid properties={data?.properties || []} />
      )}

      {/* Pagination */}
      {data && data.total_count > data.page_size && (
        <div className="flex items-center justify-center gap-2">
          <Button
            variant="outline"
            disabled={data.page <= 1}
            onClick={() => handlePageChange(data.page - 1)}
          >
            Previous
          </Button>
          <span className="text-sm text-muted-foreground">
            Page {data.page} of {Math.ceil(data.total_count / data.page_size)}
          </span>
          <Button
            variant="outline"
            disabled={!data.has_more}
            onClick={() => handlePageChange(data.page + 1)}
          >
            Next
          </Button>
        </div>
      )}
    </div>
  );
}
