// Smart College Event Planning Assistant — Frontend
"use strict";

// ── DOM refs ──────────────────────────────────────────
const $  = id => document.getElementById(id);
const addForm    = $("add-form");
const eventList  = $("event-list");
const eventCount = $("event-count");
const notice     = $("notice");
const resultPanel= $("result-panel");
const resultTitle= $("result-title");
const resultBody = $("result-body");
const bufferSel  = $("buffer-select");
const editModal  = $("edit-modal");
const editForm   = $("edit-form");
const editWarn   = $("edit-warn");

// ── Utilities ─────────────────────────────────────────
function esc(v) {
  const d = document.createElement("div");
  d.textContent = String(v ?? "");
  return d.innerHTML;
}

async function api(url, opts = {}) {
  const r = await fetch(url, opts);
  const text = await r.text();
  let data;
  try { data = text ? JSON.parse(text) : {}; } catch { throw new Error("Invalid server response."); }
  if (!r.ok) throw new Error(data.message || "Request failed.");
  return data;
}

function setNotice(msg, type = "") {
  notice.textContent = msg;
  notice.className = `notice${type ? " " + type : ""}`;
}

function showResult(title, html) {
  resultTitle.textContent = title;
  resultBody.innerHTML = html;
  resultPanel.classList.remove("hidden");
  resultPanel.scrollIntoView({ behavior: "smooth", block: "start" });
}

function closeResult() { resultPanel.classList.add("hidden"); }

function run(fn) { fn().catch(err => setNotice(err.message, "err")); }

$("btn-close-result").onclick = closeResult;

// ── Event table row ───────────────────────────────────
function makeRow(ev) {
  const hasTime = !!ev.start_time;
  const timeCell = hasTime
    ? `<strong>${esc(ev.start_time)}</strong> – <strong>${esc(ev.end_time)}</strong>`
    : `<span style="color:#9ca3af">—</span>`;
  const statusPill = ev.status === "Scheduled"
    ? `<span class="pill pill-green">Scheduled</span>`
    : `<span class="pill pill-amber">Unassigned</span>`;

  return `<tr>
    <td><span class="id-code">${esc(ev.event_id)}</span></td>
    <td><strong>${esc(ev.event_name)}</strong></td>
    <td style="color:#6b7280">${esc(ev.date)}</td>
    <td>${timeCell}</td>
    <td>${esc(ev.venue)}</td>
    <td style="color:#9ca3af;font-size:.8rem">${esc(ev.preferred_window || "—")}</td>
    <td style="font-size:.8rem;color:#6b7280">${esc((ev.participants||[]).join(", ")) || "—"}</td>
    <td>${statusPill}</td>
    <td>
      <div class="row-actions">
        <button class="act-btn suggest" data-id="${esc(ev.event_id)}">Suggest</button>
        <button class="act-btn edit"    data-id="${esc(ev.event_id)}">Edit</button>
        <button class="act-btn del"     data-id="${esc(ev.event_id)}">Delete</button>
      </div>
    </td>
  </tr>`;
}

// ── Load events ───────────────────────────────────────
async function loadEvents() {
  const data = await api("/api/events");
  const evs  = data.events || [];
  eventCount.textContent = `${evs.length} event${evs.length === 1 ? "" : "s"}`;
  eventList.innerHTML = evs.length
    ? evs.map(makeRow).join("")
    : `<tr><td class="empty-cell" colspan="9">No events yet. Load sample events or add one above.</td></tr>`;

  // Header stats
  const sched = evs.filter(e => e.status === "Scheduled").length;
  const hTotal = $("hstat-total"); if (hTotal) hTotal.textContent = evs.length;
  const hSched = $("hstat-sched"); if (hSched) hSched.textContent = sched;
  const hUnsched=$("hstat-unsched"); if (hUnsched) hUnsched.textContent = evs.length - sched;
}

async function loadBuffer() {
  try {
    const d = await api("/api/buffer");
    if (d.venue_buffer) bufferSel.value = String(d.venue_buffer);
  } catch {}
}

// ── Add event form ────────────────────────────────────
const addClashAlert = $("add-clash-alert");

