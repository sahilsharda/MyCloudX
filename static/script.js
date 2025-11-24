// MyCloudX - Google Photos/iCloud Inspired Interface
// Enhanced with storage tracking, media preview, drag-drop, and more

let TOKEN = "";
let CURRENT_FOLDER = "";
let VIEW = "grid"; // grid or list
let FILES = [];
let FILES_DETAILED = [];
let CURRENT_PREVIEW = null;
let CURRENT_PREVIEW_INDEX = -1;
let PUBLIC_URL = "";
let STORAGE_STATS = null;

// Helpers
const el = id => document.getElementById(id);
const apiBase = () => window.location.origin;

// ========== INITIALIZATION ==========
document.addEventListener('DOMContentLoaded', () => {
  bindUI();
  setThemeFromStorage();
  setupDragDrop();
  refreshUI();
});

function bindUI() {
  el('viewToggle').addEventListener('click', toggleView);
  el('file').addEventListener('change', upload);
  el('qrOpen').addEventListener('click', showQRModal);
  el('toggleTheme').addEventListener('click', toggleTheme);
  el('openSettings').addEventListener('click', toggleSettings);
  el('loginBtn')?.addEventListener('click', doLogin);
  el('newFolderBtn').addEventListener('click', createFolderPrompt);
  el('search').addEventListener('input', renderFiles);
  el('themeSelect')?.addEventListener('change', handleThemeSelect);

  // Keyboard shortcuts
  document.addEventListener('keydown', handleKeyboard);
}

function handleKeyboard(e) {
  // ESC to close preview
  if (e.key === 'Escape') {
    closePreview();
    if (!el('settingsDrawer').classList.contains('hidden')) {
      toggleSettings();
    }
  }

  // Arrow keys for preview navigation
  if (!el('previewModal').classList.contains('hidden')) {
    if (e.key === 'ArrowLeft') navigatePreview(-1);
    if (e.key === 'ArrowRight') navigatePreview(1);
    if (e.key === 'f' || e.key === 'F') toggleFullscreen();
  }
}

// ========== THEME ==========
function toggleTheme() {
  const app = el('app');
  if (app.classList.contains('theme-light')) {
    app.classList.remove('theme-light');
    app.classList.add('theme-dark');
    localStorage.setItem('mycloud_theme', 'dark');
    el('themeIcon').textContent = 'light_mode';
    el('themeSelect').value = 'dark';
  } else {
    app.classList.remove('theme-dark');
    app.classList.add('theme-light');
    localStorage.setItem('mycloud_theme', 'light');
    el('themeIcon').textContent = 'dark_mode';
    el('themeSelect').value = 'light';
  }
}

function setThemeFromStorage() {
  const t = localStorage.getItem('mycloud_theme') || 'light';
  const app = el('app');
  if (t === 'dark') {
    app.classList.remove('theme-light');
    app.classList.add('theme-dark');
    el('themeIcon').textContent = 'light_mode';
    el('themeSelect').value = 'dark';
  } else {
    app.classList.remove('theme-dark');
    app.classList.add('theme-light');
    el('themeIcon').textContent = 'dark_mode';
    el('themeSelect').value = 'light';
  }
}

function handleThemeSelect(e) {
  const app = el('app');
  if (e.target.value === 'dark') {
    app.classList.remove('theme-light');
    app.classList.add('theme-dark');
    localStorage.setItem('mycloud_theme', 'dark');
    el('themeIcon').textContent = 'light_mode';
  } else {
    app.classList.remove('theme-dark');
    app.classList.add('theme-light');
    localStorage.setItem('mycloud_theme', 'light');
    el('themeIcon').textContent = 'dark_mode';
  }
}

// ========== AUTH ==========
async function doLogin() {
  const token = el('tokenInput').value.trim();
  if (!token) return alert('Enter token');
  const form = new FormData();
  form.append('token', token);
  const res = await fetch(apiBase() + "/auth", { method: 'POST', body: form });
  if (!res.ok) return alert('Invalid token');
  TOKEN = token;
  el('statusText').textContent = 'Authenticated ✓';
  toggleSettings();
  refreshUI();
}

