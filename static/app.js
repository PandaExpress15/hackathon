/* CareerProof AI 5.0
 * AI interprets. Code calculates. Evidence verifies. You decide.
 */

const $ = (selector, root = document) => root.querySelector(selector);
const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];
const SVG_NS = "http://www.w3.org/2000/svg";

const WEIGHT_META = {
  interest_fit: { label: "Interest and skill fit", hint: "Controlled retrieval plus explicit intent signals" },
  resilience: { label: "AI resilience", hint: "Transparent human and real-world advantage profile" },
  salary: { label: "Salary", hint: "Published BLS national median wage" },
  growth: { label: "Projected growth", hint: "BLS 2024–2034 projection" },
  openings: { label: "Annual openings", hint: "BLS projected average openings" },
  education: { label: "Entry burden", hint: "Education ceiling plus related experience" },
  location: { label: "Location fit", hint: "Published state coverage, pay, and employment" },
  stability: { label: "Market stability", hint: "Employment size, openings, and state breadth" },
};

const DEFAULT_PATH_WEIGHTS = { interest_fit: 22, resilience: 23, salary: 18, growth: 10, openings: 9, education: 8, location: 5, stability: 5 };
const DEFAULT_COMPARE_WEIGHTS = { interest_fit: 12, resilience: 25, salary: 20, growth: 10, openings: 10, education: 8, location: 8, stability: 7 };
const DEMO_COMPARE_WEIGHTS = { interest_fit: 12, resilience: 30, salary: 22, growth: 8, openings: 8, education: 10, location: 5, stability: 5 };
const WORKSPACE_TITLES = {
  home: "Home", universe: "Career Universe", path: "Build My Path", compare: "Compare Lab",
  bridge: "Skills Bridge", degrees: "Degree Explorer", location: "Location Intelligence",
  saved: "Saved Plans", trust: "Evidence Center", ask: "Ask CareerProof", occupations: "Occupation Explorer",
};

const safeStorage = (() => {
  const memory = new Map();
  try {
    const storage = window.localStorage;
    const testKey = "__careerproof_storage_test__";
    storage.setItem(testKey, "1");
    storage.removeItem(testKey);
    return storage;
  } catch {
    return {
      getItem: (key) => memory.has(String(key)) ? memory.get(String(key)) : null,
      setItem: (key, value) => memory.set(String(key), String(value)),
      removeItem: (key) => memory.delete(String(key)),
      clear: () => memory.clear(),
      key: (index) => [...memory.keys()][index] ?? null,
      get length() { return memory.size; },
    };
  }
})();

const state = {
  bootstrap: null,
  home: null,
  universe: null,
  activeWorkspace: "home",
  selectedInterests: new Set(["Electronics", "Programming", "Law"]),
  skills: ["Python", "Arduino", "Writing"],
  workEnvironment: new Set(["Hands-on", "Office or analytical", "People-facing"]),
  pathWeights: { ...DEFAULT_PATH_WEIGHTS },
  compareWeights: { ...DEFAULT_COMPARE_WEIGHTS },
  compareValues: ["Electrical Engineers", "Nuclear Engineers", "Lawyers", ""],
  compareResolved: [null, null, null, null],
  comparisonTray: new Map(),
  saved: loadJSON("careerproof-saved", []),
  decisionNotes: safeStorage.getItem("careerproof-decision-notes") || "",
  lastPath: loadJSON("careerproof-last-path", null),
  lastInterpretation: null,
  lastCompare: null,
  lastOccupation: null,
  occupationCache: new Map(),
  universeCategory: null,
  universeCategoryData: null,
  judgeData: null,
  judgeStep: 0,
  judgeMode: "full",
  judgeStartedAt: null,
  judgeStepStartedAt: null,
  judgeTimer: null,
  judgeAutoplay: false,
  judgeAutoTimer: null,
  trustLoaded: { model: false, quality: false, diagnostic: false },
  toastTimer: null,
};

function loadJSON(key, fallback) {
  try {
    const value = safeStorage.getItem(key);
    return value ? JSON.parse(value) : fallback;
  } catch {
    return fallback;
  }
}

function escapeHTML(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function compactNumber(value, decimals = 1) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return "Not published";
  const number = Number(value);
  if (Math.abs(number) >= 1_000_000) return `${(number / 1_000_000).toFixed(decimals).replace(/\.0$/, "")}M`;
  if (Math.abs(number) >= 1_000) return `${(number / 1_000).toFixed(decimals).replace(/\.0$/, "")}K`;
  return Math.round(number).toLocaleString();
}

function formatNumber(value, decimals = 0) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return "Not published";
  return Number(value).toLocaleString(undefined, { maximumFractionDigits: decimals });
}

function money(value, compact = false) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return "Not published";
  if (compact) return `$${compactNumber(value, 0)}`;
  return new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 }).format(Number(value));
}

function pct(value, decimals = 1) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return "Not published";
  const number = Number(value);
  return `${number > 0 ? "+" : ""}${number.toFixed(decimals)}%`;
}

function slug(value) {
  return String(value ?? "").toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");
}

function titleCase(value) {
  return String(value ?? "").replaceAll("_", " ").replace(/\b\w/g, (m) => m.toUpperCase());
}

function debounce(fn, delay = 250) {
  let timer;
  return (...args) => {
    clearTimeout(timer);
    timer = setTimeout(() => fn(...args), delay);
  };
}

async function api(url, options = {}) {
  const config = { ...options, headers: { "Content-Type": "application/json", ...(options.headers || {}) } };
  const response = await fetch(url, config);
  let payload;
  try { payload = await response.json(); } catch { payload = null; }
  if (!response.ok) {
    const message = payload?.detail || payload?.message || `Request failed (${response.status})`;
    throw new Error(message);
  }
  return payload;
}

function showToast(message) {
  const toast = $("#toast");
  toast.textContent = message;
  toast.classList.add("show");
  clearTimeout(state.toastTimer);
  state.toastTimer = setTimeout(() => toast.classList.remove("show"), 2600);
}

function setButtonLoading(button, loading, label = "Working…") {
  if (!button) return;
  if (loading) {
    button.dataset.original = button.innerHTML;
    button.disabled = true;
    button.innerHTML = `<span class="spinner" style="width:16px;height:16px"></span><span>${escapeHTML(label)}</span>`;
  } else {
    button.disabled = false;
    if (button.dataset.original) button.innerHTML = button.dataset.original;
  }
}

