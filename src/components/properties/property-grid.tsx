'use client';

import Link from 'next/link';
import { PropertySummary } from '@/lib/api';
import { Card, CardContent, CardHeader } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { MapPin, Eye, BarChart2 } from 'lucide-react';

interface PropertyGridProps {
  properties: PropertySummary[];
}

export function PropertyGrid({ properties }: PropertyGridProps) {
  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 0,
    }).format(value);
  };

  if (properties.length === 0) {
    return (
      <div className="text-center py-12 text-muted-foreground">
        No properties found. Try adjusting your search criteria.
      </div>
    );
  }

  return (
    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
      {properties.map((property) => (
        <Card key={property.id} className="hover:shadow-md transition-shadow">
          <CardHeader className="pb-2">
            <div className="flex items-start justify-between">
              <div>
                <Link
                  href={`/properties/${property.id}`}
                  className="font-semibold hover:text-blue-600 hover:underline"
                >
                  {property.address}
                </Link>
                <div className="flex items-center text-sm text-muted-foreground mt-1">
                  <MapPin className="h-3 w-3 mr-1" />
                  {property.city}
                </div>
              </div>
              <Badge variant="secondary">{property.property_type}</Badge>
            </div>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              <div className="text-sm text-muted-foreground">
                Parcel: <span className="font-mono">{property.parcel_id}</span>
              </div>
              <div className="text-sm text-muted-foreground truncate">
                Owner: {property.owner_name}
              </div>
              <div className="grid grid-cols-2 gap-2 pt-2 border-t">
                <div>
                  <p className="text-xs text-muted-foreground">Market Value</p>
                  <p className="font-semibold">{formatCurrency(property.market_value)}</p>
                </div>
                <div>
                  <p className="text-xs text-muted-foreground">Assessed</p>
                  <p className="font-semibold">{formatCurrency(property.assessed_value)}</p>
                </div>
              </div>
              <div className="flex gap-2 pt-2">
                <Link href={`/properties/${property.id}`} className="flex-1">
                  <Button variant="outline" size="sm" className="w-full">
                    <Eye className="h-4 w-4 mr-1" /> View
                  </Button>
                </Link>
                <Link href={`/analysis/${property.id}`} className="flex-1">
                  <Button variant="outline" size="sm" className="w-full">
                    <BarChart2 className="h-4 w-4 mr-1" /> Analyze
                  </Button>
                </Link>
              </div>
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