async function promptLogin() {
  const t = prompt('Enter access token (default: secret123):', 'secret123');
  if (!t) return;
  TOKEN = t;
  const form = new FormData();
  form.append('token', TOKEN);
  const res = await fetch(apiBase() + "/auth", { method: 'POST', body: form });
  if (!res.ok) {
    TOKEN = "";
    alert('Authentication failed');
  } else {
    el('statusText').textContent = 'Authenticated ✓';
  }
}

// ========== DATA FETCHING ==========
async function refreshUI() {
  if (!TOKEN) {
    el('statusText').textContent = 'Not signed in';
    await promptLogin();
    if (!TOKEN) return;
  }

  el('statusText').textContent = 'Loading…';

  try {
    // Fetch file list
    const res = await fetch(apiBase() + "/list?token=" + encodeURIComponent(TOKEN));
    if (!res.ok) throw new Error('List failed');
    const data = await res.json();
    FILES = data.files || [];
    FILES_DETAILED = data.files_detailed || [];

    buildFolderList(FILES);
    renderFiles();

    el('statusText').textContent = `${FILES.length} items`;

    // Fetch storage stats
    await fetchStorageStats();

    // Fetch public URL
    fetchPublicUrl();
  } catch (e) {
    console.error(e);
    el('statusText').textContent = 'Load error';
  }
}

async function fetchStorageStats() {
  try {
    const res = await fetch(apiBase() + "/storage-stats?token=" + encodeURIComponent(TOKEN));
    if (!res.ok) return;
    STORAGE_STATS = await res.json();
    updateStorageUI();
  } catch (e) {
    console.error('Storage stats error:', e);
  }
}

function updateStorageUI() {
  if (!STORAGE_STATS) return;

  const { total_size_formatted, quota_formatted, usage_percent, breakdown } = STORAGE_STATS;

  // Update storage amount
  el('storageAmount').textContent = `${total_size_formatted} of ${quota_formatted}`;

  // Update storage bar
  el('storageFill').style.width = `${Math.min(usage_percent, 100)}%`;

  // Update breakdown
  const breakdownEl = el('storageBreakdown');
  breakdownEl.innerHTML = `
    <div class="storage-item">
      <span>📸 Images</span>
      <span>${formatBytes(breakdown.images.size)} (${breakdown.images.count})</span>
    </div>
    <div class="storage-item">
      <span>🎥 Videos</span>
      <span>${formatBytes(breakdown.videos.size)} (${breakdown.videos.count})</span>
    </div>
    <div class="storage-item">
      <span>📄 Documents</span>
      <span>${formatBytes(breakdown.documents.size)} (${breakdown.documents.count})</span>
    </div>
    <div class="storage-item">
      <span>📦 Other</span>
      <span>${formatBytes(breakdown.other.size)} (${breakdown.other.count})</span>
    </div>
  `;

  // Update quota display
  el('quotaDisplay').textContent = quota_formatted;
}

// ========== FOLDER MANAGEMENT ==========
function buildFolderList(files) {
  const set = new Set();
  files.forEach(f => {
    if (f.includes('/')) {
      const parts = f.split('/');
      let path = '';
      for (let i = 0; i < parts.length - 1; i++) {
        path += (i ? '/' : '') + parts[i];
        set.add(path);
      }
    }
  });

  const arr = Array.from(set).sort();
  const ul = el('folderList');
  ul.innerHTML = `
    <li data-path="" class="folder-item ${CURRENT_FOLDER === "" ? 'active' : ''}" onclick="selectFolder('')">
      <span class="material-icons-round" style="font-size: 18px;">photo_library</span>
      All Photos
    </li>
  `;

  arr.forEach(p => {
    const li = document.createElement('li');
    li.className = 'folder-item' + (p === CURRENT_FOLDER ? ' active' : '');
    li.dataset.path = p;
    li.innerHTML = `
      <span class="material-icons-round" style="font-size: 18px;">folder</span>
      ${p.split('/').pop()}
    `;
    li.onclick = () => selectFolder(p);
    ul.appendChild(li);
  });
}

