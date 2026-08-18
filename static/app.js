let ALL_ITEMS = [];
let ACTIVE_CATEGORY = "";

const cardsEl = document.getElementById("cards");
const categoryRowEl = document.getElementById("categoryRow");
const metaEl = document.getElementById("meta");
const searchBox = document.getElementById("searchBox");
const loginOverlay = document.getElementById("loginOverlay");
const appRoot = document.getElementById("appRoot");
const toastEl = document.getElementById("toast");

function fmtPrice(p) {
  return Math.round(Number(p)).toLocaleString("en-US");
}

let toastTimer = null;
function showToast(message, isError) {
  toastEl.textContent = message;
  toastEl.className = "toast" + (isError ? " error" : " success");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => toastEl.classList.add("hidden"), 2500);
}

function render() {
  const q = searchBox.value.trim().toLowerCase();
  const filtered = ALL_ITEMS.filter((it) => {
    if (ACTIVE_CATEGORY && it.category !== ACTIVE_CATEGORY) return false;
    if (q && !it.item.toLowerCase().includes(q)) return false;
    return true;
  });
  metaEl.textContent = `${filtered.length} item(s)`;
  cardsEl.innerHTML = "";
  for (const it of filtered) {
    const card = document.createElement("div");
    card.className = "card";
    card.innerHTML = `
      <div class="cat">${it.category}</div>
      <div class="name">${it.item}</div>
      <div class="price">${fmtPrice(it.price)}</div>
      <div class="status">${it.status || ""}</div>
    `;
    cardsEl.appendChild(card);
  }
}

function renderCategories() {
  const cats = [...new Set(ALL_ITEMS.map((it) => it.category))].sort();
  categoryRowEl.innerHTML = "";
  const allChip = document.createElement("div");
  allChip.className = "category-chip" + (ACTIVE_CATEGORY === "" ? " active" : "");
  allChip.textContent = "All";
  allChip.addEventListener("click", () => { ACTIVE_CATEGORY = ""; renderCategories(); render(); });
  categoryRowEl.appendChild(allChip);
  for (const c of cats) {
    const chip = document.createElement("div");
    chip.className = "category-chip" + (ACTIVE_CATEGORY === c ? " active" : "");
    chip.textContent = c;
    chip.addEventListener("click", () => { ACTIVE_CATEGORY = c; renderCategories(); render(); });
    categoryRowEl.appendChild(chip);
  }
}

async function loadItems() {
  const res = await fetch("/api/items");
  if (res.status === 401) {
    showLogin();
    return false;
  }
  const data = await res.json();
  ALL_ITEMS = data.items || [];
  renderCategories();
  render();
  return true;
}

async function loadConfig() {
  const res = await fetch("/api/config");
  if (res.status === 401) return;
  const cfg = await res.json();
  document.getElementById("sheetUrl").value = cfg.sheet_url || "";
}

function showLogin() {
  appRoot.classList.add("hidden");
  loginOverlay.classList.remove("hidden");
}

function showApp() {
  loginOverlay.classList.add("hidden");
  appRoot.classList.remove("hidden");
}

searchBox.addEventListener("input", render);

document.getElementById("refreshBtn").addEventListener("click", async () => {
  const btn = document.getElementById("refreshBtn");
  btn.disabled = true;
  btn.textContent = "...";
  try {
    const res = await fetch("/api/refresh", { method: "POST" });
    if (res.status === 401) { showLogin(); return; }
    if (!res.ok) throw new Error((await res.json()).detail || res.statusText);
    await loadItems();
    showToast("Refreshed", false);
  } catch (err) {
    showToast("Refresh failed: " + err.message, true);
  } finally {
    btn.disabled = false;
    btn.textContent = "Refresh";
  }
});

// Menu (spreadsheet link)
const menuBtn = document.getElementById("menuBtn");
const menuPanel = document.getElementById("menuPanel");
menuBtn.addEventListener("click", async () => {
  const opening = menuPanel.classList.contains("hidden");
  menuPanel.classList.toggle("hidden");
  if (opening) await loadConfig();
});
document.addEventListener("click", (e) => {
  if (!menuPanel.contains(e.target) && e.target !== menuBtn) menuPanel.classList.add("hidden");
});

document.getElementById("saveSheetBtn").addEventListener("click", async () => {
  const sheetUrl = document.getElementById("sheetUrl").value.trim();
  const statusEl = document.getElementById("menuStatus");
  statusEl.textContent = "Saving...";
  try {
    const res = await fetch("/api/config", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ sheet_url: sheetUrl }),
    });
    if (res.status === 401) { showLogin(); return; }
    if (!res.ok) throw new Error((await res.json()).detail || res.statusText);
    statusEl.textContent = "Saved.";
    showToast("Spreadsheet link saved", false);
  } catch (err) {
    statusEl.textContent = "Error: " + err.message;
    showToast("Save failed: " + err.message, true);
  }
});

// Login
async function tryLogin() {
  const password = document.getElementById("loginPassword").value;
  const statusEl = document.getElementById("loginStatus");
  statusEl.textContent = "";
  try {
    const res = await fetch("/api/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ password }),
    });
    if (!res.ok) {
      statusEl.textContent = "Wrong password.";
      return;
    }
    showApp();
    await loadItems();
  } catch (err) {
    statusEl.textContent = "Error: " + err.message;
  }
}

document.getElementById("loginBtn").addEventListener("click", tryLogin);
document.getElementById("loginPassword").addEventListener("keydown", (e) => {
  if (e.key === "Enter") tryLogin();
});

(async function init() {
  const ok = await loadItems();
  if (ok) showApp();
})();
