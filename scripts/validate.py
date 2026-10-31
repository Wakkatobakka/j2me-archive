#!/usr/bin/env python3
"""Check source identities, generated page links, anchors, metadata and exports."""
from pathlib import Path
from html.parser import HTMLParser
from urllib.parse import urlsplit, unquote, parse_qs
from collections import Counter
import json, re, csv, sys, xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[1]
CONFIG=json.loads((ROOT/'config.json').read_text());BASE=CONFIG['base_url'].rstrip('/')+'/'
CAT=json.loads((ROOT/'data/catalog.json').read_text());ENTRIES=CAT['entries'];COUNTS=CAT['counts']
LIB=json.loads((ROOT/'data/library-index.json').read_text());FILES=json.loads((ROOT/'data/file-index.json').read_text())
INDEX={item['key']:item for item in LIB+FILES};errors=[];checks=Counter()
def check(condition,message):
    checks['assertions']+=1
    if not condition:errors.append(message)

class Document(HTMLParser):
    def __init__(self,text):
        super().__init__(convert_charrefs=True);self.ids=[];self.links=[];self.labels=[];self.inputs=[];self.h1=0;self.main=0;self.images=[];self.title=False;self.feed(text)
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if a.get('id'):self.ids.append(a['id'])
        if tag=='h1':self.h1+=1
        if tag=='main':self.main+=1
        if tag=='title':self.title=True
        if tag=='label' and a.get('for'):self.labels.append(a['for'])
        if tag in ('input','select'):self.inputs.append(a)
        if tag=='img':self.images.append(a)
        for key in ('href','src'):
            if key in a:self.links.append((tag,key,a[key]))

check(len(ENTRIES)==len({e['slug'] for e in ENTRIES}),'Duplicate page slugs')
check(len(ENTRIES)==len({e['id'] for e in ENTRIES}),'Duplicate catalog IDs')
check(len(INDEX)==len(LIB)+len(FILES),'Duplicate source keys')
check(sum(bool(e['omni']) for e in ENTRIES)==10,'Expected ten Omni recovery records')
check(len(ENTRIES)==991,'Expected 991 catalog entries')
check(COUNTS['directory_listings']==989,'Expected 989 directory listings')
check({e['id'] for e in ENTRIES if e['id'].startswith('ma:')}=={i['key'] for i in LIB if i['source']=='ma'},'The main catalog does not cover every directory listing')
check(len(LIB)==COUNTS['reference_records'],'Reference count mismatch')
check(len(FILES)==COUNTS['file_inventory_entries'],'File inventory count mismatch')
check(COUNTS['game_binaries_downloaded']==0,'Unexpected binary-download count')
check(COUNTS['exact_input_binary_matches_verified']==0,'Unexpected exact-build verification claim')
check(COUNTS['ma_detail_pages']==989,'The expanded source detail crawl is incomplete')
check(not any(i['extension']=='.mpn' for i in FILES),'Mophun file in J2ME file view')
check({i['extension'] for i in FILES}<={'.jar','.jad','.zip'},'Ancillary file in J2ME file view')
check(not any(p.name.upper().startswith('LICENSE') for p in ROOT.iterdir() if p.is_file()),'Unexpected repository license file')
for e in ENTRIES:
    check(bool(e['source_records']),'Catalog entry has no source: '+e['id'])
    check((ROOT/'games'/e['slug']/'index.html').exists(),'Missing title page: '+e['slug'])
    for ref in e['source_records']:check(ref['key'] in INDEX,'Missing source reference: '+ref['key'])

shards={}
for item in LIB+FILES:
    path=ROOT/'data'/item['part']
    if item['part'] not in shards:
        check(path.exists(),'Missing source shard: '+item['part'])
        if path.exists():shards[item['part']]=json.loads(path.read_text())
    check(item['id'] in shards.get(item['part'],{}),'Missing source record: '+item['key'])
    for slug in item['catalog_slugs']:check(any(e['slug']==slug for e in ENTRIES),'Broken catalog connection: '+slug)

documents={p:Document(p.read_text()) for p in ROOT.rglob('*.html')}
for path,doc in documents.items():
    rel=str(path.relative_to(ROOT))
    check(doc.h1==1,'Expected one H1: '+rel)
    check(doc.main==1,'Expected one main landmark: '+rel)
    check(doc.title,'Missing document title: '+rel)
    check(len(doc.ids)==len(set(doc.ids)),'Duplicate element ID: '+rel)
    for image in doc.images:check('alt' in image,'Image lacks alt text: '+rel)
    for label in doc.labels:check(label in doc.ids,'Label target is missing: '+rel+'#'+label)
    for tag,attr,href in doc.links:
        if not href:continue
        if href.startswith(BASE):local=href[len(BASE):];base=ROOT
        elif urlsplit(href).scheme or href.startswith('//'):continue
        else:local=href;base=path.parent
        url=urlsplit(local);dest=(base/unquote(url.path)).resolve() if url.path else path
        if dest.is_dir():dest=dest/'index.html'
        check(dest.is_relative_to(ROOT),'Link escapes repository: '+rel+' -> '+href)
        check(dest.exists(),'Broken local link: '+rel+' -> '+href)
        checks['local_links']+=1
        if url.fragment and dest in documents:check(unquote(url.fragment) in documents[dest].ids,'Broken fragment: '+rel+' -> '+href)
        if dest==ROOT/'library/record/index.html' and url.query:
            key=parse_qs(url.query).get('key',[''])[0];check(key in INDEX,'Unknown inspector source: '+key)

with (ROOT/'data/catalog.csv').open(encoding='utf-8-sig',newline='') as f:csv_rows=list(csv.DictReader(f))
check(len(csv_rows)==len(ENTRIES),'CSV catalog count mismatch')
check({r['record_id'] for r in csv_rows}=={e['id'] for e in ENTRIES},'CSV identities mismatch')
search=json.loads((ROOT/'data/search.json').read_text())
check({s['id'] for s in search}=={e['id'] for e in ENTRIES},'Search index identities mismatch')
for s in search:check(s['sources']>0,'Search result has no source: '+s['id'])
ET.parse(ROOT/'sitemap.xml');checks['html_pages']=len(documents);checks['source_records']=len(INDEX)
report={'passed':not errors,'checks':dict(checks),'errors':errors[:100]}
out=ROOT/'.validation';out.mkdir(exist_ok=True);(out/'report.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report,indent=2));sys.exit(1 if errors else 0)
