import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Calendar, AlertTriangle } from 'lucide-react';
import { format, parseISO } from 'date-fns';

interface DeadlineAlertProps {
  deadline: string;
  daysRemaining: number;
}

export function DeadlineAlert({ deadline, daysRemaining }: DeadlineAlertProps) {
  const getAlertStyle = () => {
    if (daysRemaining <= 14) {
      return 'border-red-200 bg-red-50 text-red-800';
    }
    if (daysRemaining <= 30) {
      return 'border-orange-200 bg-orange-50 text-orange-800';
    }
    return 'border-blue-200 bg-blue-50 text-blue-800';
  };

  const Icon = daysRemaining <= 14 ? AlertTriangle : Calendar;

  return (
    <Alert className={getAlertStyle()}>
      <Icon className="h-4 w-4" />
      <AlertTitle className="font-semibold">
        {daysRemaining <= 14 ? 'Deadline Approaching!' : 'Appeal Deadline'}
      </AlertTitle>
      <AlertDescription>
        {daysRemaining} days until {format(parseISO(deadline), 'MMMM d, yyyy')}
      </AlertDescription>
    </Alert>
  );
}
