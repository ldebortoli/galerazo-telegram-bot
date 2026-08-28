const tg = window.Telegram?.WebApp;
const state = { data: null, tab: "album", busy: false };
const $ = (selector) => document.querySelector(selector);

if (tg) {
  tg.ready();
  tg.expand();
  if (tg.isVersionAtLeast?.("6.1")) {
    tg.setHeaderColor("#090b0d");
    tg.setBackgroundColor("#090b0d");
  }
}

document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll(".tab").forEach((button) => {
    button.addEventListener("click", () => showTab(button.dataset.tab));
  });
  $("#album-select").addEventListener("change", (event) => load(event.target.value));
  $("#donor-public").addEventListener("change", updateVisibility);
  $("#retry").addEventListener("click", () => load());
  load();
});

async function api(path, options = {}) {
  const headers = { "X-Telegram-Init-Data": tg?.initData || "", ...(options.headers || {}) };
  const response = await fetch(path, { ...options, headers });
  if (!response.ok) throw new Error((await response.text()) || `Error ${response.status}`);
  return response.json();
}

async function load(chatId = null) {
  $("#loading").hidden = false;
  $("#error").hidden = true;
  $("#content").hidden = true;
  try {
    const suffix = chatId ? `?chat_id=${encodeURIComponent(chatId)}` : "";
    state.data = await api(`/api/bootstrap${suffix}`);
    render();
    $("#loading").hidden = true;
    $("#content").hidden = false;
  } catch (error) {
    $("#loading").hidden = true;
    $("#error-message").textContent = error.message;
    $("#error").hidden = false;
  }
}

function showTab(name) {
  state.tab = name;
  document.querySelectorAll(".tab").forEach((button) => button.classList.toggle("active", button.dataset.tab === name));
  document.querySelectorAll(".panel").forEach((panel) => panel.classList.toggle("active", panel.id === `tab-${name}`));
}

function render() {
  const data = state.data;
  const select = $("#album-select");
  select.replaceChildren(...data.albums.map((album) => option(album.title, album.chat_id, album.chat_id === data.selected_chat_id)));
  select.disabled = data.albums.length < 2;
  const selected = data.albums.find((album) => album.chat_id === data.selected_chat_id);
  const discovered = data.natural_hisopos.filter((item) => item.quantity > 0).length;
  const total = data.natural_hisopos.length;
  $("#album-summary").innerHTML = selected
    ? `<span class="kicker">${escapeHtml(selected.title)}</span><strong>${discovered} de ${total}</strong><div class="progress-track"><div class="progress-bar" style="width:${Math.round(discovered / total * 100)}%"></div></div><p>${selected.captures} capturas históricas · los cosméticos son globales</p>`
    : `<span class="kicker">MIS ÁLBUMES</span><h2>Todavía no hay una colección</h2><p>Capturá tu primer Hisopo en un grupo para que aparezca acá.</p>`;
  $("#natural-count").textContent = `${discovered}/${total}`;
  $("#natural-grid").replaceChildren(...data.natural_hisopos.map(collectibleCard));
  const owned = data.paid_hisopos.filter((item) => item.quantity > 0);
  $("#paid-count").textContent = String(owned.length);
  $("#owned-grid").replaceChildren(...(owned.length ? owned.map(collectibleCard) : [emptyCard("Todavía no compraste Hisopos cosméticos.")]));
  $("#store-grid").replaceChildren(...data.paid_hisopos.filter((item) => !item.club_only).map(productCard));
  renderClub();
  $("#donation-buttons").replaceChildren(...data.donation_tiers.map((amount) => actionButton(`⭐ ${amount}`, () => checkout("donation", String(amount)))));
  $("#donor-public").checked = data.donor_public;
  renderPrivacyCopy();
  $("#donor-list").replaceChildren(...(data.donors.length ? data.donors.map(donorRow) : [emptyCard("Todavía no hay aportes confirmados.")]));
}

function collectibleCard(item) {
  const card = document.createElement("article");
  card.className = `collectible ${item.quantity ? "" : "locked"}`;
  card.innerHTML = `<img src="${item.image}" alt="${escapeHtml(item.name)}" loading="lazy"><span class="quantity">×${item.quantity}</span>${item.quantity ? "" : '<span class="lock">?</span>'}<div class="collectible-body"><h3>${escapeHtml(item.name)}</h3><p>${item.quantity ? "En tu colección" : "Sin descubrir"}</p></div>`;
  return card;
}

