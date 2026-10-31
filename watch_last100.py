#!/usr/bin/env python3
"""Read-only experiment: newest 100 public Salt Strong Articles, YouTube only.

Writes separate experiment data and audit; never touches the live catalog.json.
Uses the existing, previously tested WATCH long-form YouTube extractor.
"""
from __future__ import annotations
import argparse
import datetime as dt
import json
import re
import sys
import time
from collections import Counter
from pathlib import Path
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup
from sync_catalog import BASE, archive_links, extract_video, get, parse_article, same_site_url
from populate_catalog import render_article, valid

ARCHIVE_ROOTS = ("/articles/", "/fishing-tips/")
YOUTUBE_ID = re.compile(r"^[A-Za-z0-9_-]{11}$")


def unique(urls):
    result = []
    seen = set()
    for u in urls:
        url = u.split('#', 1)[0].split('?', 1)[0]
        if url not in seen and same_site_url(url):
            result.append(url)
            seen.add(url)
    return result


def discover_rest(limit):
    """Only WordPress Articles, newest publish date first. Custom route may be blocked."""
    paths = ("articles", "article")
    errors=[]
    for post_type in paths:
        try:
            urls=[]
            page=1
            while len(urls) < limit:
                per_page=min(100, limit-len(urls))
                endpoint=(f"{BASE}/wp-json/wp/v2/{post_type}?status=publish&per_page={per_page}"
                          f"&page={page}&orderby=date&order=desc&_fields=link,date,status")
                result=get(endpoint, json_mode=True)
                if not isinstance(result, list):
                    raise ValueError("Expected a list of public article records")
                if not result:break
                for record in result:
                    if record.get("status", "publish") == "publish":
                        urls.append(record.get("link", ""))
                if len(result) < per_page:break
                page+=1
            urls=unique(urls)
            if urls:
                return urls[:limit],f"WordPress REST /{post_type} (date descending)",errors
        except Exception as exc:
            errors.append(f"REST {post_type}: {str(exc)[:180]}")
    return [],None,errors


def archive_article_links(page_html):
    """Prefer article cards in the archive's main listing, avoiding menus/sidebar."""
    soup=BeautifulSoup(page_html,"html.parser")
    article_cards=soup.select('main article, .content-area article, .post-list article, .article-list article, .archive article')
    if article_cards:
        urls=[]
        for card in article_cards:
            anchors=card.select('h2 a[href], h3 a[href], .entry-title a[href], a[href]')
            for a in anchors:
                url=urljoin(BASE,a['href'])
                if same_site_url(url):
                    urls.append(url)
                    break
        if urls:
            return unique(urls)
    main=soup.select_one('main, #main, #content, .content-area')
    if main:
        urls=[urljoin(BASE,a['href']) for a in main.select('a[href]')]
        urls=unique(urls)
        if urls:return urls
    # Last resort. This may include recommendations; audit records fallback mode.
    return archive_links(page_html)


def discover_archive(limit, max_pages=15):
    errors=[]
    for root in ARCHIVE_ROOTS:
        urls=[]
        mode=None
        for n in range(1,max_pages+1):
            url=f"{BASE}{root}"+(f"page/{n}/" if n>1 else "")
            try:
                html=get(url)
                batch=archive_article_links(html)
                if not batch:break
                before=len(urls)
                urls=unique(urls+batch)
                if len(urls)==before:break
                mode=f"Public archive {root} (archive order, verify publication dates)"
                print(f"Archive page {n}: {len(batch)} links, {len(urls)} unique",flush=True)
                if len(urls)>=limit:break
                time.sleep(.25)
            except Exception as exc:
                errors.append(f"{url}: {str(exc)[:150]}")
                break
        if urls:
            return urls[:limit],mode,errors
    return [],None,errors


def choose_youtube(page_html, url, use_browser=True):
    soup=BeautifulSoup(page_html,"html.parser")
    hits=extract_video(page_html, soup)
    yt=[v for v in hits if v.get('provider')=='youtube' and YOUTUBE_ID.fullmatch(str(v.get('id','')))]
    source='server-html'
    warnings=[]
    if not yt and use_browser:
        try:
            dom,network=render_article(url)
            hits2=extract_video(dom,BeautifulSoup(dom,'html.parser'))
            yt=[v for v in hits2 if v.get('provider')=='youtube' and YOUTUBE_ID.fullmatch(str(v.get('id','')))]
            if yt:
                source='browser-dom'
            else:
                yt=[v for v in network if v.get('provider')=='youtube' and YOUTUBE_ID.fullmatch(str(v.get('id','')))]
                if yt:
                    source='browser-network'
                    warnings.append('Network-only ID: confirm it belongs to the main article player')
        except Exception as exc:
            warnings.append(f'Browser fallback failed: {str(exc)[:160]}')
    if len(yt)>1:
        warnings.append('Multiple YouTube IDs found; first selected, manual review advised')
    return (yt[0] if yt else None),source,warnings


