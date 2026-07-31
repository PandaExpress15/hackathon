const state = { bootstrap: null, currentResult: null, currentWorkspace: 'ask' };
const $ = (selector, root=document) => root.querySelector(selector);
const $$ = (selector, root=document) => [...root.querySelectorAll(selector)];

function escapeHTML(value='') {
  return String(value).replace(/[&<>'"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[c]));
}
function formatValue(value, format='') {
  if (value === null || value === undefined || value === '' || Number.isNaN(value)) return 'Not published';
  if (format === 'currency') return new Intl.NumberFormat('en-US', {style:'currency',currency:'USD',maximumFractionDigits:0}).format(Number(value));
  if (format === 'number') return new Intl.NumberFormat('en-US', {maximumFractionDigits:0}).format(Number(value));
  if (format === 'percent') return `${Number(value).toFixed(1)}%`;
  if (format === 'decimal') return Number(value).toFixed(2);
  return String(value);
}
function compactNumber(value) {
  if (value === null || value === undefined) return '—';
  return new Intl.NumberFormat('en-US',{notation:'compact',maximumFractionDigits:1}).format(Number(value));
}
function toast(message) {
  const el = $('#toast'); el.textContent = message; el.classList.add('show');
  clearTimeout(toast.timer); toast.timer = setTimeout(()=>el.classList.remove('show'),2200);
}
function navigate(workspace) {
  state.currentWorkspace = workspace;
  $$('.workspace').forEach(el => el.classList.toggle('active', el.id === `workspace-${workspace}`));
  $$('.nav-item').forEach(el => el.classList.toggle('active', el.dataset.workspace === workspace));
  const button = $(`.nav-item[data-workspace="${workspace}"]`);
  $('#workspaceLabel').textContent = button ? button.textContent.trim() : workspace;
  $('.sidebar').classList.remove('open'); window.scrollTo({top:0,behavior:'smooth'});
}

async function loadBootstrap() {
  const response = await fetch('/api/bootstrap');
  if (!response.ok) throw new Error('Could not load official data catalog.');
  state.bootstrap = await response.json();
  renderStats(); renderQuickQuestions(); renderFeatured(); renderQuestionLibrary(); renderSources();
}
function renderStats() {
  const s = state.bootstrap.stats;
  const items = [
    ['Detailed occupations', s.occupations.toLocaleString(), 'BLS national', 'blue'],
    ['State occupation rows', compactNumber(s.state_occupation_rows), `${s.states_and_districts} areas`, 'green'],
    ['Official sources', s.official_sources, 'BLS · Census · O*NET', 'blue'],
    ['Degree field groups', s.degree_field_groups, s.census_vintage, 'green'],
    ['Wage vintage', s.latest_wage_vintage, 'OEWS', 'blue'],
    ['Projection window', s.projection_window, 'BLS', 'green'],
  ];
  $('#statsGrid').innerHTML = items.map(([label,value,note,color]) => `<div class="stat-card ${color}"><small>${escapeHTML(label)}</small><strong>${escapeHTML(value)}</strong><span>${escapeHTML(note)}</span></div>`).join('');
}
function renderQuickQuestions() {
  const examples = [
    'Which states pay nuclear engineers the most?',
    'What skills do public relations specialists need?',
    "Which broad bachelor's degree fields have the highest median earnings?",
    'What is the job outlook for political scientists?',
  ];
  $('#quickQuestions').innerHTML = examples.map(q=>`<button class="question-chip" data-question="${escapeHTML(q)}">${escapeHTML(q)}</button>`).join('');
}
function renderFeatured() {
  $('#featuredGrid').innerHTML = state.bootstrap.featured_occupations.map(item=>`
    <button class="featured-card" data-soc="${item.soc_code}">
      <small>${item.soc_code}</small><h3>${escapeHTML(item.occupation_title)}</h3>
      <div class="featured-metrics"><span>Median wage<strong>${formatValue(item.annual_median_wage_2025,'currency')}</strong></span><span>Growth 2024–34<strong>${formatValue(item.employment_change_percent_2024_2034,'percent')}</strong></span></div>
    </button>`).join('');
}
function renderQuestionLibrary() {
  $('#questionLibrary').innerHTML = state.bootstrap.question_catalog.map((group,index)=>`
    <section class="question-group card"><div class="question-group-head"><div class="dataset-logo">${index<3?'BLS':index===3?'O*N':index===4?'ACS':'BLS'}</div><div><h2>${escapeHTML(group.dataset)}</h2><p>${escapeHTML(group.description)}</p></div></div>
    <div class="question-items">${group.questions.map(q=>`<button class="library-question" data-question="${escapeHTML(q)}"><span>${escapeHTML(q)}</span><span>→</span></button>`).join('')}</div></section>`).join('');
}
function renderSources() {
  const sources = state.bootstrap.catalog.sources;
  $('#sourceCatalog').innerHTML = sources.map(source=>`
    <article class="source-card card"><div class="source-meta"><span class="meta-pill">${escapeHTML(source.agency.includes('Census')?'Census':source.agency.includes('O*NET')?'O*NET':'BLS')}</span><span class="meta-pill">${escapeHTML(source.vintage)}</span></div>
    <h2>${escapeHTML(source.title)}</h2><p>${escapeHTML(source.coverage)}</p>
    <div class="source-details"><div><strong>Agency</strong>${escapeHTML(source.agency)}</div><div><strong>Terms</strong>${escapeHTML(source.license)}</div></div>
    <p><a href="${escapeHTML(source.authoritative_url)}" target="_blank" rel="noreferrer">Open authoritative source ↗</a></p></article>`).join('');
}

async function analyzeQuestion(question, dataset='auto') {
  question = question.trim(); if (!question) return;
  navigate('ask'); $('#questionInput').value = question; $('#datasetSelect').value = dataset;
  $('#resultArea').innerHTML = `<div class="loading-card card"><div class="spinner"></div><div><strong>Building a verified query</strong><p>Routing to the official dataset and calculating the answer...</p></div></div>`;
  try {
    const response = await fetch('/api/ask',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({question,dataset})});
    if (!response.ok) throw new Error((await response.json()).detail || 'Analysis failed.');
    state.currentResult = await response.json(); renderResult(state.currentResult);
  } catch (error) {
    $('#resultArea').innerHTML = `<div class="empty-state card"><div class="empty-icon">!</div><div><h3>Analysis could not be completed</h3><p>${escapeHTML(error.message)}</p></div></div>`;
  }
}
function confidenceMarkup(conf) {
  return `<div class="confidence-box"><small>Evidence confidence</small><div class="confidence-score"><strong>${conf.score}</strong><span>/100 · ${escapeHTML(conf.label)}</span></div><p>${escapeHTML(conf.reason)}</p></div>`;
}
function chartMarkup(result) {
  const spec = result.chart || {};
  if (!spec.label_key || !spec.value_key || !result.rows.some(row=>row[spec.value_key] !== null && row[spec.value_key] !== undefined)) return '';
  const values = result.rows.map(row=>Number(row[spec.value_key])||0);
  const max = Math.max(...values.map(Math.abs),1);
  return `<div class="chart-card"><h3>${escapeHTML(spec.title || 'Result chart')}</h3><div class="bar-chart">${result.rows.slice(0,15).map(row=>{
    const v = Number(row[spec.value_key])||0; const width = Math.max(2,Math.abs(v)/max*100);
    return `<div class="bar-row"><div class="bar-label" title="${escapeHTML(row[spec.label_key])}">${escapeHTML(row[spec.label_key])}</div><div class="bar-track"><div class="bar-fill" style="width:${width}%"></div></div><div class="bar-value">${formatValue(row[spec.value_key],spec.value_format)}</div></div>`;
  }).join('')}</div></div>`;
}
function tableMarkup(result) {
  if (!result.rows.length || !result.columns.length) return '';
  return `<div class="table-card"><h3>Source-backed result table</h3><table class="data-table"><thead><tr>${result.columns.map(c=>`<th>${escapeHTML(c.label)}</th>`).join('')}</tr></thead><tbody>${result.rows.map(row=>`<tr>${result.columns.map(c=>`<td>${escapeHTML(formatValue(row[c.key],c.format))}</td>`).join('')}</tr>`).join('')}</tbody></table></div>`;
}
function renderResult(result) {
  if (result.status !== 'supported') {
    $('#resultArea').innerHTML = `<article class="result-card card"><div class="result-top"><div><div class="result-status refused">Safe refusal</div><h2 class="result-title">${escapeHTML(result.headline)}</h2><p class="result-summary">${escapeHTML(result.summary)}</p></div>${confidenceMarkup(result.confidence)}</div>
      <div class="refusal-body"><h3>Closest answerable questions</h3><div class="suggestion-list">${result.suggestions.map(q=>`<button class="suggestion-button" data-question="${escapeHTML(q)}">→ ${escapeHTML(q)}</button>`).join('')}</div></div></article>`;
    return;
  }
  const sources = result.sources.map(s=>`<a class="source-link" href="${escapeHTML(s.url)}" target="_blank" rel="noreferrer">${escapeHTML(s.agency)} · ${escapeHTML(s.vintage)} ↗</a>`).join('');
  const limitations = result.limitations.length ? `<ul class="limitations">${result.limitations.map(x=>`<li>${escapeHTML(x)}</li>`).join('')}</ul>` : '';
  const suggestions = result.suggestions.length ? `<div class="evidence-box"><small>Continue exploring</small><div class="suggestion-list">${result.suggestions.map(q=>`<button class="suggestion-button" data-question="${escapeHTML(q)}">→ ${escapeHTML(q)}</button>`).join('')}</div></div>` : '';
  $('#resultArea').innerHTML = `<article class="result-card card"><div class="result-top"><div><div class="result-status">Verified by code</div><h2 class="result-title">${escapeHTML(result.headline)}</h2><p class="result-summary">${escapeHTML(result.summary)}</p></div>${confidenceMarkup(result.confidence)}</div>
    <div class="proof-strip"><div><small>1 · Route</small><strong>${escapeHTML(result.dataset)}</strong></div><div><small>2 · Intent</small><strong>${escapeHTML(result.intent)}</strong></div><div><small>3 · Rows used</small><strong>${result.evidence.rows_considered.toLocaleString()}</strong></div><div><small>4 · Evidence ID</small><strong>${escapeHTML(result.evidence_id)}</strong></div></div>
    <div class="result-body"><div class="result-main">${chartMarkup(result)}${tableMarkup(result)}</div><aside class="evidence-panel"><div class="evidence-box green"><small>Calculation</small><strong>Deterministic result</strong><p>${escapeHTML(result.evidence.calculation)}</p></div><div class="evidence-box blue"><small>Evidence Passport</small><strong class="evidence-id">${escapeHTML(result.evidence_id)}</strong><p>Changes when the question plan, source rows, or result changes.</p></div><div class="evidence-box"><small>Official sources</small>${sources}</div><div class="evidence-box"><small>Limitations</small>${limitations || '<p>No additional limitation note.</p>'}</div>${suggestions}<div class="result-actions"><button class="secondary-button" id="downloadReport">Download evidence report</button><button class="secondary-button" id="copyEvidence">Copy Evidence ID</button></div></aside></div></article>`;
}

async function searchOccupations(query) {
  if (!query.trim()) { $('#occupationSearchResults').innerHTML=''; return; }
  const response = await fetch(`/api/search/occupations?q=${encodeURIComponent(query)}&limit=10`);
  const data = await response.json();
  $('#occupationSearchResults').innerHTML = data.results.map(r=>`<button class="search-result" data-soc="${r.soc_code}"><strong>${escapeHTML(r.occupation_title)}</strong><small>${r.soc_code} · ${formatValue(r.annual_median_wage_2025,'currency')} · ${escapeHTML(r.typical_entry_education||'Education not published')}</small></button>`).join('') || '<p>No matching occupation found.</p>';
}
async function loadOccupation(soc) {
  navigate('occupations'); $('#occupationProfile').className='card occupation-profile-placeholder'; $('#occupationProfile').innerHTML='<div class="spinner"></div><p>Loading official occupation profile...</p>';
  try {
    const response = await fetch(`/api/occupation/${encodeURIComponent(soc)}`); if(!response.ok) throw new Error('Occupation profile not found.');
    const data = await response.json(); renderOccupationProfile(data);
  } catch(error) { $('#occupationProfile').innerHTML=`<div class="empty-icon">!</div><h3>Could not load profile</h3><p>${escapeHTML(error.message)}</p>`; }
}
function renderOccupationProfile(data) {
  const o = data.occupation;
  const skills = data.skills.slice(0,8); const maxSkill = Math.max(...skills.map(s=>Number(s.importance)||0),1);
  $('#occupationProfile').className='card occupation-profile';
  $('#occupationProfile').innerHTML=`<header class="occupation-header"><small>${escapeHTML(o.soc_code)} · BLS + O*NET unified profile</small><h2>${escapeHTML(o.occupation_title)}</h2><p>${escapeHTML(o.description||'Official occupation profile')}</p></header>
    <div class="occupation-kpis"><div><small>Median wage</small><strong>${formatValue(o.annual_median_wage_2025,'currency')}</strong></div><div><small>Employment</small><strong>${formatValue(o.employment_2025,'number')}</strong></div><div><small>Growth 2024–34</small><strong>${formatValue(o.employment_change_percent_2024_2034,'percent')}</strong></div><div><small>Annual openings</small><strong>${formatValue((o.annual_openings_2024_2034_thousands||0)*1000,'number')}</strong></div><div><small>Typical education</small><strong>${escapeHTML(o.typical_entry_education||'Not published')}</strong></div></div>
    <div class="occupation-content"><section class="profile-section"><h3>Essential skills</h3><div class="skill-list">${skills.map(s=>`<div class="skill-item"><span>${escapeHTML(s.skill)}</span><strong>${Number(s.importance).toFixed(2)}</strong><div class="skill-meter"><span style="width:${Number(s.importance)/maxSkill*100}%"></span></div></div>`).join('')||'<p>No published skills.</p>'}</div></section>
    <section class="profile-section"><h3>Knowledge areas</h3><div class="skill-list">${data.knowledge.slice(0,8).map(k=>`<div class="skill-item"><span>${escapeHTML(k.knowledge_area)}</span><strong>${Number(k.importance).toFixed(2)}</strong></div>`).join('')||'<p>No published knowledge areas.</p>'}</div></section>
    <section class="profile-section"><h3>Core tasks</h3><div class="task-list">${data.tasks.slice(0,7).map(t=>`<div class="task-item">${escapeHTML(t.task)}</div>`).join('')||'<p>No published tasks.</p>'}</div></section>
    <section class="profile-section"><h3>Highest-paying states with published estimates</h3><ul>${data.top_states_by_pay.slice(0,8).map(s=>`<li><strong>${escapeHTML(s.state)}</strong> · ${formatValue(s.median_annual_wage,'currency')} median · ${formatValue(s.employment,'number')} employed</li>`).join('')||'<li>No state estimates published.</li>'}</ul></section>
    <section class="profile-section"><h3>Software and tools</h3><ul>${data.software.slice(0,10).map(s=>`<li>${escapeHTML(s.software_or_tool)} <small>${s.in_demand==='Y'?'· in demand':''}${s.hot_technology==='Y'?' · hot technology':''}</small></li>`).join('')||'<li>No software examples published.</li>'}</ul></section>
    <section class="profile-section"><h3>Ask about this occupation</h3><div class="suggestion-list"><button class="suggestion-button" data-question="Which states pay ${escapeHTML(o.occupation_title.toLowerCase())} the most?">→ Compare state pay</button><button class="suggestion-button" data-question="What is the job outlook for ${escapeHTML(o.occupation_title.toLowerCase())}?">→ View projections</button><button class="suggestion-button" data-question="What skills do ${escapeHTML(o.occupation_title.toLowerCase())} need?">→ View skills with evidence</button></div></section></div>`;
}
async function downloadReport() {
  if (!state.currentResult) return;
  const response = await fetch('/api/report',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({question:state.currentResult.question,dataset:$('#datasetSelect').value})});
  const blob = await response.blob(); const url = URL.createObjectURL(blob); const a=document.createElement('a'); a.href=url; a.download='careerproof-evidence-report.html'; a.click(); URL.revokeObjectURL(url); toast('Evidence report downloaded');
}

