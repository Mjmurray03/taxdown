import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { FileText, Search, TrendingUp } from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';

// Placeholder - would come from API
const activities = [
  {
    id: 1,
    type: 'analysis',
    description: 'Analysis completed for 123 Main St',
    result: 'Appeal recommended - $450/yr savings',
    timestamp: new Date(Date.now() - 1000 * 60 * 30),
    icon: TrendingUp,
    color: 'text-green-600',
  },
  {
    id: 2,
    type: 'appeal',
    description: 'Appeal generated for 456 Oak Ave',
    result: 'Ready to file',
    timestamp: new Date(Date.now() - 1000 * 60 * 60 * 2),
    icon: FileText,
    color: 'text-blue-600',
  },
  {
    id: 3,
    type: 'search',
    description: 'Searched properties in Bella Vista',
    result: '47 results found',
    timestamp: new Date(Date.now() - 1000 * 60 * 60 * 24),
    icon: Search,
    color: 'text-gray-600',
  },
];

export function RecentActivity() {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Recent Activity</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          {activities.map((activity) => {
            const Icon = activity.icon;
            return (
              <div
                key={activity.id}
                className="flex items-start space-x-4 p-3 rounded-lg hover:bg-gray-50"
              >
                <div className={`p-2 rounded-full bg-gray-100 ${activity.color}`}>
                  <Icon className="h-4 w-4" />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium">{activity.description}</p>
                  <p className="text-xs text-muted-foreground">{activity.result}</p>
                </div>
                <div className="text-xs text-muted-foreground whitespace-nowrap">
                  {formatDistanceToNow(activity.timestamp, { addSuffix: true })}
                </div>
              </div>
            );
          })}
        </div>
      </CardContent>
    </Card>
  );
}
