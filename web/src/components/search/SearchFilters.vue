<script setup lang="ts">
import { useMediaQuery } from '@vueuse/core'
import {
  ArrowUp,
  CalendarPlus,
  Filter,
  Grid2x2,
  HardDrive,
  List,
  RefreshCw,
  RotateCcw,
} from '@lucide/vue'
import { useI18n } from 'vue-i18n'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  Collapsible,
  CollapsibleContent,
} from '@/components/ui/collapsible'
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from '@/components/ui/sheet'
import { Switch } from '@/components/ui/switch'
import { ToggleGroup, ToggleGroupItem } from '@/components/ui/toggle-group'
import { segmentItemSort, segmentItem, segmentTrack, segmentTrackSort } from '@/lib/segment-classes'
import {
  SORT_OPTIONS,
  type SearchFilters,
  type SortValue,
} from '@/lib/torrents'
import { cn } from '@/lib/utils'

const SORT_ICONS = {
  sid: ArrowUp,
  size: HardDrive,
  date: CalendarPlus,
  update: RefreshCw,
} as const

/** Field labels: tertiary tier (--jr-label), not ultra-faint muted */
const fieldLabel =
  'block space-y-1.5 text-xs font-medium text-[color:var(--jr-label)]'
/**
 * Controls sit on --secondary panel — must use --background + border
 * (bg-secondary here made solid-dark filters look like one flat slab).
 */
const fieldControl =
  'h-9 w-full rounded-[var(--radius-sm)] border border-border bg-background text-sm shadow-none ring-0 focus-visible:border-ring focus-visible:ring-2 focus-visible:ring-ring/40 dark:bg-background dark:hover:bg-muted/50'


defineProps<{
  open: boolean
  exact: boolean
  sort: SortValue
  listView: boolean
  filters: SearchFilters
  facets: {
    type: string[]
    tracker: string[]
    voice: string[]
    year: string[]
    quality: string[]
    season: string[]
  }
  activeCount: number
}>()
const emit = defineEmits<{
  'update:open': [boolean]
  'update:exact': [boolean]
  'update:sort': [SortValue]
  'update:listView': [boolean]
  serverFilter: [key: keyof SearchFilters, value: string]
  clientFilter: [key: 'refine' | 'exclude', value: string]
  reset: []
}>()

const { t } = useI18n()
const isMobile = useMediaQuery('(max-width: 639px)')

function onServer(key: keyof SearchFilters, value: string | undefined) {
  emit('serverFilter', key, value === '__all__' ? '' : (value ?? ''))
}

function selectModel(value: string) {
  return value || '__all__'
}

function setOpen(value: boolean) {
  emit('update:open', value)
}

/** Mobile sheet selects: solid popover so labels don’t bleed through glass. */
const mobileSelectContentClass =
  'z-[60] w-[var(--reka-select-trigger-width)] !bg-popover shadow-lg ![backdrop-filter:none] ![-webkit-backdrop-filter:none]'
</script>

