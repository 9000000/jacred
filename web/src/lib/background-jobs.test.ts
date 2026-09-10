import { describe, expect, it } from 'vitest'
import {
  formatJobElapsed,
  jobProgressText,
  normalizeBackgroundJobs,
} from '@/lib/background-jobs'

describe('normalizeBackgroundJobs', () => {
  it('returns an empty list for missing or invalid payloads', () => {
    expect(normalizeBackgroundJobs(undefined)).toEqual([])
    expect(normalizeBackgroundJobs({ status: 'OK' })).toEqual([])
    expect(normalizeBackgroundJobs({ jobs: 'nope' })).toEqual([])
  })

  it('keeps object jobs and drops junk', () => {
    expect(
      normalizeBackgroundJobs({
        jobs: [{ id: 'rutor:ParseAllTask', tracker: 'rutor' }, null, 3],
      }),
    ).toEqual([{ id: 'rutor:ParseAllTask', tracker: 'rutor' }])
  })
})

describe('formatJobElapsed', () => {
  it('formats seconds, minutes, and hours', () => {
    expect(formatJobElapsed(42, 'en')).toBe('42s')
    expect(formatJobElapsed(42, 'ru')).toBe('42 с')
    expect(formatJobElapsed(900, 'en')).toBe('15m')
    expect(formatJobElapsed(900, 'ru')).toBe('15 мин')
    expect(formatJobElapsed(7500, 'en')).toBe('2h 5m')
    expect(formatJobElapsed(7200, 'ru')).toBe('2 ч')
    expect(formatJobElapsed(undefined)).toBe('—')
  })
})

describe('jobProgressText', () => {
  it('prefers summary, then percent, then running', () => {
    expect(jobProgressText({ summary: '6/154 pages · category 32 · page 5' })).toBe(
      '6/154 pages · category 32 · page 5',
    )
    expect(jobProgressText({ percent: 4 })).toBe('4%')
    expect(jobProgressText({})).toBe('running')
  })
})
