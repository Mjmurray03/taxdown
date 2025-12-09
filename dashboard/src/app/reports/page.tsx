'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { MainLayout } from '@/components/layout/main-layout';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
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
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import {
  BarChart3,
  FileText,
  Download,
  Calendar,
  TrendingUp,
  Home,
  DollarSign,
  PieChart,
  Trash2,
  RefreshCw,
  AlertTriangle,
  CheckCircle,
} from 'lucide-react';
import {
  reportApi,
  portfolioApi,
  ReportConfig,
  GeneratedReport,
  PortfolioSummary,
  APIResponse,
} from '@/lib/api';
import { ConfirmDialog } from '@/components/ui/confirm-dialog';
import { useDownload } from '@/lib/hooks';
import { toast } from 'sonner';

interface ReportType {
  id: ReportConfig['report_type'];
  title: string;
  description: string;
  icon: React.ComponentType<{ className?: string }>;
  badge: string | null;
}

const reportTypes: ReportType[] = [
  {
    id: 'portfolio_summary',
    title: 'Portfolio Summary',
    description: 'Overview of your portfolio with potential tax savings',
    icon: DollarSign,
    badge: 'Popular',
  },
  {
    id: 'appeal_package',
    title: 'Appeal Package',
    description: 'Generate complete appeal documentation',
    icon: FileText,
    badge: null,
  },
  {
    id: 'property_analysis',
    title: 'Property Analysis',
    description: 'Detailed analysis of individual properties',
    icon: BarChart3,
    badge: null,
  },
  {
    id: 'comparables',
    title: 'Comparable Properties',
    description: 'Compare properties with similar assessments',
    icon: Home,
    badge: null,
  },
];

