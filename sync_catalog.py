#!/usr/bin/env python3
"""Read-only prototype sync from the public Salt Strong archive or WP REST API.

Run on a machine that can reach SaltStrong.com. No WordPress writes. This is a
starting point for deployment; verify selectors, access policies and video embeds
against real production HTML before scheduling an automated sync.
"""
from __future__ import annotations
import argparse
import datetime as dt
import html as html_lib
import json
import re
import sys
import time
from pathlib import Path
from urllib.parse import urljoin, urlparse, unquote

try:
    import requests
    from bs4 import BeautifulSoup
except ImportError:
    sys.exit("Install dependencies: python -m pip install requests beautifulsoup4")

BASE = "https://www.saltstrong.com"
UA = "SaltStrong-Watch-Prototype-Importer/0.1 (public content, read-only; contact site owner)"
SESSION = requests.Session()
SESSION.headers.update({"User-Agent": UA, "Accept": "text/html,application/json"})

TAXONOMY = {
    "Redfish": [r"\bredfish\b", r"\bred drum\b"],
    "Seatrout": [r"\bsea\s?trout\b", r"\bspeckled trout\b"],
    "Snook": [r"\bsnook\b"],
    "Flounder": [r"\bflounder\b"],
    "Marshes": [r"\bmarsh(?:es)?\b", r"\bcreek mouth"],
    "Oyster Bars": [r"\boyster\b", r"\bshell bar\b", r"\bshell reef\b"],
    "Tides": [r"\btide(?:s)?\b", r"\bhigh water\b", r"\bcurrent\b"],
    "Structure": [r"\bstructure\b", r"\bmarsh\b", r"\boyster\b", r"\bbridge\b", r"\bdock(?:s)?\b", r"\bpoints?\b"],
    "Lures": [r"\blures?\b", r"\bpaddletail", r"\btopwater\b", r"\bhardbait\b"],
    "Rigging": [r"\brigg?(?:ing)?\b", r"\bjighead", r"\bleader\b", r"\bknot\b"],
    "Gear Tests": [r"\btest(?:ed|ing|s)?\b", r"\bexperiment\b", r"\bcomparison\b"],
    "On The Water": [r"\bfishing report\b", r"\bon the water\b", r"\btrip\b"],
}

# The site's original WordPress posts often store videos as a shortcode:
#     [youtube_embed id="EEvy3gPSVIU"]
# The frontend receives a *rendered* page, where this shortcode may have been
# removed. For reliable import, pass the raw post_content from WordPress or its
# read-only catalog feed; rendered iframes remain a secondary path.
YOUTUBE_SHORTCODE = re.compile(r"\[youtube_embed\b(?P<attrs>[^\]]*)\]", re.I)
SHORTCODE_ID = re.compile(r"(?:^|\s)id\s*=\s*(?:\"([^\"]+)\"|'([^']+)'|([^\s\]]+))", re.I)

def extract_youtube_shortcode_ids(source):
    # WordPress/JSON exports can HTML-encode the shortcode punctuation.
    # Parse ID as an opaque string, then validate YouTube's 11-char ID format.
    source = html_lib.unescape(source or "").replace('\\"','"')
    ids=[]
    for match in YOUTUBE_SHORTCODE.finditer(source):
        attr=SHORTCODE_ID.search(match.group('attrs'))
        if attr:
            val=next((x for x in attr.groups() if x is not None),'').strip()
            if val and val not in ids: ids.append(val)
    return ids

VIDEO_PATTERNS = [
    ("youtube", re.compile(r"(?:youtube(?:-nocookie)?\.com/(?:embed/|shorts/|live/|watch\?v=)|youtu\.be/)([A-Za-z0-9_-]{11})", re.I)),
    ("vimeo", re.compile(r"(?:player\.)?vimeo\.com/(?:video/)?(\d{5,})", re.I)),
    ("vimeo", re.compile(r"\[vimeo_embed\b[^\]]*\bid\s*=\s*[\"']?(\d{5,})", re.I)),
    ("youtube", re.compile(r"\[youtube[^\]]*\bid\s*=\s*[\"']?([A-Za-z0-9_-]{11})", re.I)),
    # Some player templates pass the ID in a JS object rather than an iframe src.
    ("youtube", re.compile(r"[\"'](?:videoId|youtubeId|youtube_id|ytVideoId)[\"']\s*:\s*[\"']([A-Za-z0-9_-]{11})[\"']", re.I)),
]

# Keep candidate order from content selectors / iframe DOM; don't arbitrarily grab
# a recommended video from a sidebar or the website's global footer.
VIDEO_SELECTORS = ('.entry-content', '.article-content', '.post-content',
                   '.single-article-content', '.elementor-widget-theme-post-content',
                   'article', 'main')


