'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import Link from 'next/link';
import { propertyApi, analysisApi } from '@/lib/api';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { Skeleton } from '@/components/ui/skeleton';
import { useToast } from '@/components/ui/use-toast';
import {
  ArrowLeft,
  RefreshCw,
  FileText,
  CheckCircle,
  AlertTriangle,
  MinusCircle,
  TrendingDown,
  TrendingUp,
  Home
} from 'lucide-react';

interface AnalysisPageProps {
  propertyId: string;
}

export function AnalysisPage({ propertyId }: AnalysisPageProps) {
  const queryClient = useQueryClient();
  const { toast } = useToast();

  const { data: propertyData, isLoading: propertyLoading } = useQuery({
    queryKey: ['property', propertyId],
    queryFn: () => propertyApi.getById(propertyId),
  });

  const analyzeMutation = useMutation({
    mutationFn: () => analysisApi.analyze(propertyId, { force_reanalyze: true, include_comparables: true }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['property', propertyId] });
      toast({
        title: 'Analysis Complete',
        description: 'Property assessment has been analyzed.',
      });
    },
    onError: () => {
      toast({
        title: 'Analysis Failed',
        description: 'Could not complete analysis. Please try again.',
        variant: 'destructive',
      });
    },
  });

  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 0,
    }).format(value);
  };

  if (propertyLoading) {
    return <AnalysisSkeleton />;
  }

  const property = propertyData?.data;
  const analysis = property?.latest_analysis;

  if (!property) {
    return (
      <div className="text-center py-12">
        <p className="text-red-500 mb-4">Property not found</p>
        <Link href="/properties">
          <Button variant="outline">
            <ArrowLeft className="mr-2 h-4 w-4" /> Back to Properties
          </Button>
        </Link>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Link href={`/properties/${propertyId}`}>
            <Button variant="ghost" size="sm">
              <ArrowLeft className="mr-2 h-4 w-4" /> Back
            </Button>
          </Link>
          <div>
            <h1 className="text-2xl font-bold">Assessment Analysis</h1>
            <p className="text-muted-foreground">{property.address}</p>
          </div>
        </div>
        <Button
          onClick={() => analyzeMutation.mutate()}
          disabled={analyzeMutation.isPending}
        >
          {analyzeMutation.isPending ? (
            <>
              <RefreshCw className="mr-2 h-4 w-4 animate-spin" />
              Analyzing...
            </>
          ) : (
            <>
              <RefreshCw className="mr-2 h-4 w-4" />
              {analysis ? 'Re-Analyze' : 'Run Analysis'}
            </>
          )}
        </Button>
      </div>

      {!analysis ? (
        <Card>
          <CardContent className="py-12 text-center">
            <div className="mx-auto w-12 h-12 rounded-full bg-blue-100 flex items-center justify-center mb-4">
              <Home className="h-6 w-6 text-blue-600" />
            </div>
            <h3 className="text-lg font-semibold mb-2">No Analysis Yet</h3>
            <p className="text-muted-foreground mb-4">
              Run an analysis to see if this property may be over-assessed.
            </p>
            <Button onClick={() => analyzeMutation.mutate()}>
              Run Analysis
            </Button>
          </CardContent>
        </Card>
      ) : (
        <>
          {/* Score Card */}
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle>Fairness Score</CardTitle>
                  <CardDescription>
                    How your assessment compares to similar properties
                  </CardDescription>
                </div>
                <RecommendationBadge action={analysis.recommended_action} />
              </div>
            </CardHeader>
            <CardContent>
              <div className="space-y-6">
                {/* Score Display */}
                <div className="flex items-center gap-8">
                  <div className="text-center">
                    <div className="text-5xl font-bold">{analysis.fairness_score}</div>
                    <div className="text-sm text-muted-foreground">out of 100</div>
                  </div>
                  <div className="flex-1">
                    <Progress
                      value={analysis.fairness_score}
                      className="h-4"
                    />
                    <div className="flex justify-between text-xs text-muted-foreground mt-1">
                      <span>Under-assessed</span>
                      <span>Fair</span>
                      <span>Over-assessed</span>
                    </div>
                  </div>
                </div>

                {/* Interpretation */}
                <div className="p-4 rounded-lg bg-gray-50">
                  <ScoreInterpretation score={analysis.fairness_score} />
                </div>

                {/* Confidence */}
                <div className="flex items-center gap-2 text-sm">
                  <span className="text-muted-foreground">Confidence Level:</span>
                  <Badge variant="secondary">{analysis.confidence_level}%</Badge>
                  <span className="text-muted-foreground">
                    based on {analysis.comparable_count} comparable properties
                  </span>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Value Comparison */}
          <div className="grid gap-6 md:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle>Current Assessment</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div>
                  <p className="text-sm text-muted-foreground">Market Value</p>
                  <p className="text-2xl font-bold">{formatCurrency(property.market_value)}</p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Assessed Value</p>
                  <p className="text-xl font-semibold">{formatCurrency(property.assessed_value)}</p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Assessment Ratio</p>
                  <p className="text-lg">
                    {((property.assessed_value / property.market_value) * 100).toFixed(1)}%
                  </p>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Fair Assessment</CardTitle>
                <CardDescription>Based on comparable properties</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div>
                  <p className="text-sm text-muted-foreground">Fair Assessed Value</p>
                  <p className="text-2xl font-bold text-green-600">
                    {formatCurrency(analysis.fair_assessed_value)}
                  </p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Difference</p>
                  <p className="text-xl font-semibold flex items-center gap-2">
                    {property.assessed_value > analysis.fair_assessed_value ? (
                      <>
                        <TrendingDown className="h-5 w-5 text-red-500" />
                        <span className="text-red-600">
                          {formatCurrency(property.assessed_value - analysis.fair_assessed_value)} over
                        </span>
                      </>
                    ) : (
                      <>
                        <TrendingUp className="h-5 w-5 text-green-500" />
                        <span className="text-green-600">
                          {formatCurrency(analysis.fair_assessed_value - property.assessed_value)} under
                        </span>
                      </>
                    )}
                  </p>
                </div>
                <div className="p-4 rounded-lg bg-green-50 border border-green-200">
                  <p className="text-sm text-green-800">Potential Annual Savings</p>
                  <p className="text-2xl font-bold text-green-700">
                    {formatCurrency(analysis.estimated_savings)}
                  </p>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Actions */}
          {analysis.recommended_action === 'APPEAL' && (
            <Card className="border-green-200 bg-green-50">
              <CardContent className="py-6">
                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="text-lg font-semibold text-green-800">
                      This property qualifies for appeal
                    </h3>
                    <p className="text-green-700">
                      Generate a professional appeal letter with supporting evidence.
                    </p>
                  </div>
                  <Link href={`/appeals/generate/${propertyId}`}>
                    <Button size="lg" className="bg-green-600 hover:bg-green-700">
                      <FileText className="mr-2 h-5 w-5" />
                      Generate Appeal
                    </Button>
                  </Link>
                </div>
              </CardContent>
            </Card>
          )}
        </>
      )}
    </div>
  );
}

