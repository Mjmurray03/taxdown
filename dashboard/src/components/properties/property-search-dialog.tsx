'use client';

import { useState, useCallback } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Skeleton } from '@/components/ui/skeleton';
import { Badge } from '@/components/ui/badge';
import { Search, Home, Check, X } from 'lucide-react';
import { propertyApi, PropertySearchResponse, PropertySummary } from '@/lib/api';
import { useDebounce } from '@/lib/hooks';

interface PropertySearchDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSelect: (property: PropertySummary) => void;
  title?: string;
  description?: string;
  excludeIds?: string[];
}

export function PropertySearchDialog({
  open,
  onOpenChange,
  onSelect,
  title = 'Search Properties',
  description = 'Search for a property to add',
  excludeIds = [],
}: PropertySearchDialogProps) {
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedProperty, setSelectedProperty] = useState<PropertySummary | null>(null);

  const debouncedQuery = useDebounce(searchQuery, 300);

  const { data, isLoading } = useQuery<PropertySearchResponse>({
    queryKey: ['property-search-dialog', debouncedQuery],
    queryFn: () => propertyApi.search({ query: debouncedQuery, page: 1, page_size: 10 }),
    enabled: open && debouncedQuery.length >= 2,
  });

  const properties = (data?.properties || []).filter(
    (p) => !excludeIds.includes(p.id)
  );

  const formatCurrency = (value: number | null) => {
    if (value === null || value === undefined) return 'N/A';
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      maximumFractionDigits: 0,
    }).format(value);
  };

  const handleSelect = (property: PropertySummary) => {
    setSelectedProperty(property);
  };

  const handleConfirm = () => {
    if (selectedProperty) {
      onSelect(selectedProperty);
      onOpenChange(false);
      setSearchQuery('');
      setSelectedProperty(null);
    }
  };

  const handleClose = () => {
    onOpenChange(false);
    setSearchQuery('');
    setSelectedProperty(null);
  };

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="sm:max-w-[600px] max-h-[80vh]">
        <DialogHeader>
          <DialogTitle>{title}</DialogTitle>
          <DialogDescription>{description}</DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          {/* Search Input */}
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder="Search by address, owner, or parcel ID..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-10"
              autoFocus
            />
          </div>

          {/* Results */}
          <div className="min-h-[200px] max-h-[300px] overflow-y-auto border rounded-lg">
            {/* Loading State */}
            {isLoading && (
              <div className="p-4 space-y-3">
                {[...Array(3)].map((_, i) => (
                  <div key={i} className="flex items-center gap-3">
                    <Skeleton className="h-10 w-10 rounded" />
                    <div className="flex-1 space-y-2">
                      <Skeleton className="h-4 w-3/4" />
                      <Skeleton className="h-3 w-1/2" />
                    </div>
                  </div>
                ))}
              </div>
            )}

            {/* Empty State */}
            {!isLoading && searchQuery.length < 2 && (
              <div className="flex flex-col items-center justify-center py-10 text-gray-500">
                <Search className="h-8 w-8 mb-2" />
                <p className="text-sm">Type at least 2 characters to search</p>
              </div>
            )}

            {/* No Results */}
            {!isLoading && searchQuery.length >= 2 && properties.length === 0 && (
              <div className="flex flex-col items-center justify-center py-10 text-gray-500">
                <Home className="h-8 w-8 mb-2" />
                <p className="text-sm">No properties found</p>
              </div>
            )}

            {/* Results List */}
            {!isLoading && properties.length > 0 && (
              <div className="divide-y">
                {properties.map((property) => (
                  <button
                    key={property.id}
                    onClick={() => handleSelect(property)}
                    className={`w-full flex items-center justify-between p-3 hover:bg-gray-50 transition-colors text-left ${
                      selectedProperty?.id === property.id ? 'bg-blue-50 border-blue-200' : ''
                    }`}
                  >
                    <div className="flex items-center gap-3">
                      <div className={`h-10 w-10 rounded-lg flex items-center justify-center ${
                        selectedProperty?.id === property.id ? 'bg-blue-100' : 'bg-gray-100'
                      }`}>
                        {selectedProperty?.id === property.id ? (
                          <Check className="h-5 w-5 text-blue-600" />
                        ) : (
                          <Home className="h-5 w-5 text-gray-600" />
                        )}
                      </div>
                      <div>
                        <p className="font-medium">{property.address || 'Unknown Address'}</p>
                        <p className="text-sm text-gray-500">
                          {property.parcel_id} | {property.owner_name || 'Unknown Owner'}
                        </p>
                      </div>
                    </div>
                    <div className="text-right">
                      <p className="font-medium">{formatCurrency(property.total_value)}</p>
                      <Badge variant="outline" className="text-xs">
                        {property.property_type || 'Unknown'}
                      </Badge>
                    </div>
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* Selected Property Info */}
          {selectedProperty && (
            <div className="p-3 bg-blue-50 border border-blue-200 rounded-lg">
              <p className="text-sm font-medium text-blue-800">
                Selected: {selectedProperty.address || selectedProperty.parcel_id}
              </p>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex justify-end gap-2 mt-4">
          <Button variant="outline" onClick={handleClose}>
            Cancel
          </Button>
          <Button onClick={handleConfirm} disabled={!selectedProperty}>
            Select Property
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
