/* Director-bot dashboard — Model View first for training regimen. */

async function j(url, opts) {
  const r = await fetch(url, opts);
  if (!r.ok) {
    let msg = await r.text();
    try {
      const p = JSON.parse(msg);
      if (p.detail) msg = typeof p.detail === "string" ? p.detail : JSON.stringify(p.detail);
    } catch { /* plain */ }
    throw new Error(msg || r.statusText);
  }
  return r.json();
}

function $(id) { return document.getElementById(id); }

function esc(s) {
  return String(s ?? "")
    .replace(/&/g, "&amp;").replace(/</g, "&lt;")
    .replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}

function setTab(name) {
  document.querySelectorAll("#nav button").forEach((b) => {
    b.classList.toggle("active", b.dataset.tab === name);
  });
  document.querySelectorAll(".tab").forEach((t) => {
    t.classList.toggle("active", t.id === `tab-${name}`);
  });
}

document.querySelectorAll("#nav button").forEach((b) => {
  b.addEventListener("click", () => setTab(b.dataset.tab));
});

function statsHtml(stats) {
  if (!stats) return "";
  const items = [
    ["sys", stats.system_chars],
    ["user", stats.user_chars],
    ["total", stats.total_chars],
    ["~tok", stats.approx_tokens],
  ];
  return items
    .filter(([, v]) => v != null)
    .map(([k, v]) => `<div class="stat"><b>${esc(v)}</b><span>${esc(k)}</span></div>`)
    .join("");
}

function renderSections(view) {
  const el = $("mv-sections");
  if (!view) {
    el.innerHTML = "<span class='muted'>No view loaded.</span>";
    return;
  }
  const parts = [];

  if (view.sections) {
    const s = view.sections;
    if (s.process_name) {
      parts.push(`<div class="section-block"><h4>Process · ${esc(s.process_name)}</h4>
        <div class="body">${esc(s.process_blurb || "")}</div></div>`);
    }
    if (s.working_memory_text) {
      parts.push(`<div class="section-block"><h4>Working memory (as in prompt)</h4>
        <pre>${esc(s.working_memory_text)}</pre></div>`);
    }
    if (s.soul_core) {
      parts.push(`<div class="section-block"><h4>Soul core (excerpt)</h4>
        <pre>${esc((s.soul_core || "").slice(0, 600))}</pre></div>`);
    }
  }

  if (view.retrieval) {
    const r = view.retrieval;
    parts.push(`<div class="section-block"><h4>Retrieval query</h4>
      <pre>${esc(r.query || "")}</pre></div>`);
    (r.digests || []).slice(0, 6).forEach((d) => {
      const score = d.score != null ? Number(d.score).toFixed(3) : "?";
      parts.push(`<div class="hit"><span class="score">${score}</span>
        <strong>${esc(d.director || "digest")}</strong> · ${esc((d.decision || "").slice(0, 220))}</div>`);
    });
    (r.moments || []).slice(0, 4).forEach((m) => {
      const score = m.score != null ? Number(m.score).toFixed(3) : "?";
      const work = (m.work && m.work.title) || "";
      parts.push(`<div class="hit"><span class="score">${score}</span>
        moment · ${esc(work)} · ${esc((m.action_text || m.mood || "").slice(0, 180))}</div>`);
    });
  }

  if (view.candidates) {
    parts.push(`<div class="section-block"><h4>Candidates (${view.candidates.length})</h4></div>`);
    const chosenId = view.provisional_chosen?.id || view.chosen?.id;
    view.candidates.forEach((c) => {
      const chosen = c.id === chosenId ? " chosen" : "";
      const w = c.weighted != null ? ` · w=${Number(c.weighted).toFixed(3)}` : "";
      parts.push(`<div class="cand${chosen}"><div class="cid">${esc(c.id)}${w}</div>
        <div class="src">${esc(c.style_source || "")}</div>
        <div>${esc((c.action || "").slice(0, 280))}</div></div>`);
    });
  }

  if (view.score_prompt) {
    const sp = view.score_prompt;
    parts.push(`<div class="section-block"><h4>Score prompt · will_send=${esc(String(sp.will_send ?? sp.sent))}</h4>
      <div class="body">${esc(sp.note || "")}</div></div>`);
  }

  if (view.soul_note) {
    parts.push(`<div class="section-block"><h4>Note</h4><div class="body">${esc(view.soul_note || view.note || "")}</div></div>`);
  } else if (view.note) {
    parts.push(`<div class="section-block"><h4>Note</h4><div class="body">${esc(view.note)}</div></div>`);
  }

  el.innerHTML = parts.length ? parts.join("") : "<span class='muted'>No sections.</span>";
}

