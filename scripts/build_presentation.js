const fs = require('fs');
const path = require('path');
const pptxgen = require('pptxgenjs');
const {
  imageSizingCrop,
  imageSizingContain,
  safeOuterShadow,
  svgToDataUri,
  warnIfSlideHasOverlaps,
  warnIfSlideElementsOutOfBounds,
  autoFontSize,
} = require('/home/oai/skills/slides/pptxgenjs_helpers');

const ROOT = '/mnt/data/careerproof-ai';
const OUT = path.join(ROOT, 'docs', 'presentation.pptx');
const DATA = JSON.parse(fs.readFileSync(path.join(ROOT, 'docs', 'presentation_data.json'), 'utf8'));
const SCREENSHOT = path.join(ROOT, 'docs', 'assets', 'screenshots', 'dashboard.png');

const pptx = new pptxgen();
pptx.layout = 'LAYOUT_WIDE';
pptx.author = 'CareerProof AI Hackathon Team';
pptx.company = 'Secure AI Hackathon';
pptx.subject = 'Track 2 - Trustworthy Data Analysis';
pptx.title = 'CareerProof AI - Ask the job market. See the proof.';
pptx.lang = 'en-US';
pptx.theme = {
  headFontFace: 'Aptos Display',
  bodyFontFace: 'Aptos',
  lang: 'en-US',
};
pptx.defineSlideMaster({
  title: 'LIGHT',
  background: { color: 'F6F8FC' },
  objects: [],
  slideNumber: { x: 12.45, y: 7.02, w: 0.35, h: 0.2, color: '718096', fontFace: 'Aptos', fontSize: 9, align: 'right' },
});
pptx.defineSlideMaster({
  title: 'DARK',
  background: { color: '081C33' },
  objects: [],
  slideNumber: { x: 12.45, y: 7.02, w: 0.35, h: 0.2, color: 'A9C1D9', fontFace: 'Aptos', fontSize: 9, align: 'right' },
});

const C = {
  NAVY: '081C33',
  NAVY2: '102A48',
  BLUE: '2F6BFF',
  BLUE_LIGHT: 'E8F0FF',
  GREEN: '118A63',
  GREEN_LIGHT: 'E7F7F1',
  ORANGE: 'F28C28',
  ORANGE_LIGHT: 'FFF1E1',
  BG: 'F6F8FC',
  CARD: 'FFFFFF',
  TEXT: '15263A',
  MUTED: '5C6B7A',
  LINE: 'D9E2EC',
  WHITE: 'FFFFFF',
  RED: 'D64545',
  RED_LIGHT: 'FDECEC',
  TEAL: '20A4A8',
  PURPLE: '6D5CE8',
};
const SH = safeOuterShadow('000000', 0.16, 45, 2, 0.7);
const W = 13.333;
const H = 7.5;

function addNotes(slide, sources) {
  slide.addNotes(`[Sources]\n${sources.map(s => `- ${s}`).join('\n')}`);
}

function addBrand(slide, dark = false) {
  const color = dark ? C.WHITE : C.NAVY;
  slide.addShape(pptx.ShapeType.roundRect, {
    x: 0.48, y: 0.32, w: 0.42, h: 0.42,
    rectRadius: 0.08,
    fill: { color: C.GREEN }, line: { color: C.GREEN },
  });
  slide.addText('CP', {
    x: 0.49, y: 0.405, w: 0.40, h: 0.15,
    fontFace: 'Aptos Display', fontSize: 10, bold: true, color: C.WHITE,
    align: 'center', margin: 0,
  });
  slide.addText('CAREERPROOF AI', {
    x: 1.02, y: 0.36, w: 2.05, h: 0.22,
    fontFace: 'Aptos', fontSize: 10, bold: true, color,
    charSpacing: 1.4, margin: 0,
  });
}

function addSectionTitle(slide, kicker, title, subtitle, dark = false) {
  const titleColor = dark ? C.WHITE : C.TEXT;
  const muted = dark ? 'BDD0E3' : C.MUTED;
  slide.addText(kicker.toUpperCase(), {
    x: 0.62, y: 0.82, w: 3.6, h: 0.24,
    fontFace: 'Aptos', fontSize: 11, bold: true, color: C.GREEN,
    charSpacing: 1.8, margin: 0,
  });
  slide.addText(title, {
    x: 0.62, y: 1.10, w: 8.8, h: 0.58,
    fontFace: 'Aptos Display', fontSize: 27, bold: true, color: titleColor,
    margin: 0, breakLine: false,
  });
  if (subtitle) {
    slide.addText(subtitle, {
      x: 0.62, y: 1.72, w: 10.8, h: 0.38,
      fontFace: 'Aptos', fontSize: 14, color: muted,
      margin: 0,
    });
  }
}

