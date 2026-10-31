# Salt Strong WATCH: Proof of Concept

A **read-only** prototype of a video discovery layer over Salt Strong's existing article library. It does not modify WordPress, courses, members, posts, or gear links.

## Open the design

Open `index.html` in a web browser. The bundled `seed.js` provides sample data even when opening from a local file. The sample includes **10 actual public Salt Strong article titles, URLs, authors and manually identified topics**. The original demo thumbnails often point to expired or unavailable WordPress images. WATCH now prefers the real YouTube CDN thumbnail **when a verified YouTube video ID is available**, then the article image, and finally a bundled, clearly labeled preview graphic. One sample YouTube ID (the tides lesson) was verified from existing editorial context; other unverified IDs are deliberately left blank rather than fabricated.

Explore: topic chips, search for "oyster bars" / "popping cork" / "leader", coach filters, save lessons, browse view, mobile quick-browse concept, course discovery, and watch details linking back to original blogs.

The sample does **not** pretend to play videos when the actual embed URL hasn't been verified. On a genuine synced record with a YouTube/Vimeo ID, the watch detail automatically uses the provider's embedded player.

## Brand styling, readable interface, and clickable gear

The revised UI follows Salt Strong’s 2023 brand manual: primary navy `#152c52`, white backgrounds, light blue `#d6e6f2`, and orange `#ff5100` sparingly for actions. The actual unmodified Salt Strong primary logo is derived from the supplied manual. Rubik is requested from Google Fonts with system fallbacks, **without packaging/distributing brand font files**. Body and navigation sizes, card titles, metadata, and minimum button targets are enlarged for desktop and mobile readability.

In the lesson modal, **Featured gear** entries are links. The sample uses several directly verified Fish Strong product URLs; when a gear URL could not be verified, the entry clearly says **See in blog**, linking to its source article instead of inventing a product destination. The `sync_catalog.py` extractor retains gear URLs from each article when the layout supports it. Before production rollout, verify store tracking / attribution / redirects against your actual checkout flow.

For imported YouTube posts, the video ID drives `https://i.ytimg.com/vi/<ID>/hqdefault.jpg` (the platform thumbnail). Vimeo posts use article thumbnails until a verified Vimeo thumbnail endpoint and entitlement checks are configured. If previews cannot connect to the internet, a bundled graphic appears instead of a broken image. **The sample catalog is not a fully synced production feed yet.**

## Run a local site (optional)

```bash
cd salt-strong-watch
python3 -m http.server 8080
```

Open `http://localhost:8080/`. When a generated `catalog.json` is present, the prototype uses it instead of sample data.

## Automate the catalog (technical proof of concept)

Install dependencies on a trusted machine with outbound access:

```bash
python3 -m pip install requests beautifulsoup4
python3 sync_catalog.py --mode archive --pages 2 --limit 30 --output catalog.json
```

- Archive mode reads public articles linked from `https://www.saltstrong.com/fishing-tips/` and subsequent `/page/N/` URLs. It extracts YouTube/Vimeo embeds, title, thumbnail, description, article URL, author, basic taxonomy, and featured gear URLs when detectable.
- REST mode is also supported: `--mode rest --post-type articles` **only if the WordPress REST custom post-type endpoint exists and is permitted**. The URL needs verification against the actual production configuration.
- Daily incremental run: re-scan the first 2 archive pages and merge the refreshed records with the previous `catalog.json`.
- One-time backfill: run with `--pages` set high (e.g. 390) and `--limit 0`, **after** confirming rate limits, source reliability, allowed content, and operational approval. Chunk the backfill rather than running aggressively against production.
- The script does not write to WordPress; it only writes its local `catalog.json` file. Missing/restricted/ambiguous embeds are recorded or excluded. `needs_review=true` flags posts with multiple detected video IDs.
- The importer uses heuristic tagging. A later AI-enrichment pass can use a fixed taxonomy, content-derived metadata, and confidence thresholds; it should not change the blog's WordPress tags.

**Important:** This importer is an implementation starting point, not a verified live integration. The public WP REST endpoint was returning 403/was inaccessible from the inspection environment, and the source HTML could not be programmatically fetched from the build environment, so selectors and parsing must be tested against production responses before enabling autopilot. Some video embeds may be loaded client-side or via custom shortcodes; those need adapter rules. Confirm robots/access policy with the site owner.

