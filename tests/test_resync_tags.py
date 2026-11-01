import json,sys,unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from tagger import classify_item
from merge_watch_catalog import merge
from resync_existing import choose_urls

URL='https://www.saltstrong.com/articles/quick-fall-lure-strategy/'
VID={'provider':'youtube','id':'3Uwwram4wQs'}

class ResyncAndTagTests(unittest.TestCase):
    def test_incidental_night_mention_cannot_create_night_fishing(self):
        row={'title':'Quick Fall Topwater Lure Strategy: When To Switch',
             'excerpt':'Adjust lures with water depth and feeding activity.',
             'search_text':'Match your presentation to fish activity. A night bite can be different. Use topwater when fish rise. Topwater works in shallow water.',
             'tags':['Night Fishing','Live Bait','Topwater']}
        result=classify_item(row)
        self.assertNotIn('Night Fishing',result['tags'])
        self.assertIn('Topwater',result['tags'])
        self.assertLessEqual(len(result['auto_tags']),6)
    def test_relevant_night_fishing_still_matches(self):
        row={'title':'Night Fishing for Snook Around Dock Lights',
             'excerpt':'Catch snook at night with lights and moving water.',
             'search_text':'Night fishing requires light and tide planning.'}
        result=classify_item(row)
        self.assertIn('Night Fishing',result['tags'])
    def test_clean_resync_drops_stale_auto_tags_keeps_explicit_manual(self):
        prev={'id':'same','title':'Old','url':URL,'date':'2026-10-01','tags':['Night Fishing','Redfish'],
              'manual_tags':['Staff Pick'],'gear':[{'name':'Prawn','url':'https://www.saltstrong.com/shopify-sso/product.php?shopurl=https%3A%2F%2Ffishstrong.com%2Fproducts%2Fprawn'}],
              'video':VID}
        new=classify_item({'id':'new','title':'Quick Fall Lure Strategy', 'url':URL,'date':'2026-10-02',
                 'search_text':'How to match the lure to depth and feeding activity.',
                 'excerpt':'When to switch lures, with clear presentations.',
                 'tags':['Night Fishing'],'gear':[],'video':VID})
        merged,audit=merge({'items':[prev]},{'items':[new]})
        actual=merged['items'][0]
        self.assertEqual(actual['id'],'same')
        self.assertNotIn('Night Fishing',actual['tags'])
        self.assertIn('Staff Pick',actual['tags'])
        self.assertEqual(actual['gear'],prev['gear'])
        self.assertEqual(audit['stats']['added'],0)
        self.assertEqual(audit['stats']['updated'],1)
    def test_select_existing_urls_in_date_order_without_duplicates(self):
        rows=[{'title':'Old','url':URL,'date':'2026-10-01'},
              {'title':'New','url':'https://www.saltstrong.com/articles/new/','date':'2026-10-22'}]
        selected,total=choose_urls({'items':rows},25,0)
        self.assertEqual(total,2)
        self.assertEqual(len(selected),2)
        self.assertIn('/new/',selected[0])
    def test_workflow_mode_preserves_normal_import_and_deploy(self):
        yaml=(ROOT/'.github/workflows/watch-sync.yml').read_text()
        self.assertIn('resync_existing:',yaml)
        self.assertIn('python resync_existing.py',yaml)
        self.assertIn('inputs.refresh_catalog && !inputs.resync_existing',yaml)
        self.assertIn('git add catalog.json',yaml)
        self.assertIn('catalog-before.json',yaml)
    def test_selected_hidden_chip_remains_available(self):
        js=(ROOT/'app.js').read_text()
        self.assertIn("if(category!=='All' && !visible.includes(category))",js)
        self.assertIn('id="topic-filter"',js)
        self.assertNotIn('list.length<27',js)

if __name__=='__main__': unittest.main()