function pill(slide, text, x, y, w, fill, color, fontSize = 10) {
  slide.addText(text, {
    x, y, w, h: 0.34,
    fontFace: 'Aptos', fontSize, bold: true, color,
    fill: { color: fill }, line: { color: fill },
    margin: 0.05, align: 'center', valign: 'mid',
    radius: 0.12,
  });
}

function metric(slide, value, label, x, y, w, accent = C.GREEN, dark = false) {
  const fill = dark ? C.NAVY2 : C.CARD;
  const valueColor = dark ? C.WHITE : C.TEXT;
  const labelColor = dark ? 'BDD0E3' : C.MUTED;
  slide.addText([
    { text: value, options: { bold: true, fontSize: 23, color: valueColor, breakLine: true } },
    { text: label, options: { fontSize: 10.5, color: labelColor } },
  ], {
    x, y, w, h: 0.96,
    fill: { color: fill },
    line: { color: dark ? '204665' : C.LINE, pt: 0.8 },
    radius: 0.14,
    margin: [0.16, 0.16, 0.10, 0.16],
    shadow: SH,
    valign: 'mid',
  });
  slide.addShape(pptx.ShapeType.rect, {
    x, y, w: 0.055, h: 0.96,
    fill: { color: accent }, line: { color: accent },
  });
}

function card(slide, title, body, x, y, w, h, opts = {}) {
  const dark = opts.dark || false;
  const fill = opts.fill || (dark ? C.NAVY2 : C.CARD);
  const titleColor = opts.titleColor || (dark ? C.WHITE : C.TEXT);
  const bodyColor = opts.bodyColor || (dark ? 'C5D7E8' : C.MUTED);
  const accent = opts.accent || C.GREEN;
  const fontSize = opts.fontSize || 12.5;
  const titleSize = opts.titleSize || 15;
  slide.addText([
    { text: title, options: { bold: true, fontSize: titleSize, color: titleColor, breakLine: true } },
    { text: body, options: { fontSize, color: bodyColor, breakLine: false } },
  ], {
    x, y, w, h,
    fill: { color: fill },
    line: { color: opts.lineColor || accent, pt: opts.borderPt || 1.0 },
    radius: 0.14,
    margin: [0.24, 0.24, 0.20, 0.24],
    shadow: opts.shadow === false ? undefined : SH,
    valign: 'top',
    breakLine: false,
  });
}

function smallIcon(slide, label, x, y, color, dark = false) {
  slide.addShape(pptx.ShapeType.ellipse, {
    x, y, w: 0.44, h: 0.44,
    fill: { color: dark ? C.NAVY2 : C.CARD },
    line: { color, pt: 1.4 },
  });
  slide.addText(label, {
    x: x + 0.015, y: y + 0.105, w: 0.41, h: 0.14,
    fontFace: 'Aptos Display', fontSize: 9.5, bold: true, color,
    align: 'center', margin: 0,
  });
}

function addFooter(slide, text, dark = false) {
  slide.addText(text, {
    x: 0.62, y: 7.06, w: 7.5, h: 0.16,
    fontFace: 'Aptos', fontSize: 8.5,
    color: dark ? '8EABC5' : '7B8794',
    margin: 0,
  });
}

function finish(slide) {
  warnIfSlideHasOverlaps(slide, pptx);
  warnIfSlideElementsOutOfBounds(slide, pptx);
}

