function todayISO() {
  return new Date().toISOString().slice(0, 10);
}

function renderEntry(entry) {
  const li = document.createElement("li");
  const tags = entry.tags.map((t) => `<span class="tag">${t}</span>`).join(" ");
  li.innerHTML = `<strong>${entry.date}</strong> ${tags}<br>${entry.raw_text}`;
  return li;
}

async function loadEntries() {
  const list = document.getElementById("entry-list");
  list.innerHTML = "";
  const entries = await apiGet("/entries");
  entries.reverse().forEach((e) => list.appendChild(renderEntry(e)));
}

document.getElementById("entry-date").value = todayISO();

document.getElementById("entry-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const date = document.getElementById("entry-date").value;
  const raw_text = document.getElementById("entry-text").value;
  const status = document.getElementById("entry-status");

  try {
    await apiPost("/entries", { date, raw_text });
    document.getElementById("entry-text").value = "";
    status.textContent = "Logged.";
    await loadEntries();
  } catch (err) {
    status.textContent = `Error: ${err.message}`;
  }
});

loadEntries();
