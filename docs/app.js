const state = {
  data: null,
  selectedPlayer: null,
};

const PROFILE_COLORS = {
  "Alto impacto": "#7c83ff",
  "Apoyo táctico": "#ff7a59",
  "Ofensivo consistente": "#15d8a0",
  "Balanceado": "#cbd5e1",
};

const PROFILE_ORDER = [
  "Alto impacto",
  "Apoyo táctico",
  "Ofensivo consistente",
];

const RADAR_FEATURES = [
  "agresividad",
  "precision",
  "impacto",
  "soporte",
  "eficiencia",
  "entry_power",
  "consistencia",
];

function byId(id) {
  return document.getElementById(id);
}

function formatNumber(value) {
  if (typeof value !== "number") return value;
  return value.toLocaleString("es-CL");
}

function safeLower(value) {
  return String(value || "").toLowerCase();
}

function cleanText(value) {
  const text = String(value || "");

  return text
    .replaceAll("Ã¡", "á")
    .replaceAll("Ã©", "é")
    .replaceAll("Ã­", "í")
    .replaceAll("Ã³", "ó")
    .replaceAll("Ãº", "ú")
    .replaceAll("Ã", "Á")
    .replaceAll("Ã‰", "É")
    .replaceAll("Ã", "Í")
    .replaceAll("Ã“", "Ó")
    .replaceAll("Ãš", "Ú")
    .replaceAll("Ã±", "ñ")
    .replaceAll("Ã‘", "Ñ")
    .replaceAll("Ã¼", "ü")
    .replaceAll("Ãœ", "Ü")
    .replaceAll("Ä", "Á")
    .replaceAll("Â", "")
    .trim();
}

function formatRecommendationHtml(text) {
  const parts = String(text || "")
    .split("|")
    .map((item) => item.trim())
    .filter(Boolean);

  if (!parts.length) {
    return "Aquí aparecerá una recomendación personalizada basada en el estilo detectado.";
  }

  return `
    <ul style="margin:0; padding-left: 1.2rem; line-height:1.8;">
      ${parts.map((item) => `<li>${item}</li>`).join("")}
    </ul>
  `;
}

function formatFeatureLabel(feature) {
  const labels = {
    agresividad: "Agresividad",
    precision: "Precisión",
    impacto: "Impacto",
    soporte: "Soporte",
    eficiencia: "Eficiencia",
    entry_power: "Entry Power",
    consistencia: "Consistencia",
  };

  return labels[feature] || feature;
}

function getPlayerUniqueKey(player) {
  return `${safeLower(player.name)}||${safeLower(player.tag)}`;
}

function cleanText(value) {
  const text = String(value || "");

  return text
    .replaceAll("Ã¡", "á")
    .replaceAll("Ã©", "é")
    .replaceAll("Ã­", "í")
    .replaceAll("Ã³", "ó")
    .replaceAll("Ãº", "ú")
    .replaceAll("Ã", "Á")
    .replaceAll("Ã‰", "É")
    .replaceAll("Ã", "Í")
    .replaceAll("Ã“", "Ó")
    .replaceAll("Ãš", "Ú")
    .replaceAll("Ã±", "ñ")
    .replaceAll("Ã‘", "Ñ")
    .replaceAll("Ã¼", "ü")
    .replaceAll("Ãœ", "Ü")
    .replaceAll("Ä", "Á")
    .replaceAll("Â", "")
    .trim();
}

async function loadData() {
  const response = await fetch("./web_data.json");

  if (!response.ok) {
    throw new Error("No se pudo cargar web_data.json");
  }

  state.data = await response.json();
}

function getEligiblePlayers() {
  return state.data.players.filter(
    (player) => player.eligible_for_ranking === true
  );
}

function fillProfileChips() {
  const chipsWrap = byId("profileChips");
  const names = Object.values(state.data.cluster_names);

  chipsWrap.innerHTML = names
    .map(
      (name) => `
        <span class="profile-chip" style="color:${PROFILE_COLORS[name] || "#fff"};">
          ${name}
        </span>
      `
    )
    .join("");
}