function RecommendationBadge({ action }: { action: string }) {
  const config = {
    APPEAL: { icon: AlertTriangle, color: 'bg-red-100 text-red-800', label: 'Appeal Recommended' },
    MONITOR: { icon: MinusCircle, color: 'bg-yellow-100 text-yellow-800', label: 'Monitor' },
    NONE: { icon: CheckCircle, color: 'bg-green-100 text-green-800', label: 'Fairly Assessed' },
  }[action] || { icon: MinusCircle, color: 'bg-gray-100 text-gray-800', label: action };

  const Icon = config.icon;

  return (
    <Badge className={config.color}>
      <Icon className="mr-1 h-3 w-3" />
      {config.label}
    </Badge>
  );
}

function ScoreInterpretation({ score }: { score: number }) {
  if (score >= 70) {
    return (
      <p className="text-red-700">
        <strong>Significantly Over-Assessed:</strong> Your property appears to be assessed
        considerably higher than comparable properties. Filing an appeal is strongly recommended.
      </p>
    );
  }
  if (score >= 50) {
    return (
      <p className="text-orange-700">
        <strong>Moderately Over-Assessed:</strong> Your property assessment is higher than
        average for similar properties. An appeal may result in meaningful savings.
      </p>
    );
  }
  if (score >= 30) {
    return (
      <p className="text-yellow-700">
        <strong>Slightly Over-Assessed:</strong> Your assessment is somewhat higher than
        comparable properties. Consider monitoring for future changes.
      </p>
    );
  }
  return (
    <p className="text-green-700">
      <strong>Fairly Assessed:</strong> Your property assessment is in line with or
      below comparable properties. No action needed.
    </p>
  );
}

function AnalysisSkeleton() {
  return (
    <div className="space-y-6">
      <Skeleton className="h-12 w-96" />
      <Skeleton className="h-64" />
      <div className="grid gap-6 md:grid-cols-2">
        <Skeleton className="h-48" />
        <Skeleton className="h-48" />
      </div>
    </div>
  );
}
