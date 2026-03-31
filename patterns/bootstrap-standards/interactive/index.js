/* ============================================================
   AI-Native Data Systems — Bootstrap Standards Case Study
   ============================================================ */

let DATA = null;
let activeStep = null;
let activeConstraint = null;
let activeConstraintFilters = new Set();

// ----------------------------------------------------------------
// Bootstrap
// ----------------------------------------------------------------

async function init() {
  try {
    const res = await fetch('data.json');
    DATA = await res.json();
    render();
  } catch (e) {
    document.getElementById('app').innerHTML =
      `<div class="loading">Failed to load data.json: ${e.message}</div>`;
  }
}

function render() {
  document.getElementById('app').innerHTML = buildApp();
  attachListeners();
}

// ----------------------------------------------------------------
// App shell
// ----------------------------------------------------------------

function buildApp() {
  return `
    ${buildFindingCallout()}
    ${buildBrief()}
    ${buildControlsFilter()}
    <div class="section-wrap">
      <div class="section-header">
        <span class="section-eyebrow">Pipeline Comparison</span>
        <h2>Two pipelines. One agent. Identical task.</h2>
        <p>The agent's behavior is consistent across both scenarios. The outcome is determined entirely by the engineering infrastructure.</p>
      </div>
      <div class="main-grid">
        ${buildCodePanel('before')}
        ${buildCodePanel('after')}
      </div>
    </div>
    ${buildTranscriptSection()}
    ${buildControlsAnalysis()}
    ${buildClosingStatement()}
  `;
}

// ----------------------------------------------------------------
// Finding Callout
// ----------------------------------------------------------------

function buildFindingCallout() {
  const beforeFailures = DATA.before_interaction.steps.length;
  const afterSuccesses = DATA.after_interaction.steps.length;
  const testCount = 24;

  return `
    <div class="finding-callout">
      <div class="finding-eyebrow">Core Finding</div>
      <div class="finding-quote">
        "The agent didn't fail because it was careless.<br>
        It failed because the system gave it nothing to be careful with."
      </div>
      <p class="finding-body">
        This case study runs the same AI agent on the same task against two versions of the same pipeline.
        In the unstructured version, it produces compliance violations, incorrect data, and no audit trail.
        In the engineered version, it succeeds across every dimension — because the system is safe by construction.
      </p>
      <div class="finding-stats">
        <div class="finding-stat">
          <span class="finding-stat-value failure-val">${beforeFailures}</span>
          <span class="finding-stat-label">Failure modes<br>without engineering</span>
        </div>
        <div class="finding-stat">
          <span class="finding-stat-value success-val">${afterSuccesses}</span>
          <span class="finding-stat-label">Correct outcomes<br>with engineering</span>
        </div>
        <div class="finding-stat">
          <span class="finding-stat-value success-val">${testCount}</span>
          <span class="finding-stat-label">Tests validating<br>the contract</span>
        </div>
        <div class="finding-stat">
          <span class="finding-stat-value success-val">${DATA.constraints.length}</span>
          <span class="finding-stat-label">Engineering controls<br>that made the difference</span>
        </div>
      </div>
    </div>
  `;
}

// ----------------------------------------------------------------
// Brief
// ----------------------------------------------------------------

function buildBrief() {
  const p = DATA.pipeline;
  return `
    <div class="brief-grid">
      <div class="brief-main">
        <div class="brief-eyebrow">Agent Brief</div>
        <div class="brief-task">"${DATA.agent_task}"</div>
      </div>
      <div class="brief-meta">
        <div class="brief-meta-item">
          <span class="brief-meta-label">Pipeline</span>
          <span class="brief-meta-value">${p.name}</span>
        </div>
        <div class="brief-meta-item">
          <span class="brief-meta-label">Output Grain</span>
          <span class="brief-meta-value">${p.grain}</span>
        </div>
        <div class="brief-meta-item">
          <span class="brief-meta-label">SLA</span>
          <span class="brief-meta-value">${p.sla}</span>
        </div>
        <div class="brief-meta-item">
          <span class="brief-meta-label">Business Value</span>
          <span class="brief-meta-value" style="font-family:var(--font-sans);font-size:0.73rem;line-height:1.4">${p.business_value}</span>
        </div>
      </div>
    </div>
  `;
}

