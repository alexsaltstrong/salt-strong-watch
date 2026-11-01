"""Evidence-based WATCH taxonomy. Reads *article text*; never changes WP tags.

Rules are transparent and curated. Unknown phrases from repeated headings are surfaced
as suggestions for review, rather than silently published as nonsensical tags.
"""
from __future__ import annotations
from collections import Counter, defaultdict
import re

# family, display name, bounded patterns. Rules do NOT inspect WordPress tag names.
TAG_RULES = [
 ('species','Redfish',[r'\bredfish\b',r'\bred drum\b']),
 ('species','Seatrout',[r'\bsea\s?trout\b',r'\bspeckled trout\b',r'\bspecks\b']),
 ('species','Snook',[r'\bsnook\b']),('species','Flounder',[r'\bflounder\b']),
 ('species','Tarpon',[r'\btarpon\b']),('species','Black Drum',[r'\bblack drum\b']),
 ('species','Mangrove Snapper',[r'\bmangrove snapper\b']),('species','Sheepshead',[r'\bsheepshead\b']),
 ('species','Spanish Mackerel',[r'\bspanish mackerel\b']),('species','Striped Bass',[r'\bstriped bass\b']),
 ('structure','Oyster Bars',[r'\boyster bar',r'\boyster reef',r'\bshell bar',r'\bshell reef']),
 ('structure','Marshes',[r'\bmarsh(?:es)?\b',r'\bsalt marsh']),
 ('structure','Creek Mouths',[r'\bcreek mouth',r'\bcreek entrance']),
 ('structure','Marsh Drains',[r'\bmarsh drain',r'\bdrainage creek',r'\bdrain mouth']),
 ('structure','Mangroves',[r'\bmangroves?\b']),
 ('structure','Grass Flats',[r'\bgrass flat',r'\bseagrass flat']),
 ('structure','Flooded Grass',[r'\bflooded grass',r'\bflooded shoreline',r'\bflooded marsh grass']),
 ('structure','Docks',[r'\bdocks?\b',r'\bpiling']),
 ('structure','Dock Lights',[r'\bdock lights?',r'\bnight lights?']),
 ('structure','Bridges',[r'\bbridge pilings?',r'\bbridges?\b']),
 ('structure','Sandbars',[r'\bsandbars?',r'\bsand bars?']),
 ('structure','Drop-Offs',[r'\bdrop.?offs?',r'\bdepth changes?']),
 ('structure','Deep Holes',[r'\bdeep holes?',r'\bdeeper holes?']),
 ('structure','Mud Flats',[r'\bmud flats?',r'\bmuddy bottom']),
 ('structure','Structure',[r'\bstructure\b']),
 ('conditions','Tides',[r'\btides?\b',r'\btidal\b']),
 ('conditions','High Water',[r'\bhigh water\b',r'\bhigh tide\b',r'\bflood tide']),
 ('conditions','Low Tide',[r'\blow tide\b',r'\blow water\b']),
 ('conditions','Incoming Tide',[r'\bincoming tide\b',r'\bflooding tide\b']),
 ('conditions','Outgoing Tide',[r'\boutgoing tide\b',r'\bfalling tide\b']),
 ('conditions','Slack Tide',[r'\bslack tide\b',r'\bslack water\b']),
 ('conditions','Current',[r'\bcurrent seams?\b',r'\btidal current\b',r'\bwater flow\b']),
 ('conditions','Wind',[r'\bwindy\b',r'\bwind direction\b',r'\bwindward\b']),
 ('conditions','Dirty Water',[r'\bdirty water\b',r'\bmurky water\b']),
 ('conditions','Clear Water',[r'\bclear water\b',r'\bwater clarity\b']),
 ('conditions','Cold Fronts',[r'\bcold fronts?\b',r'\bpost.front\b']),
 ('conditions','Fall Fishing',[r'\bfall fishing\b',r'\bautumn fishing\b']),
 ('conditions','Night Fishing',[r'\bnight fishing\b',r'\bnight bite\b']),
 ('techniques','Popping Corks',[r'\bpopping corks?\b']),
 ('techniques','Topwater',[r'\btopwater\b',r'\bwalk.the.dog\b']),
 ('techniques','Sight Fishing',[r'\bsight fishing\b',r'\bsight casting\b']),
 ('techniques','Wade Fishing',[r'\bwade fishing\b',r'\bwading\b']),
 ('techniques','Live Bait',[r'\blive bait\b',r'\blive shrimp\b',r'\blive mullet\b']),
 ('techniques','Artificial Lures',[r'\bartificial lures?\b',r'\bartificials\b']),
 ('techniques','Match The Hatch',[r'\bmatch the hatch\b',r'\bmatching the hatch\b']),
 ('techniques','Skipping',[r'\bskipping (?:lures?|baits?)\b']),
 ('techniques','Casting',[r'\bcasting technique',r'\bcast accuracy']),
 ('techniques','Rigging',[r'\brigg?ing\b',r'\brigging tips?\b']),
 ('tackle','Jigheads',[r'\bjigheads?\b']),
 ('tackle','Paddletails',[r'\bpaddletails?\b',r'\bpaddle.tail\b']),
 ('tackle','Swimbaits',[r'\bswimbaits?\b']),
 ('tackle','Weedless Lures',[r'\bweedless\b']),
 ('tackle','Shrimp Lures',[r'\bshrimp (?:imitation|lure|bait)\b',r'\bprawn xt\b']),
 ('tackle','Leader Line',[r'\bleader line\b',r'\bfluorocarbon\b']),
 ('tackle','Fishing Rods',[r'\bfishing rods?\b',r'\btravel rod\b',r'\bslam stick\b']),
 ('tackle','Hardbaits',[r'\bhardbaits?\b',r'\bjerkbaits?\b']),
 ('tackle','Soft Plastics',[r'\bsoft plastics?\b',r'\bsoft baits?\b']),
 ('format','Gear Tests',[r'\bgear tests?\b',r'\bproduct review\b',r'\bside.by.side test\b']),
 ('format','Experiments',[r'\bexperiments?\b',r'\bwe tested\b']),
]

