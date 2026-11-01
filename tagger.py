"""WATCH controlled content taxonomy, version 3.

40 approved browse topics. Subtopics remain searchable, but cannot silently
become filter chips. Never changes WordPress taxonomy. Old machine tags are
REPLACED on successful resync; explicit manual_tags remain staff overrides.
"""
from __future__ import annotations

from collections import defaultdict
import re

TAG_VERSION = 'controlled-v3'
MAX_AUTO_TAGS = 5

# Family, approved label, matching phrases. This is the ONLY source of newly
# generated public browsing tags. Add/edit labels deliberately after review.
TAG_RULES = [
    # Species (8)
    ('species', 'Redfish', [r'\bredfish\b', r'\bred drum\b']),
    ('species', 'Seatrout', [r'\bsea\s?trout\b', r'\bspeckled trout\b', r'\bspecks\b']),
    ('species', 'Snook', [r'\bsnook\b']),
    ('species', 'Flounder', [r'\bflounder\b']),
    ('species', 'Tarpon', [r'\btarpon\b']),
    ('species', 'Sheepshead', [r'\bsheepshead\b']),
    ('species', 'Mangrove Snapper', [r'\bmangrove snapper\b']),
    ('species', 'Black Drum', [r'\bblack drum\b']),
    # Structure and habitat (8)
    ('structure', 'Oyster Bars', [r'\boyster bar', r'\boyster reef', r'\bshell (?:bar|reef)']),
    ('structure', 'Marshes', [r'\bmarsh(?:es)?\b', r'\bsalt marsh']),
    ('structure', 'Mangroves', [r'\bmangroves?\b']),
    ('structure', 'Grass Flats', [r'\bgrass flats?\b', r'\bseagrass flats?\b']),
    ('structure', 'Docks', [r'\bdocks?\b', r'\bdock pilings?\b']),
    ('structure', 'Bridges', [r'\bbridges?\b', r'\bbridge pilings?\b']),
    ('structure', 'Creek Mouths', [r'\bcreek mouths?\b', r'\bcreek entrances?\b']),
    ('structure', 'Structure', [r'\bfishing structure\b', r'\bunderwater structure\b', r'\bstructure fishing\b']),
    # Conditions (8)
    ('conditions', 'Tides', [r'\btides?\b', r'\btidal\b', r'\bslack tide\b', r'\boutgoing tide\b', r'\bincoming tide\b']),
    ('conditions', 'High Water', [r'\bhigh water\b', r'\bhigh tide\b', r'\bflood tide\b', r'\bflooded grass\b']),
    ('conditions', 'Low Tide', [r'\blow tide\b', r'\blow water\b', r'\bnegative tide\b']),
    ('conditions', 'Current', [r'\btidal currents?\b', r'\bcurrent seams?\b', r'\bwater flow\b']),
    ('conditions', 'Wind', [r'\bwindy\b', r'\bwind direction\b', r'\bwindward\b']),
    ('conditions', 'Cold Fronts', [r'\bcold fronts?\b', r'\bpost.front\b']),
    ('conditions', 'Fall Fishing', [r'\bfall fishing\b', r'\bautumn fishing\b', r'\bfall lure\b', r'\bin the fall\b', r'\bfall (?:pattern|strategy|tactics)\b']),
    ('conditions', 'Night Fishing', [r'\bnight fishing\b', r'\bnight bite\b']),
    # Technique / presentations (11)
    ('techniques', 'Lure Selection', [r'\blure (?:selection|choice|strategy|strategies)\b',
                                  r'\bmatch(?:ing)? the hatch\b', r'\bwhen to switch\b',
                                  r'\bchange (?:lures?|presentations?)\b', r'\bchoose (?:the |a )?lures?\b']),
    ('techniques', 'Topwater', [r'\btopwater\b', r'\bwalk.the.dog\b']),
    ('techniques', 'Soft Plastics', [r'\bsoft plastics?\b', r'\bsoft (?:plastic )?jerk(?:bait)?s?\b']),
    ('techniques', 'Paddletails', [r'\bpaddletails?\b', r'\bpaddle.tail\b']),
    ('techniques', 'Shrimp Lures', [r'\bshrimp (?:imitation|lures?|artificials?)\b', r'\bprawn xt\b']),
    ('techniques', 'Popping Corks', [r'\bpopping corks?\b']),
    ('techniques', 'Rigging', [r'\brigg?ing\b', r'\brigging tips?\b']),
    ('techniques', 'Sight Fishing', [r'\bsight fishing\b', r'\bsight casting\b']),
    ('techniques', 'Live Bait', [r'\blive bait\b', r'\blive shrimp\b', r'\blive mullet\b']),
    ('techniques', 'Weedless Lures', [r'\bweedless\b']),
    ('techniques', 'Jigheads', [r'\bjigheads?\b']),
    # Tackle (3)
    ('tackle', 'Leader Line', [r'\bleader line\b', r'\bfluorocarbon\b', r'\bmono(?:filament)? leader\b']),
    ('tackle', 'Fishing Rods', [r'\bfishing rods?\b', r'\btravel rods?\b', r'\bslam stick\b']),
    ('tackle', 'Hardbaits', [r'\bhardbaits?\b', r'\bjerkbaits?\b', r'\bplugs?\b']),
    # Content type (2)
    ('format', 'Gear Tests', [r'\bgear tests?\b', r'\bproduct review\b', r'\bside.by.side test\b']),
    ('format', 'Experiments', [r'\bexperiments?\b', r'\bwe tested\b', r'\btest results?\b']),
]
APPROVED_TAGS = tuple(label for _, label, _ in TAG_RULES)
assert len(APPROVED_TAGS) == 40 and len(set(APPROVED_TAGS)) == 40

