'use client';

import { PropertySearchParams } from '@/lib/api';
import { Card, CardContent } from '@/components/ui/card';
import { Label } from '@/components/ui/label';
import { Input } from '@/components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Switch } from '@/components/ui/switch';
import { Button } from '@/components/ui/button';

interface PropertyFiltersProps {
  filters: PropertySearchParams;
  onChange: (filters: Partial<PropertySearchParams>) => void;
}

export function PropertyFilters({ filters, onChange }: PropertyFiltersProps) {
  const handleReset = () => {
    onChange({
      city: undefined,
      subdivision: undefined,
      min_value: undefined,
      max_value: undefined,
      only_appeal_candidates: false,
    });
  };

  return (
    <Card>
      <CardContent className="pt-6">
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          {/* City */}
          <div className="space-y-2">
            <Label>City</Label>
            <Select
              value={filters.city || ''}
              onValueChange={(value) => onChange({ city: value || undefined })}
            >
              <SelectTrigger>
                <SelectValue placeholder="All cities" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="">All cities</SelectItem>
                <SelectItem value="Bella Vista">Bella Vista</SelectItem>
                <SelectItem value="Bentonville">Bentonville</SelectItem>
                <SelectItem value="Rogers">Rogers</SelectItem>
              </SelectContent>
            </Select>
          </div>

          {/* Value Range */}
          <div className="space-y-2">
            <Label>Min Value</Label>
            <Input
              type="number"
              placeholder="$0"
              value={filters.min_value || ''}
              onChange={(e) => onChange({ min_value: e.target.value ? Number(e.target.value) : undefined })}
            />
          </div>

          <div className="space-y-2">
            <Label>Max Value</Label>
            <Input
              type="number"
              placeholder="No max"
              value={filters.max_value || ''}
              onChange={(e) => onChange({ max_value: e.target.value ? Number(e.target.value) : undefined })}
            />
          </div>

          {/* Appeal Candidates Only */}
          <div className="space-y-2">
            <Label>Appeal Candidates</Label>
            <div className="flex items-center space-x-2 pt-2">
              <Switch
                checked={filters.only_appeal_candidates || false}
                onCheckedChange={(checked) => onChange({ only_appeal_candidates: checked })}
              />
              <span className="text-sm text-muted-foreground">
                Show only properties eligible for appeal
              </span>
            </div>
          </div>
        </div>

        <div className="mt-4 flex justify-end">
          <Button variant="ghost" onClick={handleReset}>
            Reset Filters
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