function fillSearchOptions() {
  const datalist = byId("playerOptions");
  const uniquePlayersMap = new Map();

  state.data.players.forEach((player) => {
    const key = getPlayerUniqueKey(player);

    if (!uniquePlayersMap.has(key)) {
      uniquePlayersMap.set(key, player);
    }
  });

  const uniquePlayers = [...uniquePlayersMap.values()];

  datalist.innerHTML = uniquePlayers
    .slice(0, 5000)
    .map(
      (player) => `<option value="${cleanText(player.name)}">${cleanText(player.name)} ${cleanText(player.tag)}</option>`
    )
    .join("");
}

function scorePlayerByProfile(player, profile) {
  if (profile === "Alto impacto") {
    return (
      Number(player.impacto) * 0.45 +
      Number(player.entry_power) * 0.30 +
      Number(player.agresividad) * 0.15 +
      Number(player.consistencia) * 0.10
    );
  }

  if (profile === "Apoyo táctico") {
    return (
      Number(player.soporte) * 0.50 +
      Number(player.consistencia) * 0.20 +
      Number(player.eficiencia) * 0.15 +
      Number(player.win_percent) * 0.15
    );
  }

  if (profile === "Ofensivo consistente") {
    return (
      Number(player.consistencia) * 0.40 +
      Number(player.eficiencia) * 0.30 +
      Number(player.agresividad) * 0.15 +
      Number(player.kd_ratio) * 10 * 0.15
    );
  }

  return 0;
}

function getTopPlayersByProfile(profile, limit = 10) {
  const bestPlayersMap = new Map();

  getEligiblePlayers()
    .filter((player) => player.player_type === profile)
    .forEach((player) => {
      const scoredPlayer = {
        ...player,
        profile_score: scorePlayerByProfile(player, profile),
      };

      const key = getPlayerUniqueKey(player);
      const currentBest = bestPlayersMap.get(key);

      if (!currentBest || scoredPlayer.profile_score > currentBest.profile_score) {
        bestPlayersMap.set(key, scoredPlayer);
      }
    });

  return [...bestPlayersMap.values()]
    .sort((a, b) => b.profile_score - a.profile_score)
    .slice(0, limit);
}

function pickDefaultPlayer() {
  state.selectedPlayer = null;
  byId("playerSearch").value = "";
}

function findPlayer(searchText) {
  const players = state.data.players;
  const q = safeLower(searchText).trim();

  if (!q) return null;

  let exact = players.find(
    (player) =>
      safeLower(player.name) === q ||
      safeLower(player.tag) === q ||
      safeLower(`${player.name} ${player.tag}`) === q
  );

  if (exact) return exact;

  return players.find(
    (player) =>
      safeLower(player.name).includes(q) ||
      safeLower(player.tag).includes(q) ||
      safeLower(`${player.name} ${player.tag}`).includes(q)
  );
}

function renderPlayerInfo(player) {
  byId("playerName").textContent = cleanText(player.name || "Unknown");
byId("playerTag").textContent = cleanText(player.tag || "Unknown");

  byId("primaryProfile").textContent = player.player_type;
  byId("secondaryProfile").textContent = player.secondary_profile;
  byId("profileMix").textContent = player.profile_mix;

  byId("killsValue").textContent = formatNumber(player.kills);
  byId("deathsValue").textContent = formatNumber(player.deaths);
  byId("assistsValue").textContent = formatNumber(player.assists);
  byId("kdValue").textContent = Number(player.kd_ratio).toFixed(2);
  byId("hsValue").textContent = `${Number(player.headshot_percent).toFixed(1)}%`;
  byId("winValue").textContent = `${Number(player.win_percent).toFixed(1)}%`;

  byId("profileExplanation").textContent = player.profile_explanation;
  byId("recommendationText").textContent = player.recommendation;
}

function renderPlayerInfo(player) {
  byId("playerName").textContent = cleanText(player.name || "Unknown");
  byId("playerTag").textContent = cleanText(player.tag || "Unknown");

  byId("primaryProfile").textContent = player.player_type;
  byId("secondaryProfile").textContent = player.secondary_profile;
  byId("profileMix").textContent = player.profile_mix;

  byId("killsValue").textContent = formatNumber(player.kills);
  byId("deathsValue").textContent = formatNumber(player.deaths);
  byId("assistsValue").textContent = formatNumber(player.assists);
  byId("kdValue").textContent = Number(player.kd_ratio).toFixed(2);
  byId("hsValue").textContent = `${Number(player.headshot_percent).toFixed(1)}%`;
  byId("winValue").textContent = `${Number(player.win_percent).toFixed(1)}%`;

  byId("profileExplanation").textContent = player.profile_explanation;
  byId("recommendationText").innerHTML = formatRecommendationHtml(player.recommendation);
}


