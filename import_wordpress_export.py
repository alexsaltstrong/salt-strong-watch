#!/usr/bin/env python3
"""Build a WATCH catalog from a WordPress WXR XML export (read-only).

Use an export of the public Articles custom post type only. No WordPress API,
network access, or credentials are needed. Optional --seed will enrich the
existing demo catalog and keep entries not present in a small partial export.
"""
from __future__ import annotations

import argparse
import datetime as dt
import html
import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import urlparse

from bs4 import BeautifulSoup
from sync_catalog import extract_video, classify, extract_gear, clip

NS = {
    'content': 'http://purl.org/rss/1.0/modules/content/',
    'excerpt': 'http://wordpress.org/export/1.2/excerpt/',
    'wp': 'http://wordpress.org/export/1.2/',
    'dc': 'http://purl.org/dc/elements/1.1/',
}

def value(el, path, default=''):
    e=el.find(path, NS)
    return (e.text or '').strip() if e is not None else default


def article_record(post):
    post_type=value(post,'wp:post_type')
    status=value(post,'wp:status')
    # Exclude draft, private, course, page, and membership-only records.
    if post_type != 'articles' or status != 'publish':
        return None, 'not_public_article'
    url=value(post,'link').split('#')[0]
    parsed=urlparse(url)
    if parsed.scheme!='https' or parsed.hostname not in ('saltstrong.com','www.saltstrong.com') or not parsed.path.startswith('/articles/'):
        return None,'unexpected_url'
    title=html.unescape(value(post,'title'))
    if re.search(r'\b(insider[\s-]*only|vip[\s-]*only|members[\s-]*only)\b',title,re.I):
        return None,'access_restricted_title'
    raw=value(post,'content:encoded')
    soup=BeautifulSoup(raw,'html.parser')
    videos=extract_video(raw,soup,raw_post_content=raw)
    if not videos: return None,'missing_video'
    main_text=clip(soup.get_text(' ',strip=True),5000)
    excerpt=clip(BeautifulSoup(value(post,'excerpt:encoded'),'html.parser').get_text(' ',strip=True),250)
    date=value(post,'wp:post_date')[:10]
    if not re.fullmatch(r'\d{4}-\d{2}-\d{2}', date): date=''
    author=value(post,'dc:creator') or 'Salt Strong'
    # Combine editorial tags with conservative rule-based topic labels.
    wp_tags=[]
    for node in post.findall('category'):
        if node.get('domain') in ('category','post_tag','article_categories'):
            tag=html.unescape((node.text or '').strip())
            if tag and tag not in wp_tags:wp_tags.append(tag)
    tags=classify(title,excerpt,main_text)
    for tag in wp_tags:
        if tag not in tags and len(tags)<8:tags.append(tag)
    chosen=videos[0]
    thumbnail=(f'https://i.ytimg.com/vi/{chosen["id"]}/hqdefault.jpg'
               if chosen['provider']=='youtube' else '')
    return {
        'id':parsed.path.rstrip('/').split('/')[-1],
        'title':title,'url':url,'author':author,'date':date,
        'excerpt':excerpt or clip(main_text,240),
        'tags':tags,'search_text':main_text[:3500],
        'gear':extract_gear(soup),'video':chosen,
        'video_count':len(videos),'needs_review':len(videos)>1,
        'image':thumbnail,'image_fallback':'',
    },None


def main():
    ap=argparse.ArgumentParser(description='Read-only WordPress Articles XML export -> Salt Strong WATCH catalog')
    ap.add_argument('export',help='WordPress WXR .xml downloaded from Tools > Export > Articles')
    ap.add_argument('--seed',help='Optional existing WATCH JSON catalog to enrich rather than replace')
    ap.add_argument('--output',default='catalog.json')
    args=ap.parse_args()
    path=Path(args.export)
    if not path.is_file():sys.exit('Export XML not found')
    if path.stat().st_size>300_000_000:sys.exit('Export too large (>300 MB). Export Articles in date ranges.')
    entries={};counts={}
    try:
        # WordPress WXR can contain several generations of export namespaces.
        # In production, verify the export namespace version and update NS if needed.
        tree=ET.parse(path)
        for post in tree.findall('.//item'):
            record, reason=article_record(post)
            if record:entries[record['url']]=record
            else:counts[reason]=counts.get(reason,0)+1
    except ET.ParseError as e:sys.exit(f'Invalid WordPress XML: {e}')
    if args.seed:
        seed=json.loads(Path(args.seed).read_text(encoding='utf-8'))
        known={x['url']:x for x in seed.get('items',[]) if x.get('url')}
        for url,item in entries.items():
            if url in known:
                # Keep curated tags and verified gear destinations; update actual video identity.
                known[url].update({key:item[key] for key in ('video','image','video_count','needs_review')})
            else: known[url]=item
        entries=known
    items=sorted(entries.values(),key=lambda i:i.get('date',''),reverse=True)
    result={
        'generated_at':dt.datetime.now(dt.timezone.utc).isoformat(),
        'source':'wordpress_wxr_export','demo':False,
        'items':items,'stats':{'imported':len(items),'video_ready':sum(bool(i.get('video')) for i in items),'skipped':counts},
    }
    p=Path(args.output);p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8')
    print(json.dumps(result['stats'],indent=2))
    print('Wrote',p)
    if result['stats']['video_ready']==0:sys.exit('No video IDs found: check the XML export type/shortcode format')

if __name__=='__main__':main()
