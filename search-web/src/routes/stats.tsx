import { createFileRoute } from '@tanstack/react-router'
import StatsMetricsInterface from '@/components/App/Stats/StatsMetricsInterface'

export const Route = createFileRoute('/stats')({
  component: StatsMetricsInterface,
  beforeLoad: ({ context }) => {
    const { isAuthenticated, isLoading, signinRedirect } = context.authentication;
    
    // Wait for auth to load before making decision
    if (isLoading) {
      return {};
    }
    
    if (!isAuthenticated) {
      console.log('User not authenticated, redirecting to login');
      signinRedirect();
      return {};
    }
    
    return {};
  },
})