function selectFolder(path) {
  CURRENT_FOLDER = path;
  updateActiveFolder();
}

function updateActiveFolder() {
  document.querySelectorAll('.folder-item').forEach(n => n.classList.remove('active'));
  const sel = document.querySelector(`.folder-item[data-path="${CURRENT_FOLDER}"]`);
  if (sel) sel.classList.add('active');
  el('breadcrumb').textContent = CURRENT_FOLDER ? CURRENT_FOLDER : 'All Photos';
  renderFiles();
}

function createFolderPrompt() {
  const name = prompt('Create folder (no slashes):', 'New Folder');
  if (!name || name.includes('/')) return alert('Invalid folder name');

  // Add to folder list
  const ul = el('folderList');
  const li = document.createElement('li');
  li.className = 'folder-item';
  li.dataset.path = name;
  li.innerHTML = `
    <span class="material-icons-round" style="font-size: 18px;">folder</span>
    ${name}
  `;
  li.onclick = () => selectFolder(name);
  ul.appendChild(li);

  alert('Folder created! Upload files to this folder to populate it.');
}

// ========== FILE RENDERING ==========
function renderFiles() {
  const q = el('search').value.toLowerCase();
  const inFolder = name => {
    if (!CURRENT_FOLDER) return true;
    return name.startsWith(CURRENT_FOLDER + '/');
  };

  const filtered = FILES.filter(f => inFolder(f) && (!q || f.toLowerCase().includes(q)));
  const filteredDetailed = FILES_DETAILED.filter(f => inFolder(f.name) && (!q || f.name.toLowerCase().includes(q)));

  // Separate by type
  const images = filteredDetailed.filter(f => f.type === 'image');
  const videos = filteredDetailed.filter(f => f.type === 'video');
  const others = filteredDetailed.filter(f => f.type !== 'image' && f.type !== 'video');

  // Render grid view
  const grid = el('gridView');
  grid.innerHTML = '';

  [...images, ...videos, ...others].forEach(f => {
    grid.appendChild(makeCard(f));
  });

  // Render list view
  const tbody = el('listBody');
  if (tbody) {
    tbody.innerHTML = '';
    filteredDetailed.forEach(f => {
      const tr = document.createElement('tr');
      tr.innerHTML = `
        <td>${escapeHTML(f.name.split('/').pop())}</td>
        <td>${escapeHTML(f.type)}</td>
        <td>${escapeHTML(f.size_formatted)}</td>
        <td>${formatDate(f.modified)}</td>
        <td>
          <button class="icon-btn" onclick="openPreview('${encodeURIComponent(f.name)}')">
            <span class="material-icons-round">visibility</span>
          </button>
          <button class="icon-btn" onclick="downloadFile('${encodeURIComponent(f.name)}')">
            <span class="material-icons-round">download</span>
          </button>
          <button class="icon-btn" onclick="delFile('${encodeURIComponent(f.name)}')">
            <span class="material-icons-round">delete</span>
          </button>
        </td>
      `;
      tbody.appendChild(tr);
    });
  }
}