function paintModelView(view) {
  if (!view) return;
  $("mv-system").textContent = view.system || view.score_prompt?.system || "—";
  $("mv-user").textContent = view.user || view.score_prompt?.user || "—";

  if (view.response) {
    $("mv-response").textContent = view.response;
    $("resp-tag").textContent = "live response";
  } else if (view.score_prompt) {
    $("mv-response").textContent =
      JSON.stringify({
        provisional_chosen: view.provisional_chosen,
        provisional_equilibrium: view.provisional_equilibrium,
        creativity_alpha: view.creativity_alpha,
        brain: view.brain,
        would_call_llm: view.would_call_llm,
        score_stats: view.score_prompt.stats,
      }, null, 2);
    $("resp-tag").textContent = "dry-run decide payload";
  } else {
    $("mv-response").textContent = JSON.stringify({
      live: view.live,
      brain: view.brain,
      phase: view.phase,
      would_call_llm: view.would_call_llm,
      note: view.note,
    }, null, 2);
    $("resp-tag").textContent = "dry-run";
  }

  if (view.kind === "decide") {
    $("sys-tag").textContent = "score system";
    $("user-tag").textContent = "score user JSON";
    // Prefer score prompt in the system/user panes for decide mode
    if (view.score_prompt) {
      $("mv-system").textContent = view.score_prompt.system;
      $("mv-user").textContent = view.score_prompt.user;
    }
  } else {
    $("sys-tag").textContent = "soul preamble";
    $("user-tag").textContent = "assembled user";
  }

  const stats = view.stats || view.score_prompt?.stats;
  $("mv-stats").innerHTML = statsHtml(stats) +
    (view.brain ? `<div class="stat"><b>${esc(view.brain)}</b><span>brain</span></div>` : "") +
    (view.phase ? `<div class="stat"><b>${esc(view.phase)}</b><span>phase</span></div>` : "");

  renderSections(view);
}

function traceQueryParams() {
  const params = new URLSearchParams({ n: "50" });
  const q = $("trace-q")?.value?.trim();
  const kind = $("trace-kind")?.value;
  const since = $("trace-since")?.value?.trim();
  if (q) params.set("q", q);
  if (kind) params.set("kind", kind);
  if (since) params.set("since", since);
  return params;
}

async function loadTraces() {
  try {
    const data = await j(`/api/brain/traces?${traceQueryParams()}`);
    $("trace-count").textContent =
      `${data.count || 0}${data.source === "sqlite" ? " · db" : " · mem"}`;
    const ul = $("mv-traces");
    ul.innerHTML = "";
    if (!(data.traces || []).length) {
      ul.innerHTML = "<li class='muted' style='cursor:default'>No matching traces. Stream meet or clear filters.</li>";
      return;
    }
    data.traces.forEach((t) => {
      const li = document.createElement("li");
      const persisted = t.persisted ? " · saved" : "";
      li.innerHTML = `
        <div class="t-kind">${esc(t.kind)} · ${esc(t.brain)}${t.meta?.streamed ? " · stream" : ""}</div>
        <div class="t-meta">${esc(t.ts)} · ${esc(t.id)}${t.project_id != null ? " · p" + t.project_id : ""}
          · ${esc(t.stats?.approx_tokens || "?")} tok${persisted}</div>
        <div class="t-snip">${esc((t.user || "").slice(0, 160))}</div>`;
      li.addEventListener("click", () => {
        paintModelView({
          kind: t.kind,
          live: true,
          brain: t.brain,
          system: t.system,
          user: t.user,
          response: t.response,
          stats: t.stats,
          project_id: t.project_id,
          note: t.persisted
            ? "Loaded from SQLite brain_traces (durable)."
            : "Loaded from process-local ring.",
        });
        $("resp-tag").textContent = t.persisted ? "persisted trace" : "session trace";
      });
      ul.appendChild(li);
    });
  } catch (e) {
    $("mv-traces").innerHTML = `<li class="muted">${esc(e.message)}</li>`;
  }
}