// Slide 1: Title
{
  const slide = pptx.addSlide('DARK');
  addBrand(slide, true);
  slide.addShape(pptx.ShapeType.rect, {
    x: 0.62, y: 1.20, w: 0.10, h: 0.72,
    fill: { color: C.GREEN }, line: { color: C.GREEN },
  });
  slide.addText('CareerProof AI', {
    x: 0.92, y: 1.14, w: 5.15, h: 0.72,
    fontFace: 'Aptos Display', fontSize: 35, bold: true, color: C.WHITE,
    margin: 0,
  });
  slide.addText('Ask the job market. See the proof.', {
    x: 0.92, y: 1.94, w: 5.35, h: 0.48,
    fontFace: 'Aptos', fontSize: 20, color: 'C8DAEA',
    margin: 0,
  });
  slide.addText('A trustworthy data-analysis assistant for students and early-career job seekers.', {
    x: 0.92, y: 2.55, w: 5.10, h: 0.76,
    fontFace: 'Aptos', fontSize: 15.5, color: 'AFC5D9',
    margin: 0,
  });
  pill(slide, 'TRACK 2 · TRUSTWORTHY DATA ANALYSIS', 0.92, 3.50, 3.35, C.GREEN, C.WHITE, 10);
  slide.addText('AI interprets the question. Code calculates the answer.', {
    x: 0.92, y: 4.08, w: 5.05, h: 0.74,
    fontFace: 'Aptos Display', fontSize: 21, bold: true, color: C.WHITE,
    margin: 0,
  });
  slide.addText('Every result includes visible calculations, masked evidence, confidence, and a safe refusal when the dataset cannot answer.', {
    x: 0.92, y: 4.98, w: 5.15, h: 0.86,
    fontFace: 'Aptos', fontSize: 13.5, color: 'B7CDE0',
    margin: 0,
  });

  slide.addShape(pptx.ShapeType.roundRect, {
    x: 6.46, y: 0.86, w: 6.25, h: 5.88,
    rectRadius: 0.18,
    fill: { color: '112E4B' }, line: { color: '2A5576', pt: 1.1 }, shadow: SH,
  });
  slide.addImage({ path: SCREENSHOT, ...imageSizingCrop(SCREENSHOT, 6.64, 1.04, 5.89, 5.49) });
  pill(slide, 'SYNTHETIC DEMO DATA', 10.40, 6.10, 1.88, C.ORANGE, C.NAVY, 9.5);
  addFooter(slide, 'Secure AI Hackathon · Track 2 · CareerProof AI', true);
  addNotes(slide, [
    'CareerProof AI repository and bundled synthetic dataset, generated July 30, 2026.',
    'Participant_Guide_Updated(1).pdf, Track 2 requirements on pages 7-8.',
  ]);
  finish(slide);
}

// Slide 2: Problem and user
{
  const slide = pptx.addSlide('LIGHT');
  addBrand(slide, false);
  addSectionTitle(slide, 'The problem', 'Job seekers have data, not answers', 'The risk is not only information overload. It is receiving a confident answer with no proof.');

  card(slide, 'Too many listings', 'Students must compare hundreds of postings across skills, locations, salaries, and experience levels.', 0.62, 2.32, 3.55, 1.54, { accent: C.BLUE });
  card(slide, 'Unsupported AI', 'A general chatbot can produce a plausible number without actually calculating from the uploaded dataset.', 0.62, 4.03, 3.55, 1.54, { accent: C.ORANGE });
  card(slide, 'Weak decision support', 'A number without sample size, source rows, or data-quality context can mislead a career decision.', 0.62, 5.74, 3.55, 1.05, { accent: C.RED, fontSize: 11.8, titleSize: 14.5 });

  slide.addText('THE TRUST GAP', {
    x: 4.76, y: 2.34, w: 2.0, h: 0.22,
    fontFace: 'Aptos', fontSize: 10.5, bold: true, color: C.MUTED,
    charSpacing: 1.5, margin: 0,
  });
  slide.addText('“Which skills are most common in remote jobs?”', {
    x: 4.76, y: 2.66, w: 7.45, h: 0.46,
    fontFace: 'Aptos Display', fontSize: 20, bold: true, color: C.TEXT,
    margin: 0,
  });

  card(slide, 'Typical chatbot', 'Answers in natural language\n\nMay invent or blur the calculation\n\nNo source table or reproducible plan', 4.76, 3.30, 3.28, 2.55, { accent: C.ORANGE, fill: C.ORANGE_LIGHT, lineColor: 'F6C58F', titleColor: C.NAVY, bodyColor: C.TEXT, fontSize: 12 });
  card(slide, 'CareerProof AI', 'Interprets the question\n\nRuns an allowlisted Pandas calculation\n\nShows chart, rows, confidence, and Evidence ID', 8.38, 3.30, 3.82, 2.55, { accent: C.GREEN, fill: C.GREEN_LIGHT, lineColor: 'AADCC9', titleColor: C.NAVY, bodyColor: C.TEXT, fontSize: 12 });

  slide.addShape(pptx.ShapeType.rightArrow, {
    x: 8.07, y: 4.25, w: 0.26, h: 0.42,
    fill: { color: C.BLUE }, line: { color: C.BLUE },
  });
  pill(slide, 'TARGET USERS', 4.76, 6.20, 1.24, C.NAVY, C.WHITE, 9.5);
  slide.addText('High school and college students · recent graduates · career counselors · workforce programs', {
    x: 6.14, y: 6.23, w: 6.02, h: 0.30,
    fontFace: 'Aptos', fontSize: 11.5, color: C.MUTED, margin: 0,
  });
  addFooter(slide, 'Clear user problem + practical value directly support the highest-weight judging category.');
  addNotes(slide, [
    'Participant_Guide_Updated(1).pdf, page 7: Track 2 asks teams to calculate or verify answers from the actual dataset.',
    'Participant_Guide_Updated(1).pdf, page 11: Problem and usefulness is 25% of judging.',
  ]);
  finish(slide);
}

