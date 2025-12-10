'use client';

import { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { MainLayout } from '@/components/layout/main-layout';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
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
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import {
  FileText,
  AlertTriangle,
  Plus,
  Calendar,
  Download,
  Eye,
  Trash2,
  MoreHorizontal,
  RefreshCw,
  Search,
  Copy,
  Check,
} from 'lucide-react';
import { appealApi, AppealListItem, AppealPackage, APIResponse } from '@/lib/api';
import { ConfirmDialog } from '@/components/ui/confirm-dialog';
import { useDownload, useCopyToClipboard } from '@/lib/hooks';
import { getDaysUntilDeadline, getFormattedDeadline } from '@/lib/config';
import { toast } from 'sonner';

export default function AppealsPage() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const download = useDownload();
  const [copied, copyToClipboard] = useCopyToClipboard();

  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [selectedAppeal, setSelectedAppeal] = useState<AppealListItem | null>(null);
  const [viewDialogOpen, setViewDialogOpen] = useState(false);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [appealToDelete, setAppealToDelete] = useState<string | null>(null);

  // Hydration-safe date values - only set after mount
  const [daysUntilDeadline, setDaysUntilDeadline] = useState<number | null>(null);
  const [formattedDeadline, setFormattedDeadline] = useState<string>('');

  useEffect(() => {
    setDaysUntilDeadline(getDaysUntilDeadline());
    setFormattedDeadline(getFormattedDeadline());
  }, []);

  // Fetch appeals
  const { data, isLoading, error, refetch, isFetching } = useQuery<APIResponse<AppealListItem[]>>({
    queryKey: ['appeals', statusFilter],
    queryFn: () => appealApi.list(statusFilter === 'all' ? undefined : statusFilter),
  });

  const appeals = data?.data || [];

  // Download PDF mutation
  const downloadMutation = useMutation({
    mutationFn: (propertyId: string) => appealApi.downloadPdf(propertyId),
    onSuccess: (blob, propertyId) => {
      const appeal = appeals.find((a) => a.property_id === propertyId);
      download(blob, `appeal-${appeal?.parcel_id || propertyId}.pdf`);
      toast.success('PDF downloaded successfully');
    },
    onError: (error) => {
      toast.error('Download failed: ' + (error instanceof Error ? error.message : 'Unknown error'));
    },
  });

  // Fetch full appeal details for viewing
  const { data: appealDetails, isLoading: loadingDetails } = useQuery<APIResponse<AppealPackage>>({
    queryKey: ['appeal-details', selectedAppeal?.appeal_id],
    queryFn: async () => {
      if (!selectedAppeal?.appeal_id) throw new Error('No appeal selected');
      // Get existing appeal details instead of regenerating
      return appealApi.get(selectedAppeal.appeal_id);
    },
    enabled: !!selectedAppeal?.appeal_id && viewDialogOpen,
  });

  const formatCurrency = (value: number | null | undefined) => {
    if (value === null || value === undefined) return 'N/A';
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      maximumFractionDigits: 0,
    }).format(value);
  };

  const formatDate = (dateString: string | undefined) => {
    if (!dateString) return 'N/A';
    return new Date(dateString).toLocaleDateString();
  };

  const getStatusBadge = (status: string) => {
    switch (status.toLowerCase()) {
      case 'generated':
        return <Badge variant="outline">Generated</Badge>;
      case 'submitted':
        return <Badge className="bg-blue-100 text-blue-800">Submitted</Badge>;
      case 'pending':
        return <Badge className="bg-yellow-100 text-yellow-800">Pending</Badge>;
      case 'approved':
        return <Badge className="bg-green-100 text-green-800">Approved</Badge>;
      case 'denied':
        return <Badge className="bg-red-100 text-red-800">Denied</Badge>;
      default:
        return <Badge variant="secondary">{status}</Badge>;
    }
  };

  const handleViewAppeal = (appeal: AppealListItem) => {
    setSelectedAppeal(appeal);
    setViewDialogOpen(true);
  };

  const handleDownload = (propertyId: string) => {
    downloadMutation.mutate(propertyId);
  };

  // Delete appeal mutation
  const deleteMutation = useMutation({
    mutationFn: (appealId: string) => appealApi.delete(appealId),
    onSuccess: () => {
      toast.success('Appeal deleted');
      queryClient.invalidateQueries({ queryKey: ['appeals'] });
    },
    onError: (error) => {
      toast.error('Failed to delete appeal: ' + (error instanceof Error ? error.message : 'Unknown error'));
    },
  });

  const handleDeleteClick = (appealId: string) => {
    setAppealToDelete(appealId);
    setDeleteDialogOpen(true);
  };

  const handleDeleteConfirm = () => {
    if (appealToDelete) {
      deleteMutation.mutate(appealToDelete);
    }
    setDeleteDialogOpen(false);
    setAppealToDelete(null);
  };

  const handleCopyLetter = async () => {
    if (appealDetails?.data?.appeal_letter) {
      await copyToClipboard(appealDetails.data.appeal_letter);
      toast.success('Appeal letter copied to clipboard');
    }
  };

  return (
    <MainLayout>
      <div className="space-y-6">
        {/* Page Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold tracking-tight">Appeals</h1>
            <p className="text-muted-foreground">Manage property tax appeals</p>
          </div>
          <div className="flex items-center gap-2">
            {formattedDeadline && (
              <Badge variant="outline" className="flex items-center gap-1">
                <Calendar className="h-3 w-3" />
                Filing Deadline: {formattedDeadline}
              </Badge>
            )}
            {daysUntilDeadline !== null && (
              <Badge variant={daysUntilDeadline < 30 ? 'error' : 'secondary'}>
                {daysUntilDeadline} days left
              </Badge>
            )}
          </div>
        </div>

        {/* Deadline Alert */}
        {daysUntilDeadline !== null && daysUntilDeadline < 60 && (
          <Card className="border-yellow-200 bg-yellow-50">
            <CardContent className="flex items-center justify-between py-4">
              <div className="flex items-center gap-3">
                <AlertTriangle className="h-5 w-5 text-yellow-600" />
                <div>
                  <p className="font-medium text-yellow-800">Filing Deadline Approaching</p>
                  <p className="text-sm text-yellow-700">
                    Submit your appeals before {formattedDeadline} to be considered for this tax year.
                  </p>
                </div>
              </div>
              <Link href="/properties?filter=appeal">
                <Button size="sm">Find Properties to Appeal</Button>
              </Link>
            </CardContent>
          </Card>
        )}

        {/* Filters and Actions */}
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle>Appeal Management</CardTitle>
                <CardDescription>View and manage generated appeals</CardDescription>
              </div>
              <div className="flex gap-2">
                <Button
                  variant="secondary"
                  size="sm"
                  onClick={() => refetch()}
                  disabled={isFetching}
                >
                  <RefreshCw className={`h-4 w-4 mr-2 ${isFetching ? 'animate-spin' : ''}`} />
                  Refresh
                </Button>
                <Select value={statusFilter} onValueChange={setStatusFilter}>
                  <SelectTrigger className="w-[180px]">
                    <SelectValue placeholder="Filter by status" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All Statuses</SelectItem>
                    <SelectItem value="generated">Generated</SelectItem>
                    <SelectItem value="submitted">Submitted</SelectItem>
                    <SelectItem value="pending">Pending Review</SelectItem>
                    <SelectItem value="approved">Approved</SelectItem>
                    <SelectItem value="denied">Denied</SelectItem>
                  </SelectContent>
                </Select>
                <Link href="/properties?filter=appeal">
                  <Button>
                    <Plus className="h-4 w-4 mr-2" />
                    New Appeal
                  </Button>
                </Link>
              </div>
            </div>
          </CardHeader>
          <CardContent>
            {/* Loading State */}
            {isLoading && (
              <div className="space-y-4">
                {[...Array(5)].map((_, i) => (
                  <div key={i} className="flex items-center space-x-4">
                    <Skeleton className="h-12 w-12 rounded" />
                    <div className="space-y-2 flex-1">
                      <Skeleton className="h-4 w-[250px]" />
                      <Skeleton className="h-4 w-[150px]" />
                    </div>
                    <Skeleton className="h-6 w-[80px]" />
                  </div>
                ))}
              </div>
            )}

            {/* Error State */}
            {error && (
              <div className="text-center py-10">
                <AlertTriangle className="h-10 w-10 text-red-500 mx-auto mb-4" />
                <h3 className="text-lg font-medium text-gray-900">Error loading appeals</h3>
                <p className="text-gray-500 mt-2">
                  {error instanceof Error ? error.message : 'Something went wrong'}
                </p>
                <Button onClick={() => refetch()} variant="secondary" className="mt-4">
                  Try Again
                </Button>
              </div>
            )}

            {/* Empty State */}
            {!isLoading && !error && appeals.length === 0 && (
              <div className="text-center py-10">
                <FileText className="h-10 w-10 text-gray-400 mx-auto mb-4" />
                <h3 className="text-lg font-medium text-gray-900">No appeals found</h3>
                <p className="text-gray-500 mt-2">
                  {statusFilter !== 'all'
                    ? 'No appeals match the selected filter'
                    : 'Generate appeals from the properties page'}
                </p>
                <div className="flex gap-2 justify-center mt-4">
                  {statusFilter !== 'all' && (
                    <Button variant="secondary" onClick={() => setStatusFilter('all')}>
                      Clear Filter
                    </Button>
                  )}
                  <Link href="/properties?filter=appeal">
                    <Button>
                      <Search className="h-4 w-4 mr-2" />
                      Find Properties to Appeal
                    </Button>
                  </Link>
                </div>
              </div>
            )}

            {/* Appeals Table */}
            {!isLoading && !error && appeals.length > 0 && (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Property</TableHead>
                    <TableHead>Parcel ID</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead className="text-right">Est. Savings</TableHead>
                    <TableHead>Generated</TableHead>
                    <TableHead></TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {appeals.map((appeal) => (
                    <TableRow key={appeal.appeal_id}>
                      <TableCell className="font-medium">
                        {appeal.address || 'Unknown Address'}
                      </TableCell>
                      <TableCell className="text-muted-foreground">{appeal.parcel_id}</TableCell>
                      <TableCell>{getStatusBadge(appeal.status)}</TableCell>
                      <TableCell className="text-right">
                        {formatCurrency(appeal.estimated_savings)}
                      </TableCell>
                      <TableCell>{formatDate(appeal.generated_at)}</TableCell>
                      <TableCell>
                        <div className="flex items-center gap-1">
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => handleViewAppeal(appeal)}
                          >
                            <Eye className="h-4 w-4 mr-1" />
                            View
                          </Button>
                          <DropdownMenu>
                            <DropdownMenuTrigger asChild>
                              <Button variant="ghost" size="sm">
                                <MoreHorizontal className="h-4 w-4" />
                              </Button>
                            </DropdownMenuTrigger>
                            <DropdownMenuContent align="end">
                              <DropdownMenuItem
                                onClick={() => handleDownload(appeal.property_id)}
                                disabled={downloadMutation.isPending}
                              >
                                <Download className="h-4 w-4 mr-2" />
                                Download PDF
                              </DropdownMenuItem>
                              <DropdownMenuItem
                                onClick={() => router.push(`/properties/${appeal.property_id}`)}
                              >
                                <Eye className="h-4 w-4 mr-2" />
                                View Property
                              </DropdownMenuItem>
                              <DropdownMenuItem
                                onClick={() => handleDeleteClick(appeal.appeal_id)}
                                className="text-red-600"
                              >
                                <Trash2 className="h-4 w-4 mr-2" />
                                Delete Appeal
                              </DropdownMenuItem>
                            </DropdownMenuContent>
                          </DropdownMenu>
                        </div>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </CardContent>
        </Card>

        {/* Summary Cards */}
        <div className="grid gap-4 md:grid-cols-4">
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium">Total Appeals</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{appeals.length}</div>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium">Pending</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">
                {
                  appeals.filter((a) =>
                    ['generated', 'submitted', 'pending'].includes(a.status.toLowerCase())
                  ).length
                }
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium">Approved</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-green-600">
                {appeals.filter((a) => a.status.toLowerCase() === 'approved').length}
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium">Total Potential Savings</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-blue-600">
                {formatCurrency(appeals.reduce((sum, a) => sum + (a.estimated_savings || 0), 0))}
              </div>
            </CardContent>
          </Card>
        </div>
      </div>

      {/* View Appeal Dialog */}
      <Dialog open={viewDialogOpen} onOpenChange={setViewDialogOpen}>
        <DialogContent className="max-w-3xl max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Appeal Details</DialogTitle>
            <DialogDescription>
              {selectedAppeal?.address || 'Property'} - {selectedAppeal?.parcel_id}
            </DialogDescription>
          </DialogHeader>

          {loadingDetails ? (
            <div className="space-y-4 py-4">
              <Skeleton className="h-6 w-full" />
              <Skeleton className="h-40 w-full" />
              <Skeleton className="h-6 w-3/4" />
            </div>
          ) : appealDetails?.data ? (
            <div className="space-y-4 py-4">
              {/* Status and Info */}
              <div className="flex items-center justify-between">
                {getStatusBadge(selectedAppeal?.status || 'generated')}
                <div className="text-sm text-muted-foreground">
                  Generated: {formatDate(appealDetails.data.generated_at)}
                </div>
              </div>

              {/* Savings Summary */}
              <div className="grid grid-cols-2 gap-4 p-4 bg-gray-50 rounded-lg">
                <div>
                  <p className="text-sm text-muted-foreground">Potential Savings</p>
                  <p className="text-xl font-bold text-green-600">
                    {formatCurrency(appealDetails.data.estimated_annual_savings)}
                  </p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Fairness Score</p>
                  <p className="text-xl font-bold">{appealDetails.data.fairness_score}%</p>
                </div>
              </div>

              {/* Appeal Letter */}
              <div>
                <div className="flex items-center justify-between mb-2">
                  <h4 className="font-semibold">Appeal Letter</h4>
                  <Button variant="ghost" size="sm" onClick={handleCopyLetter}>
                    {copied ? <Check className="h-4 w-4 mr-1" /> : <Copy className="h-4 w-4 mr-1" />}
                    {copied ? 'Copied' : 'Copy'}
                  </Button>
                </div>
                <pre className="whitespace-pre-wrap text-sm bg-gray-50 p-4 rounded-lg max-h-[300px] overflow-y-auto">
                  {appealDetails.data.appeal_letter}
                </pre>
              </div>

              {/* Actions */}
              <div className="flex justify-end gap-2">
                <Button
                  variant="secondary"
                  onClick={() => handleDownload(selectedAppeal!.property_id)}
                  disabled={downloadMutation.isPending}
                >
                  <Download className="h-4 w-4 mr-2" />
                  {downloadMutation.isPending ? 'Downloading...' : 'Download PDF'}
                </Button>
                <Button onClick={() => router.push(`/properties/${selectedAppeal?.property_id}`)}>
                  View Property
                </Button>
              </div>
            </div>
          ) : (
            <div className="py-8 text-center text-gray-500">
              Could not load appeal details
            </div>
          )}
        </DialogContent>
      </Dialog>

      {/* Delete Confirmation Dialog */}
      <ConfirmDialog
        open={deleteDialogOpen}
        onOpenChange={setDeleteDialogOpen}
        title="Delete Appeal"
        description="Are you sure you want to delete this appeal? This action cannot be undone."
        confirmLabel="Delete"
        variant="destructive"
        onConfirm={handleDeleteConfirm}
        loading={deleteMutation.isPending}
      />
    </MainLayout>
  );
}
