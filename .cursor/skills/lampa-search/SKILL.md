---
name: lampa-search
description: >-
  Debugs JacRed search as Lampa, Lampac PidTor, and NUM actually call it
  (Jackett v2 card vs query, parse_lang, is_serial, clarification, year gate).
  Use when Lampa/Lampac torrents are empty, card search misses a tracker, the
  user mentions parse_lang, Уточнить, PidTor, NUM, title_original, or Jackett
  Query vs query.
---

# Lampa / Lampac / NUM search

How torrent clients hit JacRed. Pair with [reference.md](reference.md) for URL
templates and `is_serial` maps. Tracker scrape playbook is separate:
[jacred-tracker-parser](../jacred-tracker-parser/SKILL.md).

Local Lampa/Lampac/NUM trees may exist under gitignored `temp/` — do not commit
them. This skill is the contract.

## Identify the client path

| Symptom / setting | Path |
|-------------------|------|
| Lampa card → Torrents, Jackett URL = JacRed | **Card** — `Query` + title pair + `year` + `is_serial` |
| Lampa filter **Уточнить** | **Clarification** — new `Query`, **no** `title` / `title_original`, year kept |
| Lampa global search (`parse_in_search`) | **Query-only** (`from_search`) |
| Lampac Online balancer PidTor | **Card fields only** — no `Query`; anime `is_serial=5` |
| NUM Android | **Query-only** + Chrome/106 UA → `NumQueryParser` |
| Lampa `parser_torrent_type=prowlarr` | Prowlarr `/api/v1/search` — **not** JacRed card mode |
| Lampa Rezka / Filmix / `plugins/online*` | Video balansers — **not** torrent parsers |

JacRed is configured as **Jackett**, not a named indexer. Path is `all` or
`status:healthy`, never `/indexers/rudub/results` from stock Lampa.

## Reproduce (do not guess URLs)

Replay the **same** request JacRed sees. Recipes: [reference.md](reference.md).

1. Card TV (Lampa): `Query` + `title` + `title_original` + `year` + `is_serial=2` + `Category[]=5000`.
2. Compare with fuzzy: `?query=` only (v1 `/api/v1.0/torrents` or v2 without titles).
3. If (1) empty and (2) hits — card year/type/`_sn`, not “parser broken”.

ASP.NET binds `Query` and `query`. Lampa sends capital `Query`; NUM sends `query`.

## Empty card checklist

Do **not** “fix” only fuzzy v1.

1. **Names** — `SearchName(title)` equals torrent `_sn` or `_so` (exact). Russian `_sn` OR original `_so`.
2. **Year** — [`MatchesCardYear`](../../../Infrastructure/Indexers/IndexerResultFilters.cs): `relased<=0` passes; movies ±1; serials `>= year-1`.
3. **Type** — `is_serial=1` needs `movie` (etc.); `=2` needs `serial`; PidTor `=5` needs `anime`.
4. **Allowlist** — `synctrackers` / `disable_trackers` / indexer path filter.
5. **Clarification** — titles omitted; matching is Query/`NumQueryParser` + leftover year/is_serial.

Lampa’s year dropdown after results filters **titles in the UI**; it does not
re-request JacRed.

## Anti-patterns

- Treating Rezka/Filmix as torrent parsers
- Inventing named Jackett indexer paths for Lampa
- Assuming v1 `?search=` is what the card button sends
- Ignoring `parse_lang` (default `df` = original title as `Query`)
- Changing tracker parse when the miss is card year/`is_serial`

## Related

- Contract tables: [reference.md](reference.md)
- JacRed v2: `Controllers/JackettController.cs`, `Application/Search/JackettCardMatcher.cs`, `Infrastructure/Indexers/NumQueryParser.cs`
- User docs: `docs/clients/overview.mdx`, `docs/api-reference/jackett.mdx`
- Tracker parsers: [jacred-tracker-parser](../jacred-tracker-parser/SKILL.md)
