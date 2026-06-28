// Organic Agentic AutoDev — live dashboard client.
// Connects to /ws for live tick snapshots; falls back to polling /api/step.

let paused = false;
const $ = (id) => document.getElementById(id);

const chartOpts = (label, color) => ({
  type: "line",
  data: { labels: [], datasets: [{ label, data: [], borderColor: color,
    backgroundColor: color + "22", tension: 0.25, pointRadius: 0, fill: true }] },
  options: {
    animation: false, responsive: true,
    scales: { x: { display: false }, y: { beginAtZero: true, grid: { color: "#30363d" },
      ticks: { color: "#8b949e" } } },
    plugins: { legend: { display: false } },
  },
});

const knowledgeChart = new Chart($("knowledgeChart"), chartOpts("records", "#2ea043"));
const complianceChart = new Chart($("complianceChart"), chartOpts("compliance", "#58a6ff"));

function pushPoint(chart, x, y, max = 60) {
  chart.data.labels.push(x);
  chart.data.datasets[0].data.push(y);
  if (chart.data.labels.length > max) {
    chart.data.labels.shift();
    chart.data.datasets[0].data.shift();
  }
  chart.update();
}

function render(s) {
  $("tick").textContent = "tick " + s.tick;
  $("agents").textContent = s.agents.alive;
  $("diff").textContent = s.agents.differentiated;
  $("organs").textContent = s.body.organs;
  $("records").textContent = s.knowledge.records;
  $("edges").textContent = s.network.edges;
  $("energy").textContent = Math.round(s.knowledge.energy_remaining);

  const slaEl = $("sla");
  slaEl.textContent = "SLA " + Math.round(s.sla.compliance_rate * 100) + "%";
  slaEl.className = "pill " + (s.sla.compliant ? "good" : "bad");

  // Roles
  const roles = Object.entries(s.agents.roles).sort((a, b) => b[1] - a[1]);
  $("roles").innerHTML = roles.map(([r, n]) =>
    `<span class="role-chip">${r}<b>${n}</b></span>`).join("") || "<span class='label'>none yet</span>";

  // SLOs
  $("slos").innerHTML = s.sla.slos.map((slo) =>
    `<li><span><span class="dot ${slo.status}"></span>${slo.name} <span class="label">${slo.priority}</span></span>`
    + `<span>${slo.value.toFixed(3)}</span></li>`).join("") || "<li class='label'>warming up…</li>";

  // Events
  $("events").innerHTML = s.events.slice().reverse().map((e) =>
    `<li><span>${e.kind}</span><span>${e.source.slice(0, 18)}</span></li>`).join("");

  pushPoint(knowledgeChart, s.tick, s.knowledge.records);
  pushPoint(complianceChart, s.tick, s.sla.compliance_rate);
}

$("pause").addEventListener("click", () => {
  paused = !paused;
  $("pause").textContent = paused ? "▶ Resume" : "⏸ Pause";
});

function connect() {
  const proto = location.protocol === "https:" ? "wss" : "ws";
  const ws = new WebSocket(`${proto}://${location.host}/ws`);
  ws.onmessage = (ev) => { if (!paused) render(JSON.parse(ev.data)); };
  ws.onclose = () => setTimeout(pollFallback, 1000);  // graceful degradation
}

async function pollFallback() {
  if (!paused) {
    try {
      const r = await fetch("/api/step");
      render(await r.json());
    } catch (_) { /* server gone */ }
  }
  setTimeout(pollFallback, 600);
}

// Seed with current state, then go live.
fetch("/api/state").then((r) => r.json()).then(render).catch(() => {});
connect();
