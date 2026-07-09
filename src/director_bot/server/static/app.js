async function j(url, opts) {
  const r = await fetch(url, opts);
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

function $(id) { return document.getElementById(id); }

function setTab(name) {
  document.querySelectorAll("nav button").forEach((b) => {
    b.classList.toggle("active", b.dataset.tab === name);
  });
  document.querySelectorAll(".tab").forEach((t) => {
    t.classList.toggle("active", t.id === `tab-${name}`);
  });
}

document.querySelectorAll("nav button").forEach((b) => {
  b.addEventListener("click", () => setTab(b.dataset.tab));
});

async function loadHealth() {
  try {
    const h = await j("/api/health");
    $("health").textContent =
      `v${h.version} · brain=${h.provider} · embed=${h.embedder} · works=${h.works} · projects=${h.projects}`;
  } catch (e) {
    $("health").textContent = `health error: ${e.message}`;
  }
}

async function loadProjects() {
  const list = $("project-list");
  list.innerHTML = "";
  const projects = await j("/api/projects");
  if (!projects.length) {
    list.innerHTML = "<li class='muted'>No projects yet — run `director-bot demo`</li>";
    return;
  }
  projects.forEach((p) => {
    const li = document.createElement("li");
    li.textContent = `[${p.id}] ${p.title} · ${p.phase} · ${p.medium || "film"}`;
    li.addEventListener("click", () => showProject(p.id));
    list.appendChild(li);
  });
}

async function showProject(id) {
  const p = await j(`/api/projects/${id}`);
  $("project-title").textContent = p.title;
  $("project-meta").textContent =
    `id=${p.id} slug=${p.slug} phase=${p.phase} genre=${p.genre || "—"} · ${p.logline || ""}`;
  $("decide-project").value = id;

  const cards = $("cards");
  cards.innerHTML = "";
  (p.cards || []).forEach((c) => {
    const el = document.createElement("div");
    el.className = "card";
    el.innerHTML = `<h4>${c.slugline || c.title || "card"}</h4>
      <p>${(c.what_happens || "").slice(0, 160)}</p>`;
    cards.appendChild(el);
  });
  if (!(p.cards || []).length) {
    cards.innerHTML = "<p class='muted'>No cards on this board.</p>";
  }

  const chain = await j(`/api/projects/${id}/chain`);
  const ok = chain.verify && chain.verify.ok;
  $("chain-status").innerHTML = ok
    ? `<span class="ok">merkle chain ok</span> · length=${chain.verify.length}` +
      (chain.agreement && chain.agreement.agreement_rate != null
        ? ` · agreement=${(chain.agreement.agreement_rate * 100).toFixed(0)}%`
        : "")
    : `<span class="bad">chain broken</span>`;

  const ol = $("decisions");
  ol.innerHTML = "";
  (chain.decisions || []).forEach((d) => {
    const li = document.createElement("li");
    li.innerHTML = `<strong>${d.phase}</strong> · ${d.equilibrium_method}<br/>
      ${(d.chosen_action || "").slice(0, 200)}<br/>
      <span class="muted">#${(d.content_hash || "").slice(0, 14)}</span>`;
    ol.appendChild(li);
  });
}

async function loadWorks() {
  const works = await j("/api/works");
  const ul = $("works-list");
  ul.innerHTML = "";
  works.forEach((w) => {
    const li = document.createElement("li");
    li.textContent = `[${w.tier}] ${w.title} — ${(w.directors || []).join(", ")} · ${(w.genres || []).join(", ")}`;
    ul.appendChild(li);
  });
}

$("lookup-btn").addEventListener("click", async () => {
  const q = $("lookup-q").value.trim();
  if (!q) return;
  const kind = $("lookup-kind").value;
  const hits = await j(`/api/lookup?q=${encodeURIComponent(q)}&kind=${kind}`);
  const ul = $("lookup-results");
  ul.innerHTML = "";
  hits.forEach((h) => {
    const li = document.createElement("li");
    const score = (h.score != null ? Number(h.score).toFixed(2) : "?");
    const body = h.decision || h.action_text || h.what_happens || h.slugline || JSON.stringify(h).slice(0, 120);
    li.innerHTML = `<span class="score">${score}</span> ${body}`;
    ul.appendChild(li);
  });
  if (!hits.length) ul.innerHTML = "<li class='muted'>no hits</li>";
});

$("decide-btn").addEventListener("click", async () => {
  const body = {
    summary: $("decide-summary").value.trim(),
    genre: $("decide-genre").value.trim(),
    phase: $("decide-phase").value,
  };
  const pid = $("decide-project").value;
  if (pid) body.project_id = Number(pid);
  if (!body.summary) {
    $("decide-out").textContent = "situation required";
    return;
  }
  try {
    const res = await j("/api/decide", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    $("decide-out").textContent = JSON.stringify(res, null, 2);
    if (body.project_id) showProject(body.project_id);
    loadProjects();
  } catch (e) {
    $("decide-out").textContent = e.message;
  }
});

$("arc-load").addEventListener("click", async () => {
  const id = Number($("arc-series").value);
  if (!id) return;
  try {
    const rep = await j(`/api/series/${id}/arc`);
    $("arc-out").textContent = JSON.stringify(rep, null, 2);
  } catch (e) {
    $("arc-out").textContent = e.message;
  }
});

$("arc-plan").addEventListener("click", async () => {
  const id = Number($("arc-series").value);
  const ep = Number($("arc-ep").value) || 1;
  if (!id) return;
  try {
    const plan = await j(`/api/series/${id}/plan/${ep}`);
    $("arc-out").textContent = JSON.stringify(plan, null, 2);
  } catch (e) {
    $("arc-out").textContent = e.message;
  }
});

loadHealth();
loadProjects();
loadWorks();
