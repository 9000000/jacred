# JacRed HTTP job scheduler (host crontab + run-job.sh)

Source of truth: [`jobs.yaml`](jobs.yaml). Generator writes `generated/*.env` + safe crontab. Each job runs via [`run-job.sh`](run-job.sh) (flock + curl `--max-time`).

JacRed returns `ok` / `work` / `disabled` quickly. Long jobs (`ParseAllTask`, `UpdateTasksParse`) start work in the background and return immediately.

## Install

Assumes JacRed at `/opt/jacred` (override with `JACRED_CRON_DIR` when generating).

```bash
chmod +x /opt/jacred/cron/*.sh
sudo /opt/jacred/cron/install.sh
```

This will:

1. Run `generate.py` → `generated/*.env` + `Data/crontab`
2. Remove leftover `jacred-job-*` **systemd** timers/services (if any)
3. Install the host crontab (`crontab Data/crontab`)

Confirm:

```bash
crontab -l | head
/opt/jacred/cron/check-jobs.sh
```

### One-shot systemd cleanup only

```bash
sudo /opt/jacred/cron/uninstall.sh
```

## Manage jobs

Edit [`jobs.yaml`](jobs.yaml):

```yaml
base_url: http://127.0.0.1:9117

jobs:
  - name: rutor-parse
    schedule: "1,16,31,46 * * * *"
    path: /cron/rutor/parse
    max_time: 900
  - name: rutor-UpdateTasksParse
    schedule: "5 2 * * *"
    path: /cron/rutor/UpdateTasksParse
    max_time: 60
    enabled: false   # optional — skip this job
```

| Field | Meaning |
|-------|---------|
| `base_url` | JacRed HTTP base |
| `schedule` | Standard 5-field cron |
| `path` | URL path relative to `base_url` |
| `max_time` | Curl `--max-time` seconds (HTTP deadline only — not crawl duration) |
| `enabled` | `false` to skip this job |

Defaults when `max_time` is omitted: ack jobs (`ParseAllTask`, `UpdateTasksParse`, `jsondb/save`) → **60s**; everything else → 900 (15m).

In-app crawl walls remain ~6h (ParseAll) / ~30m (UpdateTasks).

After edits:

```bash
sudo /opt/jacred/cron/install.sh
```

If `apikey` / `devkey` is required, add query params to `path` (e.g. `/cron/rutor/parse?devkey=...`).

Non-standard install path:

```bash
JACRED_CRON_DIR=/opt/jacred/cron python3 /opt/jacred/cron/generate.py
```

## Run / status

```bash
# one job
/opt/jacred/cron/run-job.sh rutor-parse

# status: crontab lines, env files, flock locks, leftover systemd
/opt/jacred/cron/check-jobs.sh
```

Flock lock files live under `/tmp/jacred-cron-locks/` (not logs). Override with `LOCK_DIR=...`.

Cron job output goes to the crontab owner's mail / syslog (depending on host config).

## JacRed responses

| Body | Meaning |
|------|---------|
| `ok` | Job finished (or long job started in background) |
| `work` | Tracker already busy |
| `disabled` | Tracker disabled in config |
| `TIMEOUT …` | Curl hit `max_time` |

## Schedule notes (balanced defaults in `jobs.yaml`)

Defaults keep **parse** frequent (staggered minutes) for freshness, **UpdateTasksParse** once daily, and **ParseAllTask** twice daily (morning start + afternoon/midday continue after the 6h in-app wall). Rutracker uses `04:40` + `11:40` (~6h apart); smaller task trackers use `04:xx` + `16:xx`. Toloka includes the full Update + ParseAll pipeline. Weekly `maintenance-check` runs FDB report mode.

| Pattern | Meaning | Prefer |
|---------|---------|--------|
| `* */4 * * *` | **every minute** in hours 0/4/8/12/16/20 | once daily e.g. `5 2 * * *` |
| Hourly ParseAllTask | mostly `work` while crawl runs | 2×/day start + continue |
| Same minute for many parsers | load spike | stagger (see `jobs.yaml`) |

Do not schedule `ParseLatest`, Lostfilm `ParsePages` / `ParseSeasonPacks`, or maintenance `Status` here (ops/manual).

### Job roles

| Kind | Purpose |
|------|---------|
| `parse` | Fresh releases — first page(s) / QuickParse |
| `UpdateTasksParse` | Rebuild page map in `Data/temp/*_taskParse.json` |
| `ParseAllTask` | Deep crawl pages with `updateTime ≠ today` (2×/day continue) |
| `jsondb-save` | Flush FileDB to disk |
| `maintenance` | Weekly FDB integrity report |

### Current schedule (32 jobs)

Source: [`jobs.yaml`](jobs.yaml). After edits, regenerate with `generate.py` / `install.sh`.

