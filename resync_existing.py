#!/usr/bin/env python3
"""Refresh existing WATCH article URLs in safe, resumable batches.

Does not delete records. Uses the same public article extractor as the normal
newest-post crawl. Output is a temporary import for the standard safe merge.
"""
from __future__ import annotations
import argparse
import json
import tempfile
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import urlsplit

from watch_last100 import run
from merge_watch_catalog import canonical_url, validate_catalog


def choose_urls(catalog,limit,offset=0):
    validate_catalog(catalog,'Existing WATCH catalog')
    urls=[]; seen=set()
    for row in sorted(catalog['items'],key=lambda item:(item.get('date') or '',item.get('url') or ''),reverse=True):
        url=row.get('url','')
        parsed=urlsplit(url)
        if parsed.scheme!='https' or parsed.hostname not in ('www.saltstrong.com','saltstrong.com'):
            continue
        key=canonical_url(url)
        if key not in seen:
            seen.add(key);urls.append(url)
    return urls[offset:offset+limit],len(urls)


def main():
    parser=argparse.ArgumentParser(description='Re-extract already saved WATCH articles, preserving records')
    parser.add_argument('--current',default='catalog.json')
    parser.add_argument('--limit',type=int,default=25,help='Records in this batch (1-200)')
    parser.add_argument('--offset',type=int,default=0,help='Start after N latest records, for larger catalogs')
    parser.add_argument('--output',default='resync-catalog.json')
    parser.add_argument('--audit',default='resync-audit.json')
    parser.add_argument('--summary',default='resync-summary.md')
    parser.add_argument('--selection',default='resync-selection.json')
    parser.add_argument('--no-browser',action='store_true')
    parser.add_argument('--delay',type=float,default=0.35)
    args=parser.parse_args()
    if not 1<=args.limit<=200:parser.error('--limit must be 1..200')
    if args.offset<0:parser.error('--offset must be >= 0')
    base=json.loads(Path(args.current).read_text(encoding='utf8'))
    urls,total=choose_urls(base,args.limit,args.offset)
    if not urls:raise RuntimeError('Resync selection empty; check offset and catalog.json')
    Path(args.selection).write_text(json.dumps({'total_existing':total,'selected':len(urls),'offset':args.offset,'urls':urls},indent=2)+'\n',encoding='utf8')
    with tempfile.TemporaryDirectory(prefix='watch-resync-') as temp:
        urls_path=Path(temp)/'urls.txt'
        urls_path.write_text('\n'.join(urls)+'\n',encoding='utf8')
        run(SimpleNamespace(limit=len(urls),urls_file=str(urls_path),max_pages=0,
                            no_browser=args.no_browser,delay=args.delay,output=args.output,
                            audit=args.audit,summary=args.summary))
    report=Path(args.summary)
    report.write_text(report.read_text(encoding='utf8')
                      .replace(f'# Salt Strong WATCH: last {len(urls)} public Articles test',
                               '# Salt Strong WATCH: resync existing Articles')
                      .replace('Experiment only. The live `catalog.json` was not modified.',
                               'Extraction stage complete; the subsequent safe merge updates `catalog.json` after validation.'),
                      encoding='utf8')
    with report.open('a',encoding='utf8') as f:
        f.write(f'\nExisting records in catalog: **{total}**. Selected **{len(urls)}** at offset **{args.offset}**.\n')
        if args.offset+len(urls)<total:
            f.write(f'Next batch starts at offset **{args.offset+len(urls)}**.\n')
        f.write('Failed/skipped articles remain unchanged in the merge; inspect audit.\n')
    print(f'RESYNC selected {len(urls)}/{total} existing article URLs starting at {args.offset}',flush=True)

if __name__=='__main__':main()
