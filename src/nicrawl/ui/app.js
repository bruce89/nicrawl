const form = document.querySelector('#search-form');
const cards = document.querySelector('#cards');
const detail = document.querySelector('#detail');
const message = document.querySelector('#message');
const resultCount = document.querySelector('#result-count');
const resultMeta = document.querySelector('#result-meta');
const resultsTitle = document.querySelector('#results-title');
const rankFields = document.querySelector('#rank-fields');
const modeList = document.querySelector('#mode-list');
const modeRank = document.querySelector('#mode-rank');
const submitLabel = document.querySelector('#submit-label');
const state = { mode: 'list', selected: null, report: null, request: 0, detailRequest: 0 };

function element(tag, className, content) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (content !== undefined && content !== null) node.textContent = String(content);
  return node;
}

function showMessage(text) {
  message.textContent = text;
  message.hidden = !text;
}

function terms(value) {
  return value.split(',').map(term => term.trim()).filter(Boolean);
}

function setMode(mode) {
  state.mode = mode;
  state.selected = null;
  state.report = null;
  state.detailRequest += 1;
  detail.replaceChildren(element('p', 'hint', 'Elegí una oferta de los resultados para revisarla.'));
  const ranking = mode === 'rank';
  rankFields.hidden = !ranking;
  modeList.classList.toggle('active', !ranking);
  modeRank.classList.toggle('active', ranking);
  modeList.setAttribute('aria-pressed', String(!ranking));
  modeRank.setAttribute('aria-pressed', String(ranking));
  submitLabel.textContent = ranking ? 'Priorizar ofertas' : 'Buscar ofertas';
  resultsTitle.textContent = ranking ? 'Ordenadas para vos' : 'Ofertas guardadas';
  loadResults();
}

function parameters() {
  const data = new FormData(form);
  const params = new URLSearchParams();
  for (const name of ['query', 'title_query', 'company', 'source', 'location_text']) {
    const value = String(data.get(name) || '').trim();
    if (value) params.set(name, value);
  }
  params.set('limit', String(data.get('limit') || '50'));
  if (state.mode === 'rank') {
    for (const term of terms(String(data.get('want') || ''))) params.append('want', term);
    for (const term of terms(String(data.get('avoid') || ''))) params.append('avoid', term);
    const mode = String(data.get('mode') || '');
    if (mode) params.set('mode', mode);
    params.set('fields', String(data.get('fields') ?? 'title,tags,description'));
    if (document.querySelector('#include-dismissed').checked) params.set('include_dismissed', 'true');
    if (!params.has('want') && !params.has('avoid') && !mode) {
      throw new Error('Para priorizar, indicá al menos un interés, algo a evitar o una modalidad.');
    }
  }
  return params;
}

async function api(path, options = {}) {
  const response = await fetch(path, { ...options, headers: { Accept: 'application/json', ...options.headers } });
  const body = await response.json();
  if (!response.ok) throw new Error(body.error || 'No se pudo completar la operación.');
  return body;
}

function badge(text, extra = '') {
  return element('span', `badge ${extra}`, text);
}

function humanSource(source) {
  return source === 'greenhouse:gitlab' ? 'GitLab · Greenhouse' : 'Remotive';
}

function card(item) {
  const job = state.mode === 'rank' ? item.job : item;
  const button = element('button', `card ${state.selected === job.job_key ? 'selected' : ''}`);
  button.type = 'button';
  button.dataset.key = job.job_key;
  const top = element('div', 'card-top');
  top.append(element('h3', '', job.title));
  if (state.mode === 'rank') top.append(element('span', `score ${item.score < 0 ? 'negative' : ''}`, `${item.score > 0 ? '+' : ''}${item.score} pts`));
  button.append(top, element('p', 'card-company', job.company));
  const bottom = element('div', 'card-bottom');
  bottom.append(badge(humanSource(job.source_id), 'source'));
  bottom.append(badge(job.location_raw || 'Ubicación no informada'));
  if (job.stale) bottom.append(badge('Dato antiguo'));
  button.append(bottom);
  return button;
}

function renderResults(report) {
  state.report = report;
  const items = state.mode === 'rank' ? report.results : report.jobs;
  resultCount.textContent = String(report.total);
  resultMeta.textContent = `${items.length} de ${report.total} ofertas · ${state.mode === 'rank' ? 'Puntaje explicable' : 'Ordenadas por descubrimiento'} · Sin descargar datos`;
  cards.replaceChildren();
  if (items.length === 0) {
    cards.append(element('p', 'no-results', 'No hay ofertas para esta selección. Probá cambiar los filtros.'));
    return;
  }
  for (const item of items) cards.append(card(item));
  if (state.selected) {
    const selected = cards.querySelectorAll('.card');
    for (const node of selected) node.classList.toggle('selected', node.dataset.key === state.selected);
  }
}