function scrollToTop() {
  window.scrollTo({ top: 0, behavior: matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth" });
}

function normalizeWeights(weights) {
  const clean = {};
  let total = 0;
  Object.keys(WEIGHT_META).forEach((key) => {
    clean[key] = Math.max(0, Number(weights[key] || 0));
    total += clean[key];
  });
  if (total <= 0) return { ...DEFAULT_PATH_WEIGHTS };
  const normalized = {};
  Object.entries(clean).forEach(([key, value]) => { normalized[key] = Number((value / total * 100).toFixed(1)); });
  return normalized;
}

const CATEGORY_COLORS = {
  blue: "#4d72ff", violet: "#9b53ff", gold: "#e9b44c", cyan: "#22b8e7",
  green: "#19b97c", teal: "#19b3ad", indigo: "#7165f1", orange: "#eb8d45",
};

function normalizeStatsPayload(raw = {}) {
  return {
    ...raw,
    occupations: Number(raw.occupations || 0),
    state_occupation_records: Number(raw.state_occupation_records ?? raw.state_occupation_rows ?? 0),
    degree_relationships: Number(raw.degree_relationships ?? raw.degree_occupation_links ?? 0),
    source_families: Number(raw.source_families ?? raw.official_sources ?? 0),
  };
}

function normalizeSourcePayload(source = {}) {
  return {
    ...source,
    name: source.name || source.title || source.dataset_name || source.id,
    description: source.description || source.coverage || source.use || "Official source snapshot used by CareerProof.",
    publication_date: source.publication_date || source.vintage || source.as_of,
    year: source.year || source.vintage,
    url: source.url || source.authoritative_url || source.public_url,
    direct: source.direct !== false,
  };
}

function normalizeInterpretationPayload(raw = {}) {
  const profile = raw.normalized_profile || raw.profile || {};
  return {
    ...raw,
    interpretation_summary: raw.interpretation_summary || raw.goal || "CareerProof converted your inputs into an editable decision profile.",
    constraints: (raw.constraints || []).map((item) => ({ ...item, hard: item.hard ?? String(item.strength || "").toLowerCase() === "hard" })),
    priorities: raw.priorities || [],
    assumptions: raw.assumptions || [],
    warnings: raw.warnings || [],
    remote_preference: raw.remote_preference || profile.remote_preference || "Flexible",
    willing_to_relocate: raw.willing_to_relocate ?? profile.willing_to_relocate ?? true,
    normalized_profile: profile,
  };
}

function normalizeTaskImpactPayload(raw = {}) {
  if (raw.ai_task_impact) return raw.ai_task_impact;
  const taskImpact = raw.task_impact || raw;
  const group = (tasks = []) => ({ count: tasks.length, tasks });
  return {
    human_led: group(taskImpact.human_led || []),
    ai_augmented: group(taskImpact.augmented || taskImpact.ai_augmented || []),
    routine_reduced: group(taskImpact.reduced || taskImpact.routine_reduced || []),
    method: taskImpact.method || "Transparent classification of official O*NET task statements.",
  };
}

function normalizeResiliencePayload(raw = {}) {
  if (!raw || !Object.keys(raw).length) return { overall_score: 0, overall_label: "Not available", dimensions: {}, ai_augmentation_potential: 0, ai_task_impact: normalizeTaskImpactPayload({}) };
  const dimensionsArray = Array.isArray(raw.dimensions) ? raw.dimensions : Object.values(raw.dimensions || {});
  const dimensions = {};
  dimensionsArray.forEach((dimension) => { if (dimension?.key || dimension?.label) dimensions[dimension.key || slug(dimension.label)] = dimension; });
  const augmentation = typeof raw.ai_augmentation_potential === "object" ? raw.ai_augmentation_potential.score : raw.ai_augmentation_potential;
  return {
    ...raw,
    overall_score: Number(raw.overall_score ?? raw.score ?? 0),
    overall_label: raw.overall_label || raw.label || "Review",
    dimensions,
    ai_augmentation_potential: Number(augmentation || 0),
    ai_task_impact: normalizeTaskImpactPayload(raw),
  };
}

function normalizeRoadmapPayload(raw = {}) {
  if (raw.learn || raw.build || raw.prepare) return raw;
  const learn = [], build = [], prepare = [];
  (raw.actions || []).forEach((action) => {
    const normalized = { title: action.title || action.label || titleCase(action.type), detail: action.detail || "" };
    if (["skill", "tool", "software"].includes(action.type)) learn.push(normalized);
    else if (["project", "portfolio", "build"].includes(action.type)) build.push(normalized);
    else prepare.push(normalized);
  });
  if (!build.length) build.push({ title: "Create a documented proof-of-skill project", detail: "Turn one target skill into a portfolio artifact that an advisor or employer can inspect." });
  return { ...raw, learn, build, prepare, boundary: raw.boundary || "Example actions are planning prompts, not guaranteed requirements." };
}

function normalizeChallengePayload(raw = {}) {
  if (!raw || !Object.keys(raw).length) return {};
  const weakest = Array.isArray(raw.weakest_evidence)
    ? raw.weakest_evidence.map((item) => `${titleCase(item.component)} ${Number(item.score).toFixed(1)}/100`).join(" · ")
    : raw.weakest_evidence;
  let challenger = raw.strongest_challenger;
  if (!challenger && raw.strongest_alternative) {
    const title = String(raw.strongest_alternative).split(" is the strongest challenger")[0];
    challenger = { occupation_title: title, why_it_could_win: raw.strongest_alternative };
  }
  return {
    ...raw,
    weakest_evidence: weakest || "No core source field is missing, but occupation data cannot describe a specific employer or person.",
    missing_information: raw.missing_information || raw.missing_or_limited_evidence || [],
    strongest_challenger: challenger || null,
  };
}

function normalizeCareerPayload(raw = {}) {
  const stateDetail = raw.state_match || raw.preferred_state_detail;
  const resilience = normalizeResiliencePayload(raw.resilience_profile || {
    overall_score: raw.resilience_score,
    label: raw.resilience_label,
  });
  return {
    ...raw,
    soc_code: raw.soc_code || raw.code,
    occupation_title: raw.occupation_title || raw.title || raw.occupation,
    median_wage: raw.median_wage ?? raw.annual_median_wage_2025 ?? raw.median_annual_wage,
    wage_p10: raw.wage_p10 ?? raw.annual_wage_p10_2025,
    wage_p90: raw.wage_p90 ?? raw.annual_wage_p90_2025,
    growth_percent: raw.growth_percent ?? raw.employment_change_percent_2024_2034 ?? raw.growth_2024_2034,
    annual_openings: raw.annual_openings ?? ((raw.annual_openings_2024_2034_thousands || 0) * 1000),
    education: raw.education || raw.typical_entry_education,
    score: Number(raw.score ?? raw.careerproof_score ?? 0),
    components: raw.components || raw.score_components || {},
    contributions: raw.contributions || raw.weighted_contributions || {},
    why: raw.why || raw.reasons || [],
    state_match: stateDetail ? {
      ...stateDetail,
      median_wage: stateDetail.median_wage ?? stateDetail.nominal_median_wage,
    } : null,
    resilience_profile: resilience,
    resilience_label: raw.resilience_label || resilience.overall_label,
    resilience_score: Number(raw.resilience_score ?? resilience.overall_score ?? 0),
    roadmap: normalizeRoadmapPayload(raw.roadmap || {}),
    challenge: normalizeChallengePayload(raw.challenge || {}),
  };
}

function normalizeSensitivityPayload(raw = []) {
  return (raw || []).map((scenario) => ({
    ...scenario,
    top_occupation: scenario.top_occupation || scenario.top_career?.occupation_title,
    top_score: Number(scenario.top_score ?? scenario.top_career?.score ?? 0),
  }));
}

function normalizePathPayload(raw = {}) {
  const normalizeGroup = (items) => (items || []).map(normalizeCareerPayload);
  const groups = {};
  Object.entries(raw.result_groups || {}).forEach(([key, items]) => { groups[key] = normalizeGroup(items); });
  const portfolio = {};
  Object.entries(raw.portfolio || {}).forEach(([key, value]) => { portfolio[key] = value && typeof value === "object" && value.soc_code ? normalizeCareerPayload(value) : value; });
  return {
    ...raw,
    interpretation: normalizeInterpretationPayload(raw.interpretation || raw.interpreted_request || {}),
    results: normalizeGroup(raw.results),
    result_groups: groups,
    portfolio,
    sensitivity: normalizeSensitivityPayload(raw.sensitivity),
    what_would_change_recommendation: (raw.what_would_change_recommendation || raw.what_would_change_the_recommendation || []).map((item) => ({
      ...item,
      condition: item.condition || item.scenario,
      impact: item.impact || item.explanation,
    })),
    ranking_explanation: raw.ranking_explanation ? { ...raw.ranking_explanation, top_reason: raw.ranking_explanation.top_reason || raw.ranking_explanation.plain_language } : null,
    freshness: { ...(raw.freshness || raw.data_freshness || {}), summary: raw.freshness?.summary || raw.data_freshness?.message || raw.data_freshness?.headline },
    disclosure: raw.disclosure || raw.summary,
  };
}

function normalizeComparePayload(raw = {}) {
  return {
    ...raw,
    results: (raw.results || []).map(normalizeCareerPayload),
    sensitivity: normalizeSensitivityPayload(raw.sensitivity),
    freshness: { ...(raw.freshness || raw.data_freshness || {}), summary: raw.freshness?.summary || raw.data_freshness?.message },
  };
}

function normalizeBridgePayload(raw = {}) {
  return {
    ...raw,
    source: normalizeCareerPayload(raw.source || {}),
    target: normalizeCareerPayload(raw.target || {}),
    overall_overlap: Number(raw.overall_overlap ?? raw.overlap_score ?? 0),
    task_similarity: Number(raw.task_similarity ?? raw.component_scores?.task_similarity ?? 0),
    technology_overlap: Number(raw.technology_overlap ?? raw.component_scores?.software_overlap ?? 0),
    shared_skills: (raw.shared_skills || []).map((item) => ({
      ...item,
      skill_name: item.skill_name || item.skill,
      shared_score: Number(item.shared_score ?? Math.min(item.source_importance || 0, item.target_importance || 0)),
    })),
    skill_gaps: (raw.skill_gaps || raw.skills_to_build || []).map((item) => ({ ...item, skill_name: item.skill_name || item.skill })),
    pathway: raw.pathway || (raw.next_steps || []).map((step, index) => ({ step: index + 1, title: `Transition step ${index + 1}`, detail: step })),
    boundary: raw.boundary || raw.decision_confidence?.reason || "This is an occupational-profile comparison, not a guarantee of transition readiness or employment.",
  };
}

function normalizeUniversePayload(raw = {}) {
  const categories = (raw.categories || []).map((category) => ({
    ...category,
    name: category.name || category.label,
    color: category.color || CATEGORY_COLORS[category.accent] || "#5475ff",
    size: Number(category.size ?? category.occupation_count ?? 0),
  }));
  return { ...raw, categories, occupation_count: raw.occupation_count || categories.reduce((sum, item) => sum + item.size, 0) };
}

function normalizeUniverseCategoryPayload(raw = {}) {
  const normalized = normalizeUniversePayload(raw);
  const category = normalized.categories[0] || {};
  return {
    ...raw,
    name: category.name || "Career field",
    color: category.color || "#5475ff",
    description: `Explore ${formatNumber(category.size || 0)} occupations connected through official SOC categories and work-profile evidence.`,
    occupations: (raw.nodes || raw.occupations || []).map(normalizeCareerPayload),
  };
}

function normalizeHomePayload(raw = {}) {
  const path = normalizePathPayload(raw.path || {});
  const impact = raw.impact || {};
  return {
    ...raw,
    path,
    top_matches: (raw.top_matches || path.results || []).map(normalizeCareerPayload),
    impact: {
      ...impact,
      ai_task_impact: normalizeTaskImpactPayload({ task_impact: {
        human_led: impact.human_led_examples || [], augmented: impact.augmented_examples || [], reduced: impact.reduced_examples || [], method: impact.boundary,
      } }),
    },
    local_opportunities: raw.local_opportunities || [],
    stats: normalizeStatsPayload(raw.stats),
    freshness: { ...(raw.freshness || raw.data_freshness || {}), summary: raw.freshness?.summary || raw.data_freshness?.message },
  };
}

function normalizeOccupationPayload(raw = {}) {
  if (raw.profile) return raw;
  const occupation = raw.occupation || {};
  const profile = normalizeCareerPayload({
    ...occupation,
    category: raw.category,
    resilience_profile: raw.resilience_profile,
  });
  const coverageComponents = raw.coverage?.components || {};
  const years = { national_wage: "May 2025", projection: "2024–2034", skills: "O*NET 30.3", tasks: "O*NET 30.3", education: "2024–2034", states: "May 2025", degrees: "CIP 2020 / SOC 2018" };
  const locationRows = (raw.opportunity_states || []).map((row) => ({
    ...row,
    label: row.state,
    display_value: money(row.purchasing_power_wage || row.nominal_median_wage),
  }));
  return {
    ...raw,
    profile,
    resilience_profile: normalizeResiliencePayload(raw.resilience_profile),
    skills: (raw.skills || []).map((item) => ({ ...item, skill_name: item.skill_name || item.skill })),
    technologies: (raw.software || []).map((item) => ({ ...item, commodity_title: item.commodity_title || item.software_or_tool || item.software })),
    tasks: (raw.tasks || []).map((item) => ({ ...item, task_description: item.task_description || item.task })),
    data_coverage: {
      percent: raw.coverage?.score || 0,
      components: Object.fromEntries(Object.entries(coverageComponents).map(([key, available]) => [key, { available: Boolean(available), year: years[key] || "Published snapshot" }])),
    },
    location_opportunity: {
      rows: locationRows,
      formula: "Opportunity score = 40% purchasing-power wage percentile + 30% employment percentile + 20% location-quotient percentile + 10% inverse employment-estimate RSE.",
    },
    source_lineage: (raw.data_lineage || []).map((item) => ({ dataset: item.source, value: item.provides, year: "See source catalog", direct: true })),
    data_freshness: { summary: "Wages use May 2025 data, projections use 2024–2034, and O*NET work content uses release 30.3." },
    limitations: [
      "Occupation-level estimates describe groups, not individual offers or guaranteed outcomes.",
      "Career resilience is a transparent CareerProof-derived profile, not an official automation forecast.",
    ],
  };
}

function normalizeDegreePayload(raw = {}) {
  return {
    ...raw,
    boundary: raw.boundary || raw.limitations?.[0] || "The NCES/BLS crosswalk is a qualitative relationship, not a placement rate or proof of a required degree.",
    related_careers: (raw.related_careers || raw.results || []).map(normalizeCareerPayload),
    field_earnings: raw.field_earnings || null,
  };
}

function normalizeLocationPayload(raw = {}) {
  return {
    ...raw,
    rows: (raw.rows || raw.results || []).map((row) => ({
      ...row,
      label: row.label || row.state,
      nominal_wage: row.nominal_wage ?? row.nominal_median_wage,
      confidence: row.confidence || row.decision_confidence,
    })),
    boundary: raw.boundary || raw.summary,
    freshness: { ...(raw.freshness || raw.data_freshness || {}), summary: raw.freshness?.summary || raw.data_freshness?.message || "BLS May 2025 wages are adjusted with BEA 2024 state price levels." },
  };
}

function displayForColumn(row, column) {
  const value = row[column.key];
  if (column.format === "currency") return money(value);
  if (column.format === "percent") return pct(value);
  if (column.format === "decimal") return value === null || value === undefined ? "Not published" : Number(value).toFixed(2);
  if (column.format === "number") return formatNumber(value);
  return String(value ?? "—");
}

function normalizeAskPayload(raw = {}) {
  if (raw.analysis || raw.explanation) return raw;
  if (raw.status === "refused" || raw.status === "needs_clarification") {
    return {
      ...raw,
      explanation: raw.summary,
      refusal_reason: raw.query_plan?.reason || raw.summary,
      boundary: raw.evidence?.trust_boundary,
    };
  }
  const columns = raw.columns || [];
  const labelKey = raw.chart?.label_key || columns[0]?.key || "label";
  const valueKey = raw.chart?.value_key || columns[1]?.key;
  const rows = (raw.rows || []).map((row) => ({
    ...row,
    label: row.label || row[labelKey] || row.occupation || row.state || row.skill,
    display_value: displayForColumn(row, columns.find((column) => column.key === valueKey) || { key: valueKey }),
  }));
  const sourceNames = (raw.sources || []).map((source) => source.title || source.agency || source.id);
  const sourceUrls = (raw.sources || []).map((source) => source.url).filter(Boolean);
  return {
    ...raw,
    explanation: raw.summary,
    source_id: raw.sources?.[0]?.id || raw.dataset,
    analysis: {
      rows,
      value_key: valueKey,
      table_columns: columns.map((column) => column.key),
      rows_used: raw.evidence?.rows_returned ?? rows.length,
      suppressed_or_excluded: Math.max(0, Number(raw.evidence?.rows_considered || rows.length) - Number(raw.evidence?.rows_returned || rows.length)),
      calculation: raw.evidence?.calculation,
    },
    evidence: {
      ...raw.evidence,
      evidence_id: raw.evidence_id,
      confidence: raw.confidence,
      source_names: sourceNames,
      source_urls: sourceUrls,
      dataset_note: raw.evidence?.trust_boundary,
    },
    query_plan: {
      ...raw.query_plan,
      intent: raw.intent,
      occupation_title: raw.profile?.occupation_title,
      geography: raw.query_plan?.geography || raw.query_plan?.state || "National or requested ranking",
      metric: valueKey,
      source_id: raw.sources?.[0]?.id || raw.dataset,
    },
  };
}

function normalizeModelPayload(raw = {}) {
  return {
    ...raw,
    dimensions: (raw.dimensions || []).map((dimension) => ({ ...dimension, signals: dimension.signals || dimension.keywords || [] })),
    missing_data_policy: raw.missing_data_policy || "Missing work-content fields reduce evidence coverage. CareerProof does not invent dimension evidence.",
    task_impact_method: raw.task_impact_method || "Official O*NET task statements are routed through a visible keyword taxonomy for human-led, AI-augmented, and routine-exposure examples.",
    known_limitations: raw.known_limitations || raw.validation?.known_limitations || [],
    sensitivity_presets: raw.sensitivity_presets || {},
  };
}

function normalizeQualityPayload(raw = {}) {
  return {
    ...raw,
    vintage_alignment: { ...(raw.vintage_alignment || {}), summary: raw.vintage_alignment?.summary || raw.vintage_alignment?.message },
  };
}

function normalizeDiagnosticPayload(raw = {}) {
  return {
    ...raw,
    passed: raw.passed ?? (raw.status === "pass" || raw.status === "passed"),
    routing_regression: (raw.routing_regression || raw.routing || []).map((item) => ({ ...item, expected: item.expected || item.expected_intent, actual: item.actual || item.intent })),
  };
}

function normalizeJudgePayload(raw = {}) {
  return {
    ...raw,
    interpretation: normalizeInterpretationPayload(raw.interpretation || raw.path?.interpreted_request || {}),
    path_builder: normalizePathPayload(raw.path_builder || raw.path || {}),
    comparison: normalizeComparePayload(raw.comparison || {}),
    verified_answer: normalizeAskPayload(raw.verified_answer || {}),
    safe_refusal: normalizeAskPayload(raw.safe_refusal || raw.refusal || {}),
  };
}

function getStoredProfile() {
  const last = state.lastPath?.interpretation?.normalized_profile;
  return last || state.home?.profile || {
    interests: ["Electronics", "Programming", "Law"], skills: ["Python", "Arduino", "Writing"],
    education_max: "Bachelor's degree", preferred_state: "Maryland", salary_goal: 90000,
  };
}

function switchWorkspace(name, { scroll = true } = {}) {
  const target = $(`#workspace-${name}`);
  if (!target) return;
  state.activeWorkspace = name;
  $$(".workspace").forEach((workspace) => workspace.classList.remove("active"));
  target.classList.add("active");
  $$(".nav-item[data-workspace]").forEach((button) => button.classList.toggle("active", button.dataset.workspace === name));
  $("#workspaceAnnouncer").textContent = `${WORKSPACE_TITLES[name] || name} opened`;
  $(".sidebar").classList.remove("open");
  if (scroll) scrollToTop();
  if (name === "trust") loadTrustTab("sources");
  if (name === "saved") renderSavedWorkspace();
  if (name === "universe" && state.universe) renderUniverseRoot();
}

function renderWeightControls(containerId, weights, onChange) {
  const container = $(`#${containerId}`);
  if (!container) return;
  container.innerHTML = Object.entries(WEIGHT_META).map(([key, meta]) => `
    <label class="weight-control">
      <span class="weight-head"><span>${escapeHTML(meta.label)}</span><strong data-weight-output="${key}">${Number(weights[key] || 0).toFixed(0)}%</strong></span>
      <input type="range" min="0" max="50" step="1" value="${Number(weights[key] || 0)}" data-weight-key="${key}" aria-label="${escapeHTML(meta.label)} weight">
      <small>${escapeHTML(meta.hint)}</small>
    </label>`).join("");
  container.oninput = (event) => {
    const input = event.target.closest("[data-weight-key]");
    if (!input) return;
    const key = input.dataset.weightKey;
    weights[key] = Number(input.value);
    const output = container.querySelector(`[data-weight-output="${key}"]`);
    if (output) output.textContent = `${input.value}%`;
    onChange?.(weights);
  };
}

function renderInterestChips() {
  const interests = state.bootstrap?.interests || ["Electronics", "Programming", "Writing", "Public Speaking", "Law", "Politics", "Helping People", "Science", "Business", "Creative Work", "Hands-on Work", "Math", "Research", "Building Things"];
  const container = $("#interestChips");
  if (!container) return;
  container.innerHTML = interests.map((interest) => `<button type="button" class="choice-chip ${state.selectedInterests.has(interest) ? "selected" : ""}" data-interest="${escapeHTML(interest)}">${escapeHTML(interest)}</button>`).join("");
}

function renderSkillTags() {
  const container = $("#skillTags");
  if (!container) return;
  container.innerHTML = state.skills.map((skill, index) => `<span class="tag">${escapeHTML(skill)}<button type="button" data-remove-skill="${index}" aria-label="Remove ${escapeHTML(skill)}">×</button></span>`).join("");
}

function addSkill(value) {
  const skill = String(value || "").trim();
  if (!skill) return;
  if (!state.skills.some((item) => item.toLowerCase() === skill.toLowerCase())) state.skills.push(skill);
  renderSkillTags();
  $("#skillInput").value = "";
}

function bindNavigation() {
  document.addEventListener("click", (event) => {
    const nav = event.target.closest("[data-workspace]");
    if (nav) switchWorkspace(nav.dataset.workspace);
    const jump = event.target.closest("[data-workspace-jump]");
    if (jump) switchWorkspace(jump.dataset.workspaceJump);
    const methodology = event.target.closest("[data-open-methodology]");
    if (methodology) openMethodology();
    const diagnostic = event.target.closest("[data-run-diagnostic]");
    if (diagnostic) {
      switchWorkspace("trust");
      activateTrustTab("diagnostic");
      runDiagnostic();
    }
  });
  $("#mobileMenu").addEventListener("click", () => $(".sidebar").classList.toggle("open"));
}

function bindGlobalSearch() {
  const input = $("#globalSearch");
  const menu = $("#globalSearchResults");
  const run = debounce(async () => {
    const query = input.value.trim();
    if (query.length < 2) { menu.classList.remove("open"); menu.innerHTML = ""; return; }
    try {
      const data = await api(`/api/occupations?query=${encodeURIComponent(query)}&limit=8`);
      menu.innerHTML = (data.results || []).map((item) => `<button type="button" class="autocomplete-option" data-global-soc="${item.soc_code}"><strong>${escapeHTML(item.occupation_title)}</strong><small>${escapeHTML(item.category)} · ${money(item.median_wage, true)} median · ${escapeHTML(item.resilience_label || "Resilience calculated on open")}</small></button>`).join("") || `<div class="autocomplete-option"><strong>No matching occupation</strong><small>Press Enter to ask CareerProof instead.</small></div>`;
      menu.classList.add("open");
    } catch (error) { console.error(error); }
  }, 220);
  input.addEventListener("input", run);
  input.addEventListener("focus", run);
  menu.addEventListener("click", (event) => {
    const option = event.target.closest("[data-global-soc]");
    if (!option) return;
    input.value = "";
    menu.classList.remove("open");
    openOccupation(option.dataset.globalSoc);
  });
  $("#globalSearchForm").addEventListener("submit", (event) => {
    event.preventDefault();
    const visible = menu.querySelector("[data-global-soc]");
    if (visible) { visible.click(); return; }
    const question = input.value.trim();
    if (!question) return;
    $("#questionInput").value = question;
    input.value = "";
    menu.classList.remove("open");
    switchWorkspace("ask");
    runQuestion(question);
  });
  document.addEventListener("keydown", (event) => {
    if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
      event.preventDefault(); input.focus(); input.select();
    }
    if (event.key === "Escape") {
      menu.classList.remove("open");
      closeAllOverlays();
    }
  });
  document.addEventListener("click", (event) => {
    if (!event.target.closest("#globalSearchForm")) menu.classList.remove("open");
  });
}

async function searchOccupations(query, limit = 10) {
  if (!String(query || "").trim()) return [];
  const data = await api(`/api/occupations?query=${encodeURIComponent(query.trim())}&limit=${limit}`);
  return data.results || [];
}

function attachCareerAutocomplete(input, onSelect) {
  const menu = input.parentElement.querySelector(".autocomplete-menu");
  const run = debounce(async () => {
    const query = input.value.trim();
    if (query.length < 2) { menu?.classList.remove("open"); return; }
    try {
      const results = await searchOccupations(query, 9);
      if (!menu) return;
      menu.innerHTML = results.map((item) => `<button type="button" class="autocomplete-option" data-soc="${item.soc_code}" data-title="${escapeHTML(item.occupation_title)}"><strong>${escapeHTML(item.occupation_title)}</strong><small>${escapeHTML(item.category)} · ${money(item.median_wage, true)} · ${pct(item.growth_percent)}</small></button>`).join("") || `<div class="autocomplete-option"><small>No matching occupation.</small></div>`;
      menu.classList.add("open");
    } catch (error) { console.error(error); }
  }, 220);
  input.addEventListener("input", () => { input.dataset.soc = ""; run(); });
  input.addEventListener("focus", run);
  menu?.addEventListener("click", (event) => {
    const option = event.target.closest("[data-soc]");
    if (!option) return;
    input.value = option.dataset.title;
    input.dataset.soc = option.dataset.soc;
    menu.classList.remove("open");
    onSelect?.({ soc_code: option.dataset.soc, occupation_title: option.dataset.title });
  });
  input.addEventListener("blur", () => setTimeout(() => menu?.classList.remove("open"), 150));
}

function fillStateSelects(states) {
  ["pathState", "compareState"].forEach((id) => {
    const select = $(`#${id}`);
    if (!select) return;
    const first = select.querySelector("option");
    select.innerHTML = first ? first.outerHTML : `<option value="">Any state</option>`;
    states.forEach((stateName) => select.insertAdjacentHTML("beforeend", `<option value="${escapeHTML(stateName)}">${escapeHTML(stateName)}</option>`));
  });
  $("#pathState").value = "Maryland";
  $("#compareState").value = "Maryland";
}

function renderStats() {
  const stats = state.bootstrap?.stats || {};
  const items = [
    ["▣", `${formatNumber(stats.occupations || 0)}+`, "Occupations", "analyzed"],
    ["⌂", `${compactNumber(stats.state_occupation_records || 0, 0)}+`, "Geographic records", "BLS state estimates"],
    ["◇", `${compactNumber(stats.degree_relationships || 0, 1)}+`, "Degree & career", "official relationships"],
    ["✓", `${formatNumber(stats.source_families || 0)}`, "Official data", "source families"],
    ["◎", "Every", "Recommendation", "has inspectable evidence"],
  ];
  $("#statsGrid").innerHTML = items.map(([icon, value, label, detail]) => `<div class="stat-card"><span class="stat-icon">${icon}</span><strong>${escapeHTML(value)}</strong><small>${escapeHTML(label)}<em>${escapeHTML(detail)}</em></small></div>`).join("");
}

function renderSnapshot(profile = getStoredProfile()) {
  const interests = profile.interests?.length ? profile.interests : [...state.selectedInterests];
  const skills = profile.skills || state.skills;
  const html = `
    <div class="snapshot-list">
      <div class="snapshot-item"><span>✧</span><div><small>Interests</small><strong>${escapeHTML(interests.slice(0, 4).join(", ") || "Not set")}</strong></div></div>
      <div class="snapshot-item"><span>◇</span><div><small>Education goal</small><strong>${escapeHTML(profile.education_max || "No limit")}</strong></div></div>
      <div class="snapshot-item"><span>⌖</span><div><small>Location</small><strong>${escapeHTML(profile.preferred_state || "Any state")}</strong></div></div>
      <div class="snapshot-item"><span>$</span><div><small>Salary target</small><strong>${profile.salary_goal ? `${money(profile.salary_goal)}+` : "No minimum"}</strong></div></div>
      <div class="snapshot-item"><span>⚙</span><div><small>Existing skills</small><strong>${escapeHTML((skills || []).slice(0, 4).join(", ") || "Not set")}</strong></div></div>
    </div><button class="snapshot-update" data-workspace-jump="path">✎ Update preferences</button>`;
  const container = $("#homeSnapshot");
  container.querySelectorAll(".snapshot-list,.snapshot-update,.snapshot-loading").forEach((element) => element.remove());
  container.insertAdjacentHTML("beforeend", html);
}

function cacheCareer(item) {
  if (!item?.soc_code) return;
  state.occupationCache.set(String(item.soc_code), item);
}

function renderHome() {
  if (!state.home) return;
  renderSnapshot(state.home.profile);
  renderHomeMatches(state.home.path?.results || []);
  renderHomeImpact(state.home.path?.results?.[0]);
  renderHomeOpportunities(state.home.path?.results || []);
  renderHomeFreshness(state.home.freshness);
  renderHomeUniversePreview();
}

function renderHomeMatches(results) {
  results.forEach(cacheCareer);
  $("#homeMatches").innerHTML = results.slice(0, 4).map((item, index) => `
    <article class="home-match-row" data-open-soc="${item.soc_code}" tabindex="0">
      <span class="match-rank">${index + 1}</span>
      <div class="home-match-title"><h3>${escapeHTML(item.occupation_title)}</h3><div class="match-badges"><span class="match-badge">${escapeHTML(item.resilience_label)}</span><span class="match-badge">${escapeHTML(item.feasibility?.status === "passes" ? "Feasible" : "Tradeoff")}</span></div><p>${escapeHTML(item.description || "Official occupation profile")}</p></div>
      <div class="match-metric"><strong>${money(item.median_wage, true)}</strong><small>Median wage</small></div>
      <div class="match-metric"><strong>${pct(item.growth_percent)}</strong><small>Growth</small></div>
      <button class="bookmark-button" data-save-soc="${item.soc_code}" aria-label="Save ${escapeHTML(item.occupation_title)}">☆</button>
    </article>`).join("");
}

function renderHomeImpact(item) {
  const impact = item?.resilience_profile?.ai_task_impact || {};
  const augmented = impact.ai_augmented?.count || 0;
  const human = impact.human_led?.count || 0;
  const reduced = impact.routine_reduced?.count || 0;
  const total = Math.max(augmented + human + reduced, 1);
  const augPct = Math.round(augmented / total * 100);
  const humanPct = Math.round(human / total * 100);
  const reducedPct = Math.max(0, 100 - augPct - humanPct);
  const transformedEnd = augPct + humanPct;
  $("#homeImpact").innerHTML = `
    <div class="impact-donut" style="--augmented:${augPct}%;--transformed:${transformedEnd}%;--automatable:100%"><div><span><strong>${item ? Math.round(item.resilience_score) : "—"}</strong><small>resilience</small></span></div></div>
    <div class="impact-legend">
      <div><i style="background:#338cff"></i><span>Tasks AI may augment</span><strong>${augPct}%</strong></div>
      <div><i style="background:#8952e5"></i><span>Tasks likely human-led</span><strong>${humanPct}%</strong></div>
      <div><i style="background:#ef637c"></i><span>Routine exposure signals</span><strong>${reducedPct}%</strong></div>
    </div>
    <p class="impact-note">Task categories are keyword-based explanations of published O*NET task statements. They are not forecasts of job loss.</p>`;
}

function renderHomeOpportunities(results) {
  const rows = results.filter((item) => item.state_match).slice(0, 4);
  $("#homeOpportunities").innerHTML = rows.map((item) => `
    <button class="opportunity-row" data-open-soc="${item.soc_code}">
      <span>⌖</span><strong>${escapeHTML(item.occupation_title)}</strong>
      <small>${money(item.state_match?.median_wage, true)} · ${compactNumber(item.state_match?.employment, 1)} workers</small>
      <b class="confidence-chip">${escapeHTML(item.decision_confidence?.label || "Published")}</b>
    </button>`).join("") || `<p class="muted-copy">No state rows were published for the selected profile's top results.</p>`;
}

function renderHomeFreshness(freshness) {
  if (!freshness) return;
  $("#homeFreshness").innerHTML = `<span>◷</span><div><strong>Different source years are visible, not silently blended.</strong> ${escapeHTML(freshness.summary || "")}</div><button data-workspace-jump="trust">Inspect vintages →</button>`;
}

function renderHomeUniversePreview() {
  if (!state.universe) return;
  const svg = $("#homeUniverseSvg");
  svg.innerHTML = "";
  const categories = state.universe.categories || [];
  const points = categories.map((category, index) => ({
    x: 70 + (index % 4) * 185 + (index % 2) * 25,
    y: 45 + Math.floor(index / 4) * 100 + (index % 3) * 12,
    color: category.color || "#627cff",
    category,
  }));
  for (let i = 0; i < points.length; i++) {
    for (let j = i + 1; j < points.length; j++) {
      if ((i + j) % 3 === 0 || Math.abs(points[i].x - points[j].x) < 210) {
        const line = document.createElementNS(SVG_NS, "line");
        line.setAttribute("x1", points[i].x); line.setAttribute("y1", points[i].y);
        line.setAttribute("x2", points[j].x); line.setAttribute("y2", points[j].y);
        line.setAttribute("stroke", "#334f8d"); line.setAttribute("stroke-opacity", ".35"); line.setAttribute("stroke-width", ".8");
        svg.appendChild(line);
      }
    }
  }
  points.forEach((point, index) => {
    const circle = document.createElementNS(SVG_NS, "circle");
    circle.setAttribute("cx", point.x); circle.setAttribute("cy", point.y); circle.setAttribute("r", 4 + (point.category.size || 1) / 80);
    circle.setAttribute("fill", point.color); circle.setAttribute("opacity", ".92");
    circle.style.filter = `drop-shadow(0 0 7px ${point.color})`;
    svg.appendChild(circle);
    for (let n = 0; n < 3; n++) {
      const satellite = document.createElementNS(SVG_NS, "circle");
      satellite.setAttribute("cx", point.x + Math.cos(n * 2.1 + index) * (18 + n * 6));
      satellite.setAttribute("cy", point.y + Math.sin(n * 2.1 + index) * (14 + n * 5));
      satellite.setAttribute("r", 1.7); satellite.setAttribute("fill", point.color); satellite.setAttribute("opacity", ".7");
      svg.appendChild(satellite);
    }
  });
}

function universeNode(svg, { x, y, radius, color, label, sublabel, data, className = "" }) {
  const group = document.createElementNS(SVG_NS, "g");
  group.setAttribute("class", `universe-node ${className}`);
  group.setAttribute("transform", `translate(${x} ${y})`);
  group.setAttribute("tabindex", "0");
  group.style.cursor = "pointer";
  if (data) Object.entries(data).forEach(([key, value]) => { group.dataset[key] = value; });
  const outer = document.createElementNS(SVG_NS, "circle");
  outer.setAttribute("r", radius + 8); outer.setAttribute("fill", color); outer.setAttribute("opacity", ".08");
  const circle = document.createElementNS(SVG_NS, "circle");
  circle.setAttribute("r", radius); circle.setAttribute("fill", "#0c1627"); circle.setAttribute("stroke", color); circle.setAttribute("stroke-width", "2");
  circle.style.filter = `drop-shadow(0 0 12px ${color}77)`;
  const text = document.createElementNS(SVG_NS, "text");
  text.setAttribute("text-anchor", "middle"); text.setAttribute("y", "2"); text.setAttribute("fill", "#f2f5ff"); text.setAttribute("font-size", radius > 40 ? "14" : "11.5"); text.setAttribute("font-weight", "700");
  label.split(" ").slice(0, 3).forEach((word, index) => {
    const tspan = document.createElementNS(SVG_NS, "tspan"); tspan.setAttribute("x", "0"); tspan.setAttribute("dy", index === 0 ? `${-(Math.min(label.split(" ").length, 3) - 1) * 6}` : "12"); tspan.textContent = word; text.appendChild(tspan);
  });
  group.append(outer, circle, text);
  if (sublabel) {
    const sub = document.createElementNS(SVG_NS, "text");
    sub.setAttribute("text-anchor", "middle"); sub.setAttribute("y", radius + 20); sub.setAttribute("fill", "#6f7f9c"); sub.setAttribute("font-size", "11.5"); sub.textContent = sublabel;
    group.appendChild(sub);
  }
  svg.appendChild(group);
  return group;
}

function clearUniverse() {
  const svg = $("#universeSvg");
  svg.innerHTML = "";
  $("#universeLoading").classList.add("hidden");
}

function renderUniverseRoot() {
  if (!state.universe) return;
  state.universeCategory = null;
  state.universeCategoryData = null;
  $("#universeBack").disabled = true;
  clearUniverse();
  const svg = $("#universeSvg");
  const center = { x: 480, y: 320 };
  const categories = state.universe.categories || [];
  categories.forEach((category, index) => {
    const angle = -Math.PI / 2 + index * (Math.PI * 2 / categories.length);
    const x = center.x + Math.cos(angle) * 270;
    const y = center.y + Math.sin(angle) * 215;
    const line = document.createElementNS(SVG_NS, "line");
    line.setAttribute("x1", center.x); line.setAttribute("y1", center.y); line.setAttribute("x2", x); line.setAttribute("y2", y);
    line.setAttribute("stroke", category.color || "#5772ff"); line.setAttribute("stroke-opacity", ".26"); line.setAttribute("stroke-width", "1.2");
    svg.appendChild(line);
    const node = universeNode(svg, { x, y, radius: 39, color: category.color || "#5772ff", label: category.name, sublabel: `${category.size} careers`, data: { category: category.name } });
    node.addEventListener("click", () => openUniverseCategory(category.name));
    node.addEventListener("keydown", (event) => { if (event.key === "Enter" || event.key === " ") openUniverseCategory(category.name); });
  });
  universeNode(svg, { x: center.x, y: center.y, radius: 68, color: "#7062ff", label: "Career Universe", sublabel: `${state.universe.occupation_count || 830} official occupations` });
  $("#universeDetail").innerHTML = `<div class="detail-empty"><div class="detail-orb">◎</div><h3>Choose a field</h3><p>Each category is a CareerProof interpretation of official work-content signals. Open one to see the exact occupations.</p><small>The category is derived. Salary, outlook, skills, and education values remain official.</small></div>`;
}

async function openUniverseCategory(categoryName) {
  $("#universeLoading").classList.remove("hidden");
  try {
    const raw = await api(`/api/universe?category=${encodeURIComponent(categoryName)}&limit=12`);
    const data = normalizeUniverseCategoryPayload(raw);
    state.universeCategory = categoryName;
    state.universeCategoryData = data;
    $("#universeBack").disabled = false;
    renderUniverseCategory(data);
  } catch (error) { showToast(error.message); }
  finally { $("#universeLoading").classList.add("hidden"); }
}

function renderUniverseCategory(data, filters = {}) {
  clearUniverse();
  const svg = $("#universeSvg");
  let occupations = data.occupations || [];
  const minSalary = Number(filters.salary || 0);
  const education = filters.education || "";
  const resilience = Number(filters.resilience || 0);
  occupations = occupations.filter((item) => (!minSalary || Number(item.median_wage || 0) >= minSalary) && (!education || item.education === education) && (!resilience || Number(item.resilience_score || 0) >= resilience));
  const displayed = occupations.slice(0, 18);
  const center = { x: 480, y: 320 };
  displayed.forEach((item, index) => {
    const angle = -Math.PI / 2 + index * (Math.PI * 2 / Math.max(displayed.length, 1));
    const ring = index % 2 === 0 ? 250 : 190;
    const x = center.x + Math.cos(angle) * ring;
    const y = center.y + Math.sin(angle) * (ring * .78);
    const line = document.createElementNS(SVG_NS, "line");
    line.setAttribute("x1", center.x); line.setAttribute("y1", center.y); line.setAttribute("x2", x); line.setAttribute("y2", y);
    line.setAttribute("stroke", data.color || "#5878ff"); line.setAttribute("stroke-opacity", ".22");
    svg.appendChild(line);
    const node = universeNode(svg, { x, y, radius: 25, color: data.color || "#5878ff", label: item.occupation_title, sublabel: money(item.median_wage, true), data: { soc: item.soc_code } });
    node.addEventListener("click", () => showUniverseOccupation(item.soc_code));
  });
  universeNode(svg, { x: center.x, y: center.y, radius: 60, color: data.color || "#6e65ff", label: data.name, sublabel: `${occupations.length} match filters` });
  const educationOptions = [...new Set((data.occupations || []).map((item) => item.education).filter(Boolean))].sort();
  $("#universeDetail").innerHTML = `
    <div class="universe-filter-panel">
      <span class="section-kicker">Functional filters</span><h3>${escapeHTML(data.name)}</h3>
      <p>${escapeHTML(data.description || "CareerProof human-advantage category")}</p>
      <label>Minimum median wage<input id="universeSalaryFilter" type="number" step="10000" value="${minSalary || ""}" placeholder="90000"></label>
      <label>Maximum education<select id="universeEducationFilter"><option value="">Any education</option>${educationOptions.map((value) => `<option ${value === education ? "selected" : ""}>${escapeHTML(value)}</option>`).join("")}</select></label>
      <label>Minimum resilience<select id="universeResilienceFilter"><option value="0">Any profile</option><option value="55" ${resilience === 55 ? "selected" : ""}>Moderate+</option><option value="70" ${resilience === 70 ? "selected" : ""}>Strong+</option><option value="82" ${resilience === 82 ? "selected" : ""}>Very strong</option></select></label>
      <div class="universe-filter-count"><strong>${occupations.length}</strong><small>careers match</small></div>
    </div>
    <div class="universe-list">${occupations.slice(0, 10).map((item) => `<button data-universe-soc="${item.soc_code}"><span>${escapeHTML(item.occupation_title)}</span><small>${money(item.median_wage, true)} · ${pct(item.growth_percent)} growth · ${escapeHTML(item.resilience_label)}</small></button>`).join("")}</div>
    <p class="universe-boundary">Connection shown: membership in a documented CareerProof category. It does not imply a hiring pathway or causal relationship.</p>`;
  const applyFilters = debounce(() => renderUniverseCategory(data, {
    salary: $("#universeSalaryFilter")?.value,
    education: $("#universeEducationFilter")?.value,
    resilience: $("#universeResilienceFilter")?.value,
  }), 180);
  $("#universeSalaryFilter")?.addEventListener("input", applyFilters);
  $("#universeEducationFilter")?.addEventListener("change", applyFilters);
  $("#universeResilienceFilter")?.addEventListener("change", applyFilters);
  $$("[data-universe-soc]", $("#universeDetail")).forEach((button) => button.addEventListener("click", () => showUniverseOccupation(button.dataset.universeSoc)));
}

async function showUniverseOccupation(socCode) {
  $("#universeDetail").innerHTML = `<div class="loading-card"><span class="spinner"></span><p>Joining official evidence by SOC code…</p></div>`;
  try {
    const data = normalizeOccupationPayload(await api(`/api/occupation/${encodeURIComponent(socCode)}`));
    cacheCareer(data.profile);
    const p = data.profile;
    $("#universeDetail").innerHTML = `
      <span class="section-kicker">Official SOC ${escapeHTML(p.soc_code)}</span>
      <h2>${escapeHTML(p.occupation_title)}</h2><p>${escapeHTML(p.description || "")}</p>
      <div class="detail-kpis"><div><small>Median wage</small><strong>${money(p.median_wage)}</strong></div><div><small>Growth</small><strong>${pct(p.growth_percent)}</strong></div><div><small>Openings</small><strong>${compactNumber(p.annual_openings)}</strong></div><div><small>Resilience</small><strong>${escapeHTML(p.resilience_label)} · ${p.resilience_score}</strong></div></div>
      <div class="detail-reason"><strong>Why this category</strong><p>${escapeHTML(data.category_reason || "CareerProof mapped published work-content signals to this human-advantage category.")}</p></div>
      <div class="detail-actions"><button class="primary-button" data-open-soc="${p.soc_code}">Open full profile</button><button class="outline-button" data-tray-soc="${p.soc_code}">Add to compare</button><button class="outline-button" data-save-soc="${p.soc_code}">Save</button></div>
      <button class="soft-button" id="backToUniverseCategory">← Back to ${escapeHTML(state.universeCategory)}</button>`;
    $("#backToUniverseCategory").addEventListener("click", () => renderUniverseCategory(state.universeCategoryData));
  } catch (error) { $("#universeDetail").innerHTML = `<div class="error-card">${escapeHTML(error.message)}</div>`; }
}

function pathPayload() {
  return {
    profile_text: $("#profileText").value.trim(),
    interests: [...state.selectedInterests],
    skills: [...state.skills],
    education_max: $("#pathEducation").value || null,
    preferred_state: $("#pathState").value || null,
    salary_goal: Number($("#pathSalary").value || 0) || null,
    work_environment: [...state.workEnvironment],
    remote_preference: $("#pathRemote").value,
    willing_to_relocate: $("#willingRelocate").checked,
    salary_is_hard: $("#hardSalary").checked,
    education_is_hard: $("#hardEducation").checked,
    location_is_hard: $("#hardLocation").checked,
    weights: normalizeWeights(state.pathWeights),
  };
}

function renderInterpretation(data) {
  state.lastInterpretation = data;
  const priorities = data.priorities || [];
  const constraints = data.constraints || [];
  $("#pathInterpretation").classList.remove("hidden");
  $("#pathInterpretation").innerHTML = `
    <article class="interpretation-card">
      <header><div><span class="section-kicker">AI interpretation · review required</span><h2>${escapeHTML(data.goal)}</h2><p>${escapeHTML(data.interpretation_summary)}</p></div><span class="interpretation-status">Ready for human review</span></header>
      <div class="interpretation-grid">
        <section class="interpretation-section"><h3>Constraints</h3>${constraints.map((item) => `<p><strong>${escapeHTML(item.label)}:</strong> ${escapeHTML(item.value)} ${item.hard ? '<span class="feasibility-chip blocked">Hard</span>' : ""}</p>`).join("")}</section>
        <section class="interpretation-section"><h3>Detected interests</h3><div class="interpretation-chip-list">${(data.interests || []).map((item) => `<span>${escapeHTML(item)}</span>`).join("") || "<span>None detected</span>"}</div><h3 style="margin-top:12px">Existing skills</h3><div class="interpretation-chip-list">${(data.skills || []).map((item) => `<span>${escapeHTML(item)}</span>`).join("") || "<span>None listed</span>"}</div></section>
        <section class="interpretation-section"><h3>Priorities</h3>${priorities.map((item) => `<div class="priority-row"><span>${escapeHTML(item.label)}</span><b>${item.weight}%</b></div>`).join("")}</section>
        <section class="interpretation-section"><h3>Work preferences</h3><p><strong>Environment:</strong> ${escapeHTML((data.work_environment || []).join(", ") || "No preference")}</p><p><strong>Remote:</strong> ${escapeHTML(data.remote_preference || "Not specified")}</p><p><strong>Relocation:</strong> ${data.willing_to_relocate ? "Willing" : "Not currently willing"}</p></section>
      </div>
      ${(data.warnings || []).map((warning) => `<div class="warning-line">${escapeHTML(warning)}</div>`).join("")}
      <div class="interpretation-actions"><button id="editInterpretation" class="outline-button">Edit inputs</button><button id="confirmInterpretation" class="primary-button"><span>Confirm and calculate</span><b>→</b></button></div>
    </article>`;
  $$('[data-builder-step]').forEach((step) => { step.classList.toggle("active", step.dataset.builderStep === "2"); step.classList.toggle("complete", step.dataset.builderStep === "1"); });
  $("#editInterpretation").addEventListener("click", () => { $("#profileText").focus(); $("#pathInterpretation").scrollIntoView({ behavior: "smooth", block: "start" }); showToast("Edit the form, then review the interpretation again."); });
  $("#confirmInterpretation").addEventListener("click", runPathBuilder);
  $("#pathInterpretation").scrollIntoView({ behavior: "smooth", block: "start" });
}

async function reviewPathInterpretation() {
  const button = $("#pathForm button[type=submit]");
  setButtonLoading(button, true, "Interpreting your goal…");
  try {
    const data = normalizeInterpretationPayload(await api("/api/interpret-profile", { method: "POST", body: JSON.stringify(pathPayload()) }));
    renderInterpretation(data);
  } catch (error) { showToast(error.message); }
  finally { setButtonLoading(button, false); }
}

async function runPathBuilder() {
  const button = $("#confirmInterpretation");
  setButtonLoading(button, true, "Calculating verified paths…");
  $("#pathResults").innerHTML = `<div class="empty-intelligence"><span class="spinner"></span><h2>Applying hard constraints and transparent weights</h2><p>CareerProof is ranking 830 occupations, then enriching only the visible evidence cards.</p></div>`;
  try {
    const payload = { ...pathPayload(), confirmed_interpretation: true, limit: 8 };
    const data = normalizePathPayload(await api("/api/path-builder", { method: "POST", body: JSON.stringify(payload) }));
    state.lastPath = data;
    safeStorage.setItem("careerproof-last-path", JSON.stringify(data));
    renderPathResults(data);
    renderSnapshot(data.interpretation?.normalized_profile || payload);
    $("#sidebarProgressValue").textContent = "100%";
    $("#sidebarProgressBar").style.width = "100%";
    $$('[data-builder-step]').forEach((step) => { step.classList.toggle("active", step.dataset.builderStep === "3"); step.classList.toggle("complete", step.dataset.builderStep !== "3"); });
  } catch (error) {
    $("#pathResults").innerHTML = `<div class="refusal-card"><span class="refusal-badge">Could not calculate</span><h2>CareerProof stopped safely</h2><p>${escapeHTML(error.message)}</p></div>`;
  } finally { setButtonLoading(button, false); }
}

function feasibilityClass(status) {
  if (status === "passes") return "passes";
  if (status === "blocked") return "blocked";
  return "tradeoff";
}

function contributionRows(item) {
  return Object.entries(item.contributions || {}).map(([key, value]) => `
    <div class="component-bar"><span>${escapeHTML(WEIGHT_META[key]?.label || titleCase(key))}</span><i class="component-track"><span style="width:${Math.min(100, Number(item.components?.[key] || 0))}%"></span></i><strong>${Number(value).toFixed(1)}</strong></div>`).join("");
}

function resilienceMini(profile) {
  if (!profile) return "";
  const dimensions = Object.entries(profile.dimensions || {}).slice(0, 6);
  return `<div class="resilience-mini"><div class="resilience-score-block"><strong>${Math.round(profile.overall_score)}</strong><small>${escapeHTML(profile.overall_label)} resilience</small></div><div class="resilience-dimension-list">${dimensions.map(([key, value]) => `<div class="resilience-dimension"><span>${escapeHTML(value.label)}</span><b>${Math.round(value.score)}</b><i style="--value:${Math.round(value.score)}%"></i></div>`).join("")}</div></div>`;
}

function roadmapPreview(roadmap) {
  if (!roadmap) return "";
  const items = [
    ["Learn", roadmap.learn?.[0]], ["Build", roadmap.build?.[0]], ["Prepare", roadmap.prepare?.[0]],
  ].filter(([, item]) => item);
  return `<div class="roadmap-preview"><small>FIRST PRACTICAL MOVES</small>${items.map(([label, item]) => `<div><span>${label[0]}</span><p><strong>${escapeHTML(item.title || label)}</strong><small>${escapeHTML(item.detail || "")}</small></p></div>`).join("")}<em>${escapeHTML(roadmap.boundary || "")}</em></div>`;
}

function challengePanel(item) {
  const challenge = item.challenge || {};
  return `<div class="challenge-panel hidden" data-challenge-panel="${item.soc_code}"><h4>Challenge this recommendation</h4><div class="challenge-grid"><section><h5>Weakest evidence</h5><p>${escapeHTML(challenge.weakest_evidence || "No specific weakness published.")}</p><h5>Missing information</h5><ul>${(challenge.missing_information || []).map((value) => `<li>${escapeHTML(value)}</li>`).join("")}</ul></section><section><h5>Assumptions</h5><ul>${(challenge.assumptions || []).map((value) => `<li>${escapeHTML(value)}</li>`).join("")}</ul><h5>Strongest challenger</h5><p>${escapeHTML(challenge.strongest_challenger ? `${challenge.strongest_challenger.occupation_title}: ${challenge.strongest_challenger.why_it_could_win}` : "No alternate career in the visible result set.")}</p></section></div></div>`;
}

function pathCard(item, index) {
  cacheCareer(item);
  const reasons = item.why || [];
  const profile = item.resilience_profile;
  return `<article class="path-card" style="animation-delay:${index * 55}ms">
    <div class="path-card-top">
      <div class="score-ring" style="--score:${Math.round(item.score)}"><div><strong>${Math.round(item.score)}</strong><small>fit</small></div></div>
      <div><span class="path-type">${escapeHTML(item.path_label || `Match ${index + 1}`)}</span><h3>${escapeHTML(item.occupation_title)}</h3><div class="path-meta"><span>${escapeHTML(item.soc_code)}</span><span>${escapeHTML(item.category)}</span><span>${escapeHTML(item.education || "Education not published")}</span><b class="derived-chip">CP-derived score</b></div></div>
      <span class="feasibility-chip ${feasibilityClass(item.feasibility?.status)}">${escapeHTML(item.feasibility?.status || "review")}</span>
    </div>
    <div class="path-reasons">${reasons.slice(0, 4).map((reason) => `<span>✓ ${escapeHTML(reason)}</span>`).join("")}</div>
    <div class="path-metrics"><div class="path-metric"><small>Median wage</small><strong>${money(item.median_wage)}</strong></div><div class="path-metric"><small>Wage range</small><strong>${money(item.wage_p10, true)}–${money(item.wage_p90, true)}</strong></div><div class="path-metric"><small>Growth</small><strong>${pct(item.growth_percent)}</strong></div><div class="path-metric"><small>Openings</small><strong>${compactNumber(item.annual_openings)}</strong></div><div class="path-metric"><small>${escapeHTML(item.state_match?.state || "State coverage")}</small><strong>${item.state_match ? money(item.state_match.median_wage, true) : `${item.state_coverage || 0} areas`}</strong></div></div>
    ${resilienceMini(profile)}
    <div class="component-bars">${contributionRows(item)}</div>
    ${roadmapPreview(item.roadmap)}
    <div class="path-card-actions"><button class="challenge-button" data-toggle-challenge="${item.soc_code}">Challenge recommendation</button><button data-evidence-soc="${item.soc_code}">Evidence passport</button><button data-tray-soc="${item.soc_code}">Compare</button><button data-save-soc="${item.soc_code}">Save</button><button class="explore" data-open-soc="${item.soc_code}">Full profile →</button></div>
    ${challengePanel(item)}
  </article>`;
}

function renderPathResults(data) {
  const results = data.results || [];
  const top = results[0];
  const portfolio = data.portfolio || {};
  const sensitivity = data.sensitivity || [];
  const whatChanges = data.what_would_change_recommendation || [];
  const groups = data.result_groups || {};
  $("#pathResults").innerHTML = `
    <header class="path-results-head"><span class="section-kicker">Verified recommendation set</span><h2>${escapeHTML(data.headline || "Your strongest evidence-backed paths")}</h2><p>${escapeHTML(data.disclosure || "")}</p><div class="data-vintage-inline"><span>◷</span><div><strong>Data-vintage notice:</strong> ${escapeHTML(data.freshness?.summary || "Source periods differ and are disclosed.")}</div></div></header>
    <div class="path-result-list">${results.map(pathCard).join("")}</div>
    <div class="decision-summary-grid">
      <section class="decision-panel"><span class="section-kicker">Career portfolio</span><h3>Do not bet on only one future</h3><div class="portfolio-grid">${[
        ["Primary path", portfolio.primary_path], ["Safer backup", portfolio.safer_backup], ["High upside", portfolio.high_upside_option], ["Fast entry", portfolio.fast_entry_option],
      ].map(([label, item]) => item ? `<button class="portfolio-item" data-open-soc="${item.soc_code}"><small>${escapeHTML(label)}</small><strong>${escapeHTML(item.occupation_title)}</strong><span>${Math.round(item.score)} fit · ${escapeHTML(item.resilience_label)}</span></button>` : "").join("")}</div><p class="form-disclosure">${escapeHTML(portfolio.boundary || "")}</p></section>
      <section class="decision-panel"><span class="section-kicker">Counterfactual test</span><h3>What wins under different priorities?</h3><div class="sensitivity-list">${sensitivity.map((item) => `<div class="sensitivity-row"><span>${escapeHTML(item.label)}</span><strong>${escapeHTML(item.top_occupation)}</strong><b>${Number(item.top_score).toFixed(1)}</b></div>`).join("")}</div></section>
      <section class="decision-panel"><span class="section-kicker">What would change this?</span><h3>Conditions that move the recommendation</h3><div class="sensitivity-list">${whatChanges.map((item) => `<div class="sensitivity-row"><span>${escapeHTML(item.condition)}</span><strong>${escapeHTML(item.impact)}</strong><b>↗</b></div>`).join("")}</div></section>
      <section class="decision-panel"><span class="section-kicker">Grouped alternatives</span><h3>Different ways to define success</h3><div class="sensitivity-list">${Object.entries(groups).map(([key, items]) => `<div class="sensitivity-row"><span>${escapeHTML(titleCase(key))}</span><strong>${escapeHTML(items?.[0]?.occupation_title || "No published match")}</strong><b>${items?.length || 0}</b></div>`).join("")}</div></section>
    </div>
    ${top ? `<div class="freshness-banner"><span>✦</span><div><strong>Why ${escapeHTML(top.occupation_title)} leads:</strong> ${escapeHTML(data.ranking_explanation?.top_reason || top.why?.[0] || "It best matches the selected priorities.")}</div><button data-toggle-challenge="${top.soc_code}">Challenge it →</button></div>` : ""}`;
  $("#pathResults").scrollIntoView({ behavior: "smooth", block: "start" });
}

function renderCompareSlots() {
  const container = $("#compareSlots");
  container.innerHTML = state.compareValues.map((value, index) => `
    <div class="compare-slot"><span class="slot-number">0${index + 1}</span><label>${index === 0 ? "First career" : index === 1 ? "Second career" : "Optional career"}</label><div class="career-search-wrap"><input data-compare-index="${index}" value="${escapeHTML(value)}" placeholder="Search occupation"><div class="autocomplete-menu"></div></div></div>`).join("");
  $$('[data-compare-index]', container).forEach((input) => attachCareerAutocomplete(input, (item) => {
    const index = Number(input.dataset.compareIndex);
    state.compareValues[index] = item.occupation_title;
    state.compareResolved[index] = item;
  }));
}

function comparePayload() {
  const values = $$('[data-compare-index]').map((input, index) => {
    state.compareValues[index] = input.value.trim();
    return input.value.trim();
  }).filter(Boolean);
  return {
    occupations: values,
    weights: normalizeWeights(state.compareWeights),
    preferred_state: $("#compareState").value || null,
    skills: $("#compareSkills").value.split(",").map((item) => item.trim()).filter(Boolean),
    education_max: $("#compareEducation").value || null,
    salary_goal: Number($("#compareSalary").value || 0) || null,
    salary_is_hard: $("#compareHardSalary").checked,
    education_is_hard: $("#compareHardEducation").checked,
    location_is_hard: $("#compareHardLocation").checked,
  };
}

async function runCompare() {
  const payload = comparePayload();
  if (payload.occupations.length < 2) { showToast("Add at least two careers to compare."); return; }
  const button = $("#runCompare");
  setButtonLoading(button, true, "Calculating tradeoffs…");
  $("#compareResults").innerHTML = `<div class="empty-state card"><span class="spinner"></span><h3>Calculating and verifying</h3><p>Every factual value comes from the bundled official snapshots.</p></div>`;
  try {
    const data = normalizeComparePayload(await api("/api/compare", { method: "POST", body: JSON.stringify(payload) }));
    state.lastCompare = data;
    (data.results || []).forEach(cacheCareer);
    renderCompare(data);
  } catch (error) { $("#compareResults").innerHTML = `<div class="refusal-card"><h2>Comparison stopped</h2><p>${escapeHTML(error.message)}</p></div>`; }
  finally { setButtonLoading(button, false); }
}

function compareCareerCard(item, index) {
  return `<article class="compare-career-card rank-${index + 1}"><div class="compare-rank"><span>Rank ${index + 1}</span><span class="feasibility-chip ${feasibilityClass(item.feasibility?.status)}">${escapeHTML(item.feasibility?.status || "review")}</span></div><h3>${escapeHTML(item.occupation_title)}</h3><div class="compare-score">${Number(item.score).toFixed(1)}<small>/100</small></div><div class="compare-stat-list"><div class="compare-stat"><span>Median wage</span><strong>${money(item.median_wage)}</strong></div><div class="compare-stat"><span>Growth</span><strong>${pct(item.growth_percent)}</strong></div><div class="compare-stat"><span>Annual openings</span><strong>${compactNumber(item.annual_openings)}</strong></div><div class="compare-stat"><span>Education</span><strong>${escapeHTML(item.education || "Not published")}</strong></div><div class="compare-stat"><span>Resilience</span><strong>${escapeHTML(item.resilience_label)} · ${Math.round(item.resilience_score)}</strong></div><div class="compare-stat"><span>State pay</span><strong>${item.state_match ? money(item.state_match.median_wage) : "No selected state row"}</strong></div></div><div class="path-card-actions"><button data-evidence-soc="${item.soc_code}">Evidence</button><button data-open-soc="${item.soc_code}">Profile</button><button data-save-soc="${item.soc_code}">Save</button></div></article>`;
}

function renderCompare(data) {
  const results = data.results || [];
  const winner = results[0];
  const metrics = ["interest_fit", "resilience", "salary", "growth", "openings", "education", "location", "stability"];
  $("#compareResults").innerHTML = `
    <section class="compare-winner"><span class="section-kicker">Calculated result</span><h2>${escapeHTML(data.headline || (winner ? `${winner.occupation_title} ranks first` : "Comparison"))}</h2><p>${escapeHTML(data.disclosure || "")}</p><div class="tradeoff-callout">${escapeHTML(data.tradeoff_summary?.plain_language || "The visible result reflects the selected weights and published values.")}</div></section>
    <div class="compare-card-grid">${results.map(compareCareerCard).join("")}</div>
    <section class="compare-chart card"><h3>Normalized score components</h3>${metrics.map((metric) => `<div class="comparison-row"><strong>${escapeHTML(WEIGHT_META[metric]?.label || titleCase(metric))}</strong><div class="comparison-bars">${results.map((item) => `<div class="comparison-bar"><span>${escapeHTML(item.occupation_title)}</span><i class="track"><span style="width:${Math.min(100, Number(item.components?.[metric] || 0))}%"></span></i><b>${Number(item.components?.[metric] || 0).toFixed(0)}</b></div>`).join("")}</div></div>`).join("")}</section>
    <div class="decision-summary-grid"><section class="decision-panel"><span class="section-kicker">Scenario sensitivity</span><h3>Which career wins when priorities change?</h3><div class="sensitivity-list">${(data.sensitivity || []).map((item) => `<div class="sensitivity-row"><span>${escapeHTML(item.label)}</span><strong>${escapeHTML(item.top_occupation)}</strong><b>${Number(item.top_score).toFixed(1)}</b></div>`).join("")}</div></section><section class="decision-panel"><span class="section-kicker">Evidence boundary</span><h3>What this comparison can and cannot say</h3><div class="evidence-box blue"><small>Verified</small><strong>Wage, employment, projections, skills, degree links, and state estimates</strong><p>Calculated through exact SOC-code joins and explicit formulas.</p></div><div class="evidence-box" style="margin-top:7px"><small>Not guaranteed</small><strong>Personal outcomes, future hiring, or permanent AI safety</strong><p>Those claims are outside the bundled data and are never presented as facts.</p></div></section></div>`;
  $("#compareResults").scrollIntoView({ behavior: "smooth", block: "start" });
}

async function resolveCareerInput(input) {
  if (input.dataset.soc) return { soc_code: input.dataset.soc, occupation_title: input.value.trim() };
  const results = await searchOccupations(input.value.trim(), 1);
  if (!results.length) throw new Error(`No occupation matched “${input.value.trim()}”.`);
  input.dataset.soc = results[0].soc_code;
  input.value = results[0].occupation_title;
  return results[0];
}

async function runBridge() {
  const button = $("#runBridge");
  setButtonLoading(button, true, "Building bridge…");
  try {
    const source = await resolveCareerInput($("#bridgeSource"));
    const target = await resolveCareerInput($("#bridgeTarget"));
    $$(".autocomplete-menu").forEach((menu) => menu.classList.remove("open"));
    document.activeElement?.blur?.();
    const data = normalizeBridgePayload(await api("/api/skill-bridge", { method: "POST", body: JSON.stringify({ source: source.soc_code, target: target.soc_code }) }));
    renderBridge(data);
  } catch (error) { showToast(error.message); }
  finally { setButtonLoading(button, false); }
}

function renderBridge(data) {
  cacheCareer(data.source); cacheCareer(data.target);
  $("#bridgeResults").innerHTML = `<article class="skill-bridge-card card"><header class="bridge-head"><span class="section-kicker">Possible pathway · not a guarantee</span><h2>${escapeHTML(data.headline)}</h2><p>${escapeHTML(data.boundary)}</p></header><div class="bridge-visual"><div class="bridge-career"><small>Starting career</small><h3>${escapeHTML(data.source.occupation_title)}</h3><strong>${money(data.source.median_wage)}</strong><p>${escapeHTML(data.source.education || "Education not published")}</p></div><div class="bridge-center"><div class="overlap-orb" style="--score:${Math.round(data.overall_overlap)}"><div><strong>${Math.round(data.overall_overlap)}%</strong><small>overall overlap</small></div></div></div><div class="bridge-career"><small>Target career</small><h3>${escapeHTML(data.target.occupation_title)}</h3><strong>${money(data.target.median_wage)}</strong><p>${escapeHTML(data.target.education || "Education not published")}</p></div></div><div class="bridge-component-grid"><div><small>Task similarity</small><strong>${Math.round(data.task_similarity)}%</strong></div><div><small>Technology overlap</small><strong>${Math.round(data.technology_overlap)}%</strong></div><div><small>Shared skills</small><strong>${data.shared_skills.length}</strong></div></div><div class="bridge-columns"><section class="skill-panel"><h3>Shared transferable skills</h3>${data.shared_skills.slice(0, 8).map((skill) => `<div class="skill-row"><span>${escapeHTML(skill.skill_name)}</span><strong>${Number(skill.shared_score).toFixed(1)}</strong></div>`).join("") || `<p class="form-disclosure">No exact skill-name overlap was published.</p>`}</section><section class="skill-panel"><h3>Target skill gaps</h3>${data.skill_gaps.slice(0, 8).map((skill) => `<div class="skill-row"><span>${escapeHTML(skill.skill_name)}</span><strong>${Number(skill.target_importance).toFixed(1)}</strong></div>`).join("") || `<p class="form-disclosure">No ranked gap was available.</p>`}</section></div><section class="roadmap-preview" style="margin-top:9px"><small>TRANSITION STEPS</small>${data.pathway.map((step) => `<div><span>${step.step}</span><p><strong>${escapeHTML(step.title)}</strong><small>${escapeHTML(step.detail)}</small></p></div>`).join("")}</section></article>`;
  $("#bridgeResults").scrollIntoView({ behavior: "smooth", block: "start" });
}

function renderQuickQuestions() {
  const questions = state.bootstrap?.quick_questions || [];
  $("#quickQuestions").innerHTML = questions.slice(0, 8).map((question) => `<button class="quick-question" data-quick-question="${escapeHTML(question)}">${escapeHTML(question)}</button>`).join("");
}

async function runQuestion(questionOverride = null) {
  const question = questionOverride || $("#questionInput").value.trim();
  if (!question) { showToast("Enter a question first."); return; }
  $("#questionInput").value = question;
  $("#resultArea").innerHTML = `<div class="loading-card card"><span class="loader-core"></span><h3>Building a controlled query plan</h3><p>Resolving occupation, geography, metric, filters, and the allowed calculation.</p></div>`;
  try {
    const data = normalizeAskPayload(await api("/api/ask", { method: "POST", body: JSON.stringify({ question, dataset: $("#datasetSelect").value }) }));
    renderQuestionResult(data);
  } catch (error) { $("#resultArea").innerHTML = `<div class="refusal-card"><h2>Analysis stopped</h2><p>${escapeHTML(error.message)}</p></div>`; }
}

function renderQuestionResult(data) {
  if (data.status === "refused") {
    $("#resultArea").innerHTML = `<article class="refusal-card"><span class="refusal-badge">Safe refusal</span><h2>${escapeHTML(data.headline)}</h2><p>${escapeHTML(data.explanation)}</p><div class="evidence-box"><small>Why CareerProof refused</small><strong>${escapeHTML(data.refusal_reason || "The bundled data cannot verify the requested conclusion.")}</strong><p>${escapeHTML(data.boundary || "")}</p></div><h3>Supported alternatives</h3><div class="suggestion-list">${(data.suggestions || []).map((question) => `<button data-quick-question="${escapeHTML(question)}">${escapeHTML(question)}</button>`).join("")}</div></article>`;
    return;
  }
  const rows = data.analysis?.rows || [];
  const valueKey = data.analysis?.value_key;
  const max = Math.max(...rows.map((row) => Number(row[valueKey] || 0)), 1);
  const chart = rows.slice(0, 12).map((row) => `<div class="bar-row"><span>${escapeHTML(row.label)}</span><i class="bar-track"><span class="bar-fill" style="width:${Math.max(3, Number(row[valueKey] || 0) / max * 100)}%"></span></i><strong>${escapeHTML(row.display_value)}</strong></div>`).join("");
  const tableHeaders = data.analysis?.table_columns || [];
  const table = rows.length ? `<div class="location-table-wrap"><table class="analysis-table"><thead><tr>${tableHeaders.map((header) => `<th>${escapeHTML(titleCase(header))}</th>`).join("")}</tr></thead><tbody>${rows.slice(0, 25).map((row) => `<tr>${tableHeaders.map((header) => `<td>${escapeHTML(row[header] ?? "—")}</td>`).join("")}</tr>`).join("")}</tbody></table></div>` : "";
  const confidence = data.evidence?.confidence || {};
  const plan = data.query_plan || {};
  $("#resultArea").innerHTML = `<article class="result-card card"><header class="result-top"><div><span class="section-kicker">Verified answer</span><h2>${escapeHTML(data.headline)}</h2><p>${escapeHTML(data.explanation)}</p></div><div class="confidence-stack"><div class="confidence-card"><small>Source confidence</small><strong>${escapeHTML(confidence.label || "Published")}</strong><p>${escapeHTML(confidence.reason || "")}</p></div><div class="confidence-card"><small>Evidence ID</small><strong>${escapeHTML(data.evidence?.evidence_id || "Generated")}</strong><p>${escapeHTML(data.evidence?.generated_at || "")}</p></div></div></header><div class="proof-strip"><div><small>Source</small><strong>${escapeHTML(data.evidence?.source_names?.join(" + ") || "Official snapshot")}</strong></div><div><small>Rows used</small><strong>${formatNumber(data.analysis?.rows_used || rows.length)}</strong></div><div><small>Suppressed / excluded</small><strong>${formatNumber(data.analysis?.suppressed_or_excluded || 0)}</strong></div><div><small>Calculation</small><strong>${escapeHTML(data.analysis?.calculation || "Visible below")}</strong></div></div><div class="result-body"><section class="result-main"><span class="section-kicker">Visible calculation</span><div class="bar-chart">${chart}</div>${table}</section><aside class="evidence-panel"><span class="section-kicker">Structured query plan</span><div class="query-plan"><div class="query-step"><small>Intent</small><strong>${escapeHTML(titleCase(plan.intent || "unknown"))}</strong></div><div class="query-step"><small>Occupation</small><strong>${escapeHTML(plan.occupation_title || "Not required")}</strong></div><div class="query-step"><small>Geography</small><strong>${escapeHTML(plan.geography || "National")}</strong></div><div class="query-step"><small>Metric</small><strong>${escapeHTML(titleCase(plan.metric || "Not specified"))}</strong></div><div class="query-step"><small>Source route</small><strong>${escapeHTML(plan.source_id || data.source_id)}</strong></div></div><button class="primary-button full" data-open-answer-evidence style="margin-top:10px">Open full Evidence Passport</button><h3>Limitations</h3><ul class="limitation-list">${(data.limitations || []).map((item) => `<li>${escapeHTML(item)}</li>`).join("")}</ul></aside></div></article>`;
  $("[data-open-answer-evidence]")?.addEventListener("click", () => openAnswerEvidence(data));
}

function occupationProfileTabs() {
  return ["overview", "resilience", "skills", "tasks", "locations", "degrees", "coverage"];
}

async function openOccupation(socCode) {
  switchWorkspace("occupations");
  const container = $("#occupationProfile");
  container.className = "occupation-profile-placeholder card";
  container.innerHTML = `<div class="loading-card"><span class="spinner"></span><p>Joining official sources by SOC code…</p></div>`;
  try {
    const data = normalizeOccupationPayload(await api(`/api/occupation/${encodeURIComponent(socCode)}`));
    state.lastOccupation = data;
    cacheCareer(data.profile);
    renderOccupation(data);
  } catch (error) { container.innerHTML = `<div class="refusal-card"><h2>Profile unavailable</h2><p>${escapeHTML(error.message)}</p></div>`; }
}

function taskImpactColumn(label, className, data) {
  return `<section class="task-impact-column ${className}"><h4>${escapeHTML(label)} · ${data?.count || 0}</h4>${(data?.tasks || []).slice(0, 8).map((task) => `<div class="task-item">${escapeHTML(task)}</div>`).join("") || `<div class="task-item">No matched task statements in this category.</div>`}</section>`;
}

function renderOccupation(data) {
  const p = data.profile;
  const r = data.resilience_profile;
  const coverage = data.data_coverage || {};
  const locations = data.location_opportunity?.rows || [];
  const tasks = data.tasks || [];
  const skills = data.skills || [];
  const degrees = data.related_degrees || [];
  const container = $("#occupationProfile");
  container.className = "occupation-profile card";
  container.innerHTML = `<header class="occupation-hero"><span class="section-kicker">SOC ${escapeHTML(p.soc_code)} · ${escapeHTML(p.category)}</span><h2>${escapeHTML(p.occupation_title)}</h2><p>${escapeHTML(p.description || "")}</p><div class="occupation-actions"><button class="outline-button" data-evidence-soc="${p.soc_code}">Evidence Passport</button><button class="outline-button" data-tray-soc="${p.soc_code}">Compare</button><button class="primary-button" data-save-soc="${p.soc_code}">Save</button></div></header><div class="occupation-kpis"><div class="occupation-kpi"><small>Median wage</small><strong>${money(p.median_wage)}</strong></div><div class="occupation-kpi"><small>Wage range</small><strong>${money(p.wage_p10, true)}–${money(p.wage_p90, true)}</strong></div><div class="occupation-kpi"><small>Growth</small><strong>${pct(p.growth_percent)}</strong></div><div class="occupation-kpi"><small>Annual openings</small><strong>${compactNumber(p.annual_openings)}</strong></div><div class="occupation-kpi"><small>Typical education</small><strong>${escapeHTML(p.education || "Not published")}</strong></div><div class="occupation-kpi"><small>Resilience</small><strong>${escapeHTML(r.overall_label)} · ${Math.round(r.overall_score)}</strong></div></div><nav class="profile-tabs">${occupationProfileTabs().map((tab, index) => `<button class="${index === 0 ? "active" : ""}" data-profile-tab="${tab}">${escapeHTML(titleCase(tab))}</button>`).join("")}</nav><section class="profile-panel active" data-profile-panel="overview"><div class="profile-two-col"><article class="profile-section"><h3>Career in context</h3><p>${escapeHTML(p.description || "")}</p><div class="evidence-box green"><small>Direct official values</small><strong>BLS wage and projection data · O*NET work content</strong><p>Values are joined by the published SOC occupation code.</p></div></article><article class="profile-section"><h3>Decision confidence</h3><div class="evidence-box blue"><small>Source confidence</small><strong>${escapeHTML(data.source_confidence?.label || "High")} · ${data.source_confidence?.score || 94}/100</strong><p>${escapeHTML(data.source_confidence?.reason || "")}</p></div><div class="evidence-box" style="margin-top:7px"><small>Decision confidence</small><strong>${escapeHTML(data.decision_confidence?.label || "Review")}</strong><p>${escapeHTML(data.decision_confidence?.reason || "")}</p></div></article></div><div class="profile-two-col" style="margin-top:10px"><article class="profile-section"><h3>Most important skills</h3>${skills.slice(0, 6).map((skill) => `<div class="skill-row"><span>${escapeHTML(skill.skill_name)}</span><strong>${Number(skill.importance).toFixed(1)}</strong></div>`).join("")}</article><article class="profile-section"><h3>Data-vintage boundary</h3><p>${escapeHTML(data.data_freshness?.summary || "")}</p><ul class="limitation-list">${(data.limitations || []).map((item) => `<li>${escapeHTML(item)}</li>`).join("")}</ul></article></div></section><section class="profile-panel" data-profile-panel="resilience"><div class="resilience-profile-grid"><div class="resilience-overall"><strong>${Math.round(r.overall_score)}</strong><span>${escapeHTML(r.overall_label)} resilience</span><p>${escapeHTML(r.boundary)}</p></div><div class="resilience-bars">${Object.values(r.dimensions || {}).map((dimension) => `<div class="resilience-row"><span>${escapeHTML(dimension.label)}</span><i style="--value:${Math.round(dimension.score)}%"></i><b>${Math.round(dimension.score)}</b></div>`).join("")}<div class="resilience-row"><span>AI augmentation potential</span><i style="--value:${Math.round(r.ai_augmentation_potential)}%"></i><b>${Math.round(r.ai_augmentation_potential)}</b></div></div></div><div class="task-impact-grid" style="margin-top:11px">${taskImpactColumn("Likely human-led", "human", r.ai_task_impact?.human_led)}${taskImpactColumn("AI may augment", "augment", r.ai_task_impact?.ai_augmented)}${taskImpactColumn("Routine exposure", "reduce", r.ai_task_impact?.routine_reduced)}</div><button class="outline-button" data-open-methodology style="margin-top:10px">Open complete model card</button></section><section class="profile-panel" data-profile-panel="skills"><div class="profile-two-col"><article class="profile-section"><h3>O*NET skills</h3>${skills.map((skill) => `<div class="skill-row"><span>${escapeHTML(skill.skill_name)}</span><strong>${Number(skill.importance).toFixed(1)}</strong></div><div class="skill-meter"><span style="width:${Math.min(100, Number(skill.importance) / 5 * 100)}%"></span></div>`).join("")}</article><article class="profile-section"><h3>Tools and technologies</h3>${(data.technologies || []).slice(0, 25).map((item) => `<div class="task-item"><strong>${escapeHTML(item.commodity_title)}</strong>${item.hot_technology ? ' <span class="match-badge">Hot technology</span>' : ""}</div>`).join("") || `<p>No detailed technology records were published for this occupation.</p>`}</article></div></section><section class="profile-panel" data-profile-panel="tasks"><div class="task-impact-grid">${taskImpactColumn("Likely human-led", "human", r.ai_task_impact?.human_led)}${taskImpactColumn("AI may augment", "augment", r.ai_task_impact?.ai_augmented)}${taskImpactColumn("Routine exposure", "reduce", r.ai_task_impact?.routine_reduced)}</div><article class="profile-section" style="margin-top:10px"><h3>Published O*NET task statements</h3>${tasks.map((task) => `<div class="task-item">${escapeHTML(task.task_description)}</div>`).join("")}</article></section><section class="profile-panel" data-profile-panel="locations"><div class="profile-two-col"><article class="profile-section"><h3>Top purchasing-power locations</h3>${locations.slice(0, 12).map((row) => `<div class="skill-row"><span>${escapeHTML(row.label)}</span><strong>${escapeHTML(row.display_value)}</strong></div>`).join("")}</article><article class="profile-section"><h3>How the location score works</h3><p>${escapeHTML(data.location_opportunity?.formula || "")}</p><div class="evidence-box blue"><small>State data</small><strong>${locations.length} published state estimates ranked</strong><p>Suppressed values remain missing. CareerProof never fills them with invented numbers.</p></div><button class="primary-button" data-location-soc="${p.soc_code}" style="margin-top:10px">Open Location Intelligence</button></article></div></section><section class="profile-panel" data-profile-panel="degrees"><article class="profile-section"><h3>Related instructional programs</h3><p>These are NCES/BLS crosswalk relationships. They do not prove a legal requirement or placement outcome.</p><div class="degree-career-grid">${degrees.map((degree) => `<button class="degree-career-card" data-degree-code="${degree.cip_code}"><small>CIP ${escapeHTML(degree.cip_code)}</small><h3>${escapeHTML(degree.cip_title)}</h3><p>Open official relationship map →</p></button>`).join("") || `<p>No related program rows were published.</p>`}</div></article></section><section class="profile-panel" data-profile-panel="coverage"><div class="profile-two-col"><article class="profile-section"><h3>Data coverage</h3><div class="coverage-meter"><div class="coverage-ring" style="--score:${Math.round(coverage.percent || 0)}"><div><strong>${Math.round(coverage.percent || 0)}%</strong><small>coverage</small></div></div><div class="coverage-components">${Object.entries(coverage.components || {}).map(([key, component]) => `<span>${component.available ? "✓" : "—"} ${escapeHTML(titleCase(key))} · ${escapeHTML(component.year || "No year")}</span>`).join("")}</div></div></article><article class="profile-section"><h3>Source lineage</h3>${(data.source_lineage || []).map((source) => `<div class="task-item"><strong>${escapeHTML(source.dataset)}</strong><br>${escapeHTML(source.value)} · ${escapeHTML(source.year)} · ${source.direct ? "Direct official value" : "Transformed for display"}</div>`).join("")}</article></div></section>`;
}

async function searchDegrees() {
  const query = $("#degreeSearch").value.trim();
  if (!query) return;
  try {
    const data = await api(`/api/degrees?query=${encodeURIComponent(query)}&limit=25`);
    const results = data.results || [];
    $("#degreeResults").innerHTML = results.map((item) => `<button class="degree-result" data-degree-code="${item.cip_code}"><small>CIP ${escapeHTML(item.cip_code)}</small><strong>${escapeHTML(item.cip_title)}</strong><span>${formatNumber(item.related_occupation_count)} related occupations</span></button>`).join("") || `<div class="empty-state card"><p>No degree programs matched.</p></div>`;
  } catch (error) { showToast(error.message); }
}

async function openDegree(cipCode) {
  const container = $("#degreeDetail");
  container.innerHTML = `<div class="loading-card"><span class="spinner"></span><p>Loading official degree relationships…</p></div>`;
  try {
    const data = normalizeDegreePayload(await api(`/api/degree/${encodeURIComponent(cipCode)}`));
    (data.related_careers || []).forEach(cacheCareer);
    container.innerHTML = `<span class="section-kicker">Official CIP ${escapeHTML(data.cip_code)}</span><h2>${escapeHTML(data.cip_title)}</h2><p>${escapeHTML(data.boundary)}</p><div class="evidence-box blue"><small>Broad degree-field earnings</small><strong>${data.field_earnings?.median_earnings ? money(data.field_earnings.median_earnings) : "No direct ACS field estimate mapped"}</strong><p>${escapeHTML(data.field_earnings?.disclosure || "Broad Census fields are shown only when the mapping is supported.")}</p></div><h3>Related occupations</h3><div class="degree-career-grid">${(data.related_careers || []).map((item) => `<article class="degree-career-card"><small>SOC ${escapeHTML(item.soc_code)}</small><h3>${escapeHTML(item.occupation_title)}</h3><strong>${money(item.median_wage)}</strong><p>${pct(item.growth_percent)} growth · ${escapeHTML(item.resilience_label)}</p><button class="soft-button" data-open-soc="${item.soc_code}">Open profile</button></article>`).join("")}</div>`;
  } catch (error) { container.innerHTML = `<div class="refusal-card"><h2>Degree pathway unavailable</h2><p>${escapeHTML(error.message)}</p></div>`; }
}

async function runLocation(socOverride = null) {
  const button = $("#runLocation");
  setButtonLoading(button, true, "Ranking locations…");
  try {
    let career;
    if (socOverride) career = state.occupationCache.get(String(socOverride)) || { soc_code: socOverride };
    else career = await resolveCareerInput($("#locationCareer"));
    $$(".autocomplete-menu").forEach((menu) => menu.classList.remove("open"));
    document.activeElement?.blur?.();
    const data = normalizeLocationPayload(await api(`/api/state-opportunity/${encodeURIComponent(career.soc_code)}?limit=51`));
    renderLocation(data);
  } catch (error) { showToast(error.message); }
  finally { setButtonLoading(button, false); }
}

function renderLocation(data) {
  const rows = data.rows || [];
  const top = rows.slice(0, 3);
  $("#locationResults").innerHTML = `<article class="location-results-card card"><header class="location-summary"><div><span class="section-kicker">Cost-of-living-adjusted opportunity</span><h2>${escapeHTML(data.headline)}</h2><p>${escapeHTML(data.boundary)}</p></div><div class="heading-badge"><span>Formula</span><strong>Inspectable</strong><small>${escapeHTML(data.formula)}</small></div></header><div class="location-top-grid">${top.map((row, index) => `<article class="location-card"><span class="section-kicker">Rank ${index + 1}</span><h3>${escapeHTML(row.label)}</h3><span class="location-score">${Number(row.opportunity_score).toFixed(1)}</span><div class="location-stat"><span>Nominal wage</span><strong>${money(row.nominal_wage)}</strong></div><div class="location-stat"><span>Purchasing power</span><strong>${money(row.purchasing_power_wage)}</strong></div><div class="location-stat"><span>Employment</span><strong>${compactNumber(row.employment)}</strong></div><div class="location-stat"><span>Concentration</span><strong>${Number(row.location_quotient || 0).toFixed(2)}</strong></div><div class="location-stat"><span>Confidence</span><strong>${escapeHTML(row.confidence)}</strong></div></article>`).join("")}</div><div class="location-table-wrap"><table class="location-table"><thead><tr><th>Rank</th><th>State</th><th>Nominal wage</th><th>Purchasing power</th><th>Employment</th><th>Location quotient</th><th>RPP</th><th>Confidence</th><th>Derived score</th></tr></thead><tbody>${rows.map((row, index) => `<tr><td>${index + 1}</td><td>${escapeHTML(row.label)}</td><td>${money(row.nominal_wage)}</td><td>${money(row.purchasing_power_wage)}</td><td>${formatNumber(row.employment)}</td><td>${Number(row.location_quotient || 0).toFixed(2)}</td><td>${Number(row.regional_price_parity || 0).toFixed(1)}</td><td>${escapeHTML(row.confidence)}</td><td>${Number(row.opportunity_score).toFixed(1)}</td></tr>`).join("")}</tbody></table></div><div class="data-vintage-inline"><span>◷</span><div>${escapeHTML(data.freshness?.summary || "Source periods are disclosed.")}</div></div></article>`;
  $("#locationResults").scrollIntoView({ behavior: "smooth", block: "start" });
}

function renderSources() {
  const sources = state.bootstrap?.sources || [];
  $("#sourceCatalog").innerHTML = sources.map((source) => `<article class="source-card"><small>${escapeHTML(source.agency)} · ${escapeHTML(source.publication_date || source.year || "Published snapshot")}</small><h3>${escapeHTML(source.name)}</h3><p>${escapeHTML(source.description)}</p><div class="source-meta"><span>${escapeHTML(source.license || "Public data")}</span><span>${escapeHTML(source.direct ? "Direct official values" : "Official values transformed for display")}</span></div>${source.url ? `<a href="${escapeHTML(source.url)}" target="_blank" rel="noreferrer">Open official source ↗</a>` : ""}</article>`).join("");
}

function renderQuestionLibrary() {
  const catalog = state.bootstrap?.question_catalog || [];
  const grouped = Object.groupBy ? Object.groupBy(catalog, (item) => item.category || "Questions") : catalog.reduce((acc, item) => { (acc[item.category || "Questions"] ||= []).push(item); return acc; }, {});
  $("#questionLibrary").innerHTML = Object.entries(grouped).map(([category, items]) => `<article class="question-group"><h3>${escapeHTML(category)}</h3><p>${items.length} supported examples</p>${items.map((item) => `<button data-quick-question="${escapeHTML(item.question)}">${escapeHTML(item.question)}</button>`).join("")}</article>`).join("");
}

async function loadModelCard() {
  if (state.trustLoaded.model) return;
  const model = normalizeModelPayload(await api("/api/resilience-model"));
  state.modelCard = model;
  renderModelCard(model, $("#modelCard"));
  state.trustLoaded.model = true;
}

function renderModelCard(model, container) {
  container.innerHTML = `<article class="model-overview card"><span class="section-kicker">CareerProof-derived method · version ${escapeHTML(model.version)}</span><h2>${escapeHTML(model.name)}</h2><p>${escapeHTML(model.purpose)}</p><div class="evidence-box blue"><small>Exact formula</small><strong>${escapeHTML(model.formula)}</strong><p>${escapeHTML(model.normalization)}</p></div></article><div class="model-dimension-grid">${(model.dimensions || []).map((dimension) => `<article class="model-dimension-card"><header><h3>${escapeHTML(dimension.label)}</h3><b>${Number(dimension.weight).toFixed(0)}%</b></header><p>${escapeHTML(dimension.description)}</p><div class="keyword-cloud">${(dimension.signals || []).slice(0, 12).map((signal) => `<span>${escapeHTML(signal)}</span>`).join("")}</div></article>`).join("")}</div><div class="profile-two-col"><article class="profile-section"><h3>Missing-data policy</h3><p>${escapeHTML(model.missing_data_policy)}</p><h3>Task-impact method</h3><p>${escapeHTML(model.task_impact_method)}</p></article><article class="profile-section"><h3>Known limitations</h3><ul class="limitation-list">${(model.known_limitations || []).map((item) => `<li>${escapeHTML(item)}</li>`).join("")}</ul></article></div><article class="profile-section"><h3>Sensitivity presets</h3><div class="rubric-grid">${Object.entries(model.sensitivity_presets || {}).map(([key, weights]) => `<div class="rubric-card"><strong>${escapeHTML(titleCase(key))}</strong><p>${Object.entries(weights).map(([name, value]) => `${escapeHTML(titleCase(name))} ${value}%`).join(" · ")}</p></div>`).join("")}</div></article>`;
}

async function loadDataQuality() {
  if (state.trustLoaded.quality) return;
  const data = normalizeQualityPayload(await api("/api/data-quality"));
  $("#dataQuality").innerHTML = `<article class="quality-overview card"><span class="section-kicker">Live bundled-file audit</span><h2>Coverage is measured, not assumed</h2><p>Missing and suppressed values remain missing. CareerProof shows where a result is strong, partial, or limited.</p></article><div class="quality-grid">${(data.checks || []).map((check) => `<article class="quality-card"><h3>${escapeHTML(check.name)}</h3><strong>${Number(check.coverage_percent).toFixed(1)}%</strong><div class="quality-meter"><span style="width:${check.coverage_percent}%"></span></div><p>${formatNumber(check.available)} available · ${formatNumber(check.missing)} missing · ${escapeHTML(check.status)}</p></article>`).join("")}</div><div class="profile-two-col"><article class="profile-section"><h3>State suppression monitor</h3>${Object.entries(data.state_suppression || {}).map(([key, value]) => `<div class="skill-row"><span>${escapeHTML(titleCase(key))}</span><strong>${formatNumber(value)}</strong></div>`).join("")}</article><article class="profile-section"><h3>Quality rules</h3><ul class="limitation-list">${(data.rules || []).map((rule) => `<li>${escapeHTML(rule)}</li>`).join("")}</ul></article></div><div class="data-vintage-inline"><span>◷</span><div><strong>Vintage alignment:</strong> ${escapeHTML(data.vintage_alignment?.summary || "")}</div></div>`;
  state.trustLoaded.quality = true;
}

function activateTrustTab(name) {
  $$("[data-trust-tab]").forEach((button) => button.classList.toggle("active", button.dataset.trustTab === name));
  $$("[data-trust-journey]").forEach((button) => button.classList.toggle("active", button.dataset.trustJourney === name));
  $$(".trust-tab-panel").forEach((panel) => panel.classList.toggle("active", panel.id === `trust-${name}`));
  loadTrustTab(name);
}

async function loadTrustTab(name) {
  try {
    if (name === "model") await loadModelCard();
    if (name === "quality") await loadDataQuality();
    if (name === "diagnostic" && !state.trustLoaded.diagnostic) runDiagnostic();
  } catch (error) { showToast(error.message); }
}

async function runDiagnostic() {
  const container = $("#diagnosticResults");
  container.innerHTML = `<div class="loading-card card"><span class="spinner"></span><p>Running live source, routing, trust, and feasibility checks…</p></div>`;
  try {
    const data = normalizeDiagnosticPayload(await api("/api/diagnostic"));
    state.trustLoaded.diagnostic = true;
    const checks = data.checks || [];
    const routing = data.routing_regression || [];
    const rubric = data.judge_alignment || {};
    container.innerHTML = `<div class="diagnostic-grid"><section class="diagnostic-card card"><span class="section-kicker">${data.passed ? "All checks passed" : "Action required"}</span><h3>${checks.filter((item) => item.passed).length}/${checks.length} live checks passed</h3>${checks.map((check) => `<div class="check-row"><span class="check-icon ${check.passed ? "" : "fail"}">${check.passed ? "✓" : "!"}</span><strong>${escapeHTML(check.name)}</strong><span>${escapeHTML(check.value)}</span></div>`).join("")}</section><section class="diagnostic-card card"><span class="section-kicker">Question routing regression</span><h3>${routing.filter((item) => item.passed).length}/${routing.length} supported routes passed</h3><div class="location-table-wrap"><table class="routing-table"><thead><tr><th>Question</th><th>Expected</th><th>Actual</th><th>Result</th></tr></thead><tbody>${routing.map((item) => `<tr><td>${escapeHTML(item.question)}</td><td>${escapeHTML(item.expected)}</td><td>${escapeHTML(item.actual)}</td><td>${item.passed ? "✓" : "!"}</td></tr>`).join("")}</tbody></table></div></section></div><section class="diagnostic-card card" style="margin-top:8px"><span class="section-kicker">Participant-facing rubric alignment</span><div class="rubric-grid">${Object.entries(rubric).map(([key, item]) => `<article class="rubric-card"><strong>${escapeHTML(titleCase(key))}</strong><span>${item.weight}%</span><p>${escapeHTML(item.evidence)}</p></article>`).join("")}</div></section>`;
  } catch (error) { container.innerHTML = `<div class="refusal-card"><h2>Diagnostic failed</h2><p>${escapeHTML(error.message)}</p></div>`; }
}

async function openMethodology() {
  const modal = $("#methodologyModal");
  modal.classList.add("open"); modal.setAttribute("aria-hidden", "false");
  $("#methodologyContent").innerHTML = `<div class="loading-card"><span class="spinner"></span><p>Loading transparent model card…</p></div>`;
  try {
    const model = state.modelCard || normalizeModelPayload(await api("/api/resilience-model"));
    state.modelCard = model;
    renderModelCard(model, $("#methodologyContent"));
  } catch (error) { $("#methodologyContent").innerHTML = `<p>${escapeHTML(error.message)}</p>`; }
}

function careerFromCache(socCode) {
  return state.occupationCache.get(String(socCode)) || state.home?.path?.results?.find((item) => String(item.soc_code) === String(socCode)) || state.lastPath?.results?.find((item) => String(item.soc_code) === String(socCode)) || state.lastCompare?.results?.find((item) => String(item.soc_code) === String(socCode));
}

function evidenceForCareer(item) {
  const profile = item.resilience_profile || (
    state.lastOccupation?.profile?.soc_code === item.soc_code
      ? state.lastOccupation.resilience_profile
      : null
  );
  const contributions = item.contributions || {};
  return `<div class="evidence-kpi-grid"><div class="evidence-kpi"><small>Occupation code</small><strong>${escapeHTML(item.soc_code)}</strong></div><div class="evidence-kpi"><small>Median wage</small><strong>${money(item.median_wage)}</strong></div><div class="evidence-kpi"><small>Projected growth</small><strong>${pct(item.growth_percent)}</strong></div><div class="evidence-kpi"><small>Resilience model</small><strong>v${escapeHTML(profile?.model_version || "1.0.0")}</strong></div></div><div class="evidence-grid" style="margin-top:8px"><section class="evidence-section"><h3>Direct official values</h3><ul><li>BLS OEWS 2025 wage and employment snapshot</li><li>BLS 2024–2034 employment projections</li><li>O*NET 30.3 skills, tasks, technologies, and job zone</li><li>Exact SOC-code joins across source files</li></ul></section><section class="evidence-section"><h3>CareerProof-derived values</h3><ul><li>Fit score: weighted normalized components selected by the user</li><li>Resilience: six documented dimensions from O*NET text signals</li><li>Location opportunity: published wage, employment, concentration, RPP, and estimate quality</li><li>Task impact: keyword grouping for explanation, not a job-loss forecast</li></ul></section><section class="evidence-section"><h3>Score contributions</h3>${Object.entries(contributions).map(([key, value]) => `<div class="skill-row"><span>${escapeHTML(WEIGHT_META[key]?.label || titleCase(key))}</span><strong>${Number(value).toFixed(2)}</strong></div>`).join("") || `<p>Open this career from Path Builder or Compare Lab to see user-specific score contributions.</p>`}</section><section class="evidence-section"><h3>Confidence and limits</h3><p><strong>Source confidence:</strong> ${escapeHTML(item.source_confidence?.label || "High for direct official values")}</p><p><strong>Decision confidence:</strong> ${escapeHTML(item.decision_confidence?.label || "Depends on geography and data completeness")}</p><p>No career is permanently AI-proof. CareerProof does not predict an individual's outcome.</p></section></div><div class="data-vintage-inline"><span>◷</span><div>BLS wage data use May 2025. Projections cover 2024–2034. O*NET work content uses version 30.3. BEA RPP uses 2024. These are different measurement periods.</div></div>`;
}

function openCareerEvidence(socCode) {
  const item = careerFromCache(socCode);
  if (!item) { showToast("Open the career profile first so its evidence can be assembled."); return; }
  $("#evidenceTitle").textContent = item.occupation_title;
  $("#evidenceContent").innerHTML = evidenceForCareer(item);
  const modal = $("#evidenceModal"); modal.classList.add("open"); modal.setAttribute("aria-hidden", "false");
}

function openAnswerEvidence(data) {
  const e = data.evidence || {};
  $("#evidenceTitle").textContent = data.headline || "Answer evidence";
  $("#evidenceContent").innerHTML = `<div class="evidence-kpi-grid"><div class="evidence-kpi"><small>Evidence ID</small><strong>${escapeHTML(e.evidence_id || "—")}</strong></div><div class="evidence-kpi"><small>Rows used</small><strong>${formatNumber(data.analysis?.rows_used || 0)}</strong></div><div class="evidence-kpi"><small>Rows excluded</small><strong>${formatNumber(data.analysis?.suppressed_or_excluded || 0)}</strong></div><div class="evidence-kpi"><small>Confidence</small><strong>${escapeHTML(e.confidence?.label || "Review")}</strong></div></div><div class="evidence-grid" style="margin-top:8px"><section class="evidence-section"><h3>Source lineage</h3><p>${escapeHTML((e.source_names || []).join(" + "))}</p>${(e.source_urls || []).map((url) => `<a class="source-link" href="${escapeHTML(url)}" target="_blank" rel="noreferrer">${escapeHTML(url)}</a>`).join("")}</section><section class="evidence-section"><h3>Query plan</h3><pre>${escapeHTML(JSON.stringify(data.query_plan || {}, null, 2))}</pre></section><section class="evidence-section"><h3>Calculation</h3><p>${escapeHTML(data.analysis?.calculation || "")}</p><p><strong>Dataset note:</strong> ${escapeHTML(e.dataset_note || "")}</p></section><section class="evidence-section"><h3>Limitations</h3><ul>${(data.limitations || []).map((item) => `<li>${escapeHTML(item)}</li>`).join("")}</ul></section></div>`;
  const modal = $("#evidenceModal"); modal.classList.add("open"); modal.setAttribute("aria-hidden", "false");
}

function closeAllOverlays() {
  $$(".modal-shell.open").forEach((modal) => { modal.classList.remove("open"); modal.setAttribute("aria-hidden", "true"); });
  $("#savedDrawer").classList.remove("open"); $("#savedDrawer").setAttribute("aria-hidden", "true");
  if ($("#judgeOverlay")?.classList.contains("open")) closeJudgeMode();
}

function saveCareerBySoc(socCode) {
  const item = careerFromCache(socCode);
  if (!item) { showToast("Open this career first, then save it."); return; }
  if (!state.saved.some((saved) => String(saved.soc_code) === String(socCode))) {
    state.saved.push({ soc_code: item.soc_code, occupation_title: item.occupation_title, median_wage: item.median_wage, resilience_label: item.resilience_label, category: item.category });
    safeStorage.setItem("careerproof-saved", JSON.stringify(state.saved));
    showToast(`${item.occupation_title} saved.`);
  } else showToast(`${item.occupation_title} is already saved.`);
  renderSavedCounts(); renderSavedDrawer(); renderSavedWorkspace();
}

function removeSaved(socCode) {
  state.saved = state.saved.filter((item) => String(item.soc_code) !== String(socCode));
  safeStorage.setItem("careerproof-saved", JSON.stringify(state.saved));
  renderSavedCounts(); renderSavedDrawer(); renderSavedWorkspace();
}

function renderSavedCounts() {
  $("#savedCount").textContent = state.saved.length;
  $("#savedNavCount").textContent = state.saved.length;
}

function renderSavedDrawer() {
  const container = $("#savedList");
  container.innerHTML = state.saved.length ? state.saved.map((item) => `<article class="saved-item"><div><strong>${escapeHTML(item.occupation_title)}</strong><small>${escapeHTML(item.category || "Occupation")} · ${money(item.median_wage, true)} · ${escapeHTML(item.resilience_label || "Resilience profile")}</small></div><button data-remove-saved="${item.soc_code}" aria-label="Remove ${escapeHTML(item.occupation_title)}">×</button></article>`).join("") : `<div class="empty-state"><p>No careers saved yet.</p></div>`;
}

function renderSavedWorkspace() {
  const list = $("#savedWorkspaceList");
  if (!list) return;
  list.innerHTML = state.saved.length ? state.saved.map((item) => `<article class="saved-workspace-item"><div><strong>${escapeHTML(item.occupation_title)}</strong><small>${money(item.median_wage, true)} · ${escapeHTML(item.resilience_label || "Resilience profile")}</small></div><div><button data-open-soc="${item.soc_code}">Open</button><button data-tray-soc="${item.soc_code}">Compare</button><button data-remove-saved="${item.soc_code}">Remove</button></div></article>`).join("") : `<div class="empty-state"><p>Save careers from Path Builder, Compare Lab, Career Universe, or an occupation profile.</p></div>`;
  const portfolio = state.lastPath?.portfolio || {};
  $("#savedPortfolio").innerHTML = [["Primary path", portfolio.primary_path], ["Safer backup", portfolio.safer_backup], ["High upside", portfolio.high_upside_option], ["Fast entry", portfolio.fast_entry_option]].map(([label, item]) => item ? `<button class="portfolio-item" data-open-soc="${item.soc_code}"><small>${escapeHTML(label)}</small><strong>${escapeHTML(item.occupation_title)}</strong><span>${Math.round(item.score)} fit · ${escapeHTML(item.resilience_label)}</span></button>` : `<div class="portfolio-item"><small>${escapeHTML(label)}</small><strong>Run Path Builder</strong><span>to generate this option</span></div>`).join("");
  $("#decisionNotes").value = state.decisionNotes;
}

function addToComparisonTray(socCode) {
  const item = careerFromCache(socCode) || state.saved.find((saved) => String(saved.soc_code) === String(socCode));
  if (!item) { showToast("Open this career first so CareerProof can add it."); return; }
  if (state.comparisonTray.has(String(socCode))) state.comparisonTray.delete(String(socCode));
  else if (state.comparisonTray.size < 4) state.comparisonTray.set(String(socCode), item);
  else { showToast("Compare up to four careers at a time."); return; }
  renderComparisonTray();
}

function renderComparisonTray() {
  const tray = $("#comparisonTray");
  const items = [...state.comparisonTray.values()];
  tray.classList.toggle("open", items.length > 0);
  tray.setAttribute("aria-hidden", items.length ? "false" : "true");
  $("#comparisonTrayItems").innerHTML = items.map((item) => `<span class="tray-item"><span>${escapeHTML(item.occupation_title)}</span><button data-remove-tray="${item.soc_code}" aria-label="Remove ${escapeHTML(item.occupation_title)}">×</button></span>`).join("");
  $("#comparisonTrayCount").textContent = items.length;
}

function openTrayComparison() {
  const items = [...state.comparisonTray.values()];
  if (items.length < 2) { showToast("Add at least two careers."); return; }
  state.compareValues = ["", "", "", ""];
  state.compareResolved = [null, null, null, null];
  items.forEach((item, index) => { state.compareValues[index] = item.occupation_title; state.compareResolved[index] = item; });
  renderCompareSlots();
  switchWorkspace("compare");
  setTimeout(runCompare, 100);
}

function exportSavedPlan() {
  const profile = state.lastPath?.interpretation?.normalized_profile || getStoredProfile();
  const path = state.lastPath;
  const saved = state.saved;
  const generated = new Date().toLocaleString();
  const html = `<!doctype html><html><head><meta charset="utf-8"><title>CareerProof AI Plan</title><style>body{font-family:Arial,sans-serif;max-width:900px;margin:40px auto;color:#14213d;line-height:1.5}h1{font-size:38px}h2{margin-top:32px;border-bottom:2px solid #4169e1;padding-bottom:8px}.card{border:1px solid #ccd5e6;border-radius:10px;padding:16px;margin:10px 0}.grid{display:grid;grid-template-columns:1fr 1fr;gap:10px}.muted{color:#61708b}.tag{display:inline-block;padding:4px 7px;background:#edf2ff;border-radius:6px;margin:3px}.warning{background:#fff8e6;border-left:4px solid #e5a423;padding:12px}@media print{button{display:none}}</style></head><body><h1>CareerProof AI Career Plan</h1><p class="muted">Generated ${escapeHTML(generated)} · AI interprets. Code calculates. Evidence verifies. You decide.</p><div class="warning">No career is permanently AI-proof. This report is a decision aid built from bundled official data and transparent CareerProof-derived metrics.</div><h2>User goals</h2><div class="card"><p><strong>Interests:</strong> ${escapeHTML((profile.interests || []).join(", "))}</p><p><strong>Skills:</strong> ${escapeHTML((profile.skills || []).join(", "))}</p><p><strong>Education ceiling:</strong> ${escapeHTML(profile.education_max || "No limit")}</p><p><strong>Location:</strong> ${escapeHTML(profile.preferred_state || "Any state")}</p><p><strong>Salary target:</strong> ${profile.salary_goal ? money(profile.salary_goal) : "No minimum"}</p></div><h2>Recommended portfolio</h2><div class="grid">${path ? [["Primary", path.portfolio?.primary_path], ["Safer backup", path.portfolio?.safer_backup], ["High upside", path.portfolio?.high_upside_option], ["Fast entry", path.portfolio?.fast_entry_option]].map(([label, item]) => item ? `<div class="card"><small>${escapeHTML(label)}</small><h3>${escapeHTML(item.occupation_title)}</h3><p>${money(item.median_wage)} median · ${pct(item.growth_percent)} growth · ${escapeHTML(item.resilience_label)} resilience</p></div>` : "").join("") : `<div class="card">Run Path Builder to generate a portfolio.</div>`}</div><h2>Saved careers</h2>${saved.map((item) => `<div class="card"><h3>${escapeHTML(item.occupation_title)}</h3><p>${money(item.median_wage)} · ${escapeHTML(item.resilience_label || "")}</p></div>`).join("") || `<p>No careers saved.</p>`}<h2>Decision journal</h2><div class="card">${escapeHTML(state.decisionNotes || "No notes recorded.").replaceAll("\n", "<br>")}</div><h2>Evidence and limitations</h2><ul><li>BLS May 2025 wage and employment snapshots</li><li>BLS 2024–2034 employment projections</li><li>O*NET 30.3 skills, tasks, technology, and job-zone content</li><li>BEA 2024 Regional Price Parities</li><li>NCES/BLS degree-to-career relationships</li></ul><p class="muted">CareerProof-derived fit, resilience, stability, and opportunity scores are transparent decision aids. They are not government ratings, predictions, or guarantees.</p></body></html>`;
  const blob = new Blob([html], { type: "text/html" });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url; anchor.download = "careerproof-career-plan.html"; anchor.click();
  URL.revokeObjectURL(url);
  showToast("Career plan exported as HTML. Open it in a browser to print or save as PDF.");
}

function formatJudgeTime(totalSeconds) {
  const seconds = Math.max(0, Math.round(Number(totalSeconds) || 0));
  const minutes = Math.floor(seconds / 60);
  return `${minutes}:${String(seconds % 60).padStart(2, "0")}`;
}

function getJudgeSteps() {
  const steps = state.judgeData?.steps || [];
  return state.judgeMode === "quick" ? steps.filter((step) => step.quick) : steps;
}

function currentJudgeStep() {
  return getJudgeSteps()[state.judgeStep] || null;
}

function stopJudgeAutoTimer() {
  if (state.judgeAutoTimer) window.clearTimeout(state.judgeAutoTimer);
  state.judgeAutoTimer = null;
}

function stopJudgeClock() {
  if (state.judgeTimer) window.clearInterval(state.judgeTimer);
  state.judgeTimer = null;
  stopJudgeAutoTimer();
}

function updateJudgeElapsed() {
  const elapsed = state.judgeStartedAt ? Math.floor((Date.now() - state.judgeStartedAt) / 1000) : 0;
  const output = $("#judgeElapsed");
  if (output) output.textContent = formatJudgeTime(elapsed);
}

function startJudgeClock({ reset = false } = {}) {
  if (reset || !state.judgeStartedAt) state.judgeStartedAt = Date.now();
  if (reset || !state.judgeStepStartedAt) state.judgeStepStartedAt = Date.now();
  if (state.judgeTimer) window.clearInterval(state.judgeTimer);
  updateJudgeElapsed();
  state.judgeTimer = window.setInterval(updateJudgeElapsed, 1000);
}

function judgeRubricKeys(stepId) {
  const map = {
    purpose: ["problem", "story"], interpret: ["data_ai", "trust"], path: ["prototype", "data_ai"],
    challenge: ["trust", "data_ai"], compare: ["prototype", "data_ai"], proof: ["trust", "data_ai"],
    refusal: ["trust"], plan: ["problem", "prototype"], architecture: ["architecture"], close: ["story"],
  };
  return map[stepId] || [];
}

function renderJudgeRubric() {
  const container = $("#judgeRubric");
  if (!container) return;
  const active = new Set(judgeRubricKeys(currentJudgeStep()?.id));
  container.innerHTML = (state.judgeData?.rubric || []).map((item) => `
    <div class="judge-rubric-chip ${active.has(item.key) ? "active" : ""}" title="${escapeHTML(item.proof)}">
      <span>${escapeHTML(item.label)}</span><strong>${item.weight}%</strong>
    </div>`).join("");
}

function renderJudgeTimeline() {
  const container = $("#judgeTimeline");
  if (!container) return;
  const steps = getJudgeSteps();
  container.innerHTML = steps.map((step, index) => `
    <button type="button" class="judge-timeline-step ${index === state.judgeStep ? "active" : ""} ${index < state.judgeStep ? "complete" : ""}" data-judge-step="${index}" aria-current="${index === state.judgeStep ? "step" : "false"}">
      <span class="judge-timeline-index">${index < state.judgeStep ? "✓" : String(index + 1).padStart(2, "0")}</span>
      <span class="judge-timeline-copy"><strong>${escapeHTML(step.title)}</strong><small>${escapeHTML(step.judge_focus || "Judge proof")}</small></span>
      <time>${formatJudgeTime(step.duration_seconds)}</time>
    </button>`).join("");
}

function renderJudgeProgress() {
  const steps = getJudgeSteps();
  const progress = $("#judgeProgress");
  if (progress) {
    progress.style.gridTemplateColumns = `repeat(${Math.max(1, steps.length)},1fr)`;
    progress.innerHTML = steps.map((_, index) => `<span class="${index <= state.judgeStep ? "active" : ""}"></span>`).join("");
  }
  $("#judgeStepLabel").textContent = `${state.judgeStep + 1} / ${steps.length}`;
  $("#judgeStepTime").textContent = `Suggested: ${formatJudgeTime(currentJudgeStep()?.duration_seconds || 0)}`;
  $("#judgePrev").disabled = state.judgeStep === 0;
  $("#judgeNext").innerHTML = state.judgeStep === steps.length - 1 ? `<span>Finish presentation</span><b>✓</b>` : `<span>Next proof</span><b>→</b>`;
  const live = $("#judgeOpenLive");
  if (live) live.textContent = currentJudgeStep()?.action_label || "Open live feature ↗";
  renderJudgeTimeline();
  renderJudgeRubric();
}

function judgeMiniCareer(item, index) {
  const feasibility = item.feasibility?.status || "review";
  return `<article class="judge-mini-card">
    <div class="judge-mini-rank"><span>Rank ${index + 1}</span><em class="feasibility-chip ${feasibilityClass(feasibility)}">${escapeHTML(feasibility)}</em></div>
    <h4>${escapeHTML(item.occupation_title)}</h4>
    <div class="judge-mini-score"><strong>${Number(item.score).toFixed(1)}</strong><small>CareerProof fit</small></div>
    <p>${money(item.median_wage, true)} median · ${pct(item.growth_percent)} growth</p>
    <span>${escapeHTML(item.resilience_label)} resilience</span>
  </article>`;
}

function judgeProofPoints(step) {
  return `<div class="judge-proof-points"><span>Proof points</span>${(step.proof_points || []).map((item) => `<div><i>✓</i><p>${escapeHTML(item)}</p></div>`).join("")}</div>`;
}

function judgeComponentRows(item) {
  return Object.entries(item?.contributions || {}).sort((a, b) => Number(b[1]) - Number(a[1])).slice(0, 5).map(([key, value]) => `
    <div class="judge-component-row"><span>${escapeHTML(WEIGHT_META[key]?.label || titleCase(key))}</span><i><span style="width:${Math.min(100, Number(item.components?.[key] || 0))}%"></span></i><strong>${Number(value).toFixed(1)}</strong></div>`).join("");
}

function judgePurposeVisual(data) {
  const meta = data.demo_meta || {};
  const stats = state.bootstrap?.stats || {};
  return `<div class="judge-problem-visual">
    <span class="judge-visual-label">THE USER'S QUESTION</span>
    <blockquote>${escapeHTML(meta.core_question || "What career fits me and remains valuable as AI changes work?")}</blockquote>
    <div class="judge-data-pulse">
      <div><strong>${formatNumber(stats.occupations || 830)}</strong><small>occupations</small></div>
      <div><strong>${compactNumber(stats.state_occupation_rows || 36168)}</strong><small>state records</small></div>
      <div><strong>${compactNumber(stats.degree_occupation_links || 5917)}</strong><small>degree links</small></div>
      <div><strong>${formatNumber(stats.official_sources || 8)}</strong><small>source families</small></div>
    </div>
    <p>${escapeHTML(meta.disclosure || "Demonstration values are official or clearly labeled derived metrics.")}</p>
  </div>`;
}

function judgeInterpretVisual(data) {
  const interpretation = data.interpretation || {};
  return `<div class="judge-interpret-visual">
    <div class="judge-control-chain"><span>Natural language</span><b>→</b><span>Structured interpretation</span><b>→</b><strong>User approval</strong><b>→</b><span>Calculation</span></div>
    <div class="judge-interpret-grid">
      <section><small>Goal</small><h4>${escapeHTML(interpretation.goal || "Find a sustainable AI-resilient career")}</h4><div class="judge-chip-list">${(interpretation.interests || []).map((item) => `<span>${escapeHTML(item)}</span>`).join("")}</div></section>
      <section><small>Hard and soft constraints</small>${(interpretation.constraints || []).map((item) => `<p><strong>${escapeHTML(item.label)}</strong><span>${escapeHTML(item.value)}</span>${item.hard ? '<em>HARD</em>' : ""}</p>`).join("")}</section>
      <section><small>User-controlled priorities</small>${(interpretation.priorities || []).slice(0, 6).map((item) => `<div class="judge-priority"><span>${escapeHTML(item.label)}</span><i><span style="width:${Math.min(100, Number(item.weight) * 2)}%"></span></i><strong>${Number(item.weight).toFixed(0)}%</strong></div>`).join("")}</section>
    </div>
  </div>`;
}

function judgePathVisual(data) {
  const results = data.path_builder?.results || [];
  const top = results[0] || {};
  return `<div class="judge-path-visual">
    <div class="judge-mini-cards">${results.slice(0, 3).map(judgeMiniCareer).join("")}</div>
    <div class="judge-score-proof">
      <div class="judge-score-orb" style="--score:${Math.round(top.score || 0)}"><strong>${Number(top.score || 0).toFixed(1)}</strong><span>transparent fit score</span></div>
      <div class="judge-component-list">${judgeComponentRows(top)}</div>
    </div>
    <div class="judge-hard-gate"><span>Hard constraint gate</span><strong>${formatNumber(data.path_builder?.excluded_by_hard_constraints?.count || 0)} careers excluded before ranking</strong><p>The bachelor's-degree ceiling is enforced before soft scoring.</p></div>
  </div>`;
}

function judgeChallengeVisual(data) {
  const top = data.path_builder?.results?.[0] || {};
  const challenge = top.challenge || {};
  const changes = data.path_builder?.what_would_change_recommendation || [];
  return `<div class="judge-challenge-visual">
    <header><span>CHALLENGE THE WINNER</span><h4>${escapeHTML(top.occupation_title || "Top recommendation")}</h4></header>
    <div class="judge-challenge-grid">
      <section><small>Weakest evidence</small><p>${escapeHTML(challenge.weakest_evidence || "No weakness published")}</p><small>Missing or limited</small><ul>${(challenge.missing_information || []).map((item) => `<li>${escapeHTML(item)}</li>`).join("")}</ul></section>
      <section><small>Strongest challenger</small><p><strong>${escapeHTML(challenge.strongest_challenger?.occupation_title || "Alternative shown in results")}</strong><br>${escapeHTML(challenge.strongest_challenger?.why_it_could_win || "Different priorities can change the ranking.")}</p><small>What changes the result?</small>${changes.slice(0, 3).map((item) => `<div class="judge-change-row"><span>${escapeHTML(item.condition)}</span><strong>${escapeHTML(item.impact)}</strong></div>`).join("")}</section>
    </div>
    <div class="judge-question-callout">${escapeHTML(challenge.question_to_ask || "What evidence would change your mind?")}</div>
  </div>`;
}

function judgeCompareVisual(data) {
  const results = data.comparison?.results || [];
  return `<div class="judge-compare-visual">
    <div class="judge-mini-cards">${results.slice(0, 3).map(judgeMiniCareer).join("")}</div>
    <div class="tradeoff-callout">${escapeHTML(data.comparison?.tradeoff_summary?.plain_language || "The visible result reflects the selected priorities and hard constraints.")}</div>
    <div class="judge-scenario-grid">${(data.comparison?.sensitivity || []).slice(0, 6).map((item) => `<div><span>${escapeHTML(item.label)}</span><strong>${escapeHTML(item.top_occupation)}</strong><b>${Number(item.top_score).toFixed(1)}</b></div>`).join("")}</div>
  </div>`;
}

function judgeProofVisual(data) {
  const answer = data.verified_answer || {};
  const e = answer.evidence || {};
  const rows = answer.rows || [];
  return `<div class="judge-evidence-visual">
    <div class="judge-evidence-head"><span>VERIFIED ANSWER</span><h4>${escapeHTML(answer.headline || "Inspect the proof")}</h4><p>${escapeHTML(answer.explanation || answer.summary || "")}</p></div>
    <div class="judge-evidence-kpis">
      <div><small>Source confidence</small><strong>${escapeHTML(e.confidence?.label || answer.confidence?.label || "High")}</strong></div>
      <div><small>Rows shown</small><strong>${formatNumber(rows.length)}</strong></div>
      <div><small>Excluded</small><strong>${formatNumber(answer.analysis?.suppressed_or_excluded || 0)}</strong></div>
      <div><small>Evidence ID</small><strong>${escapeHTML(e.evidence_id || answer.evidence_id || "Generated")}</strong></div>
    </div>
    <div class="judge-location-rows">${rows.slice(0, 3).map((row, index) => `<div><span>${index + 1}</span><strong>${escapeHTML(row.state)}</strong><p>${money(row.purchasing_power_wage)} purchasing-power wage</p><b>${escapeHTML(row.decision_confidence || "Review")}</b></div>`).join("")}</div>
    <div class="judge-calculation"><small>Visible calculation</small><p>${escapeHTML(answer.analysis?.calculation || e.calculation || "Calculation is displayed in the Evidence Passport.")}</p></div>
  </div>`;
}

function judgeRefusalVisual(data) {
  const refusal = data.safe_refusal || {};
  return `<div class="judge-refusal-visual">
    <div class="judge-refusal-icon">!</div>
    <span>UNSUPPORTED CLAIM BLOCKED</span>
    <h4>${escapeHTML(refusal.headline || "The available data cannot support that conclusion")}</h4>
    <p>${escapeHTML(refusal.explanation || refusal.summary || "")}</p>
    <div class="judge-refusal-plan"><small>Controlled query plan</small><code>${escapeHTML(JSON.stringify(refusal.query_plan || {}, null, 2))}</code></div>
    <div class="judge-suggestion-chips">${(refusal.suggestions || []).slice(0, 3).map((item) => `<span>${escapeHTML(item)}</span>`).join("")}</div>
  </div>`;
}

function judgePlanVisual(data) {
  const plan = data.action_plan || {};
  const roadmap = plan.roadmap || {};
  const portfolio = [["Primary path", plan.primary], ["Safer backup", plan.backup], ["High upside", plan.high_upside], ["Fast entry", plan.fast_entry]];
  return `<div class="judge-plan-visual">
    <div class="judge-portfolio-grid">${portfolio.map(([label, item]) => item ? `<article><small>${escapeHTML(label)}</small><strong>${escapeHTML(item.occupation_title)}</strong><p>${money(item.median_wage, true)} · ${escapeHTML(item.resilience_label)} resilience</p></article>` : "").join("")}</div>
    <div class="judge-roadmap"><span>ACTION ROADMAP</span>${(roadmap.actions || []).map((action, index) => `<div><i>${index + 1}</i><p><strong>${escapeHTML(action.label || action.title || titleCase(action.type))}</strong><small>${escapeHTML(action.detail || "")}</small></p></div>`).join("")}</div>
    <div class="judge-report-strip"><strong>Exportable report</strong>${(plan.report_sections || []).slice(0, 8).map((section) => `<span>${escapeHTML(section)}</span>`).join("")}</div>
  </div>`;
}

function judgeArchitectureVisual(data) {
  return `<div class="judge-architecture-visual">${(data.architecture || []).map((stage, index) => `<div class="judge-architecture-stage"><span>${index + 1}</span><section><strong>${escapeHTML(stage.label)}</strong><p>${escapeHTML(stage.detail)}</p></section>${index < (data.architecture || []).length - 1 ? "<b>→</b>" : ""}</div>`).join("")}</div>`;
}

function judgeCloseVisual(data) {
  return `<div class="judge-close-visual">
    <div class="judge-method-lockup"><span>AI interprets.</span><span>Code calculates.</span><span>Evidence verifies.</span><strong>You decide.</strong></div>
    <div class="judge-final-rubric">${(data.rubric || []).map((item) => `<div><span>${escapeHTML(item.label)}</span><strong>${item.weight}%</strong><p>${escapeHTML(item.proof)}</p></div>`).join("")}</div>
    <p>${escapeHTML(data.closing?.summary || "A practical, trustworthy career decision system.")}</p>
  </div>`;
}

function judgeVisualForStep(step, data) {
  if (step.id === "purpose") return judgePurposeVisual(data);
  if (step.id === "interpret") return judgeInterpretVisual(data);
  if (step.id === "path") return judgePathVisual(data);
  if (step.id === "challenge") return judgeChallengeVisual(data);
  if (step.id === "compare") return judgeCompareVisual(data);
  if (step.id === "proof") return judgeProofVisual(data);
  if (step.id === "refusal") return judgeRefusalVisual(data);
  if (step.id === "plan") return judgePlanVisual(data);
  if (step.id === "architecture") return judgeArchitectureVisual(data);
  return judgeCloseVisual(data);
}

function scheduleJudgeAutoplay() {
  stopJudgeAutoTimer();
  if (!state.judgeAutoplay || !$("#judgeOverlay")?.classList.contains("open")) return;
  const step = currentJudgeStep();
  const delay = Math.max(8, Number(step?.duration_seconds || 30)) * 1000;
  state.judgeAutoTimer = window.setTimeout(() => {
    const steps = getJudgeSteps();
    if (state.judgeStep < steps.length - 1) goToJudgeStep(state.judgeStep + 1);
    else setJudgeAutoplay(false);
  }, delay);
}

function setJudgeAutoplay(enabled) {
  state.judgeAutoplay = Boolean(enabled);
  const button = $("#judgeAutoplay");
  if (button) {
    button.setAttribute("aria-pressed", String(state.judgeAutoplay));
    button.textContent = state.judgeAutoplay ? "Auto-advance on" : "Auto-advance off";
    button.classList.toggle("active", state.judgeAutoplay);
  }
  if (state.judgeAutoplay) scheduleJudgeAutoplay();
  else stopJudgeAutoTimer();
}

function renderJudgeStep() {
  const data = state.judgeData;
  const step = currentJudgeStep();
  if (!data || !step) return;
  $("#judgeTitle").textContent = data.demo_meta?.title || "CareerProof AI guided presentation";
  $("#judgeSubtitle").textContent = data.demo_meta?.subtitle || "A verified success case, evidence case, and safe failure case";
  $("#judgeContent").innerHTML = `
    <article class="judge-slide" data-step-id="${escapeHTML(step.id)}">
      <section class="judge-slide-copy">
        <span class="judge-step-eyebrow">${escapeHTML(step.eyebrow || `Step ${state.judgeStep + 1}`)}</span>
        <h3>${escapeHTML(step.title)}</h3>
        <p class="judge-step-summary">${escapeHTML(step.copy)}</p>
        <div class="judge-presenter-script">
          <header><span>Suggested narration</span><button type="button" data-copy-judge-script>Copy script</button></header>
          <p>${escapeHTML(step.presenter_script || step.copy)}</p>
        </div>
        <div class="judge-focus-card"><small>What the judges should notice</small><strong>${escapeHTML(step.judge_focus || "Rubric alignment")}</strong><p>The visual on the right is generated from the same verified demo payload used by the live app.</p></div>
        ${judgeProofPoints(step)}
      </section>
      <section class="judge-slide-visual">${judgeVisualForStep(step, data)}</section>
    </article>`;
  $("[data-copy-judge-script]")?.addEventListener("click", async () => {
    try {
      await navigator.clipboard.writeText(step.presenter_script || step.copy || "");
      showToast("Presenter script copied.");
    } catch {
      showToast("Copy is unavailable in this browser. The script remains visible.");
    }
  });
  state.judgeStepStartedAt = Date.now();
  renderJudgeProgress();
  scheduleJudgeAutoplay();
}

function goToJudgeStep(index) {
  const steps = getJudgeSteps();
  state.judgeStep = Math.max(0, Math.min(Number(index) || 0, steps.length - 1));
  renderJudgeStep();
}

function setJudgeMode(mode) {
  state.judgeMode = mode === "quick" ? "quick" : "full";
  $("#judgeModeFull")?.classList.toggle("active", state.judgeMode === "full");
  $("#judgeModeQuick")?.classList.toggle("active", state.judgeMode === "quick");
  state.judgeStep = 0;
  state.judgeStartedAt = Date.now();
  state.judgeStepStartedAt = Date.now();
  renderJudgeStep();
  startJudgeClock();
}

async function startJudgeMode() {
  const overlay = $("#judgeOverlay");
  overlay.classList.add("open");
  overlay.setAttribute("aria-hidden", "false");
  document.body.classList.add("judge-mode-open");
  $("#judgeContent").innerHTML = `<div class="loading-card"><span class="spinner"></span><h3>Preparing the verified presentation</h3><p>Loading the success case, comparison, evidence case, safe refusal, and action plan…</p></div>`;
  try {
    if (!state.judgeData) state.judgeData = normalizeJudgePayload(await api("/api/judge-demo"));
    const meta = state.judgeData.demo_meta || {};
    $("#judgeFullDuration").textContent = formatJudgeTime(meta.full_duration_seconds || (state.judgeData.steps || []).reduce((sum, step) => sum + Number(step.duration_seconds || 0), 0));
    $("#judgeQuickDuration").textContent = formatJudgeTime(meta.quick_duration_seconds || (state.judgeData.steps || []).filter((step) => step.quick).reduce((sum, step) => sum + Number(step.duration_seconds || 0), 0));
    state.judgeMode = "full";
    state.judgeStep = 0;
    state.judgeStartedAt = Date.now();
    state.judgeStepStartedAt = Date.now();
    setJudgeAutoplay(false);
    $("#judgeModeFull")?.classList.add("active");
    $("#judgeModeQuick")?.classList.remove("active");
    startJudgeClock({ reset: true });
    renderJudgeStep();
    $("#judgeNext")?.focus({ preventScroll: true });
  } catch (error) {
    $("#judgeContent").innerHTML = `<div class="refusal-card"><span class="refusal-badge">Presentation stopped safely</span><h2>The verified demo payload could not load</h2><p>${escapeHTML(error.message)}</p><button class="outline-button" type="button" id="retryJudgeMode">Retry</button></div>`;
    $("#retryJudgeMode")?.addEventListener("click", () => { state.judgeData = null; startJudgeMode(); });
  }
}

function closeJudgeMode() {
  stopJudgeClock();
  setJudgeAutoplay(false);
  $("#judgeOverlay").classList.remove("open");
  $("#judgeOverlay").setAttribute("aria-hidden", "true");
  document.body.classList.remove("judge-mode-open");
}

async function openJudgeLiveFeature() {
  const step = currentJudgeStep();
  const data = state.judgeData;
  if (!step || !data) return;
  closeJudgeMode();
  applyDemoProfile();
  const pathData = data.path_builder;
  if (["interpret", "path", "challenge"].includes(step.id)) {
    switchWorkspace("path");
    renderInterpretation(data.interpretation);
    if (["path", "challenge"].includes(step.id)) {
      state.lastPath = pathData;
      safeStorage.setItem("careerproof-last-path", JSON.stringify(pathData));
      (pathData.results || []).forEach(cacheCareer);
      renderPathResults(pathData);
      if (step.id === "challenge") {
        window.setTimeout(() => {
          const top = pathData.results?.[0];
          const panel = top ? $(`[data-challenge-panel="${top.soc_code}"]`) : null;
          panel?.classList.remove("hidden");
          panel?.scrollIntoView({ behavior: "smooth", block: "center" });
        }, 200);
      }
    }
  } else if (step.id === "compare") {
    state.compareValues = (data.comparison.results || []).slice(0, 3).map((item) => item.occupation_title).concat([""]).slice(0, 4);
    state.compareResolved = (data.comparison.results || []).slice(0, 3).concat([null]).slice(0, 4);
    state.lastCompare = data.comparison;
    (data.comparison.results || []).forEach(cacheCareer);
    renderCompareSlots();
    switchWorkspace("compare");
    renderCompare(data.comparison);
  } else if (step.id === "proof") {
    switchWorkspace("ask");
    $("#questionInput").value = data.verified_answer.question || "Where does an electrical engineer's salary go furthest after cost of living?";
    renderQuestionResult(data.verified_answer);
  } else if (step.id === "refusal") {
    switchWorkspace("ask");
    $("#questionInput").value = data.safe_refusal.question || "Which bachelor's degree guarantees the highest salary after becoming a lawyer?";
    renderQuestionResult(data.safe_refusal);
  } else if (step.id === "plan") {
    state.lastPath = pathData;
    safeStorage.setItem("careerproof-last-path", JSON.stringify(pathData));
    switchWorkspace("saved");
    renderSavedWorkspace();
  } else if (step.id === "architecture") {
    switchWorkspace("trust");
    loadTrustTab("diagnostic");
  } else {
    switchWorkspace("home");
  }
  showToast(`${step.title} opened in the live product.`);
}

function applyDemoProfile() {
  $("#profileText").value = "I like electronics and programming, but I am also interested in law. I want to stay near Maryland, earn at least $90,000, and stop at a bachelor's degree.";
  state.selectedInterests = new Set(["Electronics", "Programming", "Law"]);
  state.skills = ["Python", "Arduino", "Writing", "Problem Solving"];
  state.workEnvironment = new Set(["Hands-on", "Office or analytical", "People-facing"]);
  state.pathWeights = { interest_fit: 24, resilience: 28, salary: 18, growth: 8, openings: 8, education: 7, location: 4, stability: 3 };
  $("#pathEducation").value = "Bachelor's degree"; $("#pathState").value = "Maryland"; $("#pathSalary").value = 90000;
  $("#hardEducation").checked = true; $("#hardSalary").checked = false; $("#hardLocation").checked = false; $("#willingRelocate").checked = false;
  renderInterestChips(); renderSkillTags(); renderWeightControls("pathWeights", state.pathWeights, updatePathWeightTotal); updatePathWeightTotal();
  $$("[data-work-environment]").forEach((button) => button.classList.toggle("selected", state.workEnvironment.has(button.dataset.workEnvironment)));
}

function resetJudgeDemo() {
  applyDemoProfile();
  state.comparisonTray.clear();
  renderComparisonTray();
  state.judgeStep = 0;
  state.judgeStartedAt = Date.now();
  state.judgeStepStartedAt = Date.now();
  setJudgeAutoplay(false);
  startJudgeClock({ reset: true });
  renderJudgeStep();
  showToast("Presentation reset to the verified starting profile.");
}

function resetExperience() {
  closeJudgeMode();
  applyDemoProfile();
  state.lastPath = null;
  state.lastInterpretation = null;
  state.lastCompare = null;
  state.lastOccupation = null;
  state.comparisonTray.clear();
  state.compareValues = ["Electrical Engineers", "Nuclear Engineers", "Lawyers", ""];
  state.compareResolved = [null, null, null, null];
  state.compareWeights = { ...DEFAULT_COMPARE_WEIGHTS };
  state.judgeStep = 0;
  safeStorage.removeItem("careerproof-last-path");
  renderComparisonTray();
  renderCompareSlots();
  renderWeightControls("compareWeights", state.compareWeights);
  $("#pathInterpretation").classList.add("hidden");
  $("#pathForm").classList.remove("hidden");
  $("#pathResults").innerHTML = `<div class="empty-intelligence"><span>⌁</span><h2>Your evidence-backed options will appear here</h2><p>Review the interpretation first. Then CareerProof applies hard gates, official data, the resilience model, and your weights.</p></div>`;
  $("#compareResults").innerHTML = `<div class="empty-state card"><span>⇄</span><h3>Add two or more careers</h3><p>Load the judge demo or search for careers to calculate a transparent tradeoff.</p></div>`;
  $("#bridgeSource").value = ""; $("#bridgeSource").removeAttribute("data-soc");
  $("#bridgeTarget").value = ""; $("#bridgeTarget").removeAttribute("data-soc");
  $("#bridgeResults").innerHTML = `<div class="empty-state card"><span>⌘</span><h3>Choose a starting and target career</h3><p>The bridge describes occupational overlap. It does not guarantee a transition.</p></div>`;
  $("#questionInput").value = "";
  $("#resultArea").innerHTML = `<div class="empty-state card"><span>◈</span><h3>Ask something the data can prove</h3><p>CareerProof will show the calculation, source rows, confidence, and limitations.</p></div>`;
  ["#evidenceModal", "#methodologyModal"].forEach((selector) => {
    const element = $(selector); element?.classList.remove("open"); element?.setAttribute("aria-hidden", "true");
  });
  $("#savedDrawer").classList.remove("open"); $("#savedDrawer").setAttribute("aria-hidden", "true");
  switchWorkspace("home");
  showToast("Demo reset to the verified starting profile.");
}

function updatePathWeightTotal() {
  const total = Object.values(state.pathWeights).reduce((sum, value) => sum + Number(value || 0), 0);
  $("#pathWeightTotal").textContent = `${Math.round(total)}% raw · normalized to 100%`;
}

function bindFormsAndControls() {
  $("#pathForm").addEventListener("submit", (event) => { event.preventDefault(); reviewPathInterpretation(); });
  $("#interestChips").addEventListener("click", (event) => {
    const button = event.target.closest("[data-interest]"); if (!button) return;
    const interest = button.dataset.interest;
    if (state.selectedInterests.has(interest)) state.selectedInterests.delete(interest); else state.selectedInterests.add(interest);
    button.classList.toggle("selected");
  });
  $("#workEnvironmentChips").addEventListener("click", (event) => {
    const button = event.target.closest("[data-work-environment]"); if (!button) return;
    const value = button.dataset.workEnvironment;
    if (state.workEnvironment.has(value)) state.workEnvironment.delete(value); else state.workEnvironment.add(value);
    button.classList.toggle("selected");
  });
  $("#addSkill").addEventListener("click", () => addSkill($("#skillInput").value));
  $("#skillInput").addEventListener("keydown", (event) => { if (event.key === "Enter") { event.preventDefault(); addSkill(event.target.value); } });
  $("#runCompare").addEventListener("click", runCompare);
  $("#loadDemoCompare").addEventListener("click", () => {
    state.compareValues = ["Electrical Engineers", "Software Developers", "", ""];
    state.compareWeights = { ...DEMO_COMPARE_WEIGHTS };
    renderCompareSlots(); renderWeightControls("compareWeights", state.compareWeights);
    $("#compareState").value = "Maryland"; $("#compareEducation").value = "Bachelor's degree"; $("#compareHardEducation").checked = true;
    runCompare();
  });
  $("#runBridge").addEventListener("click", runBridge);
  $("#askForm").addEventListener("submit", (event) => { event.preventDefault(); runQuestion(); });
  $("#searchDegrees").addEventListener("click", searchDegrees);
  $("#degreeSearch").addEventListener("keydown", (event) => { if (event.key === "Enter") { event.preventDefault(); searchDegrees(); } });
  $("#runLocation").addEventListener("click", () => runLocation());
  $("#runDiagnostic").addEventListener("click", () => { activateTrustTab("diagnostic"); runDiagnostic(); });
  $("#savedButton").addEventListener("click", () => { renderSavedDrawer(); $("#savedDrawer").classList.add("open"); $("#savedDrawer").setAttribute("aria-hidden", "false"); });
  $("#compareSaved").addEventListener("click", () => { state.comparisonTray.clear(); state.saved.slice(0, 4).forEach((item) => state.comparisonTray.set(String(item.soc_code), item)); renderComparisonTray(); openTrayComparison(); $("#savedDrawer").classList.remove("open"); });
  $("#openComparisonTray").addEventListener("click", openTrayComparison);
  $("#clearComparisonTray").addEventListener("click", () => { state.comparisonTray.clear(); renderComparisonTray(); });
  $("#exportSavedPlan").addEventListener("click", exportSavedPlan);
  $("#saveDecisionNotes").addEventListener("click", () => { state.decisionNotes = $("#decisionNotes").value; safeStorage.setItem("careerproof-decision-notes", state.decisionNotes); showToast("Decision journal saved locally."); });
  $("#startJudgeMode").addEventListener("click", startJudgeMode);
  $("#resetDemo").addEventListener("click", resetExperience);
  $("#closeJudge").addEventListener("click", closeJudgeMode);
  $("#judgePrev").addEventListener("click", () => goToJudgeStep(state.judgeStep - 1));
  $("#judgeNext").addEventListener("click", () => {
    const steps = getJudgeSteps();
    if (state.judgeStep < steps.length - 1) goToJudgeStep(state.judgeStep + 1);
    else {
      closeJudgeMode();
      switchWorkspace("home");
      showToast("Presentation complete. The live dashboard is ready for questions.");
    }
  });
  $("#judgeOpenLive").addEventListener("click", openJudgeLiveFeature);
  $("#judgeModeFull").addEventListener("click", () => setJudgeMode("full"));
  $("#judgeModeQuick").addEventListener("click", () => setJudgeMode("quick"));
  $("#judgeAutoplay").addEventListener("click", () => setJudgeAutoplay(!state.judgeAutoplay));
  $("#resetJudgeDemo").addEventListener("click", resetJudgeDemo);
  $("#judgeTimeline").addEventListener("click", (event) => {
    const button = event.target.closest("[data-judge-step]");
    if (button) goToJudgeStep(Number(button.dataset.judgeStep));
  });
  document.addEventListener("keydown", (event) => {
    if (!$("#judgeOverlay")?.classList.contains("open")) return;
    if (["INPUT", "TEXTAREA", "SELECT"].includes(document.activeElement?.tagName)) return;
    if (event.key === "ArrowLeft") { event.preventDefault(); goToJudgeStep(state.judgeStep - 1); }
    if (event.key === "ArrowRight") { event.preventDefault(); goToJudgeStep(state.judgeStep + 1); }
    if (event.key === " ") { event.preventDefault(); setJudgeAutoplay(!state.judgeAutoplay); }
  });
  $("#universeBack").addEventListener("click", renderUniverseRoot);
  $("#universeReset").addEventListener("click", renderUniverseRoot);
  $$("[data-trust-tab]").forEach((button) => button.addEventListener("click", () => activateTrustTab(button.dataset.trustTab)));
  attachCareerAutocomplete($("#bridgeSource")); attachCareerAutocomplete($("#bridgeTarget")); attachCareerAutocomplete($("#locationCareer"));

  $("#occupationSearch").addEventListener("input", debounce(async (event) => {
    const query = event.target.value.trim(); const menu = $("#occupationSearchResults");
    if (query.length < 2) { menu.classList.remove("open"); return; }
    try {
      const results = await searchOccupations(query, 12);
      menu.innerHTML = results.map((item) => `<button class="autocomplete-option" data-occupation-soc="${item.soc_code}"><strong>${escapeHTML(item.occupation_title)}</strong><small>${escapeHTML(item.category)} · ${money(item.median_wage, true)} · ${pct(item.growth_percent)}</small></button>`).join(""); menu.classList.add("open");
    } catch (error) { console.error(error); }
  }, 220));
}

function bindDelegatedActions() {
  document.addEventListener("click", (event) => {
    const open = event.target.closest("[data-open-soc]"); if (open) { event.preventDefault(); openOccupation(open.dataset.openSoc); }
    const occupationOption = event.target.closest("[data-occupation-soc]");
    if (occupationOption) {
      event.preventDefault();
      $("#occupationSearchResults")?.classList.remove("open");
      openOccupation(occupationOption.dataset.occupationSoc);
    }
    const save = event.target.closest("[data-save-soc]"); if (save) { event.stopPropagation(); saveCareerBySoc(save.dataset.saveSoc); }
    const tray = event.target.closest("[data-tray-soc]"); if (tray) { event.stopPropagation(); addToComparisonTray(tray.dataset.traySoc); }
    const removeTray = event.target.closest("[data-remove-tray]"); if (removeTray) { state.comparisonTray.delete(String(removeTray.dataset.removeTray)); renderComparisonTray(); }
    const removeSavedButton = event.target.closest("[data-remove-saved]"); if (removeSavedButton) removeSaved(removeSavedButton.dataset.removeSaved);
    const removeSkill = event.target.closest("[data-remove-skill]"); if (removeSkill) { state.skills.splice(Number(removeSkill.dataset.removeSkill), 1); renderSkillTags(); }
    const addSuggested = event.target.closest("[data-add-skill]"); if (addSuggested) addSkill(addSuggested.dataset.addSkill);
    const challenge = event.target.closest("[data-toggle-challenge]"); if (challenge) {
      event.preventDefault();
      event.stopPropagation();
      const card = challenge.closest(".path-card");
      const panel = card?.querySelector(".challenge-panel") || Array.from(document.querySelectorAll("[data-challenge-panel]")).find((candidate) => candidate.dataset.challengePanel === String(challenge.dataset.toggleChallenge));
      if (panel) {
        panel.classList.toggle("hidden");
        challenge.setAttribute("aria-expanded", String(!panel.classList.contains("hidden")));
        if (!panel.classList.contains("hidden")) panel.scrollIntoView({ behavior: cp5MotionBehavior(), block: "nearest" });
      }
    }
    const evidence = event.target.closest("[data-evidence-soc]"); if (evidence) openCareerEvidence(evidence.dataset.evidenceSoc);
    const editPath = event.target.closest("[data-edit-path]"); if (editPath) { $("#pathForm")?.classList.remove("hidden"); $("#pathInterpretation")?.classList.add("hidden"); cp5SetPathStep("about"); $("#pathForm")?.scrollIntoView({ behavior: cp5MotionBehavior(), block: "start" }); }
    const quick = event.target.closest("[data-quick-question]"); if (quick) { const question = quick.dataset.quickQuestion; $("#questionInput").value = question; switchWorkspace("ask"); runQuestion(question); }
    const degree = event.target.closest("[data-degree-code]"); if (degree) { switchWorkspace("degrees"); openDegree(degree.dataset.degreeCode); }
    const profileTab = event.target.closest("[data-profile-tab]"); if (profileTab) {
      const profile = profileTab.closest(".occupation-profile");
      $$('[data-profile-tab]', profile).forEach((button) => button.classList.toggle("active", button === profileTab));
      $$('[data-profile-panel]', profile).forEach((panel) => panel.classList.toggle("active", panel.dataset.profilePanel === profileTab.dataset.profileTab));
    }
    const location = event.target.closest("[data-location-soc]"); if (location) { const item = careerFromCache(location.dataset.locationSoc); $("#locationCareer").value = item?.occupation_title || ""; $("#locationCareer").dataset.soc = location.dataset.locationSoc; switchWorkspace("location"); runLocation(location.dataset.locationSoc); }
    const closeDrawer = event.target.closest("[data-close-drawer]"); if (closeDrawer) { $("#savedDrawer").classList.remove("open"); $("#savedDrawer").setAttribute("aria-hidden", "true"); }
    const closeModal = event.target.closest("[data-close-modal]"); if (closeModal) { const id = closeModal.dataset.closeModal === "evidence" ? "#evidenceModal" : "#methodologyModal"; $(id).classList.remove("open"); $(id).setAttribute("aria-hidden", "true"); }
  });
  document.addEventListener("keydown", (event) => {
    const row = event.target.closest("[data-open-soc]");
    if (row && (event.key === "Enter" || event.key === " ")) { event.preventDefault(); openOccupation(row.dataset.openSoc); }
  });
}

async function loadInitialData() {
  try {
    const [bootstrap, home, universe] = await Promise.all([
      api("/api/bootstrap"), api("/api/home"), api("/api/universe?limit=5"),
    ]);
    state.bootstrap = {
      ...bootstrap,
      stats: normalizeStatsPayload(bootstrap.stats),
      sources: (bootstrap.sources || bootstrap.catalog?.sources || []).map(normalizeSourcePayload),
      interests: bootstrap.interests || bootstrap.interest_options || [],
      question_catalog: (bootstrap.question_catalog || []).flatMap((group) =>
        group?.examples ? group.examples.map((question) => ({ category: group.category, question })) : [group]
      ),
    };
    state.home = normalizeHomePayload(home);
    state.universe = normalizeUniversePayload(universe);
    if (state.lastPath) state.lastPath = normalizePathPayload(state.lastPath);
    renderStats(); renderInterestChips(); renderSkillTags(); fillStateSelects(state.bootstrap.states || []); renderQuickQuestions(); renderSources(); renderQuestionLibrary(); renderHome();
    state.home.path?.results?.forEach(cacheCareer);
    if (state.lastPath?.results) state.lastPath.results.forEach(cacheCareer);
    state.saved.forEach(cacheCareer);
    renderSavedCounts(); renderSavedDrawer(); renderSavedWorkspace();
    $("#profileText").value = "I like electronics and programming, but I am also interested in law. I want to stay near Maryland, earn at least $90,000, and stop at a bachelor's degree.";
  } catch (error) {
    console.error(error);
    showToast(`CareerProof could not load: ${error.message}`);
    $("#homeMatches").innerHTML = `<div class="refusal-card"><h2>Data load failed</h2><p>${escapeHTML(error.message)}</p></div>`;
  }
}

function init() {
  bindNavigation(); bindGlobalSearch(); bindFormsAndControls(); bindDelegatedActions();
  renderWeightControls("pathWeights", state.pathWeights, updatePathWeightTotal); updatePathWeightTotal();
  renderWeightControls("compareWeights", state.compareWeights);
  renderCompareSlots(); renderInterestChips(); renderSkillTags(); renderSavedCounts();
  loadInitialData();
}


/* ========================================================================== */
/* CareerProof AI 5.0 approved redesign overrides                             */
/* ========================================================================== */

const CP5_ACCENTS = ["#7760ff", "#2f8cff", "#23b9a9", "#e7a847", "#ef6b6b", "#26b9d4", "#43ba78", "#b86ae8"];
const CP5_CATEGORY_VISUALS = {
  "Engineering & Technology": { color: "#2687ff", secondary: "#47c8ff", material: "ocean" },
  "Communications & Creative": { color: "#a45cff", secondary: "#e18cff", material: "violet" },
  "Law, Policy & Government": { color: "#ee9b45", secondary: "#ffc66b", material: "amber" },
  "Business & Finance": { color: "#e4b44e", secondary: "#ffe08a", material: "gold" },
  "Health & Human Services": { color: "#ed665c", secondary: "#ff9b72", material: "coral" },
  "Science & Research": { color: "#20bca8", secondary: "#6be7d0", material: "teal" },
  "Education": { color: "#40b978", secondary: "#82e4a7", material: "green" },
  "Skilled Trades & Operations": { color: "#27c1d9", secondary: "#7ae9f1", material: "cyan" },
};

function cp5Icon(name, extra = "") {
  return `<svg class="${extra}" aria-hidden="true"><use href="#i-${name}"></use></svg>`;
}

function cp5MotionBehavior() {
  return matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth";
}

function cp5SetPathStep(step) {
  const order = ["about", "priorities", "interpretation", "results"];
  const index = Math.max(0, order.indexOf(step));
  $$('[data-path-stage]').forEach((button, i) => {
    button.classList.toggle("active", i === index);
    button.classList.toggle("complete", i < index);
  });
  const form = $("#pathForm");
  if (form) form.dataset.stage = step === "priorities" ? "priorities" : "about";
}

function renderStats() {
  const stats = state.bootstrap?.stats || {};
  const items = [
    ["occupation", `${formatNumber(stats.occupations || 0)}+`, "Occupations", "Official SOC-linked profiles"],
    ["location", `${compactNumber(stats.state_occupation_records || 0, 0)}+`, "Location records", "Published state estimates"],
    ["degree", `${compactNumber(stats.degree_relationships || 0, 1)}+`, "Degree links", "Qualitative CIP-to-SOC paths"],
    ["evidence", `${formatNumber(stats.source_families || 0)}`, "Source families", "Official public datasets"],
    ["check", "100%", "Inspectable", "Every recommendation shows its proof"],
  ];
  const grid = $("#statsGrid");
  if (!grid) return;
  grid.innerHTML = items.map(([icon, value, label, detail]) => `
    <article class="stat-card">
      <span class="stat-icon">${cp5Icon(icon)}</span>
      <strong>${escapeHTML(value)}</strong>
      <small>${escapeHTML(label)}<em>${escapeHTML(detail)}</em></small>
    </article>`).join("");
}

function renderSnapshot(profile = getStoredProfile()) {
  const interests = profile.interests?.length ? profile.interests : [...state.selectedInterests];
  const skills = profile.skills?.length ? profile.skills : state.skills;
  const rows = [
    ["spark", "Interests", interests.slice(0, 4).join(", ") || "Not set"],
    ["degree", "Education goal", profile.education_max || "No limit"],
    ["location", "Location", profile.preferred_state || "Any state"],
    ["chart", "Salary target", profile.salary_goal ? `${money(profile.salary_goal)}+` : "No minimum"],
    ["bridge", "Strengths", (skills || []).slice(0, 4).join(", ") || "Not set"],
  ];
  const container = $("#homeSnapshot");
  if (!container) return;
  container.querySelectorAll(".snapshot-list,.snapshot-update,.snapshot-loading").forEach((node) => node.remove());
  container.insertAdjacentHTML("beforeend", `<div class="snapshot-list">${rows.map(([icon, label, value]) => `
    <div class="snapshot-item"><span>${cp5Icon(icon)}</span><div><small>${escapeHTML(label)}</small><strong>${escapeHTML(value)}</strong></div></div>`).join("")}</div>
    <button class="snapshot-update" data-workspace-jump="path">${cp5Icon("edit")} Refine profile</button>`);
  cp5RenderPathInputSummary(profile);
}

function renderHome() {
  if (!state.home) return;
  renderSnapshot(state.home.profile);
  renderHomeMatches(state.home.path?.results || state.home.top_matches || []);
  renderHomeImpact(state.home.path?.results?.[0]);
  renderHomeOpportunities(state.home.path?.results || []);
  renderHomeFreshness(state.home.freshness);
}

function renderHomeUniversePreview() { /* Universe visuals remain exclusive to Career Universe. */ }

function renderHomeMatches(results) {
  results.forEach(cacheCareer);
  const top = results[0];
  const container = $("#homeMatches");
  if (!container) return;
  if (!top) {
    container.innerHTML = `<div class="empty-state"><h3>Build your first path</h3><p>Add your preferences to create an evidence-backed match.</p></div>`;
    return;
  }
  const runner = results.slice(1, 3);
  container.innerHTML = `
    <article class="home-match-row featured-home-match" data-open-soc="${top.soc_code}" tabindex="0">
      <span class="match-rank">01</span>
      <div class="home-match-title">
        <span class="match-eyebrow">Best current fit</span>
        <h3>${escapeHTML(top.occupation_title)}</h3>
        <p>${escapeHTML((top.why || [top.description]).slice(0, 2).join(" · ") || "Official occupation evidence")}</p>
        <div class="match-badges"><span class="match-badge verified">${escapeHTML(top.resilience_label)} resilience</span><span class="match-badge">${escapeHTML(top.education || "Education varies")}</span></div>
      </div>
      <div class="home-match-score"><strong>${Math.round(top.score || 0)}%</strong><small>profile fit</small></div>
      <div class="match-metric"><strong>${money(top.median_wage, true)}</strong><small>median wage</small></div>
      <div class="match-metric"><strong>${pct(top.growth_percent)}</strong><small>growth</small></div>
      <button class="bookmark-button" data-save-soc="${top.soc_code}" aria-label="Save ${escapeHTML(top.occupation_title)}">${cp5Icon("bookmark")}</button>
    </article>
    ${runner.length ? `<div class="home-runner-list">${runner.map((item, index) => `<button data-open-soc="${item.soc_code}"><span>0${index + 2}</span><strong>${escapeHTML(item.occupation_title)}</strong><small>${Math.round(item.score || 0)}% fit · ${money(item.median_wage, true)}</small></button>`).join("")}</div>` : ""}`;
}

function renderHomeImpact(item) {
  const container = $("#homeImpact");
  if (!container) return;
  const impact = item?.resilience_profile?.ai_task_impact || {};
  const human = Number(impact.human_led?.count || 0);
  const augmented = Number(impact.ai_augmented?.count || 0);
  const reduced = Number(impact.routine_reduced?.count || 0);
  const total = Math.max(human + augmented + reduced, 1);
  const humanPct = Math.round(human / total * 100);
  const augmentedPct = Math.round(augmented / total * 100);
  const reducedPct = Math.max(0, 100 - humanPct - augmentedPct);
  const resilience = Math.round(item?.resilience_score || 0);
  container.innerHTML = `
    <div class="impact-donut" style="--augmented:${augmentedPct}%;--transformed:${augmentedPct + humanPct}%;--automatable:100%"><div><span><strong>${resilience || "—"}</strong><small>resilience</small></span></div></div>
    <div class="impact-legend">
      <div><i class="human"></i><span>Human-led responsibility</span><strong>${humanPct}%</strong></div>
      <div><i class="augment"></i><span>AI augmentation potential</span><strong>${augmentedPct}%</strong></div>
      <div><i class="routine"></i><span>Routine exposure signals</span><strong>${reducedPct}%</strong></div>
      <p class="impact-takeaway"><b>${escapeHTML(item?.occupation_title || "Top match")}</b> is strongest where judgment, accountability, and real-world work remain central.</p>
    </div>
    <p class="impact-note">CareerProof classifies official O*NET task statements for explanation. It does not predict job loss.</p>`;
}

function renderHomeOpportunities(results) {
  const container = $("#homeOpportunities");
  if (!container) return;
  const rows = results.filter((item) => item.state_match).slice(0, 3);
  container.innerHTML = rows.length ? rows.map((item, index) => `
    <button class="opportunity-row" data-open-soc="${item.soc_code}">
      <span class="opportunity-rank">${index + 1}</span><strong>${escapeHTML(item.occupation_title)}</strong>
      <small>${escapeHTML(item.state_match?.state || "Preferred state")} · ${money(item.state_match?.median_wage, true)} · ${compactNumber(item.state_match?.employment, 1)} workers</small>
      <b class="confidence-chip">${escapeHTML(item.decision_confidence?.label || "Published")}</b>
    </button>`).join("") : `<p class="muted-copy">State-level rows were not published for the visible top matches.</p>`;
}

function renderHomeFreshness(freshness) {
  const container = $("#homeFreshness");
  if (!container || !freshness) return;
  container.innerHTML = `${cp5Icon("clock")}<div><strong>Source years stay visible.</strong> ${escapeHTML(freshness.summary || "Wages, outlook, skills, and price levels retain their official measurement periods.")}</div><button data-workspace-jump="trust">Inspect evidence →</button>`;
}

function cp5SvgElement(tag, attrs = {}, text = "") {
  const element = document.createElementNS(SVG_NS, tag);
  Object.entries(attrs).forEach(([key, value]) => element.setAttribute(key, String(value)));
  if (text) element.textContent = text;
  return element;
}

function cp5UniverseDefs(svg) {
  const defs = cp5SvgElement("defs");
  const star = cp5SvgElement("radialGradient", { id: "cpStar", cx: "45%", cy: "40%" });
  star.append(cp5SvgElement("stop", { offset: "0%", "stop-color": "#fff8cf" }), cp5SvgElement("stop", { offset: "42%", "stop-color": "#ffd75d" }), cp5SvgElement("stop", { offset: "100%", "stop-color": "#d67811" }));
  defs.appendChild(star);
  Object.entries(CP5_CATEGORY_VISUALS).forEach(([name, visual], index) => {
    const id = `planet-${index}`;
    const grad = cp5SvgElement("radialGradient", { id, cx: "32%", cy: "28%", r: "72%" });
    grad.append(cp5SvgElement("stop", { offset: "0%", "stop-color": visual.secondary }), cp5SvgElement("stop", { offset: "47%", "stop-color": visual.color }), cp5SvgElement("stop", { offset: "100%", "stop-color": "#050a14" }));
    defs.appendChild(grad);
    visual.gradientId = id;
  });
  const glow = cp5SvgElement("filter", { id: "softGlow", x: "-80%", y: "-80%", width: "260%", height: "260%" });
  glow.append(cp5SvgElement("feGaussianBlur", { stdDeviation: "8", result: "blur" }), cp5SvgElement("feMerge"));
  const merge = glow.lastChild;
  merge.append(cp5SvgElement("feMergeNode", { in: "blur" }), cp5SvgElement("feMergeNode", { in: "SourceGraphic" }));
  defs.appendChild(glow);
  const texture = cp5SvgElement("filter", { id: "planetTexture", x: "-20%", y: "-20%", width: "140%", height: "140%" });
  texture.append(cp5SvgElement("feTurbulence", { type: "fractalNoise", baseFrequency: ".035 .09", numOctaves: "3", seed: "17", result: "noise" }));
  texture.append(cp5SvgElement("feColorMatrix", { in: "noise", type: "saturate", values: "0", result: "mono" }));
  texture.append(cp5SvgElement("feComponentTransfer", { in: "mono", result: "textureAlpha" }));
  const transfer = texture.lastChild;
  transfer.append(cp5SvgElement("feFuncA", { type: "table", tableValues: "0 .42" }));
  texture.append(cp5SvgElement("feBlend", { in: "SourceGraphic", in2: "textureAlpha", mode: "soft-light" }));
  defs.appendChild(texture);
  svg.appendChild(defs);
}

function cp5PlanetNode(svg, category, x, y, radius, index) {
  const visual = CP5_CATEGORY_VISUALS[category.name] || { color: category.color || CP5_ACCENTS[index % CP5_ACCENTS.length], secondary: "#99b8ff", gradientId: `planet-${index}` };
  const group = cp5SvgElement("g", { class: "universe-planet-node", transform: `translate(${x} ${y})`, tabindex: "0", role: "button", "aria-label": `${category.name}, ${category.size} careers` });
  group.dataset.category = category.name;
  group.style.setProperty("--planet-color", visual.color);
  const orbit = cp5SvgElement("circle", { r: radius + 12, fill: "none", stroke: visual.color, "stroke-opacity": ".18", "stroke-width": "1" });
  const halo = cp5SvgElement("circle", { r: radius + 7, fill: visual.color, opacity: ".12", filter: "url(#softGlow)" });
  const body = cp5SvgElement("circle", { r: radius, fill: `url(#${visual.gradientId || `planet-${index}`})`, stroke: visual.secondary, "stroke-opacity": ".42", "stroke-width": "1.2" });
  const texture = cp5SvgElement("circle", { r: radius * .96, fill: `url(#${visual.gradientId || `planet-${index}`})`, opacity: ".7", filter: "url(#planetTexture)", class: "planet-surface" });
  const highlight = cp5SvgElement("ellipse", { cx: -radius * .27, cy: -radius * .28, rx: radius * .25, ry: radius * .16, fill: "#ffffff", opacity: ".14", transform: "rotate(-24)" });
  const shade = cp5SvgElement("ellipse", { cx: radius * .23, cy: radius * .02, rx: radius * .76, ry: radius, fill: "#02050b", opacity: ".31", transform: "rotate(-13)" });
  const band = cp5SvgElement("path", { d: `M ${-radius * .82} ${radius * .12} Q 0 ${radius * .38} ${radius * .82} ${radius * .04}`, fill: "none", stroke: visual.secondary, "stroke-opacity": ".22", "stroke-width": Math.max(2, radius * .12), "stroke-linecap": "round" });
  const label = cp5SvgElement("text", { y: radius + 26, "text-anchor": "middle", fill: "#f0f4ff", "font-size": "13", "font-weight": "700" }, category.name.replace(" & ", " + "));
  const sub = cp5SvgElement("text", { y: radius + 43, "text-anchor": "middle", fill: visual.secondary, "font-size": "11" }, `${category.size} careers`);
  group.append(orbit, halo, body, texture, band, highlight, shade, label, sub);
  svg.appendChild(group);
  const activate = () => {
    // Focus and zoom only. The planet never spins.
    $("#universeStage")?.classList.add("camera-zooming");
    window.setTimeout(() => openUniverseCategory(category.name), matchMedia("(prefers-reduced-motion: reduce)").matches ? 0 : 340);
  };
  group.addEventListener("click", activate);
  group.addEventListener("keydown", (event) => { if (event.key === "Enter" || event.key === " ") { event.preventDefault(); activate(); } });
  return group;
}

function clearUniverseReferenceHotspots() {
  document.querySelector("#universeStage .universe-reference-hotspots")?.remove();
  document.querySelector("#universeStage .universe-reference-field")?.remove();
  document.querySelector("#universeStage .universe-reference-career")?.remove();
}

function renderUniverseReferenceField(items = [], categoryName = "Career field") {
  const stage = $("#universeStage");
  if (!stage) return;
  document.querySelector("#universeStage .universe-reference-field")?.remove();
  const layer = document.createElement("div");
  layer.className = "universe-reference-field";
  layer.innerHTML = `<img class="reference-field-planet" src="/static/images/universe-field-planet.webp" alt=""><div class="reference-field-title"><strong>${escapeHTML(categoryName)}</strong><small>${items.length} visible career moons</small></div>`;
  items.slice(0, 8).forEach((item, index) => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "reference-moon";
    button.dataset.index = String(index);
    button.setAttribute("aria-label", `Open ${item.occupation_title}`);
    button.innerHTML = `<strong>${escapeHTML(item.occupation_title)}</strong><small>${Math.round(item.resilience_score || 0)} resilience</small>`;
    button.addEventListener("click", () => showUniverseOccupation(item.soc_code));
    layer.appendChild(button);
  });
  stage.appendChild(layer);
}

