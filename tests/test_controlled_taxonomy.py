"""WATCH controlled taxonomy v3 regression tests, no network required."""
import sys
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from tagger import APPROVED_TAGS, TAG_VERSION, classify_item, enrich, phrase_suggestions
from merge_watch_catalog import merge

VID={'provider':'youtube','id':'AB1AFtQK-mg'}
URL='https://www.saltstrong.com/articles/match-the-hatch/'

class ControlledTaxonomyTests(unittest.TestCase):
    def test_exactly_forty_distinct_approved_browse_topics(self):
        self.assertEqual(len(APPROVED_TAGS),40)
        self.assertEqual(len(set(APPROVED_TAGS)),40)
        self.assertNotIn('Match The Hatch',APPROVED_TAGS)
        self.assertIn('Lure Selection',APPROVED_TAGS)

    def test_match_the_hatch_is_searchable_not_public_tag(self):
        row={'title':'Why It Is Important to Match the Hatch in Fall',
             'excerpt':'Matching baitfish size and lure presentation for redfish.',
             'search_text':'Compare lure profile to baitfish. Match the hatch to select lures.',
             'tags':['Match The Hatch','Night Fishing']}
        result=classify_item(row)
        self.assertIn('Lure Selection',result['auto_tags'])
        self.assertNotIn('Match The Hatch',result['tags'])
        self.assertIn('Match the Hatch',result['search_terms'])
        self.assertNotIn('Night Fishing',result['tags'])
        self.assertEqual(result['tagging_version'],TAG_VERSION)

    def test_incidental_body_mentions_are_not_browse_tags(self):
        row={'title':'Quick Fall Lure Strategy: When to Switch',
             'excerpt':'Choose lures when conditions change.',
             'search_text':'Night bite is different. A nighttime bite is rare. Switch lures in daytime.'}
        result=classify_item(row)
        self.assertNotIn('Night Fishing',result['tags'])
        self.assertIn('Lure Selection',result['tags'])

    def test_relevant_night_video_can_still_use_tag(self):
        row={'title':'Night Fishing Under Dock Lights for Snook',
             'excerpt':'Tips for nighttime fishing.',
             'search_text':'Night fishing techniques for dock lights and snook.'}
        result=classify_item(row)
        self.assertIn('Night Fishing',result['auto_tags'])
        self.assertIn('Snook',result['auto_tags'])

    def test_tags_capped_and_only_reviewed_automatic_labels(self):
        body=' '.join([label for label in APPROVED_TAGS]*10)
        row={'title':'Redfish topwater, tide and marsh fishing', 'search_text':body}
        result=classify_item(row)
        self.assertLessEqual(len(result['auto_tags']),5)
        self.assertTrue(set(result['auto_tags']).issubset(APPROVED_TAGS))

    def test_merge_retags_but_keeps_gear_and_identity(self):
        prev={'id':'original','title':'Old','url':URL,'video':VID,
              'tags':['Match The Hatch','Night Fishing'],
              'gear':[{'name':'Prawn','url':'https://www.saltstrong.com/shopify-sso/product.php?shopurl=https%3A%2F%2Ffishstrong.com%2Fproducts%2Fprawn'}]}
        new=classify_item({'id':'new','title':'Match the Hatch with Redfish',
                           'url':URL,'video':VID,'gear':[],'excerpt':'Pick the right lure profile'})
        out, audit=merge({'items':[prev]},{'items':[new]})
        result=out['items'][0]
        self.assertEqual(result['id'],'original')
        self.assertEqual(result['gear'],prev['gear'])
        self.assertNotIn('Match The Hatch',result['tags'])
        self.assertNotIn('Night Fishing',result['tags'])
        self.assertIn('Lure Selection',result['tags'])
        self.assertEqual(audit['stats']['updated'],1)
        self.assertEqual(audit['stats']['added'],0)

    def test_suggestions_are_review_only(self):
        records=[{'title':f'Winter creek presentations {n}',
                  'content_headings':'Winter creek strategy','url':f'https://www.saltstrong.com/articles/{n}/'}
                 for n in range(3)]
        _,sug=enrich(records)
        self.assertTrue(sug)
        self.assertTrue(all(row['status']=='review_only' for row in sug))
        self.assertTrue(all(row['tag'] not in APPROVED_TAGS for row in sug))

    def test_frontend_filters_old_unapproved_tags_and_searches_terms(self):
        js=(ROOT/'app.js').read_text()
        self.assertIn('approvedTopics = new Set',js)
        self.assertIn('publicTags(it).forEach',js)
        self.assertIn("(item.search_terms ?? []).join(' ')",js)
        self.assertIn('publicTags(it).slice(0,8)',js)
        self.assertIn("if(el.dataset.view==='home' || el.dataset.view==='saved')",js)

if __name__=='__main__':unittest.main()
