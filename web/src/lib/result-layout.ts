/** Shared row estimates for VirtualList + skeletons (must stay in sync). */

export const RESULT_LIST_GAP_MOBILE = 8
export const RESULT_LIST_GAP_DESKTOP = 4
/** Space between result cards — applied as row paddingBottom (included in measure). */
export const RESULT_CARD_GAP = 8

/**
 * Estimated card/list content height (px), excluding gap padding.
 * VirtualList adds `gap` on top for its estimateSize.
 * Keep in sync with mobile `min-height` on `article[data-layout]` in style.css —
 * estimate === min-height so first paint matches measure (no black voids / thrash).
 */
export const RESULT_ESTIMATE = {
  list: { sm: 80, mobile: 148 },
  card: { sm: 140, mobile: 156 },
} as const

export function resultEstimateSize(
  listView: boolean,
  isSmUp: boolean,
): number {
  if (listView) {
    return isSmUp ? RESULT_ESTIMATE.list.sm : RESULT_ESTIMATE.list.mobile
  }
  return isSmUp ? RESULT_ESTIMATE.card.sm : RESULT_ESTIMATE.card.mobile
}

export function resultGap(listView: boolean, isSmUp: boolean): number {
  if (listView) {
    return isSmUp ? RESULT_LIST_GAP_DESKTOP : RESULT_LIST_GAP_MOBILE
  }
  return RESULT_CARD_GAP
}

/** Custom event: FAB / shell asks the active VirtualList to remasure. */
export const JR_VIRTUAL_REMEASURE = 'jr:virtual-remeasure'
