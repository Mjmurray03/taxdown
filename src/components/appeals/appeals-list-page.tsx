'use client';

import { useQuery } from '@tanstack/react-query';
import Link from 'next/link';
import { appealApi } from '@/lib/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { FileText, Download, Eye, Plus } from 'lucide-react';
import { format, parseISO } from 'date-fns';

export function AppealsListPage() {
  const { data, isLoading } = useQuery({
    queryKey: ['appeals'],
    queryFn: () => appealApi.list(),
  });

  const appeals = data?.data || [];

  const getStatusColor = (status: string) => {
    const colors: Record<string, string> = {
      DRAFT: 'bg-gray-100 text-gray-800',
      GENERATED: 'bg-blue-100 text-blue-800',
      SUBMITTED: 'bg-yellow-100 text-yellow-800',
      PENDING: 'bg-orange-100 text-orange-800',
      APPROVED: 'bg-green-100 text-green-800',
      DENIED: 'bg-red-100 text-red-800',
    };
    return colors[status] || 'bg-gray-100 text-gray-800';
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Appeals</h1>
          <p className="text-muted-foreground">
            Manage your property tax appeal letters
          </p>
        </div>
        <Link href="/properties?filter=appeal_candidates">
          <Button>
            <Plus className="mr-2 h-4 w-4" /> Find Properties to Appeal
          </Button>
        </Link>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Your Appeals</CardTitle>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="flex items-center justify-center py-12">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600" />
            </div>
          ) : appeals.length === 0 ? (
            <div className="text-center py-12">
              <FileText className="mx-auto h-12 w-12 text-muted-foreground mb-4" />
              <h3 className="text-lg font-semibold mb-2">No Appeals Yet</h3>
              <p className="text-muted-foreground mb-4">
                Search for properties with high fairness scores to generate appeals.
              </p>
              <Link href="/properties">
                <Button>Browse Properties</Button>
              </Link>
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Property</TableHead>
                  <TableHead>Parcel ID</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Generated</TableHead>
                  <TableHead>Deadline</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {appeals.map((appeal) => (
                  <TableRow key={appeal.id}>
                    <TableCell className="font-medium">
                      {appeal.address || 'N/A'}
                    </TableCell>
                    <TableCell className="font-mono text-sm">
                      {appeal.parcel_id}
                    </TableCell>
                    <TableCell>
                      <Badge className={getStatusColor(appeal.status)}>
                        {appeal.status}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      {appeal.created_at
                        ? format(parseISO(appeal.created_at), 'MMM d, yyyy')
                        : 'N/A'}
                    </TableCell>
                    <TableCell>
                      {appeal.filing_deadline
                        ? format(parseISO(appeal.filing_deadline), 'MMM d, yyyy')
                        : 'N/A'}
                    </TableCell>
                    <TableCell className="text-right">
                      <div className="flex items-center justify-end gap-2">
                        <Link href={`/appeals/${appeal.id}`}>
                          <Button variant="ghost" size="sm">
                            <Eye className="h-4 w-4" />
                          </Button>
                        </Link>
                        <Button variant="ghost" size="sm">
                          <Download className="h-4 w-4" />
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