def content_node(soup):
    for selector in VIDEO_SELECTORS:
        el=soup.select_one(selector)
        if el: return el
    return soup.body or soup


def extract_video_candidates(text):
    out=[]
    for provider,pattern in VIDEO_PATTERNS:
        for m in pattern.finditer(text or ''):
            candidate={"provider":provider, "id":m.group(1)}
            if candidate not in out: out.append(candidate)
    return out


def render_with_browser(url, wait_ms=1800):
    """Optional real-browser fallback for lazy shortcodes / players.

    Requires playwright and Chromium on the runner.  Only read-only page actions
    are taken. Use on owner-controlled URLs, not member-only or paid content.
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise RuntimeError('Install Playwright with: pip install playwright && playwright install chromium') from exc
    with sync_playwright() as pw:
        browser=pw.chromium.launch(headless=True)
        try:
            page=browser.new_page(user_agent='Mozilla/5.0 (compatible; SaltStrongWatch/1.0; public read-only indexing)')
            page.goto(url, wait_until='domcontentloaded',timeout=30000)
            page.wait_for_timeout(wait_ms)
            # Lazy video embeds often initialize only when scrolled into view.
            for sel in ['.entry-content iframe', 'article iframe','main iframe','[data-youtube-id]','.fluid-width-video-wrapper','[data-src*=youtube]']:
                node=page.locator(sel).first
                try:
                    if node.count():node.scroll_into_view_if_needed(timeout=1000)
                except Exception: pass
            page.wait_for_timeout(wait_ms)
            return page.content()
        finally:
            browser.close()


def get(url, json_mode=False):
    r = SESSION.get(url, timeout=25)
    r.raise_for_status()
    return r.json() if json_mode else r.text


def same_site_url(url):
    p = urlparse(url)
    return p.scheme == "https" and p.hostname in ("www.saltstrong.com", "saltstrong.com") and p.path.startswith("/articles/")


def archive_links(page_html):
    soup = BeautifulSoup(page_html, "html.parser")
    found = []
    for a in soup.find_all("a", href=True):
        u = urljoin(BASE, a["href"]).split("#")[0].split("?")[0]
        if same_site_url(u) and u not in found:
            found.append(u)
    return found


def meta(soup, key, attr="property"):
    el = soup.find("meta", attrs={attr:key})
    return el.get("content", "").strip() if el else ""


def clip(s, n=350):
    return re.sub(r"\s+", " ", html_lib.unescape(s or "")).strip()[:n]


def extract_video(html, soup, raw_post_content=""):
    """Resolve the article's primary embedded media, not sidebar suggestions.

    Priority: original author shortcode -> media elements within article -> JS
    config inside article -> page-wide embed markup (last resort).
    """
    hits=[]
    def add(provider, value):
        if not value:return
        v={"provider":provider,"id":value}
        if v not in hits:hits.append(v)

    # Raw post content is authoritative because that's where the editor's
    # [youtube_embed id="..."] shortcode lives.
    for value in extract_youtube_shortcode_ids(raw_post_content):
        if re.fullmatch(r'[A-Za-z0-9_-]{11}',value):add('youtube',value)

    # Work on the article's main content, excluding menus/recommendations.
    main=content_node(soup)
    for elm in main.select('iframe, lite-youtube, [data-youtube-id], [data-video-id], [data-vimeo-id], [data-embed-url], [data-src]'):
        # Read even lazy-loaded attributes rather than assuming src is set.
        fragments=[]
        for attr in ('src','data-src','data-lazy-src','data-iframe-src','data-embed-url',
                     'srcdoc','videoid','data-youtube-id','data-video-id','data-vimeo-id'):
            val=elm.get(attr,'')
            if not val:continue
            if attr in ('videoid','data-youtube-id','data-video-id') and re.fullmatch(r'[A-Za-z0-9_-]{11}',val):
                add('youtube',val)
            elif attr=='data-vimeo-id' and re.fullmatch(r'\d{5,}',val):
                add('vimeo',val)
            else: fragments.append(html_lib.unescape(unquote(str(val))))
        for fragment in fragments:
            for item in extract_video_candidates(fragment):add(item['provider'],item['id'])

    # Shortcode can survive inside a no-script block or encoded script string.
    text=html_lib.unescape(unquote(str(main))).replace('\\/','/').replace('\\"','"')
    for value in extract_youtube_shortcode_ids(text):
        if re.fullmatch(r'[A-Za-z0-9_-]{11}',value): add('youtube',value)
    for item in extract_video_candidates(text):add(item['provider'],item['id'])

    if not hits:
        # Some themes render the player outside `article` (but still on page).
        page_text=html_lib.unescape(unquote(html)).replace('\\/','/')
        for value in extract_youtube_shortcode_ids(page_text):
            if re.fullmatch(r'[A-Za-z0-9_-]{11}',value):add('youtube',value)
        for item in extract_video_candidates(page_text):add(item['provider'],item['id'])
    return hits


def get_author(soup):
    for sel in [".author-name", ".post-author", ".entry-meta .author", "[rel=author]", ".byline"]:
        el = soup.select_one(sel)
        if el:
            value = clip(el.get_text(" ", strip=True), 100)
            if value and len(value)<70: return value.replace("By:", "").strip()
    text = clip(soup.get_text(" ", strip=True), 700)
    m = re.search(r"\bBy:\s*(Luke Simonds|Pat Ogletree|Tony Acevedo|Joe Simonds)\b", text, re.I)
    return m.group(1) if m else "Salt Strong"


def extract_gear(soup):
    heading = None
    for h in soup.find_all(re.compile("^h[1-6]$")):
        if re.search(r"featured gear", h.get_text(" ",strip=True), re.I):
            heading = h; break
    if not heading: return []
    result=[]
    for sib in heading.next_siblings:
        if getattr(sib, "name", None) and re.fullmatch("h[1-6]",sib.name): break
        if not hasattr(sib, "find_all"): continue
        for a in sib.find_all("a", href=True):
            link=urljoin(BASE,a.get("href", ""));name=clip(a.get_text(" ",strip=True),100)
            if name and link.startswith("https://") and ("fishstrong.com" in urlparse(link).hostname or "saltstrong.com" in urlparse(link).hostname):
                if name not in [g["name"] for g in result]: result.append({"name": name, "url": link})
                if len(result)>=6:return result
    return result


def classify(title, description, main_text):
    priority=" ".join([title]*3+[description]*2+[main_text[:1800]]).lower()
    tags=[]
    for tag,patterns in TAXONOMY.items():
        if any(re.search(p, priority, re.I) for p in patterns): tags.append(tag)
    return tags[:7]


def parse_article(url, content, raw_post_content=""):
    soup=BeautifulSoup(content,"html.parser")
    title_el=soup.find("h1")
    title=clip(title_el.get_text(" ",strip=True) if title_el else meta(soup,"og:title"),180)
    if not title:return None,"no title"
    description=clip(meta(soup,"description","name") or meta(soup,"og:description"),250)
    image=meta(soup,"og:image") or meta(soup,"twitter:image","name")
    if not image:
        first=soup.select_one("article img, main img")
        if first:image=first.get("src","")
    main=soup.select_one(".entry-content, .article-content, .post-content, article .content, article, main") or soup.body or soup
    main_text=clip(main.get_text(" ",strip=True),5000)
    date=meta(soup,"article:published_time")[:10]
    if not date:
        tm=soup.find("time",datetime=True)
        date=tm.get("datetime","")[:10] if tm else ""
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}",date):date=""
    restricted=re.search(r"\b(insider[\s-]*only|vip[\s-]*only|members[\s-]*only)\b",title+" "+description+" "+main_text[:300],re.I)
    if restricted:return None,"access-restricted marker"
    videos=extract_video(content,soup,raw_post_content)
    if not videos:return None,"no detectable YouTube/Vimeo embed"
    original_image = urljoin(BASE, image) if image else ""
    if videos[0]["provider"] == "youtube":
        image = f'https://i.ytimg.com/vi/{videos[0]["id"]}/hqdefault.jpg'
    if not image: image = original_image  # Vimeo may lack accessible cover artwork.
    # The WATCH frontend has a bundled fallback when neither remote image works.
    return {
        "id":urlparse(url).path.strip("/").split("/")[-1],
        "title":title,"url":url,"image":image,"image_fallback":original_image,
        "author":get_author(soup),"date":date,"excerpt":description or clip(main_text,240),
        "tags":classify(title,description,main_text),"search_text":main_text[:3500],
        "gear":extract_gear(soup),"video":videos[0],
        "video_count":len(videos),"needs_review":len(videos)>1, "video_source":"wordpress_shortcode_or_rendered_player",
    },None


def rest_links(post_type, pages):
    links=[]
    # WP installations with custom post types may not expose them at wp/v2/posts.
    for page in range(1,pages+1):
        url=f"{BASE}/wp-json/wp/v2/{post_type}?per_page=100&page={page}&_fields=link,status"
        data=get(url,json_mode=True)
        if not isinstance(data,list) or not data:break
        links.extend(p["link"] for p in data if p.get("status")=="publish" and same_site_url(p.get("link","")))
    return list(dict.fromkeys(links))


def archive_crawl(pages):
    links=[]
    for n in range(1,pages+1):
        u=f"{BASE}/fishing-tips/"+(f"page/{n}/" if n>1 else "")
        try:
            html=get(u)
            batch=archive_links(html)
            print(f"Archive page {n}: {len(batch)} article links")
            if not batch:break
            links.extend(batch)
        except requests.RequestException as e:
            print(f"Warning: archive page {n} inaccessible: {e}",file=sys.stderr)
            break
        time.sleep(.2)
    return list(dict.fromkeys(links))


def main():
    p=argparse.ArgumentParser(description="Build a read-only Salt Strong WATCH JSON catalog")
    p.add_argument("--mode",choices=["archive","rest","urls"],default="archive",help="Archive HTML fallback or WP REST post-type discovery")
    p.add_argument("--post-type",default="articles",help="REST route name for custom article type (verify on site)")
    p.add_argument("--pages",type=int,default=2,help="Archive pages to scan. Use larger value for full backfill")
    p.add_argument("--urls-file",default="",help="Read 1 public article URL per line in --mode urls")
    p.add_argument("--render-js",action="store_true",help="Use Playwright Chromium to render pages missing a server-side video ID")
    p.add_argument("--report",default="",help="Write a JSON status record for every scanned article")
    p.add_argument("--limit",type=int,default=50,help="Max articles to fetch on this run; 0 means unlimited")
    p.add_argument("--delay",type=float,default=.45,help="Seconds between article HTTP requests")
    p.add_argument("--output",default="catalog.json")
    p.add_argument("--shortcode-map",default="",help="Optional JSON object mapping article URLs to raw WordPress post_content (read-only export)")
    args=p.parse_args()
    out=Path(args.output)
    old=[]
    if out.exists():
        try:old=json.loads(out.read_text()).get("items",[])
        except Exception:pass
    try:
        if args.mode=='urls':
            if not args.urls_file:sys.exit('--mode urls requires --urls-file')
            lines=Path(args.urls_file).read_text(encoding='utf8').splitlines()
            links=list(dict.fromkeys(line.strip() for line in lines if line.strip() and not line.lstrip().startswith('#') and same_site_url(line.strip())))
        else:
            links=rest_links(args.post_type,args.pages) if args.mode=="rest" else archive_crawl(args.pages)
    except Exception as e:
        print(f"Discovery failed: {e}",file=sys.stderr)
        sys.exit(2)
    if args.limit>0:links=links[:args.limit]
    current={i["url"]:i for i in old if i.get("url")}
    shortcode_map={}
    if args.shortcode_map:
        shortcode_map=json.loads(Path(args.shortcode_map).read_text(encoding="utf8"))
        if not isinstance(shortcode_map,dict):sys.exit("--shortcode-map must be a JSON object")
    counts={}
    report=[]
    for idx,link in enumerate(links,1):
        try:
            page_html=get(link)
            entry,reason=parse_article(link,page_html,raw_post_content=shortcode_map.get(link,""))
            method='server-html'
            if not entry and reason=='no detectable YouTube/Vimeo embed' and args.render_js:
                try:
                    page_html=render_with_browser(link)
                    entry,reason=parse_article(link,page_html,raw_post_content=shortcode_map.get(link,""))
                    method='browser-rendered'
                except Exception as exc:
                    reason=f'browser-render error: {str(exc)[:220]}'
            report.append({'url':link,'status':'imported' if entry else 'skipped',
                           'reason':reason or '', 'method':method,
                           'video':entry.get('video') if entry else None})
            if entry:
                current[link]=entry
                print(f"[{idx}/{len(links)}] Imported: {entry['title'][:75]}")
            else:
                counts[reason]=counts.get(reason,0)+1
                # Remove articles from the current catalog if now confirmed restricted/non-video.
                current.pop(link,None)
        except requests.RequestException as e:
            counts["fetch error"]=counts.get("fetch error",0)+1
            report.append({'url':link,'status':'fetch-error','reason':str(e)[:220]})
            print(f"Warning: article inaccessible: {link}: {e}",file=sys.stderr)
        time.sleep(max(0,args.delay))
    result={"generated_at":dt.datetime.now(dt.timezone.utc).isoformat(),"source":f"public_{args.mode}","demo":False,
            "items":sorted(current.values(),key=lambda x:x.get("date", ""),reverse=True),
            "stats":{"scanned":len(links),"total":len(current),"skipped":counts}}
    temp=out.with_suffix(out.suffix+".tmp")
    temp.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf8")
    temp.replace(out)
    print(f"Wrote {len(current)} total records to {out}. Notes: {counts}")
    if args.report:
        Path(args.report).write_text(json.dumps({'scanned':len(links),'results':report},indent=2),encoding='utf8')
        print(f'Wrote import audit to {args.report}')
    if not links:sys.exit(1)

if __name__=="__main__":main()
