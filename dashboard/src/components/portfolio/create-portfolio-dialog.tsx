'use client';

import { useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
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
import { Textarea } from '@/components/ui/textarea';
import { toast } from 'sonner';
import { api } from '@/lib/api';

interface CreatePortfolioDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSuccess?: (portfolioId: string) => void;
}

export function CreatePortfolioDialog({
  open,
  onOpenChange,
  onSuccess,
}: CreatePortfolioDialogProps) {
  const queryClient = useQueryClient();
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');

  // Demo user ID - in production would come from auth
  const userId = 'demo-user';

  const createMutation = useMutation({
    mutationFn: async () => {
      if (!name.trim()) {
        throw new Error('Please enter a portfolio name');
      }
      const response = await api.post('/portfolios', {
        name: name.trim(),
        description: description.trim(),
        user_id: userId,
      });
      return response.data;
    },
    onSuccess: (data) => {
      toast.success('Portfolio created successfully');
      queryClient.invalidateQueries({ queryKey: ['portfolios'] });
      onOpenChange(false);
      setName('');
      setDescription('');
      if (data?.data?.id && onSuccess) {
        onSuccess(data.data.id);
      }
    },
    onError: (error) => {
      toast.error(error instanceof Error ? error.message : 'Failed to create portfolio');
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    createMutation.mutate();
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[425px]">
        <form onSubmit={handleSubmit}>
          <DialogHeader>
            <DialogTitle>Create Portfolio</DialogTitle>
            <DialogDescription>
              Create a new portfolio to organize and track your properties.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="name">Portfolio Name *</Label>
              <Input
                id="name"
                placeholder="e.g., My Investment Properties"
                value={name}
                onChange={(e) => setName(e.target.value)}
                autoFocus
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="description">Description (optional)</Label>
              <Textarea
                id="description"
                placeholder="Add a description for this portfolio..."
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                rows={3}
              />
            </div>
          </div>

          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              onClick={() => onOpenChange(false)}
              disabled={createMutation.isPending}
            >
              Cancel
            </Button>
            <Button type="submit" disabled={createMutation.isPending || !name.trim()}>
              {createMutation.isPending ? 'Creating...' : 'Create Portfolio'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
