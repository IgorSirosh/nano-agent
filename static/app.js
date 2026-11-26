/* NanoAgent v2.0 Frontend (Linear/Cursor Design + Free Gemini Distiller) */

const SVG_ICONS = {
  sidebar: '<rect width="18" height="18" x="3" y="3" rx="2"/><path d="M9 3v18"/>',
  plus: '<path d="M5 12h14"/><path d="M12 5v14"/>',
  search: '<circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/>',
  folder: '<path d="M20 20a2 2 0 0 0 2-2V8a2 2 0 0 0-2-2h-7.9a2 2 0 0 1-1.69-.9L9.6 3.9A2 2 0 0 0 7.93 3H4a2 2 0 0 0-2 2v13a2 2 0 0 0 2 2Z"/>',
  sparkles: '<path d="m12 3-1.912 5.813a2 2 0 0 1-1.275 1.275L3 12l5.813 1.912a2 2 0 0 1 1.275 1.275L12 21l1.912-5.813a2 2 0 0 1 1.275-1.275L21 12l-5.813-1.912a2 2 0 0 1-1.275-1.275L12 3Z"/>',
  sliders: '<line x1="4" x2="20" y1="21" y2="21"/><line x1="4" x2="20" y1="12" y2="12"/><line x1="4" x2="20" y1="3" y2="3"/><circle cx="14" cy="12" r="2"/><circle cx="8" cy="3" r="2"/><circle cx="16" cy="21" r="2"/>',
  edit: '<path d="M17 3a2.85 2.83 0 1 1 4 4L7.5 20.5 2 22l1.5-5.5Z"/>',
  trash: '<path d="M3 6h18"/><path d="M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6"/><path d="M8 6V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2"/>',
  send: '<path d="m5 12 7-7 7 7"/><path d="M12 19V5"/>',
  stop: '<rect width="12" height="12" x="6" y="6" rx="2"/>',
  play: '<polygon points="6 3 20 12 6 21 6 3"/>',
  copy: '<rect width="14" height="14" x="8" y="8" rx="2" ry="2"/><path d="M4 16c-1.1 0-2-.9-2-2V4c0-1.1.9-2 2-2h10c1.1 0 2 .9 2 2"/>',
  check: '<path d="M20 6 9 17l-5-5"/>',
  chevronDown: '<path d="m6 9 6 6 6-6"/>',
  chevronRight: '<path d="m9 18 6-6-6-6"/>',
  close: '<path d="M18 6 6 18"/><path d="m6 6 12 12"/>',
  compass: '<circle cx="12" cy="12" r="10"/><polygon points="16.24 7.76 14.12 14.12 7.76 16.24 9.88 9.88 16.24 7.76"/>',
  zap: '<polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/>',
  cpu: '<rect width="16" height="16" x="4" y="4" rx="2"/><rect width="6" height="6" x="9" y="9" rx="1"/><path d="M15 2v2"/><path d="M15 20v2"/><path d="M2 15h2"/><path d="M2 9h2"/><path d="M20 15h2"/><path d="M20 9h2"/><path d="M9 2v2"/><path d="M9 20v2"/>',
  layers: '<polygon points="12 2 2 7 12 12 22 7 12 2"/><polyline points="2 17 12 22 22 17"/><polyline points="2 12 12 17 22 12"/>',
  code: '<polyline points="16 18 22 12 16 6"/><polyline points="8 6 2 12 8 18"/>',
  brain: '<path d="M12 5a3 3 0 1 0-5.997.125 4 4 0 0 0-2.526 5.77 4 4 0 0 0 .556 6.588A4 4 0 1 0 12 18Z"/><path d="M12 5a3 3 0 1 1 5.997.125 4 4 0 0 1 2.526 5.77 4 4 0 0 1-.556 6.588A4 4 0 1 1 12 18Z"/>',
  terminal: '<polyline points="4 17 10 11 4 5"/><line x1="12" x2="20" y1="19" y2="19"/>',
  fileText: '<path d="M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7Z"/><path d="M14 2v4a2 2 0 0 0 2 2h4"/><path d="M10 9H8"/><path d="M16 13H8"/><path d="M16 17H8"/>',
  fileEdit: '<path d="M12 3H5a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.375 2.625a1 1 0 0 1 3 3l-9.013 9.014a2 2 0 0 1-.853.505l-2.873.84a.5.5 0 0 1-.62-.62l.84-2.873a2 2 0 0 1 .506-.852z"/>',
  folderTree: '<path d="M20 10a1 1 0 0 0 1-1V6a1 1 0 0 0-1-1h-2.5a1 1 0 0 1-.8-.4l-.9-1.2A1 1 0 0 0 15 3h-2a1 1 0 0 0-1 1v5a1 1 0 0 0 1 1Z"/><path d="M20 21a1 1 0 0 0 1-1v-3a1 1 0 0 0-1-1h-2.9a1 1 0 0 1-.88-.55l-.42-.85a1 1 0 0 0-.92-.6H13a1 1 0 0 0-1 1v5a1 1 0 0 0 1 1Z"/><path d="M3 5a2 2 0 0 0 2 2h3"/><path d="M3 3v13a2 2 0 0 0 2 2h3"/>',
  fileSearch: '<path d="M14 2v4a2 2 0 0 0 2 2h4"/><path d="M4.268 21a2 2 0 0 0 1.727 1H18a2 2 0 0 0 2-2V7l-5-5H6a2 2 0 0 0-2 2v3"/><circle cx="5" cy="14" r="3"/><path d="m9 18-1.5-1.5"/>',
  shieldCheck: '<path d="M20 13c0 5-3.5 7.5-7.66 8.95a1 1 0 0 1-.67-.01C7.5 20.5 4 18 4 13V6a1 1 0 0 1 1-1c2 0 4.5-1.2 6.24-2.72a1.17 1.17 0 0 1 1.52 0C14.51 3.81 17 5 19 5a1 1 0 0 1 1 1z"/><path d="m9 12 2 2 4-4"/>',
  key: '<circle cx="7.5" cy="15.5" r="5.5"/><path d="m21 2-9.6 9.6"/><path d="m15.5 7.5 3 3L22 7l-3-3"/>',
  refresh: '<path d="M3 12a9 9 0 0 1 9-9 9.75 9.75 0 0 1 6.74 2.74L21 8"/><path d="M21 3v5h-5"/><path d="M21 12a9 9 0 0 1-9 9 9.75 9.75 0 0 1-6.74-2.74L3 16"/><path d="M8 16H3v5"/>',
  fileCode: '<path d="M10 12.5 8 15l2 2.5"/><path d="m14 12.5 2 2.5-2 2.5"/><path d="M14 2v4a2 2 0 0 0 2 2h4"/><path d="M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7Z"/>',
  alertCircle: '<circle cx="12" cy="12" r="10"/><line x1="12" x2="12" y1="8" y2="12"/><line x1="12" x2="12.01" y1="16" y2="16"/>',
};

function iconSvg(name, size = 15) {
  const path = SVG_ICONS[name] || SVG_ICONS.zap;
  return `<svg width="${size}" height="${size}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${path}</svg>`;
}

function hydrateSvgSlots(root = document) {
  for (const el of root.querySelectorAll('.svg-slot[data-icon]')) {
    const iconName = el.dataset.icon;
    const size = parseInt(el.dataset.size || '15', 10);
    el.innerHTML = iconSvg(iconName, size);
  }
}

hydrateSvgSlots(document);

// State
let currentSessionId = null;
let loadedSessionId = null;
let currentMode = 'plan';
let currentCwd = '~';
let isGenerating = false;
let currentAbortController = null;
let allSessionsCache = [];
let loadedModels = [];
let activeModelId = localStorage.getItem('nanoagent_selected_model') || 'abliterated-model-large-flash';
let lastHandledDistillFinish = 0;
let distillPollTimer = null;
let initialConfigPromptChecked = false;
let adminKeyMarkedForClear = false;
let geminiKeyMarkedForClear = false;

// DOM Elements
const sidebar = document.getElementById('sidebar');
const btnToggleSidebar = document.getElementById('btn-toggle-sidebar');
const btnNewChat = document.getElementById('btn-new-chat');
const sessionSearchInput = document.getElementById('session-search');
const sessionsList = document.getElementById('sessions-list');

const headerVersionBadge = document.getElementById('header-version-badge');
const cwdPillBtn = document.getElementById('cwd-pill-btn');
const cwdTextEl = document.getElementById('cwd-text');
const pillBalance = document.getElementById('pill-balance');
const meterBarInner = document.getElementById('meter-bar-inner');
const meterText = document.getElementById('meter-text');
const btnDistillNow = document.getElementById('btn-distill-now');
const distillEngineTag = document.getElementById('distill-engine-tag');