STOP_HEADINGS={'final thoughts','conclusion','summary','featured gear','in this video','watch next','related articles','faq','frequently asked questions','introduction','about the author','get more tips'}
STOP_WORDS=set('the a an and or to for in on with from by at out of into what when where how why this that these those your you more most best using use ways way tips fishing fish catch catching video lesson guide learn important easy ultimate everything beginner easy'.split())


def normal(text):
    return re.sub(r'\s+',' ',str(text or '')).strip()


def classify_item(item):
    title=normal(item.get('title',''))
    snippet=normal(item.get('excerpt',''))
    article=normal(item.get('search_text',''))
    headings=normal(item.get('content_headings',''))
    # Require meaning in title/summary/headings, or at least two body mentions.
    priority=(title+' '+snippet+' '+headings).lower()
    body=article.lower()
    tags=[]; facets=defaultdict(list); evidence={}
    for family,label,patterns in TAG_RULES:
        p_hits=[re.search(p,priority,re.I) for p in patterns]
        body_hits=sum(len(re.findall(p,body,re.I)) for p in patterns)
        if any(p_hits) or body_hits >= 2:
            tags.append(label)
            facets[family].append(label)
            evidence[label]={'source':'title/summary/headings' if any(p_hits) else 'article body','mentions':body_hits}
    # Keep existing hand-curated tags for entries previously edited by the team,
    # but use discovered labels first to improve filter browsing.
    tags=list(dict.fromkeys(tags+(item.get('tags') or [])))[:18]
    item=dict(item)
    item['tags']=tags
    item['tag_facets']=dict(facets)
    item['tag_evidence']=evidence
    return item


def phrase_suggestions(items, min_articles=2):
    """Mine 2-3-word phrases from titles/headings across distinct articles.

    Suggestions are *not* auto-published as tags. A future editorial or AI review
    can promote them into TAG_RULES so discovery remains useful rather than noisy.
    """
    seen=defaultdict(set)
    for item in items:
        text=normal(item.get('title','')+' '+item.get('content_headings',''))
        words=re.findall(r'[a-z]{3,}',text.lower())
        docid=item.get('url','')
        for n in (2,3):
            for i in range(len(words)-n+1):
                chunk=words[i:i+n]
                if any(w in STOP_WORDS for w in chunk) or len(set(chunk))!=n:continue
                label=' '.join(chunk)
                seen[label].add(docid)
    existing={label.lower() for _,label,_ in TAG_RULES}
    ranked=[{'tag':p.title(),'articles':len(v)} for p,v in seen.items() if len(v)>=min_articles and p not in existing]
    return sorted(ranked,key=lambda x:(-x['articles'],x['tag']))[:40]


def enrich(items):
    updated=[classify_item(x) for x in items]
    return updated,phrase_suggestions(updated)