async function loadResults() {
  const request = ++state.request;
  showMessage('');
  cards.replaceChildren();
  resultCount.textContent = '—';
  state.report = null;
  try {
    const path = state.mode === 'rank' ? '/api/rank' : '/api/jobs';
    resultMeta.textContent = 'Consultando la colección local…';
    const report = await api(`${path}?${parameters()}`);
    if (request !== state.request) return;
    renderResults(report);
  } catch (error) {
    if (request !== state.request) return;
    resultMeta.textContent = 'La búsqueda no se completó.';
    showMessage(error.message);
  }
}

function fact(label, value) {
  const cell = element('div', 'fact');
  cell.append(element('span', 'fact-label', label), element('span', 'fact-value', value || 'No informado'));
  return cell;
}

function reasonText(reason) {
  if (reason.rule === 'mode') return `Modalidad ${reason.observed} · pediste ${reason.expected}`;
  return `${reason.rule === 'want' ? 'Interés' : 'Evitar'} “${reason.term}” · ${reason.field}`;
}

function renderDetail(report) {
  const job = report.job;
  detail.replaceChildren();
  detail.append(element('p', 'eyebrow', '03 / REVISAR'));
  detail.append(element('h2', '', job.title));
  detail.append(element('p', 'detail-company', `${job.company} · ${humanSource(job.source_id)}`));
  const facts = element('div', 'facts');
  facts.append(
    fact('Ubicación declarada', job.location_raw),
    fact('Modalidad', job.work_mode === 'unknown' ? 'No determinada' : job.work_mode),
    fact('Observada por última vez', job.last_seen_at ? job.last_seen_at.slice(0, 10) : null),
    fact('Frescura', job.stale ? 'Dato antiguo' : 'Observación reciente'),
  );
  detail.append(facts);
  try {
    const source = new URL(job.source_url);
    if (['http:', 'https:'].includes(source.protocol)) {
      const link = element('a', 'origin-link', 'Abrir aviso original ↗');
      link.href = source.href;
      link.target = '_blank';
      link.rel = 'noopener noreferrer';
      detail.append(link);
    }
  } catch (_error) { /* La fuente se conserva en el JSON; no crear un enlace inválido. */ }
  detail.append(element('p', 'hint', '“Remoto” no confirma elegibilidad geográfica. Verificá el aviso vigente.'));
  const track = element('button', 'save', 'Crear seguimiento');
  track.type = 'button';
  const trackingStatus = element('p', 'helper');
  trackingStatus.setAttribute('role', 'status');
  track.addEventListener('click', async () => {
    track.disabled = true;
    try {
      const result = await api('/api/applications', {
        method: 'POST', headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({job_key: job.job_key}),
      });
      const link = element('a', 'origin-link', result.created ? 'Borrador creado · ver seguimiento' : 'Ya existe · ver seguimiento');
      link.href = `/applications#${encodeURIComponent(result.application.id)}`;
      trackingStatus.replaceChildren(link);
    } catch (error) { trackingStatus.textContent = error.message; }
    finally { track.disabled = false; }
  });
  detail.append(track, trackingStatus);

  if (state.mode === 'rank' && state.report) {
    const result = state.report.results.find(item => item.job.job_key === job.job_key);
    if (result) {
      detail.append(element('p', 'section-title', `Puntaje ${result.score > 0 ? '+' : ''}${result.score} · razones`));
      if (result.reasons.length === 0) detail.append(element('p', 'hint', 'Ninguna regla aportó puntos.'));
      for (const reason of result.reasons) {
        const row = element('div', 'reason');
        row.append(element('span', '', reasonText(reason)));
        row.append(element('strong', reason.points < 0 ? 'negative' : 'positive', `${reason.points > 0 ? '+' : ''}${reason.points}`));
        detail.append(row);
      }
    }
  }

  const description = element('details', 'description');
  description.append(element('summary', '', 'Descripción completa'));
  description.append(element('p', '', job.description_text || 'El origen no informó una descripción.'));
  detail.append(description);

  const personal = element('form', 'personal-form');
  personal.id = 'personal-form';
  personal.append(element('p', 'section-title', 'Tu revisión personal'));
  const stateLabel = element('label', '', 'Estado');
  stateLabel.htmlFor = 'personal-state';
  const stateSelect = element('select');
  stateSelect.id = 'personal-state';
  for (const [value, label] of [['unreviewed', 'Sin revisar'], ['favorite', 'Favorita'], ['dismissed', 'Descartada']]) {
    const option = element('option', '', label);
    option.value = value;
    stateSelect.append(option);
  }
  stateSelect.value = report.personal.state;
  personal.append(stateLabel, stateSelect);
  const noteLabel = element('label', '', 'Nota privada');
  noteLabel.htmlFor = 'personal-note';
  const note = element('textarea');
  note.id = 'personal-note';
  note.maxLength = 2000;
  note.placeholder = 'Qué querés verificar, dudas o próximos pasos…';
  note.value = report.personal.note || '';
  personal.append(noteLabel, note);
  const save = element('button', 'save', 'Guardar revisión');
  save.type = 'submit';
  personal.append(save, element('span', 'save-status'));
  detail.append(personal);
}

