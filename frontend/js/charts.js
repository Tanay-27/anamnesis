// dataZoom (inside + slider) is what gives scroll-left/right and
// pinch/wheel zoom on the time axis — the whole point of choosing
// ECharts for this. `start`/`end` default to the most recent ~30% of
// the series so a long history doesn't open fully zoomed out.

function makeTimeSeriesOption(title, dates, values, seriesType) {
  return {
    title: { text: title, left: "center", textStyle: { fontSize: 14 } },
    tooltip: { trigger: "axis" },
    xAxis: { type: "category", data: dates },
    yAxis: { type: "value", scale: true },
    dataZoom: [
      { type: "inside", start: 70, end: 100 },
      { type: "slider", start: 70, end: 100 },
    ],
    series: [
      {
        type: seriesType,
        data: values,
        smooth: seriesType === "line",
        areaStyle: seriesType === "line" ? {} : undefined,
      },
    ],
  };
}

async function renderMetricChart(elementId, metricName, title, seriesType) {
  const el = document.getElementById(elementId);
  if (!el) return;
  const points = await apiGet(`/metrics/${metricName}`);
  const dates = points.map((p) => p.date);
  const values = points.map((p) => p.value);

  const chart = echarts.init(el);
  chart.setOption(makeTimeSeriesOption(title, dates, values, seriesType));
  window.addEventListener("resize", () => chart.resize());
}

async function loadGoals() {
  const container = document.getElementById("goal-list");
  if (!container) return;
  const goals = await apiGet("/goals?status=active");

  container.innerHTML = "";
  goals.forEach((g) => {
    const pct = g.percent_achieved !== null ? g.percent_achieved : null;
    const div = document.createElement("div");
    div.className = "card";
    div.innerHTML = `
      <h2>${g.metric}</h2>
      <p>${g.start_value} &rarr; ${g.target_value} by ${g.target_date}</p>
      <div class="goal-bar"><div class="goal-bar-fill" style="width:${pct ?? 0}%"></div></div>
      <p class="muted">${pct !== null ? pct.toFixed(0) + "% achieved" : "no data yet"}</p>
    `;
    container.appendChild(div);
  });
}

renderMetricChart("chart-weight", "weight_kg", "Weight (kg)", "line");
renderMetricChart("chart-steps", "steps", "Steps", "bar");
loadGoals();
