# Lampa / Lampac / NUM → JacRed (reference)

Workflow: [SKILL.md](SKILL.md). Vendor trees under gitignored `temp/` (optional local checkout: `temp/lampa-source`, `temp/lampac`, `temp/num`) are not the source of truth in git.

## Parser types (Lampa Settings → Parser)

Lampa has **no JacRed-specific parser**. `parser_torrent_type` chooses the HTTP shape. JacRed is a Jackett URL (`jackett_url`). Lampa rewrites `jacred.xyz` → `jac.red`. Indexer path is never a named tracker (`rudub`); only `all` or `status:healthy`.

| Client mode | HTTP | Card extras |
| --- | --- | --- |
| **Jackett** (default; JacRed is this) | `GET /api/v2.0/indexers/{all\|status:healthy}/results` | `title`, `title_original`, `year`, `is_serial`, `genres`, `Category[]` |
| **Prowlarr** | `GET /api/v1/search` | `type=tvsearch\|search`, `categories` — **no** title/year/is_serial |
| **TorrServer** | `/search/` and/or `/torznab/search/` | query only |

Prowlarr/TorrServer are **not** JacRed card mode. `plugins/online*` in Lampa are video balansers (Rezka, Filmix), not torrent parsers.

**Dual Jackett** (`parser_use_link` = both): Lampa merges two Jackett responses **client-side**. Each request JacRed sees is still `/indexers/all/results` (or `status:healthy`).

## Request paths vs JacRed

| Client path | What is sent | JacRed mode |
| --- | --- | --- |
| Lampa card Torrents | `Query` (`parse_lang`) + `title` + `title_original` + `year` + `is_serial` + `Category[]` | **CardMode** → `JackettCardMatcher` |
| Lampa **Уточнить** | User `Query`; **no** title pair; keep `year` / `is_serial` / `Category` | CardMode (`is_serial>=0` or categories) without title keys |
| Lampa `parse_in_search` / `from_search` | `Query` only | Fuzzy / `NumQueryParser` if NUM UA |
| Lampac Online **PidTor** | `title` + `title_original` + `year` + `is_serial`; **no Query** | CardMode |
| NUM Android | `query` only + Chrome/106 UA | `NumQueryParser` promotes into card fields |

CardMode when any of: non-empty `title` / `title_original`, `is_serial>=0`, categories, or `genres` (`IndexerRequestParams.IsCardMetadataSearch`).

ASP.NET binds `Query` and `query` (`IndexerRequestParams.ResolveSearchQuery`: `q`, then `Query`, then `query`).

## `parse_lang` → `Query` (Lampa Jackett)

Default **`df`** = original title only. Combos concatenate TMDB names and optional year (spaces, not `/`).

| `parse_lang` | `Query` roughly |
| --- | --- |
| `df` (default) | original title |
| `lg` | localized (RU) title |
| `df_lg` | original + localized |
| `lg_df` | localized + original |
| `df_year` / `lg_year` | title + year |
| `df_lg_year` / `lg_df_year` | both titles + year |

NUM-style free text (`Ru En Year`, `En Ru Year`) is parsed by `NumQueryParser` when `rqnum` is true **or** when titles are empty and the query matches those patterns.

## `is_serial`

| Source | Values |
| --- | --- |
| Lampa card | `original_name` present → **2** (serial), else **1** (movie) |
| PidTor | movie **1**, serial **2**, original language `ja` → **5** (anime) |
| JacRed matcher | **1** movie, **2** serial, **3** tvshow, **4** doc, **5** anime |

If Lampa sends `is_serial=0` but `Category[]` is set, JacRed infers type from category (`20xx` movie, `50xx` serial, `5070` anime, `5080` doc, `5020`/`2010` tvshow).

Lampa `Category[]`: `5000` if `number_of_seasons>0` else `2000`; add `5070` if language ja/zh **and** TMDB animation.

## Year