<template>
  <div class="space-y-2.5">
    <!-- Don’t flex-1 the sort track — paints a dead grey strip on wide screens -->
    <div class="flex flex-col gap-2 lg:flex-row lg:items-center lg:gap-2.5">
      <div class="jr-sort-tabs min-w-0">
        <ToggleGroup
          type="single"
          :model-value="sort"
          size="sm"
          :spacing="0"
          :class="cn(segmentTrackSort, 'justify-stretch lg:justify-start')"
          :aria-label="t('search.sortMode')"
          @update:model-value="(v) => v && emit('update:sort', v as SortValue)"
        >
          <ToggleGroupItem
            v-for="opt in SORT_OPTIONS"
            :key="opt.value"
            :value="opt.value"
            :class="segmentItemSort"
          >
            <component
              :is="SORT_ICONS[opt.value]"
              class="size-3 shrink-0 lg:size-3.5"
              aria-hidden="true"
            />
            {{ t(opt.labelKey) }}
          </ToggleGroupItem>
        </ToggleGroup>
      </div>

      <div
        class="flex flex-wrap items-center gap-x-2 gap-y-2 lg:ml-auto lg:flex-nowrap lg:shrink-0"
      >
        <label
          for="exact-search"
          class="flex h-8 shrink-0 cursor-pointer items-center gap-2 rounded-full px-1 text-sm text-[color:var(--jr-label)]"
        >
          <Switch
            id="exact-search"
            :model-value="exact"
            @update:model-value="(v) => emit('update:exact', !!v)"
          />
          {{ t('search.filters.exact') }}
        </label>

        <div class="flex shrink-0 items-center gap-0.5">
          <Button
            type="button"
            variant="ghost"
            size="sm"
            class="h-8 gap-1.5 rounded-[10px] border-transparent px-2.5 text-[color:var(--jr-label)] shadow-none hover:text-foreground lg:px-3"
            :disabled="!activeCount"
            :aria-label="t('search.filters.reset')"
            @click="emit('reset')"
          >
            <RotateCcw class="size-3.5 shrink-0" />
            <span class="hidden lg:inline">{{ t('search.filters.reset') }}</span>
          </Button>

          <Button
            id="search-filters-trigger"
            type="button"
            variant="ghost"
            size="sm"
            :class="
              cn(
                'h-8 gap-1.5 rounded-[10px] border-transparent px-2.5 shadow-none lg:px-3',
                open
                  ? 'bg-secondary text-foreground hover:bg-secondary hover:text-foreground'
                  : 'text-muted-foreground hover:text-foreground',
              )
            "
            :aria-label="t('search.filters.filters')"
            :aria-expanded="open"
            aria-controls="search-filters-panel"
            @click="setOpen(!open)"
          >
            <Filter class="size-3.5" aria-hidden="true" />
            <span class="hidden lg:inline" aria-hidden="true">{{ t('search.filters.filters') }}</span>
            <Badge
              v-if="activeCount"
              variant="secondary"
              class="ml-0.5 size-5 justify-center rounded-full bg-background/70 p-0 text-[10px] text-foreground"
            >
              {{ activeCount }}
            </Badge>
          </Button>
        </div>

        <ToggleGroup
          type="single"
          :model-value="listView ? 'list' : 'cards'"
          size="sm"
          :spacing="1"
          :class="cn(segmentTrack, 'shrink-0')"
          :aria-label="t('search.viewMode')"
          @update:model-value="
            (v) => v && emit('update:listView', v === 'list')
          "
        >
          <ToggleGroupItem value="list" :class="segmentItem" :aria-label="t('search.list')">
            <List class="size-3.5" />
            <span class="hidden lg:inline">{{ t('search.list') }}</span>
          </ToggleGroupItem>
          <ToggleGroupItem value="cards" :class="segmentItem" :aria-label="t('search.cards')">
            <Grid2x2 class="size-3.5" />
            <span class="hidden lg:inline">{{ t('search.cards') }}</span>
          </ToggleGroupItem>
        </ToggleGroup>
      </div>
    </div>

    <!-- Mobile: Reka Sheet bottom drawer -->
    <Sheet
      v-if="isMobile"
      :open="open"
      @update:open="setOpen"
    >
      <SheetContent
        side="bottom"
        class="max-h-[85dvh] rounded-t-2xl p-0"
      >
        <SheetHeader
          class="jr-sheet-drag-zone shrink-0 space-y-0 border-b p-0 px-4 pt-1 pb-3 pr-12 text-left"
        >
          <SheetTitle>{{ t('search.filters.filters') }}</SheetTitle>
          <SheetDescription class="sr-only">
            {{ t('search.filters.panel') }}
          </SheetDescription>
        </SheetHeader>

        <div
          id="search-filters-panel"
          role="region"
          :aria-label="t('search.filters.panel')"
          class="min-h-0 flex-1 space-y-3 overflow-y-auto overscroll-contain px-4 py-3"
        >
          <label class="block space-y-1.5 text-xs text-[color:var(--jr-label)]">
            {{ t('search.filters.type') }}
            <Select
              :model-value="selectModel(filters.type)"
              @update:model-value="(v) => onServer('type', String(v))"
            >
              <SelectTrigger :class="fieldControl">
                <SelectValue :placeholder="t('search.filters.all')" />
              </SelectTrigger>
              <SelectContent
                position="popper"
                :class="mobileSelectContentClass"
              >
                <SelectItem value="__all__">{{ t('search.filters.all') }}</SelectItem>
                <SelectItem
                  v-for="v in facets.type"
                  :key="v"
                  :value="v"
                >
                  {{ v }}
                </SelectItem>
              </SelectContent>
            </Select>
          </label>

          <label class="block space-y-1.5 text-xs text-[color:var(--jr-label)]">
            {{ t('search.filters.tracker') }}
            <Select
              :model-value="selectModel(filters.tracker)"
              @update:model-value="(v) => onServer('tracker', String(v))"
            >
              <SelectTrigger :class="fieldControl">
                <SelectValue :placeholder="t('search.filters.all')" />
              </SelectTrigger>
              <SelectContent
                position="popper"
                :class="mobileSelectContentClass"
              >
                <SelectItem value="__all__">{{ t('search.filters.all') }}</SelectItem>
                <SelectItem
                  v-for="v in facets.tracker"
                  :key="v"
                  :value="v"
                >
                  {{ v }}
                </SelectItem>
              </SelectContent>
            </Select>
          </label>

          <label class="block space-y-1.5 text-xs text-[color:var(--jr-label)]">
            {{ t('search.filters.voice') }}
            <Select
              :model-value="selectModel(filters.voice)"
              @update:model-value="(v) => onServer('voice', String(v))"
            >
              <SelectTrigger :class="fieldControl">
                <SelectValue :placeholder="t('search.filters.all')" />
              </SelectTrigger>
              <SelectContent
                position="popper"
                :class="mobileSelectContentClass"
              >
                <SelectItem value="__all__">{{ t('search.filters.all') }}</SelectItem>
                <SelectItem
                  v-for="v in facets.voice"
                  :key="v"
                  :value="v"
                >
                  {{ v }}
                </SelectItem>
              </SelectContent>
            </Select>
          </label>

          <label class="block space-y-1.5 text-xs text-[color:var(--jr-label)]">
            {{ t('search.filters.video') }}
            <Select
              :model-value="selectModel(filters.videotype)"
              @update:model-value="(v) => onServer('videotype', String(v))"
            >
              <SelectTrigger :class="fieldControl">
                <SelectValue :placeholder="t('search.filters.all')" />
              </SelectTrigger>
              <SelectContent
                position="popper"
                :class="mobileSelectContentClass"
              >
                <SelectItem value="__all__">{{ t('search.filters.all') }}</SelectItem>
                <SelectItem value="sdr">SDR</SelectItem>
                <SelectItem value="hdr">HDR</SelectItem>
              </SelectContent>
            </Select>
          </label>

          <label class="block space-y-1.5 text-xs text-[color:var(--jr-label)]">
            {{ t('search.filters.year') }}
            <Select
              :model-value="selectModel(filters.year)"
              @update:model-value="(v) => onServer('year', String(v))"
            >
              <SelectTrigger :class="fieldControl">
                <SelectValue :placeholder="t('search.filters.all')" />
              </SelectTrigger>
              <SelectContent
                position="popper"
                :class="mobileSelectContentClass"
              >
                <SelectItem value="__all__">{{ t('search.filters.all') }}</SelectItem>
                <SelectItem
                  v-for="v in facets.year"
                  :key="v"
                  :value="v"
                >
                  {{ v }}
                </SelectItem>
              </SelectContent>
            </Select>
          </label>

          <label class="block space-y-1.5 text-xs text-[color:var(--jr-label)]">
            {{ t('search.filters.quality') }}
            <Select
              :model-value="selectModel(filters.quality)"
              @update:model-value="(v) => onServer('quality', String(v))"
            >
              <SelectTrigger :class="fieldControl">
                <SelectValue :placeholder="t('search.filters.all')" />
              </SelectTrigger>
              <SelectContent
                position="popper"
                :class="mobileSelectContentClass"
              >
                <SelectItem value="__all__">{{ t('search.filters.all') }}</SelectItem>
                <SelectItem
                  v-for="v in facets.quality"
                  :key="v"
                  :value="v"
                >
                  {{ v }}
                </SelectItem>
              </SelectContent>
            </Select>
          </label>

          <label class="block space-y-1.5 text-xs text-[color:var(--jr-label)]">
            {{ t('search.filters.season') }}
            <Select
              :model-value="selectModel(filters.season)"
              @update:model-value="(v) => onServer('season', String(v))"
            >
              <SelectTrigger :class="fieldControl">
                <SelectValue :placeholder="t('search.filters.all')" />
              </SelectTrigger>
              <SelectContent
                position="popper"
                :class="mobileSelectContentClass"
              >
                <SelectItem value="__all__">{{ t('search.filters.all') }}</SelectItem>
                <SelectItem
                  v-for="v in facets.season"
                  :key="v"
                  :value="v"
                >
                  {{ v }}
                </SelectItem>
              </SelectContent>
            </Select>
          </label>

          <label class="block space-y-1.5 text-xs text-[color:var(--jr-label)]">
            {{ t('search.filters.refine') }}
            <Input
              :model-value="filters.refine"
              :class="fieldControl"
              :placeholder="t('search.filters.refinePlaceholder')"
              @update:model-value="(v) => emit('clientFilter', 'refine', String(v))"
            />
          </label>

          <label class="block space-y-1.5 text-xs text-[color:var(--jr-label)]">
            {{ t('search.filters.exclude') }}
            <Input
              :model-value="filters.exclude"
              :class="fieldControl"
              :placeholder="t('search.filters.excludePlaceholder')"
              @update:model-value="(v) => emit('clientFilter', 'exclude', String(v))"
            />
          </label>
        </div>

        <div class="shrink-0 border-t px-4 pt-3 pb-3">
          <Button
            type="button"
            variant="ghost"
            size="sm"
            class="gap-1.5"
            :disabled="!activeCount"
            @click="emit('reset')"
          >
            <RotateCcw class="size-3.5" />
            {{ t('search.filters.reset') }}
          </Button>
        </div>
      </SheetContent>
    </Sheet>

    <!-- Desktop filters panel -->
    <Collapsible
      v-else
      :open="open"
      @update:open="setOpen"
    >
      <CollapsibleContent>
        <div
          id="search-filters-panel"
          role="region"
          :aria-label="t('search.filters.panel')"
          class="jr-filters-panel space-y-3.5"
        >
          <div class="jr-filters-facets">
            <label :class="fieldLabel">
              {{ t('search.filters.type') }}
              <Select
                :model-value="selectModel(filters.type)"
                @update:model-value="(v) => onServer('type', String(v))"
              >
                <SelectTrigger :class="fieldControl">
                  <SelectValue :placeholder="t('search.filters.all')" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="__all__">{{ t('search.filters.all') }}</SelectItem>
                  <SelectItem v-for="v in facets.type" :key="v" :value="v">{{ v }}</SelectItem>
                </SelectContent>
              </Select>
            </label>

            <label :class="fieldLabel">
              {{ t('search.filters.tracker') }}
              <Select
                :model-value="selectModel(filters.tracker)"
                @update:model-value="(v) => onServer('tracker', String(v))"
              >
                <SelectTrigger :class="fieldControl">
                  <SelectValue :placeholder="t('search.filters.all')" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="__all__">{{ t('search.filters.all') }}</SelectItem>
                  <SelectItem v-for="v in facets.tracker" :key="v" :value="v">{{ v }}</SelectItem>
                </SelectContent>
              </Select>
            </label>

            <label :class="fieldLabel">
              {{ t('search.filters.voice') }}
              <Select
                :model-value="selectModel(filters.voice)"
                @update:model-value="(v) => onServer('voice', String(v))"
              >
                <SelectTrigger :class="fieldControl">
                  <SelectValue :placeholder="t('search.filters.all')" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="__all__">{{ t('search.filters.all') }}</SelectItem>
                  <SelectItem v-for="v in facets.voice" :key="v" :value="v">{{ v }}</SelectItem>
                </SelectContent>
              </Select>
            </label>

            <label :class="fieldLabel">
              {{ t('search.filters.video') }}
              <Select
                :model-value="selectModel(filters.videotype)"
                @update:model-value="(v) => onServer('videotype', String(v))"
              >
                <SelectTrigger :class="fieldControl">
                  <SelectValue :placeholder="t('search.filters.all')" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="__all__">{{ t('search.filters.all') }}</SelectItem>
                  <SelectItem value="sdr">SDR</SelectItem>
                  <SelectItem value="hdr">HDR</SelectItem>
                </SelectContent>
              </Select>
            </label>

            <label :class="fieldLabel">
              {{ t('search.filters.year') }}
              <Select
                :model-value="selectModel(filters.year)"
                @update:model-value="(v) => onServer('year', String(v))"
              >
                <SelectTrigger :class="fieldControl">
                  <SelectValue :placeholder="t('search.filters.all')" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="__all__">{{ t('search.filters.all') }}</SelectItem>
                  <SelectItem v-for="v in facets.year" :key="v" :value="v">{{ v }}</SelectItem>
                </SelectContent>
              </Select>
            </label>

            <label :class="fieldLabel">
              {{ t('search.filters.quality') }}
              <Select
                :model-value="selectModel(filters.quality)"
                @update:model-value="(v) => onServer('quality', String(v))"
              >
                <SelectTrigger :class="fieldControl">
                  <SelectValue :placeholder="t('search.filters.all')" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="__all__">{{ t('search.filters.all') }}</SelectItem>
                  <SelectItem v-for="v in facets.quality" :key="v" :value="v">{{ v }}</SelectItem>
                </SelectContent>
              </Select>
            </label>

            <label :class="fieldLabel">
              {{ t('search.filters.season') }}
              <Select
                :model-value="selectModel(filters.season)"
                @update:model-value="(v) => onServer('season', String(v))"
              >
                <SelectTrigger :class="fieldControl">
                  <SelectValue :placeholder="t('search.filters.all')" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="__all__">{{ t('search.filters.all') }}</SelectItem>
                  <SelectItem v-for="v in facets.season" :key="v" :value="v">{{ v }}</SelectItem>
                </SelectContent>
              </Select>
            </label>
          </div>

          <div class="grid gap-x-3 gap-y-3 sm:grid-cols-2">
            <label :class="fieldLabel">
              {{ t('search.filters.refine') }}
              <Input
                :model-value="filters.refine"
                :class="fieldControl"
                :placeholder="t('search.filters.refinePlaceholder')"
                @update:model-value="(v) => emit('clientFilter', 'refine', String(v))"
              />
            </label>
            <label :class="fieldLabel">
              {{ t('search.filters.exclude') }}
              <Input
                :model-value="filters.exclude"
                :class="fieldControl"
                :placeholder="t('search.filters.excludePlaceholder')"
                @update:model-value="(v) => emit('clientFilter', 'exclude', String(v))"
              />
            </label>
          </div>
        </div>
      </CollapsibleContent>
    </Collapsible>
  </div>
</template>