const activeMemoryStrip = document.getElementById('active-memory-strip');
const btnToggleMemoryPreview = document.getElementById('btn-toggle-memory-preview');
const memoryStripBody = document.getElementById('memory-strip-body');

const chatContainer = document.getElementById('chat-container');
const chatInput = document.getElementById('chat-input');
const btnSend = document.getElementById('btn-send');
const btnStop = document.getElementById('btn-stop');

const modeBtnPlan = document.getElementById('mode-btn-plan');
const modeBtnAct = document.getElementById('mode-btn-act');
const reasoningSelect = document.getElementById('reasoning-select');
const contextLimitSelect = document.getElementById('context-limit-select');
const thresholdSelect = document.getElementById('threshold-select');
const modelSelect = document.getElementById('model-select');

// Model UI
const modelHeaderBtn = document.getElementById('model-header-btn');
const mHeaderIcon = document.getElementById('m-header-icon');
const mHeaderName = document.getElementById('m-header-name');
const mHeaderBadge = document.getElementById('m-header-badge');
const modelPillsList = document.getElementById('model-pills-list');
const btnOpenModelModal = document.getElementById('btn-open-model-modal');
const modelModal = document.getElementById('model-modal');
const modalProviderBadge = document.getElementById('modal-provider-badge');
const modelCardsGrid = document.getElementById('model-cards-grid');
const customModelInput = document.getElementById('custom-model-input');
const customModelApplyBtn = document.getElementById('custom-model-apply-btn');

// Settings Dialog
const btnHeaderSettings = document.getElementById('btn-header-settings');
const settingsModal = document.getElementById('settings-modal');
const settingsTabs = document.querySelectorAll('.settings-tab');
const tabPanelApi = document.getElementById('tab-panel-api');
const tabPanelPrompt = document.getElementById('tab-panel-prompt');
const settingsProviderSelect = document.getElementById('settings-provider-select');
const settingsBaseurlGroup = document.getElementById('settings-baseurl-group');
const settingsBaseurlInput = document.getElementById('settings-baseurl-input');
const settingsKeyLabel = document.getElementById('settings-key-label');
const settingsApikeyInput = document.getElementById('settings-apikey-input');
const settingsAdminGroup = document.getElementById('settings-admin-group');
const settingsAdminkeyInput = document.getElementById('settings-adminkey-input');
const btnClearAdminKey = document.getElementById('btn-clear-adminkey');
const settingsDistillSelect = document.getElementById('settings-distill-select');
const distillAgyHint = document.getElementById('distill-agy-hint');
const settingsGeminiGroup = document.getElementById('settings-gemini-group');
const settingsGeminikeyInput = document.getElementById('settings-geminikey-input');
const btnClearGeminiKey = document.getElementById('btn-clear-geminikey');
const settingsSaveBtn = document.getElementById('settings-save-btn');
const settingsSaveStatus = document.getElementById('settings-save-status');

const systemPromptEditor = document.getElementById('system-prompt-editor');
const promptSaveBtn = document.getElementById('prompt-save-btn');
const promptResetBtn = document.getElementById('prompt-reset-btn');
const promptSaveStatus = document.getElementById('prompt-save-status');

// Key Pool & Rotation DOM Elements
const tabPanelKeys = document.getElementById('tab-panel-keys');
const keysTabBadge = document.getElementById('keys-tab-badge');
const keypoolCounterBadge = document.getElementById('keypool-counter-badge');
const keypoolCards = document.getElementById('keypool-cards');
const keypoolAutorotateCheck = document.getElementById('keypool-autorotate-check');
const keypoolAutopurgeCheck = document.getElementById('keypool-autopurge-check');
const btnCheckAllKeys = document.getElementById('btn-check-all-keys');
const btnPurgeExhaustedKeys = document.getElementById('btn-purge-exhausted-keys');
const newKeyMain = document.getElementById('new-key-main');
const newKeyAdmin = document.getElementById('new-key-admin');
const newKeyLabel = document.getElementById('new-key-label');
const btnAddKeypair = document.getElementById('btn-add-keypair');
const keypoolAddStatus = document.getElementById('keypool-add-status');
const pillBalanceText = document.getElementById('pill-balance-text');
const poolCountBadge = document.getElementById('pool-count-badge');
const poolDot = document.getElementById('pool-dot');

// CWD / Rename Dialog
const cwdModal = document.getElementById('cwd-modal');
const cwdModalInput = document.getElementById('cwd-modal-input');
const titleModalInput = document.getElementById('title-modal-input');
const cwdSaveBtn = document.getElementById('cwd-save-btn');
const cwdSaveStatus = document.getElementById('cwd-save-status');

// Restore persisted limit
const savedLimit = localStorage.getItem('nanoagent_context_limit');
if (savedLimit && Array.from(contextLimitSelect.options).some(o => o.value === savedLimit)) {
  contextLimitSelect.value = savedLimit;
}
contextLimitSelect.addEventListener('change', () => {
  localStorage.setItem('nanoagent_context_limit', contextLimitSelect.value);
  if (currentSessionId) {
    fetch(`/api/sessions/${currentSessionId}`)
      .then(r => (r.ok ? r.json() : null))
      .then(s => s && updateContextMeter(s.tokens || 0, getContextLimit()))
      .catch(() => {});
  }
});

// Light-dismiss fallback for browsers without native closedby support
if (!('closedBy' in HTMLDialogElement.prototype)) {
  const isOutside = (e, dlg) => {
    const r = dlg.getBoundingClientRect();
    return e.clientX < r.left || e.clientX > r.right || e.clientY < r.top || e.clientY > r.bottom;
  };
  for (const dlg of document.querySelectorAll('dialog[closedby="any"]')) {
    let pressedOutside = false;
    dlg.addEventListener('pointerdown', (e) => { pressedOutside = isOutside(e, dlg); });
    dlg.addEventListener('pointerup', (e) => {
      if (pressedOutside && isOutside(e, dlg)) dlg.close();
    });
  }
}

function getContextLimit() {
  return parseInt(contextLimitSelect.value, 10) || 32000;
}