addForm.addEventListener("submit", e => {
  e.preventDefault();
  // Hide any previous clash alert
  if (addClashAlert) { addClashAlert.classList.add("hidden"); addClashAlert.textContent = ""; }
  run(async () => {
    const body = Object.fromEntries(new FormData(addForm));
    // Strip empty optional fields so backend doesn't process blanks
    ["start_time","end_time","participants"].forEach(k => { if (!body[k]) delete body[k]; });
    const d = await api("/api/events", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    addForm.reset();
    const di = addForm.querySelector('[name="date"]');
    if (di) di.value = "2026-12-05";

    // Show clash/venue warnings prominently inside the form
    if (d.warnings && d.warnings.length) {
      addClashAlert.classList.remove("hidden");
      addClashAlert.classList.add("warn-only");
      addClashAlert.innerHTML = `<strong>⚠ Conflict warnings for ${esc(d.event_id)}:</strong>
        <ul style="margin:6px 0 0;padding-left:16px">${d.warnings.map(w => `<li>${esc(w)}</li>`).join("")}</ul>`;
      setNotice(`${d.message} — ${d.warnings.length} conflict warning(s) detected.`, "warn");
    } else {
      setNotice(`${d.message}${d.event_id ? " (ID: " + d.event_id + ")" : ""}`, "ok");
    }
    await loadEvents();
  });
});

// ── Load samples ──────────────────────────────────────
$("btn-samples").onclick = () => run(async () => {
  if (!confirm("Load sample events? This resets the current list.")) return;
  const d = await api("/api/samples", { method: "POST" });
  closeResult();
  setNotice(d.message, "ok");
  await loadEvents();
});

// ── Create schedule ───────────────────────────────────
$("btn-schedule").onclick = () => run(async () => {
  const d    = await api("/api/schedule", { method: "POST" });
  const newN = (d.assignments || []).length;
  const kept = d.scheduled - newN;

  setNotice(
    `Schedule created: ${d.scheduled} event(s) assigned (${newN} new, ${kept} preserved).`,
    d.unassigned > 0 ? "warn" : "ok"
  );

  // Always fetch and show full current schedule
  const all = (await api("/api/events")).events || [];
  const scheduled = all.filter(e => e.status === "Scheduled");
  const newIds = new Set((d.assignments || []).map(a => a.event_id));

  let html = `
    <div style="display:flex;gap:8px;margin-bottom:16px;flex-wrap:wrap">
      <span class="pill pill-green">${d.scheduled} Scheduled</span>
      <span class="pill pill-blue">${newN} Newly assigned</span>
      ${kept ? `<span class="pill pill-grey">${kept} Preserved</span>` : ""}
      ${d.unassigned > 0 ? `<span class="pill pill-amber">${d.unassigned} Unassigned</span>` : ""}
    </div>`;

  if (scheduled.length) {
    html += `<p class="section-label">All Scheduled Events</p>
      <div class="tbl-wrap"><table>
        <thead><tr><th>ID</th><th>Event Name</th><th>Time</th><th>Venue</th><th>How</th></tr></thead>
        <tbody>
          ${scheduled.map(e => `<tr>
            <td><span class="id-code">${esc(e.event_id)}</span></td>
            <td><strong>${esc(e.event_name)}</strong></td>
            <td>${esc(e.start_time)} – ${esc(e.end_time)}</td>
            <td>${esc(e.venue)}</td>
            <td>${newIds.has(e.event_id)
              ? `<span class="pill pill-blue">Auto-assigned</span>`
              : `<span class="pill pill-grey">Preserved</span>`}</td>
          </tr>`).join("")}
        </tbody>
      </table></div>`;
  }

  if (d.unassigned_explanations && Object.keys(d.unassigned_explanations).length) {
    html += `<p class="section-label" style="margin-top:16px">Could Not Schedule</p>
      <div class="alert alert-amber">
        <ul>${Object.entries(d.unassigned_explanations).map(([id, info]) =>
          `<li><strong>${esc(info.event_name)} (${esc(id)}):</strong> ${esc(info.reason)}</li>`
        ).join("")}</ul>
      </div>`;
  }

  // After scheduling, run a quick validation to surface any clashes
  const valData = await api("/api/validation");
  const pClashes = valData.details?.participant_clashes || [];
  const vOverlaps = valData.details?.venue_overlaps || [];

  if (pClashes.length || vOverlaps.length) {
    html += `<div class="alert alert-red" style="margin-top:14px">
      <h3>⚠ Conflict Alerts</h3>`;
    pClashes.forEach(c => { html += `<p style="margin:4px 0">👥 ${esc(c)}</p>`; });
    vOverlaps.forEach(v => { html += `<p style="margin:4px 0">🏛 ${esc(v)}</p>`; });
    html += `</div>`;
  }

  showResult("Schedule Result — Greedy Graph Coloring", html);
  await loadEvents();
});

// ── Show conflicts ────────────────────────────────────
$("btn-conflicts").onclick = () => run(async () => {
  const d      = await api("/api/conflicts");
  const clashes = d.simultaneous_clashes || [];
  const edges   = d.potential_conflicts  || [];
  let html = "";

  html += clashes.length
    ? `<div class="alert alert-red">
         <h3>Simultaneous Participant Clashes (${clashes.length})</h3>
         <p>These events overlap in time and share participants:</p>
         ${clashes.map(c => `
           <div class="edge-card clash" style="margin-top:8px">
             <div style="flex:1"><strong>${esc(c.first_event)}</strong>
               <span style="color:#9ca3af;font-size:.8rem;margin-left:6px">${esc(c.first_time)}</span></div>
             <span class="edge-mid">↔</span>
             <div style="flex:1"><strong>${esc(c.second_event)}</strong>
               <span style="color:#9ca3af;font-size:.8rem;margin-left:6px">${esc(c.second_time)}</span></div>
             <span class="pill pill-grey" style="font-size:.75rem">Shared: ${esc(c.shared_participants.join(", "))}</span>
           </div>`).join("")}
       </div>`
    : `<div class="alert alert-green"><h3>No Participant Clashes</h3><p>No scheduled events with shared participants overlap in time.</p></div>`;

  if (edges.length) {
    html += `<p class="section-label" style="margin-top:14px">Conflict Graph Edges — ${edges.length} connection${edges.length !== 1 ? "s" : ""}</p>
      <p style="font-size:.85rem;color:#6b7280;margin-bottom:8px">Events connected by an edge share students and must receive different time slots (graph coloring constraint).</p>`;
    edges.forEach(p => {
      html += `<div class="edge-card ${p.is_simultaneous_clash ? "clash" : "safe"}">
        <div style="flex:1"><strong>${esc(p.first_event)}</strong>
          <span style="color:#9ca3af;font-size:.78rem;margin-left:5px">${esc(p.first_time)}</span></div>
        <span class="edge-mid">— ∩ —</span>
        <div style="flex:1"><strong>${esc(p.second_event)}</strong>
          <span style="color:#9ca3af;font-size:.78rem;margin-left:5px">${esc(p.second_time)}</span></div>
        <span class="pill pill-grey" style="font-size:.75rem">${esc(p.shared_participants.join(", "))}</span>
        ${p.is_simultaneous_clash
          ? `<span class="pill" style="background:var(--red-bg);color:var(--red);border:1px solid var(--red-border);font-size:.72rem">Clashing</span>`
          : `<span class="pill pill-green" style="font-size:.72rem">Safe</span>`}
      </div>`;
    });
  } else {
    html += `<p style="color:#9ca3af;font-size:.875rem;margin-top:12px">No shared participants found across any events on the same date.</p>`;
  }

  showResult("Conflict Detection", html);
});

// ── Priority ranking ──────────────────────────────────
$("btn-priority").onclick = () => run(async () => {
  const d = await api("/api/priority");
  const r = d.ranking || [];
  if (!r.length) { showResult("Priority Ranking", "<p>No events to rank.</p>"); return; }

  const maxDeg = Math.max(...r.map(x => x.conflict_degree), 1);

  let html = `<p style="font-size:.875rem;color:#6b7280;margin-bottom:14px">
    Events ranked by <strong>conflict degree</strong> — higher degree means fewer available slots.
    Processed first during greedy graph coloring. This measures scheduling difficulty, not importance.
  </p>
  <div class="tbl-wrap"><table>
    <thead><tr><th>Rank</th><th>Event</th><th>Degree</th><th>Participants</th><th>Conflicts With</th><th>Status</th></tr></thead>
    <tbody>
      ${r.map(item => {
        const barW = Math.round((item.conflict_degree / maxDeg) * 60);
        return `<tr>
          <td><span class="rank-circle">${item.rank}</span></td>
          <td>
            <div><strong>${esc(item.event_name)}</strong></div>
            <span class="id-code" style="font-size:.75rem">${esc(item.event_id)}</span>
          </td>
          <td>
            <div class="deg-row">
              <span class="pill ${item.conflict_degree >= 2 ? "pill-amber" : item.conflict_degree >= 1 ? "pill-blue" : "pill-green"}" style="font-size:.78rem">${item.conflict_degree} edge${item.conflict_degree !== 1 ? "s" : ""}</span>
              ${item.conflict_degree > 0 ? `<div class="deg-bar" style="width:${barW}px"></div>` : ""}
            </div>
          </td>
          <td>${item.participant_count}</td>
          <td style="font-size:.85rem;color:#6b7280">${esc(item.conflicts_with_names.join(", ") || "—")}</td>
          <td>${item.status === "Scheduled"
            ? `<span class="pill pill-green">Scheduled</span>`
            : `<span class="pill pill-amber">Unassigned</span>`}</td>
        </tr>`;
      }).join("")}
    </tbody>
  </table></div>`;

  showResult("Priority Ranking", html);
});

// ── Check schedule (validation) ───────────────────────
$("btn-validate").onclick = () => run(async () => {
  const d = await api("/api/validation");
  let html = "";

  if (d.valid) {
    html = `<div class="alert alert-green">
      <h3>Schedule Passed Validation</h3>
      <ul>
        <li>No participant clashes (set intersection × time overlap)</li>
        <li>No venue overlaps (simultaneous same-venue booking)</li>
        <li>No buffer violations (${d.venue_buffer}-minute gap respected)</li>
        <li>All events have required date and venue</li>
        <li>All events have a time slot assigned</li>
      </ul>
    </div>`;
  } else {
    const pC = d.details?.participant_clashes || [];
    const vO = d.details?.venue_overlaps      || [];
    const bV = d.details?.buffer_violations   || [];
    const un = d.details?.unassigned_events   || [];
    const md = d.details?.missing_data        || [];
    const total = pC.length + vO.length + bV.length + un.length + md.length;

    html = `<div class="alert alert-amber" style="margin-bottom:12px">
      <strong>${total} issue${total !== 1 ? "s" : ""} found</strong> — resolve them and re-run to pass validation.
    </div>`;
    if (pC.length) html += `<div class="alert alert-red"><h3>Participant Clashes (${pC.length})</h3><ul>${pC.map(x=>`<li>${esc(x)}</li>`).join("")}</ul></div>`;
    if (vO.length) html += `<div class="alert alert-red"><h3>Venue Overlaps (${vO.length})</h3><ul>${vO.map(x=>`<li>${esc(x)}</li>`).join("")}</ul></div>`;
    if (bV.length) html += `<div class="alert alert-amber"><h3>Buffer Violations (${bV.length})</h3><p style="margin-bottom:6px">Venue transitions require a ${d.venue_buffer}-minute gap.</p><ul>${bV.map(x=>`<li>${esc(x)}</li>`).join("")}</ul></div>`;
    if (un.length) html += `<div class="alert alert-amber"><h3>Unassigned Events (${un.length})</h3><ul>${un.map(x=>`<li>${esc(x)}</li>`).join("")}</ul></div>`;
    if (md.length) html += `<div class="alert alert-red"><h3>Missing Data (${md.length})</h3><ul>${md.map(x=>`<li>${esc(x)}</li>`).join("")}</ul></div>`;
  }

  showResult("Schedule Validation Report", html);
});

// ── Analytics dashboard ───────────────────────────────
$("btn-analytics").onclick = () => run(async () => {
  const d = await api("/api/analytics");
  const clean = d.participant_clashes_count === 0 && d.venue_overlaps_count === 0;

  let html = `<div class="metric-grid">
    <div class="metric"><div class="metric-num">${d.total_events}</div><div class="metric-lbl">Total Events</div></div>
    <div class="metric good"><div class="metric-num">${d.scheduled_events}</div><div class="metric-lbl">Scheduled</div></div>
    <div class="metric ${d.unassigned_events > 0 ? "warn" : ""}"><div class="metric-num">${d.unassigned_events}</div><div class="metric-lbl">Unassigned</div></div>
    <div class="metric ${d.participant_clashes_count > 0 ? "bad" : ""}"><div class="metric-num">${d.participant_clashes_count}</div><div class="metric-lbl">P. Clashes</div></div>
    <div class="metric ${d.venue_overlaps_count > 0 ? "bad" : ""}"><div class="metric-num">${d.venue_overlaps_count}</div><div class="metric-lbl">Venue Overlaps</div></div>
    <div class="metric ${d.buffer_violations_count > 0 ? "warn" : ""}"><div class="metric-num">${d.buffer_violations_count}</div><div class="metric-lbl">Buffer Warnings</div></div>
  </div>
  <div class="alert ${clean ? "alert-green" : "alert-red"}" style="margin-bottom:16px">
    ${clean ? "No clashes or venue overlaps — all constraints satisfied." : "Constraint violations detected. Run Check Schedule for details."}
  </div>`;

  // Sub-tables
  const perDay = Object.entries(d.events_per_day || {});
  const venues  = Object.entries(d.venue_usage   || {}).sort((a,b) => b[1].events_count - a[1].events_count);
  const slots   = Object.entries(d.slot_usage    || {});
  const maxMin  = Math.max(...venues.map(([,v])=>v.total_minutes), 1);
  const maxSlot = Math.max(...slots.map(([,c])=>c), 1);

  html += `<div class="atbl-grid">
    <!-- Events per day -->
    <div class="atbl">
      <div class="atbl-head">Events Per Day</div>
      <table>
        <thead><tr><th>Date</th><th>Events</th></tr></thead>
        <tbody>
          ${perDay.length
            ? perDay.map(([date, cnt]) => `<tr>
                <td><strong>${esc(date)}</strong></td>
                <td><span class="pill pill-blue">${cnt}</span></td>
              </tr>`).join("")
            : `<tr><td colspan="2" style="text-align:center;color:#9ca3af;padding:16px">No data</td></tr>`}
        </tbody>
      </table>
    </div>

    <!-- Venue utilization -->
    <div class="atbl">
      <div class="atbl-head">Venue Utilization</div>
      <table>
        <thead><tr><th>Venue</th><th>Events</th><th>Total Time</th></tr></thead>
        <tbody>
          ${venues.length
            ? venues.map(([venue, info]) => `<tr>
                <td><strong>${esc(venue)}</strong></td>
                <td>${info.events_count}</td>
                <td>
                  <div class="bar-wrap">
                    <div class="bar" style="width:${Math.round((info.total_minutes/maxMin)*70)}px"></div>
                    <span style="font-size:.8rem;color:#6b7280">${info.total_minutes}m</span>
                  </div>
                </td>
              </tr>`).join("")
            : `<tr><td colspan="3" style="text-align:center;color:#9ca3af;padding:16px">No data</td></tr>`}
        </tbody>
      </table>
    </div>

    <!-- Slot distribution -->
    <div class="atbl">
      <div class="atbl-head">Time Slot Distribution</div>
      <table>
        <thead><tr><th>Slot</th><th>Usage</th></tr></thead>
        <tbody>
          ${slots.map(([slot, cnt]) => `<tr>
            <td style="font-size:.82rem;white-space:nowrap">${esc(slot)}</td>
            <td>
              <div class="bar-wrap">
                <div class="bar ${cnt === 0 ? "empty" : ""}" style="width:${cnt > 0 ? Math.max(Math.round((cnt/maxSlot)*70), 6) : 4}px"></div>
                <span style="font-size:.8rem;color:${cnt > 0 ? "var(--blue-dark)" : "#9ca3af"}">${cnt}</span>
              </div>
            </td>
          </tr>`).join("")}
        </tbody>
      </table>
    </div>
  </div>`;

  showResult("Analytics Dashboard", html);
});

// ── Buffer selector ───────────────────────────────────
bufferSel.addEventListener("change", () => run(async () => {
  const d = await api("/api/buffer", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ buffer: parseInt(bufferSel.value, 10) }),
  });
  setNotice(d.message, "ok");
}));

