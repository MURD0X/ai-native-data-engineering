/* ============================================================
   AI-Native Data Systems — Bootstrap Standards Explorer
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
    ${buildTaskBanner()}
    ${buildConstraintsBar()}
    <div class="main-grid">
      ${buildCodePanel('before')}
      ${buildCodePanel('after')}
    </div>
    ${buildTranscriptSection()}
    ${buildConstraintDetail()}
    ${buildConclusion()}
  `;
}

// ----------------------------------------------------------------
// Task Banner
// ----------------------------------------------------------------

function buildTaskBanner() {
  return `
    <div class="task-banner">
      <div class="label">Agent Task</div>
      <div class="task-text">"${DATA.agent_task}"</div>
    </div>
  `;
}

// ----------------------------------------------------------------
// Constraints Bar
// ----------------------------------------------------------------

function buildConstraintsBar() {
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
    <div class="constraints-bar">
      <div class="constraints-bar-label">Engineering Constraints — click to filter</div>
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

  return `
    <div class="panel">
      <div class="panel-header ${side}">
        <span class="panel-badge ${side}">${isAfter ? 'After' : 'Before'}</span>
        <span class="panel-title">${d.label}</span>
      </div>
      <p class="panel-summary">${d.summary}</p>
      ${isAfter ? buildMetadataSnippet(d) : buildMissingBadges(d)}
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

function buildMissingBadges(d) {
  const labels = {
    schema_contract: 'No schema contract',
    tests: 'No tests',
    governance: 'No governance metadata',
    git: 'No Git history',
    schedule: 'No schedule metadata',
  };
  const badges = (d.missing || []).map(id =>
    `<span class="impact-badge before" style="display:inline-block;margin:0 0.25rem 0.25rem 0">${labels[id]}</span>`
  ).join('');
  return `<div style="padding:0.5rem 1rem 0.375rem">${badges}</div>`;
}

function buildMetadataSnippet(d) {
  return `
    <div style="padding:0.5rem 1rem 0;font-size:0.75rem">
      <span style="color:var(--color-text-tertiary);font-weight:600;text-transform:uppercase;letter-spacing:0.06em;font-size:0.68rem">
        Key metadata
      </span>
      <pre style="background:var(--color-after-bg);border:1px solid var(--color-after-border);border-radius:4px;padding:0.4rem 0.6rem;margin-top:0.25rem;font-family:var(--font-mono);font-size:0.72rem;color:var(--color-after);overflow-x:auto;line-height:1.5">${escapeHtml(d.metadata_excerpt)}</pre>
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
    if (raw.includes('is_vip_customer') && raw.includes('VIP_REVENUE_THRESHOLD')) return 'success';
    if (raw.includes('never_expose') || raw.includes('output_columns')) return 'success';
    if (raw.includes('governance') || raw.includes('pii')) return 'highlighted';
    if (raw.includes('validate_output') || raw.includes('pytest')) return 'success';
  }
  return '';
}

function syntaxHighlight(line) {
  let h = escapeHtml(line);
  // comments
  h = h.replace(/(#.*)$/, '<span class="cm">$1</span>');
  // docstrings (triple quote lines)
  if (h.trim().startsWith('&quot;&quot;&quot;') || h.trim().endsWith('&quot;&quot;&quot;')) {
    h = `<span class="dc">${h}</span>`;
  }
  // strings
  h = h.replace(/(&quot;[^&]*?&quot;|&#39;[^&#]*?&#39;)/g, '<span class="st">$1</span>');
  // keywords
  h = h.replace(/\b(def|class|import|from|return|if|else|elif|for|in|not|and|or|raise|with|as|True|False|None|pass|lambda)\b/g, '<span class="kw">$1</span>');
  // built-in functions
  h = h.replace(/\b(print|len|range|str|int|float|bool|list|dict|set|open|None)\b/g, '<span class="nb">$1</span>');
  // numbers
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
  const afterSteps = DATA.after_interaction.steps;

  const beforeCol = beforeSteps.map(s => buildStepCard(s, 'before')).join('');
  const afterCol = afterSteps.map(s => buildStepCard(s, 'after')).join('');

  return `
    <div class="transcript-container">
      <div class="transcript-header">
        <h2>Agent Interaction — Step by Step</h2>
        <div class="mode-toggle">
          <button class="active" id="toggle-side-by-side">Side by Side</button>
          <button id="toggle-before-only">Before Only</button>
          <button id="toggle-after-only">After Only</button>
        </div>
      </div>
      <div class="transcript-body" id="transcript-body">
        <div class="transcript-column" id="col-before">
          <div class="transcript-col-header before">Before — What Failed</div>
          ${beforeCol}
        </div>
        <div class="transcript-column" id="col-after">
          <div class="transcript-col-header after">After — What Succeeded</div>
          ${afterCol}
        </div>
      </div>
    </div>
  `;
}

function buildStepCard(step, side) {
  const outcome = side === 'before' ? 'failure' : 'success';
  const constraint = DATA.constraints.find(c => c.id === step.constraint_id);
  const constraintName = constraint ? constraint.name : step.constraint_id;

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
        <span class="step-number ${outcome}">${step.id}</span>
        <span class="step-intent">${step.agent_intent}</span>
      </div>
      <div class="step-action">${step.agent_action}</div>
      <div class="step-outcome ${outcome}">
        ${outcome === 'failure' ? '✗' : '✓'} ${step.outcome}
      </div>
      <span class="step-constraint-tag" data-constraint-id="${step.constraint_id}">${constraintName}</span>
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
// Constraint Detail
// ----------------------------------------------------------------

function buildConstraintDetail() {
  const cards = DATA.constraints.map(c => {
    const isActive = activeConstraint === c.id;
    return `
      <div class="constraint-card ${isActive ? 'active' : ''}" data-constraint-card="${c.id}">
        <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:0.375rem">
          <div class="constraint-card-name">${c.name}</div>
          <span class="severity ${c.severity}">${c.severity}</span>
        </div>
        <div class="constraint-card-file">${c.file}</div>
        <div class="constraint-card-desc">${c.description}</div>
        <div class="constraint-impact">
          <div class="impact-badge before">
            <span class="impact-label">Before</span>
            ${c.before_impact}
          </div>
          <div class="impact-badge after">
            <span class="impact-label">After</span>
            ${c.after_impact}
          </div>
        </div>
      </div>
    `;
  }).join('');

  return `
    <div class="constraint-detail">
      <div class="constraint-detail-header">
        <h2>Engineering Constraints — What Made the Difference</h2>
      </div>
      <div class="constraint-grid">${cards}</div>
    </div>
  `;
}

// ----------------------------------------------------------------
// Conclusion
// ----------------------------------------------------------------

function buildConclusion() {
  return `
    <div class="conclusion">
      <h2>"Unstructured systems break AI in days, humans in months."</h2>
      <p>
        The agent didn't fail in the before state because it was careless.
        It failed because it operated without context.
        The after state succeeded because the system gave the agent
        the information it needed to make the right decisions.
      </p>
      <div class="links">
        <a href="../PATTERN.md">Read the full guide →</a>
        <a href="../before/pipeline.py">Before code</a>
        <a href="../after/pipeline.py">After code</a>
        <a href="../agent-run/COMPARISON.md">Full comparison</a>
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
      const [side, num] = stepId.split('-');
      const detailEl = document.getElementById(`detail-${side}-${num}`);

      if (activeStep === stepId) {
        activeStep = null;
        detailEl && detailEl.classList.remove('visible');
        card.classList.remove('active');
        clearCodeHighlights();
      } else {
        // Clear previous
        document.querySelectorAll('.step-card.active').forEach(c => c.classList.remove('active'));
        document.querySelectorAll('.step-detail.visible').forEach(d => d.classList.remove('visible'));
        clearCodeHighlights();

        activeStep = stepId;
        card.classList.add('active');
        detailEl && detailEl.classList.add('visible');

        // Highlight relevant constraint
        const constraintId = card.dataset.constraintId;
        highlightConstraint(constraintId);
      }
    });
  });

  // Constraint tags in step cards
  document.querySelectorAll('.step-constraint-tag').forEach(tag => {
    tag.addEventListener('click', (e) => {
      e.stopPropagation();
      const id = tag.dataset.constraintId;
      scrollToConstraint(id);
    });
  });

  // Constraint cards
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
        btn.textContent = 'Copied!';
        setTimeout(() => btn.textContent = 'Copy', 1500);
      });
    });
  });

  // Transcript mode toggle
  document.getElementById('toggle-side-by-side')?.addEventListener('click', () => {
    setTranscriptMode('side-by-side');
  });
  document.getElementById('toggle-before-only')?.addEventListener('click', () => {
    setTranscriptMode('before-only');
  });
  document.getElementById('toggle-after-only')?.addEventListener('click', () => {
    setTranscriptMode('after-only');
  });
}

function setTranscriptMode(mode) {
  const body = document.getElementById('transcript-body');
  const colBefore = document.getElementById('col-before');
  const colAfter = document.getElementById('col-after');

  document.querySelectorAll('.mode-toggle button').forEach(b => b.classList.remove('active'));

  if (mode === 'side-by-side') {
    document.getElementById('toggle-side-by-side').classList.add('active');
    body.style.gridTemplateColumns = '1fr 1fr';
    colBefore.style.display = '';
    colAfter.style.display = '';
  } else if (mode === 'before-only') {
    document.getElementById('toggle-before-only').classList.add('active');
    body.style.gridTemplateColumns = '1fr';
    colBefore.style.display = '';
    colAfter.style.display = 'none';
  } else if (mode === 'after-only') {
    document.getElementById('toggle-after-only').classList.add('active');
    body.style.gridTemplateColumns = '1fr';
    colBefore.style.display = 'none';
    colAfter.style.display = '';
  }
}

function highlightConstraint(constraintId) {
  // Dim non-matching step cards
  document.querySelectorAll('.step-card').forEach(card => {
    if (!constraintId || card.dataset.constraintId === constraintId) {
      card.style.opacity = '1';
    } else {
      card.style.opacity = '0.4';
    }
  });
}

function clearCodeHighlights() {
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