// Slide 3: Architecture
{
  const slide = pptx.addSlide('DARK');
  addBrand(slide, true);
  addSectionTitle(slide, 'How it works', 'A simple flow with a hard trust boundary', 'Language understanding helps route the question. Only deterministic code is allowed to create factual answers.', true);

  const steps = [
    ['1', 'CSV / XLSX', 'Bundled or uploaded data', C.BLUE],
    ['2', 'Validate + clean', 'Schema, dates, salaries, duplicates', C.TEAL],
    ['3', 'Local AI router', 'Intent and entity extraction', C.PURPLE],
    ['4', 'Query plan', 'Structured and allowlisted', C.ORANGE],
    ['5', 'Pandas executor', 'Deterministic calculation', C.GREEN],
    ['6', 'Proof output', 'Chart, table, confidence, audit', C.BLUE],
  ];
  const sx = 0.60;
  const gap = 0.14;
  const sw = 1.93;
  steps.forEach((step, i) => {
    const x = sx + i * (sw + gap);
    slide.addText([
      { text: step[0], options: { fontSize: 10, bold: true, color: C.WHITE, breakLine: true } },
      { text: step[1], options: { fontSize: 13.5, bold: true, color: C.WHITE, breakLine: true } },
      { text: step[2], options: { fontSize: 9.5, color: 'BDD0E3' } },
    ], {
      x, y: 2.63, w: sw, h: 1.38,
      fill: { color: C.NAVY2 }, line: { color: step[3], pt: 1.2 },
      radius: 0.14, margin: [0.14, 0.13, 0.12, 0.13],
      shadow: SH, valign: 'top',
    });
    if (i < steps.length - 1) {
      slide.addShape(pptx.ShapeType.chevron, {
        x: x + sw + 0.025, y: 3.10, w: 0.105, h: 0.38,
        fill: { color: '4D7090' }, line: { color: '4D7090' },
      });
    }
  });

  slide.addShape(pptx.ShapeType.line, {
    x: 6.82, y: 4.55, w: 0, h: 1.53,
    line: { color: C.GREEN, pt: 2.6, dash: 'dash' },
  });
  pill(slide, 'TRUST BOUNDARY', 6.02, 4.16, 1.60, C.GREEN, C.WHITE, 9.5);
  slide.addText('The AI never writes or executes Python, SQL, `eval`, or `exec`.', {
    x: 0.74, y: 4.76, w: 5.55, h: 0.48,
    fontFace: 'Aptos Display', fontSize: 19, bold: true, color: C.WHITE,
    margin: 0,
  });
  slide.addText('It creates a typed query plan. The validator rejects unsupported columns, operations, filters, and unsafe requests before calculation.', {
    x: 0.74, y: 5.37, w: 5.65, h: 0.92,
    fontFace: 'Aptos', fontSize: 12.8, color: 'BDD0E3', margin: 0,
  });

  card(slide, 'AI side', 'TF-IDF + logistic regression\nEntity matching\nClosest supported questions', 7.22, 4.62, 2.43, 1.75, { dark: true, accent: C.PURPLE, fontSize: 11.5, titleSize: 14.5 });
  card(slide, 'Code side', 'Validated filters\nPandas grouping and math\nEvidence + confidence rules', 9.87, 4.62, 2.43, 1.75, { dark: true, accent: C.GREEN, fontSize: 11.5, titleSize: 14.5 });

  addFooter(slide, 'Architecture is intentionally understandable: input → validation → AI routing → deterministic calculation → evidence.', true);
  addNotes(slide, [
    'CareerProof AI source code: src/careerproof/question_router.py, query_validator.py, query_executor.py, evidence.py, confidence.py.',
    'Participant_Guide_Updated(1).pdf, pages 3 and 11: architecture should support a working trust mechanism, not replace the product.',
  ]);
  finish(slide);
}

