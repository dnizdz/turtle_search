let ALL_ITEMS = [];
let ACTIVE_CATEGORY = "";

const cardsEl = document.getElementById("cards");
const categoryRowEl = document.getElementById("categoryRow");
const metaEl = document.getElementById("meta");
const searchBox = document.getElementById("searchBox");

function fmtPrice(p) {
  return Math.round(Number(p)).toLocaleString("en-US");
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
    card.addEventListener("click", () => openEdit(it));
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
  const data = await res.json();
  ALL_ITEMS = data.items || [];
  renderCategories();
  render();
}

searchBox.addEventListener("input", render);

// Admin menu
const menuBtn = document.getElementById("menuBtn");
const menuPanel = document.getElementById("menuPanel");
menuBtn.addEventListener("click", () => menuPanel.classList.toggle("hidden"));
document.addEventListener("click", (e) => {
  if (!menuPanel.contains(e.target) && e.target !== menuBtn) menuPanel.classList.add("hidden");
});

document.getElementById("reloadBtn").addEventListener("click", async () => {
  const token = document.getElementById("adminToken").value;
  const statusEl = document.getElementById("menuStatus");
  statusEl.textContent = "Reloading...";
  try {
    const res = await fetch("/api/admin/reload", { method: "POST", headers: { "X-Admin-Token": token } });
    if (!res.ok) throw new Error((await res.json()).detail || res.statusText);
    statusEl.textContent = "Reloaded.";
    await loadItems();
  } catch (err) {
    statusEl.textContent = "Error: " + err.message;
  }
});

// Edit modal
const editModal = document.getElementById("editModal");
let editingCode = null;

function openEdit(it) {
  editingCode = it.code;
  document.getElementById("editItem").value = it.item;
  document.getElementById("editCategory").value = it.category;
  document.getElementById("editStatus").value = it.status || "";
  document.getElementById("editPrice").value = it.price;
  document.getElementById("editStatusMsg").textContent = "";
  editModal.classList.remove("hidden");
}

document.getElementById("cancelEditBtn").addEventListener("click", () => editModal.classList.add("hidden"));

document.getElementById("saveEditBtn").addEventListener("click", async () => {
  const token = document.getElementById("adminToken").value;
  const msgEl = document.getElementById("editStatusMsg");
  const payload = {
    code: editingCode,
    item: document.getElementById("editItem").value,
    category: document.getElementById("editCategory").value,
    status: document.getElementById("editStatus").value,
    price: Math.round(parseFloat(document.getElementById("editPrice").value)),
  };
  try {
    const res = await fetch("/api/admin/update", {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-Admin-Token": token },
      body: JSON.stringify(payload),
    });
    if (!res.ok) throw new Error((await res.json()).detail || res.statusText);
    msgEl.textContent = "Saved.";
    await loadItems();
    setTimeout(() => editModal.classList.add("hidden"), 400);
  } catch (err) {
    msgEl.textContent = "Error: " + err.message;
  }
});

loadItems();