function renderUniverseReferenceCareer(profile) {
  const stage = $("#universeStage");
  if (!stage) return;
  document.querySelector("#universeStage .universe-reference-career")?.remove();
  const layer = document.createElement("div");
  layer.className = "universe-reference-career";
  layer.innerHTML = `<img class="reference-career-moon" src="/static/images/universe-career-moon.webp" alt=""><div class="reference-career-copy"><strong>${escapeHTML(profile.occupation_title)}</strong><small>${Math.round(profile.resilience_score || 0)} resilience · SOC ${escapeHTML(profile.soc_code)}</small></div>`;
  stage.appendChild(layer);
}

function renderUniverseReferenceHotspots(categories = []) {
  clearUniverseReferenceHotspots();
  const stage = $("#universeStage");
  if (!stage) return;
  const layer = document.createElement("div");
  layer.className = "universe-reference-hotspots";
  categories.slice(0, 8).forEach((category, index) => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "universe-hotspot";
    button.dataset.index = String(index);
    button.setAttribute("aria-label", `Explore ${category.name}, ${category.size} careers`);
    button.title = `Explore ${category.name}`;
    button.addEventListener("click", () => {
      stage.classList.add("camera-zooming");
      window.setTimeout(() => openUniverseCategory(category.name), matchMedia("(prefers-reduced-motion: reduce)").matches ? 0 : 300);
    });
    layer.appendChild(button);
  });
  stage.appendChild(layer);
}