// Slide 4: live result
{
  const slide = pptx.addSlide('LIGHT');
  addBrand(slide, false);
  addSectionTitle(slide, 'Live result', 'A question becomes a verified answer', DATA.remote_skills.question);

  slide.addShape(pptx.ShapeType.roundRect, {
    x: 0.62, y: 2.32, w: 7.13, h: 4.30,
    rectRadius: 0.18,
    fill: { color: C.CARD }, line: { color: C.LINE, pt: 0.8 }, shadow: SH,
  });
  slide.addImage({ path: SCREENSHOT, ...imageSizingCrop(SCREENSHOT, 0.80, 2.50, 6.77, 3.95) });

  pill(slide, DATA.remote_skills.confidence.toUpperCase(), 8.10, 2.34, 1.72, C.GREEN, C.WHITE, 9.5);
  slide.addText(DATA.remote_skills.headline, {
    x: 8.10, y: 2.90, w: 4.50, h: 0.88,
    fontFace: 'Aptos Display', fontSize: 23, bold: true, color: C.TEXT,
    margin: 0,
  });
  slide.addText(DATA.remote_skills.summary, {
    x: 8.10, y: 3.94, w: 4.45, h: 0.72,
    fontFace: 'Aptos', fontSize: 12.3, color: C.MUTED, margin: 0,
  });

  metric(slide, String(DATA.remote_skills.rows_used), 'matching remote postings', 8.10, 4.84, 2.07, C.BLUE);
  metric(slide, `${DATA.remote_skills.confidence_score}/100`, 'evidence-based confidence', 10.40, 4.84, 2.08, C.GREEN);
  slide.addText('Evidence Passport', {
    x: 8.10, y: 6.02, w: 1.58, h: 0.20,
    fontFace: 'Aptos', fontSize: 10, bold: true, color: C.MUTED, margin: 0,
  });
  slide.addText(DATA.remote_skills.proof_id, {
    x: 9.72, y: 5.98, w: 2.76, h: 0.28,
    fontFace: 'Aptos', fontSize: 12.5, bold: true, color: C.BLUE,
    margin: 0,
  });
  slide.addText('The same result can be inspected as a chart, table, source-row preview, query-plan JSON, masked CSV, and portable HTML report.', {
    x: 8.10, y: 6.38, w: 4.42, h: 0.44,
    fontFace: 'Aptos', fontSize: 10.5, color: C.MUTED, margin: 0,
  });
  addFooter(slide, 'Demo result is calculated from the bundled synthetic dataset, not generated from model memory.');
  addNotes(slide, [
    `CareerProof synthetic dataset fingerprint ${DATA.dataset.fingerprint}.`,
    `Verified analysis ${DATA.remote_skills.proof_id}: ${DATA.remote_skills.rows_used} matching postings, confidence ${DATA.remote_skills.confidence_score}/100.`,
  ]);
  finish(slide);
}

// Slide 5: Evidence Passport
{
  const slide = pptx.addSlide('LIGHT');
  addBrand(slide, false);
  addSectionTitle(slide, 'Evidence passport', 'The answer is only the beginning', 'Each result exposes how it was produced, what data it used, and where uncertainty remains.');

  const top = DATA.remote_skills.top_rows;
  slide.addText('TOP SIGNALS IN REMOTE POSTINGS', {
    x: 0.70, y: 2.30, w: 3.2, h: 0.25,
    fontFace: 'Aptos', fontSize: 10.5, bold: true, color: C.MUTED,
    charSpacing: 1.3, margin: 0,
  });
  const maxVal = Math.max(...top.map(r => r.Postings));
  top.forEach((row, i) => {
    const y = 2.73 + i * 0.55;
    slide.addText(row.Skill, {
      x: 0.70, y: y + 0.05, w: 1.67, h: 0.22,
      fontFace: 'Aptos', fontSize: 11, color: C.TEXT, margin: 0,
    });
    slide.addShape(pptx.ShapeType.roundRect, {
      x: 2.42, y: y, w: 3.25, h: 0.30,
      rectRadius: 0.10,
      fill: { color: 'E7EDF5' }, line: { color: 'E7EDF5' },
    });
    slide.addShape(pptx.ShapeType.roundRect, {
      x: 2.42, y: y, w: 3.25 * row.Postings / maxVal, h: 0.30,
      rectRadius: 0.10,
      fill: { color: i === 0 ? C.GREEN : C.BLUE }, line: { color: i === 0 ? C.GREEN : C.BLUE },
    });
    slide.addText(String(row.Postings), {
      x: 5.82, y: y + 0.02, w: 0.44, h: 0.20,
      fontFace: 'Aptos', fontSize: 10.5, bold: true, color: C.TEXT, align: 'right', margin: 0,
    });
  });

  slide.addText('VISIBLE QUERY PLAN', {
    x: 6.75, y: 2.30, w: 2.2, h: 0.25,
    fontFace: 'Aptos', fontSize: 10.5, bold: true, color: C.MUTED,
    charSpacing: 1.3, margin: 0,
  });
  slide.addText(`{
  "intent": "skill_frequency",
  "filters": ["work_mode = Remote"],
  "skill_columns": ["required_skills"],
  "limit": 10,
  "chart_type": "bar"
}`, {
    x: 6.75, y: 2.74, w: 5.85, h: 2.08,
    fontFace: 'Aptos Mono', fontSize: 12.4, color: 'DDF2FF',
    fill: { color: C.NAVY }, line: { color: '244A6A', pt: 1 },
    radius: 0.12, margin: 0.22, breakLine: false,
  });

  card(slide, 'Calculation', `${DATA.remote_skills.rows_used} rows after filters\nEach skill counted once per posting\nSorted by posting count`, 0.70, 5.43, 3.45, 1.16, { accent: C.BLUE, fontSize: 11.5, titleSize: 14.5 });
  card(slide, 'Confidence', `${DATA.remote_skills.confidence_score}/100\nDriven by row count, completeness, intent certainty, and data-quality score`, 4.39, 5.43, 3.45, 1.16, { accent: C.GREEN, fontSize: 11.2, titleSize: 14.5 });
  card(slide, 'Privacy', 'Names, emails, phone numbers, and source IDs are masked before the UI, report, export, or audit log.', 8.08, 5.43, 4.52, 1.16, { accent: C.PURPLE, fontSize: 11.2, titleSize: 14.5 });
  addFooter(slide, `Evidence ID ${DATA.remote_skills.proof_id} changes when the dataset, query plan, or result changes.`);
  addNotes(slide, [
    `CareerProof verified result ${DATA.remote_skills.proof_id} generated from bundled synthetic data.`,
    'CareerProof AI source code: evidence.py, privacy.py, confidence.py, query_executor.py.',
  ]);
  finish(slide);
}

