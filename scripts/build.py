#!/usr/bin/env python3
"""Build the complete GitHub Pages site from the checked-in metadata. No network."""
from pathlib import Path, PurePosixPath
from collections import Counter
from functools import lru_cache
from urllib.parse import quote, urlencode
import html, json, csv, math, re, hashlib, argparse

ROOT=Path(__file__).resolve().parents[1]
CONFIG=json.loads((ROOT/'config.json').read_text())
def refresh_indexes():
    """Refresh search text, source indexes and counts after an offline metadata edit."""
    data=json.loads((ROOT/'data/catalog.json').read_text());index=[];records={}
    counts_by_source=Counter()
    def write(name,value):
        (ROOT/'data'/name).write_text(json.dumps(value,ensure_ascii=False,separators=(',',':'))+'\n')
    for p in sorted((ROOT/'data/sources').glob('*/*.json')):
        source_name=p.parent.name;shard=json.loads(p.read_text())
        for ident,r in shard.items():
            key=source_name+':'+ident;assert key not in records,'Duplicate source identity: '+key
            records[key]=r;counts_by_source[source_name]+=1
            f=next((f for f in r.get('page_fact_tables',[]) if f.get('Platform')=='J2ME'),{})
            index.append({'key':key,'source':source_name,'id':ident,'part':str(p.relative_to(ROOT/'data')),
                          'title':r.get('title') or r.get('filename') or r.get('name'), 'source_url':r['source_url'],
                          'genre':r.get('genre') or r.get('source_category_label') or f.get('Genre',''),
                          'vendor':r.get('publisher') or r.get('source_vendor_label') or r.get('developer') or f.get('Publisher') or f.get('Developer',''),
                          'variant_count':len(r.get('variants',r.get('download_variants_as_listed',[]))),
                          'extension':r.get('extension') or ('.zip' if source_name=='ia' else ''),
                          'bytes_reported':r.get('bytes_reported'),'catalog_slugs':[]})
    lookup={i['key']:i for i in index};search=[]
    for e in data['entries']:
        parts=[e['title'],*e['aliases'],e['listed_year'] or '',*e['genres']];languages=set();resolutions=set();groups=0
        for ref in e['source_records']:
            r=records[ref['key']];lookup[ref['key']]['catalog_slugs'].append(e['slug'])
            parts.extend([r.get('title'),r.get('developer'),r.get('publisher'),r.get('source_vendor_label')])
            for f in r.get('page_fact_tables',[]):
                if f.get('Platform')=='J2ME':parts.extend(f.values())
            variants=r.get('variants',r.get('download_variants_as_listed',[]));groups+=len(variants)
            for v in variants:
                parts.append(v['source_label']);parts.extend(v.get('language_flags_as_listed',[]));parts.extend(v.get('filenames',[]))
                languages.update(v.get('language_flags_as_listed',[]))
                for pair in v.get('resolution_labels',[]):resolutions.add('x'.join(map(str,pair)))
        if e['omni']:parts.extend([e['omni']['edition'],e['omni']['input_files']])
        e['source_variant_groups']=groups;e['languages_as_labeled']=sorted(languages);e['resolutions_as_labeled']=sorted(resolutions)
        search.append({'id':e['id'],'slug':e['slug'],'title':e['title'],'year':e['listed_year'],'genres':e['genres'],
                       'omni':bool(e['omni']),'variants':groups,'sources':len(e['source_records']),
                       'search':' '.join(dict.fromkeys(str(x) for x in parts if x))})
    library=[i for i in index if i['source'] in ('ma','kb','rg')];files=[i for i in index if i['source'] in ('vault','ia')]
    data['counts'].update(catalog_entries=len(data['entries']),directory_listings=counts_by_source['ma'],
                          omni_recoveries=sum(bool(e['omni']) for e in data['entries']),
                          ma_detail_pages=sum(r.get('detail_page_read',False) for k,r in records.items() if k.startswith('ma:')),
                          ma_labeled_variants=sum(len(r.get('download_variants_as_listed',[])) for k,r in records.items() if k.startswith('ma:')),
                          kahvibreak_rows=counts_by_source['kb'],rg_records=counts_by_source['rg'],
                          rg_variant_groups=sum(len(r.get('variants',[])) for k,r in records.items() if k.startswith('rg:')),
                          reference_records=len(library),file_inventory_entries=len(files),
                          vault_jar_entries=sum(i['source']=='vault' and i['extension']=='.jar' for i in files),
                          vault_jad_entries=sum(i['source']=='vault' and i['extension']=='.jad' for i in files),ia_archive_entries=counts_by_source['ia'])
    write('catalog.json',data);write('search.json',search);write('library-index.json',library);write('file-index.json',files)
    snapshot=json.loads((ROOT/'data/snapshot.json').read_text());snapshot['counts']=data['counts'];write('snapshot.json',snapshot)
    return data,library,files

DATA,LIB,FILES=refresh_indexes()
ENTRIES=DATA['entries'];COUNTS=DATA['counts'];BASE=CONFIG['base_url'].rstrip('/')+'/'
INDEX={x['key']:x for x in LIB+FILES}
ENTRY_BY_SLUG={e['slug']:e for e in ENTRIES}
PAGES=[];PAGE_SIZE=36;REF_PAGE_SIZE=40
SOURCES={'ma':'My Abandonware','kb':'Kahvibreak','rg':'RG-Backup','vault':'J2ME Vault mirror','ia':'Internet Archive'}

def esc(value):return html.escape(str(value if value is not None else ''),quote=True)
def num(value):return f'{value:,}'
def read_json(path):return json.loads(path.read_text())
@lru_cache(maxsize=None)
def part(path):return read_json(ROOT/'data'/path)
def source(key):
    i=INDEX[key];return part(i['part'])[i['id']]
def root_for(path):return '../'*(len(PurePosixPath(path).parts)-1)
def external(url,label,cls=''):
    assert url.startswith(('https://','http://'))
    return f'<a href="{esc(url)}" rel="noopener noreferrer" target="_blank" class="{esc(cls)}">{label}</a>'
