'use strict';
(() => {
  const $ = id => document.getElementById(id);
  const talk = window.TALK;
  const speakerVersion = document.body.dataset.presentationVersion !== 'client';
  const flows = new Map(window.FLOWS.map(f => [f.id, f]));
  const sources = new Map(talk.sources.map(s => [s.id, s]));
  const el = (tag, text, cls) => {
    const node = document.createElement(tag);
    if (text !== undefined) node.textContent = text;
    if (cls) node.className = cls;
    return node;
  };
  const time = seconds => `${String(Math.floor(seconds / 60)).padStart(2, '0')}:${String(Math.floor(seconds % 60)).padStart(2, '0')}`;
  const link = (text, href, external = false) => {
    const a = el('a', text); a.href = href;
    if (external) { a.target = '_blank'; a.rel = 'noopener noreferrer'; }
    return a;
  };
  function references(ids, className = 'source-links') {
    const wrap = el('div', undefined, className);
    ids.forEach(id => { const src = sources.get(id); const a = link(id, src.url, src.url.startsWith('https:')); a.title = src.title; wrap.append(a); });
    return wrap;
  }
  const savedTheme = (() => { try { return localStorage.getItem('frontier-theme'); } catch { return null; } })();
  document.body.classList.toggle('light', savedTheme === 'light');
  $('theme').addEventListener('click', () => {
    document.body.classList.toggle('light');
    try { localStorage.setItem('frontier-theme', document.body.classList.contains('light') ? 'light' : 'dark'); } catch { /* Storage is optional. */ }
  });

  let index = 0;
  let total = 0;
  const starts = talk.slides.map(s => { const n = total; total += s.seconds; return n; });
  talk.slides.forEach((s, i) => {
    const button = el('button', undefined, 'chapter');
    button.append(el('span', `${String(i + 1).padStart(2, '0')} / ${time(starts[i])}`, 'number'), el('h3', s.title), el('small', `${s.section} · ${s.seconds / 60} min`));
    button.addEventListener('click', () => openDeck(i));
    $('chapter-list').append(button);
    const option = el('option', `${i + 1}. ${s.title}`); option.value = String(i); $('slide-select').append(option);
  });
  function renderSlide() {
    const s = talk.slides[index];
    const f = flows.get(s.visual);
    $('slide-section').textContent = `${String(index + 1).padStart(2, '0')} / ${talk.slides.length} · ${s.section} · ${time(starts[index])}–${time(starts[index] + s.seconds)}`;
    $('slide-status').textContent = s.status;
    $('slide-title').textContent = s.title;
    $('slide-takeaway').textContent = s.takeaway;
    $('slide-points').replaceChildren(...s.points.map(p => el('li', p)));
    $('slide-flow').src = `assets/${s.visual}.svg`;
    $('slide-flow').alt = `${f.title}: ${f.nodes.join(' → ')}. ${f.caption}`;
    $('slide-caption').textContent = f.caption;
    $('slide-sources').replaceChildren(references(s.sources), el('span', `Reviewed ${talk.reviewed}`));
    if (speakerVersion) {
      $('slide-script').textContent = s.notes;
      $('slide-cue').textContent = `Cue: ${s.cue}`;
    }
    $('slide-select').value = String(index);
    $('prev-slide').disabled = index === 0;
    $('next-slide').disabled = index === talk.slides.length - 1;
    $('slide-progress').style.width = `${(index + 1) / talk.slides.length * 100}%`;
    document.querySelector('.deck-content').scrollTop = 0;
    updateTimer();
  }
  function setSlide(i) {
    index = Math.max(0, Math.min(talk.slides.length - 1, i));
    renderSlide();
    history.replaceState(null, '', `#slide-${index + 1}`);
  }
  function openDeck(i = 0) {
    setSlide(i);
    if (!$('deck').open) $('deck').showModal();
    document.body.style.overflow = 'hidden';
  }
  function closeDeck() {
    pauseTimer();
    $('deck').close();
    document.body.style.overflow = '';
    history.replaceState(null, '', '#talk');
    if (document.fullscreenElement) document.exitFullscreen().catch(() => {});
  }
  $('present').addEventListener('click', () => openDeck(0));
  $('close-deck').addEventListener('click', closeDeck);
  $('deck').addEventListener('cancel', e => { e.preventDefault(); closeDeck(); });
  $('prev-slide').addEventListener('click', () => setSlide(index - 1));
  $('next-slide').addEventListener('click', () => setSlide(index + 1));
  $('slide-select').addEventListener('change', e => setSlide(Number(e.target.value)));
  function toggleNotes() {
    if (!speakerVersion) return;
    const visible = $('speaker-notes').hidden;
    $('speaker-notes').hidden = !visible;
    $('notes-toggle').setAttribute('aria-pressed', String(visible));
    document.querySelector('.deck-content').classList.toggle('has-notes', visible);
  }
  if (speakerVersion) $('notes-toggle').addEventListener('click', toggleNotes);
  $('fullscreen').addEventListener('click', async () => {
    try {
      if (document.fullscreenElement) await document.exitFullscreen();
      else await $('deck').requestFullscreen();
    } catch { $('fullscreen').textContent = 'Use browser fullscreen'; }
  });
  document.addEventListener('keydown', e => {
    if (!$('deck').open) return;
    if (e.key === 'Tab') {
      const focusable = [...$('deck').querySelectorAll('button:not([disabled]),a[href],select,input,[tabindex="0"]')].filter(node => node.getClientRects().length > 0);
      const first = focusable[0], last = focusable[focusable.length - 1];
      if (e.shiftKey && (document.activeElement === first || !$('deck').contains(document.activeElement))) { e.preventDefault(); last.focus(); }
      else if (!e.shiftKey && (document.activeElement === last || !$('deck').contains(document.activeElement))) { e.preventDefault(); first.focus(); }
      return;
    }
    if (/^(INPUT|SELECT|TEXTAREA)$/.test(e.target.tagName)) return;
    if (e.key === 'ArrowRight') { e.preventDefault(); setSlide(index + 1); }
    if (e.key === 'ArrowLeft') { e.preventDefault(); setSlide(index - 1); }
    if (speakerVersion && e.key.toLowerCase() === 'n') toggleNotes();
  });
  let accumulated = 0;
  let runningFrom = null;
  function elapsed() { return accumulated + (runningFrom === null ? 0 : (performance.now() - runningFrom) / 1000); }
  function updateTimer() {
    const secs = elapsed();
    $('talk-time').textContent = `${time(secs)} / 30:00`;
    $('timer-toggle').textContent = runningFrom === null ? (accumulated ? 'Resume timer' : 'Start timer') : 'Pause timer';
    const end = starts[index] + talk.slides[index].seconds;
    const overdue = Math.floor(secs - end);
    $('pace').textContent = secs === 0 ? 'Ready to rehearse' : secs >= total ? '30-minute target reached' : overdue > 0 ? `${time(overdue)} past this slide’s window` : `Slide window ends at ${time(end)}`;
  }
  function pauseTimer() { if (runningFrom !== null) { accumulated = elapsed(); runningFrom = null; } updateTimer(); }
  $('timer-toggle').addEventListener('click', () => { if (runningFrom === null) runningFrom = performance.now(); else pauseTimer(); updateTimer(); });
  $('timer-reset').addEventListener('click', () => { accumulated = 0; runningFrom = null; updateTimer(); });
  setInterval(() => { if (runningFrom !== null) updateTimer(); }, 250);
  function readHash() { const match = location.hash.match(/^#slide-(\d+)$/); if (match) openDeck(Number(match[1]) - 1); }

  function renderEvidence() {
    const query = $('evidence-search').value.trim().toLowerCase();
    const status = $('evidence-filter').value;
    const cases = talk.cases.filter(c => (status === 'all' || c.status === status) && `${c.title} ${c.domain} ${c.summary} ${c.status}`.toLowerCase().includes(query));
    $('evidence-count').textContent = `${cases.length} of ${talk.cases.length} cases`;
    $('evidence-cards').replaceChildren(...cases.map(c => {
      const card = el('article', undefined, 'card');
      card.append(el('span', c.status, 'badge'), el('h3', c.title), el('time', `${c.domain} · ${c.date}`), el('p', c.summary), references(c.sources));
      return card;
    }));
    if (!cases.length) $('evidence-cards').append(el('p', 'No matching cases. Try another search or evidence type.'));
  }
  $('evidence-search').addEventListener('input', renderEvidence);
  $('evidence-filter').addEventListener('change', renderEvidence);
  talk.sources.forEach(s => {
    const entry = el('article', undefined, 'source-entry');
    entry.append(link(`${s.id} · ${s.title}`, s.url, s.url.startsWith('https:')), el('p', s.scope), el('small', `${s.date} · ${s.type}`));
    $('source-register').append(entry);
  });
  function calculator() {
    const values = Object.fromEntries(['base', 'saving', 'review', 'correction', 'volume'].map(id => { const v = Number($(id).value); $(`${id}-out`).textContent = String(v); return [id, v]; }));
    const assisted = values.base * (1 - values.saving / 100) + values.review + values.correction;
    const net = values.volume * (values.base - assisted) / 60;
    $('net-hours').textContent = `${net >= 0 ? '+' : '−'}${Math.abs(net).toFixed(1)} hours / week`;
    $('net-detail').textContent = `${assisted.toFixed(1)} assisted minutes per task; ${(values.base - assisted).toFixed(1)} net minutes saved per task. Assumed inputs, not measured outcomes.`;
    document.querySelector('.result').classList.toggle('negative', net < 0);
  }
  $('calculator').addEventListener('input', calculator);
  $('calculator').addEventListener('submit', e => e.preventDefault());
  function drawMechanisms() {
    const u = Number($('intervention').value) / 100;
    $('intervention-out').textContent = `${Math.round(u * 100)}%`;
    const ns = 'http://www.w3.org/2000/svg';
    const node = (tag, attrs, text) => { const n = document.createElementNS(ns, tag); Object.entries(attrs).forEach(([k, v]) => n.setAttribute(k, String(v))); if (text) n.textContent = text; return n; };
    const children = [];
    for (let i = 0; i <= 4; i++) {
      const y = 280 - i * 60;
      children.push(node('line', {x1:60, y1:y, x2:525, y2:y, class:'axis'}), node('text', {x:48, y:y+4, 'text-anchor':'end'}, String(i / 4)));
      const x = 60 + i * 116.25;
      children.push(node('text', {x, y:301, 'text-anchor':'middle'}, String(i / 4)));
    }
    children.push(node('text', {x:280, y:325, 'text-anchor':'middle'}, 'Normalized time (synthetic)'), node('text', {x:12, y:165, transform:'rotate(-90 12 165)', 'text-anchor':'middle'}, 'Normalized response'));
    const curve = rate => Array.from({length:101}, (_, i) => {
      const t = i / 100;
      return `${i ? 'L' : 'M'}${(60 + 465 * t).toFixed(2)},${(280 - 240 * (1 - Math.exp(-rate * t))).toFixed(2)}`;
    }).join(' ');
    children.push(node('path', {d:curve(1 + 2*u), stroke:'var(--accent)', 'stroke-width':4, fill:'none', id:'curve-a'}), node('path', {d:curve(1 + .2*u), stroke:'var(--purple)', 'stroke-width':3, 'stroke-dasharray':'8 5', fill:'none', id:'curve-b'}));
    $('chart-drawing').replaceChildren(...children);
  }
  $('intervention').addEventListener('input', drawMechanisms);
  talk.careers.forEach(c => { const option = el('option', c.label); option.value = c.id; $('career-select').append(option); });
  function renderCareer() {
    const c = talk.careers.find(c => c.id === $('career-select').value);
    $('career-card').replaceChildren(...[['Illustrative task',c.task], ['Acceptance check',c.check], ['Accountable owner',c.human], ['Outcome metric',c.metric]].map(([label, text]) => { const part = el('div'); part.append(el('h3', label), el('p', text)); return part; }));
  }
  $('career-select').addEventListener('change', renderCareer);
  const documents = [
    ['00-abstract', 'Abstract & framing', 'Event description, audience outcomes and English key takeaways.'],
    ['01-speaker-notes', 'Timed speaker script', '16 slides, delivery cues, Mermaid flows and linked evidence.'],
    ['02-research-brief', 'Research brief', 'Mathematical scope, scientific examples and productivity interpretation.'],
    ['03-wave-intelligence', 'Wave Intelligence', 'Attributed repository contribution and the limits of mechanistic interpretation.'],
    ['04-alumni-playbook', 'Alumni pilot playbook', 'A 30-day plan, task contracts, metrics and risk controls.'],
    ['05-panel-qa', 'Panel Q&A', 'Answer cards for likely questions and an honest response to unknowns.'],
    ['06-prompts-and-exercises', 'Prompts & exercises', 'Practical templates and short audience interactions.'],
    ['07-production-and-publishing', 'Rehearsal & publishing', 'Presentation controls, draw.io editing, local preview and GitHub Pages.'],
    ['08-evidence-register', 'Evidence register', 'Sources, versions, review scope and factual limitations.'],
    ['09-fact-check-checklist', 'Pre-event fact check', 'Review claims before the event; keep automation separate from acceptance.']
  ];
  documents.filter(([id]) => speakerVersion || !['01-speaker-notes', '07-production-and-publishing'].includes(id)).forEach(([id, title, description]) => { const card = el('article', undefined, 'card'); card.append(el('h3', title), el('p', description), link('Read document →', `read/${id}.html`)); $('document-list').append(card); });
  renderEvidence(); calculator(); drawMechanisms(); renderCareer(); renderSlide(); readHash();
  window.addEventListener('hashchange', readHash);
})();