function productCard(item) {
  const card = document.createElement("article");
  card.className = "product";
  card.innerHTML = `<img src="${item.image}" alt="${escapeHtml(item.name)}" loading="lazy"><div class="product-body"><h3>${escapeHtml(item.name)}</h3><p>${escapeHtml(item.description)}</p><div class="buy-row"><span class="price">⭐ ${item.price_stars}</span></div></div>`;
  const button = actionButton(item.quantity ? "Ya es tuyo" : "Comprar", () => checkout("product", item.key));
  button.disabled = item.quantity > 0;
  card.querySelector(".buy-row").append(button);
  return card;
}

function renderClub() {
  const club = state.data.club;
  const card = $("#club-card");
  card.innerHTML = `<span class="kicker">MEMBRESÍA · CADA 30 DÍAS</span><h2>Club del Hisopo</h2><p>Recibís un Hisopo Estelar por cada período confirmado. Si cancelás, los que ya pagaste siguen en tu colección.</p><div class="buy-row"><span class="price">⭐ ${club.price_stars} / 30 días</span></div>${club.periods_paid ? `<p>Períodos acreditados: ${club.periods_paid}${club.active_until ? ` · vigente hasta ${formatDate(club.active_until)}` : ""}</p>` : ""}`;
  card.querySelector(".buy-row").append(actionButton(club.periods_paid ? "Gestionar o renovar" : "Sumarme al Club", () => checkout("subscription", "club")));
}

async function checkout(kind, itemKey) {
  if (state.busy) return;
  state.busy = true;
  try {
    const result = await api("/api/invoice", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ kind, item_key: itemKey, source_chat_id: state.data.selected_chat_id })
    });
    if (result.preview) {
      toast(result.message);
    } else if (tg?.openInvoice) {
      tg.openInvoice(result.invoice_url, (status) => {
        toast(status === "paid" ? "Pago confirmado. Actualizando colección…" : `Pago: ${status}`);
        if (status === "paid") setTimeout(() => load(state.data.selected_chat_id), 600);
      });
    } else {
      window.location.href = result.invoice_url;
    }
  } catch (error) {
    toast(error.message);
  } finally {
    state.busy = false;
  }
}

async function updateVisibility(event) {
  const isPublic = event.target.checked;
  try {
    await api("/api/donor-visibility", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ public: isPublic })
    });
    state.data.donor_public = isPublic;
    renderPrivacyCopy();
    toast(isPublic ? "Tu nombre podrá aparecer en el ranking." : "Tus aportes vuelven a mostrarse como Anónimo.");
  } catch (error) {
    event.target.checked = !isPublic;
    toast(error.message);
  }
}

function renderPrivacyCopy() {
  $("#privacy-copy").textContent = state.data.donor_public
    ? "Tu nombre puede aparecer junto al total de aportes confirmados."
    : "Tus aportes aparecen como Anónimo. Las compras y cuotas del Club no cuentan.";
}

function donorRow(item) {
  const row = document.createElement("li");
  row.innerHTML = `<span class="donor-name">${escapeHtml(item.name)}</span><strong>⭐ ${item.amount_stars}</strong>`;
  return row;
}

function actionButton(label, handler) {
  const button = document.createElement("button");
  button.className = "button";
  button.type = "button";
  button.textContent = label;
  button.addEventListener("click", handler);
  return button;
}

function emptyCard(text) {
  const node = document.createElement("div");
  node.className = "empty";
  node.textContent = text;
  return node;
}

function option(label, value, selected) {
  const node = document.createElement("option");
  node.value = value;
  node.textContent = label;
  node.selected = selected;
  return node;
}

function toast(message) {
  const node = $("#toast");
  node.textContent = message;
  node.classList.add("visible");
  clearTimeout(toast.timer);
  toast.timer = setTimeout(() => node.classList.remove("visible"), 3200);
}

function formatDate(value) {
  return new Intl.DateTimeFormat("es-AR", { dateStyle: "medium" }).format(new Date(value));
}

function escapeHtml(value) {
  const node = document.createElement("span");
  node.textContent = String(value);
  return node.innerHTML;
}
