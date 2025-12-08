'use client';

import { MainLayout } from '@/components/layout/main-layout';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import {
  BarChart3,
  FileText,
  Download,
  Calendar,
  TrendingUp,
  Home,
  DollarSign,
  PieChart,
} from 'lucide-react';

export default function ReportsPage() {
  const reportTypes = [
    {
      id: 'savings-summary',
      title: 'Savings Summary',
      description: 'Overview of potential tax savings across all properties',
      icon: DollarSign,
      badge: 'Popular',
    },
    {
      id: 'appeal-status',
      title: 'Appeal Status Report',
      description: 'Track the status of all submitted appeals',
      icon: FileText,
      badge: null,
    },
    {
      id: 'portfolio-analysis',
      title: 'Portfolio Analysis',
      description: 'Detailed analysis of portfolio performance',
      icon: BarChart3,
      badge: null,
    },
    {
      id: 'assessment-trends',
      title: 'Assessment Trends',
      description: 'Historical assessment trends and predictions',
      icon: TrendingUp,
      badge: 'New',
    },
    {
      id: 'property-comparison',
      title: 'Property Comparison',
      description: 'Compare multiple properties side by side',
      icon: Home,
      badge: null,
    },
    {
      id: 'tax-breakdown',
      title: 'Tax Breakdown',
      description: 'Detailed breakdown of tax calculations',
      icon: PieChart,
      badge: null,
    },
  ];

  const recentReports = [
    {
      name: 'Monthly Savings Summary - November 2024',
      date: '2024-11-30',
      type: 'Savings Summary',
    },
    {
      name: 'Q3 Portfolio Analysis',
      date: '2024-10-15',
      type: 'Portfolio Analysis',
    },
    {
      name: 'Appeal Status Update - October',
      date: '2024-10-31',
      type: 'Appeal Status',
    },
  ];

  return (
    <MainLayout>
      <div className="space-y-6">
        {/* Page Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold tracking-tight">Reports</h1>
            <p className="text-muted-foreground">
              Generate and view property tax reports
            </p>
          </div>
          <Button>
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
                <Card key={report.id} className="hover:shadow-md transition-shadow cursor-pointer">
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
                    <Button variant="outline" className="w-full">
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
            <CardTitle>Recent Reports</CardTitle>
            <CardDescription>
              Previously generated reports
            </CardDescription>
          </CardHeader>
          <CardContent>
            {recentReports.length > 0 ? (
              <div className="space-y-4">
                {recentReports.map((report, index) => (
                  <div
                    key={index}
                    className="flex items-center justify-between p-4 border rounded-lg hover:bg-gray-50 transition-colors"
                  >
                    <div className="flex items-center gap-3">
                      <div className="h-10 w-10 rounded-lg bg-gray-100 flex items-center justify-center">
                        <FileText className="h-5 w-5 text-gray-600" />
                      </div>
                      <div>
                        <p className="font-medium">{report.name}</p>
                        <p className="text-sm text-muted-foreground">
                          {report.type} - Generated {new Date(report.date).toLocaleDateString()}
                        </p>
                      </div>
                    </div>
                    <Button variant="ghost" size="sm">
                      <Download className="h-4 w-4 mr-2" />
                      Download
                    </Button>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-center py-10">
                <FileText className="h-10 w-10 text-gray-400 mx-auto mb-4" />
                <h3 className="text-lg font-medium text-gray-900">No reports yet</h3>
                <p className="text-gray-500 mt-2">
                  Generate a report to see it here
                </p>
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
              <div className="text-2xl font-bold">24</div>
              <p className="text-xs text-muted-foreground">This month</p>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium">Scheduled Reports</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">3</div>
              <p className="text-xs text-muted-foreground">Active schedules</p>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium">Data Updated</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">5 min ago</div>
              <p className="text-xs text-muted-foreground">Last sync</p>
            </CardContent>
          </Card>
        </div>
      </div>
    </MainLayout>
  );
}