function escapeHtml(str) {
  if (!str) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

// XSS-Safe Markdown Renderer (native Sanitizer API with strict DOMParser fallback)
const SAFE_HTML_TAGS = new Set([
  'p', 'br', 'strong', 'b', 'em', 'i', 'u', 's', 'del', 'code', 'pre',
  'blockquote', 'ul', 'ol', 'li', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
  'hr', 'table', 'thead', 'tbody', 'tr', 'th', 'td', 'a', 'span', 'div'
]);
const DROP_WITH_CONTENT_TAGS = new Set([
  'script', 'style', 'iframe', 'object', 'embed', 'svg', 'math', 'form', 'input', 'button', 'textarea', 'select'
]);

function sanitizeFallbackNode(node, docOut) {
  if (node.nodeType === Node.TEXT_NODE) {
    return docOut.createTextNode(node.textContent || '');
  }
  if (node.nodeType !== Node.ELEMENT_NODE) {
    return null;
  }
  const tag = node.tagName.toLowerCase();
  if (DROP_WITH_CONTENT_TAGS.has(tag)) {
    return null;
  }
  const el = SAFE_HTML_TAGS.has(tag) ? docOut.createElement(tag) : docOut.createElement('span');
  if (tag === 'a') {
    const href = (node.getAttribute('href') || '').trim();
    if (/^(https?:\/\/|mailto:|\/|#)/i.test(href)) {
      el.setAttribute('href', href);
      el.setAttribute('target', '_blank');
      el.setAttribute('rel', 'noopener noreferrer');
    }
  }
  for (const attr of node.attributes) {
    if (attr.name === 'class') {
      el.setAttribute('class', attr.value);
    }
  }
  for (const child of node.childNodes) {
    const cleanChild = sanitizeFallbackNode(child, docOut);
    if (cleanChild) el.appendChild(cleanChild);
  }
  return el;
}

function setSafeMarkdown(targetEl, markdownText) {
  const rawHtml = window.marked ? marked.parse(markdownText || '') : escapeHtml(markdownText || '');
  if ('setHTML' in Element.prototype) {
    try {
      targetEl.setHTML(rawHtml, {
        sanitizer: {
          elements: Array.from(SAFE_HTML_TAGS),
          attributes: ['class', 'href', 'target', 'rel'],
        },
      });
    } catch (_) {
      targetEl.setHTML(rawHtml);
    }
  } else {
    const parsed = new DOMParser().parseFromString(rawHtml, 'text/html');
    const frag = document.createDocumentFragment();
    for (const child of parsed.body.childNodes) {
      const clean = sanitizeFallbackNode(child, document);
      if (clean) frag.appendChild(clean);
    }
    targetEl.replaceChildren(frag);
  }

  for (const pre of targetEl.querySelectorAll('pre')) {
    if (pre.parentElement && pre.parentElement.classList.contains('code-block-wrap')) continue;
    const wrap = document.createElement('div');
    wrap.className = 'code-block-wrap';
    pre.parentNode.insertBefore(wrap, pre);
    wrap.appendChild(pre);

    const copyBtn = document.createElement('button');
    copyBtn.type = 'button';
    copyBtn.className = 'btn-copy-code';
    copyBtn.innerHTML = `${iconSvg('copy', 12)} <span>Копировать</span>`;
    copyBtn.onclick = async () => {
      const codeEl = pre.querySelector('code');
      const text = (codeEl ? codeEl.innerText : pre.innerText) || '';
      try {
        await navigator.clipboard.writeText(text);
        copyBtn.innerHTML = `${iconSvg('check', 12)} <span>Скопировано</span>`;
        setTimeout(() => { copyBtn.innerHTML = `${iconSvg('copy', 12)} <span>Копировать</span>`; }, 1500);
      } catch (_) {
        copyBtn.textContent = 'Ошибка';
      }
    };
    wrap.appendChild(copyBtn);
  }
}

function scrollToBottom() {
  chatContainer.scrollTop = chatContainer.scrollHeight;
}

function updateContextMeter(tokens, limit) {
  const safeLimit = limit > 0 ? limit : getContextLimit();
  const pct = Math.min(100, Math.round((tokens / safeLimit) * 100));
  meterBarInner.style.width = `${pct}%`;
  meterText.textContent = `${pct}% (${tokens}/${Math.round(safeLimit / 1000)}k)`;
  if (pct > 80) {
    meterBarInner.style.background = 'var(--crimson)';
  } else if (pct > 50) {
    meterBarInner.style.background = 'var(--amber)';
  } else {
    meterBarInner.style.background = 'var(--accent)';
  }
}

function updateCwdUI(cwdStr) {
  if (!cwdStr) return;
  currentCwd = cwdStr;
  const parts = cwdStr.replace(/\\/g, '/').split('/').filter(Boolean);
  const shortLabel = parts.length <= 2 ? cwdStr : `.../${parts.slice(-2).join('/')}`;
  cwdTextEl.textContent = shortLabel;
  cwdPillBtn.title = `Текущая папка: ${cwdStr} (нажмите, чтобы изменить)`;
}

function updateModeUI(mode, persist = false) {
  currentMode = mode === 'act' ? 'act' : 'plan';
  modeBtnPlan.classList.toggle('active', currentMode === 'plan');
  modeBtnAct.classList.toggle('active', currentMode === 'act');
  if (persist && currentSessionId) {
    fetch(`/api/sessions/${currentSessionId}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ mode: currentMode }),
    }).catch(() => {});
  }
}

modeBtnPlan.onclick = () => updateModeUI('plan', true);
modeBtnAct.onclick = () => updateModeUI('act', true);

function updateActiveMemoryStrip(memText) {
  const txt = (memText || '').trim();
  if (!txt) {
    activeMemoryStrip.classList.add('hidden');
    memoryStripBody.replaceChildren();
    return;
  }
  activeMemoryStrip.classList.remove('hidden');
  setSafeMarkdown(memoryStripBody, txt);
}

btnToggleMemoryPreview.onclick = () => {
  memoryStripBody.classList.toggle('hidden');
};

function showNotificationToast(msg, kind = 'ok') {
  const t = document.createElement('div');
  t.className = `toast-pill ${kind}`;
  const ic = kind === 'err' ? 'alertCircle' : 'shieldCheck';
  t.innerHTML = `<span class="svg-slot">${iconSvg(ic, 14)}</span> <span>${escapeHtml(msg)}</span>`;
  document.body.appendChild(t);
  setTimeout(() => t.remove(), 4500);
}

// --- Settings Dialog ---
function showBanner(el, ok, text) {
  el.classList.remove('hidden');
  el.style.color = ok ? '#34d399' : '#f87171';
  el.textContent = text;
}

for (const tab of settingsTabs) {
  tab.onclick = () => {
    for (const t of settingsTabs) t.classList.toggle('active', t === tab);
    const which = tab.dataset.tab;
    tabPanelApi.classList.toggle('hidden', which !== 'api');
    tabPanelPrompt.classList.toggle('hidden', which !== 'prompt');
    if (tabPanelKeys) tabPanelKeys.classList.toggle('hidden', which !== 'keys');
    if (which === 'keys') {
      loadKeyPool();
    }
  };
}

settingsProviderSelect.onchange = () => {
  const p = settingsProviderSelect.value;
  if (p === 'openrouter') {
    settingsBaseurlGroup.classList.add('hidden');
    settingsAdminGroup.classList.add('hidden');
    settingsKeyLabel.textContent = 'OpenRouter sk-or-v1-...';
  } else if (p === 'custom') {
    settingsBaseurlGroup.classList.remove('hidden');
    settingsAdminGroup.classList.remove('hidden');
    settingsKeyLabel.textContent = 'API ключ';
  } else {
    settingsBaseurlGroup.classList.add('hidden');
    settingsAdminGroup.classList.remove('hidden');
    settingsKeyLabel.textContent = 'Abliteration ak_...';
  }
};

settingsDistillSelect.onchange = () => {
  settingsGeminiGroup.classList.toggle('hidden', settingsDistillSelect.value !== 'gemini_free');
};

btnClearAdminKey.onclick = () => {
  adminKeyMarkedForClear = true;
  settingsAdminkeyInput.value = '';
  settingsAdminkeyInput.placeholder = 'Admin Key будет удалён при сохранении';
  btnClearAdminKey.classList.add('hidden');
};

btnClearGeminiKey.onclick = () => {
  geminiKeyMarkedForClear = true;
  settingsGeminikeyInput.value = '';
  settingsGeminikeyInput.placeholder = 'Gemini API Key будет удалён при сохранении';
  btnClearGeminiKey.classList.add('hidden');
};

let currentKeyPoolData = null;

async function loadKeyPool() {
  if (!keypoolCards) return;
  try {
    const res = await fetch('/api/keys');
    if (!res.ok) return;
    const data = await res.json();
    currentKeyPoolData = data;
    renderKeyPool(data);
  } catch (e) {
    console.error('Ошибка загрузки пула ключей:', e);
  }
}

function renderKeyPool(data) {
  if (!keypoolCards) return;
  const pairs = data.pairs || [];
  const total = data.total_pairs || pairs.length;
  const ready = data.ready_pairs_count || 0;

  if (keypoolCounterBadge) {
    keypoolCounterBadge.textContent = `${total} ${total === 1 ? 'пара' : 'пар'}`;
  }
  if (keysTabBadge) {
    keysTabBadge.textContent = String(total);
  }
  if (poolCountBadge) {
    poolCountBadge.textContent = `${ready}/${total}`;
    poolCountBadge.title = `Всего ключей: ${total}, готово к работе: ${ready}`;
  }

  if (keypoolAutorotateCheck) {
    keypoolAutorotateCheck.checked = Boolean(data.auto_rotate);
  }
  if (keypoolAutopurgeCheck) {
    keypoolAutopurgeCheck.checked = Boolean(data.auto_purge_exhausted);
  }

  keypoolCards.replaceChildren();

  if (pairs.length === 0) {
    const emptyEl = document.createElement('div');
    emptyEl.className = 'keypair-card';
    emptyEl.style.textAlign = 'center';
    emptyEl.style.padding = '20px';
    emptyEl.style.color = 'var(--text-muted)';
    emptyEl.textContent = 'Пул ключей пуст. Добавьте первую пару (Основной API + Admin Key) ниже.';
    keypoolCards.appendChild(emptyEl);
    return;
  }

  for (const p of pairs) {
    const card = document.createElement('div');
    const isActive = p.id === data.active_pair_id || p.status === 'active';
    const isExhausted = p.status === 'exhausted' || (p.balance !== null && p.balance <= 0);

    card.className = `keypair-card${isActive ? ' active' : ''}${isExhausted ? ' exhausted' : ''}`;

    let statusTagClass = 'status-tag-standby';
    let statusLabel = 'Резерв';
    if (isActive) {
      statusTagClass = 'status-tag-active';
      statusLabel = 'Активен';
    } else if (isExhausted) {
      statusTagClass = 'status-tag-exhausted';
      statusLabel = 'Исчерпан';
    }

    const balFormatted = p.formatted_balance || (p.balance !== null ? `$${Number(p.balance).toFixed(4)}` : 'Не проверен');
    const balClass = isExhausted ? 'keypair-balance-tag zero' : 'keypair-balance-tag';

    card.innerHTML = `
      <div class="keypair-card-head">
        <div class="keypair-title-box">
          <span class="keypair-label">${escapeHtml(p.label || 'Без названия')}</span>
          <span class="keypair-status-tag ${statusTagClass}">${statusLabel}</span>
        </div>
        <div class="${balClass}">${escapeHtml(balFormatted)}</div>
      </div>
      <div class="keypair-card-keys">
        <div class="key-sub-box" title="Основной API ключ для выполнения запросов">
          <span class="key-name">API:</span>
          <span>${escapeHtml(p.masked_api_key || '***')}</span>
        </div>
        <div class="key-sub-box" title="Admin Key для мониторинга баланса">
          <span class="key-name">Admin:</span>
          <span>${escapeHtml(p.masked_admin_key || '***')}</span>
        </div>
      </div>
      <div class="keypair-card-foot">
        ${!isActive ? `<button type="button" class="btn-xs btn-activate-pair" data-id="${p.id}" title="Сделать этот ключ активным вручную">${iconSvg('play', 12)}<span>Выбрать активным</span></button>` : '<span style="font-size:0.72rem;color:#34d399;display:inline-flex;align-items:center;gap:4px;">' + iconSvg('check', 12) + 'Используется сейчас</span>'}
        <button type="button" class="btn-xs btn-xs-danger btn-delete-pair" data-id="${p.id}" title="Удалить этот ключ из пула">${iconSvg('trash', 12)}<span>Удалить</span></button>
      </div>
    `;

    const actBtn = card.querySelector('.btn-activate-pair');
    if (actBtn) {
      actBtn.onclick = async () => {
        actBtn.disabled = true;
        try {
          const r = await fetch(`/api/keys/${p.id}/activate`, { method: 'POST' });
          if (r.ok) {
            const resData = await r.json();
            renderKeyPool(resData.pool);
            fetchStatus();
          }
        } catch (err) {
          console.error(err);
        } finally {
          actBtn.disabled = false;
        }
      };
    }

    const delBtn = card.querySelector('.btn-delete-pair');
    if (delBtn) {
      delBtn.onclick = async () => {
        if (!confirm(`Удалить ключ «${p.label}» из пула?`)) return;
        delBtn.disabled = true;
        try {
          const r = await fetch(`/api/keys/${p.id}`, { method: 'DELETE' });
          if (r.ok) {
            const resData = await r.json();
            renderKeyPool(resData.pool);
            fetchStatus();
          }
        } catch (err) {
          console.error(err);
        } finally {
          delBtn.disabled = false;
        }
      };
    }

    keypoolCards.appendChild(card);
  }
}

if (keypoolAutorotateCheck) {
  keypoolAutorotateCheck.onchange = async () => {
    try {
      await fetch('/api/keys/settings', {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ auto_rotate: keypoolAutorotateCheck.checked }),
      });
    } catch (e) {
      console.error(e);
    }
  };
}

if (keypoolAutopurgeCheck) {
  keypoolAutopurgeCheck.onchange = async () => {
    try {
      await fetch('/api/keys/settings', {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ auto_purge_exhausted: keypoolAutopurgeCheck.checked }),
      });
    } catch (e) {
      console.error(e);
    }
  };
}

if (btnCheckAllKeys) {
  btnCheckAllKeys.onclick = async () => {
    btnCheckAllKeys.disabled = true;
    const prevText = btnCheckAllKeys.innerHTML;
    btnCheckAllKeys.innerHTML = `${iconSvg('refresh', 13)} <span>Проверка...</span>`;
    try {
      const res = await fetch('/api/keys/check-all', { method: 'POST' });
      if (res.ok) {
        const d = await res.json();
        renderKeyPool(d.pool);
        fetchStatus();
      }
    } catch (e) {
      console.error(e);
    } finally {
      btnCheckAllKeys.innerHTML = prevText;
      btnCheckAllKeys.disabled = false;
    }
  };
}

if (btnPurgeExhaustedKeys) {
  btnPurgeExhaustedKeys.onclick = async () => {
    btnPurgeExhaustedKeys.disabled = true;
    try {
      const res = await fetch('/api/keys/purge-exhausted', { method: 'POST' });
      if (res.ok) {
        const d = await res.json();
        renderKeyPool(d.pool);
        fetchStatus();
      }
    } catch (e) {
      console.error(e);
    } finally {
      btnPurgeExhaustedKeys.disabled = false;
    }
  };
}

if (btnAddKeypair) {
  btnAddKeypair.onclick = async () => {
    const apiKey = newKeyMain.value.trim();
    const adminKey = newKeyAdmin.value.trim();
    const label = newKeyLabel.value.trim();

    if (!apiKey) {
      showBanner(keypoolAddStatus, false, 'Укажите основной API-ключ');
      return;
    }
    if (!adminKey) {
      showBanner(keypoolAddStatus, false, 'Укажите Admin Key (для баланса и проверки)');
      return;
    }

    btnAddKeypair.disabled = true;
    showBanner(keypoolAddStatus, true, 'Проверка ключей и баланса...');

    try {
      const res = await fetch('/api/keys', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          api_key: apiKey,
          admin_key: adminKey,
          label: label || undefined,
        }),
      });

      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || 'Ошибка добавления пары ключей');
      }

      showBanner(keypoolAddStatus, true, `Ключ «${data.pair.label}» успешно добавлен! Баланс: ${data.pair.formatted_balance}`);
      newKeyMain.value = '';
      newKeyAdmin.value = '';
      newKeyLabel.value = '';
      renderKeyPool(data.pool);
      fetchStatus();
    } catch (e) {
      showBanner(keypoolAddStatus, false, e.message || 'Ошибка сети при добавлении');
    } finally {
      btnAddKeypair.disabled = false;
    }
  };
}

async function openSettingsModal(defaultTab = 'api') {
  adminKeyMarkedForClear = false;
  geminiKeyMarkedForClear = false;
  settingsSaveStatus.classList.add('hidden');
  promptSaveStatus.classList.add('hidden');
  if (keypoolAddStatus) keypoolAddStatus.classList.add('hidden');
  settingsApikeyInput.value = '';
  settingsAdminkeyInput.value = '';
  settingsGeminikeyInput.value = '';

  for (const t of settingsTabs) t.classList.toggle('active', t.dataset.tab === defaultTab);
  tabPanelApi.classList.toggle('hidden', defaultTab !== 'api');
  tabPanelPrompt.classList.toggle('hidden', defaultTab !== 'prompt');
  if (tabPanelKeys) tabPanelKeys.classList.toggle('hidden', defaultTab !== 'keys');

  settingsModal.showModal();

  if (defaultTab === 'keys') {
    loadKeyPool();
  }

  try {
    const [cfgRes, promptRes] = await Promise.all([fetch('/api/config'), fetch('/api/system-prompt')]);
    if (cfgRes.ok) {
      const data = await cfgRes.json();
      if (data.provider) settingsProviderSelect.value = data.provider;
      if (data.base_url) settingsBaseurlInput.value = data.base_url;
      settingsApikeyInput.placeholder = data.masked_key
        ? `Текущий: ${data.masked_key} (оставьте пустым чтобы не менять)`
        : 'Введите ваш API-ключ...';
      settingsAdminkeyInput.placeholder = data.has_admin_key
        ? 'Настроен (введите новый для замены)'
        : 'sk_... (необязательно)';
      btnClearAdminKey.classList.toggle('hidden', !data.has_admin_key);

      settingsDistillSelect.value = data.distill_engine || 'gemini_free';
      distillAgyHint.textContent = data.agy_available
        ? 'Локальный Google Antigravity CLI (agy) обнаружен — сжатие работает бесплатно ($0).'
        : 'agy не найден: для бесплатного сжатия укажите Gemini API Key ниже.';
      distillAgyHint.style.color = data.agy_available ? '#34d399' : '#f59e0b';

      settingsGeminikeyInput.placeholder = data.has_gemini_key
        ? 'Настроен (введите новый для замены)'
        : 'AIza... (необязательно при наличии agy)';
      btnClearGeminiKey.classList.toggle('hidden', !data.has_gemini_key);

      settingsProviderSelect.onchange();
      settingsDistillSelect.onchange();
    }
    if (promptRes.ok) {
      const pdata = await promptRes.json();
      systemPromptEditor.value = pdata.content || '';
    }
  } catch (e) {
    console.error('Ошибка загрузки настроек:', e);
  }
}

btnHeaderSettings.onclick = () => openSettingsModal('api');
if (pillBalance) {
  pillBalance.onclick = () => openSettingsModal('keys');
}

settingsSaveBtn.onclick = async () => {
  const prov = settingsProviderSelect.value;
  const key = settingsApikeyInput.value.trim();
  const bUrl = settingsBaseurlInput.value.trim();
  const admRaw = settingsAdminkeyInput.value.trim();
  const admPayload = adminKeyMarkedForClear && !admRaw ? '__CLEAR__' : (admRaw || undefined);
  const gemRaw = settingsGeminikeyInput.value.trim();
  const gemPayload = geminiKeyMarkedForClear && !gemRaw ? '__CLEAR__' : (gemRaw || undefined);

  settingsSaveBtn.disabled = true;
  settingsSaveBtn.textContent = 'Сохранение...';
  try {
    const res = await fetch('/api/config', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        provider: prov,
        api_key: key,
        base_url: bUrl || undefined,
        admin_key: admPayload,
        distill_engine: settingsDistillSelect.value,
        gemini_api_key: gemPayload,
      }),
    });
    const data = await res.json();
    if (res.ok) {
      showBanner(settingsSaveStatus, true, 'Настройки сохранены');
      await fetchStatus();
      setTimeout(() => settingsModal.close(), 550);
    } else {
      showBanner(settingsSaveStatus, false, `Ошибка: ${data.detail || 'Не удалось сохранить'}`);
    }
  } catch (e) {
    showBanner(settingsSaveStatus, false, `Ошибка сети: ${e.message}`);
  } finally {
    settingsSaveBtn.disabled = false;
    settingsSaveBtn.textContent = 'Сохранить настройки';
  }
};

promptSaveBtn.onclick = async () => {
  try {
    const res = await fetch('/api/system-prompt', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ content: systemPromptEditor.value }),
    });
    const data = await res.json();
    if (res.ok) {
      showBanner(promptSaveStatus, true, 'Системный промпт обновлён');
    } else {
      showBanner(promptSaveStatus, false, `Ошибка: ${data.detail || 'Не удалось сохранить'}`);
    }
  } catch (e) {
    showBanner(promptSaveStatus, false, `Ошибка сети: ${e.message}`);
  }
};

promptResetBtn.onclick = async () => {
  try {
    const res = await fetch('/api/system-prompt/reset', { method: 'POST' });
    const data = await res.json();
    if (res.ok) {
      systemPromptEditor.value = data.content || '';
      showBanner(promptSaveStatus, true, 'Восстановлен стандартный системный промпт');
    }
  } catch (e) {
    showBanner(promptSaveStatus, false, `Ошибка сети: ${e.message}`);
  }
};

// --- CWD / Rename Dialog ---
function openCwdRenameModal(focusTitle = false) {
  if (!currentSessionId) return;
  cwdSaveStatus.classList.add('hidden');
  cwdModalInput.value = currentCwd;
  const s = allSessionsCache.find(x => x.id === currentSessionId);
  titleModalInput.value = s ? s.title : '';
  cwdModal.showModal();
  if (focusTitle) {
    titleModalInput.focus();
    titleModalInput.select();
  }
}

cwdPillBtn.onclick = () => openCwdRenameModal(false);

cwdSaveBtn.onclick = async () => {
  if (!currentSessionId) return;
  try {
    const res = await fetch(`/api/sessions/${currentSessionId}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        cwd: cwdModalInput.value.trim(),
        title: titleModalInput.value.trim(),
      }),
    });
    const data = await res.json();
    if (res.ok) {
      updateCwdUI(data.cwd);
      await loadSessions();
      cwdModal.close();
    } else {
      showBanner(cwdSaveStatus, false, data.detail || 'Ошибка сохранения');
    }
  } catch (e) {
    showBanner(cwdSaveStatus, false, e.message);
  }
};

