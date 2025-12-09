'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Skeleton } from '@/components/ui/skeleton';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Briefcase, Plus, AlertTriangle } from 'lucide-react';
import { portfolioApi, PortfolioSummary, APIResponse } from '@/lib/api';
import { toast } from 'sonner';

interface AddToPortfolioDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  propertyId: string;
  parcelId: string;
  propertyAddress?: string;
}

export function AddToPortfolioDialog({
  open,
  onOpenChange,
  propertyId,
  parcelId,
  propertyAddress,
}: AddToPortfolioDialogProps) {
  const queryClient = useQueryClient();
  const [selectedPortfolio, setSelectedPortfolio] = useState<string>('');
  const [showNewPortfolio, setShowNewPortfolio] = useState(false);
  const [newPortfolioName, setNewPortfolioName] = useState('');

  // Demo user ID - in production would come from auth
  const userId = 'demo-user';

  const { data, isLoading, error } = useQuery<APIResponse<PortfolioSummary[]>>({
    queryKey: ['portfolios', userId],
    queryFn: () => portfolioApi.list(userId),
    enabled: open,
  });

  const portfolios = data?.data || [];

  const addToPortfolioMutation = useMutation({
    mutationFn: async () => {
      if (!selectedPortfolio) {
        throw new Error('Please select a portfolio');
      }
      return portfolioApi.addProperty(selectedPortfolio, parcelId);
    },
    onSuccess: () => {
      toast.success('Property added to portfolio');
      queryClient.invalidateQueries({ queryKey: ['portfolios'] });
      onOpenChange(false);
      setSelectedPortfolio('');
    },
    onError: (error) => {
      toast.error(error instanceof Error ? error.message : 'Failed to add property');
    },
  });

  const createPortfolioMutation = useMutation({
    mutationFn: async () => {
      if (!newPortfolioName.trim()) {
        throw new Error('Please enter a portfolio name');
      }
      return portfolioApi.create({
        name: newPortfolioName.trim(),
        user_id: userId,
      });
    },
    onSuccess: (data) => {
      toast.success('Portfolio created');
      queryClient.invalidateQueries({ queryKey: ['portfolios'] });
      setShowNewPortfolio(false);
      setNewPortfolioName('');
      if (data?.data?.id) {
        setSelectedPortfolio(data.data.id);
      }
    },
    onError: (error) => {
      toast.error(error instanceof Error ? error.message : 'Failed to create portfolio');
    },
  });

  const handleSubmit = () => {
    if (showNewPortfolio) {
      createPortfolioMutation.mutate();
    } else {
      addToPortfolioMutation.mutate();
    }
  };

  const isSubmitting = addToPortfolioMutation.isPending || createPortfolioMutation.isPending;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[425px]">
        <DialogHeader>
          <DialogTitle>Add to Portfolio</DialogTitle>
          <DialogDescription>
            {propertyAddress ? (
              <>Add "{propertyAddress}" to a portfolio</>
            ) : (
              <>Add property to a portfolio for tracking</>
            )}
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-4">
          {/* Loading State */}
          {isLoading && (
            <div className="space-y-3">
              <Skeleton className="h-10 w-full" />
              <Skeleton className="h-10 w-full" />
            </div>
          )}

          {/* Error State */}
          {error && (
            <div className="flex items-center gap-2 text-red-600 text-sm">
              <AlertTriangle className="h-4 w-4" />
              <span>Failed to load portfolios</span>
            </div>
          )}

          {/* Portfolio Selection */}
          {!isLoading && !error && !showNewPortfolio && (
            <>
              {portfolios.length > 0 ? (
                <div className="space-y-2">
                  <Label>Select Portfolio</Label>
                  <Select value={selectedPortfolio} onValueChange={setSelectedPortfolio}>
                    <SelectTrigger>
                      <SelectValue placeholder="Choose a portfolio" />
                    </SelectTrigger>
                    <SelectContent>
                      {portfolios.map((portfolio) => (
                        <SelectItem key={portfolio.id} value={portfolio.id}>
                          <div className="flex items-center gap-2">
                            <Briefcase className="h-4 w-4" />
                            {portfolio.name} ({portfolio.property_count} properties)
                          </div>
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              ) : (
                <div className="text-center py-4">
                  <Briefcase className="h-10 w-10 text-gray-400 mx-auto mb-2" />
                  <p className="text-sm text-gray-500">No portfolios yet</p>
                </div>
              )}

              <Button
                variant="secondary"
                className="w-full"
                onClick={() => setShowNewPortfolio(true)}
              >
                <Plus className="h-4 w-4 mr-2" />
                Create New Portfolio
              </Button>
            </>
          )}

          {/* New Portfolio Form */}
          {showNewPortfolio && (
            <div className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="portfolio-name">Portfolio Name</Label>
                <Input
                  id="portfolio-name"
                  placeholder="e.g., My Investment Properties"
                  value={newPortfolioName}
                  onChange={(e) => setNewPortfolioName(e.target.value)}
                />
              </div>
              <Button
                variant="secondary"
                size="sm"
                onClick={() => setShowNewPortfolio(false)}
              >
                Cancel
              </Button>
            </div>
          )}
        </div>

        <DialogFooter>
          <Button variant="secondary" onClick={() => onOpenChange(false)} disabled={isSubmitting}>
            Cancel
          </Button>
          <Button onClick={handleSubmit} disabled={isSubmitting || (!showNewPortfolio && !selectedPortfolio)}>
            {isSubmitting ? 'Adding...' : showNewPortfolio ? 'Create & Add' : 'Add to Portfolio'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
