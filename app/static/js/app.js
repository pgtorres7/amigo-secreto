(() => {
  let csrfToken = "";

  const views = {
    draw: document.getElementById("view-draw"),
    adminLogin: document.getElementById("view-admin-login"),
    admin: document.getElementById("view-admin"),
  };

  function showView(name) {
    Object.entries(views).forEach(([key, el]) => {
      el.classList.toggle("hidden", key !== name);
    });
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  function showMessage(id, text, type = "error") {
    const el = document.getElementById(id);
    if (!text) {
      el.className = "message";
      el.textContent = "";
      return;
    }
    el.textContent = text;
    el.className = `message visible ${type}`;
  }

  async function api(path, options = {}) {
    if (!csrfToken) {
      await refreshCsrf();
    }
    const response = await fetch(path, {
      ...options,
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": csrfToken,
        ...(options.headers || {}),
      },
      credentials: "same-origin",
    });

    let data = {};
    try {
      data = await response.json();
    } catch {
      data = {};
    }

    if (response.status === 400 && /csrf|referrer/i.test(JSON.stringify(data) + response.statusText)) {
      await refreshCsrf();
    }

    return { ok: response.ok, status: response.status, data };
  }

  async function refreshCsrf() {
    const response = await fetch("/api/csrf", { credentials: "same-origin" });
    const data = await response.json();
    csrfToken = data.csrf_token;
  }

  function updateStats(stats, prefix = "") {
    const map = {
      total: "stat-total",
      drawn_count: "stat-drawn",
      remaining_count: "stat-remaining",
    };
    if (prefix === "admin-") {
      map.total = "admin-stat-total";
      map.drawn_count = "admin-stat-drawn";
      map.remaining_count = "admin-stat-remaining";
    }
    Object.entries(map).forEach(([key, id]) => {
      const el = document.getElementById(id);
      if (el) el.textContent = stats[key] ?? 0;
    });
  }

  function fillParticipants(participants) {
    const select = document.getElementById("participant-name");
    const current = select.value;
    select.innerHTML = '<option value="">Selecione o seu nome</option>';
    participants
      .slice()
      .sort((a, b) => a.name.localeCompare(b.name, "pt-BR"))
      .forEach((person) => {
        const option = document.createElement("option");
        option.value = person.name;
        option.textContent = person.has_drawn ? `${person.name} (já sorteou)` : person.name;
        select.appendChild(option);
      });
    if ([...select.options].some((o) => o.value === current)) {
      select.value = current;
    }
    syncPassword();
  }

  function syncPassword() {
    const hasName = Boolean(document.getElementById("participant-name").value);
    document.getElementById("password-wrap").classList.toggle("hidden", !hasName);
    const input = document.getElementById("access-password");
    input.required = hasName;
    if (!hasName) input.value = "";
  }

  async function loadStatus() {
    const { ok, data } = await api("/api/status");
    if (!ok) return data;
    updateStats(data);
    fillParticipants(data.participants || []);
    return data;
  }

  function renderIssued(passwords) {
    const box = document.getElementById("issued-passwords");
    const list = document.getElementById("issued-list");
    if (!passwords || !passwords.length) {
      box.classList.add("hidden");
      list.innerHTML = "";
      return;
    }
    box.classList.remove("hidden");
    list.innerHTML = passwords
      .map(
        (item) =>
          `<li><div class="meta"><strong>${item.name}</strong><small>Senha: <strong>${item.password}</strong></small></div></li>`
      )
      .join("");
  }

  function renderAdminParticipants(participants) {
    const list = document.getElementById("participants-list");
    const summary = document.getElementById("list-summary");
    summary.textContent = participants.length
      ? `${participants.length} cadastrado(s). O organizador não vê quem tirou quem.`
      : "Nenhum nome cadastrado ainda.";

    list.innerHTML = "";
    participants.forEach((person) => {
      const li = document.createElement("li");
      li.innerHTML = `
        <div class="meta">
          <strong>${person.name}</strong>
          <small>${person.has_drawn ? "Já sorteou" : "Pendente"}${person.has_token ? "" : " · sem senha"}</small>
        </div>
        <div class="row-actions">
          <span class="badge ${person.has_drawn ? "done" : "pending"}">${person.has_drawn ? "Sorteou" : "Pendente"}</span>
          <button type="button" class="btn btn-secondary" data-action="password" data-id="${person.id}">Nova senha</button>
          <button type="button" class="btn btn-danger" data-action="remove" data-id="${person.id}">Remover</button>
        </div>
      `;
      list.appendChild(li);
    });
  }

  async function loadAdmin() {
    const { ok, data, status } = await api("/api/admin/participants");
    if (status === 401) {
      showView("adminLogin");
      return;
    }
    if (!ok) {
      showMessage("admin-message", data.error || "Falha ao carregar admin.");
      return;
    }
    updateStats(data.stats, "admin-");
    renderAdminParticipants(data.participants || []);
    showView("admin");
  }

  document.getElementById("go-admin").addEventListener("click", async () => {
    await refreshCsrf();
    const status = await loadStatus();
    if (status?.admin) {
      await loadAdmin();
    } else {
      showView("adminLogin");
    }
  });

  document.getElementById("back-draw-1").addEventListener("click", () => {
    showView("draw");
    loadStatus();
  });
  document.getElementById("back-draw-2").addEventListener("click", () => {
    showView("draw");
    loadStatus();
  });

  document.getElementById("participant-name").addEventListener("change", syncPassword);

  document.getElementById("draw-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    showMessage("draw-message", "");
    document.getElementById("draw-result").classList.remove("visible");

    const name = document.getElementById("participant-name").value.trim();
    const password = document.getElementById("access-password").value;
    if (!name) {
      showMessage("draw-message", "Selecione o seu nome.");
      return;
    }

    const btn = document.getElementById("draw-btn");
    btn.disabled = true;
    btn.textContent = "Aguarde...";

    try {
      const { ok, data } = await api("/api/sortear", {
        method: "POST",
        body: JSON.stringify({ name, password }),
      });
      if (!ok) {
        showMessage("draw-message", data.error || "Não foi possível sortear.");
        return;
      }
      document.getElementById("result-label").textContent = `${data.giver}, o seu amigo secreto é`;
      document.getElementById("result-name").textContent = data.receiver;
      document.getElementById("draw-result").classList.add("visible");
      showMessage("draw-message", data.message, "ok");
      await loadStatus();
    } finally {
      btn.disabled = false;
      btn.textContent = "Ver / Sortear";
    }
  });

  document.getElementById("admin-login-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    showMessage("login-message", "");
    const password = document.getElementById("admin-password").value;
    const { ok, data } = await api("/api/admin/login", {
      method: "POST",
      body: JSON.stringify({ password }),
    });
    if (!ok) {
      showMessage("login-message", data.error || "Senha inválida.");
      return;
    }
    document.getElementById("admin-password").value = "";
    await loadAdmin();
  });

  document.getElementById("admin-logout").addEventListener("click", async () => {
    await api("/api/admin/logout", { method: "POST", body: "{}" });
    showView("adminLogin");
  });

  document.getElementById("add-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    showMessage("admin-message", "");
    const names = document.getElementById("names-input").value;
    const { ok, data } = await api("/api/admin/participants", {
      method: "POST",
      body: JSON.stringify({ names }),
    });
    if (!ok) {
      showMessage("admin-message", data.error || "Falha ao cadastrar.");
      return;
    }
    document.getElementById("names-input").value = "";
    showMessage(
      "admin-message",
      `${data.added} adicionado(s)${data.skipped ? `, ${data.skipped} ignorado(s)` : ""}.`,
      "ok"
    );
    renderIssued(data.passwords || []);
    updateStats(data.stats, "admin-");
    renderAdminParticipants(data.participants || []);
    await loadStatus();
  });

  document.getElementById("participants-list").addEventListener("click", async (event) => {
    const btn = event.target.closest("button[data-action]");
    if (!btn) return;
    const id = btn.getAttribute("data-id");
    const action = btn.getAttribute("data-action");

    if (action === "password") {
      const { ok, data } = await api(`/api/admin/participants/${id}/password`, {
        method: "POST",
        body: "{}",
      });
      if (!ok) {
        showMessage("admin-message", data.error || "Falha ao gerar senha.");
        return;
      }
      renderIssued([data.password]);
      showMessage("admin-message", "Nova senha gerada. Copie e envie.", "ok");
      renderAdminParticipants(data.participants || []);
      updateStats(data.stats, "admin-");
      return;
    }

    if (action === "remove") {
      if (!confirm("Remover participante?")) return;
      const { ok, data } = await api(`/api/admin/participants/${id}`, { method: "DELETE" });
      if (!ok) {
        showMessage("admin-message", data.error || "Não foi possível remover.");
        return;
      }
      showMessage("admin-message", data.message || "Removido.", "ok");
      renderAdminParticipants(data.participants || []);
      updateStats(data.stats, "admin-");
      await loadStatus();
    }
  });

  document.getElementById("reset-draws-btn").addEventListener("click", async () => {
    if (!confirm("Reiniciar todos os sorteios?")) return;
    const { ok, data } = await api("/api/admin/reset-draws", { method: "POST", body: "{}" });
    if (!ok) {
      showMessage("admin-message", data.error || "Falha ao reiniciar.");
      return;
    }
    showMessage("admin-message", data.message, "ok");
    renderAdminParticipants(data.participants || []);
    updateStats(data.stats, "admin-");
    await loadStatus();
  });

  document.getElementById("clear-all-btn").addEventListener("click", async () => {
    if (!confirm("Apagar toda a lista e todos os sorteios?")) return;
    const { ok, data } = await api("/api/admin/clear-all", { method: "POST", body: "{}" });
    if (!ok) {
      showMessage("admin-message", data.error || "Falha ao limpar.");
      return;
    }
    showMessage("admin-message", data.message, "ok");
    renderIssued([]);
    renderAdminParticipants([]);
    updateStats(data.stats, "admin-");
    await loadStatus();
  });

  // Deep link simples
  async function boot() {
    await refreshCsrf();
    await loadStatus();
    if (location.pathname.startsWith("/admin")) {
      const status = await loadStatus();
      if (status?.admin) await loadAdmin();
      else showView("adminLogin");
    } else {
      showView("draw");
    }
  }

  boot().catch((error) => {
    console.error(error);
    showMessage("draw-message", "Não foi possível carregar o sistema.");
  });
})();