## Best path to SaltStrong.com/watch

1. Create an independent WordPress page route `/watch/` and load the WATCH front-end template there (or reverse-proxy a decoupled front end while retaining the same URL).
2. Generate a cached, public-only `catalog.json` via scheduled server-side import or a small WordPress integration that is triggered on article publication. Keep the index private until all course and access rules are confirmed.
3. Enrich with a **controlled** taxonomy: species, structure, conditions, technique, gear, coach, format. Store in separate WATCH metadata, not existing post tags.
4. Keep each video's original WordPress article as the canonical written page. On a WATCH watch-detail, render approved player embeds and gear recommendations that deep-link to verified Fish Strong products or original article links.
5. Keep courses in a separate entitlement-aware feed. Never assume a video is public solely because an embed URL exists; only verified public blog content belongs in the public catalog. Course access and purchase states must come from the existing course/member system, not heuristic text matching.
6. Compare a randomized WATCH-entry experience with the existing blog journey. Track search-to-play, play-to-article, gear CTR, member/course clicks, revenue per visitor, and organic/search impact. Avoid changing canonical/indexing until validated.

## Before real deployment

- Confirm whether `/articles/` is a public WordPress custom post type and what published public JSON feed is available. May need a small authenticated read-only WP connector if the existing REST API blocks unauthenticated traffic.
- Test legacy Vimeo embeds/shortcodes, iframe patterns, multiple-video articles, missing thumbnails and protected content.
- Map actual coach bylines, gear blocks, short clips, and course entitlements using confirmed source fields.
- Harden HTML sanitation, rate limiting, caching, API authentication (if required), video privacy and accessibility; add monitoring of import failures.
- Use real analytics and conversion experiments before redirecting any existing SEO URLs.


## V3 image-handling update
- Every article starts with a different, bundled (inline SVG) Salt Strong WATCH **preview cover**. This ensures all 10 cards render something meaningful even when a sandbox browser blocks external images. These are deliberately labeled as previews, not passed off as original YouTube thumbnails.
- The browser then tries YouTube's original thumbnail sizes **when the video ID is verified**; otherwise it tries the actual article image. If a remote image loads, it replaces the preview cover. Same logic in category rows, search, Quick Browse, hero and modal.
- The sample catalog still knows the YouTube ID for only one record. The other nine articles do **not** have verified YouTube IDs in this sample. The production importer extracts IDs from actual WordPress embed HTML, then pulls the YouTube thumbnail automatically.
- A verified video now opens the detail overlay with the thumbnail visible and an explicit **Play video** button before embedding the external player.
- No production WordPress changes were made. The offline preview covers are a usability improvement, not a replacement for extracting actual YouTube thumbnail URLs.

## V4: WordPress `[youtube_embed id="..."]` shortcode integration

**Important discovery from Salt Strong:** The original `articles` posts store YouTube IDs using the exact `[youtube_embed id="..."]` WordPress shortcode. This is now a primary extraction source in `sync_catalog.py`. It handles single/double/unquoted attributes, case variation, whitespace, and HTML-encoded source. It prioritizes the author's first shortcode rather than unrelated video links elsewhere on a page. The parsed video ID generates YouTube's real `i.ytimg.com/vi/<ID>/{maxresdefault,sddefault,hqdefault}.jpg` URLs used consistently in category cards, search, hero, and the watch popup. The browser checks each resolution before replacing the built-in readable preview cover.

**Live source access limitation:** The 10-article demo was created without API-level access to the site's *raw* WordPress `post_content`. Its publicly extracted article text does not expose YouTube shortcodes. Consequently, only the tides lesson's video ID has been verified in this demo. **The other nine covers are intentionally labeled previews, not original YouTube thumbnails.** When production receives raw WordPress post content or rendered iframes, the importer can resolve them automatically; no per-card image assignment is needed. If you have a safe WordPress export of raw post content, create a JSON object mapping each article URL to that content and run `--shortcode-map /path/to/posts.json` to include it during import. The export should contain only approved public posts; don't include paid course content. Numeric shortcode values that are not valid 11-character YouTube IDs require a separate lookup adapter, not a fabricated thumbnail URL.

