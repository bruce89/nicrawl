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
    detail.append(form,reload);
    await appendDraftTools(id, detail);
    detail.append(element('h3','section-title','Historial'));
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

async function appendDraftTools(applicationId, container) {
  container.append(element('h3','section-title','Preparar borrador local'));
  const savedDrafts = await api(`/api/applications/${encodeURIComponent(applicationId)}/drafts`);
  for (const draft of savedDrafts.drafts) {
    const reopen = element('button', 'save', `Revisar borrador ${draft.id.slice(0,8)} · v${draft.current_version}`);
    reopen.type = 'button';
    const panel = element('section');
    reopen.addEventListener('click', async () => {
      reopen.disabled = true;
      try {
        const saved = await api(`/api/drafts/${encodeURIComponent(draft.id)}`);
        panel.replaceChildren(element('pre','draft-preview',saved.preview));
        appendSimulation(saved, panel);
        appendSimulation(saved, panel, true);
      } catch (error) { panel.textContent = error.message; }
      finally { reopen.disabled = false; }
    });
    container.append(reopen, panel);
  }
  const report = await api('/api/profiles');
  const profiles = report.profiles || [];
  if (!profiles.length) { container.append(element('p','helper','Guardá una versión de perfil para empezar.')); return; }
  const form = element('form','personal-form');
  const label = element('label','','Versión de perfil');
  const select = element('select');
  for (const item of profiles) { const option=element('option','',`${item.version} · ${item.label}`); option.value=item.version; select.append(option); }
  const claimLabel=element('label','','Afirmaciones respaldadas por el CV');
  const claims=element('select'); claims.multiple=true; claims.size=4;
  let currentProfile;
  async function loadClaims() {
    currentProfile=await api(`/api/profiles/${select.value}`); claims.replaceChildren();
    for (const item of currentProfile.claims) { const option=element('option','',`${item.claim_id} · ${item.statement}`); option.value=item.claim_id; claims.append(option); }
  }
  await loadClaims(); select.addEventListener('change',loadClaims);
  const openingLabel=element('label','','Apertura escrita por vos (opcional)'); const opening=element('textarea'); opening.maxLength=2000;
  const questionsLabel=element('label','','Preguntas pendientes (una por línea)'); const questions=element('textarea');
  const feedback=element('p','helper'); feedback.setAttribute('role','status');
  const save=element('button','save','Crear borrador revisable'); save.type='submit';
  form.append(label,select,claimLabel,claims,openingLabel,opening,questionsLabel,questions,save,feedback);
  form.addEventListener('submit',async event=>{ event.preventDefault(); save.disabled=true;
    try { const draft=await api(`/api/applications/${encodeURIComponent(applicationId)}/drafts`,{method:'POST',body:JSON.stringify({profile_version:Number(select.value),claim_ids:[...claims.selectedOptions].map(x=>x.value),opening:opening.value,questions:questions.value.split('\n').map(x=>x.trim()).filter(Boolean)})});
      const preview=element('pre','draft-preview',draft.preview); container.append(preview);
      appendSimulation(draft, container);
      appendSimulation(draft, container, true);
      const download=element('button','save','Descargar borrador Markdown'); download.type='button'; download.addEventListener('click',()=>{const a=document.createElement('a');a.href=URL.createObjectURL(new Blob([draft.preview],{type:'text/markdown;charset=utf-8'}));a.download=`nicrawl-borrador-${draft.id}.md`;a.click();URL.revokeObjectURL(a.href);}); container.append(download);
      feedback.textContent='Borrador guardado localmente; revisá cada dato antes de usarlo.';
    } catch(error){feedback.textContent=error.message;} finally{save.disabled=false;}
  });
  container.append(form);
}
document.querySelector('#profile-form').addEventListener('submit',async event=>{
  event.preventDefault(); const form=event.currentTarget, button=form.querySelector('button'), status=document.querySelector('#profile-status'); button.disabled=true;
  try { const cv=document.querySelector('#profile-cv').value; const profile=await api('/api/profiles',{method:'PUT',body:JSON.stringify({label:document.querySelector('#profile-label').value,cv_text:cv,claims:[{statement:document.querySelector('#profile-claim').value,evidence:document.querySelector('#profile-evidence').value}]})});
    status.textContent=`Versión ${profile.version} guardada; el CV queda en almacenamiento local sin cifrar.`; form.reset(); if(selected) await load(selected);
  } catch(error){status.textContent=error.message;} finally{button.disabled=false;}
});

