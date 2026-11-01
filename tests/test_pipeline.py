import json,sys,unittest
from pathlib import Path
from unittest.mock import patch
from bs4 import BeautifulSoup
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from sync_catalog import extract_youtube_shortcode_ids,extract_video,extract_gear,parse_article
from tagger import classify_item,enrich,phrase_suggestions
from merge_watch_catalog import merge

class PipelineTests(unittest.TestCase):
 def test_shortcode_and_rendered_player(self):
  self.assertEqual(extract_youtube_shortcode_ids('[youtube_embed id="3Uwwram4wQs"]'),['3Uwwram4wQs'])
  html='<main><iframe data-src="https://www.youtube-nocookie.com/embed/AB1AFtQK-mg"></iframe></main>'
  self.assertEqual(extract_video(html,BeautifulSoup(html,'html.parser'))[0]['id'],'AB1AFtQK-mg')
 def test_gear_and_readable_content(self):
  html='''<html><head><meta name="description" content="Catch redfish on flooded grass with a popping cork"></head><body><article><h1>Redfish in Flooded Grass</h1><h2>Rigging a popping cork</h2><p>On the flooded grass in the marsh, cast a popping cork with a shrimp lure.</p><a href="https://fishstrong.com/products/prawn-xt">Prawn XT</a><iframe src="https://www.youtube.com/embed/AB1AFtQK-mg"></iframe></article></body></html>'''
  row,err=parse_article('https://www.saltstrong.com/articles/grass/',html)
  self.assertIsNone(err)
  self.assertEqual(row['gear'][0]['url'],'https://fishstrong.com/products/prawn-xt')
  self.assertIn('popping cork',row['content_headings'])
  enriched=classify_item(row)
  self.assertIn('Flooded Grass',enriched['tags'])
  self.assertIn('Popping Corks',enriched['tags'])
 def test_dedup_and_merge_preserves_older_gear(self):
  base={'items':[{'id':'old','title':'Old','url':'https://www.saltstrong.com/articles/old/','tags':['Redfish'],'gear':[{'name':'Prawn','url':'https://fishstrong.com/products/prawn'}], 'video':{'provider':'youtube','id':'AB1AFtQK-mg'}}]}
  imported={'items':[{'id':'new','title':'Updated','url':'https://saltstrong.com/articles/old','tags':['Flooded Grass'],'gear':[], 'video':{'provider':'youtube','id':'AB1AFtQK-mg'}},{'id':'second','title':'Second','url':'https://www.saltstrong.com/articles/new/','tags':['Tides'],'gear':[], 'video':{'provider':'youtube','id':'3Uwwram4wQs'}}]}
  output,audit=merge(base,imported)
  self.assertEqual(len(output['items']),2)
  self.assertEqual(audit['stats']['updated'],1)
  old=next(x for x in output['items'] if x['id']=='old')
  self.assertEqual(len(old['gear']),1)
  self.assertIn('Flooded Grass',old['tags'])
 def test_new_topic_suggestions_are_review_only(self):
  a=[{'title':'Winter Creek Pattern Secrets','content_headings':'Winter creek patterns','url':'u1'}, {'title':'Winter Creek Pattern Tactics','content_headings':'Winter creek patterns','url':'u2'}]
  sug=phrase_suggestions(a)
  self.assertTrue(any('Winter Creek' in x['tag'] for x in sug))
 def test_no_autorun_on_design_push(self):
  t=(ROOT/'.github/workflows/watch-sync.yml').read_text()
  self.assertIn("if: github.event_name != 'push'",t)
  self.assertIn("github.event_name == 'schedule'",t)
  self.assertIn('catalog.json _site/',t)
 def test_click_title_is_not_article_link(self):
  js=(ROOT/'app.js').read_text()
  self.assertIn('class="card-title" data-open=',js)
  self.assertNotIn('<a class="card-title"',js)
  self.assertIn('Read full article',js)

if __name__=='__main__':unittest.main()
