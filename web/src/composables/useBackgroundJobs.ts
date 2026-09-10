import { useQuery } from '@tanstack/vue-query'
import { computed } from 'vue'
import { apiClient } from '@/lib/api/client'
import { normalizeBackgroundJobs } from '@/lib/background-jobs'

/** Polls `/health/background-jobs` for in-process ParseAll / UpdateTasks. */
export function useBackgroundJobs() {
  const query = useQuery({
    queryKey: ['health', 'background-jobs'],
    queryFn: () => apiClient.getBackgroundJobs(),
    refetchInterval: 15_000,
    retry: 1,
  })

  const jobs = computed(() => normalizeBackgroundJobs(query.data.value))

  return {
    ...query,
    jobs,
  }
}