function renderUniverseRoot() {
  if (!state.universe) return;
  state.universeCategory = null;
  state.universeCategoryData = null;
  $("#universeBack").disabled = true;
  $("#universeReset").disabled = false;
  const overviewStage = $("#universeStage");
  overviewStage?.classList.remove("camera-zooming", "career-focused", "field-focused", "reference-field", "reference-career");
  overviewStage?.classList.add("reference-overview");
  clearUniverseReferenceHotspots();
  clearUniverse();
  const svg = $("#universeSvg");
  cp5UniverseDefs(svg);
  const center = { x: 480, y: 316 };
  const categories = state.universe.categories || [];
  renderUniverseReferenceHotspots(categories);
  [128, 205, 286].forEach((rx, index) => svg.appendChild(cp5SvgElement("ellipse", { cx: center.x, cy: center.y, rx, ry: rx * .66, fill: "none", stroke: "#5976aa", "stroke-opacity": index === 1 ? ".18" : ".11", "stroke-width": "1", "stroke-dasharray": index === 2 ? "3 7" : "none" })));
  const sunGroup = cp5SvgElement("g", { class: "profile-sun", transform: `translate(${center.x} ${center.y})` });
  sunGroup.append(cp5SvgElement("circle", { r: 73, fill: "#e3981b", opacity: ".12", filter: "url(#softGlow)" }), cp5SvgElement("circle", { r: 55, fill: "url(#cpStar)", stroke: "#ffe99a", "stroke-width": "1.5" }), cp5SvgElement("text", { y: "-2", "text-anchor": "middle", fill: "#1e1300", "font-size": "14", "font-weight": "800" }, "YOUR PROFILE"), cp5SvgElement("text", { y: "17", "text-anchor": "middle", fill: "#4a2a00", "font-size": "11", "font-weight": "700" }, "evidence center"));
  svg.appendChild(sunGroup);
  categories.forEach((category, index) => {
    const angle = -Math.PI / 2 + index * (Math.PI * 2 / categories.length) + (index % 2 ? .09 : -.04);
    const ring = index % 3 === 0 ? 278 : index % 3 === 1 ? 222 : 168;
    const x = center.x + Math.cos(angle) * ring;
    const y = center.y + Math.sin(angle) * ring * .68;
    cp5PlanetNode(svg, category, x, y, index % 3 === 0 ? 34 : 29, index);
  });
  $("#universeDetail").innerHTML = `<div class="detail-empty universe-intro"><span class="detail-kicker">Your career universe</span><h3>Choose a field to move closer.</h3><p>Every planet represents a CareerProof category. The careers and numbers behind it remain connected to official SOC, BLS, O*NET, Census, BEA, and NCES records.</p><div class="universe-intro-stats"><div><strong>${formatNumber(state.universe.occupation_count || 830)}</strong><small>occupations</small></div><div><strong>8</strong><small>career fields</small></div><div><strong>Fixed</strong><small>career moons</small></div></div><p class="universe-boundary">The category map is a visual navigation system, not a prediction or causal pathway.</p></div>`;
  cp5RenderUniverseFallback();
}

