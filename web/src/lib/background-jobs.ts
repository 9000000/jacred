import type { components } from '@/lib/api/types'

export type BackgroundJob = components['schemas']['BackgroundJob']
export type BackgroundJobsResponse = components['schemas']['BackgroundJobsResponse']

/** Pull a jobs array out of `/health/background-jobs` (or a malformed payload). */
export function normalizeBackgroundJobs(data: unknown): BackgroundJob[] {
  if (!data || typeof data !== 'object') return []
  const jobs = (data as { jobs?: unknown }).jobs
  if (!Array.isArray(jobs)) return []
  return jobs.filter((job): job is BackgroundJob => !!job && typeof job === 'object')
}

/** Compact elapsed label: `42s`, `15m`, `2h 5m`. */
export function formatJobElapsed(
  seconds: number | null | undefined,
  locale = 'en',
): string {
  const n = Number(seconds)
  if (!Number.isFinite(n) || n < 0) return '—'
  const sec = Math.floor(n)
  const ru = locale.toLowerCase().startsWith('ru')
  if (sec < 60) return ru ? `${sec} с` : `${sec}s`
  const minutes = Math.floor(sec / 60)
  if (minutes < 60) return ru ? `${minutes} мин` : `${minutes}m`
  const hours = Math.floor(minutes / 60)
  const rem = minutes % 60
  if (ru) return rem ? `${hours} ч ${rem} мин` : `${hours} ч`
  return rem ? `${hours}h ${rem}m` : `${hours}h`
}

export function jobProgressText(job: BackgroundJob): string {
  const summary = String(job.summary || '').trim()
  if (summary) return summary
  if (typeof job.percent === 'number' && Number.isFinite(job.percent)) {
    return `${Math.round(job.percent)}%`
  }
  return 'running'
}
