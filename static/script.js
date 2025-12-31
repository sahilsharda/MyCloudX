// MyCloudX - JWT Authentication Version

let TOKEN = "";
let CURRENT_FOLDER = "";
let FILES = [];
let FOLDERS = [];
let FILES_DETAILED = [];
let CURRENT_PREVIEW = null;
let CURRENT_PREVIEW_INDEX = -1;
let STORAGE_STATS = null;

// Helpers
const el = id => document.getElementById(id);
const apiBase = () => window.location.origin;

// ========== INITIALIZATION ==========
document.addEventListener('DOMContentLoaded', () => {
  bindUI();
  setThemeFromStorage();
  initializeGoogleAuth();

  // Check for saved token
  const savedToken = localStorage.getItem('mycloud_jwt');
  if (savedToken) {
    TOKEN = savedToken;
    if (isTokenExpired(TOKEN)) {
      logout();
    } else {
      // Verify token validity by fetching list
      refreshUI().catch(() => {
        logout();
      });
      // Start periodic check
      setInterval(checkTokenExpiry, 60000); // Check every minute
    }
  } else {
    showAuthModal();
  }
});

function isTokenExpired(token) {
  if (!token) return true;
  try {
    const payload = JSON.parse(atob(token.split('.')[1]));
    const now = Math.floor(Date.now() / 1000);
    return payload.exp < now;
  } catch (e) {
    return true;
  }
}

function checkTokenExpiry() {
  if (TOKEN && isTokenExpired(TOKEN)) {
    alert('Session expired. Please log in again.');
    logout();
  }
}

function bindUI() {
  // Auth
  el('doLoginBtn').addEventListener('click', doLogin);
  el('doRegisterBtn').addEventListener('click', doRegister);
  el('showRegister').addEventListener('click', (e) => { e.preventDefault(); toggleAuthMode('register'); });
  el('showLogin').addEventListener('click', (e) => { e.preventDefault(); toggleAuthMode('login'); });
  el('logoutBtn').addEventListener('click', logout);

  // Main UI
  el('viewToggle').addEventListener('click', toggleView);
  el('file').addEventListener('change', upload);
  el('qrOpenSettings')?.addEventListener('click', showQRModal);
  el('openSettings').addEventListener('click', toggleSettings);
  el('saveProfileBtn')?.addEventListener('click', saveProfileName);
  el('newFolderBtn').addEventListener('click', createFolderPrompt);
  el('search').addEventListener('input', renderFiles);
  el('themeSelect')?.addEventListener('change', handleThemeSelect);

  // Mobile
  el('menuBtn')?.addEventListener('click', toggleSidebar);
  el('sidebarOverlay')?.addEventListener('click', toggleSidebar);

  // Keyboard
  document.addEventListener('keydown', handleKeyboard);
}

// ========== AUTHENTICATION ==========
function showAuthModal() {
  el('app').classList.add('hidden');
  el('authModal').classList.remove('hidden');
  el('loginUser').focus();
}

function showApp() {
  el('authModal').classList.add('hidden');
  el('app').classList.remove('hidden');
  loadProfileName();
}

function toggleAuthMode(mode) {
  const loginForm = el('loginForm');
  const registerForm = el('registerForm');

  // Fade out current form
  const activeForm = loginForm.classList.contains('hidden') ? registerForm : loginForm;
  activeForm.style.opacity = '0';
  activeForm.style.transform = 'translateY(10px)';

  setTimeout(() => {
    if (mode === 'register') {
      loginForm.classList.add('hidden');
      registerForm.classList.remove('hidden');
      el('authTitle').textContent = 'Create Account';
      el('authSubtitle').textContent = 'Join MyCloudX today';
    } else {
      registerForm.classList.add('hidden');
      loginForm.classList.remove('hidden');
      el('authTitle').textContent = 'Welcome Back';
      el('authSubtitle').textContent = 'Sign in to access your cloud';
    }

    // Fade in new form
    const newForm = mode === 'register' ? registerForm : loginForm;
    newForm.style.opacity = '0';
    newForm.style.transform = 'translateY(-10px)';

    // Force reflow
    newForm.offsetHeight;

    newForm.style.transition = 'all 0.4s ease';
    newForm.style.opacity = '1';
    newForm.style.transform = 'translateY(0)';
  }, 300);
}