export default function ReportsPage() {
  const queryClient = useQueryClient();
  const download = useDownload();

  // State
  const [generateDialogOpen, setGenerateDialogOpen] = useState(false);
  const [selectedReportType, setSelectedReportType] = useState<ReportType | null>(null);
  const [selectedPortfolioId, setSelectedPortfolioId] = useState<string>('');
  const [selectedFormat, setSelectedFormat] = useState<'pdf' | 'csv' | 'xlsx'>('pdf');
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [reportToDelete, setReportToDelete] = useState<string | null>(null);
  const [scheduleDialogOpen, setScheduleDialogOpen] = useState(false);

  // Demo user ID
  const userId = 'demo-user';

  // Fetch portfolios for selection
  const { data: portfoliosData } = useQuery<APIResponse<PortfolioSummary[]>>({
    queryKey: ['portfolios', userId],
    queryFn: () => portfolioApi.list(userId),
  });

  const portfolios = portfoliosData?.data || [];

  // Fetch generated reports
  const { data: reportsData, isLoading: loadingReports, error: reportsError, refetch: refetchReports } = useQuery<APIResponse<GeneratedReport[]>>({
    queryKey: ['reports'],
    queryFn: () => reportApi.list(),
  });

  const generatedReports = reportsData?.data || [];

  // Generate report mutation
  const generateMutation = useMutation({
    mutationFn: (config: ReportConfig) => reportApi.generate(config),
    onSuccess: (data) => {
      toast.success('Report generated successfully');
      queryClient.invalidateQueries({ queryKey: ['reports'] });
      setGenerateDialogOpen(false);
      setSelectedReportType(null);
      setSelectedPortfolioId('');
      setDateRange({ start: '', end: '' });
    },
    onError: (error) => {
      toast.error('Failed to generate report: ' + (error instanceof Error ? error.message : 'Unknown error'));
    },
  });

  // Download report mutation
  const downloadMutation = useMutation({
    mutationFn: (reportId: string) => reportApi.download(reportId),
    onSuccess: (blob, reportId) => {
      const report = generatedReports.find((r) => r.id === reportId);
      download(blob, `${report?.name || 'report'}.${report?.format || 'pdf'}`);
      toast.success('Report downloaded');
    },
    onError: (error) => {
      toast.error('Download failed');
    },
  });

  // Delete report mutation
  const deleteMutation = useMutation({
    mutationFn: (reportId: string) => reportApi.delete(reportId),
    onSuccess: () => {
      toast.success('Report deleted');
      queryClient.invalidateQueries({ queryKey: ['reports'] });
    },
    onError: (error) => {
      toast.error('Failed to delete report');
    },
  });

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString();
  };

  const handleGenerateClick = (reportType: ReportType) => {
    setSelectedReportType(reportType);
    setGenerateDialogOpen(true);
  };

  const handleGenerateSubmit = () => {
    if (!selectedReportType) return;

    const config: ReportConfig = {
      report_type: selectedReportType.id,
      portfolio_id: selectedPortfolioId || undefined,
      format: selectedFormat,
    };

    generateMutation.mutate(config);
  };

  const handleDeleteClick = (reportId: string) => {
    setReportToDelete(reportId);
    setDeleteDialogOpen(true);
  };

  const handleDeleteConfirm = () => {
    if (reportToDelete) {
      deleteMutation.mutate(reportToDelete);
    }
    setDeleteDialogOpen(false);
    setReportToDelete(null);
  };

  const handleDownload = (reportId: string) => {
    downloadMutation.mutate(reportId);
  };

  return (
    <MainLayout>
      <div className="space-y-6">
        {/* Page Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold tracking-tight">Reports</h1>
            <p className="text-muted-foreground">Generate and view property tax reports</p>
          </div>
          <Button onClick={() => setScheduleDialogOpen(true)}>
            <Calendar className="h-4 w-4 mr-2" />
            Schedule Report
          </Button>
        </div>

        {/* Report Types */}
        <div>
          <h2 className="text-xl font-semibold mb-4">Generate Report</h2>
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {reportTypes.map((report) => {
              const Icon = report.icon;
              return (
                <Card
                  key={report.id}
                  className="hover:shadow-md transition-shadow cursor-pointer"
                  onClick={() => handleGenerateClick(report)}
                >
                  <CardHeader>
                    <div className="flex items-start justify-between">
                      <div className="h-10 w-10 rounded-lg bg-blue-100 flex items-center justify-center">
                        <Icon className="h-5 w-5 text-blue-600" />
                      </div>
                      {report.badge && (
                        <Badge variant={report.badge === 'New' ? 'default' : 'secondary'}>
                          {report.badge}
                        </Badge>
                      )}
                    </div>
                    <CardTitle className="text-lg mt-2">{report.title}</CardTitle>
                    <CardDescription>{report.description}</CardDescription>
                  </CardHeader>
                  <CardContent>
                    <Button
                      variant="secondary"
                      className="w-full"
                      onClick={(e) => {
                        e.stopPropagation();
                        handleGenerateClick(report);
                      }}
                    >
                      Generate
                    </Button>
                  </CardContent>
                </Card>
              );
            })}
          </div>
        </div>

        {/* Recent Reports */}
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle>Recent Reports</CardTitle>
                <CardDescription>Previously generated reports</CardDescription>
              </div>
              <Button
                variant="secondary"
                size="sm"
                onClick={() => refetchReports()}
                disabled={loadingReports}
              >
                <RefreshCw className={`h-4 w-4 mr-2 ${loadingReports ? 'animate-spin' : ''}`} />
                Refresh
              </Button>
            </div>
          </CardHeader>
          <CardContent>
            {loadingReports && (
              <div className="space-y-4">
                {[...Array(3)].map((_, i) => (
                  <div key={i} className="flex items-center gap-4">
                    <Skeleton className="h-10 w-10 rounded" />
                    <div className="flex-1">
                      <Skeleton className="h-4 w-[200px]" />
                      <Skeleton className="h-3 w-[150px] mt-1" />
                    </div>
                    <Skeleton className="h-8 w-[100px]" />
                  </div>
                ))}
              </div>
            )}

            {reportsError && (
              <div className="text-center py-10">
                <AlertTriangle className="h-10 w-10 text-red-500 mx-auto mb-4" />
                <p className="text-gray-500">Failed to load reports</p>
                <Button variant="secondary" onClick={() => refetchReports()} className="mt-4">
                  Try Again
                </Button>
              </div>
            )}

            {!loadingReports && !reportsError && generatedReports.length === 0 && (
              <div className="text-center py-10">
                <FileText className="h-10 w-10 text-gray-400 mx-auto mb-4" />
                <h3 className="text-lg font-medium text-gray-900">No reports yet</h3>
                <p className="text-gray-500 mt-2">Generate a report to see it here</p>
              </div>
            )}

            {!loadingReports && !reportsError && generatedReports.length > 0 && (
              <div className="space-y-4">
                {generatedReports.map((report) => (
                  <div
                    key={report.id}
                    className="flex items-center justify-between p-4 border rounded-lg hover:bg-gray-50 transition-colors"
                  >
                    <div className="flex items-center gap-3">
                      <div className="h-10 w-10 rounded-lg bg-gray-100 flex items-center justify-center">
                        <FileText className="h-5 w-5 text-gray-600" />
                      </div>
                      <div>
                        <p className="font-medium">{report.name}</p>
                        <p className="text-sm text-muted-foreground">
                          {report.type} | {report.format.toUpperCase()} | Generated{' '}
                          {formatDate(report.created_at)}
                        </p>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleDownload(report.id)}
                        disabled={downloadMutation.isPending}
                      >
                        <Download className="h-4 w-4 mr-2" />
                        Download
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleDeleteClick(report.id)}
                        className="text-red-600 hover:text-red-700 hover:bg-red-50"
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Quick Stats */}
        <div className="grid gap-4 md:grid-cols-3">
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium">Reports Generated</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{generatedReports.length}</div>
              <p className="text-xs text-muted-foreground">Total reports</p>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium">Scheduled Reports</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">0</div>
              <p className="text-xs text-muted-foreground">Active schedules</p>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium">Data Updated</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">Just now</div>
              <p className="text-xs text-muted-foreground">Last sync</p>
            </CardContent>
          </Card>
        </div>
      </div>

      {/* Generate Report Dialog */}
      <Dialog open={generateDialogOpen} onOpenChange={setGenerateDialogOpen}>
        <DialogContent className="sm:max-w-[500px]">
          <DialogHeader>
            <DialogTitle>
              Generate {selectedReportType?.title || 'Report'}
            </DialogTitle>
            <DialogDescription>
              Configure the report options below
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-4">
            {/* Portfolio Selection */}
            <div className="space-y-2">
              <Label>Portfolio (Optional)</Label>
              <Select value={selectedPortfolioId} onValueChange={setSelectedPortfolioId}>
                <SelectTrigger>
                  <SelectValue placeholder="All portfolios" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="">All Portfolios</SelectItem>
                  {portfolios.map((portfolio) => (
                    <SelectItem key={portfolio.id} value={portfolio.id}>
                      {portfolio.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {/* Format Selection */}
            <div className="space-y-2">
              <Label>Output Format</Label>
              <Select
                value={selectedFormat}
                onValueChange={(value: 'pdf' | 'csv' | 'xlsx') => setSelectedFormat(value)}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="pdf">PDF Document</SelectItem>
                  <SelectItem value="csv">CSV Spreadsheet</SelectItem>
                  <SelectItem value="xlsx">Excel Workbook</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>

          <DialogFooter>
            <Button variant="secondary" onClick={() => setGenerateDialogOpen(false)}>
              Cancel
            </Button>
            <Button
              onClick={handleGenerateSubmit}
              disabled={generateMutation.isPending}
            >
              {generateMutation.isPending ? (
                <>
                  <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
                  Generating...
                </>
              ) : (
                'Generate Report'
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Schedule Report Dialog */}
      <Dialog open={scheduleDialogOpen} onOpenChange={setScheduleDialogOpen}>
        <DialogContent className="sm:max-w-[500px]">
          <DialogHeader>
            <DialogTitle>Schedule Report</DialogTitle>
            <DialogDescription>
              Set up automatic report generation on a schedule
            </DialogDescription>
          </DialogHeader>

          <div className="py-4">
            <div className="text-center py-8">
              <Calendar className="h-12 w-12 text-gray-400 mx-auto mb-4" />
              <h3 className="text-lg font-medium text-gray-900">Coming Soon</h3>
              <p className="text-gray-500 mt-2">
                Scheduled reports will be available in a future update
              </p>
            </div>
          </div>

          <DialogFooter>
            <Button variant="secondary" onClick={() => setScheduleDialogOpen(false)}>
              Close
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Delete Confirmation Dialog */}
      <ConfirmDialog
        open={deleteDialogOpen}
        onOpenChange={setDeleteDialogOpen}
        title="Delete Report"
        description="Are you sure you want to delete this report? This action cannot be undone."
        confirmLabel="Delete"
        variant="destructive"
        onConfirm={handleDeleteConfirm}
        loading={deleteMutation.isPending}
      />
    </MainLayout>
  );
}