function makeCard(fileData) {
  const div = document.createElement('div');
  div.className = 'file-card';

  const img = document.createElement('img');
  img.className = 'file-thumb';
  const url = apiBase() + "/download/" + encodeURIComponent(fileData.name) + "?token=" + encodeURIComponent(TOKEN);

  if (fileData.type === 'image') {
    img.src = url;
    img.alt = fileData.name;
  } else if (fileData.type === 'video') {
    img.src = 'data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" width="200" height="200"><rect fill="%23000" width="200" height="200"/><text x="50%" y="50%" fill="%23fff" font-size="60" text-anchor="middle" dy=".3em">▶</text></svg>';
    img.alt = 'video';
  } else {
    img.src = 'data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" width="200" height="200"><rect fill="%23f0f0f0" width="200" height="200"/><text x="50%" y="50%" fill="%23666" font-size="40" text-anchor="middle" dy=".3em">📄</text></svg>';
    img.alt = 'file';
  }

  img.onclick = () => openPreview(encodeURIComponent(fileData.name));

  const meta = document.createElement('div');
  meta.className = 'file-meta';

  const name = document.createElement('div');
  name.className = 'file-name';
  name.textContent = fileData.name.split('/').pop();
  name.title = fileData.name;

  const info = document.createElement('div');
  info.className = 'file-info';
  info.innerHTML = `
    <span>${fileData.size_formatted}</span>
    <span>${formatDate(fileData.modified)}</span>
  `;

  const actions = document.createElement('div');
  actions.className = 'file-actions';

  const dl = document.createElement('button');
  dl.className = 'icon-btn';
  dl.innerHTML = '<span class="material-icons-round">download</span>';
  dl.onclick = (e) => {
    e.stopPropagation();
    downloadFile(encodeURIComponent(fileData.name));
  };

  const rm = document.createElement('button');
  rm.className = 'icon-btn';
  rm.innerHTML = '<span class="material-icons-round">delete</span>';
  rm.onclick = (e) => {
    e.stopPropagation();
    delFile(encodeURIComponent(fileData.name));
  };

  actions.appendChild(dl);
  actions.appendChild(rm);

  meta.appendChild(name);
  meta.appendChild(info);

  div.appendChild(img);
  div.appendChild(meta);
  div.appendChild(actions);

  return div;
}

// ========== UPLOAD ==========
async function upload() {
  if (!TOKEN) {
    await promptLogin();
    if (!TOKEN) return;
  }

  const files = el('file').files;
  if (!files || files.length === 0) return;

  let targetFolder = CURRENT_FOLDER || "";

  // Upload each file
  for (let i = 0; i < files.length; i++) {
    const f = files[i];
    await uploadSingleFile(f, targetFolder, i + 1, files.length);
  }

  // Clear input
  el('file').value = '';

  // Refresh UI
  await refreshUI();
}

async function uploadSingleFile(file, folder, current, total) {
  const form = new FormData();
  form.append('token', TOKEN);

  const filename = folder ? (folder + '/' + file.name) : file.name;
  form.append('file', file, filename);

  // Show progress
  const progressEl = el('uploadProgress');
  progressEl.classList.remove('hidden');
  el('uploadText').textContent = `Uploading ${current} of ${total}: ${file.name}`;
  el('uploadPercent').textContent = '0%';
  el('progressFill').style.width = '0%';

  try {
    const xhr = new XMLHttpRequest();

    xhr.upload.addEventListener('progress', (e) => {
      if (e.lengthComputable) {
        const percent = Math.round((e.loaded / e.total) * 100);
        el('uploadPercent').textContent = `${percent}%`;
        el('progressFill').style.width = `${percent}%`;
      }
    });

    xhr.addEventListener('load', () => {
      if (xhr.status === 200) {
        el('uploadText').textContent = `Uploaded ${current} of ${total}`;
        setTimeout(() => {
          if (current === total) {
            progressEl.classList.add('hidden');
          }
        }, 1000);
      } else {
        alert(`Upload failed for ${file.name}`);
        progressEl.classList.add('hidden');
      }
    });

    xhr.addEventListener('error', () => {
      alert(`Upload error for ${file.name}`);
      progressEl.classList.add('hidden');
    });

    xhr.open('POST', apiBase() + '/upload');
    xhr.send(form);

    // Wait for completion
    await new Promise((resolve) => {
      xhr.addEventListener('loadend', resolve);
    });
  } catch (e) {
    console.error('Upload error:', e);
    alert(`Upload failed for ${file.name}`);
    progressEl.classList.add('hidden');
  }
}

