"""WATCH search regression checks: run automatically by existing Python test workflow."""
import json
import shutil
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

class SearchRelevanceTests(unittest.TestCase):
    def test_fishing_search_relevance_in_browser_js(self):
        if not shutil.which('node'):
            self.skipTest('Node.js is not installed on this test runner')
        code = r'''
const fs = require('fs');
const vm = require('vm');
const src = fs.readFileSync(process.argv[1], 'utf8');
const helper = src.slice(0, src.indexOf('\n(() => {'));
if (!helper.includes('const WatchSearch')) throw Error('Missing search helper');
const S = vm.runInNewContext(helper + '\nWatchSearch;', {});
const assert = (ok, explanation) => { if (!ok) throw Error(explanation); };
const item = fields => S.compile({
  title: '', tags: [], excerpt: '', content_headings: '', search_text: '',
  search_terms: [], ...fields
}, fields.tags || []);
const scored = (data, query) => S.evaluate(item(data), query);
const titleNight = {title: 'How to Catch Snook at Night', tags: ['Night Fishing']};
const commentContaminated = {title: 'Quick Fall Fishing Lure Strategy', excerpt: 'Adjust lure depth to fish activity', search_text:'a reader says night fishing after dark'};
const dayIncidental = {title:'How to Find Redfish on High Water', tags:['Redfish'], excerpt:'A better-than-average day out fishing', search_text:'Fish today, then tomorrow, a day later and during the day'};
const broadSearch = {title:'Best Paddletail Lures for Redfish', excerpt:'Adjust your search for feeding fish', search_text:'Search Search SEARCH for your favorite lures'};
const hatch = {title:'Why It Is Important to Match the Hatch in the Fall', tags:['Lure Selection'],search_text:'Match the hatch to choose a lure.'};
const tide = {title:'Redfish on Oyster Bars',tags:['Redfish','Oyster Bars','Tides'],excerpt:'How to fish outgoing tide near oyster bars'};
assert(scored(titleNight,'night fishing').score>0,'Relevant night lesson missing');
assert(scored({title:'Fishing Dock Lights for Snook'},'night fishing').score>0,'Synonym dock lights missing');
assert(scored(commentContaminated,'night fishing').score===0,'Incidental nighttime hit');
assert(scored(commentContaminated,'night').score===0,'Incidental night word hit');
assert(scored({title:'Lures That Work in Fall',excerpt:'Can also be effective at night'},'night fishing').score===0,'Incidental night excerpt hit');
assert(scored(dayIncidental,'day').score===0,'Incidental day hit');
assert(scored(dayIncidental,'today').score===0,'Substring match for today');
assert(scored(broadSearch,'search').score===0,'Generic article-body search hit');
assert(scored(hatch,'match the hatch').score>0,'Match the hatch exact title should work');
assert(scored(tide,'redfish on outgoing tides around oyster bars').score>0,'Multi-topic fishing query missing');
assert(scored({title:'Redfish',tags:['Redfish']},'redfish').score>0,'Redfish tag missing');
assert(scored({title:'Redfish',search_terms:['night fishing'],search_text:'night fishing'},'night fishing').score===0,'Stale keyword match');
assert(scored({title:'Day Fishing vs Night Fishing'},'day').score>0,'Day title word should match');
const short = scored({title:'Redfish in Marshes',search_text:'a tiny place with oyster bars'},'oyster bars');
assert(short.score===0,'Single incidental body phrase matched');
const repeated = scored({title:'Learning to Fish Structure',search_text:'oyster bars work. oyster bars can help. oyster bars can hold fish.'},'oyster bars and structure');
// An all-term query can require multiple high-signal concepts; no arbitrary OR results.
assert(repeated.score===0,'Broad body phrase incorrectly matched');
assert(scored({title:'Redfish'},'snook').score===0,'Unrelated species match');
console.log('PASS: WATCH search regression checks');
'''
        completed = subprocess.run(
            ['node', '-e', code, str(ROOT/'app.js')], text=True,
            capture_output=True, timeout=12
        )
        self.assertEqual(completed.returncode, 0, completed.stderr + completed.stdout)
        self.assertIn('PASS:', completed.stdout)

if __name__ == '__main__': unittest.main()