function cp5RenderUniverseFallback() {
  const fallback = $("#universeListFallback");
  if (!fallback || !state.universe) return;
  fallback.innerHTML = `<div class="list-fallback-head"><div><span class="section-kicker">Accessible list view</span><h2>Career fields</h2></div><button id="closeUniverseList" class="outline-button">Return to universe</button></div><div class="universe-field-list">${(state.universe.categories || []).map((category) => `<button data-universe-list-category="${escapeHTML(category.name)}"><i style="background:${CP5_CATEGORY_VISUALS[category.name]?.color || category.color}"></i><span><strong>${escapeHTML(category.name)}</strong><small>${formatNumber(category.size)} occupations · ${money(category.median_wage, true)} typical field median</small></span><b>Explore →</b></button>`).join("")}</div>`;
  $$('[data-universe-list-category]', fallback).forEach((button) => button.addEventListener("click", () => openUniverseCategory(button.dataset.universeListCategory)));
  $("#closeUniverseList")?.addEventListener("click", () => { fallback.classList.add("hidden"); $("#universeStage")?.classList.remove("hidden"); });
}

function renderUniverseCategory(data, filters = {}) {
  clearUniverseReferenceHotspots();
  clearUniverse();
  $("#universeStage")?.classList.remove("reference-overview", "reference-career", "camera-zooming", "career-focused");
  $("#universeStage")?.classList.add("field-focused", "reference-field");
  const svg = $("#universeSvg");
  cp5UniverseDefs(svg);
  let occupations = data.occupations || [];
  const minSalary = Number(filters.salary || 0);
  const education = filters.education || "";
  const resilience = Number(filters.resilience || 0);
  occupations = occupations.filter((item) => (!minSalary || Number(item.median_wage || 0) >= minSalary) && (!education || item.education === education) && (!resilience || Number(item.resilience_score || 0) >= resilience));
  const displayed = occupations.slice(0, 12);
  renderUniverseReferenceField(displayed, data.name);
  const center = { x: 470, y: 316 };
  const visual = CP5_CATEGORY_VISUALS[data.name] || { color: data.color || "#487cff", secondary: "#8db4ff", gradientId: "planet-0" };
  const category = { name: data.name, size: occupations.length, color: visual.color };
  cp5PlanetNode(svg, category, center.x, center.y, 87, 0).removeAttribute("data-category");
  const centerNode = svg.querySelector(".universe-planet-node:last-of-type");
  if (centerNode) { centerNode.style.pointerEvents = "none"; centerNode.querySelectorAll("text").forEach((node) => node.remove()); }
  displayed.forEach((item, index) => {
    const angle = -Math.PI / 2 + index * (Math.PI * 2 / Math.max(displayed.length, 1));
    const ring = index % 2 ? 242 : 186;
    const x = center.x + Math.cos(angle) * ring;
    const y = center.y + Math.sin(angle) * ring * .72;
    const line = cp5SvgElement("line", { x1: center.x, y1: center.y, x2: x, y2: y, stroke: visual.color, "stroke-opacity": ".12", "stroke-dasharray": "3 7" });
    svg.insertBefore(line, centerNode || null);
    const moon = cp5SvgElement("g", { class: "career-moon-node", transform: `translate(${x} ${y})`, tabindex: "0", role: "button", "aria-label": `${item.occupation_title}, ${Math.round(item.resilience_score)} resilience` });
    moon.dataset.soc = item.soc_code;
    const radius = 18 + Math.min(10, Number(item.score || item.resilience_score || 0) / 18);
    moon.append(cp5SvgElement("circle", { r: radius + 6, fill: visual.color, opacity: ".08" }), cp5SvgElement("circle", { r: radius, fill: `url(#${visual.gradientId || "planet-0"})`, stroke: visual.secondary, "stroke-opacity": ".55" }), cp5SvgElement("circle", { r: radius * .96, fill: `url(#${visual.gradientId || "planet-0"})`, opacity: ".72", filter: "url(#planetTexture)", class: "planet-surface" }), cp5SvgElement("ellipse", { cx: 5, cy: 1, rx: radius * .72, ry: radius, fill: "#02050b", opacity: ".35" }));
    const words = String(item.occupation_title).split(" ").slice(0, 4);
    const label = cp5SvgElement("text", { y: radius + 20, "text-anchor": "middle", fill: "#e8efff", "font-size": "10.5", "font-weight": "700" });
    words.forEach((word, i) => label.appendChild(cp5SvgElement("tspan", { x: 0, dy: i ? 11 : 0 }, word)));
    moon.appendChild(label);
    const activate = () => showUniverseOccupation(item.soc_code);
    moon.addEventListener("click", activate);
    moon.addEventListener("keydown", (event) => { if (event.key === "Enter" || event.key === " ") { event.preventDefault(); activate(); } });
    svg.appendChild(moon);
  });
  const educationOptions = [...new Set((data.occupations || []).map((item) => item.education).filter(Boolean))].sort();
  $("#universeDetail").innerHTML = `
    <div class="field-detail-head"><span class="field-swatch" style="--field:${visual.color}"></span><div><span class="section-kicker">Selected field</span><h2>${escapeHTML(data.name)}</h2><p>${escapeHTML(data.description || "Explore careers connected by official occupation evidence.")}</p></div></div>
    <div class="field-filter-grid"><label>Minimum wage<input id="universeSalaryFilter" type="number" step="10000" value="${minSalary || ""}" placeholder="90000"></label><label>Education<select id="universeEducationFilter"><option value="">Any education</option>${educationOptions.map((value) => `<option ${value === education ? "selected" : ""}>${escapeHTML(value)}</option>`).join("")}</select></label><label>Resilience<select id="universeResilienceFilter"><option value="0">Any profile</option><option value="55" ${resilience === 55 ? "selected" : ""}>Moderate+</option><option value="70" ${resilience === 70 ? "selected" : ""}>Strong+</option><option value="82" ${resilience === 82 ? "selected" : ""}>Very strong</option></select></label></div>
    <div class="field-count"><strong>${occupations.length}</strong><span>careers match these filters</span></div>
    <div class="universe-list">${occupations.slice(0, 10).map((item) => `<button data-universe-soc="${item.soc_code}"><span><strong>${escapeHTML(item.occupation_title)}</strong><small>${money(item.median_wage, true)} · ${pct(item.growth_percent)} growth</small></span><b>${Math.round(item.resilience_score)}<small>resilience</small></b></button>`).join("")}</div>
    <p class="universe-boundary">Career moons stay fixed to support readable selection and keyboard access. Their position does not represent rank.</p>`;
  const applyFilters = debounce(() => renderUniverseCategory(data, { salary: $("#universeSalaryFilter")?.value, education: $("#universeEducationFilter")?.value, resilience: $("#universeResilienceFilter")?.value }), 180);
  $("#universeSalaryFilter")?.addEventListener("input", applyFilters);
  $("#universeEducationFilter")?.addEventListener("change", applyFilters);
  $("#universeResilienceFilter")?.addEventListener("change", applyFilters);
  $$('[data-universe-soc]', $("#universeDetail")).forEach((button) => button.addEventListener("click", () => showUniverseOccupation(button.dataset.universeSoc)));
}