function renderEmptyState() {
  byId("playerName").textContent = "Ingresa un jugador";
  byId("playerTag").textContent = "Busca por nombre o tag para ver su análisis";

  byId("primaryProfile").textContent = "-";
  byId("secondaryProfile").textContent = "-";
  byId("profileMix").textContent = "Escribe un jugador y presiona “Analizar jugador”";

  byId("killsValue").textContent = "-";
  byId("deathsValue").textContent = "-";
  byId("assistsValue").textContent = "-";
  byId("kdValue").textContent = "-";
  byId("hsValue").textContent = "-";
  byId("winValue").textContent = "-";

  byId("profileExplanation").textContent =
    "Aquí aparecerá una interpretación del perfil cuando selecciones un jugador.";

  byId("recommendationText").textContent =
    "Aquí aparecerá una recomendación personalizada basada en el estilo detectado.";

  Plotly.purge("playerRadarChart");
  Plotly.purge("playerComparisonChart");

  byId("playerRadarChart").innerHTML = `
    <div style="display:flex; align-items:center; justify-content:center; height:100%; min-height:360px; color:#a8b2c9; text-align:center; padding:24px;">
      Ingresa un jugador para ver la comparación con su perfil.
    </div>
  `;

  byId("playerComparisonChart").innerHTML = `
    <div style="display:flex; align-items:center; justify-content:center; height:100%; min-height:360px; color:#a8b2c9; text-align:center; padding:24px;">
      Ingresa un jugador para ver sus atributos comparados con el promedio global.
    </div>
  `;
}

function renderEmptyState() {
  byId("playerName").textContent = "Ingresa un jugador";
  byId("playerTag").textContent = "Busca por nombre o tag para ver su análisis";

  byId("primaryProfile").textContent = "-";
  byId("secondaryProfile").textContent = "-";
  byId("profileMix").textContent = "Escribe un jugador y presiona “Analizar jugador”";

  byId("killsValue").textContent = "-";
  byId("deathsValue").textContent = "-";
  byId("assistsValue").textContent = "-";
  byId("kdValue").textContent = "-";
  byId("hsValue").textContent = "-";
  byId("winValue").textContent = "-";

  byId("profileExplanation").textContent =
    "Aquí aparecerá una interpretación del perfil cuando selecciones un jugador.";

  byId("recommendationText").innerHTML =
    "Aquí aparecerá una recomendación personalizada basada en el estilo detectado.";

  Plotly.purge("playerRadarChart");
  Plotly.purge("playerComparisonChart");

  byId("playerRadarChart").innerHTML = `
    <div style="display:flex; align-items:center; justify-content:center; height:100%; min-height:360px; color:#a8b2c9; text-align:center; padding:24px;">
      Ingresa un jugador para ver la comparación con su perfil.
    </div>
  `;

  byId("playerComparisonChart").innerHTML = `
    <div style="display:flex; align-items:center; justify-content:center; height:100%; min-height:360px; color:#a8b2c9; text-align:center; padding:24px;">
      Ingresa un jugador para ver sus atributos comparados con el promedio global.
    </div>
  `;
}

