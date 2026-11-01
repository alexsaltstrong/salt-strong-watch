"""Controlled WATCH content tagging. Never modifies WordPress tags.

Automatic tags are *recomputed* on every successful import, not unioned with old
heuristic labels. Explicit ``manual_tags`` are kept in a separate field.
Unknown recurring phrases stay suggestions for human review.
"""
from __future__ import annotations
from collections import defaultdict
import re

TAG_VERSION = 'relevance-v2'

# Curated labels; allow new labels only by editing/reviewing this taxonomy.
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

STOP_WORDS=set('the a an and or to for in on with from by at out of into what when where how why this that these those your you more most best using use ways way tips fishing fish catch catching video lesson guide learn important easy ultimate everything beginner'.split())

def normal(text):
    return re.sub(r'\s+',' ',str(text or '')).strip()

def count_matches(patterns, text):
    return sum(len(re.findall(p,text,re.I)) for p in patterns)

def classify_item(item):
    """Fewer, higher-signal tags. Never carry old auto-generated tags forward."""
    title=normal(item.get('title',''))
    summary=normal(item.get('excerpt',''))
    headings=normal(item.get('content_headings',''))
    article=normal(item.get('search_text',''))
    candidates=[]
    for family,label,patterns in TAG_RULES:
        title_hits=count_matches(patterns,title)
        heading_hits=count_matches(patterns,headings)
        summary_hits=count_matches(patterns,summary)
        body_hits=count_matches(patterns,article)
        # A single incidental phrase in the body is not a topic. Strong main
        # content evidence needs to come from the editorial title/heading, or
        # independently from the summary AND the body, or repeated body mentions.
        qualifies=(title_hits>0 or heading_hits>0 or
                   (summary_hits>0 and body_hits>=1) or body_hits>=4)
        # Night Fishing is often incidental to a general lure strategy. Only
        # publish it when the video is *framed* as night fishing in its title,
        # lesson headings, or summary with repeated treatment in the body.
        if label=='Night Fishing':
            qualifies=bool(title_hits or heading_hits or (summary_hits and body_hits>=3))
        if not qualifies:continue
        score=title_hits*7+heading_hits*5+summary_hits*2+min(body_hits,5)
        candidates.append((score,label,family,{'title':title_hits,'headings':heading_hits,'summary':summary_hits,'body':body_hits}))
    candidates.sort(key=lambda e:(-e[0],e[1]))
    auto=[x[1] for x in candidates[:6]]
    manual=[normal(t) for t in item.get('manual_tags',[]) if normal(t)]
    tags=list(dict.fromkeys(auto+manual))
    result=dict(item)
    result['tags']=tags
    result['auto_tags']=auto
    result['tag_facets']={family:[x[1] for x in candidates[:6] if x[2]==family] for family in ['species','structure','conditions','techniques','tackle','format'] if any(x[2]==family for x in candidates[:6])}
    result['tag_evidence']={label:evidence for _,label,_,evidence in candidates[:6]}
    result['tagging_version']=TAG_VERSION
    return result

def phrase_suggestions(items,min_articles=2):
    """Discover candidates for review; never auto-create public topic chips."""
    documents=defaultdict(set)
    for item in items:
        words=re.findall(r'[a-z]{3,}',normal(item.get('title','')+' '+item.get('content_headings','')).lower())
        for n in (2,3):
            for i in range(len(words)-n+1):
                chunk=words[i:i+n]
                if any(w in STOP_WORDS for w in chunk) or len(set(chunk))!=n:continue
                documents[' '.join(chunk)].add(item.get('url',''))
    existing={label.lower() for _,label,_ in TAG_RULES}
    proposals=[{'tag':phrase.title(),'articles':len(urls)} for phrase,urls in documents.items() if len(urls)>=min_articles and phrase not in existing]
    return sorted(proposals,key=lambda x:(-x['articles'],x['tag']))[:40]

def enrich(items):
    updated=[classify_item(i) for i in items]
    return updated,phrase_suggestions(updated)