// ========== DRAG & DROP ==========
function setupDragDrop() {
  const contentArea = el('contentArea');

  contentArea.addEventListener('dragover', (e) => {
    e.preventDefault();
    contentArea.classList.add('drag-over');
  });

  contentArea.addEventListener('dragleave', (e) => {
    e.preventDefault();
    contentArea.classList.remove('drag-over');
  });

  contentArea.addEventListener('drop', async (e) => {
    e.preventDefault();
    contentArea.classList.remove('drag-over');

    const files = e.dataTransfer.files;
    if (!files || files.length === 0) return;

    if (!TOKEN) {
      await promptLogin();
      if (!TOKEN) return;
    }

    // Upload dropped files
    const targetFolder = CURRENT_FOLDER || "";

    for (let i = 0; i < files.length; i++) {
      await uploadSingleFile(files[i], targetFolder, i + 1, files.length);
    }

    await refreshUI();
  });
}

// ========== PREVIEW ==========
async function openPreview(encodedName) {
  const name = decodeURIComponent(encodedName);
  CURRENT_PREVIEW = name;

  // Find index in current filtered list
  const q = el('search').value.toLowerCase();
  const inFolder = n => {
    if (!CURRENT_FOLDER) return true;
    return n.startsWith(CURRENT_FOLDER + '/');
  };
  const filtered = FILES.filter(f => inFolder(f) && (!q || f.toLowerCase().includes(q)));
  CURRENT_PREVIEW_INDEX = filtered.indexOf(name);

  el('previewName').textContent = name.split('/').pop();
  el('previewBody').innerHTML = '<div class="preview-nav"><button onclick="navigatePreview(-1)"><span class="material-icons-round">chevron_left</span></button><button onclick="navigatePreview(1)"><span class="material-icons-round">chevron_right</span></button></div>';

  const url = apiBase() + "/download/" + encodeURIComponent(name) + "?token=" + encodeURIComponent(TOKEN);

  // Get file type
  const fileData = FILES_DETAILED.find(f => f.name === name);
  const type = fileData ? fileData.type : 'other';

  if (type === 'image') {
    const im = document.createElement('img');
    im.src = url;
    im.alt = name;
    el('previewBody').appendChild(im);

    if (fileData) {
      el('previewFooter').textContent = `${fileData.size_formatted} • ${formatDate(fileData.modified)}`;
    }
  } else if (type === 'video') {
    const v = document.createElement('video');
    v.src = url;
    v.controls = true;
    v.autoplay = true;
    v.style.maxWidth = '100%';
    v.style.maxHeight = '70vh';
    el('previewBody').appendChild(v);

    if (fileData) {
      el('previewFooter').textContent = `${fileData.size_formatted} • ${formatDate(fileData.modified)}`;
    }
  } else if (name.match(/\.(pdf)$/i)) {
    const iframe = document.createElement('iframe');
    iframe.src = url;
    iframe.style.width = '100%';
    iframe.style.height = '70vh';
    iframe.style.border = 'none';
    iframe.style.borderRadius = 'var(--radius-md)';
    el('previewBody').appendChild(iframe);
  } else {
    try {
      const resp = await fetch(url);
      const txt = await resp.text();
      const pre = document.createElement('pre');
      pre.style.maxHeight = '60vh';
      pre.style.overflow = 'auto';
      pre.style.padding = '16px';
      pre.style.background = 'var(--surface)';
      pre.style.borderRadius = 'var(--radius-md)';
      pre.textContent = txt.slice(0, 20000);
      el('previewBody').appendChild(pre);
    } catch (e) {
      el('previewBody').innerHTML = '<p style="color: var(--text-secondary);">Preview not available</p>';
    }
  }

  el('previewModal').classList.remove('hidden');
}

