"""WATCH regressions: comments must never enter catalog text or video discovery."""
import json
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from sync_catalog import authored_article_text, parse_article, extract_video
from merge_watch_catalog import merge
from tagger import classify_item
from bs4 import BeautifulSoup

URL = 'https://www.saltstrong.com/articles/match-the-hatch-test/'
SSO = ('https://www.saltstrong.com/shopify-sso/product.php?shopurl='
       'https%3A%2F%2Ffishstrong.com%2Fproducts%2Fhoss-helix')


def page(inner, extra=''):
    return ('''<html><head><meta name="description" content="Choose the right lure profile in fall"></head>
    <body><main><article><h1>Match the Hatch Lure Strategy</h1>
    <div class="entry-content">''' + inner + '''</div>''' + extra +
    '''</article></main></body></html>''')


class ArticleOnlyContentTests(unittest.TestCase):
    def test_comments_after_entry_content_not_indexed(self):
        content = page('''<h2>Lure Selection</h2><p>Compare baitfish size to your paddletail.</p>
          <iframe src="https://www.youtube.com/embed/AB1AFtQK-mg"></iframe>
          <h2>Featured Gear</h2><ul><li><a href="''' + SSO + '''">Hoss Helix Hook</a></li></ul>''',
            '''<section id="comments" class="comments-area"><h2>Comments</h2>
              <ol class="comment-list"><li id="comment-101">Reader: I love night fishing.
              Night fishing under dock lights is great!</li></ol></section>
              <aside><h2>Related articles</h2>Night Fishing Tips</aside>''')
        row, err = parse_article(URL, content)
        self.assertIsNone(err)
        self.assertNotIn('night fishing', row['search_text'].lower())
        self.assertNotIn('comments', row['content_headings'].lower())
        self.assertIn('paddletail', row['search_text'].lower())
        self.assertEqual(row['content_scope_version'], 'article-body-only-v1')
        self.assertEqual(row['gear'][0]['url'], SSO)
        self.assertNotIn('Night Fishing', classify_item(row)['tags'])

    def test_comments_in_post_content_ignored_even_inside_outer_article(self):
        html = page('''<p>A soft plastics tutorial for redfish.</p>
            <iframe src="https://www.youtube.com/embed/AB1AFtQK-mg"></iframe>
            <section class="wpdiscuz"><div class="wpd-comment-text">Night fishing night fishing.</div></section>
            <div class="related-posts">Night Fishing Related Reading</div>''')
        row, err = parse_article(URL, html)
        self.assertIsNone(err)
        self.assertNotIn('night fishing', row['search_text'].lower())
        self.assertEqual(row['video']['id'], 'AB1AFtQK-mg')

    def test_article_without_specific_content_class_prunes_comment_heading(self):
        html = '''<html><body><article><h1>Fall Lures</h1>
        <p>Switch to paddletails when fish feed lower in the water column.</p>
        <iframe src="https://www.youtube.com/embed/AB1AFtQK-mg"></iframe>
        <h2>10 Comments</h2><p>Someone mentioned night fishing night fishing</p>
        </article></body></html>'''
        row, err = parse_article(URL, html)
        self.assertIsNone(err)
        self.assertNotIn('night fishing', row['search_text'].lower())
        self.assertNotIn('10 Comments', row['content_headings'])
        self.assertIn('paddletails', row['search_text'])

    def test_comment_youtube_embed_does_not_qualify_an_article(self):
        html = page('<h2>What to try</h2><p>This article has no YouTube player.</p>',
            '''<section id="comments"><p>Reader embedded a video:
              <iframe src="https://www.youtube.com/embed/AB1AFtQK-mg"></iframe></p></section>''')
        row, err = parse_article(URL, html)
        self.assertIsNone(row)
        self.assertEqual(err, 'no detectable YouTube/Vimeo embed')

    def test_clean_resync_purges_old_comment_text_but_retains_gear(self):
        old = {'id':'same','title':'Old title','url':URL,
               'search_text':'reader says night fishing night fishing all day',
               'tags':['Night Fishing'], 'video':{'provider':'youtube','id':'AB1AFtQK-mg'},
               'gear':[{'name':'Hoss Helix Hook','url':SSO}]}
        newly = classify_item({'id':'new','title':'Lure Strategy','url':URL,
                               'search_text':'', 'excerpt':'Choosing lures for redfish',
                               'content_scope_version':'article-body-only-v1',
                               'video':{'provider':'youtube','id':'AB1AFtQK-mg'},
                               'gear':[]})
        output, audit = merge({'items':[old]}, {'items':[newly]})
        self.assertEqual(output['items'][0]['search_text'], '')
        self.assertEqual(output['items'][0]['gear'], old['gear'])
        self.assertEqual(output['items'][0]['id'], 'same')
        self.assertNotIn('Night Fishing', output['items'][0]['tags'])
        self.assertEqual(audit['stats']['updated'], 1)
        self.assertEqual(audit['stats']['added'], 0)

    def test_new_search_is_phrase_first(self):
        js = (ROOT/'app.js').read_text(encoding='utf8')
        self.assertIn('const searchScore =', js)
        self.assertIn('const count = body.split(terms).length - 1', js)
        self.assertIn("count >= 2 || (count === 1 && body.indexOf(terms) < 900)", js)
        self.assertIn('searchScore(b)-searchScore(a)', js)


if __name__ == '__main__':
    unittest.main()