function renderPlayerRadar(player) {
  const chartEl = byId("playerRadarChart");
  chartEl.innerHTML = "";

  const profileSummary = state.data.profile_summary.find(
    (profile) => profile.player_type === player.player_type
  );

  const radarLabels = RADAR_FEATURES.map((feature) => formatFeatureLabel(feature));
  const playerValues = RADAR_FEATURES.map((key) => Number(player[key]));
  const profileValues = RADAR_FEATURES.map((key) => Number(profileSummary[key]));

  const data = [
    {
      type: "scatterpolar",
      r: playerValues,
      theta: radarLabels,
      fill: "toself",
      name: cleanText(player.name),
      line: {
        color: PROFILE_COLORS[player.player_type] || "#8b92ff",
        width: 3,
      },
      marker: {
        size: 6,
        color: PROFILE_COLORS[player.player_type] || "#8b92ff",
      },
      fillcolor: "rgba(139,146,255,0.18)",
      hovertemplate: "<b>%{theta}</b><br>Valor: %{r:.1f}<extra></extra>",
    },
    {
      type: "scatterpolar",
      r: profileValues,
      theta: radarLabels,
      fill: "toself",
      name: `Promedio ${player.player_type}`,
      line: {
        color: "#f5c84c",
        width: 2.5,
        dash: "dash",
      },
      marker: {
        size: 5,
        color: "#f5c84c",
      },
      fillcolor: "rgba(245,200,76,0.12)",
      hovertemplate: "<b>%{theta}</b><br>Promedio: %{r:.1f}<extra></extra>",
    },
  ];

  const layout = {
    paper_bgcolor: "rgba(0,0,0,0)",
    plot_bgcolor: "rgba(0,0,0,0)",
    font: {
      family: "Inter, sans-serif",
      color: "#f4f7ff",
      size: 14,
    },
    polar: {
      bgcolor: "rgba(0,0,0,0)",
      radialaxis: {
        visible: true,
        range: [0, 100],
        tickfont: {
          family: "Inter, sans-serif",
          size: 12,
          color: "#c8d2ea",
        },
        gridcolor: "rgba(255,255,255,0.10)",
        linecolor: "rgba(255,255,255,0.14)",
      },
      angularaxis: {
        tickfont: {
          family: "Inter, sans-serif",
          size: 13,
          color: "#eef2ff",
        },
        gridcolor: "rgba(255,255,255,0.08)",
        linecolor: "rgba(255,255,255,0.12)",
      },
    },
    legend: {
      orientation: "h",
      y: 1.13,
      x: 0,
      font: {
        family: "Inter, sans-serif",
        size: 13,
        color: "#eef2ff",
      },
    },
    margin: { l: 40, r: 40, t: 35, b: 35 },
  };

  Plotly.newPlot(chartEl, data, layout, {
    responsive: true,
    displaylogo: false,
    displayModeBar: false,
    scrollZoom: false,
  });
}

function getGlobalMeans() {
  const players = getEligiblePlayers().length ? getEligiblePlayers() : state.data.players;
  const means = {};

  for (const feature of RADAR_FEATURES) {
    const values = players.map((player) => Number(player[feature]));
    const sum = values.reduce((acc, value) => acc + value, 0);
    means[feature] = sum / values.length;
  }

  return means;
}

function renderPlayerComparisonChart(player) {
  const chartEl = byId("playerComparisonChart");
  chartEl.innerHTML = "";

  const globalMeans = getGlobalMeans();

  const featureLabels = RADAR_FEATURES.map((feature) => formatFeatureLabel(feature));
  const playerValues = RADAR_FEATURES.map((feature) => Number(player[feature]));
  const avgValues = RADAR_FEATURES.map((feature) => Number(globalMeans[feature]));

  const data = [
    {
      type: "bar",
      x: featureLabels,
      y: playerValues,
      name: cleanText(player.name),
      marker: {
        color: PROFILE_COLORS[player.player_type] || "#8b92ff",
      },
      hovertemplate: "<b>%{x}</b><br>Jugador: %{y:.1f}<extra></extra>",
    },
    {
      type: "bar",
      x: featureLabels,
      y: avgValues,
      name: "Promedio global",
      marker: {
        color: "#a5afc3",
      },
      hovertemplate: "<b>%{x}</b><br>Promedio: %{y:.1f}<extra></extra>",
    },
  ];

  const layout = {
    barmode: "group",
    paper_bgcolor: "rgba(0,0,0,0)",
    plot_bgcolor: "rgba(0,0,0,0)",
    font: {
      family: "Inter, sans-serif",
      color: "#f4f7ff",
      size: 14,
    },
    margin: { l: 55, r: 20, t: 25, b: 80 },
    xaxis: {
      tickangle: -18,
      automargin: true,
      tickfont: {
        family: "Inter, sans-serif",
        size: 13,
        color: "#eef2ff",
      },
      gridcolor: "rgba(255,255,255,0.04)",
      zeroline: false,
    },
    yaxis: {
      title: {
        text: "Valor",
        font: {
          family: "Inter, sans-serif",
          size: 15,
          color: "#eef2ff",
        },
      },
      range: [0, 100],
      tickfont: {
        family: "Inter, sans-serif",
        size: 12,
        color: "#c8d2ea",
      },
      gridcolor: "rgba(255,255,255,0.10)",
      zeroline: false,
    },
    legend: {
      orientation: "h",
      y: 1.12,
      x: 0,
      font: {
        family: "Inter, sans-serif",
        size: 13,
        color: "#eef2ff",
      },
    },
  };

  Plotly.newPlot(chartEl, data, layout, {
    responsive: true,
    displaylogo: false,
    displayModeBar: false,
    scrollZoom: false,
  });
}

