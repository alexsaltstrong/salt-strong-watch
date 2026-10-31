import json
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path
from unittest.mock import patch
import watch_last100 as w

BASE='https://www.saltstrong.com/articles/'

class Last100Tests(unittest.TestCase):
    def test_archive_link_collection_rejects_navigation(self):
        content='''<main><article><h2><a href="/articles/new-one/">New</a></h2></article>
        <article><h2><a href="/articles/second-one/">Two</a></h2></article></main>
        <footer><a href="/articles/old-one/">Old</a></footer>'''
        self.assertEqual(w.archive_article_links(content),[BASE+'new-one/',BASE+'second-one/'])

    def test_youtube_only_and_skip_vimeo_and_text(self):
        urls=[BASE+'one/',BASE+'two/',BASE+'three/']
        pages={
            urls[0]:'<html><main><h1>Fishing oysters</h1>[youtube_embed id="AbCdef_1234"]</main></html>',
            urls[1]:'<html><main><h1>Vimeo lesson</h1><iframe src="https://player.vimeo.com/video/123456789"></iframe></main></html>',
            urls[2]:'<html><main><h1>Text article</h1><p>No video here.</p></main></html>',
        }
        with tempfile.TemporaryDirectory() as tmp:
            d=Path(tmp)
            args=Namespace(limit=3,max_pages=3,urls_file=None,no_browser=True,delay=0,
                output=str(d/'catalog.json'),audit=str(d/'audit.json'),summary=str(d/'summary.md'))
            with patch.object(w,'discover_rest',return_value=(urls,'REST test',[])),patch.object(w,'get',side_effect=lambda u:pages[u]):
                c,a=w.run(args)
            self.assertEqual(c['stats']['articles_scanned'],3)
            self.assertEqual(c['stats']['youtube_videos'],1)
            self.assertEqual(c['stats']['skipped'],2)
            self.assertEqual(c['items'][0]['video']['id'],'AbCdef_1234')
            self.assertTrue(c['items'][0]['image'].endswith('/AbCdef_1234/hqdefault.jpg'))
            self.assertTrue((d/'audit.json').exists())

if __name__=='__main__':unittest.main()
