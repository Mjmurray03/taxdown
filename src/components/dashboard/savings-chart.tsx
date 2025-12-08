'use client';

import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { PieChart, Pie, Cell, ResponsiveContainer, Legend, Tooltip } from 'recharts';

interface SavingsChartProps {
  totalSavings: number;
  appealCandidates: number;
}

export function SavingsChart({ totalSavings, appealCandidates }: SavingsChartProps) {
  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 0,
    }).format(value);
  };

  // Mock data - would come from API
  const data = [
    { name: 'Highly Over-assessed (70+)', value: Math.floor(appealCandidates * 0.3), color: '#ef4444' },
    { name: 'Moderately Over-assessed (50-70)', value: Math.floor(appealCandidates * 0.5), color: '#f97316' },
    { name: 'Slightly Over-assessed (30-50)', value: Math.floor(appealCandidates * 0.2), color: '#eab308' },
  ];

  if (totalSavings === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Savings Breakdown</CardTitle>
          <CardDescription>
            No over-assessed properties detected
          </CardDescription>
        </CardHeader>
        <CardContent className="flex items-center justify-center h-64">
          <p className="text-muted-foreground">
            All properties appear fairly assessed
          </p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Savings Breakdown</CardTitle>
        <CardDescription>
          {formatCurrency(totalSavings)} in potential annual savings
        </CardDescription>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={250}>
          <PieChart>
            <Pie
              data={data}
              cx="50%"
              cy="50%"
              innerRadius={60}
              outerRadius={80}
              paddingAngle={5}
              dataKey="value"
            >
              {data.map((entry, index) => (
                <Cell key={`cell-${index}`} fill={entry.color} />
              ))}
            </Pie>
            <Tooltip
              formatter={(value: number) => [`${value} properties`, '']}
            />
            <Legend />
          </PieChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
}