# Precisely selected search-only phrases. We can index these without adding
# a new navigation filter every time someone uses the phrase in a blog.
SEARCH_ONLY = {
    'Match the Hatch': [r'\bmatch(?:ing)? the hatch\b'],
    'Baitfish Profiles': [r'\bbaitfish profiles?\b'],
    'Outgoing Tide': [r'\boutgoing tide\b', r'\bfalling tide\b'],
    'Incoming Tide': [r'\bincoming tide\b', r'\bflooding tide\b'],
    'Slack Tide': [r'\bslack tide\b'],
    'Flooded Grass': [r'\bflooded grass\b', r'\bflooded marsh grass\b'],
    'Marsh Drains': [r'\bmarsh drains?\b', r'\bdrain mouth\b'],
    'Dock Lights': [r'\bdock lights?\b'],
    'Jerk Shads': [r'\bjerk shads?\b'],
    'Knot Strength': [r'\bknot strength\b'],
    'Creek Entrances': [r'\bcreek entrances?\b'],
    'Lure Color': [r'\blure colors?\b', r'\bcolor selection\b'],
}

STOP_WORDS = set(('the a an and or to for in on with from by at out of into what when where how why '
                  'this that these those your you more most best using use ways way tips fishing fish '
                  'catch catching video lesson guide learn important easy ultimate everything beginner').split())

def normal(text):
    return re.sub(r'\s+', ' ', str(text or '')).strip()

def count_matches(patterns, text):
    return sum(len(re.findall(pattern, text, re.I)) for pattern in patterns)

def classify_item(item):
    """Return a new article with only approved auto tags and searchable terms."""
    title = normal(item.get('title'))
    summary = normal(item.get('excerpt'))
    headings = normal(item.get('content_headings'))
    body = normal(item.get('search_text'))
    candidates = []
    for family, label, patterns in TAG_RULES:
        t, h, s, b = (count_matches(patterns, field) for field in (title, headings, summary, body))
        # A throwaway mention in a long blog is not a browse category.
        qualifies = bool(t or h or (s and b >= 2) or b >= 5)
        if label == 'Night Fishing':
            # Night bite is a common incidental comparison in daytime lessons.
            qualifies = bool(t or h or (s and b >= 3))
        if not qualifies:
            continue
        score = t * 9 + h * 6 + s * 3 + min(b, 6)
        candidates.append((score, label, family, {'title': t, 'headings': h, 'summary': s, 'body': b}))
    candidates.sort(key=lambda v: (-v[0], v[1]))
    chosen = candidates[:MAX_AUTO_TAGS]
    auto = [label for _, label, _, _ in chosen]
    manual = list(dict.fromkeys(normal(t) for t in item.get('manual_tags', []) if normal(t)))
    # Manual tags are explicit human editorial overrides. They are NOT part of
    # automatic taxonomy growth and can be reviewed separately.
    tags = list(dict.fromkeys(auto + manual))
    phrases = [phrase for phrase, patterns in SEARCH_ONLY.items()
               if count_matches(patterns, ' '.join((title, headings, summary, body)))]
    result = dict(item)
    result.update({
        'auto_tags': auto,
        'manual_tags': manual,
        'tags': tags,
        'tag_facets': {family: [label for _, label, f, _ in chosen if f == family]
                       for family in ('species', 'structure', 'conditions', 'techniques', 'tackle', 'format')
                       if any(f == family for _, _, f, _ in chosen)},
        'tag_evidence': {label: evidence for _, label, _, evidence in chosen},
        'search_terms': phrases,
        'tagging_version': TAG_VERSION,
    })
    return result

def phrase_suggestions(items, min_articles=3):
    """Report possible new topics for humans; never publish them automatically."""
    docs = defaultdict(set)
    for item in items:
        words = re.findall(r'[a-z]{3,}',
                           normal(item.get('title', '') + ' ' + item.get('content_headings', '')).lower())
        for n in (2, 3):
            for i in range(len(words) - n + 1):
                phrase = words[i:i+n]
                if len(set(phrase)) < n or any(w in STOP_WORDS for w in phrase):
                    continue
                docs[' '.join(phrase)].add(item.get('url', ''))
    approved = {tag.lower() for tag in APPROVED_TAGS}
    known = {tag.lower() for tag in SEARCH_ONLY}
    suggestions = [{'tag': phrase.title(), 'articles': len(urls), 'status': 'review_only'}
                   for phrase, urls in docs.items()
                   if len(urls) >= min_articles and phrase not in approved and phrase not in known]
    return sorted(suggestions, key=lambda x: (-x['articles'], x['tag']))[:30]

def enrich(items):
    result = [classify_item(item) for item in items]
    return result, phrase_suggestions(result)