async function showUniverseOccupation(socCode) {
  clearUniverseReferenceHotspots();
  $("#universeStage")?.classList.remove("reference-overview", "camera-zooming");
  $("#universeDetail").innerHTML = `<div class="loading-card"><span class="spinner"></span><p>Joining wage, outlook, skills, education, and resilience evidence…</p></div>`;
  try {
    const data = normalizeOccupationPayload(await api(`/api/occupation/${encodeURIComponent(socCode)}`));
    cacheCareer(data.profile);
    const p = data.profile;
    const visual = CP5_CATEGORY_VISUALS[p.category] || { color: "#4f79ff", secondary: "#90b0ff" };
    $("#universeStage")?.classList.remove("field-focused", "reference-field");
    $("#universeStage")?.classList.add("career-focused", "reference-career");
    renderUniverseReferenceCareer(p);
    const svg = $("#universeSvg");
    svg.innerHTML = "";
    cp5UniverseDefs(svg);
    const group = cp5SvgElement("g", { class: "career-profile-orb", transform: "translate(480 315)" });
    group.append(cp5SvgElement("circle", { r: 145, fill: visual.color, opacity: ".09", filter: "url(#softGlow)" }), cp5SvgElement("circle", { r: 112, fill: `url(#${CP5_CATEGORY_VISUALS[p.category]?.gradientId || "planet-0"})`, stroke: visual.secondary, "stroke-width": "1.4", "stroke-opacity": ".55" }), cp5SvgElement("ellipse", { cx: 26, cy: 3, rx: 89, ry: 112, fill: "#02050b", opacity: ".39" }), cp5SvgElement("text", { y: 158, "text-anchor": "middle", fill: "#f3f6ff", "font-size": "19", "font-weight": "750" }, p.occupation_title), cp5SvgElement("text", { y: 181, "text-anchor": "middle", fill: visual.secondary, "font-size": "12" }, `SOC ${p.soc_code} · ${p.resilience_label} resilience`));
    svg.appendChild(group);
    $("#universeDetail").innerHTML = `
      <span class="section-kicker">Full career profile</span><h2>${escapeHTML(p.occupation_title)}</h2><p>${escapeHTML(p.description || "")}</p>
      <div class="detail-kpis"><div><small>Median wage</small><strong>${money(p.median_wage)}</strong></div><div><small>Growth</small><strong>${pct(p.growth_percent)}</strong></div><div><small>Annual openings</small><strong>${compactNumber(p.annual_openings)}</strong></div><div><small>AI resilience</small><strong>${Math.round(p.resilience_score)} · ${escapeHTML(p.resilience_label)}</strong></div></div>
      <div class="career-profile-reasons"><strong>Why this career can remain valuable</strong>${Object.values(data.resilience_profile?.dimensions || {}).sort((a,b) => b.score-a.score).slice(0,3).map((dimension) => `<div><span>${escapeHTML(dimension.label)}</span><b>${Math.round(dimension.score)}</b></div>`).join("")}</div>
      <div class="detail-actions"><button class="primary-button" data-open-soc="${p.soc_code}">Open complete evidence profile</button><button class="outline-button" data-tray-soc="${p.soc_code}">Compare</button><button class="outline-button" data-save-soc="${p.soc_code}">Save</button></div>
      <button class="soft-button" id="backToUniverseCategory">← Back to ${escapeHTML(state.universeCategory || p.category)}</button>`;
    $("#backToUniverseCategory")?.addEventListener("click", () => renderUniverseCategory(state.universeCategoryData));
  } catch (error) {
    $("#universeDetail").innerHTML = `<div class="error-card">${escapeHTML(error.message)}</div>`;
  }
}

