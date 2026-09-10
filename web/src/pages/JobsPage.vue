<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import { Loader2, RefreshCw } from '@lucide/vue'
import { Button } from '@/components/ui/button'
import BackgroundJobsCard from '@/components/stats/BackgroundJobsCard.vue'
import { useBackgroundJobs } from '@/composables/useBackgroundJobs'

const { t } = useI18n()
const { jobs, isFetching, isError, refetch } = useBackgroundJobs()

function load() {
  void refetch()
}
</script>

<template>
  <section class="space-y-4">
    <div class="flex flex-wrap items-start justify-between gap-3">
      <div class="space-y-1">
        <h1 class="text-2xl font-semibold tracking-tight">
          {{ t('jobs.title') }}
        </h1>
        <p class="text-sm text-muted-foreground">
          {{ t('jobs.subtitle') }}
        </p>
      </div>
      <Button
        type="button"
        variant="outline"
        size="sm"
        class="h-9 gap-1.5"
        :disabled="isFetching"
        :aria-busy="isFetching"
        @click="load"
      >
        <Loader2 v-if="isFetching" class="size-3.5 animate-spin" />
        <RefreshCw v-else class="size-3.5" />
        {{ t('jobs.refresh') }}
      </Button>
    </div>

    <p
      v-if="isError"
      class="rounded-lg border border-destructive/30 bg-destructive/10 px-3 py-2 text-sm text-destructive"
      role="alert"
    >
      {{ t('jobs.loadFailed') }}
    </p>

    <BackgroundJobsCard
      :jobs="jobs"
      :is-loading="isFetching"
    />
  </section>
</template>
