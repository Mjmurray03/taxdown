import Link from 'next/link';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { ArrowRight, TrendingUp } from 'lucide-react';

interface TopProperty {
  property_id: string;
  parcel_id: string;
  address: string | null;
  value: number;
  metric_name: string;
}

interface TopOpportunitiesProps {
  opportunities: TopProperty[];
}

export function TopOpportunities({ opportunities }: TopOpportunitiesProps) {
  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 0,
    }).format(value);
  };

  if (opportunities.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Top Opportunities</CardTitle>
          <CardDescription>Properties with highest savings potential</CardDescription>
        </CardHeader>
        <CardContent className="flex items-center justify-center h-64">
          <p className="text-muted-foreground">No opportunities found yet</p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Top Opportunities</CardTitle>
        <CardDescription>Properties with highest savings potential</CardDescription>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          {opportunities.slice(0, 5).map((property, index) => (
            <div
              key={property.property_id}
              className="flex items-center justify-between p-3 rounded-lg bg-gray-50 hover:bg-gray-100 transition-colors"
            >
              <div className="flex items-center space-x-3">
                <div className="flex items-center justify-center w-8 h-8 rounded-full bg-purple-100 text-purple-700 font-semibold text-sm">
                  {index + 1}
                </div>
                <div>
                  <p className="font-medium text-sm">
                    {property.address || property.parcel_id}
                  </p>
                  <p className="text-xs text-muted-foreground">
                    {property.parcel_id}
                  </p>
                </div>
              </div>
              <div className="flex items-center space-x-3">
                <Badge variant="secondary" className="bg-green-100 text-green-800">
                  <TrendingUp className="w-3 h-3 mr-1" />
                  {formatCurrency(property.value)}/yr
                </Badge>
                <Link href={`/properties/${property.property_id}`}>
                  <Button variant="ghost" size="sm">
                    <ArrowRight className="h-4 w-4" />
                  </Button>
                </Link>
              </div>
            </div>
          ))}
        </div>

        {opportunities.length > 5 && (
          <div className="mt-4 text-center">
            <Link href="/properties?filter=appeal_candidates">
              <Button variant="outline" size="sm">
                View All {opportunities.length} Opportunities
              </Button>
            </Link>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