def plain_md(text):
    # The guide contains only inline code and simple Markdown links in these fields.
    pieces=[];last=0
    for m in re.finditer(r'`([^`]+)`|\[([^\]]+)\]\((https?://[^\s)]+)\)',text or ''):
        pieces.append(esc(text[last:m.start()]))
        pieces.append('<code>'+esc(m[1])+'</code>' if m[1] else external(m[3],esc(m[2])))
        last=m.end()
    pieces.append(esc((text or '')[last:]));return ''.join(pieces)
def facts(rows):
    return '<dl class="facts">'+''.join(f'<dt>{esc(k)}</dt><dd>{v}</dd>' for k,v in rows if v)+'</dl>'
def page(path,title,description,content,active='',body_attrs='',root_override=None):
    root=root_override if root_override is not None else root_for(path)
    canonical=BASE+path.removesuffix('index.html')
    nav=[('catalog/index.html','Catalog','catalog'),('recovered/index.html','Wakka’s recoveries','recovered'),('field-notes/index.html','Field notes','notes'),('sources/index.html','Sources','sources')]
    links=''.join(f'<a href="{root}{href}"'+(' aria-current="page"' if key==active else '')+f'>{label}</a>' for href,label,key in nav)
    owner=esc(CONFIG['owner']);repo=f'https://github.com/{CONFIG["owner"]}/{CONFIG["repository"]}'
    text=f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="color-scheme" content="dark"><meta name="theme-color" content="#0c111a"><meta name="description" content="{esc(description)}">
<meta property="og:type" content="website"><meta property="og:title" content="{esc(title)}"><meta property="og:description" content="{esc(description)}"><meta property="og:url" content="{esc(canonical)}"><meta property="og:image" content="{esc(BASE)}assets/banner.png"><meta name="twitter:card" content="summary_large_image">
<link rel="canonical" href="{esc(canonical)}"><link rel="icon" href="{root}assets/favicon.svg" type="image/svg+xml"><link rel="stylesheet" href="{root}assets/styles.css">
<script defer src="{root}assets/search-core.js"></script><script defer src="{root}assets/app.js"></script><title>{esc(title)}</title></head>
<body data-root="{root}" {body_attrs}><a class="skip" href="#main">Skip to content</a>
<header class="site-header"><div class="shell nav"><a class="brand" href="{root}index.html" aria-label="J2ME Archive home"><span class="brand-icon" aria-hidden="true"></span><span>J2ME <b>/</b> ARCHIVE</span></a><nav class="top-nav" aria-label="Main navigation">{links}<a class="external" href="{repo}" rel="noopener noreferrer" target="_blank">The project ↗</a></nav></div></header>
<main id="main">{content}</main>
<footer class="foot"><div class="shell"><div class="footer-top"><div><a class="brand" href="{root}index.html"><span>THE LOST CATALOG <b>/</b> J2ME</span></a><p>Created and maintained by <a href="https://github.com/{owner}">{owner}</a>. An independent guide to pocket gaming history, with the evidence left attached.</p></div><nav class="archive-links" aria-label="More from Wakka"><a href="https://wakkatobakka.github.io/">The workshop ↗</a><a href="https://wakkatobakka.github.io/qualcomm-brew-archive/">Qualcomm BREW</a><a href="https://wakkatobakka.github.io/zeebo-archive/">Zeebo</a><a href="https://wakkatobakka.github.io/exen-game-archive/">ExEn</a><a href="https://wakkatobakka.github.io/doja-archive/">DoJa</a></nav></div><div class="footer-bottom"><span>Catalog snapshot: October 30, 2026 · Game files remain with their sources.</span><span><a href="{root}sources/index.html">Source credits</a> · <a href="{repo}/issues">Report a correction</a></span></div></div></footer></body></html>'''
    dest=ROOT/path;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_text(text);PAGES.append(path)

def card(e,root):
    genre=' / '.join(e['genres']) or 'Genre not recorded'
    return f'''<a class="record" href="{root}games/{e['slug']}/index.html"><div><div class="record-top"><span>{esc(e['listed_year'] or 'YEAR UNRECORDED')} / J2ME</span>{'<span class="badge omni">OMNI RECOVERY</span>' if e['omni'] else '<span>SOURCE-LISTED</span>'}</div><h3>{esc(e['title'])}</h3></div><div class="record-bottom"><span>{esc(genre)}</span><span class="arrow" aria-hidden="true">↗</span></div></a>'''

def pager(current,total,url):
    if total<2:return ''
    nums=sorted(set([1,total,*range(max(1,current-2),min(total,current+2)+1)]))
    out=['<nav class="pagination" aria-label="Result pages">']
    if current>1:out.append(f'<a href="{url(current-1)}" aria-label="Previous page">←</a>')
    prev=0
    for i in nums:
        if prev and i-prev>1:out.append('<span aria-hidden="true">…</span>')
        out.append(f'<a href="{url(i)}"'+(' aria-current="page"' if i==current else '')+f' aria-label="Page {i}">{i}</a>');prev=i
    if current<total:out.append(f'<a href="{url(current+1)}" aria-label="Next page">→</a>')
    return ''.join(out)+'</nav>'

def page_heading(kicker,title,desc):
    return f'<div class="shell page-heading"><div class="kicker">{kicker}</div><h1>{title}</h1><p>{desc}</p></div>'

def home():
    featured=[('nowhere','N/W'),('ratchet-clank-going-mobile','R&amp;C'),('silent-hill-orphan','S/H'),('god-of-war-betrayal','G/W')]
    cards=''
    for number,(slug,glyph) in enumerate(featured,1):
        e=ENTRY_BY_SLUG[slug]
        cards+=f'<a class="recovery-card" href="games/{slug}/index.html"><div class="card-top"><span>0{number} / OMNI RECOVERY</span><span>↗</span></div><div class="card-glyph" aria-hidden="true">{glyph}</div><div><h3>{esc(e["title"])}</h3><p>{esc(e["omni"]["edition"])}</p></div></a>'
    body=f'''<section class="shell hero"><div><div class="eyebrow">WAKKATOBAKKA’S POCKET GAMING ARCHIVES</div><h1>Before the app store,<br><em>there was the .jar.</em></h1><p class="hero-lede">Games tucked into tiny phones. A different build for seemingly every screen. Follow the titles, the editions, and the trails they left behind.</p><div class="buttons"><a class="btn btn-primary" href="catalog/index.html">Explore {num(COUNTS['catalog_entries'])} entries <span aria-hidden="true">↘</span></a><a class="btn btn-secondary" href="recovered/index.html">Wakka’s recoveries <span aria-hidden="true">→</span></a></div><p class="hero-note">A source-linked catalog, starting with the J2ME games brought back through Omni Player. Handset labels and title matches stay attached to their evidence.</p></div><img class="hero-art" src="assets/hero.svg" width="600" height="640" alt="An illustrated J2ME phone. Press start. Again. Beneath it: Small screens. Long afterlives."></section>
