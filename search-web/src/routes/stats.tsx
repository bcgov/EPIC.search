import { createFileRoute } from '@tanstack/react-router'
import StatsMetricsInterface from '@/components/App/Stats/StatsMetricsInterface'

export const Route = createFileRoute('/stats')({
  component: StatsMetricsInterface,
  beforeLoad: () => {
    // Explicitly allow anonymous access - no authentication required
    return {};
  },
})