async function previewModelView() {
  const mode = $("mv-mode").value;
  const topic = $("mv-topic").value.trim();
  if (!topic) {
    $("mv-response").textContent = "Enter a situation / message first.";
    return;
  }
  const project_id = $("mv-project").value ? Number($("mv-project").value) : null;
  const phase = $("mv-phase").value;
  try {
    let view;
    if (mode === "meet") {
      view = await j("/api/model-view/meet", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ topic, project_id, phase }),
      });
    } else {
      view = await j("/api/model-view/decide", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          summary: topic,
          project_id,
          phase,
          genre: "",
        }),
      });
    }
    paintModelView(view);
  } catch (e) {
    $("mv-response").textContent = e.message;
  }
}

function setStreamStatus(text, isError) {
  const el = $("stream-status");
  if (!text) {
    el.hidden = true;
    el.textContent = "";
    el.classList.remove("error");
    return;
  }
  el.hidden = false;
  el.textContent = text;
  el.classList.toggle("error", !!isError);
}

/** Parse SSE chunks from a fetch ReadableStream (POST body support). */
async function consumeSSE(response, handlers) {
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buf = "";
  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buf += decoder.decode(value, { stream: true });
    let sep;
    while ((sep = buf.indexOf("\n\n")) >= 0) {
      const raw = buf.slice(0, sep);
      buf = buf.slice(sep + 2);
      let event = "message";
      let data = "";
      raw.split("\n").forEach((line) => {
        if (line.startsWith("event:")) event = line.slice(6).trim();
        else if (line.startsWith("data:")) data += line.slice(5).trim();
      });
      if (!data) continue;
      let parsed;
      try { parsed = JSON.parse(data); } catch { parsed = data; }
      if (handlers[event]) handlers[event](parsed);
      if (handlers.any) handlers.any(event, parsed);
    }
  }
}

async function liveMeetStream() {
  const topic = $("mv-topic").value.trim();
  if (!topic) return;
  const project_id = $("mv-project").value ? Number($("mv-project").value) : null;
  const btn = $("mv-live");
  btn.disabled = true;
  $("mv-response").textContent = "";
  $("mv-response").classList.add("streaming");
  $("resp-tag").textContent = "streaming…";
  setStreamStatus("connecting…");

  let responseText = "";
  let tokens = 0;
  try {
    const res = await fetch("/api/soul/meet/stream", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Accept: "text/event-stream",
      },
      body: JSON.stringify({ message: topic, project_id }),
    });
    if (!res.ok) {
      throw new Error(await res.text() || res.statusText);
    }
    await consumeSSE(res, {
      meta: (view) => {
        paintModelView({ ...view, response: "" });
        $("mv-response").textContent = "";
        $("mv-response").classList.add("streaming");
        $("resp-tag").textContent = "streaming…";
        setStreamStatus(`meta · brain=${view.brain || "?"} · phase=${view.phase || "?"}`);
      },
      token: (d) => {
        responseText += d.t || "";
        tokens += 1;
        $("mv-response").textContent = responseText;
        setStreamStatus(`streaming · chunks=${tokens} · chars=${responseText.length}`);
      },
      done: (view) => {
        paintModelView(view);
        $("mv-response").classList.remove("streaming");
        $("resp-tag").textContent = "stream complete";
        setStreamStatus(
          `done · chunks=${tokens} · chars=${(view.response || "").length} · saved to brain_traces`,
        );
      },
      error: (err) => {
        $("mv-response").classList.remove("streaming");
        $("resp-tag").textContent = "stream error";
        const partial = err.partial || responseText;
        if (partial) $("mv-response").textContent = partial + "\n\n[error] " + (err.message || "");
        else $("mv-response").textContent = err.message || "stream error";
        setStreamStatus(err.message || "error", true);
      },
    });
    await loadTraces();
    if (project_id) {
      await showProject(project_id);
      await loadProjects();
    }
  } catch (e) {
    $("mv-response").classList.remove("streaming");
    $("mv-response").textContent = e.message;
    $("resp-tag").textContent = "error";
    setStreamStatus(e.message, true);
  } finally {
    btn.disabled = false;
  }
}