// --- Model Selection Logic ---
modelHeaderBtn.onclick = () => modelModal.showModal();
btnOpenModelModal.onclick = () => modelModal.showModal();

customModelApplyBtn.onclick = () => {
  const val = customModelInput.value.trim();
  if (!val) return;
  setActiveModel(val, true);
  customModelInput.value = '';
  modelModal.close();
};

customModelInput.onkeydown = (e) => {
  if (e.key === 'Enter') customModelApplyBtn.click();
};

function resolveModelIconName(rawIcon) {
  return SVG_ICONS[rawIcon] ? rawIcon : 'zap';
}

function setActiveModel(modelId, save = true) {
  if (!modelId) return;
  activeModelId = modelId;
  if (save) localStorage.setItem('nanoagent_selected_model', modelId);

  let model = loadedModels.find(m => m.id === modelId);
  if (!model) {
    model = {
      id: modelId,
      name: modelId,
      short_name: modelId.split('/').pop(),
      icon: 'code',
      badge: 'Своя',
      context: 'Пользовательская',
      desc: 'Собственный ID модели',
    };
    loadedModels.push(model);
    renderPills();
    renderCards();
  }

  let opt = Array.from(modelSelect.options).find(o => o.value === modelId);
  if (!opt) {
    opt = document.createElement('option');
    opt.value = modelId;
    opt.textContent = model.name || modelId;
    modelSelect.appendChild(opt);
  }
  modelSelect.value = modelId;

  mHeaderIcon.innerHTML = iconSvg(resolveModelIconName(model.icon), 14);
  mHeaderName.textContent = model.short_name || model.name || model.id;
  mHeaderBadge.textContent = model.context ? model.context.split(' ')[0] : '1M';

  for (const btn of document.querySelectorAll('.model-pill')) {
    btn.classList.toggle('active', btn.dataset.modelId === modelId);
  }
  for (const card of document.querySelectorAll('.model-card')) {
    const isAct = card.dataset.modelId === modelId;
    card.classList.toggle('active', isAct);
    const statusBox = card.querySelector('.model-card-status');
    if (statusBox) {
      statusBox.innerHTML = isAct
        ? `<span class="status-active-badge">${iconSvg('check', 13)} Активна</span>`
        : '<button type="button" class="btn-select-model">Выбрать</button>';
    }
  }
}