function appendSimulation(draft, container, httpMode = false) {
  const resource = httpMode ? 'http-trials' : 'simulations';
  const panel = element('section', 'personal-form');
  const start = element('button','save',httpMode ? 'Preparar ensayo HTTP' : 'Preparar ensayo local'); start.type = 'button';
  const feedback = element('p','helper'); feedback.setAttribute('role','status');
  panel.append(start, feedback); container.append(panel);
  start.addEventListener('click', async () => {
    start.disabled = true;
    try {
      let report = await api(`/api/${resource}`, {method:'POST', body:JSON.stringify({draft_id:draft.id,version:draft.version})});
      const review = element('pre','draft-preview',report.payload.preview);
      const notice = element('p','helper',`Destino: ${report.destination}. Receptor de prueba en este equipo; no registra una postulación real.`);
      const checkbox = element('input'); checkbox.type = 'checkbox';
      const reviewLabel = element('label','','Revisé este contenido para el ensayo local '); reviewLabel.append(checkbox);
      const scenario = element('select'); scenario.setAttribute('aria-label','Resultado a simular');
      for (const [value,text] of Object.entries({accepted:'Aceptación',rejected:'Rechazo','timeout-before':'Sin respuesta antes de recibir','timeout-after':'Sin respuesta después de recibir'})) {
        const option = element('option','',text); option.value=value; scenario.append(option);
      }
      const send = element('button','save','Confirmar ensayo'); send.type='button';
      const reconcile = element('button','save','Consultar recibo local'); reconcile.type='button';
      const retry = element('button','save','Reintentar con la misma clave'); retry.type='button';
      const states = {prepared:'Preparado',sending:'Envío sin resultado final; consultá el recibo',uncertain:'Incierto: consultá el recibo antes de reintentar',accepted:'Aceptado por el receptor de prueba',rejected:'Rechazado por el receptor de prueba'};
      let busy = false;
      function refreshControls() {
        feedback.textContent = `${states[report.state]} · ID ${report.id}${report.message ? ' · '+report.message : ''}`;
        send.disabled = busy || !checkbox.checked || report.state !== 'prepared';
        reconcile.disabled = busy || !['uncertain','sending'].includes(report.state);
        retry.disabled = busy || !checkbox.checked || report.state !== 'uncertain' || !report.history.at(-1)?.action.startsWith('reconcile:');
      }
      checkbox.addEventListener('change', refreshControls);
      async function act(action, body) {
        busy = true; refreshControls();
        try {
          report = await api(`/api/${resource}/${report.id}/${action}`, {method:'POST',body:JSON.stringify(body)});
        } catch(error) {
          // Una respuesta HTTP perdida tampoco justifica repetir automáticamente.
          try { report = await api(`/api/${resource}/${report.id}`); } catch { /* volver a abrir recupera el ID */ }
          feedback.textContent=error.message; return;
        } finally { busy=false; send.disabled=true; retry.disabled=true; reconcile.disabled=false; }
        refreshControls();
      }
      send.addEventListener('click',()=>act('send',{review_sha256:report.review_sha256,scenario:scenario.value}));
      reconcile.addEventListener('click',()=>act('reconcile',{}));
      retry.addEventListener('click',()=>act('retry',{review_sha256:report.review_sha256}));
      panel.replaceChildren(notice,review,reviewLabel,scenario,send,reconcile);
      if (httpMode) panel.append(retry);
      panel.append(feedback); refreshControls();
    } catch(error) { feedback.textContent=error.message; start.disabled=false; }
  });
}
