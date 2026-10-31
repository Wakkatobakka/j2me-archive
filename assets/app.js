(function () {
  'use strict';
  const root = document.body.dataset.root || '';
  const core = window.ArchiveSearch;
  const labels = {ma: 'My Abandonware', kb: 'Kahvibreak', rg: 'RG-Backup', vault: 'J2ME Vault mirror', ia: 'Internet Archive'};
  const number = value => Number(value).toLocaleString();
  function node(tag, text, cls) {
    const result = document.createElement(tag);
    if (text !== undefined && text !== null) result.textContent = String(text);
    if (cls) result.className = cls;
    return result;
  }
  function link(href, text, cls, outside) {
    const result = node('a', text, cls);
    const url = new URL(href, location.href);
    if (!['https:', 'http:'].includes(url.protocol)) throw new Error('Unsupported source URL');
    result.href = url.href;
    if (outside) { result.target = '_blank'; result.rel = 'noopener noreferrer'; }
    return result;
  }
  async function getJSON(path) {
    const response = await fetch(root + 'data/' + path);
    if (!response.ok) throw new Error('Metadata request failed');
    return response.json();
  }
  function statusMessage(text, warning) { return node('p', text, 'notice' + (warning ? ' warning' : '')); }
  function catalogCard(item) {
    const card = link(root + 'games/' + item.slug + '/index.html', '', 'record');
    const top = node('div');
    const row = node('div', null, 'record-top');
    row.append(node('span', (item.year || 'YEAR UNRECORDED') + ' / J2ME'));
    row.append(node('span', item.omni ? 'OMNI RECOVERY' : 'SOURCE-LISTED', item.omni ? 'badge omni' : ''));
    top.append(row, node('h3', item.title));
    const bottom = node('div', null, 'record-bottom');
    bottom.append(node('span', item.genres.join(' / ') || 'Genre not recorded'), node('span', '↗', 'arrow'));
    card.append(top, bottom);
    return card;
  }
  function referenceRow(item, isFile) {
    const href = root + 'library/record/index.html?key=' + encodeURIComponent(item.key);
    const row = node('div', null, 'library-row' + (isFile ? ' file-row' : ''));
    const main = node('div');const title = node('h3');title.append(link(href, item.title));
    const detail = isFile ? (item.bytes_reported === null ? 'Size not recorded' : number(item.bytes_reported) + ' bytes reported') :
      (item.variant_count ? item.variant_count + ' source edition groups' : item.genre || 'Bibliographic source record');
    const description = node('p', detail + ' · ');
    description.append(link(item.source_url, 'Original source ↗', '', true));
    main.append(title, description);
    const vendor = isFile ? item.extension.toUpperCase().replace('.', '') + ' · ' + detail : item.vendor || 'Credit not recorded';
    const arrow = link(href, '↗', 'arrow');arrow.setAttribute('aria-label', 'Inspect ' + item.title);
    row.append(main, node('span', vendor, 'vendor'), node('span', labels[item.source], 'badge'), arrow);
    return row;
  }
  function initBrowser(container) {
    const kind = container.dataset.browser;
    const isCatalog = kind === 'catalog';const isFile = kind === 'files';
    const form = document.querySelector(isCatalog ? '#catalog-form' : '#reference-form');
    const results = document.querySelector('#results');const count = document.querySelector('#result-count');
    const pages = document.querySelector('#pages');const clear = document.querySelector('#clear-filters');
    const size = isCatalog ? 36 : 40;
    let all = [];let activePage = Number(container.dataset.page || 1);let timer;
    const fields = Array.from(form.elements).filter(field => field.name);
    function readURL() {
      const params = new URLSearchParams(location.search);
      fields.forEach(field => {
        if (field.type === 'checkbox') field.checked = params.get(field.name) === '1';
        else field.value = params.get(field.name) || (field.name === 'sort' ? 'title' : '');
      });
      activePage = params.has('page') ? Number(params.get('page')) : Number(container.dataset.page || 1);
    }
    function state() {
      return Object.fromEntries(fields.map(field => [field.name, field.type === 'checkbox' ? field.checked : field.value]));
    }
    function paramsFor(s, p) {
      const params = new URLSearchParams();
      Object.entries(s).forEach(([key, value]) => {
        if (value && !(key === 'sort' && value === 'title')) params.set(key, value === true ? '1' : value);
      });
      if (p > 1) params.set('page', String(p));
      return params;
    }
    function pageURL(p, s) {
      const url = new URL(root + kind + '/index.html', location.href);
      url.search = paramsFor(s, p).toString();
      return url.href;
    }
    function render(updateURL) {
      const s = state();
      const selected = isCatalog ? core.filterCatalog(all, s) : core.filterReferences(all, s);
      const view = core.paginate(selected, activePage, size);activePage = view.page;
      const fragment = document.createDocumentFragment();
      view.items.forEach(item => fragment.append(isCatalog ? catalogCard(item) : referenceRow(item, isFile)));
      if (!view.total) {
        const empty = node('div', null, 'empty');empty.append(node('h3', 'No records on that trail.'), node('p', 'Try a shorter title, a different spelling, or clear the filters.'));
        fragment.append(empty);
      }
      results.replaceChildren(fragment);
      const range = node('strong', view.total ? number(view.start + 1) + '–' + number(view.start + view.items.length) + ' of ' + number(view.total) : '0');
      count.replaceChildren(range, document.createTextNode(' ' + (isCatalog ? 'catalog entries' : isFile ? 'file references' : 'source records')));
      clear.hidden = !Object.entries(s).some(([key, value]) => value && !(key === 'sort' && value === 'title'));
      const nav = node('nav', null, 'pagination');nav.setAttribute('aria-label', 'Result pages');
      function pageLink(p, text, label) {
        const a = link(pageURL(p, s), text);a.setAttribute('aria-label', label || 'Page ' + p);
        if (p === view.page) a.setAttribute('aria-current', 'page');
        a.addEventListener('click', event => {
          if (event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
          event.preventDefault();activePage = p;render(true);container.scrollIntoView({block: 'start', behavior: 'instant'});
          results.setAttribute('tabindex', '-1');results.focus({preventScroll: true});
        });return a;
      }
      if (view.pages > 1) {
        if (view.page > 1) nav.append(pageLink(view.page - 1, '←', 'Previous page'));
        const values = [...new Set([1, view.pages, ...Array.from({length: 5}, (_, i) => view.page - 2 + i).filter(p => p >= 1 && p <= view.pages)])].sort((a,b) => a-b);
        let previous = 0;
        values.forEach(p => {if (previous && p - previous > 1) nav.append(node('span', '…'));nav.append(pageLink(p, String(p)));previous = p;});
        if (view.page < view.pages) nav.append(pageLink(view.page + 1, '→', 'Next page'));
      }
      pages.replaceChildren(nav);
      if (updateURL) {
        const next = new URL(location.href);next.search = paramsFor(s, view.page).toString();
        history.replaceState(null, '', next);
      }
    }
    form.addEventListener('submit', event => {event.preventDefault();clearTimeout(timer);activePage=1;render(true);});
    fields.forEach(field => field.addEventListener(field.type === 'search' ? 'input' : 'change', () => {
      clearTimeout(timer);activePage=1;
      if (field.type === 'search') timer=setTimeout(() => render(true), 180);else render(true);
    }));
    clear.addEventListener('click', () => {form.reset();activePage=1;render(true);document.querySelector('#search').focus();});
    window.addEventListener('popstate', () => {readURL();render(false);});
    getJSON(isCatalog ? 'search.json' : isFile ? 'file-index.json' : 'library-index.json').then(items => {
      all=items;readURL();form.hidden=false;clear.hidden=false;render(false);
    }).catch(() => {
      const message=statusMessage('Search could not load. The page links and original-source links below are still available. Reload the page to retry.', true);
      container.prepend(message);
    });
  }
  function initVariants() {
    const input=document.querySelector('#variant-query');if (!input) return;
    const control=input.closest('.variant-search');const rows=Array.from(document.querySelectorAll('[data-variant]'));
    const output=document.querySelector('#variant-count');const empty=document.querySelector('#variant-empty');
    control.hidden=false;
    function filter() {
      let shown=0;
      rows.forEach(row => {row.hidden=!core.matches(row.dataset.variant, input.value);if (!row.hidden) shown++;});
      document.querySelectorAll('.variant-group').forEach(group => {group.hidden=!Array.from(group.querySelectorAll('[data-variant]')).some(row=>!row.hidden);});
      document.querySelectorAll('#editions details').forEach(details => {
        const hasRows=details.querySelector('[data-variant]');
        if (hasRows) {details.hidden=!Array.from(details.querySelectorAll('[data-variant]')).some(row=>!row.hidden);if (input.value && !details.hidden) details.open=true;}
      });
      output.textContent=number(shown)+' / '+number(rows.length)+' labels';empty.hidden=shown>0;
    }
    input.addEventListener('input', filter);filter();
  }
  function addFacts(parent, pairs) {
    const dl=node('dl', null, 'facts');
    pairs.forEach(([key,value]) => {if (value !== undefined && value !== null && value !== '') dl.append(node('dt', key), node('dd', Array.isArray(value) ? value.join(', ') : value));});
    parent.append(dl);
  }
  function addTable(parent, headings, data) {
    const wrap=node('div', null, 'table-wrap');const table=node('table');const head=node('thead');const hr=node('tr');
    headings.forEach(title=>{const th=node('th', title);th.scope='col';hr.append(th);});head.append(hr);table.append(head);
    const tbody=node('tbody');
    data.forEach(values=>{const tr=node('tr');values.forEach(value=>{const td=node('td');
      if (value && value.nodeType) td.append(value);else if (Array.isArray(value)) value.forEach(v=>td.append(node('code',v),node('br')));else td.textContent=value===null||value===undefined?'Not recorded':String(value);
      tr.append(td);});tbody.append(tr);});
    table.append(tbody);wrap.append(table);parent.append(wrap);
  }
  async function initInspector() {
    const mount=document.querySelector('#source-record');if (!mount) return;
    const key=new URLSearchParams(location.search).get('key');
    if (!key) {mount.replaceChildren(statusMessage('Choose a source record from the reference library or file inventories.'));return;}
    try {
      const isFile=key.startsWith('vault:')||key.startsWith('ia:');
      const index=await getJSON(isFile?'file-index.json':'library-index.json');const item=index.find(i=>i.key===key);
      if (!item || !/^sources\/(ma|kb|rg|vault|ia)\/\d{3}\.json$/.test(item.part)) throw new Error('Unknown record');
      const shard=await getJSON(item.part);const record=shard[item.id];if (!record) throw new Error('Missing record');
      const article=node('article', null, 'prose');article.append(node('div', labels[item.source]+' / '+item.id, 'kicker'),node('h2',item.title));
      const buttons=node('div',null,'buttons');buttons.append(link(record.source_url,'Visit the original source ↗','btn btn-primary',true));
      if (record.source_viewer_url) buttons.append(link(record.source_viewer_url,'Open source viewer ↗','btn btn-secondary',true));
      article.append(buttons);
      if (item.source==='ma') {
        article.append(node('h3','Directory record'));addFacts(article,[['Source title',record.title],['Listed year',record.listed_year],['Directory platform',record.listed_platforms],['Listing page',record.listing_page],['Detail page read',record.detail_page_read?'Yes':'Not in this snapshot']]);
        record.page_fact_tables.forEach((f,i)=>{article.append(node('h3','Source fact table '+(i+1)+' · '+(f.Platform||'platform not labeled')));addFacts(article,Object.entries(f));});
        article.append(statusMessage('Other-platform tables remain attributed to their own platform labels. No package has been inspected to verify these claims.'));
        if (record.download_variants_as_listed.length) {article.append(node('h3','J2ME edition labels as listed'));addTable(article,['Source label','Language flags','Source'],record.download_variants_as_listed.map(v=>[v.source_label,v.language_flags_as_listed.join(', ')||'Not labeled',link(v.source_download_reference,'Listed file ↗','',true)]));}
        article.append(node('h3','Page provenance'));addFacts(article,[['Page SHA-256',record.page_sha256||'Not recorded']]);
        article.append(node('p','The page hash identifies the source HTML read during research. It is not a game-file hash.'));
      } else if (item.source==='kb') {
        article.append(statusMessage('Kahvibreak includes J2ME and Mophun. This public table has no per-row platform field; the record remains a bibliographic lead.',true));
        addFacts(article,[['Title',record.title],['Genre',record.genre],['Developer as listed',record.developer],['Publisher as listed',record.publisher],['Source row',record.source_row],['Table version','1.6']]);
      } else if (item.source==='rg') {
        article.append(statusMessage('Vendor is a source vendor label. “Added to source” is not a release date. File groups and filenames are metadata references, not verified recovered builds.'));
        addFacts(article,[['Title',record.title],['Source vendor',record.source_vendor_label],['Source category',record.source_category_label],['Added to source',record.source_added_text],['Source collection',record.source_collection],['Original source ID',record.source_id],['File groups',record.variants.length]]);
        article.append(node('h3','File groups as listed'));
        if (record.variants.length) addTable(article,['Handset / language label','Filenames','Source size value'],record.variants.map(v=>[v.source_label,v.filenames,String(v.source_size_value??'Not recorded')+' (unit unspecified)']));
        else article.append(node('p','This metadata record has no file groups.'));
        article.append(node('p','RG-Backup source notice: CC BY-NC-SA 4.0. Source descriptions, images, and UI code are excluded.'));
      } else if (item.source==='vault') {
        article.append(statusMessage('This is a secondary file inventory attributed by its uploader to Kahvibreak. A filename and a .jar extension do not independently verify a title or MIDP runtime.',true));
        addFacts(article,[['Source path',record.path],['Filename',record.filename],['Filename extension',record.extension],['Reported bytes',record.bytes_reported],['Git blob object ID',record.git_blob_oid],['Source-reported LFS SHA-256',record.lfs_sha256_reported||'Not present']]);
        article.append(node('p','The Git blob object ID is not a raw-file SHA-256. Any LFS digest above was reported by the source and was not independently measured from a downloaded game. Dataset-card notice: CC BY-NC 4.0.'));
      } else {
        article.append(statusMessage('An inventory entry in the j2me-hipnosis item. Archive contents were not downloaded, inspected, or tested for this catalog.'));
        addFacts(article,[['Filename',record.name],['Reported bytes',record.bytes_reported],['Source-reported SHA-1',record.sha1_reported],['Source-reported MD5',record.md5_reported]]);
        article.append(node('p','Hashes are transcribed from item metadata rather than independently measured.'));
      }
      if (item.catalog_slugs.length) {
        article.append(node('h3','Main-catalog connections'));const related=node('div',null,'related-list');
        const catalog=await getJSON('catalog.json');
        item.catalog_slugs.forEach(slug=>{const entry=catalog.entries.find(e=>e.slug===slug);related.append(link(root+'games/'+slug+'/index.html',entry?entry.title:slug));});
        article.append(related,node('p','These connections are catalog or title-level links. They do not establish that the source describes an identical handset build.'));
      }
      article.append(node('h3','Source scope and credits'),link(root+'sources/index.html','Read the source register →','text-link'));
      mount.replaceChildren(article);document.title=item.title+' · Source Record | J2ME Archive';
    } catch (_) {
      mount.replaceChildren(statusMessage('That source record could not be loaded. Check the link or reload the page.',true),link(root+'library/index.html','Return to the reference library →','text-link'));
    }
  }
  if (!core) return;
  const browser=document.querySelector('[data-browser]');if (browser) initBrowser(browser);
  initVariants();initInspector();
})();