// Slide 6: Unique features
{
  const slide = pptx.addSlide('DARK');
  addBrand(slide, true);
  addSectionTitle(slide, 'Beyond the minimum', 'Four features that make the product memorable', 'Each feature adds practical value without weakening the trust model.', true);

  const features = [
    ['ID', 'Evidence Passport', 'Recompute the ID, then replay the validated plan when the active dataset matches.', C.BLUE],
    ['?', 'Refusal Coach', 'Explains why a question is unsupported and suggests the closest answerable alternatives.', C.ORANGE],
    ['SK', 'Career Signal Lab', 'Compares a user skill list with transparent role-level frequency signals. It is not a hiring score.', C.GREEN],
    ['QL', 'Cleaning Ledger', 'Shows every cleaning action, invalid row, missing field, and quality warning instead of hiding them.', C.PURPLE],
  ];
  features.forEach((f, i) => {
    const col = i % 2;
    const row = Math.floor(i / 2);
    const x = 0.72 + col * 6.15;
    const y = 2.45 + row * 2.05;
    smallIcon(slide, f[0], x, y + 0.10, f[3], true);
    slide.addText(f[1], {
      x: x + 0.64, y, w: 4.55, h: 0.35,
      fontFace: 'Aptos Display', fontSize: 18, bold: true, color: C.WHITE, margin: 0,
    });
    slide.addText(f[2], {
      x: x + 0.64, y: y + 0.52, w: 4.80, h: 0.78,
      fontFace: 'Aptos', fontSize: 12.3, color: 'BDD0E3', margin: 0,
    });
    slide.addShape(pptx.ShapeType.line, {
      x: x + 0.64, y: y + 1.50, w: 4.84, h: 0,
      line: { color: '294A68', pt: 1 },
    });
  });

  slide.addText('Also included', {
    x: 0.72, y: 6.60, w: 1.15, h: 0.22,
    fontFace: 'Aptos', fontSize: 10, bold: true, color: '8EABC5', margin: 0,
  });
  pill(slide, 'SCENARIO COMPARE', 1.98, 6.52, 1.74, C.NAVY2, C.WHITE, 9);
  pill(slide, 'MASKED AUDIT LOG', 3.88, 6.52, 1.72, C.NAVY2, C.WHITE, 9);
  pill(slide, 'HTML REPORT EXPORT', 5.76, 6.52, 1.80, C.NAVY2, C.WHITE, 9);
  pill(slide, 'NO API KEY REQUIRED', 7.72, 6.52, 1.75, C.NAVY2, C.WHITE, 9);
  pill(slide, 'CSV / XLSX UPLOAD', 9.63, 6.52, 1.70, C.NAVY2, C.WHITE, 9);
  addFooter(slide, 'Unique does not mean unsafe: every advanced feature still uses the same validated calculation pipeline.', true);
  addNotes(slide, [
    'CareerProof AI user interface and source modules: ui.py, insights.py, evidence.py, audit.py, data_quality.py.',
    'Participant_Guide_Updated(1).pdf, page 8: optional Track 2 layers include masking, unsupported-question handling, natural language to Pandas, confidence labels, and report export.',
  ]);
  finish(slide);
}

