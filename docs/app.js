const MODEL_META = {
  "samaya-system": { name: "Samaya System", harness: "Samaya", symbol: "★" },
  "fa-v2-fable-5": { name: "Claude Fable 5", harness: "Finance Agent v2", symbol: "◆" },
  "fa-v2-gpt-5-6-sol": { name: "GPT 5.6 Sol", harness: "Finance Agent v2", symbol: "◆" },
  "fa-v2-opus-4-8": { name: "Claude Opus 4.8", harness: "Finance Agent v2", symbol: "◆" },
  "fa-v2-gpt-5-5": { name: "GPT 5.5", harness: "Finance Agent v2", symbol: "◆" },
  "fa-v2-glm-5-2": { name: "GLM 5.2", harness: "Finance Agent v2", symbol: "◆" },
  "fa-v2-deepseek-v4-pro": { name: "DeepSeek V4 Pro", harness: "Finance Agent v2", symbol: "◆" },
  "fa-v2-kimi-k2-6": { name: "Kimi K2.6", harness: "Finance Agent v2", symbol: "◆" },
  "fa-v2-gemini-3-1-pro": { name: "Gemini 3.1 Pro", harness: "Finance Agent v2", symbol: "◆" },
  "web-search-opus-4-8": { name: "Claude Opus 4.8", harness: "Web Search", symbol: "●" },
  "web-search-gemini-3-1-pro": { name: "Gemini 3.1 Pro", harness: "Web Search", symbol: "●" },
  "web-search-gpt-5-5": { name: "GPT 5.5", harness: "Web Search", symbol: "●" },
};

const state = { axis: "cost", selected: "samaya-system", runs: [] };

const fmt = {
  pct: (value) => `${(value * 100).toFixed(1)}%`,
  usd: (value) => `$${value.toFixed(2)}`,
  seconds: (value) => `${Math.round(value)}s`,
  number: (value) => Number(value).toLocaleString("en-US"),
};

