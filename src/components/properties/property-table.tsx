'use client';

import Link from 'next/link';
import { PropertySummary } from '@/lib/api';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { ArrowUpDown, ArrowUp, ArrowDown, Eye, BarChart2 } from 'lucide-react';

interface PropertyTableProps {
  properties: PropertySummary[];
  onSort: (field: string, order: 'asc' | 'desc') => void;
  sortBy?: string;
  sortOrder?: 'asc' | 'desc';
}

export function PropertyTable({ properties, onSort, sortBy, sortOrder }: PropertyTableProps) {
  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 0,
    }).format(value);
  };

  const handleSort = (field: string) => {
    const newOrder = sortBy === field && sortOrder === 'asc' ? 'desc' : 'asc';
    onSort(field, newOrder);
  };

  const SortIcon = ({ field }: { field: string }) => {
    if (sortBy !== field) return <ArrowUpDown className="h-4 w-4" />;
    return sortOrder === 'asc'
      ? <ArrowUp className="h-4 w-4" />
      : <ArrowDown className="h-4 w-4" />;
  };

  if (properties.length === 0) {
    return (
      <div className="text-center py-12 text-muted-foreground">
        No properties found. Try adjusting your search criteria.
      </div>
    );
  }

  return (
    <div className="rounded-md border">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead className="w-[300px]">
              <Button variant="ghost" onClick={() => handleSort('address')}>
                Address <SortIcon field="address" />
              </Button>
            </TableHead>
            <TableHead>Parcel ID</TableHead>
            <TableHead>Owner</TableHead>
            <TableHead>
              <Button variant="ghost" onClick={() => handleSort('value')}>
                Market Value <SortIcon field="value" />
              </Button>
            </TableHead>
            <TableHead>
              <Button variant="ghost" onClick={() => handleSort('assessed_value')}>
                Assessed <SortIcon field="assessed_value" />
              </Button>
            </TableHead>
            <TableHead>Type</TableHead>
            <TableHead className="text-right">Actions</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {properties.map((property) => (
            <TableRow key={property.id}>
              <TableCell className="font-medium">
                <Link
                  href={`/properties/${property.id}`}
                  className="hover:text-blue-600 hover:underline"
                >
                  {property.address}
                </Link>
                <div className="text-xs text-muted-foreground">
                  {property.city}
                </div>
              </TableCell>
              <TableCell className="font-mono text-sm">
                {property.parcel_id}
              </TableCell>
              <TableCell className="max-w-[150px] truncate">
                {property.owner_name}
              </TableCell>
              <TableCell>{formatCurrency(property.market_value)}</TableCell>
              <TableCell>{formatCurrency(property.assessed_value)}</TableCell>
              <TableCell>
                <Badge variant="secondary">
                  {property.property_type}
                </Badge>
              </TableCell>
              <TableCell className="text-right">
                <div className="flex items-center justify-end gap-2">
                  <Link href={`/properties/${property.id}`}>
                    <Button variant="ghost" size="sm">
                      <Eye className="h-4 w-4" />
                    </Button>
                  </Link>
                  <Link href={`/analysis/${property.id}`}>
                    <Button variant="ghost" size="sm">
                      <BarChart2 className="h-4 w-4" />
                    </Button>
                  </Link>
                </div>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}