// Slide 7: trust and QA
{
  const slide = pptx.addSlide('LIGHT');
  addBrand(slide, false);
  addSectionTitle(slide, 'Trust + quality', 'Designed to fail safely and prove it', 'The product is tested against normal questions, malformed data, private-data requests, and prompt-injection attempts.');

  const controls = [
    ['Invented numbers', 'Deterministic Pandas executor', C.GREEN],
    ['Arbitrary code', 'Typed query plan + operation allowlist', C.BLUE],
    ['PII exposure', 'Mask before UI, export, report, or log', C.PURPLE],
    ['Tiny samples', 'Minimum group size + confidence downgrade', C.ORANGE],
    ['Missing fields', 'Unsupported-question refusal', C.RED],
  ];
  slide.addText('RISK', { x: 0.75, y: 2.33, w: 2.1, h: 0.22, fontSize: 10, bold: true, color: C.MUTED, charSpacing: 1.2, margin: 0 });
  slide.addText('VISIBLE CONTROL', { x: 3.40, y: 2.33, w: 3.2, h: 0.22, fontSize: 10, bold: true, color: C.MUTED, charSpacing: 1.2, margin: 0 });
  controls.forEach((row, i) => {
    const y = 2.75 + i * 0.65;
    slide.addText(row[0], {
      x: 0.75, y, w: 2.35, h: 0.33,
      fontFace: 'Aptos', fontSize: 12, color: C.TEXT,
      margin: 0,
    });
    slide.addShape(pptx.ShapeType.line, {
      x: 3.05, y: y + 0.12, w: 0.25, h: 0,
      line: { color: row[2], pt: 2.3, beginArrowType: 'none', endArrowType: 'triangle' },
    });
    slide.addText(row[1], {
      x: 3.42, y, w: 3.95, h: 0.33,
      fontFace: 'Aptos', fontSize: 12, bold: true, color: C.TEXT,
      margin: 0,
    });
    slide.addShape(pptx.ShapeType.line, {
      x: 0.75, y: y + 0.47, w: 6.62, h: 0,
      line: { color: C.LINE, pt: 0.8 },
    });
  });

  metric(slide, String(DATA.qa.pytest_count), 'automated tests passed', 7.82, 2.38, 2.15, C.BLUE);
  metric(slide, `${DATA.qa.demo_checks_passed}/${DATA.qa.demo_checks_total}`, 'judge-ready checks passed', 10.24, 2.38, 2.15, C.GREEN);
  metric(slide, `${DATA.dataset.quality_score}/100`, 'bundled data-quality score', 7.82, 3.58, 2.15, C.PURPLE);
  metric(slide, '0', 'API keys required', 10.24, 3.58, 2.15, C.ORANGE);

  slide.addText('SAFE REFUSAL DEMO', {
    x: 7.82, y: 4.92, w: 2.3, h: 0.22,
    fontFace: 'Aptos', fontSize: 10.5, bold: true, color: C.MUTED,
    charSpacing: 1.2, margin: 0,
  });
  slide.addText(`“${DATA.refusal.question}”`, {
    x: 7.82, y: 5.30, w: 4.55, h: 0.42,
    fontFace: 'Aptos Display', fontSize: 17.5, bold: true, color: C.TEXT, margin: 0,
  });
  slide.addText(`${DATA.refusal.headline}. ${DATA.refusal.summary}`, {
    x: 7.82, y: 5.86, w: 4.55, h: 0.64,
    fontFace: 'Aptos', fontSize: 12, color: C.MUTED, margin: 0,
  });
  pill(slide, DATA.refusal.proof_id, 9.83, 6.54, 2.54, C.RED_LIGHT, C.RED, 9.5);
  addFooter(slide, 'Known limitations are shown in the product and presentation rather than hidden.');
  addNotes(slide, [
    `CareerProof AI pytest result: ${DATA.qa.pytest_count} passed. Demo checker result: ${DATA.qa.demo_checks_passed}/${DATA.qa.demo_checks_total} passed.`,
    `Safe refusal proof ${DATA.refusal.proof_id}.`,
    'Participant_Guide_Updated(1).pdf, pages 7-8 and 11: unsupported-question handling and meaningful trust controls are explicit evaluation priorities.',
  ]);
  finish(slide);
}

