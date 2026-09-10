<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { Badge } from '@/components/ui/badge'
import {
  formatJobElapsed,
  jobProgressText,
  type BackgroundJob,
} from '@/lib/background-jobs'
import { getTrackerDisplayName } from '@/lib/stats'
import { getSafeIconPath } from '@/lib/torrents'

const props = defineProps<{
  jobs: BackgroundJob[]
  isLoading?: boolean
}>()

const { t, locale } = useI18n()

const rows = computed(() =>
  props.jobs.map((job) => {
    const slug = String(job.tracker || job.id?.split(':')[0] || '')
    const percent =
      typeof job.percent === 'number' && Number.isFinite(job.percent)
        ? Math.max(0, Math.min(100, Math.round(job.percent)))
        : null
    return {
      key: job.id || `${slug}:${job.job || 'job'}`,
      slug,
      name: getTrackerDisplayName(slug),
      iconSrc: getSafeIconPath(slug),
      action: job.job || 'ParseAllTask',
      progress: jobProgressText(job),
      elapsed: formatJobElapsed(job.elapsedSeconds, locale.value),
      percent,
    }
  }),
)
</script>

<template>
  <section
    class="jr-elevated rounded-xl border p-4"
    :aria-label="t('jobs.title')"
    :aria-busy="isLoading"
  >
    <p
      v-if="!rows.length"
      class="px-1 py-8 text-center text-sm text-muted-foreground"
    >
      {{ t('jobs.empty') }}
    </p>
    <ul
      v-else
      class="space-y-2.5"
    >
      <li
        v-for="row in rows"
        :key="row.key"
        class="min-w-0 rounded-lg bg-secondary/60 px-3 py-2.5"
      >
        <div class="flex min-w-0 items-center gap-2.5">
          <img
            :src="row.iconSrc"
            alt=""
            width="18"
            height="18"
            class="size-[18px] shrink-0 rounded-sm"
          />
          <div class="min-w-0 flex-1">
            <div class="flex min-w-0 flex-wrap items-center gap-2">
              <span class="truncate text-sm font-medium">{{ row.name }}</span>
              <Badge
                variant="outline"
                class="font-normal"
              >
                {{ row.action }}
              </Badge>
              <span class="ml-auto shrink-0 text-xs tabular-nums text-muted-foreground">
                {{ row.elapsed }}
              </span>
            </div>
            <p class="mt-1 truncate text-xs text-muted-foreground">
              {{ row.progress }}
            </p>
          </div>
        </div>
        <div
          v-if="row.percent != null"
          class="mt-2 h-1 overflow-hidden rounded-full bg-muted"
          role="progressbar"
          :aria-valuenow="row.percent"
          aria-valuemin="0"
          aria-valuemax="100"
        >
          <div
            class="h-full rounded-full bg-primary/80"
            :style="{ width: `${row.percent}%` }"
          />
        </div>
      </li>
    </ul>
  </section>
</template>