function renderPills() {
  modelPillsList.replaceChildren();
  for (const m of loadedModels) {
    const btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'model-pill' + (m.id === activeModelId ? ' active' : '');
    btn.dataset.modelId = m.id;
    btn.onclick = () => setActiveModel(m.id, true);
    const short = escapeHtml(m.short_name || m.name || m.id);
    const tag = m.context ? escapeHtml(m.context.split(' ')[0]) : '';
    const ic = iconSvg(resolveModelIconName(m.icon), 13);
    btn.innerHTML = `<span class="model-dot"></span>${ic}<span>${short}</span>${tag ? `<span class="pill-tag tabular">${tag}</span>` : ''}`;
    modelPillsList.appendChild(btn);
  }
}

function renderCards() {
  modelCardsGrid.replaceChildren();
  for (const m of loadedModels) {
    const isAct = m.id === activeModelId;
    const card = document.createElement('div');
    card.className = 'model-card' + (isAct ? ' active' : '');
    card.dataset.modelId = m.id;
    card.onclick = () => {
      setActiveModel(m.id, true);
      modelModal.close();
    };
    const ic = iconSvg(resolveModelIconName(m.icon), 17);
    card.innerHTML = `
      <div class="model-card-left">
        <div class="model-card-icon">${ic}</div>
        <div>
          <div class="model-card-title-row">
            <span class="model-card-name">${escapeHtml(m.name || m.id)}</span>
            ${m.badge ? `<span class="model-card-badge">${escapeHtml(m.badge)}</span>` : ''}
            ${m.context ? `<span class="model-card-context tabular">${escapeHtml(m.context)}</span>` : ''}
          </div>
          <div class="model-card-desc">${escapeHtml(m.desc || '')}</div>
          <div class="model-card-id">${escapeHtml(m.id)}</div>
        </div>
      </div>
      <div class="model-card-status">
        ${isAct ? `<span class="status-active-badge">${iconSvg('check', 13)} Активна</span>` : '<button type="button" class="btn-select-model">Выбрать</button>'}
      </div>
    `;
    modelCardsGrid.appendChild(card);
  }
}

