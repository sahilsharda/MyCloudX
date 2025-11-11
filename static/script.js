let TOKEN = "";
function apiBase() { return window.location.origin; }

async function login() {
  const t = document.getElementById('token').value.trim();
  try {
    const form = new FormData();
    form.append("token", t);
    const res = await fetch(apiBase() + "/auth", {
      method: "POST",
      body: form
    });
    if (!res.ok) throw new Error("Bad token");
    TOKEN = t;
    document.getElementById('authStatus').textContent = "✅ Authenticated";
    refresh();
  } catch {
    TOKEN = "";
    document.getElementById('authStatus').textContent = "❌ Invalid token";
  }
}

async function upload() {
  if (!TOKEN) return alert("Please login first");
  const f = document.getElementById('file').files[0];
  if (!f) return alert("Select a file first");
  const form = new FormData();
  form.append("token", TOKEN);
  form.append("file", f);
  const res = await fetch(apiBase() + "/upload", { method: "POST", body: form });
  if (res.ok) { alert("Uploaded ✅"); refresh(); } else alert("Upload failed ❌");
}

async function refresh() {
  if (!TOKEN) return;
  const res = await fetch(apiBase() + "/list?token=" + encodeURIComponent(TOKEN));
  if (!res.ok) return;
  const data = await res.json();
  const tbody = document.getElementById('fileRows');
  tbody.innerHTML = "";
  if (!data.files.length) {
    tbody.innerHTML = `<tr><td class="muted" colspan="2">No files uploaded yet</td></tr>`;
    return;
  }
  for (const name of data.files) {
    const tr = document.createElement('tr');
    const nameCell = document.createElement('td');
    nameCell.textContent = `📄 ${name}`;
    
    const actionsCell = document.createElement('td');
    const downloadLink = document.createElement('a');
    downloadLink.href = `${apiBase()}/download/${encodeURIComponent(name)}?token=${encodeURIComponent(TOKEN)}`;
    downloadLink.textContent = '⬇️ Download';
    
    const deleteLink = document.createElement('a');
    deleteLink.href = '#';
    deleteLink.textContent = '🗑️ Delete';
    deleteLink.onclick = (e) => { e.preventDefault(); delFile(name); return false; };
    
    actionsCell.appendChild(downloadLink);
    actionsCell.appendChild(document.createTextNode(' | '));
    actionsCell.appendChild(deleteLink);
    
    tr.appendChild(nameCell);
    tr.appendChild(actionsCell);
    tbody.appendChild(tr);
  }
}

async function delFile(name) {
  if (!TOKEN) return;
  if (!confirm("Delete " + name + "?")) return;
  const res = await fetch(apiBase() + "/delete/" + encodeURIComponent(name) + "?token=" + encodeURIComponent(TOKEN), { method: "DELETE" });
  if (res.ok) refresh(); else alert("Delete failed ❌");
}

function showQRModal() {
  const modal = document.getElementById("qrModal");
  modal.style.display = "flex";
}

function hideQRModal() {
  const modal = document.getElementById("qrModal");
  modal.style.display = "none";
}

function handleModalClick(e) {
  if (e.target.id === "qrModal") hideQRModal();
}
