import { createFileRoute } from '@tanstack/react-router'
import StatsMetricsInterface from '@/components/App/Stats/StatsMetricsInterface'

export const Route = createFileRoute('/stats')({
  component: StatsMetricsInterface,
  beforeLoad: ({ context }) => {
    const { isAuthenticated, signinRedirect } = context.authentication;
    if (!isAuthenticated) {
      signinRedirect();
    }
  },
})
