(() => {
  'use strict';
  const input = document.getElementById('creator-search');
  if (!input) return;
  const cards = Array.from(document.querySelectorAll('.creator-card'));
  const norm = value => value.toLocaleLowerCase().normalize('NFKD').replace(/[\u0300-\u036f]/g, '');
  document.querySelector('.creator-tools').hidden = false;
  function filter() {
    const needle = norm(input.value.trim());
    let shown = 0;
    for (const card of cards) {
      card.hidden = !norm(card.dataset.search).includes(needle);
      if (!card.hidden) shown++;
    }
    document.getElementById('creator-count').textContent = `${shown} of ${cards.length} people and organisations`;
    document.getElementById('creator-empty').hidden = shown !== 0;
  }
  function revealHash() {
    let id;
    try { id = decodeURIComponent(location.hash.slice(1)); } catch (_) { return; }
    const target = document.getElementById(id);
    if (!target || !target.classList.contains('creator-card')) return;
    input.value = '';
    filter();
    target.querySelector('details').open = true;
    target.scrollIntoView({block:'start'});
  }
  input.addEventListener('input', filter);
  window.addEventListener('hashchange', revealHash);
  filter();
  revealHash();
})();
