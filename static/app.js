/* NanoAgent v2.0 Frontend */

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
let initialConfigPromptChecked = false;
let hasAdminKeyConfigured = false;
let adminKeyMarkedForClear = false;

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
const settingsSaveBtn = document.getElementById('settings-save-btn');
const settingsSaveStatus = document.getElementById('settings-save-status');

const systemPromptEditor = document.getElementById('system-prompt-editor');
const promptSaveBtn = document.getElementById('prompt-save-btn');
const promptResetBtn = document.getElementById('prompt-reset-btn');
const promptSaveStatus = document.getElementById('prompt-save-status');

// CWD / Rename Dialog
const cwdModal = document.getElementById('cwd-modal');
const cwdModalInput = document.getElementById('cwd-modal-input');
const titleModalInput = document.getElementById('title-modal-input');
const cwdSaveBtn = document.getElementById('cwd-save-btn');
const cwdSaveStatus = document.getElementById('cwd-save-status');

// Restore persisted settings
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

  // Wrap <pre> blocks with Copy buttons
  const pres = targetEl.querySelectorAll('pre');
  for (const pre of pres) {
    if (pre.parentElement && pre.parentElement.classList.contains('code-block-wrap')) continue;
    const wrap = document.createElement('div');
    wrap.className = 'code-block-wrap';
    pre.parentNode.insertBefore(wrap, pre);
    wrap.appendChild(pre);

    const copyBtn = document.createElement('button');
    copyBtn.type = 'button';
    copyBtn.className = 'btn-copy-code';
    copyBtn.textContent = '📋 Копировать';
    copyBtn.onclick = async () => {
      const codeEl = pre.querySelector('code');
      const text = (codeEl ? codeEl.innerText : pre.innerText) || '';
      try {
        await navigator.clipboard.writeText(text);
        copyBtn.textContent = '✓ Скопировано';
        setTimeout(() => { copyBtn.textContent = '📋 Копировать'; }, 1500);
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
    meterBarInner.style.background = 'var(--danger)';
  } else if (pct > 50) {
    meterBarInner.style.background = 'var(--warning)';
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

function showNotificationToast(msg) {
  const t = document.createElement('div');
  t.className = 'status-pill';
  t.style.position = 'fixed';
  t.style.bottom = '90px';
  t.style.right = '22px';
  t.style.zIndex = '9999';
  t.style.background = '#2e1065';
  t.style.borderColor = '#a855f7';
  t.innerHTML = `<span>✨</span> <span>${escapeHtml(msg)}</span>`;
  document.body.appendChild(t);
  setTimeout(() => t.remove(), 4200);
}

// --- Settings Dialog Logic ---
function showBanner(el, ok, text) {
  el.classList.remove('hidden');
  el.style.color = ok ? '#4ade80' : '#f87171';
  el.textContent = text;
}

for (const tab of settingsTabs) {
  tab.onclick = () => {
    for (const t of settingsTabs) t.classList.toggle('active', t === tab);
    const which = tab.dataset.tab;
    tabPanelApi.classList.toggle('hidden', which !== 'api');
    tabPanelPrompt.classList.toggle('hidden', which !== 'prompt');
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

btnClearAdminKey.onclick = () => {
  adminKeyMarkedForClear = true;
  settingsAdminkeyInput.value = '';
  settingsAdminkeyInput.placeholder = 'Admin Key будет удалён при сохранении';
  btnClearAdminKey.classList.add('hidden');
};

async function openSettingsModal() {
  adminKeyMarkedForClear = false;
  settingsSaveStatus.classList.add('hidden');
  promptSaveStatus.classList.add('hidden');
  settingsApikeyInput.value = '';
  settingsAdminkeyInput.value = '';
  settingsModal.showModal();

  try {
    const [cfgRes, promptRes] = await Promise.all([fetch('/api/config'), fetch('/api/system-prompt')]);
    if (cfgRes.ok) {
      const data = await cfgRes.json();
      if (data.provider) settingsProviderSelect.value = data.provider;
      if (data.base_url) settingsBaseurlInput.value = data.base_url;
      settingsApikeyInput.placeholder = data.masked_key
        ? `Текущий: ${data.masked_key} (оставьте пустым чтобы не менять)`
        : 'Введите ваш API-ключ...';
      hasAdminKeyConfigured = !!data.has_admin_key;
      settingsAdminkeyInput.placeholder = hasAdminKeyConfigured
        ? 'Настроен (введите новый для замены)'
        : 'sk_... (необязательно)';
      btnClearAdminKey.classList.toggle('hidden', !hasAdminKeyConfigured);
      settingsProviderSelect.onchange();
    }
    if (promptRes.ok) {
      const pdata = await promptRes.json();
      systemPromptEditor.value = pdata.content || '';
    }
  } catch (e) {
    console.error('Ошибка загрузки настроек:', e);
  }
}

btnHeaderSettings.onclick = openSettingsModal;

settingsSaveBtn.onclick = async () => {
  const prov = settingsProviderSelect.value;
  const key = settingsApikeyInput.value.trim();
  const bUrl = settingsBaseurlInput.value.trim();
  const admRaw = settingsAdminkeyInput.value.trim();
  const admPayload = adminKeyMarkedForClear && !admRaw ? '__CLEAR__' : (admRaw || undefined);

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
      }),
    });
    const data = await res.json();
    if (res.ok) {
      showBanner(settingsSaveStatus, true, '✓ Настройки сохранены');
      await fetchStatus();
      setTimeout(() => settingsModal.close(), 650);
    } else {
      showBanner(settingsSaveStatus, false, `Ошибка: ${data.detail || 'Не удалось сохранить'}`);
    }
  } catch (e) {
    showBanner(settingsSaveStatus, false, `Ошибка сети: ${e.message}`);
  } finally {
    settingsSaveBtn.disabled = false;
    settingsSaveBtn.textContent = '💾 Сохранить API';
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
      showBanner(promptSaveStatus, true, '✓ Системный промпт обновлён');
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
      showBanner(promptSaveStatus, true, '↺ Восстановлен стандартный системный промпт');
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
      icon: '⚡',
      badge: 'Своя модель',
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

  mHeaderIcon.textContent = model.icon || '⚡';
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
        ? '<span class="status-active-badge">✓ Активна</span>'
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
    btn.innerHTML = `<span>${m.icon || '⚡'}</span><span>${short}</span>${tag ? `<span class="pill-tag">${tag}</span>` : ''}`;
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
    card.innerHTML = `
      <div class="model-card-left">
        <div class="model-card-icon">${m.icon || '⚡'}</div>
        <div>
          <div class="model-card-title-row">
            <span class="model-card-name">${escapeHtml(m.name || m.id)}</span>
            ${m.badge ? `<span class="model-card-badge">${escapeHtml(m.badge)}</span>` : ''}
            ${m.context ? `<span class="model-card-context">${escapeHtml(m.context)}</span>` : ''}
          </div>
          <div class="model-card-desc">${escapeHtml(m.desc || '')}</div>
          <div class="model-card-id">${escapeHtml(m.id)}</div>
        </div>
      </div>
      <div class="model-card-status">
        ${isAct ? '<span class="status-active-badge">✓ Активна</span>' : '<button type="button" class="btn-select-model">Выбрать</button>'}
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
    pillBalance.textContent = data.balance || '—';

    if (data.provider) {
      const names = {
        abliteration: 'Abliteration AI (Без цензуры)',
        openrouter: 'OpenRouter API',
        custom: 'Свой OpenAI-совместимый API',
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
    subEl.className = 'session-sub';
    subEl.textContent = `${s.messages_count || 0} сообщ. • ${s.tokens || 0} tok`;
    meta.appendChild(titleEl);
    meta.appendChild(subEl);

    const actions = document.createElement('div');
    actions.className = 'session-actions';

    const editBtn = document.createElement('button');
    editBtn.type = 'button';
    editBtn.className = 'btn-session-act';
    editBtn.title = 'Переименовать / папка';
    editBtn.textContent = '✏️';
    editBtn.onclick = (e) => {
      e.stopPropagation();
      if (s.id !== currentSessionId) selectSession(s.id).then(() => openCwdRenameModal(true));
      else openCwdRenameModal(true);
    };

    const delBtn = document.createElement('button');
    delBtn.type = 'button';
    delBtn.className = 'btn-session-act del';
    delBtn.title = 'Удалить';
    delBtn.textContent = '✕';
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
    showNotificationToast('Сначала дождитесь завершения или остановите текущий запрос');
    return;
  }
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

function buildToolCardElement(toolName, cmdPreview, output, diffText, exitCode, isArchived = false) {
  const row = document.createElement('div');
  row.className = 'msg-row' + (isArchived ? ' archived' : '');
  const cat = getToolCategory(toolName);
  const card = document.createElement('div');
  card.className = `tool-card ${cat}`;

  const errClass = exitCode && exitCode !== 0 ? ' err' : '';
  const statusLabel = exitCode !== undefined && exitCode !== null
    ? (exitCode === 0 ? '✓ OK' : `exit ${exitCode}`)
    : 'выполнено';

  const header = document.createElement('div');
  header.className = 'tool-header';
  header.innerHTML = `
    <div class="tool-header-left">
      <span class="tool-tag ${cat}">${escapeHtml(toolName)}</span>
      <span class="tool-cmd-preview">${escapeHtml((cmdPreview || '').slice(0, 90))}</span>
    </div>
    <span class="tool-timer${errClass}">${escapeHtml(statusLabel)}</span>
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
    ? `${ev.tokens_before} ➔ ${ev.tokens_after} tok (−${ev.saved_percent}%)`
    : 'Дистиллировано';
  card.innerHTML = `
    <div class="distiller-header">
      <div class="distiller-title"><span>🧠</span> <span>AI Context Distiller: Рабочая память обновлена</span></div>
      <span class="distiller-badge">${escapeHtml(statsBadge)}</span>
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
      <span>💭 Рассуждения модели</span>
      <span style="font-size: 0.74rem">свернуть / развернуть</span>
    </div>
    <div class="thinking-content"${collapsed ? ' style="display:none;"' : ''}></div>
  `;
  const contentEl = box.querySelector('.thinking-content');
  contentEl.textContent = text;
  box.querySelector('.thinking-summary').onclick = () => {
    contentEl.style.display = contentEl.style.display === 'none' ? 'block' : 'none';
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
    <span class="plan-execute-hint">🧭 План готов. Подтвердите выполнение, чтобы разблокировать запись файлов и терминал.</span>
    <button type="button" class="btn-execute-plan">▶️ Выполнить план</button>
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
        'Привет! Это **NanoAgent v2.0** с асинхронным движком, 6 встроенными инструментами (`read_file`, `write_file`, `edit_file`, `list_dir`, `search_files`, `bash`) и потокобезопасным сжатием контекста.\n\nВыберите режим **🧭 План** или **⚡ Авто** внизу и опишите задачу.',
        'assistant'
      );
      return;
    }

    for (const m of msgs) {
      const archived = Boolean(m.compressed);
      if (m.role === 'system_event' && m.event === 'distilled') {
        appendDistillEventCard(m);
      } else if (m.is_distilled_memory || (m.role === 'user' && m.content && m.content.startsWith('[🧠 ДИСТИЛЛИРОВАННАЯ'))) {
        const clean = (m.content || '').replace('[🧠 ДИСТИЛЛИРОВАННАЯ РАБОЧАЯ ПАМЯТЬ АГЕНТА]', '').trim();
        appendDistillEventCard({ summary: clean });
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

// --- Background Distiller Polling ---
btnDistillNow.onclick = async () => {
  if (!currentSessionId) return;
  try {
    const res = await fetch('/api/distill', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ session_id: currentSessionId, model: modelSelect.value }),
    });
    const data = await res.json();
    showNotificationToast(data.message || 'Фоновое сжатие запущено');
    checkBackgroundDistillStatus();
  } catch (e) {
    console.error('Ошибка запуска дистилляции:', e);
  }
};