// --- Status & Sessions ---
async function fetchStatus() {
  try {
    const res = await fetch('/api/status');
    if (!res.ok) return;
    const data = await res.json();

    if (headerVersionBadge && data.port) {
      headerVersionBadge.textContent = `v${data.version || '2.0'} :${data.port}`;
    }

    if (pillBalanceText) {
      pillBalanceText.textContent = data.balance || '—';
    } else if (pillBalance) {
      pillBalance.textContent = data.balance || '—';
    }

    if (data.keys_pool) {
      if (poolCountBadge) {
        poolCountBadge.textContent = `${data.keys_pool.ready || 1}/${data.keys_pool.total || 1}`;
        poolCountBadge.title = `Всего ключей: ${data.keys_pool.total}, с балансом: ${data.keys_pool.ready}`;
      }
      if (keysTabBadge) {
        keysTabBadge.textContent = String(data.keys_pool.total || 1);
      }
      if (poolDot) {
        poolDot.className = 'pool-dot' + (data.keys_pool.ready === 0 ? ' danger' : (data.balance === '$0.0000' ? ' warning' : ''));
      }
      if (pillBalance && data.keys_pool.active_label) {
        pillBalance.title = `Активен: ${data.keys_pool.active_label} (${data.balance || '—'}). В резерве: ${Math.max(0, (data.keys_pool.ready || 1) - 1)}. Нажмите для ротации и пула.`;
      }
    }

    if (distillEngineTag) {
      distillEngineTag.textContent = data.distill_label || 'Gemini · $0';
      btnDistillNow.classList.toggle('paid-mode', data.distill_engine === 'main_api');
    }

    if (data.provider) {
      const names = {
        abliteration: 'Abliteration AI',
        openrouter: 'OpenRouter API',
        custom: 'OpenAI-совместимый API',
      };
      modalProviderBadge.textContent = names[data.provider] || data.provider;
    }

    if (Array.isArray(data.models)) {
      loadedModels = data.models;
      modelSelect.replaceChildren();
      for (const m of loadedModels) {
        const opt = document.createElement('option');
        opt.value = m.id;
        opt.textContent = m.name || m.id;
        modelSelect.appendChild(opt);
      }
      renderPills();
      renderCards();
      if (!loadedModels.some(m => m.id === activeModelId) && loadedModels.length > 0) {
        activeModelId = loadedModels[0].id;
      }
      setActiveModel(activeModelId, false);
    }

    if (!initialConfigPromptChecked) {
      initialConfigPromptChecked = true;
      if (data.has_key === false) {
        openSettingsModal();
      }
    }
  } catch (e) {
    console.error('Ошибка /api/status:', e);
  }
}

function renderSessionsList() {
  const filter = (sessionSearchInput.value || '').trim().toLowerCase();
  const filtered = filter
    ? allSessionsCache.filter(s => (s.title || '').toLowerCase().includes(filter))
    : allSessionsCache;

  sessionsList.replaceChildren();
  for (const s of filtered) {
    const item = document.createElement('div');
    item.className = 'session-item' + (s.id === currentSessionId ? ' active' : '');
    item.onclick = () => selectSession(s.id);

    const meta = document.createElement('div');
    meta.className = 'session-meta';
    const titleEl = document.createElement('span');
    titleEl.className = 'session-title';
    titleEl.textContent = s.title || `Диалог ${s.id}`;
    const subEl = document.createElement('span');
    subEl.className = 'session-sub tabular';
    subEl.textContent = `${s.messages_count || 0} сообщ. · ${s.tokens || 0} tok`;
    meta.appendChild(titleEl);
    meta.appendChild(subEl);

    const actions = document.createElement('div');
    actions.className = 'session-actions';

    const editBtn = document.createElement('button');
    editBtn.type = 'button';
    editBtn.className = 'btn-session-act';
    editBtn.title = 'Переименовать / папка';
    editBtn.innerHTML = iconSvg('edit', 13);
    editBtn.onclick = (e) => {
      e.stopPropagation();
      if (s.id !== currentSessionId) selectSession(s.id).then(() => openCwdRenameModal(true));
      else openCwdRenameModal(true);
    };

    const delBtn = document.createElement('button');
    delBtn.type = 'button';
    delBtn.className = 'btn-session-act del';
    delBtn.title = 'Удалить';
    delBtn.innerHTML = iconSvg('trash', 13);
    delBtn.onclick = (e) => {
      e.stopPropagation();
      deleteSession(s.id);
    };

    actions.appendChild(editBtn);
    actions.appendChild(delBtn);

    item.appendChild(meta);
    item.appendChild(actions);
    sessionsList.appendChild(item);
  }
}

sessionSearchInput.addEventListener('input', renderSessionsList);

async function loadSessions() {
  try {
    const res = await fetch('/api/sessions');
    if (!res.ok) return;
    allSessionsCache = await res.json();
    renderSessionsList();
    if (!currentSessionId && allSessionsCache.length > 0) {
      await selectSession(allSessionsCache[0].id);
    }
  } catch (e) {
    console.error('Ошибка загрузки сессий:', e);
  }
}

async function selectSession(id) {
  if (isGenerating && currentSessionId !== id) {
    showNotificationToast('Дождитесь завершения или остановите текущий запрос', 'err');
    return;
  }
  stopDistillPolling();
  currentSessionId = id;
  renderSessionsList();
  await loadSessionMessages(id);
}

async function deleteSession(id) {
  if (!confirm('Удалить этот диалог?')) return;
  await fetch(`/api/sessions/${id}`, { method: 'DELETE' });
  if (currentSessionId === id) {
    currentSessionId = null;
    loadedSessionId = null;
  }
  await loadSessions();
}

// --- Rendering Messages & Tools ---
function createDiffElement(diffText) {
  const box = document.createElement('div');
  box.className = 'diff-box';
  for (const line of String(diffText).split('\n')) {
    const div = document.createElement('div');
    div.className = 'diff-line';
    if (line.startsWith('+++') || line.startsWith('---')) div.classList.add('diff-meta');
    else if (line.startsWith('@@')) div.classList.add('diff-hunk');
    else if (line.startsWith('+')) div.classList.add('diff-add');
    else if (line.startsWith('-')) div.classList.add('diff-del');
    div.textContent = line;
    box.appendChild(div);
  }
  return box;
}

function getToolCategory(toolName) {
  if (toolName === 'read_file' || toolName === 'list_dir' || toolName === 'search_files') return 'readonly';
  if (toolName === 'write_file' || toolName === 'edit_file') return 'edit';
  return 'bash';
}

function getToolIconName(toolName) {
  if (toolName === 'read_file') return 'fileText';
  if (toolName === 'list_dir') return 'folderTree';
  if (toolName === 'search_files') return 'fileSearch';
  if (toolName === 'write_file' || toolName === 'edit_file') return 'fileEdit';
  return 'terminal';
}

function buildToolCardElement(toolName, cmdPreview, output, diffText, exitCode, isArchived = false) {
  const row = document.createElement('div');
  row.className = 'msg-row' + (isArchived ? ' archived' : '');
  const cat = getToolCategory(toolName);
  const card = document.createElement('div');
  card.className = `tool-card ${cat}`;

  const errClass = exitCode && exitCode !== 0 ? ' err' : '';
  const statusLabel = exitCode !== undefined && exitCode !== null
    ? (exitCode === 0 ? 'OK' : `exit ${exitCode}`)
    : 'выполнено';

  const header = document.createElement('div');
  header.className = 'tool-header';
  header.innerHTML = `
    <div class="tool-header-left">
      <span class="svg-slot tool-icon">${iconSvg(getToolIconName(toolName), 13)}</span>
      <span class="tool-tag ${cat}">${escapeHtml(toolName)}</span>
      <span class="tool-cmd-preview">${escapeHtml((cmdPreview || '').slice(0, 90))}</span>
    </div>
    <span class="tool-timer tabular${errClass}">${escapeHtml(statusLabel)}</span>
  `;
  header.onclick = () => {
    if (cat === 'readonly') card.classList.toggle('expanded');
  };
  card.appendChild(header);

  if (toolName === 'bash' && cmdPreview) {
    const cmdLine = document.createElement('div');
    cmdLine.className = 'tool-cmd-line';
    cmdLine.textContent = `$ ${cmdPreview}`;
    card.appendChild(cmdLine);
  }

  if (diffText) {
    card.appendChild(createDiffElement(diffText));
  }

  const outBox = document.createElement('div');
  outBox.className = 'tool-output-box';
  outBox.textContent = output || '';
  card.appendChild(outBox);

  row.appendChild(card);
  return row;
}