// ── Table row buttons ─────────────────────────────────
eventList.addEventListener("click", e => {
  const btn = e.target.closest(".act-btn");
  if (!btn) return;
  const id = btn.dataset.id;

  if (btn.classList.contains("suggest")) {
    run(async () => {
      const d = await api(`/api/events/${encodeURIComponent(id)}/suggestions`);
      let html = `<div class="alert alert-blue" style="margin-bottom:12px">
        <strong>${esc(d.event_name)}</strong> (${esc(d.event_id)}) &nbsp;·&nbsp;
        Venue: ${esc(d.venue)} &nbsp;·&nbsp;
        Window: ${esc(d.preferred_window)}
      </div>
      <p style="font-size:.875rem;color:#6b7280;margin-bottom:12px">${esc(d.summary)}</p>`;

      if (d.valid_slots?.length) {
        html += `<p class="section-label">Valid Slots</p><div class="slots">`;
        d.valid_slots.forEach(s => {
          html += `<div class="slot-row ok">
            <div>
              <div class="slot-time">${esc(s.slot)}</div>
              <div class="slot-why">${esc(s.reason)}</div>
            </div>
            <button class="btn-green btn apply-btn"
              data-id="${esc(d.event_id)}" data-s="${esc(s.start_time)}" data-e="${esc(s.end_time)}">
              Apply
            </button>
          </div>`;
        });
        html += `</div>`;
      }

      if (d.rejected_slots?.length) {
        html += `<p class="section-label" style="margin-top:14px">Unavailable Slots</p><div class="slots">`;
        d.rejected_slots.forEach(s => {
          html += `<div class="slot-row no">
            <div>
              <div class="slot-time" style="color:#9ca3af">${esc(s.slot)}</div>
              <div class="slot-why">${esc(s.reason)}</div>
            </div>
          </div>`;
        });
        html += `</div>`;
      }

      showResult(`Slot Suggestions — ${id}`, html);
    });
  }

  if (btn.classList.contains("edit")) {
    run(async () => {
      const { event: ev } = await api(`/api/events/${encodeURIComponent(id)}`);
      $("e-id").value    = ev.event_id;
      $("e-name").value  = ev.event_name;
      $("e-date").value  = ev.date;
      $("e-venue").value = ev.venue;
      $("e-window").value= ev.preferred_window || "";
      $("e-start").value = ev.start_time || "";
      $("e-end").value   = ev.end_time   || "";
      $("e-parts").value = (ev.participants || []).join(", ");
      $("e-desc").value  = ev.description || "";
      editWarn.classList.add("hidden");
      editWarn.innerHTML = "";
      editModal.classList.remove("hidden");
    });
  }

  if (btn.classList.contains("del")) {
    if (!confirm(`Delete event ${id}? This cannot be undone.`)) return;
    run(async () => {
      const d = await api(`/api/events/${encodeURIComponent(id)}`, { method: "DELETE" });
      setNotice(d.message, "ok");
      await loadEvents();
    });
  }
});

