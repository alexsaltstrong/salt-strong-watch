import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import populate_catalog


class CatalogTests(unittest.TestCase):
    def test_public_shortcodes_generate_thumbnail_and_player_id(self):
        urls = [f'https://www.saltstrong.com/articles/example-{i}/' for i in range(2)]
        ids = ['AbCdef_1234', 'XyZ234_-abc']
        pages = {u: f'<html><main><h1>Example {i}</h1>[youtube_embed id="{ids[i]}"]</main></html>' for i, u in enumerate(urls)}
        with tempfile.TemporaryDirectory() as temp:
            seed = Path(temp) / 'catalog.sample.json'
            output = Path(temp) / 'catalog.json'
            audit = Path(temp) / 'import-audit.json'
            seed.write_text(json.dumps({'items': [{'id': str(i), 'title': f'Example {i}', 'url': u,
                                                  'gear': [{'name': 'Dr Popper', 'url': 'https://fishstrong.com/products/test'}],
                                                  'video': None} for i, u in enumerate(urls)]}))
            args = ['populate_catalog.py', '--seed', str(seed), '--output', str(output), '--audit', str(audit), '--no-browser']
            with patch.object(populate_catalog, 'get', side_effect=lambda u: pages[u]), patch.object(sys, 'argv', args):
                populate_catalog.main()
            result = json.loads(output.read_text())
            self.assertEqual(result['stats']['resolved'], 2)
            self.assertEqual([i['video']['id'] for i in result['items']], ids)
            self.assertTrue(result['items'][0]['image'].endswith('AbCdef_1234/hqdefault.jpg'))
            self.assertEqual(result['items'][0]['gear'][0]['name'], 'Dr Popper')


if __name__ == '__main__':
    unittest.main()
