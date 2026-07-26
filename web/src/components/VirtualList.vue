<script setup lang="ts" generic="T">
import { useWindowVirtualizer } from '@tanstack/vue-virtual'
import { useEventListener } from '@vueuse/core'
import type { ComponentPublicInstance } from 'vue'
import {
  computed,
  nextTick,
  onActivated,
  onBeforeUnmount,
  onMounted,
  ref,
  toRef,
  watch,
} from 'vue'
import {
  JR_VIRTUAL_REMEASURE,
  RESULT_CARD_GAP,
  RESULT_ESTIMATE,
} from '@/lib/result-layout'

const props = withDefaults(
  defineProps<{
    items: T[]
    estimateSize?: number
    overscan?: number
    gap?: number
    getItemKey?: (index: number, item: T) => string | number
  }>(),
  {
    estimateSize: RESULT_ESTIMATE.card.mobile,
    overscan: 8,
    gap: RESULT_CARD_GAP,
  },
)

const listRef = ref<HTMLElement | null>(null)
const itemsRef = toRef(props, 'items')

/**
 * Document Y of the list root — must stay stable during scroll.
 * Never recompute from getBoundingClientRect + scrollY (iOS sticky/URL bar).
 */
const scrollMargin = ref(0)
/**
 * Sticky header+dock overlay height (viewport). scrollToIndex / first-visible
 * use this so rows align under the dock, not under the viewport top.
 */
const scrollPaddingStart = ref(0)
let chromeResizeObserver: ResizeObserver | null = null

function documentOffsetTop(el: HTMLElement | null): number {
  if (!el || typeof window === 'undefined') return 0
  let top = 0
  let node: HTMLElement | null = el
  while (node) {
    top += node.offsetTop
    const parent: Element | null = node.offsetParent
    node = parent instanceof HTMLElement ? parent : null
  }
  return Math.max(0, top)
}

/** Visible bottom of sticky search chrome in viewport coords. */
function measureStickyPadding(): number {
  if (typeof window === 'undefined') return 0
  const dock = document.querySelector('.jr-search-dock')
  if (!(dock instanceof HTMLElement)) return 0
  const bottom = dock.getBoundingClientRect().bottom
  return Math.max(0, Math.min(Math.round(bottom), window.innerHeight))
}

/** Update scrollMargin; returns delta when it changed. */
function refreshScrollMargin(): number {
  const next = documentOffsetTop(listRef.value)
  const prev = scrollMargin.value
  if (next === prev) return 0
  scrollMargin.value = next
  return next - prev
}

function refreshScrollPadding() {
  const next = measureStickyPadding()
  if (next === scrollPaddingStart.value) return false
  scrollPaddingStart.value = next
  return true
}

/**
 * Refresh margin + sticky padding without wiping the size cache.
 * Optionally compensate scrollY when list offsetTop changes (filters open).
 * Never scrollTo mid-fling — queue until scroll settles (iOS touch).
 */
let pendingScrollCompensate = 0
let touchSettleTimer: ReturnType<typeof setTimeout> | null = null

function applyScrollCompensate(delta: number) {
  if (delta === 0 || typeof window === 'undefined') return
  const y =
    window.scrollY ||
    document.documentElement.scrollTop ||
    document.body.scrollTop ||
    0
  if (y > 0) {
    window.scrollTo(0, y + delta)
  }
}

function flushPendingScrollCompensate() {
  if (pendingScrollCompensate !== 0) {
    const delta = pendingScrollCompensate
    pendingScrollCompensate = 0
    applyScrollCompensate(delta)
  }
  // Apply real row heights deferred during fling (RO measured but size was locked).
  if (!virtualizer.value.isScrolling) {
    virtualizer.value.measure()
  }
}

function syncScrollMargin(forceMeasure = false, compensateScroll = true) {
  const delta = refreshScrollMargin()
  refreshScrollPadding()
  if (compensateScroll && delta !== 0 && typeof window !== 'undefined') {
    if (virtualizer.value.isScrolling) {
      pendingScrollCompensate += delta
    } else {
      applyScrollCompensate(delta)
    }
  }
  if (forceMeasure) {
    virtualizer.value.measure()
  }
}

/**
 * Gap is padding on the row (not virtualizer.gap) so measured height always
 * includes spacing — prevents adjacent translateY rows from overlapping.
 * offsetHeight (not RO borderBox) is stable on iOS transformed rows.
 *
 * Critical: TanStack's ResizeObserver still calls options.measureElement while
 * isScrolling (only the ref-path skips). Returning a locked size keeps delta=0
 * so translateY does not thrash under the finger.
 */
const virtualizer = useWindowVirtualizer(
  computed(() => ({
    count: itemsRef.value.length,
    // estimate must cover card + gap padding
    estimateSize: () => props.estimateSize + props.gap,
    overscan: props.overscan,
    gap: 0,
    scrollMargin: scrollMargin.value,
    scrollPaddingStart: scrollPaddingStart.value,
    measureElement: (
      el: Element,
      _entry: ResizeObserverEntry | undefined,
      instance: { isScrolling: boolean },
    ) => {
      const node = el as HTMLElement
      const fallback = props.estimateSize + props.gap
      const raw = node.offsetHeight
      const measured = raw > 0 ? Math.round(raw) : fallback

      if (instance.isScrolling) {
        const locked = Number(node.dataset.jrRowSize)
        if (locked > 0) return locked
        // First paint mid-fling: keep estimate until scroll settles.
        node.dataset.jrPending = '1'
        return fallback
      }

      node.dataset.jrRowSize = String(measured)
      delete node.dataset.jrPending
      return measured
    },
    getItemKey: (index: number) => {
      const item = itemsRef.value[index]
      if (item !== undefined && props.getItemKey) {
        return props.getItemKey(index, item)
      }
      return index
    },
  })),
)

