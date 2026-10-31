#!/usr/bin/env python3
"""Populate Salt Strong WATCH from public article players, preserving sample gear.

Read-only to WordPress. The output JSON is safe to publish only after verifying
that every article included is public (seed contains 10 public articles).
"""
import argparse
import datetime as dt
import json
import re
import sys
from pathlib import Path
from urllib.parse import urlparse

from bs4 import BeautifulSoup
from sync_catalog import SESSION, get, parse_article, extract_video, extract_video_candidates

VIDEO_ID = re.compile(r'^[A-Za-z0-9_-]{11}$')


def valid(v):
    return bool(isinstance(v, dict) and (
        (v.get('provider') == 'youtube' and VIDEO_ID.fullmatch(str(v.get('id', '')))) or
        (v.get('provider') == 'vimeo' and re.fullmatch(r'\d{5,}', str(v.get('id', ''))))
    ))


def render_article(url):
    """Return DOM plus real embedded player URLs from a headless browser."""
    from playwright.sync_api import sync_playwright
    found = []
    def record(text):
        for candidate in extract_video_candidates(str(text).replace('\\/', '/')):
            if valid(candidate) and candidate not in found:
                found.append(candidate)
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=['--no-sandbox'])
        context = browser.new_context(
            viewport={'width': 1380, 'height': 900},
            user_agent='Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36'
        )
        page = context.new_page()
        page.on('request', lambda request: record(request.url) if ('youtube.com/embed/' in request.url or 'youtube-nocookie.com/embed/' in request.url or 'player.vimeo.com/video/' in request.url) else None)
        try:
            page.goto(url, wait_until='domcontentloaded', timeout=45000)
            page.wait_for_timeout(1500)
            # Wordpress shortcode players can lazy-load below the fold.
            for fraction in (0.22, 0.45, 0.7, 1.0):
                page.evaluate('(f) => window.scrollTo(0, document.body.scrollHeight*f)', fraction)
                page.wait_for_timeout(800)
            # Prioritize actual iframe targets over JS snippets/recommendations.
            iframe_urls = page.locator('article iframe, main iframe, .entry-content iframe, .article-content iframe').evaluate_all(
                '(els) => els.map(e => e.src || e.dataset.src || e.dataset.lazySrc || "").filter(Boolean)'
            )
            dom = page.content()
            for url in iframe_urls:
                record(url)
            for frame in page.frames:
                if frame != page.main_frame: record(frame.url)
            return dom, found
        finally:
            browser.close()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--seed', default='catalog.sample.json')
    ap.add_argument('--output', default='catalog.json')
    ap.add_argument('--audit', default='import-audit.json')
    ap.add_argument('--no-browser', action='store_true', help='Skip browser fallback for unit/local testing')
    a = ap.parse_args()
    seed = json.loads(Path(a.seed).read_text(encoding='utf8'))
    rows = seed['items']
    # Preserve previously verified IDs across incremental runs, even when an
    # article is temporarily unreachable. Never discard a working player.
    prior_path = Path(a.output)
    if prior_path.exists():
        try:
            prior = json.loads(prior_path.read_text(encoding='utf8'))
            prior_by_url = {i.get('url'): i for i in prior.get('items', [])}
            for item in rows:
                previous_item = prior_by_url.get(item.get('url'), {})
                if valid(previous_item.get('video')):
                    item['video'] = previous_item['video']
                    item['video_source'] = previous_item.get('video_source', 'prior-catalog')
                    if item['video']['provider'] == 'youtube':
                        item['image'] = 'https://i.ytimg.com/vi/' + item['video']['id'] + '/hqdefault.jpg'
        except (OSError, ValueError, KeyError, TypeError):
            pass
    audit = []
    new_ids = 0
    for i, item in enumerate(rows, 1):
        url = item['url']
        previous = item.get('video') if valid(item.get('video')) else None
        video = None
        origin = None
        errors = []
        try:
            html = get(url)
            candidates = extract_video(html, BeautifulSoup(html, 'html.parser'))
            candidates = [v for v in candidates if valid(v)]
            if candidates:
                video = candidates[0]; origin = 'public-html'
                if len(candidates) > 1:
                    errors.append('Multiple video IDs in HTML; selected primary content candidate')
        except Exception as e:
            errors.append('HTTP: ' + str(e)[:180])

        if not video and not a.no_browser:
            try:
                dom, network = render_article(url)
                candidates = [v for v in extract_video(dom, BeautifulSoup(dom, 'html.parser')) if valid(v)]
                if candidates:
                    video = candidates[0]; origin = 'browser-dom'
                elif network:
                    video = network[0]; origin = 'browser-player-request'
                if len(candidates) > 1 or (not candidates and len(network) > 1):
                    errors.append('Multiple detected players; verify selected ID')
            except Exception as e:
                errors.append('Browser: ' + str(e)[:180])

        if video:
            if video != previous: new_ids += 1
            item['video'] = video
            item['video_source'] = origin
            if video['provider'] == 'youtube':
                item['image'] = 'https://i.ytimg.com/vi/' + video['id'] + '/hqdefault.jpg'
            # Keep existing article metadata, gear recommendations and fallback image.
        status = 'resolved' if valid(item.get('video')) else 'missing'
        audit.append({'title': item['title'], 'url': url, 'status': status,
                      'video': item.get('video'), 'source': origin or ('existing-seed' if previous else None),
                      'errors': errors})
        print(f'[{i}/{len(rows)}] {status}: {item["title"][:60]} | {item.get("video")}', flush=True)

    resolved = sum(valid(x.get('video')) for x in rows)
    result = {'generated_at': dt.datetime.now(dt.timezone.utc).isoformat(), 'source': 'public_article_import',
              'demo': False, 'items': rows, 'stats': {'total': len(rows), 'resolved': resolved, 'unresolved': len(rows)-resolved, 'new_video_ids': new_ids}}
    Path(a.output).write_text(json.dumps(result, indent=2, ensure_ascii=False)+'\n', encoding='utf8')
    Path(a.audit).write_text(json.dumps({'stats': result['stats'], 'results': audit}, indent=2, ensure_ascii=False)+'\n', encoding='utf8')
    print('RESULT:', json.dumps(result['stats']), flush=True)
    if resolved < len(rows):
        print('NOTE: unresolved articles remain. See import-audit.json. No IDs were guessed.', file=sys.stderr)
    # Fail if no improvement. The GitHub action can still upload the audit for diagnosis.
    if resolved <= 1:
        sys.exit(2)

if __name__ == '__main__': main()