async function liveMeetSync() {
  const topic = $("mv-topic").value.trim();
  if (!topic) return;
  const project_id = $("mv-project").value ? Number($("mv-project").value) : null;
  try {
    setStreamStatus("meet (blocking)…");
    const view = await j("/api/soul/meet", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: topic, project_id }),
    });
    paintModelView(view);
    $("resp-tag").textContent = "live response";
    setStreamStatus("saved to brain_traces");
    await loadTraces();
    if (project_id) {
      await showProject(project_id);
      await loadProjects();
    }
  } catch (e) {
    $("mv-response").textContent = e.message;
    setStreamStatus(e.message, true);
  }
}

$("mv-preview").addEventListener("click", previewModelView);
$("mv-live").addEventListener("click", liveMeetStream);
$("mv-live-sync").addEventListener("click", liveMeetSync);
$("mv-refresh-traces").addEventListener("click", loadTraces);
$("trace-search")?.addEventListener("click", loadTraces);
$("trace-q")?.addEventListener("keydown", (e) => {
  if (e.key === "Enter") loadTraces();
});
$("mv-topic").addEventListener("keydown", (e) => {
  if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) liveMeetStream();
  else if (e.key === "Enter") previewModelView();
});

// ---- board card editor ----
$("card-add")?.addEventListener("click", () => {
  if (!activeProjectId) {
    alert("Select a project first");
    return;
  }
  openCardEditor({ title: "New beat", what_happens: "" });
});
$("card-cancel")?.addEventListener("click", hideCardEditor);
$("card-save")?.addEventListener("click", async () => {
  if (!activeProjectId) return;
  const id = $("card-edit-id").value;
  const body = {
    slugline: $("card-slugline").value.trim(),
    title: $("card-title").value.trim(),
    what_happens: $("card-what").value.trim(),
    structural_beat: $("card-beat").value.trim(),
    emotional_spine: $("card-spine").value.trim(),
    tags: $("card-tags").value.split(",").map((s) => s.trim()).filter(Boolean),
  };
  const act = $("card-act").value;
  if (act !== "") body.act = Number(act);
  try {
    if (id) {
      await j(`/api/cards/${id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
    } else {
      await j(`/api/projects/${activeProjectId}/cards`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
    }
    hideCardEditor();
    await showProject(activeProjectId);
  } catch (e) {
    alert(e.message);
  }
});
$("card-delete")?.addEventListener("click", async () => {
  const id = $("card-edit-id").value;
  if (!id || !activeProjectId) return;
  if (!confirm(`Delete card #${id}?`)) return;
  try {
    await j(`/api/cards/${id}`, { method: "DELETE" });
    hideCardEditor();
    await showProject(activeProjectId);
  } catch (e) {
    alert(e.message);
  }
});

// ---- health / projects ----
async function loadHealth() {
  try {
    const h = await j("/api/health");
    $("health").textContent =
      `v${h.version} · ${h.works} works · ${h.projects} projects` +
      (h.brain_traces != null ? ` · ${h.brain_traces} traces` : "");
    $("provider-pill").textContent = `brain · ${h.provider} · embed · ${h.embedder}`;
    $("path-pill").textContent = h.db || h.home || "—";
  } catch (e) {
    $("health").textContent = `health error: ${e.message}`;
  }
}

async function loadProjects() {
  const list = $("project-list");
  const sel = $("mv-project");
  const prev = sel.value;
  list.innerHTML = "";
  sel.innerHTML = `<option value="">— none —</option>`;
  const projects = await j("/api/projects");
  if (!projects.length) {
    list.innerHTML = "<li class='muted' style='cursor:default'>No projects — run <code>director-bot demo</code></li>";
    return;
  }
  projects.forEach((p) => {
    const li = document.createElement("li");
    li.textContent = `[${p.id}] ${p.title} · ${p.phase}`;
    li.addEventListener("click", () => {
      list.querySelectorAll("li").forEach((x) => x.classList.remove("active"));
      li.classList.add("active");
      showProject(p.id);
      $("decide-project").value = p.id;
      $("mv-project").value = String(p.id);
    });
    list.appendChild(li);
    const opt = document.createElement("option");
    opt.value = String(p.id);
    opt.textContent = `[${p.id}] ${p.title}`;
    sel.appendChild(opt);
  });
  if (prev) sel.value = prev;
}

let activeProjectId = null;

function hideCardEditor() {
  const ed = $("card-editor");
  if (ed) ed.hidden = true;
  $("card-edit-id").value = "";
}

function openCardEditor(card) {
  $("card-editor").hidden = false;
  $("card-editor-title").textContent = card?.id ? `Edit card #${card.id}` : "New card";
  $("card-edit-id").value = card?.id || "";
  $("card-slugline").value = card?.slugline || "";
  $("card-title").value = card?.title || "";
  $("card-what").value = card?.what_happens || "";
  $("card-beat").value = card?.structural_beat || "";
  $("card-act").value = card?.act != null ? card.act : "";
  $("card-spine").value = card?.emotional_spine || "";
  $("card-tags").value = Array.isArray(card?.tags) ? card.tags.join(", ") : "";
}

function renderCards(cards, projectId) {
  const root = $("cards");
  root.innerHTML = "";
  if (!(cards || []).length) {
    root.innerHTML = "<p class='muted' style='padding:0 0.85rem 0.85rem'>No cards — click + Card to add one.</p>";
    return;
  }
  cards.forEach((c) => {
    const el = document.createElement("div");
    el.className = "card";
    el.innerHTML = `<h4>${esc(c.slugline || c.title || "card")}</h4>
      <p>${esc((c.what_happens || "").slice(0, 160))}</p>
      <p class="muted" style="margin-top:0.35rem">#${esc(c.id)} · ${esc(c.structural_beat || "—")}</p>`;
    el.addEventListener("click", () => {
      root.querySelectorAll(".card").forEach((x) => x.classList.remove("active"));
      el.classList.add("active");
      openCardEditor(c);
    });
    root.appendChild(el);
  });
}

async function showProject(id) {
  activeProjectId = id;
  const p = await j(`/api/projects/${id}`);
  $("project-title").textContent = p.title;
  $("project-meta").textContent =
    `id=${p.id} · slug=${p.slug} · phase=${p.phase} · genre=${p.genre || "—"} · ${p.logline || ""}`;
  $("decide-project").value = id;
  $("wm-text").textContent = p.working_memory_text || "(empty)";
  hideCardEditor();
  renderCards(p.cards || [], id);

  const chain = await j(`/api/projects/${id}/chain`);
  const ok = chain.verify && chain.verify.ok;
  $("chain-status").innerHTML = ok
    ? `chain ok · n=${chain.verify.length}` +
      (chain.agreement && chain.agreement.agreement_rate != null
        ? ` · agr=${(chain.agreement.agreement_rate * 100).toFixed(0)}%`
        : "")
    : `chain broken`;
  $("chain-status").className = "tag " + (ok ? "ok" : "bad");

  const ol = $("decisions");
  ol.innerHTML = "";
  (chain.decisions || []).forEach((d) => {
    const li = document.createElement("li");
    li.innerHTML = `<strong>${esc(d.phase)}</strong> · ${esc(d.equilibrium_method)}<br/>
      ${esc((d.chosen_action || "").slice(0, 200))}<br/>
      <span class="muted">#${esc((d.content_hash || "").slice(0, 14))} · id=${esc(d.id)}</span>`;
    li.style.cursor = "pointer";
    li.addEventListener("click", async () => {
      try {
        const box = await j(`/api/decisions/${d.id}`);
        setTab("decide");
        $("decide-out").textContent = JSON.stringify(box, null, 2);
        $("decide-glass").innerHTML = renderDecideGlass({
          chosen_id: d.chosen_id,
          chosen_action: d.chosen_action,
          candidates: d.candidates || [],
          equilibrium: d.scores,
          situation: d.situation,
          model_view: null,
          brain: (d.scores && d.scores.brain) || "—",
        });
      } catch (e) {
        $("decide-out").textContent = e.message;
      }
    });
    ol.appendChild(li);
  });
}

async function loadWorks() {
  const works = await j("/api/works");
  const ul = $("works-list");
  ul.innerHTML = "";
  works.forEach((w) => {
    const li = document.createElement("li");
    li.style.cursor = "default";
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
    li.style.cursor = "default";
    const score = h.score != null ? Number(h.score).toFixed(2) : "?";
    const body = h.decision || h.action_text || h.what_happens || h.slugline || JSON.stringify(h).slice(0, 120);
    li.innerHTML = `<span class="score">${score}</span> ${esc(body)}`;
    ul.appendChild(li);
  });
  if (!hits.length) ul.innerHTML = "<li class='muted' style='cursor:default'>no hits</li>";
});

function renderDecideGlass(res) {
  const parts = [];
  parts.push(`<div class="section-block"><h4>Chosen · ${esc(res.chosen_id || "")}</h4>
    <div class="body">${esc(res.chosen_action || "")}</div>
    <div class="body muted">brain=${esc(res.brain)} · scored=${esc(String(res.brain_scored))}
    · α=${esc(res.creativity_alpha)}</div></div>`);
  if (res.situation) {
    parts.push(`<div class="section-block"><h4>Situation blob</h4><pre class="body">${esc(res.situation)}</pre></div>`);
  }
  (res.candidates || []).forEach((c) => {
    const chosen = c.id === res.chosen_id ? " chosen" : "";
    parts.push(`<div class="cand${chosen}"><div class="cid">${esc(c.id)}</div>
      <div class="src">${esc(c.style_source || "")}</div>
      <div>${esc((c.action || "").slice(0, 240))}</div>
      <div class="src">${esc(JSON.stringify(c.scores || {}))}</div></div>`);
  });
  if (res.model_view && res.model_view.score_prompt) {
    const sp = res.model_view.score_prompt;
    parts.push(`<div class="section-block"><h4>Score prompt sent=${esc(String(sp.sent))}</h4>
      <pre class="body">${esc((sp.system || "").slice(0, 200))}…\n\n${esc((sp.user || "").slice(0, 500))}…</pre></div>`);
  }
  if (res.equilibrium) {
    parts.push(`<div class="section-block"><h4>Equilibrium</h4>
      <pre class="body">${esc(JSON.stringify(res.equilibrium, null, 2))}</pre></div>`);
  }
  return parts.join("");
}

async function runDecide(commit) {
  const body = {
    summary: $("decide-summary").value.trim(),
    genre: $("decide-genre").value.trim(),
    phase: $("decide-phase").value,
    commit,
  };
  const pid = $("decide-project").value;
  if (pid) body.project_id = Number(pid);
  const style = $("decide-style").value.trim();
  if (style) body.style_refs = style.split(",").map((s) => s.trim()).filter(Boolean);
  if (!body.summary) {
    $("decide-out").textContent = "situation required";
    return;
  }
  try {
    if (!commit) {
      const view = await j("/api/model-view/decide", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          summary: body.summary,
          genre: body.genre,
          phase: body.phase,
          project_id: body.project_id,
          style_refs: body.style_refs || [],
        }),
      });
      $("decide-out").textContent = JSON.stringify(view, null, 2);
      $("decide-glass").innerHTML = renderDecideGlass({
        chosen_id: view.provisional_chosen?.id,
        chosen_action: view.provisional_chosen?.action,
        candidates: view.candidates,
        equilibrium: view.provisional_equilibrium,
        situation: view.situation_blob,
        model_view: { score_prompt: view.score_prompt },
        brain: view.brain,
        brain_scored: false,
        creativity_alpha: view.creativity_alpha,
      });
      paintModelView(view);
      return;
    }
    const res = await j("/api/decide", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    $("decide-out").textContent = JSON.stringify(res, null, 2);
    $("decide-glass").innerHTML = renderDecideGlass(res);
    if (res.model_view) paintModelView(res.model_view);
    if (body.project_id) showProject(body.project_id);
    loadProjects();
    loadTraces();
  } catch (e) {
    $("decide-out").textContent = e.message;
  }
}

$("decide-btn").addEventListener("click", () => runDecide(true));
$("decide-preview").addEventListener("click", () => runDecide(false));

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
    if (plan.model_view) {
      paintModelView({
        kind: "arc",
        live: plan.model_view.would_call_llm,
        brain: plan.model_view.brain,
        system: plan.model_view.system,
        user: plan.model_view.user,
        response: plan.brain_notes,
        note: "Arc plan model_view",
      });
    }
    loadTraces();
  } catch (e) {
    $("arc-out").textContent = e.message;
  }
});

async function loadSoul() {
  try {
    const s = await j("/api/soul");
    $("soul-core").textContent = s.core || "—";
    $("soul-taste").textContent = s.taste || "—";
    $("soul-process").textContent = s.process_notes || "—";
    $("soul-preamble").textContent = s.system_preamble || "—";
    $("soul-stats").textContent =
      `${s.stats?.preamble_chars || 0} chars · ~${s.stats?.approx_tokens || 0} tok`;
  } catch (e) {
    $("soul-preamble").textContent = e.message;
  }
}

// boot
loadHealth();
loadProjects();
loadWorks();
loadSoul();
loadTraces();