async function checkBackgroundDistillStatus() {
  if (!currentSessionId) return;
  try {
    const res = await fetch(`/api/distill/status/${currentSessionId}`);
    if (!res.ok) return;
    const data = await res.json();
    if (data.status === 'running') {
      btnDistillNow.disabled = true;
      btnDistillNow.innerHTML = `<div class="spinner"></div> <span>Сжимаю...</span>`;
    } else {
      btnDistillNow.disabled = false;
      btnDistillNow.innerHTML = `<span>⚡</span> <span>Сжать память</span>`;
      if (data.status === 'done' && data.finished_at && data.finished_at > lastHandledDistillFinish) {
        lastHandledDistillFinish = data.finished_at;
        showNotificationToast(`Память сжата: ${data.tokens_before} ➔ ${data.tokens_after} tok (−${data.saved_percent}%)`);
        updateContextMeter(data.tokens_after, getContextLimit());
        updateActiveMemoryStrip(data.summary || '');
        if (!isGenerating && loadedSessionId === currentSessionId) {
          await loadSessionMessages(currentSessionId);
          await loadSessions();
        }
      }
    }
  } catch (_) {}
}

setInterval(checkBackgroundDistillStatus, 3000);

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
    timerEl.textContent = ec && ec !== 0 ? `${dur}s (exit ${ec})` : `${dur}s ✓`;
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
      appendMessage(`❌ Ошибка: ${detail}`, 'assistant');
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
        } else if (data.type === 'usage') {
          if (data.balance) pillBalance.textContent = data.balance;
          if (data.context_tokens !== undefined) {
            updateContextMeter(data.context_tokens, data.context_limit);
          }
        } else if (data.type === 'plan_ready') {
          appendPlanActionBar();
        } else if (data.type === 'cancelled') {
          removeStatus();
          appendMessage('⏹ Выполнение остановлено.', 'assistant');
        } else if (data.type === 'error') {
          removeStatus();
          appendMessage(`❌ Ошибка: ${data.error}`, 'assistant');
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
      appendMessage('⏹ Запрос прерван пользователем.', 'assistant');
    } else {
      appendMessage(`❌ Ошибка сети: ${err.message}`, 'assistant');
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
setInterval(fetchStatus, 20000);