function closePreview() {
  el('previewModal').classList.add('hidden');
  CURRENT_PREVIEW = null;
  CURRENT_PREVIEW_INDEX = -1;
}

function navigatePreview(direction) {
  const q = el('search').value.toLowerCase();
  const inFolder = n => {
    if (!CURRENT_FOLDER) return true;
    return n.startsWith(CURRENT_FOLDER + '/');
  };
  const filtered = FILES.filter(f => inFolder(f) && (!q || f.toLowerCase().includes(q)));

  if (filtered.length === 0) return;

  let newIndex = CURRENT_PREVIEW_INDEX + direction;
  if (newIndex < 0) newIndex = filtered.length - 1;
  if (newIndex >= filtered.length) newIndex = 0;

  openPreview(encodeURIComponent(filtered[newIndex]));
}

function downloadCurrent() {
  if (CURRENT_PREVIEW) downloadFile(encodeURIComponent(CURRENT_PREVIEW));
}

function toggleFullscreen() {
  const modal = el('previewModal');
  if (!document.fullscreenElement) {
    modal.requestFullscreen().catch(err => console.error('Fullscreen error:', err));
  } else {
    document.exitFullscreen();
  }
}

// ========== FILE OPERATIONS ==========
function downloadFile(encoded) {
  const name = decodeURIComponent(encoded);
  const url = apiBase() + "/download/" + encodeURIComponent(name) + "?token=" + encodeURIComponent(TOKEN);
  window.open(url, '_blank');
}

async function delFile(encoded) {
  const name = decodeURIComponent(encoded);
  if (!confirm(`Delete "${name}"?`)) return;

  const res = await fetch(
    apiBase() + "/delete/" + encodeURIComponent(name) + "?token=" + encodeURIComponent(TOKEN),
    { method: 'DELETE' }
  );

  if (res.ok) {
    await refreshUI();
  } else {
    alert('Delete failed');
  }
}

// ========== VIEW TOGGLE ==========
function toggleView() {
  VIEW = VIEW === 'grid' ? 'list' : 'grid';
  el('gridView').classList.toggle('hidden', VIEW !== 'grid');
  el('listView').classList.toggle('hidden', VIEW === 'grid');
  el('viewIcon').textContent = VIEW === 'grid' ? 'view_list' : 'grid_view';
}

// ========== MODALS ==========
function showQRModal() {
  el('qrModal').classList.remove('hidden');
}

function hideQRModal() {
  el('qrModal').classList.add('hidden');
}

function toggleSettings() {
  el('settingsDrawer').classList.toggle('hidden');
}

function handleModalClick(e) {
  if (e.target.classList.contains('modal')) {
    e.target.classList.add('hidden');
  }
}

// ========== UTILITIES ==========
function escapeHTML(s) {
  return (s || '').toString()
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#039;');
}

function formatBytes(bytes) {
  if (!bytes || bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

function formatDate(isoString) {
  if (!isoString) return '';
  const date = new Date(isoString);
  const now = new Date();
  const diff = now - date;
  const days = Math.floor(diff / (1000 * 60 * 60 * 24));

  if (days === 0) return 'Today';
  if (days === 1) return 'Yesterday';
  if (days < 7) return `${days} days ago`;
  if (days < 30) return `${Math.floor(days / 7)} weeks ago`;
  if (days < 365) return `${Math.floor(days / 30)} months ago`;

  return date.toLocaleDateString();
}

async function fetchPublicUrl() {
  try {
    const res = await fetch('/public_url.txt');
    if (res.ok) {
      const txt = await res.text();
      PUBLIC_URL = txt.trim();
      el('publicLinkArea').innerHTML = PUBLIC_URL
        ? `<a href="${PUBLIC_URL}" target="_blank" style="color: var(--accent); text-decoration: none;">Public Link ↗</a>`
        : '';
    }
  } catch (e) {
    // Ignore
  }
}
