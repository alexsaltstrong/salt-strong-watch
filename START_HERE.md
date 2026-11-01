# Salt Strong WATCH VNext - clean replacement

**This package is ready to upload, but it has NOT been pushed to your GitHub account.**
It will not crawl SaltStrong.com until you manually run the refresh action or the next scheduled run.

## First: protect your existing catalog and history

1. In `https://github.com/alexsaltstrong/salt-strong-watch`, use **Code > Download ZIP** to back up the repo before editing.
2. In GitHub's Code tab, check whether `catalog.json` exists. **Keep that file. Do not overwrite or delete it.** The replacement package intentionally does not include it.
3. Do NOT delete the repository itself. Git history and Pages settings are useful recovery options.

## Recommended install: GitHub Desktop (easiest for several files)

1. Open GitHub Desktop and **clone** `alexsaltstrong/salt-strong-watch`.
2. Unzip this VNext package on your Mac.
3. Copy the **contents** of `SaltStrong_WATCH_VNext_Repo` into the cloned repository folder, preserving `.github/workflows/watch-sync.yml` and `assets/`.
4. Replace matching files. **DO NOT DELETE `catalog.json`**. Do not copy the package's outer folder as a nested folder.
5. In GitHub Desktop, review the changes. You should see a new `styles.css`, updated `index.html`, `app.js`, extractor scripts, tags, tests, and one updated `watch-sync.yml`.
6. You can safely delete old, unused scripts and the old experimental `.github/workflows/watch-last100-test.yml` after you confirm that this new setup runs. **Do not delete the current `catalog.json`.** `pages-build-deployment` may be automatically managed by GitHub; leave it alone.
7. Commit with message `WATCH VNext clean rebuild` and **Push origin**.

If you prefer GitHub's website: use **Add file > Upload files** to replace the files in the repo root and `assets/`; replace `.github/workflows/watch-sync.yml` separately through its pencil editor. The workflow path must remain exact.

## Important: ensure Pages uses GitHub Actions

Go to repository **Settings > Pages > Build and deployment > Source**, select **GitHub Actions**.

## Why the old version kept losing videos

Older versions rebuilt the 10-video catalog during ordinary app/style pushes. In VNext:
- A `push` containing app/style/workflow changes **only deploys the committed `catalog.json`**. No WordPress crawl.
- Manual **Run workflow** with `refresh_catalog=true` scans the chosen recent article count, enriches tags, merges records without deleting earlier entries, commits `catalog.json` to Git history, and deploys.
- Scheduled daily runs do the same latest-100 scan and merge.
- A backup and audit are uploaded for every import.

## Run a 100-article import

1. GitHub repository > **Actions**.
2. Select **WATCH - deploy and optional article refresh**.
3. Choose **Run workflow** > `refresh_catalog=true` > `scan_limit=100` > Run.
4. Inspect `last100-summary.md` and `merge-summary.md` in the job summary.
5. Under the run's artifacts, download `watch-refresh-audit-backup` for skipped posts and new tag suggestions.
6. Open `https://alexsaltstrong.github.io/salt-strong-watch/` after successful deploy.

If `catalog.json` does not exist in the repository, the new workflow first tries to retrieve the old published catalog. If it cannot retrieve and validate it, **the workflow refuses to deploy**, preventing silent data loss. In that case, download the previously published `catalog.json` manually and commit it to the root of your repo (or copy the sample JSON as a deliberate fresh-start bootstrap if you choose to discard old records).

## What WATCH VNext does

- Both thumbnail **and video title** are actual buttons that open the WATCH popup. Neither links to WordPress.
- **Read full article** is a separate button inside the popup.
- Videos use verified YouTube IDs and i.ytimg.com thumbnails. Vimeo-only/text-only are skipped by the importer.
- The published `catalog.json` accumulates successful records; no deletion when an article is absent from the latest-100 scan.
- Gear links are extracted from in-article Fish Strong products and preserved when an update lacks gear.
- Article text is used to produce **new WATCH tags** such as `Flooded Grass`, `Creek Mouths`, `Dock Lights`, `Popping Corks` and more, regardless of WordPress tags.
- Unrecognized recurring title/heading phrases go to `watch-tag-suggestions.json` for review, not into public filters until verified.
- Hearted favorites remain **browser-local** until you connect WordPress authentication/favorites. This update does not change member accounts.
- No WordPress posts, tags, users, access rules, or courses are modified.

## Known limitations

- The crawler relies on publicly accessible WordPress pages, and lazy embeds sometimes require a browser fallback. A successful scan is not proof that all page gear links were found.
- Content-based tags are transparent rule-based enrichment, **not an AI language-model classifier**. Tag suggestions require editorial review.
- The new clean UI has been tested locally; YouTube playback on the live HTTPS Pages domain still needs a final check after deployment.
- Some videos may block third-party embedding, even if their thumbnails load.

## Development test (optional)

```bash
python3 -m pip install -r requirements.txt
python3 -m unittest discover -s tests -v
python3 -m http.server 8000
```

The demo page falls back to `catalog.sample.json` if you don't have a `catalog.json`. It includes 10 IDs observed in the successful GitHub test. Running `http.server` only serves files, it does not import or update WordPress.
