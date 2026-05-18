# proceedings-data

Parliamentary debates + questions data for the IndiaVotes / Netas Explorer architecture. Lok Sabha + Rajya Sabha, four-way split, one Cloudflare Pages project per split.

## Why this repo exists

Earlier, debates + questions scrape lived in `NakliTechie/sansadsaar-proceedings-data` as part of SansadSaar. As the data volume grew (LS questions alone is ~243K records and climbing) and as the per-MP analytic experience moved into Netas Explorer, the right home shifted to the IndiaVotes org. This repo is the new home.

SansadSaar continues to surface a thin metadata view (title-only search) — eventually that view will link out to the richer per-MP experience hosted under `new.indiavotes.com/netas/`. Both apps read from the four Pages projects below.

## Repo layout

```
.
├── _debates_core.py            shared core (LS + RS code)
├── _questions_core.py          shared core (LS + RS code)
├── build_debates_ls.py         thin wrapper: BUILDER_HOUSE_FILTER=ls, BUILDER_DOCS_SUBDIR=debates-ls
├── build_debates_rs.py         thin wrapper: BUILDER_HOUSE_FILTER=rs, BUILDER_DOCS_SUBDIR=debates-rs
├── build_questions_ls.py       thin wrapper
├── build_questions_rs.py       thin wrapper
├── debates/                    scraper package (HTTP layer, LS + RS scrapers)
│   ├── common.py
│   └── scrapers/
│       ├── loksabha.py
│       └── rajyasabha.py
├── questions/                  scraper package
│   ├── common.py
│   └── scrapers/
│       ├── loksabha.py
│       └── rajyasabha.py
├── parliamentwatch_text_shards.py    shared text-shard + write_json_idempotent helpers
├── requirements.txt
├── .github/workflows/
│   ├── debates-ls-scrape.yml     ──┐
│   ├── debates-ls-derive.yml       │ workflow_run-chained + 30 min backstop
│   ├── debates-rs-scrape.yml       │
│   ├── debates-rs-derive.yml       │
│   ├── questions-ls-scrape.yml     │
│   ├── questions-ls-derive.yml     │
│   ├── questions-rs-scrape.yml     │
│   ├── questions-rs-derive.yml   ──┘
│   └── cf-sync.yml                deploys all 4 docs subtrees via matrix
└── docs/
    ├── debates-ls/              → Pages project: proceedings-debates-ls
    ├── debates-rs/              → Pages project: proceedings-debates-rs
    ├── questions-ls/            → Pages project: proceedings-questions-ls
    └── questions-rs/            → Pages project: proceedings-questions-rs
```

## Why two cores + four wrappers, not four full scripts

The user wanted "one build script per house" — i.e. four separately invocable entry points. Going all the way to four 700-line forks would have duplicated ~80% of the code (load_existing_reports, save_reports, build_manifest, compute_audit, build_search_bundle, build_search_index, write_meta, write_text_shards, consolidate_markers, the checkpoint commit loop, etc.). So each corpus gets one shared core (`_debates_core.py`, `_questions_core.py`) and four ~25-line wrappers set the three env-var hooks that drive per-split behaviour:

| Env var                 | Set by             | Effect inside core                              |
|-------------------------|--------------------|-------------------------------------------------|
| `BUILDER_DOCS_SUBDIR`   | each wrapper       | `DOCS = ASSETS / "<subdir>"`                    |
| `BUILDER_CORPUS_NAME`   | each wrapper       | `meta.json["corpus"]`                           |
| `BUILDER_HOUSE_FILTER`  | each wrapper       | `HOUSES = ["ls"]` or `["rs"]` — gates walks     |

The wrappers are the "one script per house" interface; the cores are the implementation. Each wrapper can be invoked standalone (`python build_debates_ls.py`) and produces only its split's output.

## Cloudflare Pages setup (manual, one-time)

The `cf-sync.yml` workflow expects four Pages projects to exist already:

| Split          | Pages project name           | Suggested custom domain (TBD)    |
|----------------|------------------------------|----------------------------------|
| debates-ls     | `proceedings-debates-ls`     | `debates-ls.indiavotes.com`      |
| debates-rs     | `proceedings-debates-rs`     | `debates-rs.indiavotes.com`      |
| questions-ls   | `proceedings-questions-ls`   | `questions-ls.indiavotes.com`    |
| questions-rs   | `proceedings-questions-rs`   | `questions-rs.indiavotes.com`    |

For each project: disconnect the GitHub integration (so this workflow's `wrangler pages deploy` is the only deploy source) and add the custom domain after first deploy.

Repo secrets required:

| Secret                  | Purpose                                                         |
|-------------------------|-----------------------------------------------------------------|
| `CLOUDFLARE_API_TOKEN`  | scope: Workers Scripts (Edit) + Workers R2 Storage (Edit)        |
| `CLOUDFLARE_ACCOUNT_ID` | the IndiaVotes CF account                                       |

## Cron schedule

| Workflow                  | Cron                  | Notes                            |
|---------------------------|-----------------------|----------------------------------|
| debates-ls-scrape         | `23 */2 * * *`        | 12×/day, offset                  |
| debates-rs-scrape         | `43 */2 * * *`        | 12×/day, offset                  |
| questions-ls-scrape       | `13 */2 * * *`        | 12×/day, offset                  |
| questions-rs-scrape       | `33 */2 * * *`        | 12×/day, offset                  |
| *-derive (×4)             | `*/30 * * * *`        | + workflow_run from sibling scrape |
| cf-sync                   | `5 0,4,8,12,16,20 * * *` | every 4 h, all 4 splits in parallel via matrix |

## Initial backfill (RS)

The two RS scrapers default to `recent-2` (walk only the two most recent sessions per firing) — the same default as the legacy repo. To do the initial historical backfill, dispatch each RS workflow once with `rs_sessions: all`:

```sh
gh workflow run --repo indiavotes/proceedings-data "Debates RS scrape and publish" -f rs_sessions=all
gh workflow run --repo indiavotes/proceedings-data "Questions RS scrape and publish" -f rs_sessions=all
```

This walks every session the API exposes (~72) in one run. After that, the recurring cron picks up new sittings via `recent-2`.

## Data shape

Each `docs/<split>/` produces the same set of files (matching the existing convention used by the SansadSaar app + Netas):

- `meta.json` — corpus identity + totals + run stats + freshness timestamp. Always-bumped `generated_at` (non-idempotent write) so the app sees "last successful run" rather than "last data change".
- `reports-meta.json` — shard manifest.
- `reports-<house>-NN.json` — sharded records (newest-first).
- `manifest.json` — text-shard manifest.
- `texts-meta.json` + `texts-NN.json` — bundled text shards.
- `audit.json` — record health: counts of with-text / empty / error / never-attempted.

## Independence Principle

This repo does not import from SansadSaar, parliamentwatch-data, or the netas/indiavotes Astro apps. Cross-corpus shared code (HTTP layer, rate-limit handling, text-shard packing, idempotent write) lives in this repo's local modules.

## Provenance

Code carried over from `NakliTechie/sansadsaar-proceedings-data` (which itself carried the LS scrapers from earlier `parliamentwatch-data`). The split into four wrappers landed when this repo was bootstrapped (2026-05-18).

## Credits

- Indian Parliament data via [sansad.in](https://sansad.in).