<section class="statband" aria-label="Catalog at a glance"><div class="shell stats"><div class="stat"><strong class="accent">{num(COUNTS['catalog_entries'])}</strong><span>individual catalog entries</span></div><div class="stat"><strong class="blue">10</strong><span>Omni recovery starting points</span></div><div class="stat"><strong>989</strong><span>J2ME directory listings</span></div><div class="stat"><strong>2000–15</strong><span>years listed in that directory</span></div></div></section>
<section class="shell section"><div class="section-head"><div><div class="kicker">THE ONES THAT STARTED THIS</div><h2>Back from the tiny screen.</h2></div><p>Four places to begin. Each page keeps Wakka’s recorded input edition separate from the other builds found along the way.</p></div><div class="recovery-grid">{cards}</div><div class="section-foot"><span>Ten J2ME entries, recorded in the public Omni Player game guide.</span><a class="text-link" href="recovered/index.html">Visit the whole recovery shelf →</a></div></section>
<section class="shell section split-note"><div><div class="kicker">THE SAME NAME IS ONLY THE START</div><h2>A game. A phone.<br><em>A very particular build.</em></h2><p>A familiar title can lead to different resolutions, languages, versions, and handset families. The interesting part is keeping those details together.</p><a class="text-link" href="field-notes/index.html">How this catalog follows the trail ↗</a></div><ol class="note-list"><li><span class="number">01</span><div><h3>Start with the title.</h3><p>Search the main catalog by title, alias, credit, or edition label. Every entry has its own page and an original source to follow.</p></div></li><li><span class="number">02</span><div><h3>Look at the editions.</h3><p>Handsets, versions, languages, and filenames remain as their sources list them. A JAR and its JAD descriptor belong to the same trail.</p></div></li><li><span class="number">03</span><div><h3>Keep the loose ends.</h3><p>Conflicting credits and uncertain matches are part of the record. A source listing is a lead; an exact recovered input takes more evidence.</p></div></li></ol></section>
<section class="shell section"><div class="reference-callout"><div><div class="kicker">THE RABBIT HOLE HAS A BASEMENT</div><h2>There’s a larger paper trail.</h2><p>Search {num(COUNTS['reference_records'])} attributed source records from My Abandonware, Kahvibreak, and RG-Backup, plus separate file inventories. These collections overlap, and some include other platforms.</p></div><a class="btn btn-secondary" href="library/index.html">Open the reference library <span aria-hidden="true">↗</span></a></div></section>'''
    page('index.html',CONFIG['title'],f'A source-linked J2ME catalog by Wakkatobakka: {COUNTS["catalog_entries"]} entries, ten Omni recoveries, and a larger reference library.',body)

def catalog_pages():
    total=math.ceil(len(ENTRIES)/PAGE_SIZE)
    years=sorted({e['listed_year'] for e in ENTRIES if e['listed_year']},reverse=True)
    genres=sorted({g for e in ENTRIES for g in e['genres']})
    for n in range(1,total+1):
        path='catalog/index.html' if n==1 else f'catalog/page/{n}/index.html';root=root_for(path)
        form=f'''<form class="toolbar" id="catalog-form" role="search" hidden><div class="field"><label for="search">Title, credit, handset, or edition</label><input id="search" name="q" type="search" placeholder="Try Nowhere, Nokia, 240x320…" autocomplete="off"></div><div class="field"><label for="year">Listed year</label><select id="year" name="year"><option value="">All years</option>{''.join(f'<option>{y}</option>' for y in years)}<option value="unknown">Not recorded</option></select></div><div class="field"><label for="genre">Genre as listed</label><select id="genre" name="genre"><option value="">All genres</option>{''.join(f'<option>{esc(g)}</option>' for g in genres)}<option value="unknown">Not recorded</option></select></div><div class="field"><label for="sort">Sort by</label><select id="sort" name="sort"><option value="title">Title A–Z</option><option value="oldest">Oldest first</option><option value="newest">Newest first</option><option value="recovered">Omni recoveries first</option></select></div><div class="filter-toggles"><label><input type="checkbox" name="omni" id="omni"> Wakka’s recoveries only</label><label><input type="checkbox" name="variants" id="variants"> Has external edition labels</label></div></form>'''
        start=(n-1)*PAGE_SIZE;batch=ENTRIES[start:start+PAGE_SIZE]
        body=page_heading('THE DOCUMENTED INDEX','Find something <em>forgotten.</em>',f'{num(len(ENTRIES))} entries: the 989 titles listed in My Abandonware’s J2ME directory, plus two additional Omni recoveries. Broader, unresolved source records live in the <a href="{root}library/index.html">reference library</a>.')
        body+=f'<section class="shell browse-layout" data-browser="catalog" data-page="{n}">{form}<noscript><p class="no-script">Browse all entries with the page links below. Enable JavaScript for search, filters, and sorting.</p></noscript><div class="result-meta"><span id="result-count" aria-live="polite"><strong>{start+1}–{start+len(batch)} of {num(len(ENTRIES))}</strong> catalog entries</span><button type="button" class="clear" id="clear-filters" hidden>Clear filters</button></div><div class="catalog-grid" id="results">'+''.join(card(e,root) for e in batch)+'</div><div id="pages">'+pager(n,total,lambda i:root+('catalog/index.html' if i==1 else f'catalog/page/{i}/index.html'))+f'</div><div class="download-links"><span>Catalog metadata:</span><a href="{root}data/catalog.csv" download>CSV ↓</a><a href="{root}data/catalog.json" download>JSON ↓</a><a href="{root}data/README.md">Field definitions</a><a href="{root}sources/index.html">Source register</a></div></section>'
        page(path,f'J2ME Catalog · Page {n} | The Lost Catalog',f'Browse {num(len(ENTRIES))} source-linked J2ME entries, with search by title, credit, handset and edition.',body,'catalog')

def recoveries_page():
    recovered=[e for e in ENTRIES if e['omni']]
    body=page_heading('WAKKA’S STARTING SHELF','The games that <em>came back.</em>','Ten J2ME entries from the public Omni Player game guide. These pages start with the recorded bridge inputs, then follow bibliographic and edition leads outward.')
    body+='<section class="shell browse-layout"><p class="notice"><strong>What “Omni recovery” means here:</strong> the title and input edition are recorded in Wakka’s public guide. This catalog has not independently tested or hash-matched the original JARs. See the linked guide for current setup and support details.</p><div class="catalog-grid">'+''.join(card(e,'../') for e in recovered)+'</div><div class="buttons"><a class="btn btn-primary" href="https://github.com/Wakkatobakka/Omni-Player/blob/main/GAME_GUIDE.md">Read the Omni game guide ↗</a><a class="btn btn-secondary" href="../catalog/index.html">Explore the full catalog →</a></div></section>'
    page('recovered/index.html','Wakka’s J2ME Recoveries | The Lost Catalog','The ten J2ME recovery entries recorded in Wakkatobakka’s public Omni Player game guide, with edition details and source leads.',body,'recovered')

def ma_variants(record):
    rows=record.get('download_variants_as_listed',[])
    if not rows:return '<p>No J2ME download labels were extracted from this source page. This does not establish whether a build survives elsewhere.</p>'
    body=f'<div class="variant-group"><h3>My Abandonware · {len(rows)} source labels</h3><p class="source-credit">Versions, handset names, languages, and sizes are transcribed labels. Labels have not been checked inside the files.</p><div class="table-wrap"><table class="variant-table"><thead><tr><th scope="col">Source edition label</th><th scope="col">Language flags</th><th scope="col">Source</th></tr></thead><tbody>'
    for row in rows:
        text=row['source_label']+' '+' '.join(row['language_flags_as_listed'])
        body+=f'<tr data-variant="{esc(text)}"><td>{esc(row["source_label"])}</td><td>{esc(", ".join(row["language_flags_as_listed"]) or "Not labeled")}</td><td>{external(row["source_download_reference"],"Listed file ↗")}</td></tr>'
    return body+'</tbody></table></div></div>'

def rg_variants(record):
    rows=record.get('variants',[])
    if not rows:return '<p>This source record has no file groups. It supplies a metadata lead, without establishing a surviving package.</p>'
    body=f'<div class="variant-group"><h3>RG-Backup · {len(rows)} source groups</h3><p class="source-credit">A group can contain a JAR and its JAD descriptor. Size values have no unit specified in the extracted source record.</p><div class="table-wrap"><table class="variant-table"><thead><tr><th scope="col">Handset / language label</th><th scope="col">Filenames as listed</th><th scope="col">Source size value</th></tr></thead><tbody>'
    for row in rows:
        text=row['source_label']+' '+' '.join(row['filenames'])
        body+=f'<tr data-variant="{esc(text)}"><td>{esc(row["source_label"])}</td><td class="file-stack">'+''.join('<code>'+esc(f)+'</code>' for f in row['filenames'])+f'</td><td>{esc(row["source_size_value"])} <small>(unit unspecified)</small></td></tr>'
    return body+'</tbody></table></div></div>'

def game_pages():
    for e in ENTRIES:
        path=f'games/{e["slug"]}/index.html';root='../../'
        records=[(ref,source(ref['key'])) for ref in e['source_records']]
        ma=[r for ref,r in records if ref['key'].startswith('ma:')]
        candidates=[(ref,r) for ref,r in records if not ref['key'].startswith('ma:')]
        tags=f'<span class="badge">{esc(e["listed_year"] or "YEAR NOT RECORDED")}</span><span class="badge">J2ME SOURCE RECORD</span>'
        if e['omni']:tags+='<span class="badge omni">OMNI RECOVERY</span>'
        if e['review_flags']:tags+='<span class="badge warning">RESEARCH NOTE</span>'
        deck=' / '.join(e['genres']) or 'A source-linked record in Wakka’s J2ME catalog.'
        body=f'<div class="shell detail-head"><nav class="breadcrumbs" aria-label="Breadcrumb"><a href="../../index.html">J2ME Archive</a><span>/</span><a href="../../catalog/index.html">Catalog</a><span>/</span><span>{esc(e["title"])}</span></nav><div class="detail-tags">{tags}</div><h1>{esc(e["title"])}</h1><p class="detail-deck">{esc(deck)}</p></div><div class="shell detail-layout"><div class="detail-content">'
        if e['omni']:
            s=e['omni']
            body+='<section class="detail-section" id="recovery"><div class="edition-box"><div class="kicker">WAKKA’S RECORDED INPUT</div><h2>The Omni recovery edition.</h2>'
            body+=facts([('Edition',esc(s['edition'])),('Input file',plain_md(s['input_files'])),('Recorded source',plain_md(s['recorded_source'])),('Source status',esc(s['source_status']))])
            body+=f'<p class="source-credit">Recorded in {external(s["source_url"],"Omni Player’s public game guide ↗")}. Edition details above belong to that recorded input. The source listings below have not been verified as byte-identical matches.</p></div></section>'
        if e['review_flags']:
            body+='<section class="detail-section" id="research"><h2>Loose ends worth keeping.</h2>'
            for f in e['review_flags']:
                body+=f'<div class="notice warning"><strong>{esc(f["issue"])}</strong><ul>'+''.join(f'<li>{esc(c["source"])}: {esc(c["claim"])}</li>' for c in f['claims'])+f'</ul>{esc(f["decision"])}</div>'
            body+='</section>'
        body+='<section class="detail-section" id="record"><h2>The bibliographic record.</h2>'
        if ma:
            r=ma[0];tables=r.get('page_fact_tables',[])
            specific=[f for f in tables if f.get('Platform')=='J2ME']
            selected=specific[0] if specific else {}
            if selected:
                body+=facts([(k,esc(v)) for k,v in selected.items()])
                if len(tables)>1:body+='<p class="source-credit">This source page also covers other platforms. The table above is the table explicitly labeled J2ME.</p>'
            else:
                body+=facts([('Source title',esc(r['title'])),('Listed year',esc(r['listed_year'])),('Directory platform',esc(r['listed_platforms']))])
                if tables:body+='<p class="notice">The source page’s other fact tables are not explicitly scoped to J2ME. They are retained in the source metadata without assigning their credits to this edition.</p>'
            body+=f'<p class="source-credit">As listed by {external(r["source_url"],"My Abandonware ↗")}. Source facts and dates are bibliographic claims, rather than verification of an original package.</p>'
        else:
            body+='<p>This entry starts with Wakka’s recorded Omni input. The research crawl found title-level leads in the sources below, but no matching entry in the 989-title My Abandonware directory snapshot.</p>'
        body+='</section>'
        body+='<section class="detail-section" id="editions"><h2>Follow the edition trail.</h2><p>Source labels can identify useful candidates. A matching name, handset, or language label alone does not prove that a file matches the recovered input.</p>'
        if e['omni']:
            terms={'age-of-empires-iii':'Age Empires','digital-devil-story-megami-tensei':'Megami','god-of-war-betrayal':'God War','nowhere':'Nowhere','ratchet-clank-going-mobile':'Ratchet','silent-hill-orphan':'Silent Hill','spider-man-doc-ock':'DocOck','the-sims-2-pets':'Sims Pets','the-witcher-crimson-trail':'Witcher','resident-evil-uprising':'Uprising'}
            file_url=root+'files/index.html?'+urlencode({'q':terms.get(e['slug'],e['title'])})
            body+=f'<p class="source-credit"><a href="{esc(file_url)}">Search the separate file inventories for filename leads →</a>. Results can include other editions or related titles; they have not been matched to this input.</p>'
        if any(r.get('download_variants_as_listed') or r.get('variants') for ref,r in records):
            body+='<div class="variant-search" hidden><label for="variant-query">Find an edition label or filename</label><input type="search" id="variant-query" placeholder="Try K790, English, 240x320…" autocomplete="off"><span id="variant-count" class="source-credit" aria-live="polite"></span></div><p class="notice" id="variant-empty" hidden>No edition labels match that search. Clear the field to see every label.</p>'
        for r in ma:body+=ma_variants(r)
        for ref,r in candidates:
            if ref['key'].startswith('rg:'):
                body+='<details><summary>'+esc(r['title'])+f' · RG-Backup / {esc(r["source_collection"])} · {len(r["variants"])} file groups</summary><div class="details-body"><p>Title-level candidate. The source vendor label is <strong>'+esc(r.get('source_vendor_label') or 'not recorded')+'</strong>; it is not silently reassigned as a developer or publisher credit.</p>'+rg_variants(r)+f'<p class="source-credit">{external(r["source_url"],"Pinned metadata record ↗")} · {external(r["source_viewer_url"],"Source viewer ↗")}</p></div></details>'
        if not ma and not any(ref['key'].startswith('rg:') for ref,r in candidates):body+='<p>No handset-level file groups are attached to this entry in the current snapshot.</p>'
        body+='</section><section class="detail-section" id="sources"><h2>The sources, side by side.</h2><p>These references remain separate records. A normalized title or reviewed alias supplies a candidate connection; it does not settle platform, credits, or build identity.</p><div class="source-cards">'
        for ref,r in records:
            key=ref['key'];src=INDEX[key]['source']
            rows=[('Source title',esc(r.get('title','')))]
            if src=='kb':rows+=[('Genre',esc(r.get('genre'))),('Developer',esc(r.get('developer'))),('Publisher',esc(r.get('publisher'))),('Platform scope','Mixed J2ME / Mophun table; no per-row platform field')]
            elif src=='rg':rows+=[('Source vendor',esc(r.get('source_vendor_label'))),('Category',esc(r.get('source_category_label'))),('Added to source',esc(r.get('source_added_text')))]
            else:rows+=[('Listed year',esc(r.get('listed_year'))),('Directory platform','J2ME')]
            viewer=root+'library/record/index.html?'+urlencode({'key':key})
            body+=f'<article class="source-card"><h3>{esc(SOURCES[src])}</h3>'+facts(rows)+f'<a class="text-link" href="{esc(viewer)}">Inspect this source record →</a>'+external(r['source_url'],'Visit the original source ↗','text-link')+'</article>'
        body+='</div></section><section class="detail-section" id="limits"><h2>What this page establishes.</h2><p>This is an attributed catalog record. No original game package was downloaded, executed, or hashed for this site. File survival, present-day download availability, emulator compatibility, and exact input matches remain separate questions.</p>'
        issue='https://github.com/'+CONFIG['owner']+'/'+CONFIG['repository']+'/issues/new?'+urlencode({'title':'Catalog correction: '+e['title']})
        body+=f'<p>Found a missing credit or a stronger source? {external(issue,"Report the detail to Wakka ↗")}. Wakka reviews reports and maintains the catalog.</p></section></div><aside class="aside" aria-label="On this page"><h2>IN THIS RECORD</h2><div class="aside-links">'
        if e['omni']:body+='<a href="#recovery">The Omni input</a>'
        if e['review_flags']:body+='<a href="#research">Research notes</a>'
        body+='<a href="#record">Bibliographic record</a><a href="#editions">Edition trail</a><a href="#sources">Source comparison</a><a href="#limits">Evidence limits</a></div><p>Titles, source rows, edition labels, and files are different things. This catalog keeps their units visible.</p></aside></div>'
        page(path,e['title']+' | J2ME Archive',f'Source-linked J2ME metadata for {e["title"]}, including recorded editions, credits where listed, and research limits.',body,'catalog')

def source_row(item,root,is_file=False):
    r=source(item['key']);key=item['key'];viewer=root+'library/record/index.html?'+urlencode({'key':key})
    label=SOURCES[item['source']]
    if is_file:detail=(num(item['bytes_reported'])+' bytes reported') if item.get('bytes_reported') is not None else 'Size not recorded'
    else:detail=(str(item['variant_count'])+' source edition groups') if item['variant_count'] else (item['genre'] or 'Bibliographic source record')
    vendor=(item['extension'].upper().lstrip('.')+' · '+detail) if is_file else (item['vendor'] or 'Credit not recorded')
    return f'<div class="library-row'+(' file-row' if is_file else '')+f'"><div><h3><a href="{esc(viewer)}">{esc(item["title"])}</a></h3><p>{esc(detail)} · {external(r["source_url"],"Original source ↗")}</p></div><span class="vendor">{esc(vendor)}</span><span class="badge">{esc(label)}</span><a href="{esc(viewer)}" class="arrow" aria-label="Inspect {esc(item["title"])}">↗</a></div>'

def reference_pages(is_file=False):
    name='files' if is_file else 'library';items=FILES if is_file else LIB
    items=sorted(items,key=lambda i:(i['title'] or '').casefold());total=math.ceil(len(items)/REF_PAGE_SIZE)
    choices=[('vault','J2ME Vault mirror'),('ia','Internet Archive')] if is_file else [('ma','My Abandonware'),('kb','Kahvibreak'),('rg','RG-Backup')]
    for n in range(1,total+1):
        path=f'{name}/index.html' if n==1 else f'{name}/page/{n}/index.html';root=root_for(path)
        kicker='FILENAMES, WITH THEIR PROVENANCE' if is_file else 'THE WIDER SOURCE TRAIL'
        title='The file <em>inventories.</em>' if is_file else 'Down the <em>rabbit hole.</em>'
        description=(f'{num(len(items))} file references: JARs and JAD descriptors listed by the J2ME Vault mirror, plus 25 archives listed by an Internet Archive item. File counts are not game counts.' if is_file else f'Search {num(len(items))} attributed source records. Collections overlap; Kahvibreak also includes Mophun, and title matches here remain leads for further research.')
        body=page_heading(kicker,title,description)
        source_options=''.join(f'<option value="{key}">{esc(label)}</option>' for key,label in choices)
        extra='<div class="field"><label for="extension">File label</label><select name="extension" id="extension"><option value="">All files</option><option value=".jar">JAR candidates</option><option value=".jad">JAD descriptors</option><option value=".zip">Archive packages</option></select></div>' if is_file else '<div class="field"><label for="scope">Catalog connection</label><select id="scope" name="scope"><option value="">All source records</option><option value="linked">Linked to main catalog</option><option value="unlinked">Wider research leads</option></select></div>'
        form=f'<form class="toolbar" id="reference-form" role="search" hidden><div class="field"><label for="search">'+('Filename or source' if is_file else 'Title, credit, or source category')+f'</label><input type="search" id="search" name="q" placeholder="'+('Try Ratchet, Silent Hill, .jar…' if is_file else 'Try Gameloft, Nowhere, Sonic…')+f'" autocomplete="off"></div><div class="field"><label for="source">Source collection</label><select name="source" id="source"><option value="">All sources</option>{source_options}</select></div>{extra}<div class="field"><label for="sort">Sort by</label><select id="sort" name="sort"><option value="title">Title A–Z</option><option value="reverse">Title Z–A</option></select></div></form>'
        start=(n-1)*REF_PAGE_SIZE;batch=items[start:start+REF_PAGE_SIZE]
        body+=f'<section class="shell browse-layout" data-browser="{name}" data-page="{n}"><p class="notice">'+('A filename is a discovery lead. JAR extensions do not verify MIDP compatibility; source-reported hashes have not been measured from downloaded game files. Mophun and ancillary mirror files are excluded from this view. ' if is_file else 'The main catalog has a narrower scope. This library preserves the source records separately, including unresolved and potentially non-J2ME entries. ')+f'<a href="{root}'+('library/index.html">Browse title sources' if is_file else 'files/index.html">Browse file inventories')+f'</a> · <a href="{root}sources/index.html">Read the source notes</a>.</p>{form}<noscript><p class="no-script">Use the page links below to browse every source record. Each row also links directly to its original source. The local record inspector requires JavaScript.</p></noscript><div class="result-meta"><span id="result-count" aria-live="polite"><strong>{start+1}–{start+len(batch)} of {num(len(items))}</strong> '+('file references' if is_file else 'source records')+'</span><button class="clear" type="button" id="clear-filters" hidden>Clear filters</button></div><div class="library-list" id="results">'+''.join(source_row(i,root,is_file) for i in batch)+'</div><div id="pages">'+pager(n,total,lambda i:root+(f'{name}/index.html' if i==1 else f'{name}/page/{i}/index.html'))+'</div></section>'
        page(path,('File Inventories' if is_file else 'Reference Library')+f' · Page {n} | J2ME Archive',description,body,'sources')

def inspector_page():
    body=page_heading('AN ATTRIBUTED SOURCE RECORD','Inspect the <em>evidence.</em>','A source record keeps its own field names, platform scope, edition labels, and provenance. Connections to the main catalog are discovery leads.')
    body+='<div class="shell browse-layout"><div id="source-record" aria-live="polite"><p class="loading">Loading the selected source record…</p></div><noscript><p class="no-script">The local inspector requires JavaScript. The <a href="../index.html">reference library</a> provides an original-source link for every record.</p></noscript></div>'
    page('library/record/index.html','Source Record Inspector | J2ME Archive','Inspect the original metadata fields, file labels and provenance behind a J2ME research lead.',body,'sources','data-inspector="true"')

def notes_page():
    body=page_heading('FIELD NOTES','Keep the game.<br><em>Keep its story.</em>','A catalog for the games Wakka brought back—and the much larger set of trails still worth following.')
    body+='''<section class="shell browse-layout"><article class="prose"><h2>Why this one exists.</h2><p>The BREW, Zeebo, ExEn, and DoJa catalogs follow different corners of the same pocket gaming rabbit hole. This J2ME catalog starts with the ten games documented in Omni Player’s public guide, then reaches into larger bibliographic collections.</p><p>The first public catalog joins 989 explicitly labeled J2ME directory listings with two additional Omni recovery titles. That gives each entry a stable page without pretending the wider research collections have already been reconciled into one definitive game list.</p><h2>One title can have many editions.</h2><p>Source labels show different screen sizes, handset families, versions, and languages. A filename can be renamed by a collector; a JAR can be paired with a JAD descriptor. Two matching titles do not establish matching files.</p><p>The recovery pages preserve the recorded bridge input separately. A Sony Ericsson K790 listing for <a href="../games/nowhere/index.html">Nowhere</a>, for example, is a useful candidate for the K790 input in the guide. It still needs a comparison with that original input to establish identity.</p><h2>Three different kinds of evidence.</h2><ul><li><strong>Omni recovery record:</strong> title and input edition recorded by Wakka in the public game guide. This is a report of that guide, not a new compatibility test.</li><li><strong>Source-listed metadata:</strong> a title, date, credit, or edition label transcribed from an attributed source. The source can be mistaken or incomplete.</li><li><strong>Title-level candidate:</strong> a connection made by a reviewed alias or normalized title. It helps discovery without establishing the same platform or build.</li></ul><h2>What stays unresolved.</h2><p><a href="../games/resident-evil-uprising/index.html">Resident Evil: Uprising</a> has conflicting creator labels between the guide and external records. <a href="../games/the-witcher-crimson-trail/index.html">The Witcher: Crimson Trail</a> has a language distinction that a matching Nokia N73 label does not resolve. Those differences remain visible on their pages.</p><p>Digital Devil Story: Megami Tensei is labeled J2ME in the starting sources. A broad Java platform label is not enough to settle every runtime-family distinction, including DoJa versus standard MIDP. The original runtime metadata has not been inspected here.</p><h2>How matches were made.</h2><p>The main directory titles are compared with the bibliographic sources after Unicode normalization, case folding, punctuation removal, and converting “&amp;” to “and.” Explicit aliases are also used for the ten recovery titles. Every such link remains a title-level candidate. No fuzzy title score is used to silently combine records.</p><p>The file inventory is separate: it preserves source-listed filenames, sizes, and reported hashes without assigning those files to canonical games by guesswork. The J2ME Vault mirror attributes its material to Kahvibreak, so a matching record in both is not independent corroboration.</p><h2>How to read the numbers.</h2><p>A catalog entry, a source row, an edition-label group, and a file are different units. Source collections overlap. Their totals are never added together as a count of distinct games. Release years come from a platform-scoped fact table or the explicit J2ME directory; RG’s date-added field remains a date added to that source.</p><h2>Created and maintained by Wakka.</h2><p>The original site presentation, catalog organization, and artwork are Wakkatobakka’s work. Source communities retain credit for their preservation and metadata. Game binaries, source descriptions, cover art, and screenshots are not bundled.</p><p>Report a concrete error, missing credit, or broken link through <a href="https://github.com/Wakkatobakka/j2me-archive/issues">GitHub Issues</a>, including a source where possible. Wakka reviews those reports and publishes updates.</p><div class="buttons"><a class="btn btn-primary" href="../catalog/index.html">Explore the catalog →</a><a class="btn btn-secondary" href="../sources/index.html">Read the source register →</a></div></article></section>'''
    page('field-notes/index.html','Field Notes | J2ME Archive','How Wakkatobakka’s J2ME catalog separates recovered inputs, source claims, handset editions, and unresolved title matches.',body,'notes')

def sources_page():
    snap=read_json(ROOT/'data/snapshot.json')
    body=page_heading('THE EVIDENCE LEFT ATTACHED','The people.<br><em>The paper trail.</em>','The original collectors and catalogers made these trails possible. Every displayed source claim keeps an attribution and a link back.')
    records=[('Wakkatobakka / Omni Player','https://github.com/Wakkatobakka/Omni-Player/blob/main/GAME_GUIDE.md','10 publicly recorded J2ME recovery entries','The game guide supplies the starting titles and recorded input editions. Exact original files and acquisition pages remain unknown for some entries. The guide’s current support details can change independently of this snapshot.'),('My Abandonware / Codestible and credited contributors','https://www.myabandonware.com/browse/platform/j2me/',f'989 directory listings · {num(COUNTS["ma_detail_pages"])} detail pages read · {num(COUNTS["ma_labeled_variants"])} J2ME file labels','All 66 directory pages were read. Only explicitly J2ME-scoped download labels are used. Other-platform fact tables are retained in the source metadata without assigning their credits to a J2ME build. Source prose and artwork are excluded.'),('Kahvibreak / Flashpoint Archive and curation community','https://flashpointarchive.org/datahub/Kahvibreak_Game_List','5,627 rows in the public version 1.6 table','The project includes J2ME and Mophun. This table lacks a per-row platform column, so its rows remain bibliographic research leads. Developer and publisher fields are displayed as claims by this source.'),('RG-Backup / remixer-dec / original rugame.mobi contributors','https://github.com/remixer-dec/rg-backup',f'9,932 records · {num(COUNTS["rg_variant_groups"])} source file groups','Only games and cgames sections are included; application and Symbian sections were excluded. Vendor stays vendor, date added stays date added, and size units remain unspecified. Encoded descriptions, images, fonts, and source UI code are excluded.'),('M5-Dev / J2ME Vault mirror','https://huggingface.co/datasets/M5-Dev/j2me-vault','7,291 JAR candidates · 111 JAD descriptors','A secondary mirror attributed by its uploader to Kahvibreak. Only file-tree metadata was read. Forty-eight .mpn Mophun files and 93 ancillary files were excluded from this site’s J2ME-oriented file inventory. File extensions do not establish runtime compatibility.'),('Internet Archive / j2me-hipnosis / original collectors','https://archive.org/details/j2me-hipnosis','25 original archive-file inventory entries','Only item metadata was read. Sizes and SHA-1/MD5 values are source-reported; no archives were downloaded to measure them. The item is a recorded acquisition source for God of War: Betrayal in the Omni guide.')]
    body+='<section class="shell browse-layout"><div class="source-cards">'
    for title,url,count,desc in records:body+=f'<article class="source-card"><h3>{esc(title)}</h3><p><strong>{esc(count)}</strong></p><p>{esc(desc)}</p>{external(url,"Visit the source ↗","text-link")}</article>'
    body+=f'''</div><article class="prose"><h2>Snapshot and source notices.</h2><p>Prepared October 30, 2026. RG-Backup is pinned to commit <code>{esc(snap['rg_snapshot_commit'])}</code>; its original metadata URLs in this catalog point to that commit. My Abandonware detail-page SHA-256 values identify the HTML pages read, not game files.</p><p>The RG-Backup source README states <a href="https://creativecommons.org/licenses/by-nc-sa/4.0/">CC BY-NC-SA 4.0</a>. That existing source notice is retained for the attributed RG metadata and its reformatted display. The J2ME Vault dataset card states <a href="https://creativecommons.org/licenses/by-nc/4.0/">CC BY-NC 4.0</a>; its file inventory remains separately attributed. These third-party source notices do not grant permissions for Wakkatobakka’s unrelated original site code, writing, or artwork.</p><p>Original game rights, trademarks, and source materials remain with their respective holders. This project contains metadata, source links, original presentation, and original decorative artwork. It does not bundle game binaries or assert ownership of other people’s preservation work.</p><h2>Inspect the metadata.</h2><p><a href="../data/catalog.csv">Catalog CSV</a> · <a href="../data/catalog.json">Catalog JSON</a> · <a href="../data/snapshot.json">Snapshot counts and scope</a> · <a href="../data/README.md">Field definitions</a></p><p><a href="https://bluemaxima.org/kahvibreak/">Kahvibreak’s project page</a> and <a href="https://flashpointarchive.org/datahub/Kahvibreak_Curation_Tutorial">curation documentation</a> explain the broader collection. The <a href="../library/index.html">reference library</a> keeps source records separate, while <a href="../files/index.html">file inventories</a> preserve file-level leads.</p></article></section>'''
    page('sources/index.html','Sources and Credits | J2ME Archive','The source register, original preservation credits, snapshot scope, and third-party metadata notices for Wakkatobakka’s J2ME catalog.',body,'sources')

def exports():
    with (ROOT/'data/catalog.csv').open('w',newline='',encoding='utf-8-sig') as f:
        w=csv.writer(f);w.writerow(['record_id','title','listed_year','genres_as_listed','omni_recovery','recorded_edition','source_variant_groups','source_records','page'])
        for e in ENTRIES:w.writerow([e['id'],e['title'],e['listed_year'] or '', ' | '.join(e['genres']),str(bool(e['omni'])).lower(),e['omni']['edition'] if e['omni'] else '',e['source_variant_groups'],' | '.join(r['key'] for r in e['source_records']),BASE+'games/'+e['slug']+'/'])
    (ROOT/'robots.txt').write_text('User-agent: *\nAllow: /\nSitemap: '+BASE+'sitemap.xml\n')
    sitemap=['<?xml version="1.0" encoding="UTF-8"?>','<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for path in PAGES:
        if path in ('404.html','library/record/index.html'):continue
        sitemap.append('<url><loc>'+esc(BASE+path.removesuffix('index.html'))+'</loc></url>')
    (ROOT/'sitemap.xml').write_text('\n'.join(sitemap+['</urlset>'])+'\n')

def not_found():
    body='<section class="shell section"><div class="kicker">404 / THE TRAIL WENT QUIET</div><h1>This page is<br><em>out of signal.</em></h1><p>The title might still be in the catalog. Start there and follow the source trail again.</p><div class="buttons"><a class="btn btn-primary" href="'+BASE+'catalog/">Search the catalog →</a><a class="btn btn-secondary" href="'+BASE+'">Back to the archive →</a></div></section>'
    page('404.html','Out of Signal | J2ME Archive','Find your way back to Wakkatobakka’s J2ME catalog.',body,root_override=BASE)

def main():
    # Only remove directories entirely owned by this generator.
    import shutil
    for directory in ('games','catalog','recovered','library','files','sources','field-notes'):
        p=ROOT/directory
        if p.exists():shutil.rmtree(p)
    home();catalog_pages();recoveries_page();game_pages();reference_pages();reference_pages(True);inspector_page();notes_page();sources_page();not_found();exports()
    print(json.dumps({'html_pages':len(PAGES),'catalog_entries':len(ENTRIES),'omni_recoveries':sum(bool(e['omni']) for e in ENTRIES),'reference_records':len(LIB),'file_references':len(FILES),'build':'complete','network_requests':0}))

if __name__=='__main__':main()