| Job | Kind | Cron | When it runs | Path | max_time |
|-----|------|------|--------------|------|----------|
| jsondb-save | save | `*/5 * * * *` | every 5 min | `/jsondb/save` | 60s |
| rutor-parse | parse | `1,16,31,46 * * * *` | hourly :01,:16,:31,:46 | `/cron/rutor/parse` | 900s |
| rutor-UpdateTasksParse | UpdateTasks | `5 2 * * *` | daily 02:05 | `/cron/rutor/UpdateTasksParse` | 60s |
| rutor-ParseAllTask | ParseAll | `30 4,16 * * *` | daily 04:30, 16:30 | `/cron/rutor/ParseAllTask` | 60s |
| rutracker-parse | parse | `0 * * * *` | hourly :00 | `/cron/rutracker/parse` | 900s |
| rutracker-UpdateTasksParse | UpdateTasks | `20 3 * * *` | daily 03:20 | `/cron/rutracker/UpdateTasksParse` | 60s |
| rutracker-ParseAllTask | ParseAll | `40 4,11 * * *` | daily 04:40, 11:40 | `/cron/rutracker/ParseAllTask` | 60s |
| kinozal-parse | parse | `3,18,33,48 * * * *` | hourly :03,:18,:33,:48 | `/cron/kinozal/parse` | 900s |
| kinozal-UpdateTasksParse | UpdateTasks | `10 2 * * *` | daily 02:10 | `/cron/kinozal/UpdateTasksParse` | 60s |
| kinozal-ParseAllTask | ParseAll | `35 4,16 * * *` | daily 04:35, 16:35 | `/cron/kinozal/ParseAllTask` | 60s |
| nnmclub-parse | parse | `5,20,35,50 * * * *` | hourly :05,:20,:35,:50 | `/cron/nnmclub/parse` | 900s |
| nnmclub-UpdateTasksParse | UpdateTasks | `15 2 * * *` | daily 02:15 | `/cron/nnmclub/UpdateTasksParse` | 60s |
| nnmclub-ParseAllTask | ParseAll | `42 4,16 * * *` | daily 04:42, 16:42 | `/cron/nnmclub/ParseAllTask` | 60s |
| selezen-parse | parse | `9,24,39,54 * * * *` | hourly :09,:24,:39,:54 | `/cron/selezen/parse` | 900s |
| megapeer-parse | parse | `8 * * * *` | hourly :08 | `/cron/megapeer/parse` | 900s |
| megapeer-UpdateTasksParse | UpdateTasks | `20 2 * * *` | daily 02:20 | `/cron/megapeer/UpdateTasksParse` | 60s |
| megapeer-ParseAllTask | ParseAll | `45 4,16 * * *` | daily 04:45, 16:45 | `/cron/megapeer/ParseAllTask` | 60s |
| torrentby-parse | parse | `7,22,37,52 * * * *` | hourly :07,:22,:37,:52 | `/cron/torrentby/parse` | 900s |
| torrentby-UpdateTasksParse | UpdateTasks | `25 2 * * *` | daily 02:25 | `/cron/torrentby/UpdateTasksParse` | 60s |
| torrentby-ParseAllTask | ParseAll | `50 4,16 * * *` | daily 04:50, 16:50 | `/cron/torrentby/ParseAllTask` | 60s |
| toloka-parse | parse | `14,54 * * * *` | hourly :14,:54 | `/cron/toloka/parse` | 900s |
| toloka-UpdateTasksParse | UpdateTasks | `30 2 * * *` | daily 02:30 | `/cron/toloka/UpdateTasksParse` | 60s |
| toloka-ParseAllTask | ParseAll | `55 4,16 * * *` | daily 04:55, 16:55 | `/cron/toloka/ParseAllTask` | 60s |
| mazepa-parse | parse | `25 * * * *` | hourly :25 | `/cron/mazepa/parse` | 900s |
| lostfilm-parse | parse | `11,26,41,56 * * * *` | hourly :11,:26,:41,:56 | `/cron/lostfilm/parse` | 900s |
| bitru-parse | parse | `10,30,50 * * * *` | hourly :10,:30,:50 | `/cron/bitru/parse` | 900s |
| knaben-parse | parse | `12,32,52 * * * *` | hourly :12,:32,:52 | `/cron/knaben/parse` | 900s |
| animelayer-parse | parse | `2,17,32,47 * * * *` | hourly :02,:17,:32,:47 | `/cron/animelayer/parse` | 900s |
| anidub-parse | parse | `4,19,34,49 * * * *` | hourly :04,:19,:34,:49 | `/cron/anidub/parse` | 900s |
| aniliberty-parse | parse | `6,21,36,51 * * * *` | hourly :06,:21,:36,:51 | `/cron/aniliberty/parse` | 900s |
| baibako-parse | parse | `8,23,38,53 * * * *` | hourly :08,:23,:38,:53 | `/cron/baibako/parse` | 900s |
| maintenance-check | maintenance | `0 5 * * 0` | Sun 05:00 | `/cron/maintenance/Check?mode=report` | 60s |

## Layout

```text
cron/
  jobs.yaml         # edit schedules + max_time here
  generate.py       # → generated/*.env + crontab
  run-job.sh        # curl runner (flock + --max-time)
  install.sh        # generate + uninstall systemd leftovers + crontab
  uninstall.sh      # remove leftover jacred-job systemd units
  check-jobs.sh     # crontab / locks / leftover systemd status
  generated/        # .env + crontab (gitignored)
  README.md
Data/crontab        # installable crontab; regenerated by generate.py
```