def run(args):
    limit=args.limit
    if args.urls_file:
        urls=unique([s.strip() for s in Path(args.urls_file).read_text(encoding='utf-8').splitlines() if s.strip() and not s.lstrip().startswith('#')])[:limit]
        origin='supplied test URL list'
        discovery_errors=[]
    else:
        urls,origin,discovery_errors=discover_rest(limit)
        if not urls:
            urls,origin,archive_errors=discover_archive(limit,args.max_pages)
            discovery_errors.extend(archive_errors)
    if not urls:
        raise RuntimeError('No published Articles were discovered. See discovery_errors in job logs.')

    items=[]
    audit=[]
    counts=Counter()
    for idx,url in enumerate(urls,1):
        reason=''
        warnings=[]
        video=None
        item=None
        method=''
        try:
            html=get(url)
            item,reason=parse_article(url,html)
            # The original parser supports Vimeo too; YouTube-only mode overrides it.
            if reason=='access-restricted marker':
                reason='restricted article'
            else:
                video,method,warnings=choose_youtube(html,url,not args.no_browser)
                if video and valid(video):
                    if not item:
                        # parse_article normally returns a record when any video exists.
                        # If it failed because video is in a network-only player, use the
                        # rendered HTML or an explicit error rather than fabricate metadata.
                        if not args.no_browser:
                            try:
                                dom,network=render_article(url)
                                item,_=parse_article(url,dom)
                            except Exception as exc:
                                warnings.append(f'Rendered metadata unavailable: {str(exc)[:100]}')
                    if item:
                        item['video']=video
                        item['image']=f'https://i.ytimg.com/vi/{video["id"]}/hqdefault.jpg'
                        item['video_source']=method
                        item['needs_review']=bool(warnings) or item.get('needs_review',False)
                        reason=''
                    else:
                        reason='unable to parse article metadata'
                else:
                    reason='no YouTube ID found (text-only, Vimeo-only or inaccessible player)'
        except Exception as exc:
            reason=f'fetch or parsing error: {str(exc)[:170]}'
        if item and not reason and video:
            counts['included']+=1
            items.append(item)
            status='included'
        else:
            status='skipped'
            counts[reason or 'unknown']+=1
        audit.append({'article':url,'status':status,'reason':reason,'video':video,
                      'method':method,'warnings':warnings,'title':item.get('title') if item else None})
        print(f'[{idx}/{len(urls)}] {status.upper():8} {url} '+(f'YT={video["id"]}' if video else reason),flush=True)
        time.sleep(max(0,args.delay))

    items.sort(key=lambda x:x.get('date') or '',reverse=True)
    stamp=dt.datetime.now(dt.timezone.utc).isoformat()
    catalog={'generated_at':stamp,'source':f'public_last_{limit}_articles_experiment','demo':False,
             'experiment_only':True,'items':items,
             'stats':{'articles_scanned':len(urls),'youtube_videos':len(items),'skipped':len(urls)-len(items)}}
    audit_result={'generated_at':stamp,'discovery':origin,'discovery_errors':discovery_errors,
                  'stats':dict(catalog['stats']), 'skipped_by_reason':{k:v for k,v in counts.items() if k!='included'},
                  'results':audit}
    Path(args.output).write_text(json.dumps(catalog,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    Path(args.audit).write_text(json.dumps(audit_result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    summary=(f'# Salt Strong WATCH: last {limit} public Articles test\n\n'
             f'- Discovery: {origin}\n'
             f'- Articles scanned: **{len(urls)}**\n'
             f'- YouTube videos included: **{len(items)}**\n'
             f'- Skipped: **{len(urls)-len(items)}**\n\n'
             '## Skipped reasons\n\n'+''.join(f'- {reason}: {count}\n' for reason,count in audit_result['skipped_by_reason'].items())+'\n'
             'Experiment only. The live `catalog.json` was not modified. '
             'If discovery fell back to archive order, review publication dates in the audit to confirm the sample covers the actual newest 100 posts.\n')
    Path(args.summary).write_text(summary,encoding='utf-8')
    print('RESULT:',json.dumps(audit_result['stats']),flush=True)
    print('DISCOVERY:',origin,flush=True)
    if discovery_errors:print('Discovery warnings:',discovery_errors,flush=True)
    if len(urls)!=limit: print(f'WARNING: Discovered only {len(urls)} of requested {limit} articles.',flush=True)
    if not items: raise RuntimeError('No playable YouTube video IDs were found. Inspect the audit before broadening the crawl.')
    return catalog,audit_result


def main():
    ap=argparse.ArgumentParser(description='Read-only last-100 WordPress Articles to YouTube-only WATCH catalog')
    ap.add_argument('--limit',type=int,default=100)
    ap.add_argument('--max-pages',type=int,default=15)
    ap.add_argument('--no-browser',action='store_true',help='Skip Chromium fallback')
    ap.add_argument('--urls-file',help='Optional URL list for local test')
    ap.add_argument('--delay',type=float,default=0.35,help='Seconds between requests to Salt Strong')
    ap.add_argument('--output',default='last100-catalog.json')
    ap.add_argument('--audit',default='last100-audit.json')
    ap.add_argument('--summary',default='last100-summary.md')
    args=ap.parse_args()
    if not 1<=args.limit<=200:ap.error('--limit must be 1 to 200')
    run(args)

if __name__=='__main__':main()