// Slide 8: rubric and close
{
  const slide = pptx.addSlide('DARK');
  addBrand(slide, true);
  addSectionTitle(slide, 'Why it is submission-ready', 'Built around what the judges actually score', 'A useful end-to-end product first, with trust, evidence, clear architecture, and a concise story.', true);

  const rubric = [
    ['Problem + usefulness', 25, C.GREEN, 'Clear early-career user problem'],
    ['Working prototype', 25, C.BLUE, 'Upload → question → proof → export'],
    ['Data + AI quality', 15, C.PURPLE, 'Local intent AI + deterministic math'],
    ['Trust + safety', 15, C.ORANGE, 'Masking, refusal, confidence, audit'],
    ['Architecture clarity', 10, C.TEAL, 'Simple input-to-output flow'],
    ['Demo + storytelling', 10, '7DA4D8', 'Success case + limitation case'],
  ];
  rubric.forEach((r, i) => {
    const y = 2.42 + i * 0.62;
    slide.addText(r[0], {
      x: 0.72, y: y + 0.05, w: 2.10, h: 0.22,
      fontFace: 'Aptos', fontSize: 11, color: C.WHITE, margin: 0,
    });
    slide.addShape(pptx.ShapeType.roundRect, {
      x: 2.88, y, w: 2.85, h: 0.28,
      rectRadius: 0.09,
      fill: { color: '24435F' }, line: { color: '24435F' },
    });
    slide.addShape(pptx.ShapeType.roundRect, {
      x: 2.88, y, w: 2.85 * r[1] / 25, h: 0.28,
      rectRadius: 0.09,
      fill: { color: r[2] }, line: { color: r[2] },
    });
    slide.addText(`${r[1]}%`, {
      x: 5.92, y: y + 0.03, w: 0.48, h: 0.20,
      fontFace: 'Aptos', fontSize: 10.5, bold: true, color: C.WHITE, align: 'right', margin: 0,
    });
    slide.addText(r[3], {
      x: 6.60, y: y + 0.03, w: 2.62, h: 0.24,
      fontFace: 'Aptos', fontSize: 10.3, color: 'BDD0E3', margin: 0,
    });
  });

  slide.addShape(pptx.ShapeType.roundRect, {
    x: 9.52, y: 2.36, w: 3.07, h: 3.62,
    rectRadius: 0.16,
    fill: { color: C.NAVY2 }, line: { color: '2D5675', pt: 1 }, shadow: SH,
  });
  slide.addText('READY TO SUBMIT', {
    x: 9.84, y: 2.62, w: 2.42, h: 0.25,
    fontFace: 'Aptos', fontSize: 10.5, bold: true, color: C.GREEN,
    charSpacing: 1.3, align: 'center', margin: 0,
  });
  slide.addText('CareerProof AI', {
    x: 9.78, y: 3.05, w: 2.55, h: 0.45,
    fontFace: 'Aptos Display', fontSize: 22, bold: true, color: C.WHITE,
    align: 'center', margin: 0,
  });
  slide.addText('Ask the job market.\nSee the proof.', {
    x: 9.92, y: 3.67, w: 2.30, h: 0.78,
    fontFace: 'Aptos Display', fontSize: 18, bold: true, color: 'C7DAEA',
    align: 'center', margin: 0,
  });
  pill(slide, '646 CLEANED ROWS', 9.95, 4.70, 2.18, C.GREEN, C.WHITE, 9.5);
  pill(slide, '12 / 12 DEMOS', 9.95, 5.12, 2.18, C.BLUE, C.WHITE, 9.5);
  slide.addText('This dataset is synthetic. Limitations disclosed. No external API required.', {
    x: 9.82, y: 5.57, w: 2.44, h: 0.34,
    fontFace: 'Aptos', fontSize: 9.6, color: '9FB8CE', align: 'center', margin: 0,
  });

  slide.addText('Final manual steps', {
    x: 0.72, y: 6.35, w: 1.35, h: 0.22,
    fontFace: 'Aptos', fontSize: 10, bold: true, color: '8EABC5', margin: 0,
  });
  slide.addText('Push public GitHub history · record the ≤10-minute video · add team details · upload the verified ZIP', {
    x: 2.15, y: 6.32, w: 6.82, h: 0.32,
    fontFace: 'Aptos', fontSize: 11, color: C.WHITE, margin: 0,
  });
  addFooter(slide, 'CareerProof AI · Trustworthy answers require visible proof.', true);
  addNotes(slide, [
    'Participant_Guide_Updated(1).pdf, page 11: participant-facing judging weights.',
    'Participant_Guide_Updated(1).pdf, pages 14-15: repository, presentation, video, ZIP, disclosure, and no-secret requirements.',
    'CareerProof AI repository: verified local build and bundled synthetic dataset.',
  ]);
  finish(slide);
}

pptx.writeFile({ fileName: OUT });
console.log(`Wrote ${OUT}`);
