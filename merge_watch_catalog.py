#!/usr/bin/env python3
"""Safely merge a YouTube-only recent-articles import into the durable WATCH catalog.

Read-only to WordPress. Never delete old lessons during a recent-article import.
The merged catalog is written atomically.  A backup and audit are always created
before writing a successful merged catalog.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import tempfile
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit
from urllib.request import Request, urlopen

YOUTUBE_ID = re.compile(r'^[A-Za-z0-9_-]{11}$')
DEFAULT_PUBLISHED = 'https://alexsaltstrong.github.io/salt-strong-watch/catalog.json'


def canonical_url(value):
    """Canonical comparison key; never rewrite displayed article URLs."""
    parts = urlsplit(str(value or '').strip())
    host = (parts.hostname or '').lower()
    if host.startswith('www.'):
        host = host[4:]
    path = re.sub(r'/+', '/', parts.path or '/')
    if path != '/':
        path = path.rstrip('/')
    return f'{host}{path}'.lower() if host else ''


def valid_youtube(row):
    video = row.get('video') or {}
    return (isinstance(video, dict) and video.get('provider') == 'youtube'
            and bool(YOUTUBE_ID.fullmatch(str(video.get('id', '')))))


def validate_catalog(data, label):
    if not isinstance(data, dict) or not isinstance(data.get('items'), list):
        raise ValueError(f'{label} must contain an items array')
    seen = set()
    for n, row in enumerate(data['items'], 1):
        if not isinstance(row, dict) or not row.get('title') or not row.get('url'):
            raise ValueError(f'{label} row {n} missing title/url')
        key = canonical_url(row['url'])
        if not key or not key.startswith('saltstrong.com/'):
            raise ValueError(f'{label} row {n} has unexpected source URL: {row["url"]}')
        if key in seen:
            raise ValueError(f'{label} contains duplicate article: {row["url"]}')
        seen.add(key)
    return data


def read_base(path, published_url):
    if path.is_file():
        base = json.loads(path.read_text(encoding='utf8'))
        return validate_catalog(base, 'Current catalog'), 'repository catalog.json'
    req = Request(published_url, headers={'User-Agent': 'SaltStrong-Watch-Catalog-Backup/1.0', 'Accept':'application/json'})
    try:
        with urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode('utf8'))
    except Exception as exc:
        raise RuntimeError('No local catalog.json and unable to fetch currently deployed catalog. '
                           'Refusing to overwrite existing WATCH lessons. ' + str(exc)) from exc
    return validate_catalog(data, 'Live catalog'), f'live site {published_url}'


def merge(base, imported):
    validate_catalog(base, 'Existing catalog')
    validate_catalog(imported, 'Imported catalog')
    if not base['items']:
        raise ValueError('Existing catalog empty: refusing to replace without manual review')
    if not imported['items']:
        raise ValueError('No imported videos: refusing to publish')
    current = {canonical_url(row['url']): dict(row) for row in base['items']}
    before_keys = set(current)
    added = updated = 0
    warnings = []
    for row in imported['items']:
        if not valid_youtube(row):
            raise ValueError('Import contains non-YouTube or missing video ID: ' + str(row['url']))
        key = canonical_url(row['url'])
        new = dict(row)
        if key in current:
            prev = current[key]
            combined = {**prev, **new}
            # Preserve identity for browser-stored hearts and deep link stability.
            combined['id'] = prev.get('id') or new.get('id')
            # Keep editorial/known-good recommendations if scraper found no gear.
            if not new.get('gear') and prev.get('gear'):
                combined['gear'] = prev['gear']
            if not new.get('author') or new.get('author') == 'Salt Strong':
                combined['author'] = prev.get('author') or new.get('author')
            if not new.get('date'):
                combined['date'] = prev.get('date', '')
            if not new.get('excerpt'):
                combined['excerpt'] = prev.get('excerpt', '')
            if not new.get('search_text'):
                combined['search_text'] = prev.get('search_text', '')
            if not new.get('image_fallback'):
                combined['image_fallback'] = prev.get('image_fallback', '')
            # Merge AI/heuristic tags with existing hand-picked tags.
            tags = list(dict.fromkeys([*prev.get('tags', []), *new.get('tags', [])]))
            combined['tags'] = tags[:12]
            current[key] = combined
            updated += 1
        else:
            current[key] = new
            added += 1
    if not before_keys.issubset(current):
        raise AssertionError('An existing article would be dropped; refusing to publish')
    ids = {}
    for row in current.values():
        id_ = str(row.get('id', ''))
        if id_ in ids:
            warnings.append(f'ID collision between {ids[id_]} and {row["url"]}: {id_}')
        ids[id_] = row['url']
    ordered = sorted(current.values(), key=lambda x:(str(x.get('date') or ''),str(x.get('title') or '')),reverse=True)
    stats = {'total': len(ordered), 'previous':len(before_keys),
             'imported':len(imported['items']), 'added':added, 'updated':updated,
             'retained_not_in_recent_scan':len(before_keys)-updated,
             'recent_articles_scanned':imported.get('stats',{}).get('articles_scanned'),
             'recent_articles_skipped':imported.get('stats',{}).get('skipped')}
    out = {'generated_at':dt.datetime.now(dt.timezone.utc).isoformat(),
           'source':'wordpress_recent_articles_merged', 'demo':False,
           'items':ordered,'stats':stats}
    return out, {'stats':stats,'warnings':warnings}


def atomic_json(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile('w',dir=path.parent,prefix='watch-',suffix='.tmp',
                                     encoding='utf8',delete=False) as tmp:
        json.dump(obj,tmp,ensure_ascii=False,indent=2)
        tmp.write('\n')
        tmp_path=tmp.name
    os.replace(tmp_path,path)


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--current',default='catalog.json')
    p.add_argument('--imported',default='last100-catalog.json')
    p.add_argument('--backup',default='catalog-before.json')
    p.add_argument('--audit',default='last100-merge-audit.json')
    p.add_argument('--summary',default='last100-merge-summary.md')
    p.add_argument('--published-url',default=DEFAULT_PUBLISHED)
    args=p.parse_args()
    target=Path(args.current)
    base,origin=read_base(target,args.published_url)
    new=json.loads(Path(args.imported).read_text(encoding='utf8'))
    output,audit=merge(base,new)
    audit['base_source']=origin
    atomic_json(Path(args.backup),base)
    atomic_json(Path(args.audit),audit)
    atomic_json(target,output)
    stats=audit['stats']
    summary=(f'## WATCH import and publish result\n\n'
             f'- Existing catalog: **{stats["previous"]}**\n'
             f'- Recent articles scanned: **{stats["recent_articles_scanned"]}**\n'
             f'- YouTube records imported: **{stats["imported"]}**\n'
             f'- New articles added: **{stats["added"]}**\n'
             f'- Existing articles refreshed: **{stats["updated"]}**\n'
             f'- Previous records retained: **{stats["retained_not_in_recent_scan"]}** (outside current scan)\n'
             f'- Total WATCH videos after merge: **{stats["total"]}**\n'
             f'- Base catalog source: {origin}\n\n'
             'Earlier entries are preserved; no older videos are deleted by this operation.\n')
    Path(args.summary).write_text(summary,encoding='utf8')
    print(summary,flush=True)
    if audit['warnings']:
        for warning in audit['warnings']:
            print('WARNING:',warning,flush=True)


if __name__=='__main__':
    main()
