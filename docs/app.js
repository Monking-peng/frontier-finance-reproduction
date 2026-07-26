const fmt = {
  number: (value) => Number(value).toLocaleString("en-US"),
};

const categoryLabels = {
  environment_anomaly: "环境问题",
  agent_failure: "解析问题",
  completed_with_findings: "最终结果",
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

function renderFacts(facts) {
  const labels = {
    automotive_sales: "汽车销售收入",
    regulatory_credits: "碳积分收入",
    automotive_leasing: "汽车租赁收入",
    total_automotive: "汽车业务总收入",
    energy: "能源生产与储存收入",
    services_other: "服务及其他收入",
    total_revenue: "总收入",
  };
  document.querySelector("#demo-facts").innerHTML = `
    <table>
      <caption class="sr-only">Tesla 2024 年第四季度收入推导，单位为百万美元</caption>
      <thead><tr><th>收入项目</th><th data-number>2024 全年</th><th data-number>前 9 个月</th><th data-number>推导 Q4</th></tr></thead>
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
      <strong>评分标准 ${item.rubric_id} · 数据冲突</strong>
      <p>${escapeHtml(item.rubric_text)}</p>
      <dl>
        <div><dt>SEC 计算结果</dt><dd>${fmt.number(item.source_derived_value_usd_millions)}m</dd></div>
        <div><dt>评分标准要求</dt><dd>${fmt.number(item.rubric_target_usd_millions)}m</dd></div>
      </dl>
    </article>
  `).join("");
}

function renderTimeline(events) {
  document.querySelector("#failure-timeline").innerHTML = events.map((event) => {
    const passed = event.status === "passed";
    const category = categoryLabels[event.category] || event.category;
    return `<li>
      <time datetime="${event.at}">${event.at.slice(11, 19)} UTC</time>
      <span class="failure-category ${passed ? "passed" : ""}">${escapeHtml(category)}</span>
      <p>${escapeHtml(event.summary)}</p>
    </li>`;
  }).join("");
}

async function main() {
  try {
    const [facts, anomalies, failures] = await Promise.all([
      readJson("data/demo/facts.json"),
      readJson("data/demo/rubric_audit.json"),
      readJson("data/failure-timeline.json"),
    ]);
    renderFacts(facts);
    renderAnomalies(anomalies);
    renderTimeline(failures);
  } catch (error) {
    document.querySelector("#data-error").hidden = false;
    console.error(error);
  }
}

main();
