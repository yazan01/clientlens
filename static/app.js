const state = {
  clients: [],
  products: [],
  client: null,
  messages: [],
  feedback: "",
};

const $ = (sel) => document.querySelector(sel);

function escapeHtml(s) {
  return s.replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

function renderMarkdown(md) {
  const inline = (t) => escapeHtml(t)
    .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
    .replace(/(^|[^*])\*(?!\s)(.+?)\*/g, "$1<em>$2</em>")
    .replace(/`(.+?)`/g, "<code>$1</code>");
  const lines = md.split(/\r?\n/);
  let html = "", list = null, i = 0;
  const closeList = () => { if (list) { html += `</${list}>`; list = null; } };
  while (i < lines.length) {
    const line = lines[i];
    if (/^\s*\|.*\|\s*$/.test(line) && i + 1 < lines.length && /^\s*\|[\s:|-]+\|\s*$/.test(lines[i + 1])) {
      closeList();
      const cells = (l) => l.trim().replace(/^\||\|$/g, "").split("|").map((c) => inline(c.trim()));
      html += "<table><thead><tr>" + cells(line).map((c) => `<th>${c}</th>`).join("") + "</tr></thead><tbody>";
      i += 2;
      while (i < lines.length && /^\s*\|.*\|\s*$/.test(lines[i])) {
        html += "<tr>" + cells(lines[i]).map((c) => `<td>${c}</td>`).join("") + "</tr>";
        i++;
      }
      html += "</tbody></table>";
      continue;
    }
    let m;
    if ((m = line.match(/^(#{1,4})\s+(.*)/))) { closeList(); html += `<h2>${inline(m[2])}</h2>`; }
    else if ((m = line.match(/^\s*[-*]\s+(.*)/))) { if (list !== "ul") { closeList(); html += "<ul>"; list = "ul"; } html += `<li>${inline(m[1])}</li>`; }
    else if ((m = line.match(/^\s*\d+[.)]\s+(.*)/))) { if (list !== "ol") { closeList(); html += "<ol>"; list = "ol"; } html += `<li>${inline(m[1])}</li>`; }
    else if (line.trim() === "") { closeList(); }
    else { closeList(); html += `<p>${inline(line)}</p>`; }
    i++;
  }
  closeList();
  return html;
}

async function api(path, body) {
  const res = await fetch(path, body ? {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body),
  } : undefined);
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const detail = typeof data.detail === "string" ? data.detail : JSON.stringify(data.detail || data);
    throw new Error(detail || `Request failed (${res.status})`);
  }
  return data;
}

function showStep(step) {
  for (const s of ["select", "interview", "feedback"]) $(`#step-${s}`).classList.toggle("hidden", s !== step);
  document.querySelectorAll(".steps li").forEach((li) => li.classList.toggle("active", li.dataset.step === step));
  window.scrollTo(0, 0);
}

function renderClients() {
  $("#client-list").innerHTML = state.clients.map((c) => `
    <div class="card">
      <h2>${escapeHtml(c.name)}</h2>
      <div class="headline">${escapeHtml(c.headline)}</div>
      <p>${escapeHtml(c.public_profile)}</p>
      <button class="btn" data-client="${escapeHtml(c.id)}">Start interview</button>
    </div>`).join("");
  $("#client-list").querySelectorAll("button").forEach((b) =>
    b.addEventListener("click", () => startInterview(b.dataset.client)));
}

function startInterview(clientId) {
  state.client = state.clients.find((c) => c.id === clientId);
  state.messages = [];
  state.feedback = "";
  $("#chat-client-name").textContent = state.client.name;
  $("#chat-client-headline").textContent = state.client.headline;
  $("#summary").value = "";
  $("#feedback").innerHTML = "Write your summary, select products and click <em>Get coach feedback</em>.";
  $("#feedback").classList.add("muted");
  $("#btn-download").disabled = true;
  document.querySelectorAll("#product-checks input").forEach((i) => (i.checked = false));
  renderChat();
  showStep("interview");
  $("#chat-input").focus();
}

function bubble(role, text, extraClass = "") {
  const who = role === "user" ? "You" : state.client.name;
  const cls = role === "user" ? "student" : "client";
  return `<div class="msg ${cls} ${extraClass}"><span class="who">${escapeHtml(who)}</span>${escapeHtml(text)}</div>`;
}

function renderChat(extra = "") {
  const log = $("#chat-log");
  log.innerHTML = bubble("assistant", state.client.opening_line) +
    state.messages.map((m) => bubble(m.role, m.content)).join("") + extra;
  log.scrollTop = log.scrollHeight;
}

async function sendMessage(text) {
  state.messages.push({ role: "user", content: text });
  renderChat(`<div class="msg client typing">${escapeHtml(state.client.name)} is typing...</div>`);
  $("#btn-send").disabled = true;
  try {
    const { reply } = await api("/api/chat", { client_id: state.client.id, messages: state.messages });
    state.messages.push({ role: "assistant", content: reply });
    renderChat();
  } catch (e) {
    state.messages.pop();
    $("#chat-input").value = text;
    renderChat(`<div class="msg error">Error: ${escapeHtml(e.message)}</div>`);
  } finally {
    $("#btn-send").disabled = false;
    $("#chat-input").focus();
  }
}

function renderProducts() {
  $("#product-list").innerHTML = state.products.map((p) => `
    <details class="product">
      <summary>${escapeHtml(p.name)}
        <span class="tag ${p.sharia_compliant ? "islamic" : "conv"}">${p.sharia_compliant ? "Islamic" : "Conventional"}</span>
      </summary>
      <div class="muted small">${escapeHtml(p.category)}</div>
      <strong>Features</strong><ul>${p.features.map((f) => `<li>${escapeHtml(f)}</li>`).join("")}</ul>
      <strong>Limitations</strong><ul>${p.limitations.map((f) => `<li>${escapeHtml(f)}</li>`).join("")}</ul>
    </details>`).join("");
  $("#product-checks").innerHTML = state.products.map((p) => `
    <label><input type="checkbox" value="${escapeHtml(p.id)}"> ${escapeHtml(p.name)}
      <span class="tag ${p.sharia_compliant ? "islamic" : "conv"}">${p.sharia_compliant ? "Islamic" : "Conventional"}</span></label>`).join("");
}

function selectedProductIds() {
  return [...document.querySelectorAll("#product-checks input:checked")].map((i) => i.value);
}

async function getFeedback() {
  const btn = $("#btn-feedback");
  btn.disabled = true;
  $("#feedback").classList.add("muted");
  $("#feedback").textContent = "The coach is reviewing your interview...";
  try {
    const { feedback } = await api("/api/feedback", {
      client_id: state.client.id,
      messages: state.messages,
      summary: $("#summary").value,
      recommended_product_ids: selectedProductIds(),
    });
    state.feedback = feedback;
    $("#feedback").classList.remove("muted");
    $("#feedback").innerHTML = renderMarkdown(feedback);
    $("#btn-download").disabled = false;
  } catch (e) {
    $("#feedback").innerHTML = `<span style="color:var(--error)">Error: ${escapeHtml(e.message)}</span>`;
  } finally {
    btn.disabled = false;
  }
}

function downloadSession() {
  const names = Object.fromEntries(state.products.map((p) => [p.id, p.name]));
  const c = state.client;
  const turn = (who, text) =>
    `<div class="p-turn"><strong>${escapeHtml(who)}:</strong> ${escapeHtml(text)}</div>`;
  const convo = [turn(`${c.name} (AI Client)`, c.opening_line)]
    .concat(state.messages.map((m) =>
      turn(m.role === "user" ? "Student" : `${c.name} (AI Client)`, m.content)));
  const summary = $("#summary").value.trim();
  const recs = selectedProductIds().map((id) => `<li>${escapeHtml(names[id] || id)}</li>`).join("");

  $("#print-view").innerHTML = `
    <h1>Sample Interview - ${escapeHtml(c.name)}</h1>
    <h2 class="p-section">1. Conversation between the student and the AI Client</h2>
    ${convo.join("")}
    <h2 class="p-section">2. Student's summary and product recommendations</h2>
    <h3>Summary</h3>
    <p class="p-pre">${summary ? escapeHtml(summary) : "<em>(no summary)</em>"}</p>
    <h3>Recommended products</h3>
    ${recs ? `<ul>${recs}</ul>` : "<p><em>(none)</em></p>"}
    <h2 class="p-section">3. AI Coach feedback</h2>
    <div class="feedback">${renderMarkdown(state.feedback)}</div>`;

  const title = document.title;
  document.title = `interview-${c.id}`;
  window.print();
  document.title = title;
}

$("#chat-form").addEventListener("submit", (e) => {
  e.preventDefault();
  const text = $("#chat-input").value.trim();
  if (!text || $("#btn-send").disabled) return;
  $("#chat-input").value = "";
  sendMessage(text);
});
$("#chat-input").addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); $("#chat-form").requestSubmit(); }
});
$("#btn-end").addEventListener("click", () => {
  if (!state.messages.length) { alert("Ask the client at least one question first."); return; }
  showStep("feedback");
});
$("#btn-back").addEventListener("click", () => showStep("interview"));
$("#btn-feedback").addEventListener("click", getFeedback);
$("#btn-download").addEventListener("click", downloadSession);
$("#btn-restart").addEventListener("click", () => showStep("select"));

(async function init() {
  try {
    const [clients, products] = await Promise.all([api("/api/clients"), api("/api/products")]);
    state.clients = clients;
    state.products = products;
    renderClients();
    renderProducts();
  } catch (e) {
    $("#client-list").innerHTML = `<p style="color:var(--error)">Failed to load data: ${escapeHtml(e.message)}</p>`;
  }
})();
