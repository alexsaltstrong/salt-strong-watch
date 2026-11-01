#!/usr/bin/env python3
"""Add content-derived WATCH tags to last100-catalog.json; save a review file."""
import argparse,json
from pathlib import Path
from tagger import enrich

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--input',default='last100-catalog.json')
    p.add_argument('--output',default='last100-enriched.json')
    p.add_argument('--suggestions',default='watch-tag-suggestions.json')
    a=p.parse_args()
    data=json.loads(Path(a.input).read_text(encoding='utf-8'))
    data['items'],proposals=enrich(data['items'])
    data['tagging_method']='article text/title/heading keyword rules; proposed topics require review'
    Path(a.output).write_text(json.dumps(data,indent=2,ensure_ascii=False)+'\n',encoding='utf8')
    Path(a.suggestions).write_text(json.dumps({'suggestions':proposals},indent=2)+'\n',encoding='utf8')
    print(f'Enriched {len(data["items"])} articles with content tags; {len(proposals)} candidate new topics for review.')
if __name__=='__main__':main()
