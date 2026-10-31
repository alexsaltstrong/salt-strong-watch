"""Unit tests cover actual shortcode shape and typical rendered WordPress players."""
from bs4 import BeautifulSoup
from sync_catalog import extract_video,parse_article
import unittest

YT1='EEvy3gPSVIU'
YT2='abcdefghijk'
VIDS=['[youtube_embed id="EEvy3gPSVIU"]',"[youtube_embed id='EEvy3gPSVIU']",'[youtube_embed id=EEvy3gPSVIU]',
      '<iframe src="https://www.youtube-nocookie.com/embed/EEvy3gPSVIU"></iframe>',
      '<iframe data-src="https://www.youtube.com/embed/EEvy3gPSVIU"></iframe>',
      '<lite-youtube videoid="EEvy3gPSVIU"></lite-youtube>',
      '<div data-youtube-id="EEvy3gPSVIU"></div>',
      '<script>const p={"videoId":"EEvy3gPSVIU"}</script>',
      '<iframe src="https:\\/\\/www.youtube.com\\/embed\\/EEvy3gPSVIU"></iframe>',
      '<iframe srcdoc="&lt;iframe src=&quot;https://www.youtube.com/embed/EEvy3gPSVIU&quot;&gt;"></iframe>']
class Tests(unittest.TestCase):
 def test_sources(self):
  for piece in VIDS:
   with self.subTest(piece=piece):
    html='<article><main>'+piece+'</main></article>'
    vids=extract_video(html,BeautifulSoup(html,'html.parser'))
    self.assertTrue(vids and vids[0]=={'provider':'youtube','id':YT1},vids)
 def test_editor_shortcodes_first(self):
  html='<main><iframe src="https://youtube.com/embed/abcdefghijk"></iframe></main>'
  vids=extract_video(html,BeautifulSoup(html,'html.parser'),'Intro [youtube_embed id="EEvy3gPSVIU"]')
  self.assertEqual(vids[0]['id'],YT1)
 def test_avoid_sidebar(self):
  html='<body><main><iframe src="https://youtube.com/embed/EEvy3gPSVIU"></iframe></main><aside><iframe src="https://youtube.com/embed/abcdefghijk"></iframe></aside></body>'
  vids=extract_video(html,BeautifulSoup(html,'html.parser'))
  self.assertEqual(vids,[{'provider':'youtube','id':YT1}])
 def test_catalog_entry(self):
  html='<html><head><meta property="og:image" content="https://www.saltstrong.com/thumbnail.jpg"></head><body><main><h1>Test Long Form</h1><p>Redfish around marshes</p><iframe data-src="https://www.youtube.com/embed/EEvy3gPSVIU"></iframe></main></body></html>'
  item,reason=parse_article('https://www.saltstrong.com/articles/test/',html)
  self.assertIsNone(reason)
  self.assertEqual(item['video']['id'],YT1)
  self.assertEqual(item['image'],f'https://i.ytimg.com/vi/{YT1}/hqdefault.jpg')
if __name__=='__main__':unittest.main(verbosity=2)
