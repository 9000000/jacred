# Rutracker tracker

JacRed sync for [rutracker.org](https://rutracker.org) via cron endpoints under `/cron/rutracker/`.

Cloudflare often blocks direct clients (`403` / “Just a moment…”). Use a Worker reverse-proxy **alias** so fetches go through CF edge:

```yaml
Rutracker:
  alias: https://rutracker.workers.dev
```

- **HTTP** (lists, topics): `rqHost()` → alias when set  
- **FDB `url`**: always canonical `https://rutracker.org/forum/viewtopic.php?t=…`  
- **Login**: not required for current parser (magnets on public topic pages; auth code is commented out)

## Cron endpoints

| Action | Code path | What it does |
| -------- | ----------- | -------------- |
| `Parse` | `ParseAsync` | First page (`page=0` by default) of each **QuickParse** forum (~**65**) |
| `UpdateTasksParse` | `UpdateTasksParseAsync` | Hits **all ~211** forums to learn page counts → `Data/temp/rutracker_taskParse.json` (**no lock**) |
| `ParseLatest` | `ParseLatestAsync` | First *N* pages of **every** cat in `taskParse` (heavy once the map is full) |
| `ParseAllTask` | `ParseAllTaskAsync` | Full backlog of every page in `taskParse` (multi-hour) |

### Request unit (`parsePage`)

1. **1×** GET forum list  
2. For each torrent **not** already in FDB with the same title: **1×** GET topic (magnet)

`parseDelay` / `reqMinute` apply to `ParseLatest` and `ParseAllTask` only — **not** to `Parse` or `UpdateTasksParse`.

Category counts (from `RutrackerCategories`): **211** forums, **65** `QuickParse = true`.

## Recommended cron (minimize requests, keep useful freshness)

Primary freshness is **`Parse` page 0 of QuickParse**, not `ParseAllTask`.

Repo [`cron/jobs.yaml`](../../../cron/jobs.yaml) follows this cadence (ParseAll twice daily so a 6h wall can continue same day):

```cron
# Fresh releases: 65 quick forums, first page only (~65 GETs/run)
0 * * * *     curl -s "http://127.0.0.1:9117/cron/rutracker/parse"

# Rebuild page-task map once (211 GETs) — not every few hours
20 3 * * *    curl -s "http://127.0.0.1:9117/cron/rutracker/UpdateTasksParse"

# Deep crawl: morning start + ~6h later continue (pages with updateTime != today)
40 4,11 * * * curl -s "http://127.0.0.1:9117/cron/rutracker/ParseAllTask"
```

### Avoid

- Hourly `UpdateTasksParse` / `ParseAllTask` — over-requests; while a crawl runs cron only gets `work`. Prefer 2×/day ParseAll (start + continue).  
- Scheduling `ParseLatest?pages=5` for “light” refresh — with a full `taskParse` it is **heavier** than hourly `parse` (~211×N forum pages).

### Tunable intensity

| Goal | Change |
| ------ | -------- |
| Fresher (~30 min) | `*/30 * * * *` → `parse` |
| Quieter | `0 */2 * * *` → `parse` |
| Slower deep crawl | raise `Rutracker.reqMinute` (longer `parseDelay`) |

## Worker requests / day (recommended cron)

Assumptions: 65 QuickParse, 211 forums, ~**40** pages/cat average for full crawl; topic GETs only when FDB misses title.

### Fixed forum GETs

| Component | Forum GETs |
| ----------- | ------------ |
| `parse` hourly | **1 560 / day** (65 × 24) |
| `UpdateTasksParse` daily | **211 / day** |
| `ParseAllTask` 2×/day (up to 6h each) | forum GETs depend on unfinished pages; floor often **~1–2k / day** amortized when warm |
| **Forum floor** | **~2–4 000 / day** (parse + Update + partial ParseAll) |

### Totals including topic/magnet GETs (warm DB)

| Horizon | Forum only | Quiet (~300 topic/day) | Typical (~750 topic/day) | Busy (~1 500 topic/day) |
| --------- | ------------ | ------------------------ | -------------------------- | ------------------------- |
| **1 day** | ~3 000 | ~3 300 | ~3 800 | ~4 500 |
| **7 days** | ~21 000 | ~23 000 | ~27 000 | ~32 000 |
| **30 days** | ~89 000 | ~100 000 | ~114 000 | ~136 000 |

Planning ballpark: **~3.5k–4.5k / day**, **~25k–30k / week**, **~100k–120k / month** via the Worker.

A cold first full crawl can spike topic GETs for several days until the task map pages catch up.

### vs aggressive schedules

Forum floor alone is often **~15k+ / day** if Update/ParseAll fire hourly; prefer the balanced block above (also the repo default in `cron/jobs.yaml`).

## Related files

- `RutrackerSyncService.cs` — cron sync  
- `RutrackerParser.cs` — HTML → torrents / magnets  
- `RutrackerCategories.cs` — forum map + QuickParse  
- `Controllers/Cron/RutrackerController.cs` — HTTP entrypoints  
- Repo `cron/jobs.yaml` / `Data/crontab` — balanced schedule (matches recommended block above)