function appendDistillEventCard(ev) {
  const row = document.createElement('div');
  row.className = 'msg-row';
  const card = document.createElement('div');
  card.className = 'distiller-card';
  const statsBadge = ev.tokens_before !== undefined
    ? `${ev.tokens_before} -> ${ev.tokens_after} tok (-${ev.saved_percent}%)`
    : 'Консолидировано';
  const engineLabel = ev.engine_label || 'Active Memory';
  card.innerHTML = `
    <div class="distiller-header">
      <div class="distiller-title">${iconSvg('sparkles', 14)} <span>Active Memory обновлена</span></div>
      <div class="distiller-badges">
        <span class="distiller-engine-pill">${escapeHtml(engineLabel)}</span>
        <span class="distiller-badge tabular">${escapeHtml(statsBadge)}</span>
      </div>
    </div>
    <div class="distiller-body"></div>
  `;
  setSafeMarkdown(card.querySelector('.distiller-body'), ev.summary || ev.content || '');
  row.appendChild(card);
  chatContainer.appendChild(row);
}

function appendMessage(text, role, isArchived = false) {
  const row = document.createElement('div');
  row.className = 'msg-row' + (isArchived ? ' archived' : '');
  if (role === 'user') {
    const b = document.createElement('div');
    b.className = 'user-bubble';
    b.textContent = text;
    row.appendChild(b);
  } else {
    const b = document.createElement('div');
    b.className = 'assistant-text-box';
    setSafeMarkdown(b, text || '');
    row.appendChild(b);
  }
  chatContainer.appendChild(row);
  return row;
}

function appendReasoningBox(text, collapsed = true) {
  const row = document.createElement('div');
  row.className = 'msg-row';
  const box = document.createElement('div');
  box.className = 'thinking-box';
  box.innerHTML = `
    <div class="thinking-summary">
      <span class="thinking-label">${iconSvg('brain', 14)} <span>Ход рассуждений</span></span>
      <span class="svg-slot">${iconSvg(collapsed ? 'chevronRight' : 'chevronDown', 14)}</span>
    </div>
    <div class="thinking-content"${collapsed ? ' style="display:none;"' : ''}></div>
  `;
  const contentEl = box.querySelector('.thinking-content');
  const chevEl = box.querySelector('.thinking-summary .svg-slot');
  contentEl.textContent = text;
  box.querySelector('.thinking-summary').onclick = () => {
    const isHidden = contentEl.style.display === 'none';
    contentEl.style.display = isHidden ? 'block' : 'none';
    chevEl.innerHTML = iconSvg(isHidden ? 'chevronDown' : 'chevronRight', 14);
  };
  row.appendChild(box);
  chatContainer.appendChild(row);
  return box;
}

function appendPlanActionBar() {
  const existing = chatContainer.querySelector('.plan-execute-bar');
  if (existing) existing.remove();

  const row = document.createElement('div');
  row.className = 'msg-row';
  const bar = document.createElement('div');
  bar.className = 'plan-execute-bar';
  bar.innerHTML = `
    <span class="plan-execute-hint">${iconSvg('compass', 15)} <span>План готов. Подтвердите выполнение для доступа к инструментам изменения.</span></span>
    <button type="button" class="btn-execute-plan">${iconSvg('play', 13)} <span>Выполнить план</span></button>
  `;
  bar.querySelector('.btn-execute-plan').onclick = () => {
    row.remove();
    sendMessage('Выполняй предложенный план по шагам.', true);
  };
  row.appendChild(bar);
  chatContainer.appendChild(row);
  scrollToBottom();
}

async function loadSessionMessages(id) {
  try {
    const res = await fetch(`/api/sessions/${id}`);
    if (!res.ok) return;
    const data = await res.json();
    loadedSessionId = id;

    updateCwdUI(data.cwd || '~');
    updateModeUI(data.mode || 'plan', false);
    updateActiveMemoryStrip(data.active_memory || '');
    updateContextMeter(data.tokens || 0, getContextLimit());

    chatContainer.replaceChildren();
    const msgs = data.messages || [];
    if (msgs.length === 0) {
      appendMessage(
        'Рабочая среда **NanoAgent v2.0** готова.\n\nВыберите режим **План** (только чтение и проектирование) или **Авто** (полное выполнение), выберите модель и опишите задачу.',
        'assistant'
      );
      return;
    }

    for (const m of msgs) {
      const archived = Boolean(m.compressed);
      if (m.role === 'system_event' && m.event === 'distilled') {
        appendDistillEventCard(m);
      } else if (m.is_distilled_memory || (m.role === 'user' && m.content && m.content.includes('ДИСТИЛЛИРОВАННАЯ'))) {
        const clean = (m.content || '').replace(/\[.*?ДИСТИЛЛИРОВАННАЯ[^\]]*\]/, '').trim();
        appendDistillEventCard({ summary: clean, engine_label: 'Legacy' });
      } else if (m.is_distilled_ack) {
        continue;
      } else if (m.role === 'user') {
        appendMessage(m.content, 'user', archived);
      } else if (m.role === 'assistant') {
        if (m.reasoning) appendReasoningBox(m.reasoning, true);
        if (m.content) appendMessage(m.content, 'assistant', archived);
      } else if (m.role === 'tool') {
        const cardRow = buildToolCardElement(
          m.tool_name || 'bash',
          m.command || '',
          m.content || '',
          m.diff || null,
          m.exit_code,
          archived
        );
        chatContainer.appendChild(cardRow);
      }
    }
    scrollToBottom();
  } catch (e) {
    console.error('Ошибка загрузки сообщений:', e);
  }
}

// --- Smart On-Demand Distill Polling (Zero Idle Spam) ---
function setDistillButtonBusy(busy) {
  btnDistillNow.disabled = busy;
  const labelSpan = btnDistillNow.querySelector('span:nth-child(2)');
  if (labelSpan) labelSpan.textContent = busy ? 'Сжимаю...' : 'Сжать память';
}

function stopDistillPolling() {
  if (distillPollTimer) {
    clearInterval(distillPollTimer);
    distillPollTimer = null;
  }
  setDistillButtonBusy(false);
}

function startDistillPolling(sessionId) {
  stopDistillPolling();
  setDistillButtonBusy(true);
  let polls = 0;

  const checkOnce = async () => {
    polls += 1;
    if (polls > 45 || sessionId !== currentSessionId) {
      stopDistillPolling();
      return;
    }
    try {
      const res = await fetch(`/api/distill/status/${sessionId}`);
      if (!res.ok) return;
      const data = await res.json();

      if (data.status === 'running') {
        setDistillButtonBusy(true);
        return;
      }

      stopDistillPolling();

      if (data.status === 'done' && data.finished_at && data.finished_at > lastHandledDistillFinish) {
        lastHandledDistillFinish = data.finished_at;
        showNotificationToast(
          `Память сжата (${data.engine_label || 'Gemini · $0'}): ${data.tokens_before} -> ${data.tokens_after} tok (-${data.saved_percent}%)`,
          'ok'
        );
        updateContextMeter(data.tokens_after, getContextLimit());
        updateActiveMemoryStrip(data.summary || '');
        if (!isGenerating && loadedSessionId === currentSessionId) {
          await loadSessionMessages(currentSessionId);
          await loadSessions();
        }
      } else if (data.status === 'skipped') {
        showNotificationToast(data.message || 'Сжимать пока нечего', 'ok');
      } else if (data.status === 'error') {
        showNotificationToast(data.error || 'Ошибка дистилляции', 'err');
      }
    } catch (_) {
      stopDistillPolling();
    }
  };

  distillPollTimer = setInterval(checkOnce, 1500);
  checkOnce();
}

btnDistillNow.onclick = async () => {
  if (!currentSessionId) return;
  setDistillButtonBusy(true);
  try {
    const res = await fetch('/api/distill', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ session_id: currentSessionId, model: modelSelect.value }),
    });
    const data = await res.json();
    showNotificationToast(data.message || 'Сжатие памяти запущено', 'ok');
    startDistillPolling(currentSessionId);
  } catch (e) {
    setDistillButtonBusy(false);
    showNotificationToast(`Ошибка запуска сжатия: ${e.message}`, 'err');
  }
};

// --- Live Streaming & Stop ---
let activeThinkingBox = null;
let activeThinkingContent = null;
let currentAssistantBox = null;
let currentAssistantRaw = '';
let activeToolRow = null;
let activeStatusPill = null;
let toolStartTime = 0;
let toolTimerInterval = null;

function showStatus(text) {
  removeStatus();
  activeStatusPill = document.createElement('div');
  activeStatusPill.className = 'status-pill';
  activeStatusPill.innerHTML = `<div class="spinner"></div><span>${escapeHtml(text)}</span>`;
  chatContainer.appendChild(activeStatusPill);
  scrollToBottom();
}