document.addEventListener('click', event => {
  const nav = event.target.closest('.nav-item'); if(nav) navigate(nav.dataset.workspace);
  const q = event.target.closest('[data-question]'); if(q) analyzeQuestion(q.dataset.question,'auto');
  const soc = event.target.closest('[data-soc]'); if(soc) loadOccupation(soc.dataset.soc);
  if(event.target.closest('#openSources')) navigate('sources');
  if(event.target.closest('#mobileMenu')) $('.sidebar').classList.toggle('open');
  if(event.target.closest('#downloadReport')) downloadReport();
  if(event.target.closest('#copyEvidence') && state.currentResult) { navigator.clipboard.writeText(state.currentResult.evidence_id); toast('Evidence ID copied'); }
  if(event.target.closest('.demo-refusal')) analyzeQuestion("What bachelor's degree should I pursue for the highest pay after becoming a lawyer?",'auto');
});
$('#askForm').addEventListener('submit',e=>{e.preventDefault(); analyzeQuestion($('#questionInput').value,$('#datasetSelect').value);});
let searchTimer; $('#occupationSearch').addEventListener('input',e=>{clearTimeout(searchTimer); searchTimer=setTimeout(()=>searchOccupations(e.target.value),220);});
$('#questionInput').addEventListener('keydown',e=>{if(e.key==='Enter'&&!e.shiftKey){e.preventDefault(); $('#askForm').requestSubmit();}});
loadBootstrap().catch(error=>{console.error(error);toast(error.message);});