function cp5RenderPathInputSummary(profile = pathPayload()) {
  const container = $("#pathInputSummary");
  if (!container) return;
  const rows = [
    ["spark", "Interests", (profile.interests || [...state.selectedInterests]).slice(0, 4).join(", ") || "Not set"],
    ["bridge", "Skills", (profile.skills || state.skills).slice(0, 4).join(", ") || "Not set"],
    ["degree", "Education", profile.education_max || "No limit"],
    ["location", "Location", profile.preferred_state || "Any state"],
    ["chart", "Salary", profile.salary_goal ? `${money(profile.salary_goal)}+` : "No minimum"],
  ];
  container.innerHTML = rows.map(([icon, label, value]) => `<div class="input-summary-item"><span>${cp5Icon(icon)}</span><div><small>${escapeHTML(label)}</small><strong>${escapeHTML(value)}</strong></div></div>`).join("");
}

function renderInterpretation(data) {
  state.lastInterpretation = data;
  cp5SetPathStep("interpretation");
  const warnings = data.warnings || [];
  const review = data.input_review || {};
  const container = $("#pathInterpretation");
  container.classList.remove("hidden");
  container.innerHTML = `
    <article class="interpretation-card cp5-interpretation">
      <header><div><span class="section-kicker">Step 3 · confirm the AI interpretation</span><h2>${escapeHTML(data.goal)}</h2><p>${escapeHTML(data.interpretation_summary)}</p></div><span class="interpretation-status ${warnings.length ? "review" : "clear"}">${warnings.length ? `${warnings.length} item${warnings.length === 1 ? "" : "s"} to review` : "Inputs look consistent"}</span></header>
      ${review.corrections?.length ? `<div class="input-repair-banner">${cp5Icon("check")}<div><strong>Likely input mistakes repaired for review</strong><p>${review.corrections.map((item) => `${escapeHTML(item.from)} → ${escapeHTML(item.to)}`).join(" · ")}</p></div></div>` : ""}
      <div class="interpretation-grid">
        <section class="interpretation-section"><h3>What CareerProof understood</h3><div class="interpretation-chip-list">${(data.interests || []).map((item) => `<span>${escapeHTML(item)}</span>`).join("") || "<span>No interests detected</span>"}</div><h3>Existing strengths</h3><div class="interpretation-chip-list">${(data.skills || []).map((item) => `<span>${escapeHTML(item)}</span>`).join("") || "<span>No skills listed</span>"}</div></section>
        <section class="interpretation-section"><h3>Constraints</h3>${(data.constraints || []).map((item) => `<p><strong>${escapeHTML(item.label)}</strong><span>${escapeHTML(item.value)}</span>${item.hard ? '<b class="feasibility-chip blocked">Hard</b>' : '<b class="feasibility-chip tradeoff">Preference</b>'}</p>`).join("")}</section>
        <section class="interpretation-section priority-review"><h3>Ranking priorities</h3>${(data.priorities || []).slice(0, 8).map((item) => `<div class="priority-row"><span>${escapeHTML(item.label)}</span><i><b style="width:${item.weight * 2}%"></b></i><strong>${item.weight}%</strong></div>`).join("")}</section>
        <section class="interpretation-section"><h3>Human-error checks</h3>${(review.checks || ["Required inputs validated", "Conflicting settings reviewed", "No user choice silently changed"]).map((item) => `<div class="review-check">${cp5Icon("check")}<span>${escapeHTML(item)}</span></div>`).join("")}</section>
      </div>
      ${warnings.map((warning) => `<div class="warning-line">${cp5Icon("warning")}<span>${escapeHTML(warning)}</span></div>`).join("")}
      <div class="interpretation-actions"><button id="editInterpretation" class="outline-button">← Edit inputs</button><button id="confirmInterpretation" class="primary-button"><span>Confirm and calculate</span><b>→</b></button></div>
    </article>`;
  $("#editInterpretation")?.addEventListener("click", () => { cp5SetPathStep("about"); container.classList.add("hidden"); $("#pathForm")?.scrollIntoView({ behavior: cp5MotionBehavior(), block: "start" }); });
  $("#confirmInterpretation")?.addEventListener("click", runPathBuilder);
  container.scrollIntoView({ behavior: cp5MotionBehavior(), block: "start" });
}

async function reviewPathInterpretation() {
  const button = $("#pathForm button[type=submit]");
  setButtonLoading(button, true, "Reviewing inputs and possible human errors…");
  cp5RenderPathInputSummary(pathPayload());
  try {
    const data = normalizeInterpretationPayload(await api("/api/interpret-profile", { method: "POST", body: JSON.stringify(pathPayload()) }));
    renderInterpretation(data);
  } catch (error) { showToast(error.message); }
  finally { setButtonLoading(button, false); }
}

async function runPathBuilder() {
  const button = $("#confirmInterpretation");
  setButtonLoading(button, true, "Validating and ranking 830 occupations…");
  $("#pathResults").innerHTML = `<div class="empty-intelligence calculation-loader"><span class="spinner"></span><h2>Building your evidence-backed ranking</h2><ol><li>Applying hard constraints</li><li>Calculating transparent score components</li><li>Checking sensitivity and competing paths</li><li>Joining visible evidence</li></ol></div>`;
  try {
    const payload = { ...pathPayload(), confirmed_interpretation: true, limit: 8 };
    const data = normalizePathPayload(await api("/api/path-builder", { method: "POST", body: JSON.stringify(payload) }));
    state.lastPath = data;
    safeStorage.setItem("careerproof-last-path", JSON.stringify(data));
    renderPathResults(data);
    renderSnapshot(data.interpretation?.normalized_profile || payload);
    cp5RenderPathInputSummary(data.interpretation?.normalized_profile || payload);
    cp5SetPathStep("results");
    $("#pathForm")?.classList.add("hidden");
    $("#pathInterpretation")?.classList.add("hidden");
  } catch (error) {
    $("#pathResults").innerHTML = `<div class="refusal-card"><span class="refusal-badge">Calculation stopped safely</span><h2>Review the inputs</h2><p>${escapeHTML(error.message)}</p><button class="outline-button" data-workspace-jump="path">Return to inputs</button></div>`;
  } finally { setButtonLoading(button, false); }
}

function cp5ToggleChallenge(button, event) {
  event?.preventDefault();
  event?.stopImmediatePropagation();
  const panel = button?.closest(".path-card")?.querySelector(".challenge-panel");
  if (!panel) return false;
  panel.classList.toggle("hidden");
  button.setAttribute("aria-expanded", String(!panel.classList.contains("hidden")));
  if (!panel.classList.contains("hidden")) panel.scrollIntoView({ behavior: cp5MotionBehavior(), block: "nearest" });
  return false;
}

function cp5OpenRecommendationEvidence(button, event) {
  event?.preventDefault();
  event?.stopImmediatePropagation();
  openCareerEvidence(button?.dataset?.evidenceSoc);
  return false;
}

function cp5PathResultCard(item, index) {
  cacheCareer(item);
  const reasons = (item.why || []).slice(0, 3);
  const accent = CP5_ACCENTS[index % CP5_ACCENTS.length];
  const status = item.feasibility?.status || "review";
  return `<article class="path-card path-result-card" style="--result-accent:${accent}">
    <div class="result-rank">${String(index + 1).padStart(2, "0")}</div>
    <div class="score-ring" style="--score:${Math.round(item.score)}"><div><strong>${Math.round(item.score)}%</strong><small>fit</small></div></div>
    <span class="path-type">${escapeHTML(item.path_label || `Match ${index + 1}`)}</span>
    <h3>${escapeHTML(item.occupation_title)}</h3>
    <div class="path-result-quick-actions"><button type="button" data-toggle-challenge="${item.soc_code}" aria-expanded="false" onclick="return cp5ToggleChallenge(this, event)">Challenge result</button><button type="button" data-evidence-soc="${item.soc_code}" onclick="return cp5OpenRecommendationEvidence(this, event)">View evidence</button></div>
    <p class="result-description">${escapeHTML(item.description || "Official occupation profile")}</p>
    <div class="result-tag-row">${reasons.map((reason, reasonIndex) => `<span class="${reasonIndex ? "alt" : ""}">${escapeHTML(reason)}</span>`).join("")}</div>
    <div class="result-kpis"><div><small>Median wage</small><strong>${money(item.median_wage, true)}</strong></div><div><small>Growth</small><strong>${pct(item.growth_percent)}</strong></div><div><small>AI resilience</small><strong>${Math.round(item.resilience_score)} · ${escapeHTML(item.resilience_label)}</strong></div><div><small>Education</small><strong>${escapeHTML(item.education || "Not published")}</strong></div></div>
    <div class="constraint-result"><span class="feasibility-chip ${feasibilityClass(status)}">${escapeHTML(status)}</span><small>${escapeHTML(item.feasibility?.warnings?.[0] || item.feasibility?.hard_failures?.[0] || "Visible constraints checked")}</small></div>
    <div class="component-bars">${contributionRows(item)}</div>
    <div class="path-result-actions"><button type="button" data-tray-soc="${item.soc_code}">Compare</button><button type="button" data-save-soc="${item.soc_code}">Save</button><button type="button" class="primary-link" data-open-soc="${item.soc_code}">Full profile →</button></div>
    ${challengePanel(item)}
  </article>`;
}

function renderPathResults(data) {
  const results = data.results || [];
  const portfolio = data.portfolio || {};
  const sensitivity = data.sensitivity || [];
  const changes = data.what_would_change_recommendation || [];
  const top = results[0];
  if (!top) {
    $("#pathResults").innerHTML = `<div class="refusal-card"><h2>No supported path remained</h2><p>Relax one hard constraint or add more interests and skills.</p></div>`;
    return;
  }
  const portfolioRows = [["Primary path", portfolio.primary_path], ["Safer backup", portfolio.safer_backup], ["High upside", portfolio.high_upside_option], ["Fast entry", portfolio.fast_entry_option]];
  $("#pathResults").innerHTML = `
    <div class="path-results-head"><div><span class="section-kicker">Step 4 · evidence-backed results</span><h2>${escapeHTML(data.headline)}</h2><p>${escapeHTML(data.summary)}</p></div><div class="winner-confidence"><small>Decision confidence</small><strong>${escapeHTML(top.decision_confidence?.label || "Review")}</strong><span>${Math.round(top.decision_confidence?.score || 0)}/100</span><button class="outline-button" data-edit-path>Adjust inputs</button></div></div>
    <div class="path-results-v5">${results.slice(0, 3).map(cp5PathResultCard).join("")}</div>
    <div class="path-results-extra">
      <section class="path-details-panel"><header><div><span class="section-kicker">Portfolio strategy</span><h3>Do not depend on one path</h3></div></header><div class="portfolio-grid">${portfolioRows.map(([label, item]) => item ? `<button class="portfolio-item" data-open-soc="${item.soc_code}"><small>${escapeHTML(label)}</small><strong>${escapeHTML(item.occupation_title)}</strong><span>${Math.round(item.score)} fit · ${escapeHTML(item.resilience_label)}</span></button>` : `<div class="portfolio-item"><small>${escapeHTML(label)}</small><strong>Not available</strong><span>Adjust preferences</span></div>`).join("")}</div></section>
      <section class="path-details-panel"><header><div><span class="section-kicker">Counterfactuals</span><h3>What changes the winner?</h3></div></header><div class="sensitivity-list">${sensitivity.slice(0, 8).map((scenario) => `<div class="sensitivity-row"><span>${escapeHTML(scenario.label)}</span><strong>${escapeHTML(scenario.top_occupation || "No result")}</strong><b>${Number(scenario.top_score || 0).toFixed(1)}</b></div>`).join("")}</div></section>
    </div>
    <section class="recommendation-change-panel"><span class="section-kicker">Challenge the model</span><h3>Evidence that could change the recommendation</h3><div>${changes.slice(0, 4).map((item) => `<article><strong>${escapeHTML(item.condition || "Change a priority")}</strong><p>${escapeHTML(item.impact || "The ranking may change.")}</p></article>`).join("")}</div></section>
    <div class="data-vintage-inline">${cp5Icon("clock")}<div>${escapeHTML(data.freshness?.summary || "Official source periods remain visible and are not treated as one synchronized snapshot.")}</div></div>`;
  renderSavedWorkspace();
  $("#pathResults").scrollIntoView({ behavior: cp5MotionBehavior(), block: "start" });
}

function cp5CompareMetricRows(results) {
  const metrics = [
    ["salary", "Earnings", "median_wage", (v) => money(v, true)],
    ["growth", "Job growth", "growth_percent", (v) => pct(v)],
    ["resilience", "AI resilience", "resilience_score", (v) => `${Math.round(v || 0)}`],
    ["openings", "Annual openings", "annual_openings", (v) => compactNumber(v, 0)],
    ["education", "Education access", "education", (v) => String(v || "Not published")],
    ["location", "Location coverage", "state_coverage", (v) => `${formatNumber(v || 0)} areas`],
    ["stability", "Market stability", "stability_score", (v) => `${Math.round(v || 0)}`],
    ["fit", "Skills alignment", "score", (v) => `${Math.round(v || 0)}`],
  ];
  return metrics.map(([key, label, field, formatter]) => {
    let winnerIndex = 0;
    if (key === "education") winnerIndex = results.reduce((best, item, i) => Number(item.components?.education || 0) > Number(results[best]?.components?.education || 0) ? i : best, 0);
    else winnerIndex = results.reduce((best, item, i) => Number(item[field] || 0) > Number(results[best]?.[field] || 0) ? i : best, 0);
    return `<div class="comparison-row"><span>${escapeHTML(label)}</span>${results.slice(0, 3).map((item, index) => `<div class="metric-cell ${index === winnerIndex ? "round-winner" : ""}"><strong>${escapeHTML(formatter(item[field]))}</strong>${index === winnerIndex ? "<small>round winner</small>" : ""}</div>`).join("")}</div>`;
  }).join("");
}

