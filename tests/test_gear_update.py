"""Regression tests for featured gear, SSO URLs and latest WATCH code."""
import sys,unittest
from pathlib import Path
from urllib.parse import quote
from bs4 import BeautifulSoup
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from sync_catalog import extract_gear

class GearUpdateTests(unittest.TestCase):
    def test_featured_gear_seven_links_and_section_boundary(self):
        links=[]
        for i in range(7):
            url=f'https://www.saltstrong.com/shopify-sso/product.php?shopurl={quote("https://fishstrong.com/products/gear-"+str(i),safe="")}'
            links.append(f'<li><a href="{url}">Item {i}</a></li>')
        html='<article><h2>Featured Gear</h2><div><ul>'+''.join(links)+'</ul></div><h2>Other content</h2><a href="https://fishstrong.com/products/unrelated">unrelated</a></article>'
        gear=extract_gear(BeautifulSoup(html,'html.parser'))
        self.assertEqual(len(gear),7)
        self.assertTrue(all('shopify-sso/product.php' in g['url'] for g in gear))
    def test_direct_product_fallback_and_safety(self):
        html='''<main><a href="https://fishstrong.com/products/prawn-xt">Prawn XT</a>
        <a href="https://fishstrong.com/">Shop Homepage</a>
        <a href="https://notfishstrong.com/products/phony">Fake</a></main>'''
        self.assertEqual([x['name'] for x in extract_gear(BeautifulSoup(html,'html.parser'))],['Prawn XT'])
    def test_frontend_sso_and_header_and_quality(self):
        js=(ROOT/'app.js').read_text()
        css=(ROOT/'styles.css').read_text()
        self.assertIn('const ssoGearUrl',js)
        self.assertIn('parsed.pathname === \'/shopify-sso/product.php\'',js)
        self.assertIn('encodeURIComponent(url)',js)
        self.assertIn('maxresdefault.jpg',js)
        self.assertIn('naturalWidth <= 320',js)
        self.assertIn('topic-spotlight',js)
        self.assertIn('www.saltstrong.com/courses/',js)
        self.assertIn('.brand strong{position:relative;top:4px',css)
    def test_scraper_generates_maxres_references(self):
        self.assertIn('maxresdefault.jpg',(ROOT/'watch_last100.py').read_text())
        self.assertIn('maxresdefault.jpg',(ROOT/'sync_catalog.py').read_text())

if __name__=='__main__':unittest.main()