async function doLogin() {
  const user = el('loginUser').value.trim();
  const pass = el('loginPass').value.trim();
  if (!user || !pass) return alert('Please enter username and password');

  try {
    const form = new FormData();
    form.append('username', user);
    form.append('password', pass);

    const res = await fetch(apiBase() + "/token", { method: 'POST', body: form });
    if (!res.ok) throw new Error('Invalid credentials');

    const data = await res.json();
    TOKEN = data.access_token;
    localStorage.setItem('mycloud_jwt', TOKEN);
    localStorage.setItem('mycloud_username', user);

    showApp();
    refreshUI();
  } catch (e) {
    alert(e.message);
  }
}

async function doRegister() {
  const user = el('regUser').value.trim();
  const pass = el('regPass').value.trim();
  if (!user || !pass) return alert('Please choose username and password');

  try {
    const form = new FormData();
    form.append('username', user);
    form.append('password', pass);

    // Register
    const res = await fetch(apiBase() + "/register", { method: 'POST', body: form });
    if (!res.ok) {
      const d = await res.json();
      throw new Error(d.detail || 'Registration failed');
    }

    alert('Account created! Please sign in.');
    toggleAuthMode('login');
    el('loginUser').value = user;
    el('loginPass').focus();
  } catch (e) {
    alert(e.message);
  }
}

function logout() {
  TOKEN = "";
  localStorage.removeItem('mycloud_jwt');
  localStorage.removeItem('mycloud_username');
  window.location.reload();
}

function authHeaders() {
  if (isTokenExpired(TOKEN)) {
    logout();
    throw new Error('Session expired');
  }
  return { 'Authorization': `Bearer ${TOKEN}` };
}

// ========== GOOGLE AUTH ==========
function initializeGoogleAuth() {
  // CRITICAL: Replace with actual Client ID
  const CLIENT_ID = "63790555520-tn4jh7hfidgpqtq4u6ils6p6urj6h8hu.apps.googleusercontent.com";

  if (typeof google === 'undefined') {
    setTimeout(initializeGoogleAuth, 500);
    return;
  }

  google.accounts.id.initialize({
    client_id: CLIENT_ID,
    callback: handleGoogleCredentialResponse
  });

  google.accounts.id.renderButton(
    document.getElementById("googleBtnContainer"),
    { theme: "outline", size: "large", width: 320 }
  );
}

async function handleGoogleCredentialResponse(response) {
  const form = new FormData();
  form.append('credential', response.credential);

  try {
    const res = await fetch(apiBase() + "/auth/google", {
      method: 'POST',
      body: form
    });
    if (!res.ok) throw new Error('Google Sign-In failed');

    const data = await res.json();
    TOKEN = data.access_token;
    localStorage.setItem('mycloud_jwt', TOKEN);
    localStorage.setItem('mycloud_username', data.username);

    showApp();
    refreshUI();
  } catch (e) {
    alert(e.message);
  }
}

// ========== PROFILE ==========
function loadProfileName() {
  const user = localStorage.getItem('mycloud_username') || 'User';
  const display = localStorage.getItem('mycloud_profile_name') || user;

  el('profileName').textContent = display;
  el('profileNameDrawer').textContent = display;
  el('profileNameInput').value = display;

  const init = display.charAt(0).toUpperCase();
  el('profilePic').textContent = init;
  el('profilePicDrawer').textContent = init;
}

function saveProfileName() {
  const name = el('profileNameInput').value.trim();
  if (name) {
    localStorage.setItem('mycloud_profile_name', name);
    loadProfileName();
    alert('Name updated');
  }
}

// ========== MAIN DATA LOOP ==========
async function refreshUI() {
  if (!TOKEN) return;
  el('statusText').textContent = 'Loading...';

  try {
    const res = await fetch(apiBase() + "/list", { headers: authHeaders() });
    if (res.status === 401) { logout(); return; }
    if (!res.ok) throw new Error('Failed to load files');

    const data = await res.json();
    FILES = data.files || [];
    FILES_DETAILED = data.files_detailed || [];
    FOLDERS = data.folders || [];

    buildFolderList(FOLDERS);
    renderFiles();
    fetchStorageStats();
    el('statusText').textContent = 'Connected';
  } catch (e) {
    console.error(e);
    el('statusText').textContent = 'Error';
  }
}