const virtualItems = computed(() => virtualizer.value.getVirtualItems())
const totalSize = computed(() => virtualizer.value.getTotalSize())
const activeScrollMargin = computed(
  () => virtualizer.value.options.scrollMargin ?? 0,
)

function measureRow(el: Element | ComponentPublicInstance | null) {
  const node =
    el instanceof HTMLElement
      ? el
      : el && '$el' in el && el.$el instanceof HTMLElement
        ? el.$el
        : null
  if (!node || !node.isConnected) return
  // Uses virtualizer measureElement (offsetHeight) — never return 0 ourselves.
  virtualizer.value.measureElement(node)
}

/** Margin sync only — keeps measured heights (FAB / fonts / KeepAlive). */
function refreshMarginAfterPaint() {
  void nextTick(() => {
    requestAnimationFrame(() => {
      refreshScrollMargin()
      refreshScrollPadding()
    })
  })
}

/** Full cache remasure — only for layout mode / viewport geometry changes. */
function remasureAfterPaint() {
  void nextTick(() => {
    requestAnimationFrame(() => {
      refreshScrollMargin()
      refreshScrollPadding()
      virtualizer.value.measure()
    })
  })
}

/**
 * First row visible below sticky chrome (not overscan-only / not under dock).
 */
function getFirstVisibleIndex() {
  const offset = virtualizer.value.scrollOffset ?? 0
  const pad = scrollPaddingStart.value
  const fold = offset + pad
  const items = virtualizer.value.getVirtualItems()
  for (const item of items) {
    if (item.end > fold) return item.index
  }
  return items[0]?.index ?? 0
}

function scrollToIndex(
  index: number,
  align: 'start' | 'center' | 'end' | 'auto' = 'start',
) {
  const max = Math.max(0, itemsRef.value.length - 1)
  const clamped = Math.min(Math.max(0, index), max)
  // Fresh sticky metrics so align:start lands under the dock, not under the nav.
  refreshScrollPadding()
  virtualizer.value.scrollToIndex(clamped, { align })
}

function scrollToStart() {
  window.scrollTo({ top: 0, left: 0, behavior: 'auto' })
  document.documentElement.scrollTop = 0
  document.body.scrollTop = 0
}

function observeChrome() {
  if (typeof ResizeObserver === 'undefined') return
  chromeResizeObserver?.disconnect()
  chromeResizeObserver = new ResizeObserver(() => {
    // Dock/header height only — update margin + compensate scroll, no cache wipe.
    syncScrollMargin(false)
  })
  const header = document.querySelector('header.jr-glass-nav')
  const dock = document.querySelector('.jr-search-dock')
  const filters = document.querySelector('.jr-filters-panel')
  if (header) chromeResizeObserver.observe(header)
  if (dock) chromeResizeObserver.observe(dock)
  if (filters) chromeResizeObserver.observe(filters)
}

onMounted(() => {
  refreshScrollMargin()
  refreshScrollPadding()
  observeChrome()
  void document.fonts?.ready?.then(() => {
    refreshMarginAfterPaint()
  })
})

onBeforeUnmount(() => {
  chromeResizeObserver?.disconnect()
  chromeResizeObserver = null
  if (touchSettleTimer) {
    clearTimeout(touchSettleTimer)
    touchSettleTimer = null
  }
  pendingScrollCompensate = 0
})

useEventListener(
  window,
  'resize',
  () => {
    // Width change can reflow card wrap — remasure once.
    void nextTick(() => syncScrollMargin(true))
  },
  { passive: true },
)

useEventListener(
  window,
  'orientationchange',
  () => {
    void nextTick(() => syncScrollMargin(true))
  },
  { passive: true },
)

// Flush chrome scroll compensation deferred during touch/fling.
useEventListener(window, 'scrollend', flushPendingScrollCompensate, {
  passive: true,
})
// iOS Safari may omit scrollend after touch; settle shortly after touch ends.
useEventListener(
  window,
  'touchend',
  () => {
    if (touchSettleTimer) clearTimeout(touchSettleTimer)
    touchSettleTimer = setTimeout(() => {
      touchSettleTimer = null
      flushPendingScrollCompensate()
    }, 120)
  },
  { passive: true },
)

useEventListener(window, JR_VIRTUAL_REMEASURE, () => {
  // FAB: margin only — do not wipe size cache after scroll-to-top.
  refreshMarginAfterPaint()
})

onActivated(() => {
  void nextTick(() => {
    refreshScrollMargin()
    refreshScrollPadding()
    observeChrome()
  })
})

// Layout mode / gap change only — identity changes use getItemKey, not measure().
watch(
  () => [props.estimateSize, props.gap] as const,
  () => {
    remasureAfterPaint()
  },
)

defineExpose({
  listRef,
  virtualizer,
  syncScrollMargin,
  getFirstVisibleIndex,
  scrollToIndex,
  scrollToStart,
  observeChrome,
})
</script>

<template>
  <div
    ref="listRef"
    data-virtual-list
    class="relative z-0 w-full"
    style="overflow-anchor: none"
  >
    <div
      role="list"
      class="relative w-full"
      :style="{ height: `${totalSize}px` }"
    >
      <div
        v-for="row in virtualItems"
        :key="String(row.key)"
        :ref="measureRow"
        :data-index="row.index"
        class="absolute top-0 left-0 z-0 box-border w-full"
        :style="{
          paddingBottom: gap > 0 ? `${gap}px` : undefined,
          transform: `translateY(${row.start - activeScrollMargin}px)`,
        }"
      >
        <slot
          :item="items[row.index]!"
          :index="row.index"
        />
      </div>
    </div>
    <slot name="footer" />
  </div>
</template>
