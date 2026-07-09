function listify(items, cls) {
  if (!items || items.length === 0) return "<li class='muted'>none</li>";
  return items.map((i) => `<li class="${cls}">${i}</li>`).join("");
}

function renderRollup(rollup) {
  const li = document.createElement("li");
  const s = rollup.summary;

  const numericRows = Object.entries(s.numeric_metrics || {})
    .map(([name, stats]) => {
      const sign = stats.trend >= 0 ? "+" : "";
      return `<li>${name}: ${stats.start} &rarr; ${stats.end} (${sign}${stats.trend.toFixed(2)})</li>`;
    })
    .join("");

  li.innerHTML = `
    <h3>Rollup #${rollup.id} — ${rollup.period_start} to ${rollup.period_end}</h3>
    <p class="muted">${s.entry_count ?? "?"} entries covered &middot; status: ${rollup.status}</p>
    <div class="diff-block">
      <strong>Numeric metrics</strong>
      <ul>${numericRows || "<li class='muted'>none</li>"}</ul>
      <strong class="promoted">Promoted</strong>
      <ul>${listify(s.promoted, "promoted")}</ul>
      <strong class="carried">Carried forward</strong>
      <ul>${listify(s.carried_forward, "carried")}</ul>
      <strong class="dropped">Dropped</strong>
      <ul>${listify(s.dropped, "dropped")}</ul>
    </div>
  `;

  if (rollup.status === "draft") {
    const actions = document.createElement("div");
    actions.innerHTML = `
      <button class="approve">Approve</button>
      <button class="secondary reject">Reject</button>
    `;
    actions.querySelector(".approve").addEventListener("click", () => reviewRollup(rollup.id, "approve"));
    actions.querySelector(".reject").addEventListener("click", () => reviewRollup(rollup.id, "reject"));
    li.appendChild(actions);
  }

  return li;
}

async function reviewRollup(id, action) {
  const notes = prompt("Reviewer notes (optional):") || null;
  // Same endpoints Epoch 5/6 already implement and test — this UI adds
  // no new backend behavior, just a second frontend on the same logic.
  await apiPost(`/rollups/${id}/${action}`, { reviewer_notes: notes });
  await loadRollups();
}

async function loadRollups() {
  const list = document.getElementById("rollup-list");
  list.innerHTML = "";
  const rollups = await apiGet("/rollups");
  if (rollups.length === 0) {
    list.innerHTML = "<li class='muted'>No rollups yet.</li>";
    return;
  }
  rollups.forEach((r) => list.appendChild(renderRollup(r)));
}

loadRollups();