// ----------------------------------------------------------------
// Controls Filter
// ----------------------------------------------------------------

function buildControlsFilter() {
  const pills = DATA.constraints.map(c => {
    const active = activeConstraintFilters.size === 0 || activeConstraintFilters.has(c.id);
    return `
      <button
        class="constraint-pill ${active ? 'active' : 'inactive'}"
        data-constraint-id="${c.id}"
        title="${c.description}"
      >
        <span class="dot"></span>
        ${c.name}
        <span class="severity ${c.severity}">${c.severity}</span>
      </button>
    `;
  }).join('');

  return `
    <div class="controls-filter">
      <div class="controls-filter-label">Filter by control</div>
      <div class="controls-filter-divider"></div>
      <div class="constraints-list">${pills}</div>
    </div>
  `;
}

// ----------------------------------------------------------------
// Code Panels
// ----------------------------------------------------------------

function buildCodePanel(side) {
  const d = DATA[side];
  const isAfter = side === 'after';
  const filename = isAfter ? 'after/pipeline.py' : 'before/pipeline.py';
  const exhibitNum = isAfter ? '2' : '1';

  return `
    <div class="panel">
      <div class="panel-exhibit-label">Exhibit ${exhibitNum}</div>
      <div class="panel-header ${side}">
        <span class="panel-badge ${side}">${isAfter ? 'After' : 'Before'}</span>
        <span class="panel-title">${d.label}</span>
      </div>
      <p class="panel-summary">${d.summary}</p>
      ${isAfter ? buildMetadataBar(d) : buildMissingBar(d)}
      <div class="code-header">
        <span class="code-filename">${filename}</span>
        <button class="copy-btn" data-copy-side="${side}">Copy</button>
      </div>
      <div class="code-block" id="code-${side}">
        <pre>${renderCode(d.code, side)}</pre>
      </div>
    </div>
  `;
}

function buildMissingBar(d) {
  const labels = {
    schema_contract: 'No schema contract',
    tests:           'No tests',
    governance:      'No governance metadata',
    git:             'No Git discipline',
    schedule:        'No schedule metadata',
  };
  const badges = (d.missing || []).map(id =>
    `<span class="missing-badge">${labels[id] || id}</span>`
  ).join('');
  return `<div class="panel-missing-bar">${badges}</div>`;
}

function buildMetadataBar(d) {
  return `
    <div class="panel-meta-bar">
      <div class="meta-label">Key metadata (metadata.yaml)</div>
      <pre class="meta-pre">${escapeHtml(d.metadata_excerpt)}</pre>
    </div>
  `;
}

// ----------------------------------------------------------------
// Syntax Highlighting (lightweight)
// ----------------------------------------------------------------

function renderCode(code, side) {
  const lines = code.split('\n');
  return lines.map((raw, i) => {
    const lineNum = i + 1;
    const highlighted = syntaxHighlight(raw);
    const classes = getLineClasses(lineNum, raw, side);
    return `<span class="line ${classes}" data-line="${lineNum}">${highlighted}</span>`;
  }).join('\n');
}

function getLineClasses(lineNum, raw, side) {
  if (side === 'before') {
    if (raw.includes('rolling_30d_revenue') && raw.includes('5000')) return 'failure';
    if (raw.includes('customer_name') || raw.includes("'address'")) return 'failure';
  }
  if (side === 'after') {
    if (raw.includes('is_vip_customer') && raw.includes('vip_threshold')) return 'success';
    if (raw.includes('never_expose') || raw.includes('output_columns')) return 'success';
    if (raw.includes('governance') || raw.includes('pii')) return 'highlighted';
    if (raw.includes('validate_output') || raw.includes('pytest')) return 'success';
  }
  return '';
}

