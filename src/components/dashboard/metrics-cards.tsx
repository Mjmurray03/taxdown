import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import {
  DollarSign,
  Home,
  TrendingUp,
  Calculator
} from 'lucide-react';

interface Metrics {
  total_properties: number;
  total_market_value: number;
  total_assessed_value: number;
  estimated_annual_tax: number;
  total_potential_savings: number;
  appeal_candidates: number;
  average_fairness_score: number | null;
}

export function MetricsCards({ metrics }: { metrics: Metrics }) {
  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(value);
  };

  const cards = [
    {
      title: 'Total Properties',
      value: metrics.total_properties.toString(),
      description: 'In your portfolio',
      icon: Home,
      color: 'text-blue-600',
      bgColor: 'bg-blue-50',
    },
    {
      title: 'Portfolio Value',
      value: formatCurrency(metrics.total_market_value),
      description: `Assessed: ${formatCurrency(metrics.total_assessed_value)}`,
      icon: DollarSign,
      color: 'text-green-600',
      bgColor: 'bg-green-50',
    },
    {
      title: 'Potential Savings',
      value: formatCurrency(metrics.total_potential_savings),
      description: `${metrics.appeal_candidates} properties eligible`,
      icon: TrendingUp,
      color: 'text-purple-600',
      bgColor: 'bg-purple-50',
      highlight: metrics.total_potential_savings > 0,
    },
    {
      title: 'Annual Tax',
      value: formatCurrency(metrics.estimated_annual_tax),
      description: metrics.average_fairness_score
        ? `Avg fairness: ${metrics.average_fairness_score.toFixed(0)}%`
        : 'Based on current assessments',
      icon: Calculator,
      color: 'text-orange-600',
      bgColor: 'bg-orange-50',
    },
  ];

  return (
    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
      {cards.map((card, index) => {
        const Icon = card.icon;
        return (
          <Card key={index} className={card.highlight ? 'ring-2 ring-purple-200' : ''}>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                {card.title}
              </CardTitle>
              <div className={`p-2 rounded-lg ${card.bgColor}`}>
                <Icon className={`h-4 w-4 ${card.color}`} />
              </div>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{card.value}</div>
              <p className="text-xs text-muted-foreground mt-1">
                {card.description}
              </p>
            </CardContent>
          </Card>
        );
      })}
    </div>
  );
}
