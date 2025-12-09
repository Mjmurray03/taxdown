// Console logging for debugging
export const debugLog = (component: string, action: string, data?: any) => {
  if (process.env.NODE_ENV === 'development') {
    console.log(`[${component}] ${action}`, data || '');
  }
};

// Validate API response structure
export const validateResponse = <T>(response: any, requiredFields: string[]): response is T => {
  return requiredFields.every(field => field in response);
};

// Format currency values
export const formatCurrency = (value: number | null | undefined): string => {
  if (value == null) return '$0';
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(value);
};

// Format number with thousands separator
export const formatNumber = (value: number | null | undefined): string => {
  if (value == null) return '0';
  return new Intl.NumberFormat('en-US').format(value);
};

// Calculate days until deadline
export const daysUntil = (dateString: string): number => {
  const deadline = new Date(dateString);
  const today = new Date();
  const diffTime = deadline.getTime() - today.getTime();
  return Math.ceil(diffTime / (1000 * 60 * 60 * 24));
};

// Get urgency color based on days remaining
export const getUrgencyColor = (daysRemaining: number): string => {
  if (daysRemaining < 14) return 'destructive';
  if (daysRemaining < 30) return 'warning';
  return 'default';
};
