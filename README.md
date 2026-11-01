# Salt Strong WATCH VNext

A public YouTube video discovery layer above Salt Strong's existing WordPress Articles. [Installation and restore guide](START_HERE.md).

## Architecture

- **Frontend:** `index.html`, `styles.css`, `app.js`, `assets/` (vanilla JS, static GitHub Pages)
- **Durable catalog:** `catalog.json` stored in Git history (intentionally **not** shipped in this replacement ZIP; keep your existing one)
- **Discovery:** `watch_last100.py` finds newest public WordPress `/articles/` via REST date-desc, falling back to archive if needed
- **Extractor:** `sync_catalog.py`, `populate_catalog.py` find the primary `[youtube_embed id="..."]`/rendered iframe, article metadata and eligible Fish Strong gear links
- **Enrichment:** `tagger.py`, `enrich_import.py` add topic tags from article text (never write WP tags) and propose new phrases for review
- **Safe merge:** `merge_watch_catalog.py` preserves previous rows, stable IDs and known-good gear URLs
- **Automation:** `.github/workflows/watch-sync.yml`; plain code pushes deploy only, manual/nightly refresh imports then deploys
- **Tests:** `python -m unittest discover -s tests -v`

## Safety

This repo is a prototype, not a replacement for SaltStrong.com. The importer only reads public pages. No logins, Memberium permissions, or premium course entitlements are assumed. Courses are displayed as discovery placeholders only. Hearts are stored locally in each visitor's browser, not their WordPress account. Do not treat crawler-detected product links as fully audited until checked for tracking and product availability.
