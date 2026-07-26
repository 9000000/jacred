<script setup lang="ts">
import { useDebounceFn, useMediaQuery, useOnline, until } from '@vueuse/core'
import { computed, nextTick, onBeforeUnmount, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { Loader2, Search, WifiOff, X } from '@lucide/vue'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import SearchFilters from '@/components/search/SearchFilters.vue'
import TorrentCard from '@/components/search/TorrentCard.vue'
import TorrentResultSkeleton from '@/components/search/TorrentResultSkeleton.vue'
import { useTorrents } from '@/composables/useTorrents'
import { useShellTools } from '@/composables/useShellTools'
import {
  clearRecentSearches,
  getRecentSearches,
} from '@/lib/recent-searches'
import { resultGap } from '@/lib/result-layout'
import {
  torrentKey,
  type SearchFilters as SearchFilterState,
  type SortValue,
} from '@/lib/torrents'

defineOptions({ name: 'SearchPage' })

const { t } = useI18n()
const { openTorrServer } = useShellTools()
const {
  query,
  sort,
  exact,
  listView,
  filtersOpen,
  filters,
  facets,
  visibleItems,
  isLoading,
  isFetching,
  errorMessage,
  currentQuery,
  activeFilterCount,
  resultsHeader,
  search,
  retrySearch,
  prefetchRecent,
  setSort,
  setExact,
  toggleListView,
  setFiltersOpen,
  updateServerFilter,
  updateClientFilter,
  resetFilters,
  toggleTrackerFilter,
  clearSearch,
} = useTorrents()

const listRef = ref<HTMLElement | null>(null)
const recent = ref(getRecentSearches())
const isSmUp = useMediaQuery('(min-width: 640px)')
const isOnline = useOnline()

const listGap = computed(() => resultGap(true, isSmUp.value))
const cardGap = computed(() => resultGap(false, isSmUp.value))
const resultsGap = computed(() =>
  listView.value ? listGap.value : cardGap.value,
)

const hasResults = computed(
  () => !!currentQuery.value && visibleItems.value.length > 0,
)
/** Spinner / «Поиск…» only on first load — never on sort/filter refetch. */
const showSearchBusy = computed(
  () => isLoading.value && !hasResults.value,
)
const showRefetchCue = computed(
  () => isFetching.value && hasResults.value && !isLoading.value,
)
const showEmptyHint = computed(
  () => !currentQuery.value && !visibleItems.value.length && !isLoading.value,
)
const showNothingFound = computed(
  () =>
    !!currentQuery.value &&
    !visibleItems.value.length &&
    !isLoading.value &&
    !errorMessage.value,
)

let settleToken = 0
let viewAnchorToken = 0

/** Pin viewport to document top so results start under the search dock. */
function pinResultsStart() {
  window.scrollTo(0, 0)
  document.documentElement.scrollTop = 0
  document.body.scrollTop = 0
}

function dockBottom(): number {
  const dock = document.querySelector('.jr-search-dock')
  if (!(dock instanceof HTMLElement)) return 0
  return Math.max(0, dock.getBoundingClientRect().bottom)
}

/** Index of first result card below the sticky dock. */
function getFirstVisibleIndex(): number {
  const root = listRef.value
  if (!root) return 0
  const cards = root.querySelectorAll('[data-result-card]')
  const fold = dockBottom()
  for (let i = 0; i < cards.length; i++) {
    const el = cards[i]
    if (el && el.getBoundingClientRect().bottom > fold) return i
  }
  return 0
}

/** Place card `index` just under the sticky dock. */
function scrollToResultIndex(index: number) {
  const root = listRef.value
  if (!root) return
  const cards = root.querySelectorAll('[data-result-card]')
  const el = cards[Math.min(Math.max(0, index), cards.length - 1)]
  if (!(el instanceof HTMLElement)) return
  const top = el.getBoundingClientRect().top + window.scrollY
  window.scrollTo(0, Math.max(0, top - dockBottom()))
}

async function settleListLayout() {
  const token = ++settleToken
  pinResultsStart()
  await nextTick()
  if (token !== settleToken) return
  await new Promise<void>((resolve) => {
    requestAnimationFrame(() => resolve())
  })
}

/** Wait for the in-flight torrents fetch so results exist before pinning. */
async function waitForSearchPaint() {
  await nextTick()
  await new Promise<void>((resolve) => {
    requestAnimationFrame(() => resolve())
  })
  if (isLoading.value || isFetching.value) {
    await until(() => !isLoading.value && !isFetching.value).toBe(true)
  }
  await settleListLayout()
}

function onSubmit(e: Event) {
  e.preventDefault()
  if (!isOnline.value) return
  // Blur submit so the browser does not scroll the focused control into view.
  if (document.activeElement instanceof HTMLElement) {
    document.activeElement.blur()
  }
  pinResultsStart()
  void search().then(async () => {
    recent.value = getRecentSearches()
    await waitForSearchPaint()
  })
}

function applyRecent(q: string) {
  if (!isOnline.value) return
  query.value = q
  if (document.activeElement instanceof HTMLElement) {
    document.activeElement.blur()
  }
  pinResultsStart()
  void search().then(async () => {
    recent.value = getRecentSearches()
    await waitForSearchPaint()
  })
}

function onClearRecent() {
  clearRecentSearches()
  recent.value = []
}

function onRetry() {
  pinResultsStart()
  retrySearch()
  void waitForSearchPaint()
}

/** Server-driven filter/sort: pin top, refetch, settle (button stays idle via scoped placeholder). */
function runServerFilterSearch(apply: () => void) {
  pinResultsStart()
  apply()
  if (query.value.trim()) {
    void waitForSearchPaint()
  }
}

function onSortUpdate(value: SortValue) {
  runServerFilterSearch(() => setSort(value))
}

function onExactUpdate(value: boolean) {
  runServerFilterSearch(() => setExact(value))
}

function onServerFilter(
  key: keyof SearchFilterState,
  value: string,
) {
  runServerFilterSearch(() => updateServerFilter(key, value))
}

function onResetFilters() {
  runServerFilterSearch(() => resetFilters())
}

function onToggleTrackerFilter(tracker: string) {
  runServerFilterSearch(() => toggleTrackerFilter(tracker))
}

const pinClientFilter = useDebounceFn(() => {
  pinResultsStart()
}, 200)

function onClientFilter(key: 'refine' | 'exclude', value: string) {
  updateClientFilter(key, value)
  pinClientFilter()
}

/** Keep the same result under the sticky dock when list ↔ cards heights change. */
async function onListViewUpdate(next: boolean) {
  if (next === listView.value) return
  const token = ++viewAnchorToken
  const anchorIndex = getFirstVisibleIndex()
  toggleListView()
  await nextTick()
  await nextTick()
  if (token !== viewAnchorToken) return
  await new Promise<void>((resolve) => {
    requestAnimationFrame(() => resolve())
  })
  if (token !== viewAnchorToken) return
  scrollToResultIndex(anchorIndex)
  await new Promise<void>((resolve) => {
    requestAnimationFrame(() => resolve())
  })
  if (token !== viewAnchorToken) return
  const drifted = getFirstVisibleIndex()
  if (Math.abs(drifted - anchorIndex) > 1) {
    scrollToResultIndex(anchorIndex)
  }
}

onBeforeUnmount(() => {
  settleToken += 1
  viewAnchorToken += 1
})
</script>

<template>
  <section class="flex flex-col gap-4">
    <header class="space-y-1 text-center">
      <h1 class="text-2xl font-semibold tracking-tight text-balance">
        {{ t('search.title') }}
      </h1>
      <p class="mx-auto max-w-2xl text-sm text-pretty text-muted-foreground">
        {{ t('search.subtitle') }}
      </p>
    </header>

    <div
      v-if="!isOnline"
      class="flex items-center gap-2 rounded-lg border border-destructive/30 bg-destructive/10 px-3 py-2 text-sm text-destructive"
      role="status"
    >
      <WifiOff class="size-4 shrink-0" aria-hidden="true" />
      {{ t('search.offline') }}
    </div>

    <!-- Same chrome before and after search — sticky without a sudden “card” skin -->
    <div
      class="jr-sticky-dock jr-search-dock sticky flex flex-col gap-2 py-2 sm:gap-2.5 sm:py-2.5"
      style="top: var(--jr-header-offset)"
    >
      <form
        class="flex flex-col gap-2 sm:flex-row sm:items-stretch"
        @submit="onSubmit"
      >
        <div class="relative min-w-0 flex-1">
          <Search
            class="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-muted-foreground"
            aria-hidden="true"
          />
          <Input
            id="search-input"
            v-model="query"
            type="search"
            name="s"
            autocomplete="off"
            enterkeyhint="search"
            class="h-11 rounded-[12px] border-0 bg-secondary pr-10 pl-9 shadow-none focus-visible:ring-2 focus-visible:ring-ring/40 dark:bg-secondary"
            :placeholder="t('search.placeholder')"
            :aria-label="t('search.queryAria')"
          />
          <Button
            v-if="query"
            type="button"
            variant="ghost"
            size="icon"
            class="absolute top-1/2 right-1 size-8 -translate-y-1/2 rounded-[10px]"
            :aria-label="t('search.clear')"
            @click="clearSearch"
          >
            <X class="size-4" />
          </Button>
        </div>
        <Button
          type="submit"
          class="h-11 min-w-[7.5rem] shrink-0 gap-2 rounded-[12px] px-5"
          :disabled="showSearchBusy || !isOnline"
          :aria-busy="showSearchBusy"
        >
          <Loader2 v-if="showSearchBusy" class="size-4 animate-spin" />
          {{ showSearchBusy ? t('search.searching') : t('search.submit') }}
        </Button>
      </form>

      <div
        v-if="recent.length && !currentQuery"
        class="flex flex-wrap items-center gap-2"
      >
        <span class="text-xs text-muted-foreground">{{ t('search.recent') }}</span>
        <Button
          v-for="item in recent"
          :key="item"
          type="button"
          variant="secondary"
          size="sm"
          class="jr-recent-chip relative max-w-[14rem] min-h-9 truncate px-2.5 text-xs font-normal"
          :disabled="!isOnline"
          @mouseenter="isOnline && prefetchRecent(item)"
          @focus="isOnline && prefetchRecent(item)"
          @click="applyRecent(item)"
        >
          {{ item }}
        </Button>
        <Button
          type="button"
          variant="ghost"
          size="sm"
          class="jr-recent-chip relative min-h-9 px-2 text-xs text-muted-foreground"
          @click="onClearRecent"
        >
          {{ t('search.clearRecent') }}
        </Button>
      </div>

      <SearchFilters
        :open="filtersOpen"
        :exact="exact"
        :sort="sort"
        :list-view="listView"
        :filters="filters"
        :facets="facets"
        :active-count="activeFilterCount"
        @update:open="setFiltersOpen"
        @update:exact="onExactUpdate"
        @update:sort="onSortUpdate"
        @update:list-view="onListViewUpdate"
        @server-filter="onServerFilter"
        @client-filter="onClientFilter"
        @reset="onResetFilters"
      />
    </div>

    <div
      v-if="errorMessage"
      class="flex flex-wrap items-center gap-2 rounded-lg border border-destructive/30 bg-destructive/10 px-3 py-2 text-sm text-destructive"
      role="alert"
    >
      <span class="min-w-0 flex-1">{{ errorMessage }}</span>
      <Button
        type="button"
        variant="outline"
        size="sm"
        class="h-8 shrink-0"
        :disabled="!isOnline || isFetching"
        @click="onRetry"
      >
        {{ t('search.retry') }}
      </Button>
    </div>

    <div
      v-if="showSearchBusy"
      class="flex flex-col"
      :style="{ gap: `${resultsGap}px` }"
      aria-busy="true"
      :aria-label="t('search.loadingResults')"
    >
      <TorrentResultSkeleton
        v-for="i in 6"
        :key="i"
        :list-view="listView"
        :is-sm-up="isSmUp"
      />
    </div>

    <template v-else>
      <p
        v-if="resultsHeader || showRefetchCue"
        class="flex items-center gap-2 text-sm text-muted-foreground"
        aria-live="polite"
      >
        <Loader2
          v-if="showRefetchCue"
          class="size-3.5 shrink-0 animate-spin"
          aria-hidden="true"
        />
        <span :class="showRefetchCue ? 'opacity-70' : undefined">
          {{ showRefetchCue && !resultsHeader ? t('search.loadingMore') : resultsHeader }}
        </span>
      </p>

      <div
        v-if="showEmptyHint"
        class="jr-glass-panel rounded-xl border border-dashed px-4 py-12 text-center text-muted-foreground"
      >
        {{ t('search.emptyHint') }}
      </div>

      <div
        v-else-if="showNothingFound"
        class="jr-glass-panel rounded-xl border border-dashed px-4 py-12 text-center text-muted-foreground"
      >
        {{ t('search.nothingFound') }}
      </div>

      <div
        v-else-if="hasResults"
        ref="listRef"
        class="jr-results-list flex flex-col"
        role="list"
        :style="{ gap: `${resultsGap}px` }"
        :aria-busy="isFetching"
      >
        <TorrentCard
          v-for="(item, index) in visibleItems"
          :key="torrentKey(item)"
          :item="item"
          :list-view="listView"
          :position="index + 1"
          :set-size="visibleItems.length"
          :active-tracker="filters.tracker"
          @filter-tracker="onToggleTrackerFilter"
          @open-torr-server="openTorrServer"
        />
      </div>
    </template>
  </section>
</template>