function renderTopBoards() {
  const wrap = byId("topBoardsWrap");

  const boardsHtml = PROFILE_ORDER.map((profile) => {
    const players = getTopPlayersByProfile(profile, 10);

    const rows = players
      .map(
        (player, index) => `
          <tr data-player="${player.name}">
            <td>#${index + 1}</td>
            <td>
              <strong>${cleanText(player.name)}</strong><br>
<span class="muted">${cleanText(player.tag)}</span>
            </td>
            <td>${player.profile_score.toFixed(2)}</td>
            <td>${Number(player.kd_ratio).toFixed(2)}</td>
            <td>${Number(player.headshot_percent).toFixed(1)}%</td>
            <td>${Number(player.win_percent).toFixed(1)}%</td>
            <td>${formatNumber(player.wins)}</td>
          </tr>
        `
      )
      .join("");

    return `
      <div class="glass-card" style="padding:18px;">
        <div class="card-title-wrap" style="padding:4px 4px 14px;">
          <h3 style="margin:0; color:${PROFILE_COLORS[profile] || "#fff"};">Top ${profile}</h3>
          <span class="mini-badge">Top 10</span>
        </div>

        <div class="table-wrap">
          <table class="players-table">
            <thead>
              <tr>
                <th>#</th>
                <th>Jugador</th>
                <th>Score perfil</th>
                <th>K/D</th>
                <th>HS%</th>
                <th>Win%</th>
                <th>Wins</th>
              </tr>
            </thead>
            <tbody>
              ${rows || `<tr><td colspan="7">No hay jugadores suficientes en este perfil.</td></tr>`}
            </tbody>
          </table>
        </div>
      </div>
    `;
  }).join("");

  wrap.innerHTML = `
    <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(340px, 1fr)); gap:18px;">
      ${boardsHtml}
    </div>
  `;

  wrap.querySelectorAll("tbody tr[data-player]").forEach((row) => {
    row.addEventListener("click", () => {
      const playerName = row.getAttribute("data-player");
      const player = state.data.players.find((p) => p.name === playerName);

      if (player) {
        state.selectedPlayer = player;
        byId("playerSearch").value = player.name;
        renderSelectedPlayer();
        byId("analyzer").scrollIntoView({
          behavior: "smooth",
          block: "start",
        });
      }
    });
  });
}

function renderSelectedPlayer() {
  if (!state.selectedPlayer) {
    renderEmptyState();
    return;
  }

  renderPlayerInfo(state.selectedPlayer);
  renderPlayerRadar(state.selectedPlayer);
  renderPlayerComparisonChart(state.selectedPlayer);
}

function bindEvents() {
  function runSearchAndFocusAnalysis() {
    const player = findPlayer(byId("playerSearch").value);

    if (!player) {
      alert("No se encontró un jugador con ese nombre o tag.");
      return;
    }

    state.selectedPlayer = player;
    renderSelectedPlayer();

    byId("playerSearch").blur();

    setTimeout(() => {
      byId("analyzer").scrollIntoView({
        behavior: "smooth",
        block: "start",
      });
    }, 80);
  }

  byId("analyzeBtn").addEventListener("click", () => {
    runSearchAndFocusAnalysis();
  });

  byId("playerSearch").addEventListener("keydown", (event) => {
    if (event.key === "Enter") {
      event.preventDefault();
      runSearchAndFocusAnalysis();
    }
  });
}

async function init() {
  try {
    await loadData();
    fillProfileChips();
    fillSearchOptions();
    pickDefaultPlayer();
    bindEvents();
    renderSelectedPlayer();
    renderTopBoards();
  } catch (error) {
    console.error(error);
    document.body.innerHTML = `
      <main style="padding:40px; color:white; font-family:Inter, sans-serif;">
        <h1>Error cargando Valostats</h1>
        <p>No se pudo cargar <code>web_data.json</code>. Abre la página desde un servidor local o GitHub Pages.</p>
      </main>
    `;
  }
}

init();