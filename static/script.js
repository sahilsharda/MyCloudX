let TOKEN = "";

function apiBase() { return window.location.origin; }

async function login() {
  const t = document.getElementById('token').value.trim();
  const form = new FormData();
  form.append("token", t);
  const res = await fetch(apiBase() + "/auth", { method: "POST", body: form });
  if (res.ok) {
    TOKEN = t;
    document.getElementById('authPanel').style.display = 'none';
    refresh();
  } else {
    alert("Invalid token!");
  }
}

function toggleAuth() {
  document.getElementById('authPanel').style.display =
    document.getElementById('authPanel').style.display === 'none' ? 'flex' : 'none';
}

async function upload() {
  if (!TOKEN) return alert("Please login first");
  const fileInput = document.getElementById('file');
  const file = fileInput.files[0];
  if (!file) return;
  const form = new FormData();
  form.append("file", file);
  form.append("token", TOKEN);
  const res = await fetch(apiBase() + "/upload", { method: "POST", body: form });
  if (res.ok) refresh();
}

async function refresh() {
  const res = await fetch(apiBase() + "/list?token=" + encodeURIComponent(TOKEN));
  const data = await res.json();
  const grid = document.getElementById('gallery');
  grid.innerHTML = "";
  data.files.forEach(f => {
    const card = document.createElement('div');
    card.className = 'file-card';
    const thumb = document.createElement('img');
    thumb.className = 'file-thumb';
    thumb.src = f.match(/\.(jpg|jpeg|png|gif)$/i)
      ? apiBase() + "/download/" + f + "?token=" + TOKEN
      : "https://cdn-icons-png.flaticon.com/512/3767/3767084.png";
    const name = document.createElement('div');
    name.className = 'file-name';
    name.textContent = f;

    const actions = document.createElement('div');
    actions.className = 'file-actions';
    const d = document.createElement('button');
    d.innerHTML = '<span class="material-icons-round" style="font-size:18px;">delete</span>';
    d.onclick = () => delFile(f);
    const dl = document.createElement('button');
    dl.innerHTML = '<span class="material-icons-round" style="font-size:18px;">download</span>';
    dl.onclick = () => window.open(apiBase() + "/download/" + f + "?token=" + TOKEN);

    actions.appendChild(dl);
    actions.appendChild(d);
    card.appendChild(actions);
    card.appendChild(thumb);
    card.appendChild(name);
    grid.appendChild(card);
  });
}

async function delFile(name) {
  if (!confirm("Delete " + name + "?")) return;
  await fetch(apiBase() + "/delete/" + encodeURIComponent(name) + "?token=" + TOKEN, { method: "DELETE" });
  refresh();
}

function showQRModal() {
  document.getElementById("qrModal").style.display = "flex";
}

function hideQRModal() {
  document.getElementById("qrModal").style.display = "none";
}

function handleModalClick(e) {
  if (e.target.id === "qrModal") hideQRModal();
}
