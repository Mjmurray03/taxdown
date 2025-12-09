/**
 * Application configuration constants
 *
 * These values should be updated as needed for each tax year.
 * In the future, these could be fetched from the API.
 */

// Arkansas property tax appeal deadline
// This should be updated each year - currently set for 2026 tax year
export const APPEAL_DEADLINE = new Date('2026-03-01');

// Calculate days until deadline
export function getDaysUntilDeadline(): number {
  const today = new Date();
  return Math.ceil((APPEAL_DEADLINE.getTime() - today.getTime()) / (1000 * 60 * 60 * 24));
}

// Format the deadline for display
export function getFormattedDeadline(): string {
  return APPEAL_DEADLINE.toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
  });
}

// Default mill rate for Benton County, AR
export const DEFAULT_MILL_RATE = 65.0;

// Demo user ID - in production this would come from auth
export const DEMO_USER_ID = 'demo-user';