async function readJson(path) {
  const response = await fetch(path);
  if (!response.ok) throw new Error(`${path}: HTTP ${response.status}`);
  return response.json();
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function metaFor(run) {
  return MODEL_META[run.id] || { name: run.label, harness: run.system, symbol: "■" };
}

function renderDetail() {
  const run = state.runs.find((item) => item.id === state.selected) || state.runs[0];
  if (!run) return;
  const meta = metaFor(run);
  document.querySelector("#chart-detail").innerHTML = `
    <span class="detail-label panel-label">${escapeHtml(meta.harness)}</span>
    <h3>${escapeHtml(meta.name)}</h3>
    <dl>
      <div><dt>Qualification rate</dt><dd>${fmt.pct(run.qualification_rate)}</dd></div>
      <div><dt>Average cost</dt><dd>${fmt.usd(run.cost_per_query)}</dd></div>
      <div><dt>Average latency</dt><dd>${fmt.seconds(run.latency_per_query)}</dd></div>
      <div><dt>Queries</dt><dd>${run.num_records}</dd></div>
    </dl>
  `;
}

function pointMarkup(run, x, y) {
  const meta = metaFor(run);
  const selected = run.id === state.selected;
  const color = run.id === "samaya-system" ? "#91a5ff" : "#faf8f1";
  const label = `${meta.name} · ${meta.harness}`;
  let shape = `<circle cx="${x}" cy="${y}" r="${selected ? 8 : 6}" fill="${color}" />`;
  if (meta.symbol === "◆") {
    const size = selected ? 9 : 7;
    shape = `<path d="M ${x} ${y - size} L ${x + size} ${y} L ${x} ${y + size} L ${x - size} ${y} Z" fill="${color}" />`;
  }
  if (meta.symbol === "★") {
    shape = `<text x="${x}" y="${y + 7}" text-anchor="middle" fill="${color}" font-size="25">★</text>`;
  }
  return `
    <g class="point-group" data-run-id="${run.id}" tabindex="0" role="button" aria-label="${escapeHtml(label)}, ${fmt.pct(run.qualification_rate)}">
      ${shape}
      <text class="point-label" x="${x + 12}" y="${y - 10}">${escapeHtml(meta.name)}</text>
    </g>
  `;
}

function renderChart() {
  const container = document.querySelector("#tradeoff-chart");
  const width = 820;
  const height = 430;
  const margin = { left: 64, right: 34, top: 28, bottom: 58 };
  const innerWidth = width - margin.left - margin.right;
  const innerHeight = height - margin.top - margin.bottom;
  const accessor = state.axis === "cost" ? "cost_per_query" : "latency_per_query";
  const values = state.runs.map((run) => run[accessor]);
  const maxX = Math.max(...values) * 1.08;
  const minY = 0.18;
  const maxY = 0.54;
  const xScale = (value) => margin.left + (value / maxX) * innerWidth;
  const yScale = (value) => margin.top + ((maxY - value) / (maxY - minY)) * innerHeight;
  const yTicks = [0.2, 0.3, 0.4, 0.5];
  const xTicks = [0, 0.25, 0.5, 0.75, 1].map((step) => step * maxX);
  const axisName = state.axis === "cost" ? "Cost / query (USD)" : "Average latency (seconds)";
  const tickText = (value) => (state.axis === "cost" ? `$${value.toFixed(1)}` : `${Math.round(value)}s`);

  container.innerHTML = `
    <svg viewBox="0 0 ${width} ${height}" role="img" aria-labelledby="chart-title chart-desc">
      <title id="chart-title">官方 FrontierFinance 质量与${state.axis === "cost" ? "成本" : "延迟"}权衡</title>
      <desc id="chart-desc">越高代表 rubric 通过率越高，越靠左代表${state.axis === "cost" ? "成本" : "延迟"}越低。下方表格提供相同数据。</desc>
      <rect x="${margin.left}" y="${margin.top}" width="${innerWidth * 0.36}" height="${innerHeight * 0.28}" fill="#1637d5" opacity="0.14" />
      <text class="tick-label" x="${margin.left + 10}" y="${margin.top + 18}">DESIRABLE REGION</text>
      ${yTicks.map((tick) => `
        <line class="grid-line" x1="${margin.left}" x2="${width - margin.right}" y1="${yScale(tick)}" y2="${yScale(tick)}" />
        <text class="tick-label" x="${margin.left - 12}" y="${yScale(tick) + 4}" text-anchor="end">${Math.round(tick * 100)}%</text>
      `).join("")}
      ${xTicks.map((tick) => `
        <line class="grid-line" x1="${xScale(tick)}" x2="${xScale(tick)}" y1="${margin.top}" y2="${height - margin.bottom}" />
        <text class="tick-label" x="${xScale(tick)}" y="${height - margin.bottom + 24}" text-anchor="middle">${tickText(tick)}</text>
      `).join("")}
      <text class="axis-label" x="${margin.left + innerWidth / 2}" y="${height - 10}" text-anchor="middle">${axisName}</text>
      <text class="axis-label" transform="translate(16 ${margin.top + innerHeight / 2}) rotate(-90)" text-anchor="middle">Rubric qualification rate</text>
      ${state.runs.map((run) => pointMarkup(run, xScale(run[accessor]), yScale(run.qualification_rate))).join("")}
    </svg>
  `;

  container.querySelectorAll(".point-group").forEach((point) => {
    const select = () => {
      state.selected = point.dataset.runId;
      renderChart();
      renderDetail();
    };
    point.addEventListener("click", select);
    point.addEventListener("keydown", (event) => {
      if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        select();
      }
    });
  });
}

