'use client';

import { useState, useRef } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { MainLayout } from '@/components/layout/main-layout';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { Input } from '@/components/ui/input';
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
  Briefcase,
  Plus,
  Home,
  DollarSign,
  TrendingUp,
  AlertTriangle,
  Search,
  RefreshCw,
  Download,
  Upload,
  Trash2,
  MoreHorizontal,
  Eye,
  ChevronRight,
} from 'lucide-react';
import {
  portfolioApi,
  analysisApi,
  PortfolioSummary,
  PortfolioDetail,
  PropertySummary,
  APIResponse,
} from '@/lib/api';
import { CreatePortfolioDialog } from '@/components/portfolio/create-portfolio-dialog';
import { PropertySearchDialog } from '@/components/properties/property-search-dialog';
import { ConfirmDialog } from '@/components/ui/confirm-dialog';
import { useDownload, useLocalStorage } from '@/lib/hooks';
import { toast } from 'sonner';

export default function PortfolioPage() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const download = useDownload();
  const fileInputRef = useRef<HTMLInputElement>(null);

  // State
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedPortfolioId, setSelectedPortfolioId] = useLocalStorage<string | null>('selected-portfolio-id', null);
  const [createDialogOpen, setCreateDialogOpen] = useState(false);
  const [addPropertyDialogOpen, setAddPropertyDialogOpen] = useState(false);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [portfolioToDelete, setPortfolioToDelete] = useState<string | null>(null);
  const [removePropertyDialogOpen, setRemovePropertyDialogOpen] = useState(false);
  const [propertyToRemove, setPropertyToRemove] = useState<{ portfolioId: string; propertyId: string } | null>(null);

  // Demo user ID - in production would come from auth
  const userId = 'demo-user';

  // Fetch portfolios list
  const { data: portfoliosData, isLoading: loadingPortfolios, error: portfoliosError, refetch: refetchPortfolios } = useQuery<APIResponse<PortfolioSummary[]>>({
    queryKey: ['portfolios', userId],
    queryFn: () => portfolioApi.list(userId),
  });

  const portfolios = portfoliosData?.data || [];

  // Fetch selected portfolio details
  const { data: portfolioDetailData, isLoading: loadingDetail, refetch: refetchDetail } = useQuery<APIResponse<PortfolioDetail>>({
    queryKey: ['portfolio-detail', selectedPortfolioId],
    queryFn: () => portfolioApi.get(selectedPortfolioId!),
    enabled: !!selectedPortfolioId,
  });

  const selectedPortfolio = portfolioDetailData?.data;

  // Filter portfolios by search
  const filteredPortfolios = portfolios.filter((p) =>
    p.name.toLowerCase().includes(searchQuery.toLowerCase())
  );

  // Mutations
  const deletePorfolioMutation = useMutation({
    mutationFn: (portfolioId: string) => portfolioApi.delete(portfolioId),
    onSuccess: () => {
      toast.success('Portfolio deleted');
      queryClient.invalidateQueries({ queryKey: ['portfolios'] });
      if (selectedPortfolioId === portfolioToDelete) {
        setSelectedPortfolioId(null);
      }
    },
    onError: (error) => {
      toast.error('Failed to delete portfolio');
    },
  });

  const addPropertyMutation = useMutation({
    mutationFn: (property: PropertySummary) =>
      portfolioApi.addProperty(selectedPortfolioId!, property.parcel_id),
    onSuccess: () => {
      toast.success('Property added to portfolio');
      queryClient.invalidateQueries({ queryKey: ['portfolio-detail', selectedPortfolioId] });
      queryClient.invalidateQueries({ queryKey: ['portfolios'] });
    },
    onError: (error) => {
      toast.error('Failed to add property');
    },
  });

  const removePropertyMutation = useMutation({
    mutationFn: ({ portfolioId, propertyId }: { portfolioId: string; propertyId: string }) =>
      portfolioApi.removeProperty(portfolioId, propertyId),
    onSuccess: () => {
      toast.success('Property removed from portfolio');
      queryClient.invalidateQueries({ queryKey: ['portfolio-detail', selectedPortfolioId] });
      queryClient.invalidateQueries({ queryKey: ['portfolios'] });
    },
    onError: (error) => {
      toast.error('Failed to remove property');
    },
  });

  const analyzeAllMutation = useMutation({
    mutationFn: (portfolioId: string) => portfolioApi.analyzeAll(portfolioId),
    onSuccess: (data) => {
      toast.success(`Analyzed ${data.data?.analyzed || 0} properties`);
      queryClient.invalidateQueries({ queryKey: ['portfolio-detail', selectedPortfolioId] });
    },
    onError: (error) => {
      toast.error('Batch analysis failed');
    },
  });

  const exportMutation = useMutation({
    mutationFn: (portfolioId: string) => portfolioApi.exportCsv(portfolioId),
    onSuccess: (blob) => {
      const portfolio = portfolios.find((p) => p.id === selectedPortfolioId);
      download(blob, `portfolio-${portfolio?.name || 'export'}.csv`);
      toast.success('Portfolio exported');
    },
    onError: (error) => {
      toast.error('Export failed');
    },
  });

  const importMutation = useMutation({
    mutationFn: (file: File) => portfolioApi.importCsv(selectedPortfolioId!, file),
    onSuccess: () => {
      toast.success('Properties imported');
      queryClient.invalidateQueries({ queryKey: ['portfolio-detail', selectedPortfolioId] });
      queryClient.invalidateQueries({ queryKey: ['portfolios'] });
    },
    onError: (error) => {
      toast.error('Import failed');
    },
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

  const handleDeletePortfolio = (portfolioId: string) => {
    setPortfolioToDelete(portfolioId);
    setDeleteDialogOpen(true);
  };

  const handleDeleteConfirm = () => {
    if (portfolioToDelete) {
      deletePorfolioMutation.mutate(portfolioToDelete);
    }
    setDeleteDialogOpen(false);
    setPortfolioToDelete(null);
  };

  const handleRemoveProperty = (propertyId: string) => {
    if (selectedPortfolioId) {
      setPropertyToRemove({ portfolioId: selectedPortfolioId, propertyId });
      setRemovePropertyDialogOpen(true);
    }
  };

  const handleRemovePropertyConfirm = () => {
    if (propertyToRemove) {
      removePropertyMutation.mutate(propertyToRemove);
    }
    setRemovePropertyDialogOpen(false);
    setPropertyToRemove(null);
  };

  const handleAddProperty = (property: PropertySummary) => {
    addPropertyMutation.mutate(property);
    setAddPropertyDialogOpen(false);
  };

  const handleImportClick = () => {
    fileInputRef.current?.click();
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      importMutation.mutate(file);
    }
    e.target.value = '';
  };

  return (
    <MainLayout>
      <div className="space-y-6">
        {/* Page Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold tracking-tight">Portfolio</h1>
            <p className="text-muted-foreground">Manage your property portfolios</p>
          </div>
          <Button onClick={() => setCreateDialogOpen(true)}>
            <Plus className="h-4 w-4 mr-2" />
            Create Portfolio
          </Button>
        </div>

        <div className="grid md:grid-cols-3 gap-6">
          {/* Portfolio List Sidebar */}
          <div className="space-y-4">
            {/* Search */}
            <Card>
              <CardContent className="pt-6">
                <div className="relative">
                  <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                  <Input
                    placeholder="Search portfolios..."
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    className="pl-10"
                  />
                </div>
              </CardContent>
            </Card>

            {/* Portfolio Cards */}
            {loadingPortfolios && (
              <div className="space-y-3">
                {[...Array(3)].map((_, i) => (
                  <Card key={i}>
                    <CardHeader className="pb-2">
                      <Skeleton className="h-5 w-[150px]" />
                      <Skeleton className="h-4 w-[100px]" />
                    </CardHeader>
                    <CardContent>
                      <Skeleton className="h-6 w-[80px]" />
                    </CardContent>
                  </Card>
                ))}
              </div>
            )}

            {portfoliosError && (
              <Card>
                <CardContent className="py-6">
                  <div className="text-center">
                    <AlertTriangle className="h-8 w-8 text-red-500 mx-auto mb-2" />
                    <p className="text-sm text-gray-500">Failed to load portfolios</p>
                    <Button variant="secondary" size="sm" onClick={() => refetchPortfolios()} className="mt-2">
                      Retry
                    </Button>
                  </div>
                </CardContent>
              </Card>
            )}

            {!loadingPortfolios && !portfoliosError && filteredPortfolios.length === 0 && (
              <Card>
                <CardContent className="py-8">
                  <div className="text-center">
                    <Briefcase className="h-10 w-10 text-gray-400 mx-auto mb-2" />
                    <p className="text-sm text-gray-500 mb-3">
                      {searchQuery ? 'No portfolios match your search' : 'No portfolios yet'}
                    </p>
                    {!searchQuery && (
                      <Button size="sm" onClick={() => setCreateDialogOpen(true)}>
                        <Plus className="h-4 w-4 mr-2" />
                        Create First Portfolio
                      </Button>
                    )}
                  </div>
                </CardContent>
              </Card>
            )}

            {!loadingPortfolios && !portfoliosError && filteredPortfolios.map((portfolio) => (
              <Card
                key={portfolio.id}
                className={`cursor-pointer transition-all hover:shadow-md ${
                  selectedPortfolioId === portfolio.id ? 'ring-2 ring-blue-500' : ''
                }`}
                onClick={() => setSelectedPortfolioId(portfolio.id)}
              >
                <CardHeader className="pb-2">
                  <div className="flex items-start justify-between">
                    <div>
                      <CardTitle className="text-base">{portfolio.name}</CardTitle>
                      <CardDescription>{formatDate(portfolio.created_at)}</CardDescription>
                    </div>
                    <DropdownMenu>
                      <DropdownMenuTrigger asChild onClick={(e) => e.stopPropagation()}>
                        <Button variant="ghost" size="sm">
                          <MoreHorizontal className="h-4 w-4" />
                        </Button>
                      </DropdownMenuTrigger>
                      <DropdownMenuContent align="end">
                        <DropdownMenuItem
                          onClick={(e) => {
                            e.stopPropagation();
                            setSelectedPortfolioId(portfolio.id);
                          }}
                        >
                          <Eye className="h-4 w-4 mr-2" />
                          View Details
                        </DropdownMenuItem>
                        <DropdownMenuItem
                          onClick={(e) => {
                            e.stopPropagation();
                            handleDeletePortfolio(portfolio.id);
                          }}
                          className="text-red-600"
                        >
                          <Trash2 className="h-4 w-4 mr-2" />
                          Delete
                        </DropdownMenuItem>
                      </DropdownMenuContent>
                    </DropdownMenu>
                  </div>
                </CardHeader>
                <CardContent>
                  <div className="flex items-center justify-between text-sm">
                    <div className="flex items-center gap-1 text-muted-foreground">
                      <Home className="h-3 w-3" />
                      {portfolio.property_count} properties
                    </div>
                    <div className="font-medium">{formatCurrency(portfolio.total_value)}</div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>

          {/* Portfolio Details */}
          <div className="md:col-span-2 space-y-4">
            {!selectedPortfolioId ? (
              <Card>
                <CardContent className="py-20">
                  <div className="text-center">
                    <Briefcase className="h-16 w-16 text-gray-300 mx-auto mb-4" />
                    <h3 className="text-lg font-medium text-gray-900">Select a Portfolio</h3>
                    <p className="text-gray-500 mt-2">
                      Choose a portfolio from the list to view details and manage properties
                    </p>
                  </div>
                </CardContent>
              </Card>
            ) : loadingDetail ? (
              <Card>
                <CardHeader>
                  <Skeleton className="h-6 w-[200px]" />
                  <Skeleton className="h-4 w-[150px]" />
                </CardHeader>
                <CardContent>
                  <div className="space-y-4">
                    {[...Array(3)].map((_, i) => (
                      <div key={i} className="flex items-center gap-4">
                        <Skeleton className="h-10 w-10 rounded" />
                        <div className="flex-1">
                          <Skeleton className="h-4 w-[200px]" />
                          <Skeleton className="h-3 w-[150px] mt-1" />
                        </div>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            ) : selectedPortfolio ? (
              <>
                {/* Portfolio Header */}
                <Card>
                  <CardHeader>
                    <div className="flex items-start justify-between">
                      <div>
                        <CardTitle>{selectedPortfolio.name}</CardTitle>
                        <CardDescription>
                          {selectedPortfolio.property_count} properties | Created {formatDate(selectedPortfolio.created_at)}
                        </CardDescription>
                      </div>
                      <div className="flex gap-2">
                        <Button
                          variant="secondary"
                          size="sm"
                          onClick={() => refetchDetail()}
                        >
                          <RefreshCw className="h-4 w-4" />
                        </Button>
                        <DropdownMenu>
                          <DropdownMenuTrigger asChild>
                            <Button variant="secondary" size="sm">
                              <Download className="h-4 w-4 mr-2" />
                              Export
                            </Button>
                          </DropdownMenuTrigger>
                          <DropdownMenuContent>
                            <DropdownMenuItem
                              onClick={() => exportMutation.mutate(selectedPortfolioId!)}
                              disabled={exportMutation.isPending}
                            >
                              Export as CSV
                            </DropdownMenuItem>
                          </DropdownMenuContent>
                        </DropdownMenu>
                        <Button
                          variant="secondary"
                          size="sm"
                          onClick={handleImportClick}
                          disabled={importMutation.isPending}
                        >
                          <Upload className="h-4 w-4 mr-2" />
                          {importMutation.isPending ? 'Importing...' : 'Import CSV'}
                        </Button>
                        <input
                          type="file"
                          ref={fileInputRef}
                          onChange={handleFileChange}
                          accept=".csv"
                          className="hidden"
                        />
                        <Button
                          size="sm"
                          onClick={() => analyzeAllMutation.mutate(selectedPortfolioId!)}
                          disabled={analyzeAllMutation.isPending}
                        >
                          <TrendingUp className="h-4 w-4 mr-2" />
                          {analyzeAllMutation.isPending ? 'Analyzing...' : 'Analyze All'}
                        </Button>
                      </div>
                    </div>
                  </CardHeader>
                  <CardContent>
                    <div className="grid grid-cols-3 gap-4">
                      <div className="text-center p-4 bg-gray-50 rounded-lg">
                        <div className="text-2xl font-bold">{selectedPortfolio.property_count}</div>
                        <div className="text-sm text-muted-foreground">Properties</div>
                      </div>
                      <div className="text-center p-4 bg-gray-50 rounded-lg">
                        <div className="text-2xl font-bold text-blue-600">
                          {formatCurrency(selectedPortfolio.total_value)}
                        </div>
                        <div className="text-sm text-muted-foreground">Total Value</div>
                      </div>
                      <div className="text-center p-4 bg-gray-50 rounded-lg">
                        <div className="text-2xl font-bold text-green-600">
                          {formatCurrency(selectedPortfolio.total_potential_savings || 0)}
                        </div>
                        <div className="text-sm text-muted-foreground">Potential Savings</div>
                      </div>
                    </div>
                  </CardContent>
                </Card>

                {/* Properties List */}
                <Card>
                  <CardHeader>
                    <div className="flex items-center justify-between">
                      <CardTitle className="text-base">Properties</CardTitle>
                      <Button size="sm" onClick={() => setAddPropertyDialogOpen(true)}>
                        <Plus className="h-4 w-4 mr-2" />
                        Add Property
                      </Button>
                    </div>
                  </CardHeader>
                  <CardContent>
                    {selectedPortfolio.properties.length === 0 ? (
                      <div className="text-center py-10">
                        <Home className="h-10 w-10 text-gray-400 mx-auto mb-2" />
                        <p className="text-gray-500">No properties in this portfolio</p>
                        <Button
                          size="sm"
                          className="mt-3"
                          onClick={() => setAddPropertyDialogOpen(true)}
                        >
                          <Plus className="h-4 w-4 mr-2" />
                          Add First Property
                        </Button>
                      </div>
                    ) : (
                      <Table>
                        <TableHeader>
                          <TableRow>
                            <TableHead>Address</TableHead>
                            <TableHead>Parcel ID</TableHead>
                            <TableHead className="text-right">Value</TableHead>
                            <TableHead>Type</TableHead>
                            <TableHead></TableHead>
                          </TableRow>
                        </TableHeader>
                        <TableBody>
                          {selectedPortfolio.properties.map((property) => (
                            <TableRow key={property.id}>
                              <TableCell className="font-medium">
                                {property.address || 'Unknown'}
                              </TableCell>
                              <TableCell className="text-muted-foreground">
                                {property.parcel_id}
                              </TableCell>
                              <TableCell className="text-right">
                                {formatCurrency(property.total_value)}
                              </TableCell>
                              <TableCell>
                                <Badge variant="outline">
                                  {property.property_type || 'Unknown'}
                                </Badge>
                              </TableCell>
                              <TableCell>
                                <div className="flex items-center gap-1">
                                  <Link href={`/properties/${property.id}`}>
                                    <Button variant="ghost" size="sm">
                                      View
                                    </Button>
                                  </Link>
                                  <DropdownMenu>
                                    <DropdownMenuTrigger asChild>
                                      <Button variant="ghost" size="sm">
                                        <MoreHorizontal className="h-4 w-4" />
                                      </Button>
                                    </DropdownMenuTrigger>
                                    <DropdownMenuContent align="end">
                                      <DropdownMenuItem
                                        onClick={() => router.push(`/properties/${property.id}`)}
                                      >
                                        <Eye className="h-4 w-4 mr-2" />
                                        View Property
                                      </DropdownMenuItem>
                                      <DropdownMenuItem
                                        onClick={() => router.push(`/properties/${property.id}?tab=analysis`)}
                                      >
                                        <TrendingUp className="h-4 w-4 mr-2" />
                                        Run Analysis
                                      </DropdownMenuItem>
                                      <DropdownMenuItem
                                        onClick={() => handleRemoveProperty(property.id)}
                                        className="text-red-600"
                                      >
                                        <Trash2 className="h-4 w-4 mr-2" />
                                        Remove from Portfolio
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
              </>
            ) : null}
          </div>
        </div>
      </div>

      {/* Create Portfolio Dialog */}
      <CreatePortfolioDialog
        open={createDialogOpen}
        onOpenChange={setCreateDialogOpen}
        onSuccess={(id) => setSelectedPortfolioId(id)}
      />

      {/* Add Property Dialog */}
      <PropertySearchDialog
        open={addPropertyDialogOpen}
        onOpenChange={setAddPropertyDialogOpen}
        onSelect={handleAddProperty}
        title="Add Property to Portfolio"
        description="Search for a property to add to this portfolio"
        excludeIds={selectedPortfolio?.properties.map((p) => p.id) || []}
      />

      {/* Delete Portfolio Confirmation */}
      <ConfirmDialog
        open={deleteDialogOpen}
        onOpenChange={setDeleteDialogOpen}
        title="Delete Portfolio"
        description="Are you sure you want to delete this portfolio? This action cannot be undone. Properties will not be deleted."
        confirmLabel="Delete"
        variant="destructive"
        onConfirm={handleDeleteConfirm}
        loading={deletePorfolioMutation.isPending}
      />

      {/* Remove Property Confirmation */}
      <ConfirmDialog
        open={removePropertyDialogOpen}
        onOpenChange={setRemovePropertyDialogOpen}
        title="Remove Property"
        description="Are you sure you want to remove this property from the portfolio?"
        confirmLabel="Remove"
        variant="destructive"
        onConfirm={handleRemovePropertyConfirm}
        loading={removePropertyMutation.isPending}
      />
    </MainLayout>
  );
}
