const labels = {draft:'Borrador', submitted:'Enviada', interview:'Entrevista', closed:'Cerrada'};
const cards = document.querySelector('#application-cards');
const detail = document.querySelector('#application-detail');
const status = document.querySelector('#application-status');
let selected = null, detailRequest = 0, listRequest = 0;

function element(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined && text !== null) node.textContent = String(text);
  return node;
}
async function api(path, options = {}) {
  const response = await fetch(path, {...options, headers:{'Content-Type':'application/json', ...options.headers}});
  const body = await response.json();
  if (!response.ok) throw new Error(body.error || 'No se pudo completar la operación.');
  return body;
}
async function refresh() {
  const request = ++listRequest;
  try {
    const state = document.querySelector('#state-filter').value;
    const report = await api(`/api/applications?limit=200&state=${encodeURIComponent(state)}`);
    if (request !== listRequest) return;
    document.querySelector('#application-count').textContent = report.total;
    status.textContent = `${report.applications.length} de ${report.total} registros locales`;
    cards.replaceChildren();
    for (const item of report.applications) {
      const button = element('button', 'card');
      button.type = 'button'; button.dataset.id = item.id;
      button.append(element('h3','',item.title), element('p','card-company',item.company), element('span','badge',labels[item.state]));
      cards.append(button);
    }
    if (!report.total) cards.append(element('p','no-results','No hay candidaturas para este estado.'));
  } catch (error) { if (request === listRequest) status.textContent = error.message; }
}
async function load(id) {
  const request = ++detailRequest;
  selected = id;
  detail.replaceChildren(element('p','hint','Cargando historial…'));
  try {
    const report = await api(`/api/applications/${encodeURIComponent(id)}`);
    if (request !== detailRequest) return;
    const item = report.application;
    detail.replaceChildren(element('h2','',item.title), element('p','detail-company',item.company));
    const url = new URL(item.url);
    if (['http:','https:'].includes(url.protocol)) {
      const link = element('a','origin-link','Abrir referencia ↗');
      link.href = url.href; link.target = '_blank'; link.rel = 'noopener noreferrer'; detail.append(link);
    }
    detail.append(element('p','helper',item.job_key ? `Oferta: ${item.job_key}` : 'Referencia manual, sin extracción.'));
    const form = element('form','personal-form');
    const stateLabel = element('label','','Estado registrado'); stateLabel.htmlFor = 'application-state';
    const select = element('select'); select.id = 'application-state';
    for (const [value,text] of Object.entries(labels)) {
      const option = element('option','',text); option.value = value; select.append(option);
    }
    select.value = item.state;
    const reasonLabel = element('label','','Motivo o avance'); reasonLabel.htmlFor = 'application-reason';
    const reason = element('textarea'); reason.id = 'application-reason'; reason.maxLength = 2000; reason.required = true;
    const save = element('button','save','Guardar estado local'); save.type = 'submit';
    const feedback = element('p','helper'); feedback.setAttribute('role','status');
    form.append(stateLabel,select,reasonLabel,reason,element('p','hint','Podés corregir o reabrir un estado. El motivo y el estado anterior se conservan.'),save,feedback);
    form.addEventListener('submit',async event => {
      event.preventDefault(); save.disabled = true;
      try {
        await api(`/api/applications/${encodeURIComponent(id)}`, {method:'PATCH', body:JSON.stringify({state:select.value,expected_revision:item.revision,reason:reason.value})});
        if (selected === id) await load(id);
        await refresh();
      } catch (error) { feedback.textContent = error.message; }
      finally { save.disabled = false; }
    });
    const reload = element('button','save','Recargar historial'); reload.type = 'button'; reload.addEventListener('click',() => load(id));
    detail.append(form,reload,element('h3','section-title','Historial'));
    for (const event of report.history) {
      const row = element('div','application-event');
      row.append(element('strong','',`${event.revision} · ${labels[event.to_state]}`),element('p','helper',event.at),element('p','',event.reason || 'Borrador creado'));
      detail.append(row);
    }
  } catch (error) { if (request === detailRequest) detail.replaceChildren(element('p','message',error.message)); }
}
document.querySelector('#reference-form').addEventListener('submit',async event => {
  event.preventDefault();
  const button = event.target.querySelector('button'), feedback = document.querySelector('#create-status');
  button.disabled = true;
  try {
    const report = await api('/api/applications',{method:'POST',body:JSON.stringify({
      url:document.querySelector('#reference-url').value.trim(), title:document.querySelector('#reference-title').value.trim(),
      company:document.querySelector('#reference-company').value.trim(),reason:document.querySelector('#reference-reason').value,
    })});
    feedback.textContent = report.created ? 'Borrador creado. No se envió ninguna candidatura.' : 'La referencia ya existe. Se muestra la candidatura original; no se cambió su nota.';
    if (report.created) event.target.reset();
    await refresh(); await load(report.application.id);
  } catch (error) { feedback.textContent = error.message; }
  finally { button.disabled = false; }
});
cards.addEventListener('click', event => { const button = event.target.closest('[data-id]'); if (button) load(button.dataset.id); });
document.querySelector('#state-filter').addEventListener('change',refresh);
document.querySelector('#refresh-applications').addEventListener('click',refresh);
refresh();
if (location.hash) load(decodeURIComponent(location.hash.slice(1)));
