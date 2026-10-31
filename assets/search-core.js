/* Shared search rules. No network or browser state in this module. */
(function (host) {
  'use strict';
  function normalize(value) {
    return String(value || '').normalize('NFKD').replace(/[\u0300-\u036f]/g, '')
      .toLowerCase().replace(/&/g, ' and ').replace(/(\d)\s*[xх×]\s*(?=\d)/g, '$1x');
  }
  function matches(text, query) {
    const haystack = normalize(text);
    return normalize(query).trim().split(/\s+/).filter(Boolean).every(token => haystack.includes(token));
  }
  function compareTitle(a, b) {
    return a.title.localeCompare(b.title, undefined, {numeric: true, sensitivity: 'base'}) || String(a.id || a.key).localeCompare(String(b.id || b.key));
  }
  function filterCatalog(items, state) {
    const selected = items.filter(item =>
      matches(item.search, state.q) &&
      (!state.year || (state.year === 'unknown' ? !item.year : item.year === state.year)) &&
      (!state.genre || (state.genre === 'unknown' ? !item.genres.length : item.genres.includes(state.genre))) &&
      (!state.omni || item.omni) && (!state.variants || item.variants > 0));
    return selected.sort((a, b) => {
      if (state.sort === 'recovered' && a.omni !== b.omni) return a.omni ? -1 : 1;
      if (state.sort === 'oldest' || state.sort === 'newest') {
        if (!a.year !== !b.year) return a.year ? -1 : 1;
        const delta = Number(a.year || 0) - Number(b.year || 0);
        if (delta) return state.sort === 'newest' ? -delta : delta;
      }
      return compareTitle(a, b);
    });
  }
  function filterReferences(items, state) {
    return items.filter(item =>
      matches([item.title, item.vendor, item.genre, item.source, item.extension, item.key].join(' '), state.q) &&
      (!state.source || item.source === state.source) &&
      (!state.extension || item.extension === state.extension) &&
      (!state.scope || (state.scope === 'linked' ? item.catalog_slugs.length > 0 : item.catalog_slugs.length === 0)))
      .sort((a, b) => (state.sort === 'reverse' ? -1 : 1) * compareTitle(a, b));
  }
  function paginate(items, requested, size) {
    const pages = Math.max(1, Math.ceil(items.length / size));
    const page = Math.max(1, Math.min(pages, Math.floor(Number(requested) || 1)));
    const start = (page - 1) * size;
    return {page, pages, start, total: items.length, items: items.slice(start, start + size)};
  }
  const api = {normalize, matches, filterCatalog, filterReferences, paginate};
  if (typeof module === 'object' && module.exports) module.exports = api;
  else host.ArchiveSearch = api;
})(typeof window !== 'undefined' ? window : globalThis);