async function fetchStorageStats() {
  try {
    const res = await fetch(apiBase() + "/storage-stats", { headers: authHeaders() });
    if (res.ok) {
      STORAGE_STATS = await res.json();
      updateStorageUI();
    }
  } catch (e) { console.error(e); }
}

function updateStorageUI() {
  if (!STORAGE_STATS) return;
  const { total_size_formatted, quota_formatted, usage_percent, breakdown } = STORAGE_STATS;

  el('storageAmount').textContent = `${total_size_formatted} of ${quota_formatted}`;
  el('storageFill').style.width = `${Math.min(usage_percent, 100)}%`;

  // Breakdown
  el('storageBreakdown').innerHTML = `
    <div class="storage-item"><span>📸 Images</span><span>${formatBytes(breakdown.images.size)}</span></div>
    <div class="storage-item"><span>🎥 Videos</span><span>${formatBytes(breakdown.videos.size)}</span></div>
    <div class="storage-item"><span>📄 Docs</span><span>${formatBytes(breakdown.documents.size)}</span></div>
    <div class="storage-item"><span>📦 Other</span><span>${formatBytes(breakdown.other.size)}</span></div>
  `;
}

// ========== FILE & FOLDER RENDERING ==========
function renderFiles() {
  const q = el('search').value.toLowerCase();
  const validFiles = FILES_DETAILED.filter(f => {
    // Logic for flat list vs folders if needed. For now assuming flat or simple folder filter
    const inFolder = CURRENT_FOLDER ? f.name.startsWith(CURRENT_FOLDER + '/') : true;
    // Note: server returns all files recursively. We need to filter for CURRENT VIEW only.
    // But for simplicity, let's just show everything or implement basic folder logic client side?
    // Server 'list' now returns specific user files.

    // Let's implement client-side folder view:
    // If CURRENT_FOLDER is empty, show files with NO slashes (root).
    // If CURRENT_FOLDER is "A", show files starting with "A/" but having no further slashes.

    const relPath = CURRENT_FOLDER ? f.name.substring(CURRENT_FOLDER.length + 1) : f.name;
    const isDirectChild = !relPath.includes('/') && (CURRENT_FOLDER ? f.name.startsWith(CURRENT_FOLDER + '/') : true);

    // Also simple search override
    if (q) return f.name.toLowerCase().includes(q);

    return isDirectChild;
  });

  const grid = el('gridView');
  grid.innerHTML = '';

  if (validFiles.length === 0) {
    grid.innerHTML = '<div class="empty-state">No files here</div>';
  }

  validFiles.forEach(f => grid.appendChild(makeCard(f)));
}

function makeCard(f) {
  const div = document.createElement('div');
  div.className = 'file-card';

  const img = document.createElement('img');
  img.className = 'file-thumb';
  img.loading = 'lazy';

  // Fetch thumbnail logic with Auth Header
  if (f.type === 'image') {
    img.src = '/static/placeholder.png'; // placeholder
    // Fetch authenticated blob
    fetch(apiBase() + `/thumbnail/${f.name}`, { headers: authHeaders() })
      .then(r => r.blob())
      .then(blob => {
        img.src = URL.createObjectURL(blob);
      })
      .catch(() => {
        // Fallback to fetch full image
        fetch(apiBase() + `/download/${f.name}`, { headers: authHeaders() })
          .then(r => r.blob())
          .then(b => img.src = URL.createObjectURL(b));
      });
  } else {
    // Standard icons
    img.src = f.type === 'video'
      ? 'data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100" viewBox="0 0 24 24"><path fill="%23666" d="M10 8v8l6-4l-6-4Z"/></svg>'
      : 'data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100" viewBox="0 0 24 24"><path fill="%23666" d="M14 2H6c-1.1 0-1.99.9-1.99 2L4 20c0 1.1.89 2 1.99 2H18c1.1 0 2-.9 2-2V8l-6-6zm2 16H8v-2h8v2zm0-4H8v-2h8v2zm-3-5V3.5L18.5 9H13z"/></svg>';
  }

  img.onclick = () => openPreview(f);

  div.innerHTML = `
    <div class="file-meta">
      <div class="file-name" title="${f.name}">${f.name.split('/').pop()}</div>
      <div class="file-info">${f.size_formatted}</div>
    </div>
  `;
  div.prepend(img);

  // Actions
  const actions = document.createElement('div');
  actions.className = 'file-actions';

  const btnDl = document.createElement('button');
  btnDl.className = 'icon-btn';
  btnDl.innerHTML = '<span class="material-icons-round">download</span>';
  btnDl.onclick = (e) => { e.stopPropagation(); downloadFile(f.name); };

  const btnDel = document.createElement('button');
  btnDel.className = 'icon-btn';
  btnDel.innerHTML = '<span class="material-icons-round">delete</span>';
  btnDel.onclick = (e) => { e.stopPropagation(); deleteFile(f.name); };

  actions.append(btnDl, btnDel);
  div.append(actions);

  return div;
}