function syntaxHighlight(line) {
  let h = escapeHtml(line);
  h = h.replace(/(#.*)$/, '<span class="cm">$1</span>');
  if (h.trim().startsWith('&quot;&quot;&quot;') || h.trim().endsWith('&quot;&quot;&quot;')) {
    h = `<span class="dc">${h}</span>`;
  }
  h = h.replace(/(&quot;[^&]*?&quot;|&#39;[^&#]*?&#39;)/g, '<span class="st">$1</span>');
  h = h.replace(/\b(def|class|import|from|return|if|else|elif|for|in|not|and|or|raise|with|as|True|False|None|pass|lambda)\b/g, '<span class="kw">$1</span>');
  h = h.replace(/\b(print|len|range|str|int|float|bool|list|dict|set|open|None)\b/g, '<span class="nb">$1</span>');
  h = h.replace(/\b(\d[\d_]*\.?\d*)\b/g, '<span class="nb">$1</span>');
  return h;
}

function escapeHtml(str) {
  return str
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

// ----------------------------------------------------------------
// Transcript Section
// ----------------------------------------------------------------

function buildTranscriptSection() {
  const beforeSteps = DATA.before_interaction.steps;
  const afterSteps  = DATA.after_interaction.steps;

  const beforeCol = beforeSteps.map(s => buildStepCard(s, 'before')).join('');
  const afterCol  = afterSteps.map(s => buildStepCard(s, 'after')).join('');

  return `
    <div class="section-wrap">
      <div class="transcript-container">
        <div class="transcript-header">
          <div class="transcript-header-text">
            <span class="section-eyebrow">Comparative Analysis</span>
            <h2>Agent Interaction — Step by Step</h2>
          </div>
          <div class="mode-toggle">
            <button class="active" id="toggle-side-by-side">Side by Side</button>
            <button id="toggle-before-only">Before</button>
            <button id="toggle-after-only">After</button>
          </div>
        </div>
        <div class="transcript-body" id="transcript-body">
          <div class="transcript-column" id="col-before">
            <div class="transcript-col-header before">
              <span class="col-header-dot"></span>
              Scenario A — Unstructured Pipeline
            </div>
            ${beforeCol}
          </div>
          <div class="transcript-column" id="col-after">
            <div class="transcript-col-header after">
              <span class="col-header-dot"></span>
              Scenario B — Engineered Pipeline
            </div>
            ${afterCol}
          </div>
        </div>
      </div>
    </div>
  `;
}

function buildStepCard(step, side) {
  const outcome = side === 'before' ? 'failure' : 'success';
  const constraint = DATA.constraints.find(c => c.id === step.constraint_id);
  const constraintName = constraint ? constraint.name : step.constraint_id;
  const stepLabel = String(step.id).padStart(2, '0');

  const isFiltered = activeConstraintFilters.size > 0 && !activeConstraintFilters.has(step.constraint_id);
  const displayStyle = isFiltered ? 'display:none' : '';

  return `
    <div
      class="step-card ${outcome}"
      data-step-id="${side}-${step.id}"
      data-constraint-id="${step.constraint_id}"
      style="${displayStyle}"
    >
      <div class="step-header">
        <span class="step-number ${outcome}">${stepLabel}</span>
        <span class="step-intent">${step.agent_intent}</span>
      </div>
      <div class="step-action">${step.agent_action}</div>
      <div class="step-outcome ${outcome}">
        <span class="step-outcome-icon">${outcome === 'failure' ? '✕' : '✓'}</span>
        ${step.outcome}
      </div>
      <span class="step-constraint-tag" data-constraint-id="${step.constraint_id}">↗ ${constraintName}</span>
      <div class="step-detail" id="detail-${side}-${step.id}">
        <p>${side === 'before' ? step.assumption_made || '' : (step.constraint_applied || '')}</p>
        <div class="why ${outcome}">
          ${side === 'before' ? step.why_it_failed : step.why_it_succeeded}
        </div>
      </div>
    </div>
  `;
}

// ----------------------------------------------------------------
// Controls Analysis (Constraint Detail)
// ----------------------------------------------------------------

function buildControlsAnalysis() {
  const cards = DATA.constraints.map((c, idx) => {
    const isActive = activeConstraint === c.id;
    const num = String(idx + 1).padStart(2, '0');
    return `
      <div class="constraint-card ${isActive ? 'active' : ''}" data-constraint-card="${c.id}">
        <div class="constraint-card-number">${num}</div>
        <div class="constraint-card-header">
          <div class="constraint-card-name">${c.name}</div>
          <span class="severity ${c.severity}">${c.severity}</span>
        </div>
        <div class="constraint-card-file">${c.file}</div>
        <div class="constraint-card-desc">${c.description}</div>
        <div class="constraint-impact">
          <div class="impact-block before">
            <span class="impact-block-label">Without</span>
            <div class="impact-block-text">${c.before_impact}</div>
          </div>
          <div class="impact-block after">
            <span class="impact-block-label">With</span>
            <div class="impact-block-text">${c.after_impact}</div>
          </div>
        </div>
      </div>
    `;
  }).join('');

  return `
    <div class="section-wrap">
      <div class="controls-detail">
        <div class="controls-detail-header">
          <span class="section-eyebrow">Engineering Controls</span>
          <h2>What Made the Difference</h2>
          <p>Five practices that are non-negotiable when AI agents operate on data infrastructure. Click any card to highlight related steps above.</p>
        </div>
        <div class="constraint-grid">${cards}</div>
      </div>
    </div>
  `;
}

// ----------------------------------------------------------------
// Closing Statement
// ----------------------------------------------------------------

function buildClosingStatement() {
  return `
    <div class="closing-statement">
      <div class="closing-eyebrow">Conclusion</div>
      <div class="closing-quote">
        "Unstructured systems don't just break under AI — they amplify every gap, instantly."
      </div>
      <p class="closing-body">
        A pipeline without tests works under human oversight for months.
        The same pipeline with an AI agent surfaces every edge case in its first week.
        The corner cut in 2023 becomes the production incident in 2024.
        Engineering discipline doesn't change because of AI — it becomes non-negotiable because of it.
      </p>
      <div class="closing-links">
        <a href="../PATTERN.md" target="_blank" rel="noopener" class="primary-link">Read the full guide →</a>
        <a href="../before/pipeline.py" target="_blank" rel="noopener">Before pipeline</a>
        <a href="../after/pipeline.py" target="_blank" rel="noopener">After pipeline</a>
        <a href="../agent-run/COMPARISON.md" target="_blank" rel="noopener">Full comparison</a>
        <a href="https://github.com/MURD0X/ai-native-data-engineering" target="_blank" rel="noopener">GitHub →</a>
      </div>
    </div>
  `;
}

// ----------------------------------------------------------------
// Event Listeners
// ----------------------------------------------------------------

function attachListeners() {
  // Constraint filter pills
  document.querySelectorAll('.constraint-pill').forEach(pill => {
    pill.addEventListener('click', () => {
      const id = pill.dataset.constraintId;
      if (activeConstraintFilters.has(id)) {
        activeConstraintFilters.delete(id);
      } else {
        activeConstraintFilters.add(id);
      }
      render();
    });
  });

  // Step cards — toggle detail + highlight
  document.querySelectorAll('.step-card').forEach(card => {
    card.addEventListener('click', () => {
      const stepId = card.dataset.stepId;
      const parts = stepId.split('-');
      const side = parts[0];
      const num  = parts[1];
      const detailEl = document.getElementById(`detail-${side}-${num}`);

      if (activeStep === stepId) {
        activeStep = null;
        detailEl && detailEl.classList.remove('visible');
        card.classList.remove('active');
        clearHighlights();
      } else {
        document.querySelectorAll('.step-card.active').forEach(c => c.classList.remove('active'));
        document.querySelectorAll('.step-detail.visible').forEach(d => d.classList.remove('visible'));
        clearHighlights();

        activeStep = stepId;
        card.classList.add('active');
        detailEl && detailEl.classList.add('visible');
        highlightConstraint(card.dataset.constraintId);
      }
    });
  });

  // Constraint tags in step cards — scroll to control card
  document.querySelectorAll('.step-constraint-tag').forEach(tag => {
    tag.addEventListener('click', (e) => {
      e.stopPropagation();
      scrollToConstraint(tag.dataset.constraintId);
    });
  });

  // Control cards — toggle active state and dim unrelated steps
  document.querySelectorAll('[data-constraint-card]').forEach(card => {
    card.addEventListener('click', () => {
      const id = card.dataset.constraintCard;
      activeConstraint = activeConstraint === id ? null : id;
      highlightConstraint(activeConstraint);
      render();
    });
  });

  // Copy buttons
  document.querySelectorAll('[data-copy-side]').forEach(btn => {
    btn.addEventListener('click', () => {
      const side = btn.dataset.copySide;
      const code = DATA[side].code;
      navigator.clipboard.writeText(code).then(() => {
        btn.textContent = 'Copied';
        setTimeout(() => btn.textContent = 'Copy', 1500);
      });
    });
  });

  // Transcript mode toggle
  document.getElementById('toggle-side-by-side')?.addEventListener('click', () => setTranscriptMode('side-by-side'));
  document.getElementById('toggle-before-only')?.addEventListener('click',   () => setTranscriptMode('before-only'));
  document.getElementById('toggle-after-only')?.addEventListener('click',    () => setTranscriptMode('after-only'));
}

function setTranscriptMode(mode) {
  const body      = document.getElementById('transcript-body');
  const colBefore = document.getElementById('col-before');
  const colAfter  = document.getElementById('col-after');

  document.querySelectorAll('.mode-toggle button').forEach(b => b.classList.remove('active'));

  if (mode === 'side-by-side') {
    document.getElementById('toggle-side-by-side').classList.add('active');
    body.style.gridTemplateColumns = '1fr 1fr';
    colBefore.style.display = '';
    colAfter.style.display  = '';
  } else if (mode === 'before-only') {
    document.getElementById('toggle-before-only').classList.add('active');
    body.style.gridTemplateColumns = '1fr';
    colBefore.style.display = '';
    colAfter.style.display  = 'none';
  } else if (mode === 'after-only') {
    document.getElementById('toggle-after-only').classList.add('active');
    body.style.gridTemplateColumns = '1fr';
    colBefore.style.display = 'none';
    colAfter.style.display  = '';
  }
}

function highlightConstraint(constraintId) {
  document.querySelectorAll('.step-card').forEach(card => {
    card.style.opacity = (!constraintId || card.dataset.constraintId === constraintId) ? '1' : '0.35';
  });
}

function clearHighlights() {
  document.querySelectorAll('.step-card').forEach(c => c.style.opacity = '1');
}

function scrollToConstraint(id) {
  const card = document.querySelector(`[data-constraint-card="${id}"]`);
  if (card) {
    card.scrollIntoView({ behavior: 'smooth', block: 'center' });
    card.classList.add('active');
    setTimeout(() => {
      if (activeConstraint !== id) card.classList.remove('active');
    }, 2000);
  }
}

// ----------------------------------------------------------------
// Start
// ----------------------------------------------------------------

document.addEventListener('DOMContentLoaded', init);
