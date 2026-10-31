#!/usr/bin/env python3
"""Rebuild the original vector banner; render its PNG with Inkscape if installed."""
from pathlib import Path
import json, re, shutil, subprocess

ROOT=Path(__file__).resolve().parents[1]
data=json.loads((ROOT/'data/catalog.json').read_text())
hero=(ROOT/'assets/hero.svg').read_text()
inner=re.sub(r'^<svg[^>]*>|</svg>\s*$','',hero.strip())
inner=re.sub(r'<title[^>]*>.*?</title>|<desc[^>]*>.*?</desc>','',inner,flags=re.S)
svg=f'''<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="630" viewBox="0 0 1200 630">
<title>J2ME / The Lost Catalog</title>
<defs><linearGradient id="bg" x2="1" y2="1"><stop stop-color="#16212a"/><stop offset=".6" stop-color="#0c111a"/><stop offset="1" stop-color="#111925"/></linearGradient></defs>
<rect width="1200" height="630" fill="url(#bg)"/>
<path d="M34 35h1132v560H34Z" fill="none" stroke="#253341"/>
<g font-family="DejaVu Sans,sans-serif">
<g transform="translate(60 69)"><rect width="20" height="30" rx="5" fill="none" stroke="#ffb078" stroke-width="2"/><rect x="5" y="6" width="10" height="12" fill="#ffb078"/><text x="33" y="21" fill="#e8edf0" font-size="18" font-weight="700" letter-spacing="1">J2ME / ARCHIVE</text></g>
<text x="60" y="181" fill="#a7daeb" font-size="13" letter-spacing="2" font-weight="700">WAKKATOBAKKA’S POCKET GAMING ARCHIVES</text>
<text x="60" y="259" fill="#edf1f4" font-size="49" font-weight="700" letter-spacing="-1.3">Before the app store,</text>
<text x="60" y="320" fill="#ffb078" font-size="49" font-weight="700" letter-spacing="-1.3">there was the .jar.</text>
<text x="61" y="374" fill="#b2beca" font-size="18">The titles. The editions. The trails they left behind.</text>
<rect x="60" y="415" width="196" height="39" rx="4" fill="#ffb078"/>
<text x="158" y="440" text-anchor="middle" fill="#211b17" font-size="14" font-weight="700">{data['counts']['catalog_entries']:,} CATALOG ENTRIES</text>
<text x="275" y="440" fill="#a7daeb" font-size="13" font-weight="600" letter-spacing="1">10 OMNI RECOVERIES</text>
<path d="M60 514h565" stroke="#354452"/>
<text x="60" y="550" fill="#8fa4b5" font-size="13">THE LOST CATALOG · AN INDEPENDENT ARCHIVE BY WAKKA</text>
</g>
<g transform="translate(654,40) scale(.86)">{inner}</g>
</svg>'''
(ROOT/'artwork').mkdir(exist_ok=True)
path=ROOT/'artwork/banner.svg';path.write_text(svg)
inkscape=shutil.which('inkscape')
if inkscape:
    subprocess.run([inkscape,str(path),'--export-type=png','--export-width=1200','--export-height=630','--export-filename='+str(ROOT/'assets/banner.png')],check=True,stdout=subprocess.DEVNULL)
    print('Rendered assets/banner.png (1200×630) from artwork/banner.svg')
else:
    print('Updated artwork/banner.svg. Inkscape is needed only to regenerate its PNG; the checked-in PNG remains available.')