async function loadDetail(key) {
  const request = ++state.detailRequest;
  state.selected = key;
  for (const node of cards.querySelectorAll('.card')) node.classList.toggle('selected', node.dataset.key === key);
  detail.replaceChildren(element('p', 'hint', 'Cargando detalle…'));
  try {
    const report = await api(`/api/jobs/${encodeURIComponent(key)}`);
    if (request !== state.detailRequest) return;
    renderDetail(report);
  } catch (error) {
    if (request !== state.detailRequest) return;
    detail.replaceChildren(element('p', 'message', error.message));
  }
}

form.addEventListener('submit', event => { event.preventDefault(); loadResults(); });
modeList.addEventListener('click', () => setMode('list'));
modeRank.addEventListener('click', () => setMode('rank'));
cards.addEventListener('click', event => {
  const button = event.target.closest('.card');
  if (button) loadDetail(button.dataset.key);
});
detail.addEventListener('submit', async event => {
  if (event.target.id !== 'personal-form') return;
  event.preventDefault();
  const save = event.target.querySelector('.save');
  const status = event.target.querySelector('.save-status');
  save.disabled = true;
  status.textContent = 'Guardando…';
  try {
    await api(`/api/jobs/${encodeURIComponent(state.selected)}/personal`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        state: event.target.querySelector('#personal-state').value,
        note: event.target.querySelector('#personal-note').value,
      }),
    });
    status.textContent = 'Guardado';
    await loadDetail(state.selected);
    await loadResults();
  } catch (error) {
    status.textContent = error.message;
  } finally {
    save.disabled = false;
  }
});

const savedSelect = document.querySelector('#saved-search');
const savedStatus = document.querySelector('#saved-status');

async function loadSavedOptions(selected = '') {
  const book = await api('/api/searches');
  savedSelect.replaceChildren();
  const placeholder = element('option', '', 'Elegí una búsqueda…');
  placeholder.value = '';
  savedSelect.append(placeholder);
  for (const profile of book.searches) {
    const option = element('option', '', profile.name);
    option.value = profile.name;
    savedSelect.append(option);
  }
  savedSelect.value = selected;
}

document.querySelector('#load-search').addEventListener('click', async () => {
  try {
    if (!savedSelect.value) throw new Error('Elegí una búsqueda guardada.');
    const profile = await api(`/api/searches/${encodeURIComponent(savedSelect.value)}`);
    for (const name of ['query', 'title_query', 'company', 'source', 'location_text', 'limit', 'mode']) {
      form.elements.namedItem(name).value = profile[name] ?? '';
    }
    for (const name of ['want', 'avoid', 'fields']) {
      form.elements.namedItem(name).value = profile[name].join(',');
    }
    document.querySelector('#include-dismissed').checked = profile.include_dismissed;
    document.querySelector('#search-name').value = profile.name;
    document.querySelector('#search-goal').value = profile.goal;
    document.querySelector('#replace-search').checked = false;
    savedStatus.textContent = `Cargada: ${profile.name}. ${profile.goal}`;
    setMode(profile.view);
  } catch (error) { savedStatus.textContent = error.message; }
});

document.querySelector('#save-search').addEventListener('click', async event => {
  const button = event.currentTarget;
  button.disabled = true;
  try {
    const data = new FormData(form);
    const profile = {
      name: document.querySelector('#search-name').value.trim(),
      goal: document.querySelector('#search-goal').value.trim(),
      view: state.mode,
      limit: Number(data.get('limit')),
      mode: String(data.get('mode') || '') || null,
      include_dismissed: document.querySelector('#include-dismissed').checked,
    };
    for (const name of ['query', 'title_query', 'company', 'source', 'location_text']) profile[name] = String(data.get(name) || '').trim();
    for (const name of ['want', 'avoid', 'fields']) profile[name] = terms(String(data.get(name) || ''));
    await api('/api/searches', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ profile, replace: document.querySelector('#replace-search').checked }),
    });
    await loadSavedOptions(profile.name);
    document.querySelector('#replace-search').checked = false;
    savedStatus.textContent = `Guardada: ${profile.name}. Disponible también desde la terminal.`;
  } catch (error) { savedStatus.textContent = error.message; }
  finally { button.disabled = false; }
});

loadSavedOptions().catch(error => { savedStatus.textContent = error.message; });
loadResults();