| Layer | Behavior |
| --- | --- |
| Lampa card | `year` from `first_air_date` or `release_date` (always on card) |
| JacRed `MatchesCardYear` | `year<=0` or `relased<=0` **passes**; movies ±1; serials `relased >= year-1` |
| Lampa torrents UI filter | Optional **client-side** filter on result titles; does **not** re-call the API |

Do not confuse the UI year filter with a second Jackett request.

## URL templates (local `:9117`)

Replace host/port. Omit `apikey` if unset. Lampa uses capital `Query`.

### Lampa card — TV (Jackett)

```bash
curl -sG "http://127.0.0.1:9117/api/v2.0/indexers/all/results" \
  --data-urlencode "Query=Lanterns" \
  --data-urlencode "title=Фонари" \
  --data-urlencode "title_original=Lanterns" \
  --data-urlencode "year=2025" \
  --data-urlencode "is_serial=2" \
  --data-urlencode "Category[]=5000"
```

Movie: `is_serial=1`, `Category[]=2000`. Anime PidTor: `is_serial=5`, often no `Query`.

### Lampa clarification (Уточнить)

```bash
curl -sG "http://127.0.0.1:9117/api/v2.0/indexers/all/results" \
  --data-urlencode "Query=фонари" \
  --data-urlencode "year=2025" \
  --data-urlencode "is_serial=2" \
  --data-urlencode "Category[]=5000"
```

No `title` / `title_original`.

### Lampa / NUM query-only

```bash
curl -sG "http://127.0.0.1:9117/api/v2.0/indexers/all/results" \
  --data-urlencode "query=фонари"
```

NUM UA (triggers `rqnum` in `JackettSearchService`):

```bash
curl -sG "http://127.0.0.1:9117/api/v2.0/indexers/all/results" \
  -A "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/106.0.0.0 Safari/537.36" \
  --data-urlencode "query=Фонари Lanterns 2025"
```

### PidTor (card fields, no Query)

```bash
curl -sG "http://127.0.0.1:9117/api/v2.0/indexers/all/results" \
  --data-urlencode "title=Фонари" \
  --data-urlencode "title_original=Lanterns" \
  --data-urlencode "year=2025" \
  --data-urlencode "is_serial=2"
```

### Contrast: fuzzy v1 (not the card button)

```bash
curl -s "http://127.0.0.1:9117/api/v1.0/torrents?search=фонари"
```

Healthy indexer alias (same as `all` on JacRed):

```text
GET /api/v2.0/indexers/status:healthy/results
```

Named `/indexers/rudub/results` is **not** what stock Lampa sends.

## JacRed code pointers

| Piece | Path |
| --- | --- |
| v2 entry | `Controllers/JackettController.cs` |
| Query bind / CardMode flag | `Infrastructure/Indexers/IndexerRequestParams.cs` (`ResolveSearchQuery`, `IsCardMetadataSearch`) |
| NUM UA + `is_serial` in QS | `Application/Search/JackettSearchService.cs` (`rqnum`) |
| Card exact match | `Application/Search/JackettCardMatcher.cs` |
| Year gate | `Infrastructure/Indexers/IndexerResultFilters.cs` (`MatchesCardYear`) |
| Query-only → titles | `Infrastructure/Indexers/NumQueryParser.cs` |
| Combined search | `Infrastructure/Indexers/IndexerSearchEngine.cs` |

Lampa client (if checked out locally, do not commit):

- `temp/lampa-source/src/core/api/sources/parser.js` — Jackett query build (~card extras)
- `temp/lampa-source/src/components/full/start/torrents.js` — card Torrents entry
- `temp/lampa-source/src/components/torrents.js` — optional UI year filter
- `temp/lampac/Modules/PidTor/Controller.cs` — PidTor card fields

User-facing: `docs/clients/overview.mdx`, `docs/api-reference/jackett.mdx`, `docs/concepts/search.mdx`.