// ── Apply slot from suggestion panel ─────────────────
resultBody.addEventListener("click", e => {
  const btn = e.target.closest(".apply-btn");
  if (!btn) return;
  run(async () => {
    const d = await api(`/api/events/${encodeURIComponent(btn.dataset.id)}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ start_time: btn.dataset.s, end_time: btn.dataset.e }),
    });
    setNotice(d.message, "ok");
    await loadEvents();
    closeResult();
  });
});

// ── Edit modal ────────────────────────────────────────
$("btn-close-edit").onclick  = () => editModal.classList.add("hidden");
$("btn-cancel-edit").onclick = () => editModal.classList.add("hidden");

editForm.addEventListener("submit", e => {
  e.preventDefault();
  run(async () => {
    const body    = Object.fromEntries(new FormData(editForm));
    const eventId = body.event_id;
    const d = await api(`/api/events/${encodeURIComponent(eventId)}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });

    if (d.warnings?.length) {
      editWarn.classList.remove("hidden");
      editWarn.innerHTML = `<strong>Warnings — review before closing:</strong>
        <ul style="margin-top:6px">${d.warnings.map(w=>`<li>${esc(w)}</li>`).join("")}</ul>
        <p style="margin-top:6px;font-size:.82em">The event was saved. Adjust times above or close to proceed.</p>`;
      setNotice(`${d.message} (${d.warnings.length} warning(s) — see edit dialog)`, "warn");
      await loadEvents();
    } else {
      setNotice(d.message, "ok");
      editModal.classList.add("hidden");
      await loadEvents();
    }
  });
});

// ── Init ──────────────────────────────────────────────
loadEvents().catch(err => setNotice(err.message, "err"));
loadBuffer();
