import { createFileRoute } from '@tanstack/react-router'
import StatsMetricsInterface from '@/components/App/Stats/StatsMetricsInterface'

export const Route = createFileRoute('/_authenticated/stats')({
  component: () => <StatsMetricsInterface />,
})