// ========== OPERATIONS ==========
async function upload() {
  const files = el('file').files;
  if (!files.length) return;

  const folder = CURRENT_FOLDER ? CURRENT_FOLDER : "";

  el('uploadProgress').classList.remove('hidden');

  for (let i = 0; i < files.length; i++) {
    const file = files[i];
    el('uploadText').textContent = `Uploading ${file.name}...`;

    const form = new FormData();
    form.append('file', file);

    try {
      const res = await fetch(apiBase() + '/upload', {
        method: 'POST',
        headers: authHeaders(),
        body: form
      });
      if (!res.ok) alert('Upload failed: ' + file.name);
    } catch (e) { console.error(e); }
  }

  el('file').value = '';
  el('uploadProgress').classList.add('hidden');
  refreshUI();
}

async function downloadFile(name) {
  try {
    const res = await fetch(apiBase() + `/download/${name}`, { headers: authHeaders() });
    if (!res.ok) throw new Error('Download failed');
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = name.split('/').pop();
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
  } catch (e) { alert(e.message); }
}

async function deleteFile(name) {
  if (!confirm('Delete ' + name + '?')) return;
  try {
    const res = await fetch(apiBase() + `/delete/${name}`, {
      method: 'DELETE',
      headers: authHeaders()
    });
    if (res.ok) refreshUI();
  } catch (e) { alert('Delete failed'); }
}

async function createFolderPrompt() {
  const name = prompt('Folder name:');
  if (!name) return;

  // Logic for folder creation not strictly implemented in this script version for brevity 
  // but follows same pattern: fetch('/folders/create', { body: form, headers... })
  alert("Folder creation to be implemented fully in client logic.");
}

// ========== PREVIEW ==========
async function openPreview(f) {
  el('previewModal').classList.remove('hidden');
  el('previewName').textContent = f.name;
  el('previewBody').innerHTML = 'Loading...';

  // Use blob fetch for preview content
  try {
    const res = await fetch(apiBase() + `/download/${f.name}`, { headers: authHeaders() });
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);

    el('previewBody').innerHTML = '';
    if (f.type === 'image') {
      const img = document.createElement('img');
      img.src = url;
      el('previewBody').appendChild(img);
    } else if (f.type === 'video') {
      const vid = document.createElement('video');
      vid.src = url;
      vid.controls = true;
      el('previewBody').appendChild(vid);
    } else {
      el('previewBody').textContent = 'Preview not available for this type';
    }
  } catch (e) {
    el('previewBody').textContent = 'Error loading preview';
  }
}

function closePreview() { el('previewModal').classList.add('hidden'); }
function toggleSidebar() { el('sidebar').classList.toggle('open'); el('sidebarOverlay').classList.toggle('visible'); }
function toggleSettings() { el('settingsDrawer').classList.toggle('hidden'); }
function handleKeyboard(e) { if (e.key === 'Escape') closePreview(); }
function toggleView() { /* Implementation omitted for brevity */ }
function formatBytes(bytes) {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}
function handleThemeSelect(e) {
  if (e.target.value === 'dark') {
    el('app').classList.add('theme-dark');
    el('app').classList.remove('theme-light');
  } else {
    el('app').classList.add('theme-light');
    el('app').classList.remove('theme-dark');
  }
}
function setThemeFromStorage() { /* ... */ }
function buildFolderList(folders) {
  const ul = el('folderList');
  ul.innerHTML = '<li class="folder-item active">All Files</li>';
  // Add logic if desired
}
function showQRModal() { el('qrModal').classList.remove('hidden'); }
function hideQRModal() { el('qrModal').classList.add('hidden'); }
function handleModalClick(e) { if (e.target === e.currentTarget) e.target.classList.add('hidden'); }
