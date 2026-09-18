#!/usr/bin/env python3
"""Unstick ParseAll when a few map slots never mark done (empty hole pages).

Works on every IParseAllStarter trio map (flat cat/page or nested cat/arg/page):
anibelka, kinozal, korsars, megapeer, nnmclub, rutor, rutracker, toloka,
torrentby, ultradox. Omit the slug to act on all of them that have files.

JacRed only advances a slot when parsePage returns true. Empty-but-valid
listings leave parseAllCycleId stale, so the cycle sits at pending=N forever
and never rotates. This edits Data/temp/{slug}_taskParse.json in place.

  python3 scripts/parseall_cycle.py --dir /opt/jacred/Data/temp status
  python3 scripts/parseall_cycle.py --dir /opt/jacred/Data/temp skip-pending
  python3 scripts/parseall_cycle.py --dir /opt/jacred/Data/temp skip-pending --apply
  python3 scripts/parseall_cycle.py --dir /opt/jacred/Data/temp recrawl --skip-pending --apply
  python3 scripts/parseall_cycle.py --dir /opt/jacred/Data/temp recrawl rutor kinozal --skip-pending --apply
  python3 scripts/parseall_cycle.py --dir /opt/jacred/Data/temp mark rutor 1/160 4/233 --apply
  ssh master.jacred.stream 'python3 - --dir /opt/jacred/Data/temp status' < scripts/parseall_cycle.py

No slug + skip-pending/recrawl --skip-pending: only trackers with
0 < pending <= --max-pending (hole-loop). A live crawl is left alone.
Stop ParseAll for those slugs first (/health/background-jobs) or the
running job can overwrite the json.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path

try:
    REPO_ROOT = Path(__file__).resolve().parents[1]
except NameError:
    REPO_ROOT = Path.cwd()

DEFAULT_DIRS = (
    Path("/opt/jacred/Data/temp"),
    REPO_ROOT / "Data" / "temp",
    Path("Data/temp"),
)

# Keep in sync with tests/JacRed.Tests/Trackers/ParseAllStarterCoverageTests.cs
PARSEALL_SLUGS = (
    "anibelka",
    "kinozal",
    "korsars",
    "megapeer",
    "nnmclub",
    "rutor",
    "rutracker",
    "toloka",
    "torrentby",
    "ultradox",
)


def default_temp_dir() -> Path:
    for p in DEFAULT_DIRS:
        if p.is_dir():
            return p
    return DEFAULT_DIRS[0]


def today_stamp() -> str:
    # Match C# DateTime.Today as stored by Newtonsoft on master (+03:00).
    s = datetime.now().astimezone().strftime("%Y-%m-%dT00:00:00%z")
    if len(s) >= 5 and s[-5] in "+-" and s[-3] != ":":
        s = s[:-2] + ":" + s[-2:]
    return s


def utc_now_z() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def iter_pages(node, prefix=()):
    if isinstance(node, list):
        for item in node:
            if isinstance(item, dict) and "page" in item:
                yield prefix, item
        return
    if isinstance(node, dict):
        for key, child in node.items():
            yield from iter_pages(child, prefix + (str(key),))


def page_key(prefix, item) -> str:
    return "/".join(prefix + (str(item["page"]),))


def is_pending(item, cycle_id: str | None) -> bool:
    if not cycle_id:
        return True
    return item.get("parseAllCycleId") != cycle_id


def load_json(path: Path):
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def atomic_write(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def backup(path: Path) -> Path:
    bak = path.with_suffix(path.suffix + ".bak")
    shutil.copy2(path, bak)
    return bak


def discover_slugs(temp_dir: Path) -> list[str]:
    on_disk = {p.name[: -len("_taskParse.json")] for p in temp_dir.glob("*_taskParse.json")}
    known = [s for s in PARSEALL_SLUGS if s in on_disk]
    extra = sorted(on_disk - set(PARSEALL_SLUGS))
    return known + extra


def resolve_slugs(temp_dir: Path, requested: list[str] | None) -> list[str]:
    if requested:
        return list(requested)
    slugs = discover_slugs(temp_dir)
    if not slugs:
        raise SystemExit(f"no ParseAll *_taskParse.json in {temp_dir}")
    return slugs


def looks_stuck(pending_count: int, max_pending: int, force: bool) -> bool:
    if pending_count <= 0:
        return False
    return force or pending_count <= max_pending


def load_tracker(temp_dir: Path, slug: str):
    task_path = temp_dir / f"{slug}_taskParse.json"
    cycle_path = temp_dir / f"{slug}_parseAllCycle.json"
    task = load_json(task_path)
    cycle = load_json(cycle_path) or {}
    if task is None:
        raise SystemExit(f"missing {task_path}")
    pages = list(iter_pages(task))
    cid = cycle.get("CycleId") or None
    pending = [(page_key(pref, item), item) for pref, item in pages if is_pending(item, cid)]
    return task_path, cycle_path, task, cycle, pages, pending, cid


def print_status(temp_dir: Path, slug: str) -> None:
    task_path, cycle_path, _task, cycle, pages, pending, cid = load_tracker(temp_dir, slug)
    total = len(pages)
    print(f"{slug}: pending={len(pending)}/{total} cycle={cid or '-'} "
          f"started={cycle.get('StartedAtUtc', '-')} fingerprint={(cycle.get('MapFingerprint') or '')[:12]} "
          f"files={task_path.name},{cycle_path.name}")
    for key, item in pending[:40]:
        print(f"  {key}  cycleId={item.get('parseAllCycleId')!r}  updateTime={item.get('updateTime')}")
    if len(pending) > 40:
        print(f"  ... {len(pending) - 40} more")


def mark_items(items, cycle_id: str) -> int:
    stamp = today_stamp()
    n = 0
    for item in items:
        item["parseAllCycleId"] = cycle_id
        item["updateTime"] = stamp
        n += 1
    return n


def clear_cycle_ids(items) -> int:
    n = 0
    for item in items:
        if item.get("parseAllCycleId"):
            item["parseAllCycleId"] = None
            n += 1
    return n


def apply_files(task_path: Path, cycle_path: Path, task, cycle, apply: bool) -> None:
    if not apply:
        print("dry-run (no write). pass --apply to save.")
        return
    backup(task_path)
    if cycle_path.is_file():
        backup(cycle_path)
    atomic_write(task_path, task)
    atomic_write(cycle_path, cycle)
    print(f"wrote {task_path} and {cycle_path} (backups *.bak)")


def refuse_too_many(slug: str, pending, max_pending: int, force: bool, action: str) -> bool:
    """True = abort this slug."""
    if force or len(pending) <= max_pending:
        return False
    keys = ", ".join(k for k, _ in pending[:8])
    print(
        f"{slug}: skip {action}: {len(pending)} pending > --max-pending {max_pending} "
        f"({keys}…). live crawl, not a hole-loop. --force or pass this slug explicitly."
    )
    return True


def cmd_skip_pending(temp_dir: Path, slug: str, apply: bool, max_pending: int, force: bool, require_stuck: bool) -> None:
    task_path, cycle_path, task, cycle, pages, pending, cid = load_tracker(temp_dir, slug)
    if not cid:
        print(f"{slug}: no CycleId; use recrawl instead")
        return
    if not pending:
        print(f"{slug}: already pending=0/{len(pages)}")
        return
    if require_stuck and not looks_stuck(len(pending), max_pending, force):
        refuse_too_many(slug, pending, max_pending, force, "skip-pending")
        return
    if refuse_too_many(slug, pending, max_pending, force, "skip-pending"):
        return
    n = mark_items([item for _, item in pending], cid)
    print(f"{slug}: mark {n} pending slots done in cycle {cid}")
    for key, _ in pending:
        print(f"  skip {key}")
    apply_files(task_path, cycle_path, task, cycle, apply)
    print(f"{slug}: next ParseAllTask pending=0 → new cycle (full recrawl, same holes will stick again)")


def cmd_recrawl(temp_dir: Path, slug: str, skip_pending: bool, apply: bool, max_pending: int, force: bool, require_stuck: bool) -> None:
    task_path, cycle_path, task, cycle, pages, pending, _cid = load_tracker(temp_dir, slug)
    if require_stuck and skip_pending and not looks_stuck(len(pending), max_pending, force):
        if not pending:
            print(f"{slug}: skip recrawl, pending=0/{len(pages)}")
        else:
            refuse_too_many(slug, pending, max_pending, force, "recrawl --skip-pending")
        return
    if skip_pending and refuse_too_many(slug, pending, max_pending, force, "recrawl --skip-pending"):
        return
    new_id = uuid.uuid4().hex
    skip_set = {id(item) for _, item in pending} if skip_pending else set()
    skipped = mark_items([item for _, item in pending], new_id) if skip_pending else 0
    reset = clear_cycle_ids([item for _, item in pages if id(item) not in skip_set])
    cycle = {
        "CycleId": new_id,
        "StartedAtUtc": utc_now_z(),
        "MapFingerprint": cycle.get("MapFingerprint"),
        "MapCount": len(pages),
    }
    print(f"{slug}: new cycle {new_id} map={len(pages)} pending={len(pages) - skipped} skipped_holes={skipped} cleared={reset}")
    if skip_pending:
        for key, _ in pending:
            print(f"  skip {key}")
    apply_files(task_path, cycle_path, task, cycle, apply)
    print(f"{slug}: then curl -sS http://127.0.0.1:9117/cron/{slug}/ParseAllTask")


def cmd_mark(temp_dir: Path, slug: str, keys: list[str], apply: bool) -> None:
    task_path, cycle_path, task, cycle, pages, _pending, cid = load_tracker(temp_dir, slug)
    if not cid:
        raise SystemExit(f"{slug}: no CycleId")
    want = set(keys)
    found = []
    for pref, item in pages:
        key = page_key(pref, item)
        if key in want:
            found.append((key, item))
    missing = want - {k for k, _ in found}
    if missing:
        raise SystemExit(f"unknown keys: {', '.join(sorted(missing))}")
    n = mark_items([item for _, item in found], cid)
    print(f"{slug}: mark {n} slots done in cycle {cid}")
    for key, _ in found:
        print(f"  skip {key}")
    apply_files(task_path, cycle_path, task, cycle, apply)


def self_test() -> None:
    with tempfile.TemporaryDirectory() as raw:
        d = Path(raw)
        cid = "aaa" + "b" * 29
        flat = {
            "1": [
                {"page": 0, "parseAllCycleId": cid, "updateTime": "2026-09-18T00:00:00+03:00"},
                {"page": 160, "parseAllCycleId": "old", "updateTime": "2026-09-17T00:00:00+03:00"},
            ],
            "4": [
                {"page": 233, "parseAllCycleId": "old", "updateTime": "2026-09-17T00:00:00+03:00"},
            ],
        }
        cycle = {"CycleId": cid, "StartedAtUtc": "2026-09-18T12:00:00Z", "MapFingerprint": "ff", "MapCount": 3}
        atomic_write(d / "rutor_taskParse.json", flat)
        atomic_write(d / "rutor_parseAllCycle.json", cycle)
        _tp, _cp, task, cycle, pages, pending, loaded = load_tracker(d, "rutor")
        assert loaded == cid and len(pages) == 3 and [k for k, _ in pending] == ["1/160", "4/233"]

        mark_items([item for _, item in pending], cid)
        atomic_write(d / "rutor_taskParse.json", task)
        pending2 = load_tracker(d, "rutor")[5]
        assert pending2 == []

        nested = {"2024": {"0": [{"page": 3, "parseAllCycleId": "abc"}]}}
        atomic_write(d / "kinozal_taskParse.json", nested)
        atomic_write(d / "kinozal_parseAllCycle.json", {"CycleId": "abc", "MapCount": 1})
        assert load_tracker(d, "kinozal")[5] == []
        nested["2024"]["0"][0]["parseAllCycleId"] = "old"
        atomic_write(d / "kinozal_taskParse.json", nested)
        keys = [k for k, _ in load_tracker(d, "kinozal")[5]]
        assert keys == ["2024/0/3"], keys

        assert discover_slugs(d) == ["kinozal", "rutor"]
        # live crawl (pending=2 on a 2-page map still counts as stuck if <= max)
        live = {"0": [{"page": i, "parseAllCycleId": None} for i in range(80)]}
        atomic_write(d / "nnmclub_taskParse.json", live)
        atomic_write(d / "nnmclub_parseAllCycle.json", {"CycleId": "nnm", "MapCount": 80})
        assert looks_stuck(2, 50, False) is True
        assert looks_stuck(80, 50, False) is False
        assert looks_stuck(0, 50, False) is False
    print("self-test ok")


def add_write_flags(sp: argparse.ArgumentParser) -> None:
    sp.add_argument("--apply", action="store_true", help="write files (default is dry-run)")
    sp.add_argument("--max-pending", type=int, default=50, help="refuse skip when pending exceeds this")
    sp.add_argument("--force", action="store_true", help="allow skip/recrawl above --max-pending")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--dir", type=Path, default=None, help="Data/temp directory")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("self-test")
    st = sub.add_parser("status", help="all ParseAll trackers, or given slugs")
    st.add_argument("slugs", nargs="*", help="omit = every trio map on disk")
    sp = sub.add_parser("skip-pending", help="mark current pending slots done (hole-loop)")
    sp.add_argument("slugs", nargs="*", help="omit = every stuck tracker (pending <= --max-pending)")
    add_write_flags(sp)
    rc = sub.add_parser("recrawl", help="new cycle; omit slug = stuck trackers only")
    rc.add_argument("slugs", nargs="*", help="omit = every stuck tracker")
    rc.add_argument("--skip-pending", action="store_true", help="keep current pending slots skipped in the new cycle")
    add_write_flags(rc)
    mk = sub.add_parser("mark", help="mark named keys done in the current cycle")
    mk.add_argument("slug")
    mk.add_argument("keys", nargs="+", help="flat cat/page or nested cat/arg/page")
    mk.add_argument("--apply", action="store_true", help="write files (default is dry-run)")
    return p


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    if args.cmd == "self-test":
        self_test()
        return
    temp_dir = args.dir or default_temp_dir()
    if args.cmd == "status":
        slugs = resolve_slugs(temp_dir, args.slugs)
        missing = [s for s in PARSEALL_SLUGS if s not in slugs] if not args.slugs else []
        for slug in slugs:
            try:
                print_status(temp_dir, slug)
            except SystemExit as ex:
                print(f"{slug}: {ex}")
        if missing:
            print("no taskParse yet: " + ", ".join(missing))
        return
    if args.cmd in ("skip-pending", "recrawl"):
        explicit = bool(args.slugs)
        slugs = resolve_slugs(temp_dir, args.slugs)
        if args.cmd == "recrawl" and not explicit and not args.skip_pending and not args.force:
            raise SystemExit("recrawl with no slug needs --skip-pending (stuck hole-loops only) or --force")
        require_stuck = not explicit
        for slug in slugs:
            try:
                if args.cmd == "skip-pending":
                    cmd_skip_pending(temp_dir, slug, args.apply, args.max_pending, args.force, require_stuck)
                else:
                    cmd_recrawl(temp_dir, slug, args.skip_pending, args.apply, args.max_pending, args.force, require_stuck)
            except SystemExit as ex:
                print(f"{slug}: {ex}")
        return
    if args.cmd == "mark":
        cmd_mark(temp_dir, args.slug, args.keys, args.apply)


if __name__ == "__main__":
    main()