function removeStatus() {
  if (activeStatusPill) {
    activeStatusPill.remove();
    activeStatusPill = null;
  }
}

function finalizeCurrentAssistantBox() {
  currentAssistantBox = null;
  currentAssistantRaw = '';
}

function finalizeCurrentToolCard() {
  if (toolTimerInterval) clearInterval(toolTimerInterval);
  toolTimerInterval = null;
  activeToolRow = null;
}

function handleReasoningChunk(delta) {
  if (!activeThinkingBox) {
    activeThinkingBox = appendReasoningBox('', false);
    activeThinkingContent = activeThinkingBox.querySelector('.thinking-content');
  }
  activeThinkingContent.textContent += delta;
  scrollToBottom();
}

function handleContentChunk(delta) {
  activeThinkingBox = null;
  if (!currentAssistantBox) {
    const row = document.createElement('div');
    row.className = 'msg-row';
    currentAssistantBox = document.createElement('div');
    currentAssistantBox.className = 'assistant-text-box';
    row.appendChild(currentAssistantBox);
    chatContainer.appendChild(row);
  }
  currentAssistantRaw += delta;
  setSafeMarkdown(currentAssistantBox, currentAssistantRaw);
  scrollToBottom();
}

function handleToolStart(toolName, cmdPreview) {
  activeThinkingBox = null;
  finalizeCurrentAssistantBox();
  finalizeCurrentToolCard();

  activeToolRow = buildToolCardElement(toolName, cmdPreview, '', null, null, false);
  const outBox = activeToolRow.querySelector('.tool-output-box');
  outBox.innerHTML = '<div class="spinner" style="display:inline-block; vertical-align:middle; margin-right:6px;"></div>Выполнение...';
  if (getToolCategory(toolName) === 'readonly') {
    activeToolRow.querySelector('.tool-card').classList.add('expanded');
  }
  chatContainer.appendChild(activeToolRow);
  scrollToBottom();

  toolStartTime = Date.now();
  const timerEl = activeToolRow.querySelector('.tool-timer');
  timerEl.classList.add('running');
  toolTimerInterval = setInterval(() => {
    if (timerEl) timerEl.textContent = `${((Date.now() - toolStartTime) / 1000).toFixed(1)}s`;
  }, 100);
}

function handleToolDone(data) {
  if (toolTimerInterval) clearInterval(toolTimerInterval);
  toolTimerInterval = null;
  if (!activeToolRow) return;

  const dur = ((Date.now() - toolStartTime) / 1000).toFixed(2);
  const card = activeToolRow.querySelector('.tool-card');
  const timerEl = card.querySelector('.tool-timer');
  const ec = data.exit_code;
  if (timerEl) {
    timerEl.classList.remove('running');
    timerEl.textContent = ec && ec !== 0 ? `${dur}s (exit ${ec})` : `${dur}s OK`;
    if (ec && ec !== 0) timerEl.classList.add('err');
  }

  if (data.diff) {
    const outBox = card.querySelector('.tool-output-box');
    card.insertBefore(createDiffElement(data.diff), outBox);
  }
  const outBox = card.querySelector('.tool-output-box');
  if (outBox) outBox.textContent = data.output || '';

  if (getToolCategory(data.tool) === 'readonly' && (!ec || ec === 0)) {
    card.classList.remove('expanded');
  }
  if (data.cwd) updateCwdUI(data.cwd);

  activeToolRow = null;
  scrollToBottom();
}

async function stopGeneration() {
  if (!isGenerating) return;
  btnStop.disabled = true;
  if (currentSessionId) {
    fetch('/api/chat/stop', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ session_id: currentSessionId }),
    }).catch(() => {});
  }
  if (currentAbortController) {
    currentAbortController.abort();
  }
}

btnStop.onclick = stopGeneration;

async function sendMessage(overrideText = null, approveExecution = false) {
  const text = (overrideText !== null ? overrideText : chatInput.value).trim();
  if (!text || isGenerating) return;

  const existingPlanBar = chatContainer.querySelector('.plan-execute-bar');
  if (existingPlanBar) existingPlanBar.closest('.msg-row')?.remove();

  isGenerating = true;
  btnSend.classList.add('hidden');
  btnStop.classList.remove('hidden');
  btnStop.disabled = false;

  if (overrideText === null) {
    chatInput.value = '';
    autoResizeInput();
  }

  appendMessage(text, 'user');
  scrollToBottom();
  showStatus('Инициализация...');

  currentAbortController = new AbortController();

  try {
    const res = await fetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      signal: currentAbortController.signal,
      body: JSON.stringify({
        message: text,
        session_id: currentSessionId,
        model: modelSelect.value || activeModelId,
        reasoning_effort: reasoningSelect.value,
        context_limit: getContextLimit(),
        compress_threshold: parseFloat(thresholdSelect.value),
        mode: currentMode,
        approve_execution: approveExecution,
      }),
    });

    if (!res.ok) {
      let detail = `HTTP ${res.status}`;
      try {
        const errJson = await res.json();
        detail = errJson.detail || detail;
      } catch (_) {}
      removeStatus();
      appendMessage(`Ошибка: ${detail}`, 'assistant');
      return;
    }

    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop();

      for (const line of lines) {
        if (!line.startsWith('data: ')) continue;
        const raw = line.slice(6).trim();
        if (!raw) continue;
        const data = JSON.parse(raw);

        if (data.type === 'session_init') {
          currentSessionId = data.session_id;
          loadedSessionId = data.session_id;
          if (data.cwd) updateCwdUI(data.cwd);
          if (data.context_tokens !== undefined) {
            updateContextMeter(data.context_tokens, data.context_limit);
          }
        } else if (data.type === 'distill_started') {
          startDistillPolling(currentSessionId);
        } else if (data.type === 'status') {
          showStatus(data.text);
        } else if (data.type === 'reasoning') {
          removeStatus();
          handleReasoningChunk(data.delta);
        } else if (data.type === 'content') {
          removeStatus();
          handleContentChunk(data.delta);
        } else if (data.type === 'tool_start') {
          removeStatus();
          handleToolStart(data.tool, data.command);
        } else if (data.type === 'tool_done') {
          handleToolDone(data);
        } else if (data.type === 'context_update') {
          updateContextMeter(data.context_tokens, data.context_limit);
        } else if (data.type === 'key_rotated') {
          showNotificationToast(`Ротация API: переключено на «${data.label}» (${data.balance})`, 'ok');
          fetchStatus();
        } else if (data.type === 'usage') {
          if (data.balance) {
            if (pillBalanceText) pillBalanceText.textContent = data.balance;
            else if (pillBalance) pillBalance.textContent = data.balance;
          }
          if (data.context_tokens !== undefined) {
            updateContextMeter(data.context_tokens, data.context_limit);
          }
        } else if (data.type === 'plan_ready') {
          appendPlanActionBar();
        } else if (data.type === 'cancelled') {
          removeStatus();
          appendMessage('Выполнение остановлено пользователем.', 'assistant');
        } else if (data.type === 'error') {
          removeStatus();
          appendMessage(`Ошибка: ${data.error}`, 'assistant');
        } else if (data.type === 'done') {
          removeStatus();
          finalizeCurrentAssistantBox();
          finalizeCurrentToolCard();
        }
      }
    }
  } catch (err) {
    removeStatus();
    if (err.name === 'AbortError') {
      appendMessage('Запрос прерван пользователем.', 'assistant');
    } else {
      appendMessage(`Ошибка сети: ${err.message}`, 'assistant');
    }
  } finally {
    removeStatus();
    finalizeCurrentAssistantBox();
    finalizeCurrentToolCard();
    isGenerating = false;
    currentAbortController = null;
    btnStop.classList.add('hidden');
    btnSend.classList.remove('hidden');
    await loadSessions();
    chatInput.focus();
  }
}

function autoResizeInput() {
  chatInput.style.height = 'auto';
  chatInput.style.height = Math.min(200, Math.max(44, chatInput.scrollHeight)) + 'px';
}

chatInput.addEventListener('input', autoResizeInput);
btnSend.onclick = () => sendMessage(null, false);
chatInput.onkeydown = (e) => {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    sendMessage(null, false);
  }
};

btnNewChat.onclick = async () => {
  if (isGenerating) return;
  const res = await fetch('/api/sessions/new', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ title: 'Новый диалог', mode: currentMode }),
  });
  if (res.ok) {
    const s = await res.json();
    currentSessionId = s.id;
    await loadSessions();
    await loadSessionMessages(s.id);
  }
};

btnToggleSidebar.onclick = () => {
  sidebar.classList.toggle('collapsed');
};

// Startup
fetchStatus();
loadSessions();