function renderLeaderboard() {
  const sorted = [...state.runs].sort((a, b) => b.qualification_rate - a.qualification_rate);
  document.querySelector("#leaderboard-table").innerHTML = `
    <table>
      <caption class="sr-only">官方 FrontierFinance 系统性能排名</caption>
      <thead><tr><th>#</th><th>System</th><th>Harness</th><th data-number>Score</th><th data-number>Latency</th><th data-number>Cost</th></tr></thead>
      <tbody>
        ${sorted.map((run, index) => {
          const meta = metaFor(run);
          return `<tr>
            <td>${index + 1}</td>
            <td><span class="system-symbol" aria-hidden="true">${meta.symbol}</span>${escapeHtml(meta.name)}</td>
            <td>${escapeHtml(meta.harness)}</td>
            <td data-number>${fmt.pct(run.qualification_rate)}</td>
            <td data-number>${fmt.seconds(run.latency_per_query)}</td>
            <td data-number>${fmt.usd(run.cost_per_query)}</td>
          </tr>`;
        }).join("")}
      </tbody>
    </table>
  `;
}

function renderFacts(facts) {
  const labels = {
    automotive_sales: "Automotive sales",
    regulatory_credits: "Regulatory credits",
    automotive_leasing: "Automotive leasing",
    total_automotive: "Total automotive revenue",
    energy: "Energy generation & storage",
    services_other: "Services & other",
    total_revenue: "Total revenue",
  };
  document.querySelector("#demo-facts").innerHTML = `
    <table>
      <caption class="sr-only">Tesla Q4 2024 收入推导</caption>
      <thead><tr><th>Metric</th><th data-number>FY 2024</th><th data-number>9M 2024</th><th data-number>Q4 derived</th></tr></thead>
      <tbody>
        ${Object.keys(labels).map((key) => `<tr>
          <td>${labels[key]}</td>
          <td data-number>${fmt.number(facts.fy[key])}</td>
          <td data-number>${fmt.number(facts.nine_month[key])}</td>
          <td data-number><strong>${fmt.number(facts.q4[key])}</strong></td>
        </tr>`).join("")}
      </tbody>
    </table>
  `;
}

function renderAnomalies(anomalies) {
  document.querySelector("#anomaly-list").innerHTML = anomalies.map((item) => `
    <article class="anomaly-item">
      <strong>RUBRIC ${item.rubric_id} · SCORING ANOMALY</strong>
      <p>${escapeHtml(item.rubric_text)}</p>
      <dl>
        <div><dt>SEC-derived</dt><dd>${fmt.number(item.source_derived_value_usd_millions)}m</dd></div>
        <div><dt>Rubric target</dt><dd>${fmt.number(item.rubric_target_usd_millions)}m</dd></div>
      </dl>
    </article>
  `).join("");
}

function renderTimeline(events) {
  document.querySelector("#failure-timeline").innerHTML = events.map((event) => {
    const passed = event.status === "passed";
    return `<li>
      <time datetime="${event.at}">${event.at.slice(11, 19)} UTC</time>
      <span class="failure-category ${passed ? "passed" : ""}">${escapeHtml(event.category)}</span>
      <p>${escapeHtml(event.summary)}</p>
    </li>`;
  }).join("");
}

async function main() {
  try {
    const [performance, facts, anomalies, failures] = await Promise.all([
      readJson("data/official/system-performance.json"),
      readJson("data/demo/facts.json"),
      readJson("data/demo/rubric_audit.json"),
      readJson("data/failure-timeline.json"),
    ]);
    state.runs = performance.runs;
    renderChart();
    renderDetail();
    renderLeaderboard();
    renderFacts(facts);
    renderAnomalies(anomalies);
    renderTimeline(failures);
  } catch (error) {
    document.querySelector("#data-error").hidden = false;
    console.error(error);
  }
}

document.querySelectorAll("[data-axis]").forEach((button) => {
  button.addEventListener("click", () => {
    state.axis = button.dataset.axis;
    document.querySelectorAll("[data-axis]").forEach((item) => {
      item.setAttribute("aria-pressed", String(item === button));
    });
    renderChart();
  });
});

main();