The standalone HTML demo is intentionally bundled with immediate, locally rendered thumbnail covers so no category row or modal has a broken-image icon when remote images are blocked. Before a production launch, validate correct IDs, image availability, embeds, and permission filtering for each imported post.

## WordPress XML export: reliable way to make the actual videos play (V5)

Because Salt Strong stores video IDs in the original WordPress `post_content`
with `[youtube_embed id="..."]`, a WordPress **Articles** XML export is the
safest no-site-change way to repair a prototype without guessing IDs.

**In WordPress:** Tools > Export > Articles (custom post type; if present).
Choose **Published** articles and a limited date range if those options exist.
Download the XML, then use the read-only import script below. Avoid exporting
or sharing *All content* if it would include member-only posts, course content,
private user data, drafts, or other confidential content.

```bash
python3 -m pip install beautifulsoup4 requests
cd salt-strong-watch
python3 import_wordpress_export.py /path/to/salt-strong-export.xml \
  --seed catalog.sample.json --output catalog.json
python3 -m http.server 8080
```

Open http://localhost:8080/. Existing demo cards matching exported articles
will now use the correct YouTube IDs, i.ytimg.com original thumbnails, and
embedded video players. New public video articles appear as additional cards.
The script filters to published `articles` URLs and skips titles explicitly
labeled VIP/Insider-only. Review any privacy edge cases before a broad import.
This is a one-time proof-of-concept import; a small WordPress read-only catalog
feed is preferred for eventual ongoing automatic refresh.

**Important:** YouTube embeds can fail when the prototype is opened as a `file://`
document due to missing HTTP Referer. For final verification use a proper HTTP
origin (local test server) and preferably an HTTPS staging page, and check
embedding eligibility for each video. Source:
https://support.google.com/youtube/answer/171780

A WordPress XML export is user-supplied source data, not proof of successful
YouTube playback on all browsers. Validate at least Chrome, Safari and mobile.

## V6: long-form browser inspection, without WordPress exports

This release prioritizes the editor's original `[youtube_embed id="VIDEO_ID"]` shortcode and the rendered video player. It adds real-browser inspection for long-form article pages that render the YouTube player *after* page load. That is a fallback; the normal HTTP parser already recognizes iframe `src`, `data-src`, `srcdoc`, `lite-youtube` `videoid`, `data-youtube-id`, and several JS player configurations. The preferred ID is located within the article body so unrelated recommendation videos don't win.

You can test six **public long-form** URLs already listed in `longform-test-urls.txt`, without exporting WordPress:

```bash
python3 -m pip install requests beautifulsoup4 playwright
python3 -m playwright install chromium
python3 sync_catalog.py --mode urls \
  --urls-file longform-test-urls.txt --render-js --limit 6 \
  --output catalog.json --report import-audit.json
python3 -m http.server 8765
```

Open `http://localhost:8765/`. You can also try `START_WATCH_MAC.command` on macOS, which creates a local environment and starts the demo without VS Code. Python 3 and ordinary network access are required. If macOS blocks the downloaded script, open it in Terminal from the extracted directory with `bash START_WATCH_MAC.command`. The launcher installs its own dependencies locally and does not alter WordPress.

**Import audit:** `import-audit.json` lists each URL's import result, extraction method, and detected video ID. The WATCH page separately shows how many imported articles have IDs and playable embeds. Nothing is guessed or silently assigned when an ID is missing. Images for detected YouTube IDs are resolved automatically from `i.ytimg.com` in every card and watch popup. On localhost the player has a real HTTP origin, unlike opening the HTML via `file://`.

**Limitations:** This builder environment couldn't access live `www.saltstrong.com` raw HTML or run Chromium against the live site, so this release has *not* proved the six live video IDs. Unit tests passed using representative shortcode, iframe, lazy-load, and JavaScript player fixtures. Only an actual site-connected run can confirm whether the long-form shortcode renders a discoverable media ID. Some videos may forbid third-party embedding; validate on the final staging domain before rollout.