function renderCompare(data) {
  state.lastCompare = data;
  const results = data.results || [];
  results.forEach(cacheCareer);
  if (results.length < 2) {
    $("#compareResults").innerHTML = `<div class="refusal-card"><h2>Add at least two valid careers</h2><p>The battle needs two supported occupation records.</p></div>`;
    return;
  }
  const winner = results[0];
  const runner = results[1];
  const gap = Number(data.tradeoff_summary?.score_gap ?? winner.score - runner.score);
  const closeBattle = gap < 3;
  const colors = ["#7058ff", "#2d92ff", "#20b69e", "#e1a742"];
  const cards = results.slice(0, 4).map((item, index) => `
    <article class="compare-career-card contender-card ${index === 0 ? "winner" : ""}" style="--contender:${colors[index]}">
      <span class="contender-rank">${index === 0 ? "WINNER" : `#${index + 1}`}</span><div class="contender-score"><strong>${Math.round(item.score)}</strong><small>overall</small></div>
      <h3>${escapeHTML(item.occupation_title)}</h3><p>${escapeHTML(item.category)}</p>
      <div class="contender-kpis"><div><small>Salary</small><strong>${money(item.median_wage, true)}</strong></div><div><small>Growth</small><strong>${pct(item.growth_percent)}</strong></div><div><small>Resilience</small><strong>${Math.round(item.resilience_score)}</strong></div></div>
      <span class="feasibility-chip ${feasibilityClass(item.feasibility?.status)}">${escapeHTML(item.feasibility?.status || "review")}</span>
      <button data-open-soc="${item.soc_code}">Inspect career →</button>
    </article>`).join("");
  $("#compareResults").innerHTML = `
    <article class="battle-arena card">
      <header class="battle-verdict"><div><span class="section-kicker">Evidence battle complete</span><h2>${escapeHTML(winner.occupation_title)} wins this setup</h2><p>${escapeHTML(data.tradeoff_summary?.plain_language || data.summary)}</p></div><div class="verdict-badge"><small>${closeBattle ? "Close decision" : "Current winner"}</small><strong>${Math.round(winner.score)}–${Math.round(runner.score)}</strong><span>${Math.abs(gap).toFixed(1)} point gap</span></div></header>
      <div class="arena-stage" style="--battle-count:${Math.min(results.length, 4)}"><div class="arena-beam left"></div>${cards}<div class="battle-vs">VS</div><div class="arena-beam right"></div></div>
      <div class="tradeoff-callout battle-summary-callout"><strong>Why ${escapeHTML(winner.occupation_title)} won</strong><p>${escapeHTML(data.tradeoff_summary?.plain_language || data.summary)}</p></div>
      <nav class="battle-tabs"><button class="active" data-battle-tab="overview">Overview</button><button data-battle-tab="tradeoffs">Tradeoffs</button><button data-battle-tab="scenarios">Scenarios</button><button data-battle-tab="evidence">Evidence</button></nav>
      <section class="battle-panel active" data-battle-panel="overview"><div class="battle-metric-table" style="--battle-cols:${Math.min(results.length, 3)}"><div class="battle-metric-head"><span>Battle category</span>${results.slice(0,3).map((item) => `<strong>${escapeHTML(item.occupation_title)}</strong>`).join("")}</div>${cp5CompareMetricRows(results)}</div></section>
      <section class="battle-panel" data-battle-panel="tradeoffs"><div class="battle-tradeoff-detail"><strong>Why ${escapeHTML(winner.occupation_title)} won</strong><p>${escapeHTML(data.tradeoff_summary?.plain_language || data.summary)}</p></div><div class="battle-tradeoff-grid"><article><h3>Winner advantages</h3>${(data.tradeoff_summary?.advantages || []).map((item) => `<div><span>${escapeHTML(titleCase(item.component))}</span><strong>+${Number(item.contribution_gap).toFixed(1)}</strong></div>`).join("")}</article><article><h3>Where the runner-up wins</h3>${(data.tradeoff_summary?.disadvantages || []).map((item) => `<div><span>${escapeHTML(titleCase(item.component))}</span><strong>${Number(item.contribution_gap).toFixed(1)}</strong></div>`).join("")}</article></div></section>
      <section class="battle-panel" data-battle-panel="scenarios"><div class="scenario-grid">${(data.sensitivity || []).map((scenario) => `<article><small>${escapeHTML(scenario.label)}</small><strong>${escapeHTML(scenario.top_occupation || "No result")}</strong><span>${Number(scenario.top_score || 0).toFixed(1)}</span></article>`).join("")}</div></section>
      <section class="battle-panel" data-battle-panel="evidence"><div class="evidence-box blue"><small>Formula</small><strong>${escapeHTML(data.formula || "Weighted sum of normalized score components")}</strong><p>Raw official values stay visible. CareerProof-derived scores reflect the selected priorities and constraints.</p></div><ul class="limitation-list">${(data.limitations || []).map((item) => `<li>${escapeHTML(item)}</li>`).join("")}</ul></section>
      <div class="hard-constraint-line"><strong>Hard-constraint check</strong><span>${results.some((item) => item.feasibility?.status === "blocked") ? "At least one contender is blocked by the current setup." : "No contender is blocked. Change a hard constraint to test feasibility."}</span></div>
    </article>`;
  $("#compareSetupSummary").innerHTML = `<h2>Your Battle Setup</h2><div class="battle-setup-list">${results.map((item, index) => `<div><i style="background:${colors[index]}"></i><span>${escapeHTML(item.occupation_title)}</span><strong>${Math.round(item.score)}</strong></div>`).join("")}</div><p>Location: ${escapeHTML($("#compareState")?.value || "National")}</p>`;
  $("#compareKeyTakeaways").innerHTML = `<h2>Key Takeaways</h2><div class="takeaway-winner"><small>Current winner</small><strong>${escapeHTML(winner.occupation_title)}</strong><span>${Math.round(winner.score)} overall</span></div><p>${escapeHTML(data.tradeoff_summary?.plain_language || data.summary)}</p><button class="soft-button" data-open-soc="${winner.soc_code}">Open winner profile</button>`;
  $$('[data-battle-tab]', $("#compareResults")).forEach((button) => button.addEventListener("click", () => {
    $$('[data-battle-tab]', $("#compareResults")).forEach((item) => item.classList.toggle("active", item === button));
    $$('[data-battle-panel]', $("#compareResults")).forEach((panel) => panel.classList.toggle("active", panel.dataset.battlePanel === button.dataset.battleTab));
  }));
  $("#compareResults").scrollIntoView({ behavior: cp5MotionBehavior(), block: "start" });
}

function renderBridge(data) {
  cacheCareer(data.source); cacheCareer(data.target);
  const overlap = Math.round(data.overall_overlap || 0);
  const gaps = data.skill_gaps?.length ? data.skill_gaps.slice(0, 6) : (data.software_to_learn || []).slice(0, 4).map((name, index) => ({ skill_name: typeof name === "string" ? name : (name.software || name.name || `Target tool ${index + 1}`), target_importance: 3.5 }));
  const months = overlap >= 75 ? "3–6 months" : overlap >= 55 ? "6–12 months" : overlap >= 35 ? "9–18 months" : "12–24 months";
  const skillColors = ["technical", "analysis", "design", "leadership", "communication", "credential"];
  const start = data.source;
  const target = data.target;
  $("#bridgeResults").innerHTML = `<article class="skill-bridge-card card">
    <header class="bridge-v5-head"><div><span class="section-kicker">Skill Bridge · CareerProof-derived transition view</span><h2>${escapeHTML(start.occupation_title)} → ${escapeHTML(target.occupation_title)}</h2><p>${escapeHTML(data.summary)}</p><small class="bridge-view-label">Skill Bridge</small></div><div class="bridge-readiness"><small>Transition readiness</small><strong>${overlap}%</strong><span>Estimated planning window: ${months}</span></div></header>
    <div class="bridge-landscape">
      <section class="bridge-career-platform current"><span>Current career</span><h3>${escapeHTML(start.occupation_title)}</h3><strong>${money(start.median_wage, true)}</strong><small>${escapeHTML(start.education || "Education varies")}</small></section>
      <div class="bridge-structure" aria-label="Visual path from current to target career">
        <svg viewBox="0 0 720 250" role="img" aria-label="A bridge built from transferable and missing skills"><defs><linearGradient id="bridgeDeck" x1="0" x2="1"><stop offset="0" stop-color="#7559ff"/><stop offset="1" stop-color="#248bff"/></linearGradient></defs><path d="M35 188 Q360 15 685 188" fill="none" stroke="#3f5f93" stroke-width="4"/><path d="M35 188 L685 188" stroke="url(#bridgeDeck)" stroke-width="18" stroke-linecap="round"/><path d="M65 188 L65 74 M655 188 L655 74" stroke="#7a91bb" stroke-width="5"/><path d="M65 74 Q360 25 655 74" fill="none" stroke="#7a91bb" stroke-width="3"/>${[0,1,2,3,4,5].map((i) => `<line x1="${115+i*99}" y1="${188}" x2="${115+i*99}" y2="${64 + Math.abs(2.5-i)*10}" stroke="#556f9b" stroke-width="2"/>`).join("")}</svg>
        <div class="bridge-skill-planks">${(data.shared_skills || []).slice(0, 4).map((skill, index) => `<span class="${skillColors[index]}">${escapeHTML(skill.skill_name)}</span>`).join("")}${gaps.map((skill, index) => `<span class="missing ${skillColors[(index + 2) % skillColors.length]}">${escapeHTML(skill.skill_name)}<small>build</small></span>`).join("")}</div>
      </div>
      <section class="bridge-career-platform target"><span>Target career</span><h3>${escapeHTML(target.occupation_title)}</h3><strong>${money(target.median_wage, true)}</strong><small>${escapeHTML(target.education || "Education varies")}</small></section>
    </div>
    <div class="bridge-insight-grid">
      <section><h3>Shared transferable skills</h3>${(data.shared_skills || []).slice(0, 8).map((skill) => `<div class="skill-row"><span>${escapeHTML(skill.skill_name)}</span><strong>${Number(skill.shared_score || skill.target_importance || 0).toFixed(1)}</strong></div>`).join("") || `<p>No exact shared skill names were published.</p>`}</section>
      <section><h3>Skills and tools to build</h3>${gaps.map((skill) => `<div class="skill-row"><span>${escapeHTML(skill.skill_name)}</span><strong>Priority</strong></div>`).join("") || `<p>The published profiles already overlap strongly. Validate employer-specific tools next.</p>`}</section>
      <section class="bridge-metrics"><h3>Transition evidence</h3><div><span>Task similarity</span><strong>${Math.round(data.task_similarity)}%</strong></div><div><span>Technology overlap</span><strong>${Math.round(data.technology_overlap)}%</strong></div><div><span>Wage difference</span><strong>${money(data.wage_difference, true)}</strong></div><div><span>Growth difference</span><strong>${pct(data.growth_difference)}</strong></div></section>
    </div>
    <section class="bridge-roadmap"><span class="section-kicker">TRANSITION STEPS</span>${(data.pathway || []).map((step, index) => `<article><i>${index + 1}</i><div><strong>${escapeHTML(step.title || `Transition step ${index + 1}`)}</strong><p>${escapeHTML(step.detail || "")}</p></div></article>`).join("")}</section>
    <footer class="bridge-actions"><button class="primary-button" data-save-soc="${target.soc_code}">Save transition target</button><button class="outline-button" data-open-soc="${target.soc_code}">Open required evidence</button><button class="outline-button" data-workspace-jump="degrees">Explore education paths</button></footer>
    <p class="bridge-boundary">${escapeHTML(data.boundary)} The planning window is a CareerProof heuristic based on occupational-profile overlap, not a guaranteed completion time.</p>
  </article>`;
  $("#bridgeResults").scrollIntoView({ behavior: cp5MotionBehavior(), block: "start" });
}

function cp5TableCell(value, column) {
  if (column?.format === "currency") return money(value);
  if (column?.format === "percent") return pct(value);
  if (column?.format === "number") return formatNumber(value);
  if (column?.format === "decimal") return value === null || value === undefined ? "—" : Number(value).toFixed(2);
  return String(value ?? "—");
}

function renderQuestionResult(data) {
  const evidencePanel = $("#askEvidencePanel");
  if (data.status === "refused" || data.status === "needs_clarification") {
    $("#resultArea").innerHTML = `<article class="refusal-card"><span class="refusal-badge">${data.status === "refused" ? "Safe refusal" : "Clarification needed"}</span><h2>${escapeHTML(data.headline)}</h2><p>${escapeHTML(data.explanation || data.summary)}</p><div class="evidence-box"><small>Why CareerProof stopped</small><strong>${escapeHTML(data.refusal_reason || data.summary || "The requested claim is outside the bundled data.")}</strong><p>No unsupported calculation was run.</p></div><h3>Try a supported question</h3><div class="suggestion-list">${(data.suggestions || []).map((question) => `<button data-quick-question="${escapeHTML(question)}">${escapeHTML(question)}</button>`).join("")}</div></article>`;
    if (evidencePanel) evidencePanel.innerHTML = `<header><span class="section-kicker">Trust boundary</span><h2>Unsupported claim blocked</h2></header><div class="refusal-evidence">${cp5Icon("shield")}<strong>No calculation was performed.</strong><p>${escapeHTML(data.boundary || data.summary || "The necessary variable or causal link is absent.")}</p><pre>${escapeHTML(JSON.stringify(data.query_plan || {}, null, 2))}</pre></div>`;
    return;
  }
  const rows = data.analysis?.rows || [];
  const columns = data.columns || [];
  const valueKey = data.analysis?.value_key;
  const max = Math.max(...rows.map((row) => Number(row[valueKey] || 0)), 1);
  const interpreted = data.interpreted_question || data.question;
  const repairs = data.input_corrections || [];
  const tableColumns = columns.length ? columns : (data.analysis?.table_columns || []).map((key) => ({ key, label: titleCase(key) }));
  const chart = rows.slice(0, 10).map((row) => `<div class="bar-row"><span>${escapeHTML(row.label)}</span><i class="bar-track"><span class="bar-fill" style="width:${Math.max(3, Number(row[valueKey] || 0) / max * 100)}%"></span></i><strong>${escapeHTML(row.display_value)}</strong></div>`).join("");
  const table = rows.length ? `<div class="location-table-wrap"><table class="analysis-table"><thead><tr>${tableColumns.map((column) => `<th>${escapeHTML(column.label || titleCase(column.key))}</th>`).join("")}</tr></thead><tbody>${rows.slice(0, 25).map((row) => `<tr>${tableColumns.map((column) => `<td>${escapeHTML(cp5TableCell(row[column.key], column))}</td>`).join("")}</tr>`).join("")}</tbody></table></div>` : "";
  $("#resultArea").innerHTML = `<article class="result-card ask-answer-card">
    <header class="answer-summary"><span class="assistant-avatar">CP</span><div><span class="section-kicker">Verified answer</span><h2>${escapeHTML(data.headline)}</h2><p>${escapeHTML(data.explanation || data.summary)}</p></div><span class="answer-confidence">${escapeHTML(data.confidence?.label || "Published")}<small>${Number(data.confidence?.score || 0)}/100</small></span></header>
    ${repairs.length ? `<div class="input-repair-banner">${cp5Icon("edit")}<div><strong>I interpreted your wording as:</strong><p>${escapeHTML(interpreted)}</p><small>${repairs.map((item) => `${escapeHTML(item.from)} → ${escapeHTML(item.to)}`).join(" · ")}</small></div></div>` : `<div class="query-interpretation"><small>Question understood as</small><strong>${escapeHTML(interpreted)}</strong></div>`}
    <div class="proof-strip"><div><small>Dataset</small><strong>${escapeHTML(data.dataset)}</strong></div><div><small>Rows used</small><strong>${formatNumber(data.analysis?.rows_used || rows.length)}</strong></div><div><small>Decision confidence</small><strong>${escapeHTML(data.decision_confidence?.label || "Review")}</strong></div><div><small>Evidence ID</small><strong>${escapeHTML(data.evidence_id || data.evidence?.evidence_id || "Generated")}</strong></div></div>
    <div class="confidence-card answer-confidence-card"><small>Decision boundary</small><strong>${escapeHTML(data.decision_confidence?.label || "Review with context")}</strong><p>${escapeHTML(data.decision_confidence?.reason || data.confidence?.reason || "Official evidence supports the calculation. Personal outcomes still depend on circumstances outside the dataset.")}</p></div>
    <section class="answer-visual"><div class="bar-chart">${chart}</div>${table}</section>
    <div class="query-plan"><div><small>Intent</small><strong>${escapeHTML(titleCase(data.intent || "analysis"))}</strong></div><div><small>Calculation</small><strong>${escapeHTML(data.evidence?.calculation || data.analysis?.calculation || "Visible deterministic calculation")}</strong></div><div><small>Human-error checks</small><strong>${escapeHTML((data.human_error_checks || []).join(" · ") || "Input and route validated")}</strong></div></div>
    <div class="suggested-followups">${(data.suggestions || []).slice(0,4).map((question) => `<button data-quick-question="${escapeHTML(question)}">${escapeHTML(question)}</button>`).join("")}</div>
  </article>`;
  if (evidencePanel) evidencePanel.innerHTML = `<header><span class="section-kicker">Live Evidence</span><h2>How this answer was built</h2></header>
    <div class="evidence-status"><span>${cp5Icon("check")}</span><div><strong>${escapeHTML(data.confidence?.label || "Published")} source confidence</strong><p>${escapeHTML(data.confidence?.reason || "Official source rows and a reproducible calculation.")}</p></div></div>
    <section><h3>Source lineage</h3>${(data.sources || []).map((source) => `<a class="live-source" href="${escapeHTML(source.url || "#")}" target="_blank" rel="noreferrer"><strong>${escapeHTML(source.title || source.agency || source.id)}</strong><small>${escapeHTML(source.agency || "Official source")} · ${escapeHTML(source.vintage || "Published snapshot")}</small></a>`).join("")}</section>
    <section><h3>Structured query plan</h3><pre>${escapeHTML(JSON.stringify(data.query_plan || {}, null, 2))}</pre></section>
    <section><h3>Limitations</h3><ul>${(data.limitations || []).map((item) => `<li>${escapeHTML(item)}</li>`).join("") || "<li>No additional limitation was returned.</li>"}</ul></section>
    <button class="primary-button full" data-open-answer-evidence>Open Evidence Passport</button>`;
  $$('[data-open-answer-evidence]').forEach((button) => button.addEventListener("click", () => openAnswerEvidence(data)));
}

function renderOccupation(data) {
  const p = data.profile;
  const r = data.resilience_profile || {};
  const locations = data.location_opportunity?.rows || [];
  const skills = data.skills || [];
  const tasks = data.tasks || [];
  const degrees = data.related_degrees || [];
  const coverage = data.data_coverage || {};
  const container = $("#occupationProfile");
  container.className = "occupation-profile card occupation-profile-v5";
  const tabs = ["overview", "work", "skills", "education", "outlook", "locations", "evidence"];
  container.innerHTML = `<header class="occupation-hero"><div><span class="section-kicker">SOC ${escapeHTML(p.soc_code)} · ${escapeHTML(p.category)}</span><h2>${escapeHTML(p.occupation_title)}</h2><p>${escapeHTML(p.description || "")}</p></div><div class="occupation-actions"><button class="outline-button" data-evidence-soc="${p.soc_code}">Evidence Passport</button><button class="outline-button" data-tray-soc="${p.soc_code}">Compare</button><button class="primary-button" data-save-soc="${p.soc_code}">Save</button></div></header>
    <div class="occupation-kpis"><div class="occupation-kpi"><small>Median wage</small><strong>${money(p.median_wage)}</strong><span>May 2025</span></div><div class="occupation-kpi"><small>Wage range</small><strong>${money(p.wage_p10, true)}–${money(p.wage_p90, true)}</strong><span>10th–90th percentile</span></div><div class="occupation-kpi"><small>Growth</small><strong>${pct(p.growth_percent)}</strong><span>2024–2034</span></div><div class="occupation-kpi"><small>Annual openings</small><strong>${compactNumber(p.annual_openings)}</strong><span>Projected average</span></div><div class="occupation-kpi"><small>AI resilience</small><strong>${Math.round(p.resilience_score)}</strong><span>${escapeHTML(p.resilience_label)}</span></div><div class="occupation-kpi"><small>Entry education</small><strong>${escapeHTML(p.education || "Not published")}</strong><span>Typical BLS category</span></div></div>
    <nav class="occupation-tabs">${tabs.map((tab, index) => `<button data-profile-tab="${tab}" class="${index === 0 ? "active" : ""}">${escapeHTML(titleCase(tab))}</button>`).join("")}</nav>
    <div class="occupation-tab-panels">
      <section data-profile-panel="overview" class="active"><div class="profile-two-col"><article class="profile-section"><h3>Why this career may remain valuable</h3>${Object.values(r.dimensions || {}).sort((a,b) => b.score-a.score).slice(0,4).map((dimension) => `<div class="dimension-row"><span>${escapeHTML(dimension.label)}</span><i><b style="width:${Math.round(dimension.score)}%"></b></i><strong>${Math.round(dimension.score)}</strong></div>`).join("")}</article><article class="profile-section"><h3>AI impact</h3>${taskImpactColumn("Human-led", "human-led", r.ai_task_impact?.human_led)}${taskImpactColumn("AI-augmented", "augmented", r.ai_task_impact?.ai_augmented)}</article></div></section>
      <section data-profile-panel="work"><div class="profile-section"><h3>Official O*NET task statements</h3>${tasks.slice(0,12).map((task) => `<div class="task-item">${escapeHTML(task.task_description)}</div>`).join("") || "<p>No task statements available.</p>"}</div></section>
      <section data-profile-panel="skills"><div class="skills-profile-grid">${skills.slice(0,12).map((skill) => `<article><strong>${escapeHTML(skill.skill_name)}</strong><span>${Number(skill.importance || 0).toFixed(2)}</span></article>`).join("")}</div></section>
      <section data-profile-panel="education"><div class="profile-section"><h3>Related degree pathways</h3><p>The crosswalk is qualitative. It does not prove placement or a required major.</p><div class="degree-chip-grid">${degrees.slice(0,12).map((degree) => `<button data-degree-code="${degree.cip_code}" data-workspace-jump="degrees"><strong>${escapeHTML(degree.cip_title)}</strong><small>CIP ${escapeHTML(degree.cip_code)}</small></button>`).join("") || "<p>No direct crosswalk relationships published.</p>"}</div></div></section>
      <section data-profile-panel="outlook"><div class="profile-two-col"><article class="profile-section"><h3>Published outlook</h3><div class="outlook-large"><strong>${pct(p.growth_percent)}</strong><span>employment growth</span></div><div class="outlook-large"><strong>${compactNumber(p.annual_openings)}</strong><span>annual openings</span></div></article><article class="profile-section"><h3>Market breadth</h3><div class="outlook-large"><strong>${formatNumber(p.state_coverage || 0)}</strong><span>published state and territory rows</span></div><div class="outlook-large"><strong>${Math.round(p.stability_score || 0)}</strong><span>CareerProof stability score</span></div></article></div></section>
      <section data-profile-panel="locations"><div class="profile-section"><h3>Top purchasing-power opportunities</h3>${locations.slice(0,8).map((row, index) => `<div class="location-profile-row"><span>${index + 1}</span><strong>${escapeHTML(row.label)}</strong><small>${escapeHTML(row.display_value)} adjusted</small></div>`).join("") || "<p>No state rows available.</p>"}<button class="primary-button" data-location-soc="${p.soc_code}">Open Location Intelligence</button></div></section>
      <section data-profile-panel="evidence"><div class="profile-two-col"><article class="profile-section"><h3>Data coverage</h3><div class="coverage-ring" style="--score:${Math.round(coverage.percent || 0)}"><div><strong>${Math.round(coverage.percent || 0)}%</strong><small>coverage</small></div></div>${Object.entries(coverage.components || {}).map(([key, value]) => `<div class="coverage-line"><span>${escapeHTML(titleCase(key))}</span><strong>${value.available ? "Available" : "Missing"}</strong></div>`).join("")}</article><article class="profile-section"><h3>Source lineage and limits</h3>${(data.source_lineage || []).map((line) => `<div class="lineage-row"><strong>${escapeHTML(line.dataset)}</strong><span>${escapeHTML(line.value)}</span></div>`).join("")}<ul class="limitation-list">${(data.limitations || []).map((item) => `<li>${escapeHTML(item)}</li>`).join("")}</ul></article></div></section>
    </div>`;
  $$('[data-profile-tab]', container).forEach((button) => button.addEventListener("click", () => {
    $$('[data-profile-tab]', container).forEach((item) => item.classList.toggle("active", item === button));
    $$('[data-profile-panel]', container).forEach((panel) => panel.classList.toggle("active", panel.dataset.profilePanel === button.dataset.profileTab));
  }));
}

async function openDegree(cipCode) {
  const container = $("#degreeDetail");
  container.innerHTML = `<div class="loading-card"><span class="spinner"></span><p>Joining degree and occupation evidence…</p></div>`;
  try {
    const data = normalizeDegreePayload(await api(`/api/degree/${encodeURIComponent(cipCode)}`));
    (data.related_careers || []).forEach(cacheCareer);
    const careers = data.related_careers || [];
    container.innerHTML = `<span class="section-kicker">Academic pathway · CIP ${escapeHTML(data.cip_code)}</span><h2>${escapeHTML(data.cip_title)}</h2><p>${escapeHTML(data.boundary)}</p>
      <div class="degree-pathway-timeline"><article class="degree-milestone start"><i>1</i><div><small>Program</small><strong>${escapeHTML(data.cip_title)}</strong><p>CIP ${escapeHTML(data.cip_code)}</p></div></article><article class="degree-milestone"><i>2</i><div><small>Broad earnings context</small><strong>${data.field_earnings?.median_earnings ? money(data.field_earnings.median_earnings) : "No direct ACS mapping"}</strong><p>${escapeHTML(data.field_earnings?.disclosure || "Shown only when a supported broad field match exists.")}</p></div></article><article class="degree-milestone"><i>3</i><div><small>Connected careers</small><strong>${formatNumber(careers.length)} official relationships</strong><p>Qualitative crosswalk links, not placement rates.</p></div></article></div>
      <h3>Related occupations</h3><div class="degree-career-grid">${careers.slice(0,12).map((item) => `<article class="degree-career-card"><small>SOC ${escapeHTML(item.soc_code)}</small><h3>${escapeHTML(item.occupation_title)}</h3><strong>${money(item.median_wage)}</strong><p>${pct(item.growth_percent)} growth · ${escapeHTML(item.education || "Education varies")}</p><div><button data-open-soc="${item.soc_code}">Profile</button><button data-tray-soc="${item.soc_code}">Compare</button></div></article>`).join("")}</div>`;
  } catch (error) { container.innerHTML = `<div class="refusal-card"><h2>Degree pathway unavailable</h2><p>${escapeHTML(error.message)}</p></div>`; }
}

function renderLocation(data) {
  const rows = data.rows || [];
  const top = rows.slice(0, 3);
  $("#locationResults").innerHTML = `<article class="location-results-card card"><header class="location-summary"><div><span class="section-kicker">Location Intelligence</span><h2>${escapeHTML(data.headline)}</h2><p>${escapeHTML(data.boundary)}</p></div><div class="heading-badge"><span>Purchasing power</span><strong>Salary ÷ RPP × 100</strong><small>${escapeHTML(data.formula)}</small></div></header>
    <div class="location-lens-v5"><div class="location-map-visual" aria-hidden="true"><span class="map-shape"></span>${top.map((row, index) => `<i class="map-pin pin-${index + 1}"><b>${index + 1}</b><small>${escapeHTML(row.label)}</small></i>`).join("")}</div><div class="location-top-grid">${top.map((row, index) => `<article class="location-card"><span class="section-kicker">Rank ${index + 1}</span><h3>${escapeHTML(row.label)}</h3><span class="location-score">${Number(row.opportunity_score).toFixed(1)}</span><div class="location-stat"><span>Nominal salary</span><strong>${money(row.nominal_wage)}</strong></div><div class="location-stat"><span>Purchasing power</span><strong>${money(row.purchasing_power_wage)}</strong></div><div class="location-stat"><span>Employment</span><strong>${compactNumber(row.employment)}</strong></div><div class="location-stat"><span>Concentration</span><strong>${Number(row.location_quotient || 0).toFixed(2)}</strong></div></article>`).join("")}</div></div>
    <div class="location-table-wrap"><table class="location-table"><thead><tr><th>Rank</th><th>State</th><th>Nominal wage</th><th>Purchasing power</th><th>Employment</th><th>Location quotient</th><th>RPP</th><th>Confidence</th><th>Derived score</th></tr></thead><tbody>${rows.map((row, index) => `<tr><td>${index + 1}</td><td>${escapeHTML(row.label)}</td><td>${money(row.nominal_wage)}</td><td>${money(row.purchasing_power_wage)}</td><td>${formatNumber(row.employment)}</td><td>${Number(row.location_quotient || 0).toFixed(2)}</td><td>${Number(row.regional_price_parity || 0).toFixed(1)}</td><td>${escapeHTML(row.confidence)}</td><td>${Number(row.opportunity_score).toFixed(1)}</td></tr>`).join("")}</tbody></table></div><div class="data-vintage-inline">${cp5Icon("clock")}<div>${escapeHTML(data.freshness?.summary || "BLS wage estimates and BEA price levels retain their source years.")}</div></div></article>`;
  $("#locationResults").scrollIntoView({ behavior: cp5MotionBehavior(), block: "start" });
}

function renderSavedWorkspace() {
  const list = $("#savedWorkspaceList");
  if (!list) return;
  const primary = state.lastPath?.portfolio?.primary_path || state.saved[0];
  list.innerHTML = state.saved.length ? `<div class="saved-leading-choice">${primary ? `<small>Current leading choice</small><strong>${escapeHTML(primary.occupation_title)}</strong><span>${money(primary.median_wage, true)} · ${escapeHTML(primary.resilience_label || "Resilience profile")}</span>` : ""}</div>${state.saved.map((item, index) => `<article class="saved-workspace-item"><span>${String(index + 1).padStart(2,"0")}</span><div><strong>${escapeHTML(item.occupation_title)}</strong><small>${money(item.median_wage, true)} · ${escapeHTML(item.resilience_label || "Resilience profile")}</small></div><div><button data-open-soc="${item.soc_code}">Open</button><button data-tray-soc="${item.soc_code}">Compare</button><button data-remove-saved="${item.soc_code}">Remove</button></div></article>`).join("")}` : `<div class="saved-empty-v5">${cp5Icon("bookmark")}<h3>Build your first career plan</h3><p>Save a career from Path Builder, Compare Lab, Career Universe, or Occupation Explorer.</p><button class="primary-button" data-workspace-jump="path">Build My Path</button></div>`;
  const portfolio = state.lastPath?.portfolio || {};
  $("#savedPortfolio").innerHTML = [["Primary path", portfolio.primary_path], ["Safer backup", portfolio.safer_backup], ["High upside", portfolio.high_upside_option], ["Fast entry", portfolio.fast_entry_option]].map(([label, item], index) => item ? `<button class="portfolio-item" data-open-soc="${item.soc_code}"><i>${index + 1}</i><small>${escapeHTML(label)}</small><strong>${escapeHTML(item.occupation_title)}</strong><span>${Math.round(item.score)} fit · ${escapeHTML(item.resilience_label)}</span></button>` : `<div class="portfolio-item"><i>${index + 1}</i><small>${escapeHTML(label)}</small><strong>Run Path Builder</strong><span>to generate this role</span></div>`).join("");
  $("#decisionNotes").value = state.decisionNotes;
  const planGrid = $(".saved-workspace-grid");
  if (planGrid && !$("#careerPlanTimeline")) planGrid.insertAdjacentHTML("afterend", `<section class="card career-plan-timeline" id="careerPlanTimeline"><header><div><span class="section-kicker">My Career Plan</span><h2>Turn evidence into action</h2></div><span>${state.saved.length} careers shortlisted</span></header><div class="plan-timeline"><article class="complete"><i>1</i><div><strong>Explore and shortlist</strong><p>${state.saved.length ? `${state.saved.length} career${state.saved.length === 1 ? "" : "s"} saved` : "Save your first career"}</p></div></article><article class="${state.lastPath ? "complete" : ""}"><i>2</i><div><strong>Validate fit and tradeoffs</strong><p>${state.lastPath ? "Path Builder ranking completed" : "Run Build My Path"}</p></div></article><article class="${state.lastCompare ? "complete" : ""}"><i>3</i><div><strong>Challenge the leading choice</strong><p>${state.lastCompare ? "Comparison completed" : "Use Compare Lab"}</p></div></article><article><i>4</i><div><strong>Create proof of skill</strong><p>Choose a project, credential, or experience step</p></div></article></div></section>`);
}

function renderSources() {
  const sources = state.bootstrap?.sources || [];
  const container = $("#sourceCatalog");
  if (!container) return;
  container.innerHTML = `<div class="source-journey-intro"><span class="section-kicker">Step 1 · where the data comes from</span><h2>Official sources, each used for a specific job</h2><p>CareerProof keeps direct values, transformed values, and derived decision aids visibly separate.</p></div>${sources.map((source, index) => `<article class="source-card" style="--source-accent:${CP5_ACCENTS[index % CP5_ACCENTS.length]}"><span class="source-number">${String(index + 1).padStart(2,"0")}</span><small>${escapeHTML(source.agency)} · ${escapeHTML(source.publication_date || source.year || "Published snapshot")}</small><h3>${escapeHTML(source.name)}</h3><p>${escapeHTML(source.description)}</p><div class="source-meta"><span>${escapeHTML(source.direct ? "Direct official values" : "Official values transformed for display")}</span><span>${escapeHTML(source.license || "Public data")}</span></div>${source.url ? `<a href="${escapeHTML(source.url)}" target="_blank" rel="noreferrer">Open official source ↗</a>` : ""}</article>`).join("")}`;
}

function switchWorkspace(name, { scroll = true } = {}) {
  const target = $(`#workspace-${name}`);
  if (!target) return;
  state.activeWorkspace = name;
  $$(".workspace").forEach((workspace) => workspace.classList.remove("active"));
  target.classList.add("active");
  $$(".nav-item[data-workspace]").forEach((button) => button.classList.toggle("active", button.dataset.workspace === name));
  const announcer = $("#workspaceAnnouncer"); if (announcer) announcer.textContent = `${WORKSPACE_TITLES[name] || name} opened`;
  $(".sidebar")?.classList.remove("open");
  document.body.dataset.workspace = name;
  if (scroll) scrollToTop();
  if (name === "trust") loadTrustTab("sources");
  if (name === "saved") renderSavedWorkspace();
  if (name === "universe" && state.universe) renderUniverseRoot();
  if (name === "path") cp5RenderPathInputSummary();
}

function cp5BindRedesignControls() {
  $("#pathStageNext")?.addEventListener("click", () => { cp5SetPathStep("priorities"); $("[data-path-form-stage='priorities']")?.scrollIntoView({ behavior: cp5MotionBehavior(), block: "start" }); });
  $("#pathStageBack")?.addEventListener("click", () => { cp5SetPathStep("about"); $("#pathForm")?.scrollIntoView({ behavior: cp5MotionBehavior(), block: "start" }); });
  $("#editPathSummary")?.addEventListener("click", () => { cp5SetPathStep("about"); $("#pathForm")?.scrollIntoView({ behavior: cp5MotionBehavior(), block: "start" }); });
  $("#editPathInputs")?.addEventListener("click", () => { $("#pathForm")?.classList.remove("hidden"); $("#pathInterpretation")?.classList.add("hidden"); cp5SetPathStep("about"); $("#pathForm")?.scrollIntoView({ behavior: cp5MotionBehavior(), block: "start" }); });
  $("#pathForm")?.addEventListener("input", () => cp5RenderPathInputSummary(pathPayload()));
  $("#universeReset")?.addEventListener("click", renderUniverseRoot);
  $("#universeListToggle")?.addEventListener("click", () => { $("#universeListFallback")?.classList.toggle("hidden"); $("#universeStage")?.classList.toggle("hidden"); cp5RenderUniverseFallback(); });
  $("#toggleCompareSetup")?.addEventListener("click", () => { const card=$(".compare-control-card"); card?.classList.toggle("collapsed"); $("#toggleCompareSetup").textContent=card?.classList.contains("collapsed") ? "Expand setup" : "Collapse setup"; });
  $("#swapBridge")?.addEventListener("click", () => { const a=$("#bridgeSource"), b=$("#bridgeTarget"); const temp=a.value; a.value=b.value; b.value=temp; const soc=a.dataset.soc; a.dataset.soc=b.dataset.soc || ""; b.dataset.soc=soc || ""; });
  $$('[data-degree-query]').forEach((button) => button.addEventListener("click", () => { $("#degreeSearch").value=button.dataset.degreeQuery; searchDegrees(); }));
  $$('[data-featured-title]').forEach((button) => button.addEventListener("click", async () => { const results=await searchOccupations(button.dataset.featuredTitle, 1); if(results[0]) openOccupation(results[0].soc_code); }));
  $$('[data-nav-toggle]').forEach((button) => button.addEventListener("click", () => { const group=button.closest(".nav-group"); group?.classList.toggle("open"); button.setAttribute("aria-expanded", String(group?.classList.contains("open"))); }));
  $$('[data-trust-journey]').forEach((button) => button.addEventListener("click", () => activateTrustTab(button.dataset.trustJourney)));
  $("#sidebarCollapse")?.addEventListener("click", () => document.body.classList.toggle("sidebar-collapsed"));
  $("#degreeModeToggle")?.addEventListener("click", (event) => { const button=event.target.closest("button"); if(!button)return; $$("#degreeModeToggle button").forEach((item)=>item.classList.toggle("active",item===button)); $("#degreeSearch").placeholder=button.dataset.degreeMode==="career" ? "Search a career to find related degrees…" : "Search electrical engineering, computer science…"; });
  window.addEventListener("resize", () => {
    if (window.innerWidth <= 480 && state.activeWorkspace === "home") {
      $$(".workspace").forEach((workspace) => workspace.classList.remove("active"));
      $("#workspace-home")?.classList.add("active");
      document.body.dataset.workspace = "home";
    }
  });
}

function init() {
  bindNavigation();
  bindGlobalSearch();
  bindFormsAndControls();
  bindDelegatedActions();
  cp5BindRedesignControls();
  renderWeightControls("pathWeights", state.pathWeights, updatePathWeightTotal);
  updatePathWeightTotal();
  renderWeightControls("compareWeights", state.compareWeights);
  renderCompareSlots();
  renderInterestChips();
  renderSkillTags();
  renderSavedCounts();
  cp5SetPathStep("about");
  loadInitialData();
}

document.addEventListener("DOMContentLoaded", init);
