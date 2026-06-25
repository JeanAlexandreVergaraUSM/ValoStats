const state = {
  data: null,
  selectedPlayer: null,
  currentAnalysis: null,
  isAnalyzing: false,
};

const API_BASE_URL = "";
const API_ANALYZE_URL = "/api/analyze";
const IS_GITHUB_PAGES = window.location.hostname.includes("github.io");

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

function safeLower(value) {
  return String(value || "").toLowerCase();
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
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

function formatNumber(value, decimals = null) {
  const numericValue = Number(value);

  if (!Number.isFinite(numericValue)) {
    return "-";
  }

  if (decimals !== null) {
    return numericValue.toLocaleString("es-CL", {
      minimumFractionDigits: decimals,
      maximumFractionDigits: decimals,
    });
  }

  return numericValue.toLocaleString("es-CL");
}

function formatPercent(value, decimals = 1) {
  const numericValue = Number(value);

  if (!Number.isFinite(numericValue)) {
    return "-";
  }

  return `${numericValue.toFixed(decimals)}%`;
}

function formatSigned(value, decimals = 2) {
  const numericValue = Number(value);

  if (!Number.isFinite(numericValue)) {
    return "-";
  }

  const sign = numericValue > 0 ? "+" : "";
  return `${sign}${numericValue.toFixed(decimals)}`;
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

function formatRecommendationHtml(value) {
  let items = [];

  if (Array.isArray(value)) {
    items = value;
  } else {
    items = String(value || "")
      .split("|")
      .map((item) => item.trim())
      .filter(Boolean);
  }

  if (!items.length) {
    return "Aquí aparecerá una recomendación personalizada basada en el estilo detectado.";
  }

  return `
    <ul style="margin:0; padding-left:1.2rem; line-height:1.8;">
      ${items.map((item) => `<li>${escapeHtml(cleanText(item))}</li>`).join("")}
    </ul>
  `;
}

function getPlayerUniqueKey(player) {
  return `${safeLower(player.name)}||${safeLower(player.tag)}`;
}

function normalizeChartValue(value, maxValue) {
  const numericValue = Number(value);

  if (!Number.isFinite(numericValue) || !Number.isFinite(maxValue) || maxValue <= 0) {
    return 0;
  }

  return Math.max(0, Math.min(100, (numericValue / maxValue) * 100));
}

async function loadData() {
  const response = await fetch("./web_data.json");

  if (!response.ok) {
    throw new Error("No se pudo cargar web_data.json");
  }

  state.data = await response.json();
}

function getEligiblePlayers() {
  if (!state.data || !Array.isArray(state.data.players)) {
    return [];
  }

  return state.data.players.filter(
    (player) => player.eligible_for_ranking === true
  );
}

function fillProfileChips() {
  const chipsWrap = byId("profileChips");

  if (!chipsWrap || !state.data) {
    return;
  }

  const names = Object.values(state.data.cluster_names || {});

  chipsWrap.innerHTML = names
    .map(
      (name) => `
        <span class="profile-chip" style="color:${PROFILE_COLORS[name] || "#fff"};">
          ${escapeHtml(cleanText(name))}
        </span>
      `
    )
    .join("");
}

function fillSearchOptions() {
  const datalist = byId("playerOptions");

  if (!datalist || !state.data || !Array.isArray(state.data.players)) {
    return;
  }

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
      (player) => `
        <option value="${escapeHtml(cleanText(player.name))}">
          ${escapeHtml(cleanText(player.name))} ${escapeHtml(cleanText(player.tag))}
        </option>
      `
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
  state.currentAnalysis = null;

  const searchInput = byId("playerSearch");

  if (searchInput) {
    searchInput.value = "";
  }
}

function findPlayer(searchText) {
  if (!state.data || !Array.isArray(state.data.players)) {
    return null;
  }

  const players = state.data.players;
  const q = safeLower(searchText).trim();

  if (!q) return null;

  const exact = players.find(
    (player) =>
      safeLower(player.name) === q ||
      safeLower(player.tag) === q ||
      safeLower(`${player.name} ${player.tag}`) === q ||
      safeLower(`${player.name}#${String(player.tag || "").replace("#", "")}`) === q
  );

  if (exact) return exact;

  return players.find(
    (player) =>
      safeLower(player.name).includes(q) ||
      safeLower(player.tag).includes(q) ||
      safeLower(`${player.name} ${player.tag}`).includes(q)
  );
}

function buildAnalysisExplanationItems(analysis) {
  const prediction = analysis.prediction_summary || {};
  const rankContext = analysis.rank_context || {};
  const filterInfo = rankContext.filter_info || {};

  const items = [];

  if (prediction.competitive_status) {
    items.push({
      title: "Estado competitivo",
      text: prediction.competitive_status,
    });
  }

  if (prediction.trend_explanation) {
    items.push({
      title: "Tendencia reciente",
      text: prediction.trend_explanation,
    });
  }

  if (rankContext.target_avg_team_rank_nearest) {
    items.push({
      title: "Comparación por lobby",
      text: `La media de lobby analizada es ${rankContext.target_avg_team_rank_nearest}. Por eso se compara contra referentes del grupo ${rankContext.target_avg_team_rank_group || "similar"}.`,
    });
  }

  if (filterInfo.message) {
    items.push({
      title: "Base de referencia",
      text: filterInfo.message,
    });
  }

  return items;
}

function buildAnalysisExplanation(analysis) {
  return buildAnalysisExplanationItems(analysis)
    .map((item) => item.text)
    .join(" ");
}

function mapAnalysisToPlayer(analysis) {
  const player = analysis.player || {};
  const summary = analysis.summary || {};
  const prediction = analysis.prediction_summary || {};

  return {
    name: player.name || "Unknown",
    tag: player.tag ? `#${String(player.tag).replace("#", "")}` : "",
    player_type: prediction.main_style || "Unknown",
    secondary_profile: prediction.secondary_style || "Unknown",
    profile_mix: `${prediction.performance_level || "Sin predicción"} · ${prediction.trend_status || "Sin tendencia"}`,
    kills: summary.total_kills,
    deaths: summary.total_deaths,
    assists: summary.total_assists,
    kd_ratio: summary.recent_kd,
    headshot_percent: summary.recent_hs,
    win_percent: summary.winrate,
    profile_explanation: buildAnalysisExplanation(analysis),
    profile_explanation_items: buildAnalysisExplanationItems(analysis),
    recommendation: analysis.recommendations || [],
  };
}

function formatProfileExplanationHtml(player) {
  const items = Array.isArray(player.profile_explanation_items)
    ? player.profile_explanation_items
    : [];

  if (!items.length) {
    return escapeHtml(cleanText(player.profile_explanation || "-"));
  }

  return `
    <div class="profile-explanation-grid">
      ${items
        .map(
          (item) => `
            <div class="profile-explanation-item">
              <span>${escapeHtml(cleanText(item.title))}</span>
              <p>${escapeHtml(cleanText(item.text))}</p>
            </div>
          `
        )
        .join("")}
    </div>
  `;
}

function renderPlayerInfo(player) {
  byId("playerName").textContent = cleanText(player.name || "Unknown");
  byId("playerTag").textContent = cleanText(player.tag || "Unknown");

  byId("primaryProfile").textContent = cleanText(player.player_type || "-");
  byId("secondaryProfile").textContent = cleanText(player.secondary_profile || "-");
  byId("profileMix").textContent = cleanText(player.profile_mix || "-");

  byId("killsValue").textContent = formatNumber(player.kills);
  byId("deathsValue").textContent = formatNumber(player.deaths);
  byId("assistsValue").textContent = formatNumber(player.assists);
  byId("kdValue").textContent = formatNumber(player.kd_ratio, 2);
  byId("hsValue").textContent = formatPercent(player.headshot_percent, 1);
  byId("winValue").textContent = formatPercent(player.win_percent, 1);

  byId("profileExplanation").innerHTML = formatProfileExplanationHtml(player);
  byId("recommendationText").innerHTML = formatRecommendationHtml(player.recommendation);
}

function ensureDynamicAnalysisSection() {
  let section = byId("dynamicAnalysisSection");

  

  if (section) {
    return section;
  }

  section = document.createElement("section");
  section.id = "dynamicAnalysisSection";
  section.classList.add("page-view-section", "view-analyzer");
section.classList.remove("hidden-view");
  section.style.marginTop = "26px";

  const analyzer = byId("analyzer");
  const topBoards = byId("topBoardsWrap");

  if (analyzer && analyzer.parentNode) {
    analyzer.parentNode.insertBefore(section, analyzer.nextSibling);
  } else if (topBoards && topBoards.parentNode) {
    topBoards.parentNode.insertBefore(section, topBoards);
  } else {
    document.body.appendChild(section);
  }

  return section;
}

function clearDynamicAnalysisSection() {
  const section = byId("dynamicAnalysisSection");

  if (section) {
    section.innerHTML = "";
    section.style.display = "none";
  }
}

function renderEmptyState() {
  byId("playerName").textContent = "Ingresa un jugador";
  byId("playerTag").textContent = "Busca por Riot ID, por ejemplo PoloGB#LAS";

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
    "Aquí aparecerá una interpretación del perfil cuando selecciones o analices un jugador.";

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
      Ingresa un jugador para ver sus atributos comparados con el promedio global o con su grupo similar.
    </div>
  `;

  clearDynamicAnalysisSection();
}

function renderPlayerRadar(player) {
  const chartEl = byId("playerRadarChart");
  chartEl.innerHTML = "";

  const profileSummary = state.data.profile_summary.find(
    (profile) => profile.player_type === player.player_type
  );

  const radarLabels = RADAR_FEATURES.map((feature) => formatFeatureLabel(feature));
  const playerValues = RADAR_FEATURES.map((key) => Number(player[key]));
  const profileValues = RADAR_FEATURES.map((key) =>
    profileSummary ? Number(profileSummary[key]) : 0
  );

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
      name: `Promedio ${cleanText(player.player_type)}`,
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

  const layout = getBaseRadarLayout();

  Plotly.newPlot(chartEl, data, layout, {
    responsive: true,
    displaylogo: false,
    displayModeBar: false,
    scrollZoom: false,
  });
}

function getBaseRadarLayout() {
  return {
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
}

function renderAnalysisRadar(analysis) {
  const chartEl = byId("playerRadarChart");
  chartEl.innerHTML = "";

  const summary = analysis.summary || {};
  const similar = analysis.similar_group_summary || {};
  const player = analysis.player || {};
  const prediction = analysis.prediction_summary || {};

  const labels = [
    "ACS",
    "ADR",
    "K/D",
    "KAST",
    "Winrate",
    "DDA",
    "Entry Success",
  ];

  const playerValues = [
    normalizeChartValue(summary.recent_acs, 300),
    normalizeChartValue(summary.recent_adr, 200),
    normalizeChartValue(summary.recent_kd, 2),
    Number(summary.recent_kast || 0),
    Number(summary.winrate || 0),
    normalizeChartValue(summary.recent_dda, 80),
    Number(summary.recent_entry_success || 0),
  ];

  const similarValues = [
    normalizeChartValue(similar.avg_acs, 300),
    normalizeChartValue(similar.avg_adr, 200),
    normalizeChartValue(similar.avg_kd, 2),
    Number(similar.avg_kast || 0),
    Number(similar.avg_winrate || 0),
    normalizeChartValue(similar.avg_dda, 80),
    Number(similar.avg_entry_success || 0),
  ];

  const mainStyle = prediction.main_style || "Balanceado";
  const mainColor = PROFILE_COLORS[mainStyle] || "#8b92ff";

  const data = [
    {
      type: "scatterpolar",
      r: playerValues,
      theta: labels,
      fill: "toself",
      name: cleanText(player.riot_id || player.name || "Jugador"),
      line: {
        color: mainColor,
        width: 3,
      },
      marker: {
        size: 6,
        color: mainColor,
      },
      fillcolor: "rgba(139,146,255,0.18)",
      hovertemplate: "<b>%{theta}</b><br>Valor normalizado: %{r:.1f}<extra></extra>",
    },
    {
      type: "scatterpolar",
      r: similarValues,
      theta: labels,
      fill: "toself",
      name: "Grupo similar",
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
      hovertemplate: "<b>%{theta}</b><br>Grupo similar: %{r:.1f}<extra></extra>",
    },
  ];

  Plotly.newPlot(chartEl, data, getBaseRadarLayout(), {
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

  Plotly.newPlot(chartEl, data, getBaseBarLayout("Valor", [0, 100]), {
    responsive: true,
    displaylogo: false,
    displayModeBar: false,
    scrollZoom: false,
  });
}

function renderAnalysisComparisonChart(analysis) {
  const chartEl = byId("playerComparisonChart");
  chartEl.innerHTML = "";

  const summary = analysis.summary || {};
  const similar = analysis.similar_group_summary || {};
  const player = analysis.player || {};
  const prediction = analysis.prediction_summary || {};

  const labels = [
    "ACS",
    "ADR",
    "K/D",
    "KAST",
    "Winrate",
    "Entry Success",
  ];

  const playerValues = [
    Number(summary.recent_acs || 0),
    Number(summary.recent_adr || 0),
    Number(summary.recent_kd || 0),
    Number(summary.recent_kast || 0),
    Number(summary.winrate || 0),
    Number(summary.recent_entry_success || 0),
  ];

  const similarValues = [
    Number(similar.avg_acs || 0),
    Number(similar.avg_adr || 0),
    Number(similar.avg_kd || 0),
    Number(similar.avg_kast || 0),
    Number(similar.avg_winrate || 0),
    Number(similar.avg_entry_success || 0),
  ];

  const mainStyle = prediction.main_style || "Balanceado";
  const mainColor = PROFILE_COLORS[mainStyle] || "#8b92ff";

  const data = [
    {
      type: "bar",
      x: labels,
      y: playerValues,
      name: cleanText(player.riot_id || player.name || "Jugador"),
      marker: {
        color: mainColor,
      },
      hovertemplate: "<b>%{x}</b><br>Jugador: %{y:.2f}<extra></extra>",
    },
    {
      type: "bar",
      x: labels,
      y: similarValues,
      name: "Grupo similar",
      marker: {
        color: "#a5afc3",
      },
      hovertemplate: "<b>%{x}</b><br>Grupo similar: %{y:.2f}<extra></extra>",
    },
  ];

  Plotly.newPlot(chartEl, data, getBaseBarLayout("Valor", null), {
    responsive: true,
    displaylogo: false,
    displayModeBar: false,
    scrollZoom: false,
  });
}

function getBaseBarLayout(yTitle, yRange) {
  return {
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
        text: yTitle,
        font: {
          family: "Inter, sans-serif",
          size: 15,
          color: "#eef2ff",
        },
      },
      range: yRange || undefined,
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
}

function renderTopBoards() {
  const wrap = byId("topBoardsWrap");

  if (!wrap || !state.data) {
    return;
  }

  const boardsHtml = PROFILE_ORDER.map((profile) => {
    const players = getTopPlayersByProfile(profile, 10);

    const rows = players
      .map(
        (player, index) => `
          <tr data-player="${escapeHtml(player.name)}">
            <td>#${index + 1}</td>
            <td>
              <strong>${escapeHtml(cleanText(player.name))}</strong><br>
              <span class="muted">${escapeHtml(cleanText(player.tag))}</span>
            </td>
            <td>${formatNumber(player.profile_score, 2)}</td>
            <td>${formatNumber(player.kd_ratio, 2)}</td>
            <td>${formatPercent(player.headshot_percent, 1)}</td>
            <td>${formatPercent(player.win_percent, 1)}</td>
            <td>${formatNumber(player.wins)}</td>
          </tr>
        `
      )
      .join("");

    return `
      <div class="glass-card" style="padding:18px;">
        <div class="card-title-wrap" style="padding:4px 4px 14px;">
          <h3 style="margin:0; color:${PROFILE_COLORS[profile] || "#fff"};">Top ${escapeHtml(profile)}</h3>
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
        state.currentAnalysis = null;
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

function renderAnalysisExtraSections(analysis) {
  const section = ensureDynamicAnalysisSection();
  const player = analysis.player || {};
  const summary = analysis.summary || {};
  const prediction = analysis.prediction_summary || {};
  const rankContext = analysis.rank_context || {};
  const similarSummary = analysis.similar_group_summary || {};
  const gap = analysis.gap_analysis || {};
  const similarPlayers = analysis.similar_players || [];
  const matches = analysis.matches || [];
  const methodology = analysis.methodology || {};
  const temporal = analysis.temporal_evolution || {};
const previousHalf = temporal.previous_half || {};
const recentHalf = temporal.recent_half || {};
const deltas = temporal.deltas || {};

  section.style.display = "block";

  const similarRows = similarPlayers
    .slice(0, 10)
    .map(
      (item) => `
        <tr>
          <td>#${item.rank}</td>
          <td>
            <strong>${escapeHtml(cleanText(item.reference_riot_id))}</strong><br>
            <span class="muted">Lobby ${escapeHtml(cleanText(item.avg_team_rank_nearest))}</span>
          </td>
          <td>${formatNumber(item.recent_kd, 2)}</td>
          <td>${formatNumber(item.recent_acs, 1)}</td>
          <td>${formatPercent(item.winrate, 1)}</td>
          <td>${escapeHtml(cleanText(item.main_agent))}</td>
        </tr>
      `
    )
    .join("");

  const matchRows = matches
    .map(
      (match) => `
        <tr>
          <td>#${match.match_number}</td>
          <td>
            <strong>${escapeHtml(cleanText(match.map))}</strong><br>
            <span class="muted">${escapeHtml(cleanText(match.agent))}</span>
          </td>
          <td>${escapeHtml(cleanText(match.result))}</td>
          <td>${formatNumber(match.acs, 0)}</td>
          <td>${formatNumber(match.kills, 0)}/${formatNumber(match.deaths, 0)}/${formatNumber(match.assists, 0)}</td>
          <td>${escapeHtml(cleanText(match.performance_prediction))}</td>
          <td>${escapeHtml(cleanText(match.style_prediction))}</td>
          <td>${escapeHtml(cleanText(match.trend_signal))}</td>
        </tr>
      `
    )
    .join("");

  section.innerHTML = `
    <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(220px, 1fr)); gap:16px; margin-bottom:18px;">
      <div class="glass-card" style="padding:20px;">
        <span class="section-kicker">Rendimiento</span>
        <h3 style="margin:8px 0 0;">${escapeHtml(cleanText(prediction.performance_level || "-"))}</h3>
        <p class="muted" style="margin:8px 0 0;">${escapeHtml(cleanText(prediction.competitive_status || ""))}</p>
      </div>

      <div class="glass-card" style="padding:20px;">
        <span class="section-kicker">Tendencia</span>
        <h3 style="margin:8px 0 0;">${escapeHtml(cleanText(prediction.trend_status || "-"))}</h3>
        <p class="muted" style="margin:8px 0 0;">Puntaje: ${formatNumber(prediction.trend_numeric_score, 0)}</p>
      </div>

      <div class="glass-card" style="padding:20px;">
        <span class="section-kicker">Media de lobby</span>
        <h3 style="margin:8px 0 0;">${escapeHtml(cleanText(rankContext.target_avg_team_rank_nearest || "-"))}</h3>
        <p class="muted" style="margin:8px 0 0;">Grupo: ${escapeHtml(cleanText(rankContext.target_avg_team_rank_group || "-"))}</p>
      </div>

      <div class="glass-card" style="padding:20px;">
        <span class="section-kicker">Grupo similar</span>
        <h3 style="margin:8px 0 0;">${formatNumber(similarSummary.players_compared, 0)} referentes</h3>
        <p class="muted" style="margin:8px 0 0;">Winrate prom.: ${formatPercent(similarSummary.avg_winrate, 1)}</p>
      </div>
    </div>

    <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(280px, 1fr)); gap:16px; margin-bottom:18px;">
      <div class="glass-card" style="padding:20px;">
        <span class="section-kicker">Brechas vs grupo similar</span>
        <h3 style="margin:8px 0 14px;">Comparación por lobby similar</h3>
        <div style="display:grid; grid-template-columns:repeat(2, minmax(0, 1fr)); gap:10px;">
          <span class="mini-badge">K/D ${formatSigned(gap.kd_gap, 3)}</span>
          <span class="mini-badge">ACS ${formatSigned(gap.acs_gap, 2)}</span>
          <span class="mini-badge">ADR ${formatSigned(gap.adr_gap, 2)}</span>
          <span class="mini-badge">KAST ${formatSigned(gap.kast_gap, 2)}</span>
          <span class="mini-badge">Winrate ${formatSigned(gap.winrate_gap, 2)}</span>
          <span class="mini-badge">Entry ${formatSigned(gap.entry_success_gap, 2)}</span>
        </div>
      </div>
    </div>

    <div class="glass-card" style="padding:20px; margin-bottom:18px;">
      <div class="card-title-wrap" style="padding:0 0 14px;">
        <h3 style="margin:0;">Referentes similares por media de lobby</h3>
        <span class="mini-badge">${escapeHtml(cleanText(rankContext.filter_info?.message || "Comparación por rango de partida"))}</span>
      </div>

      <div class="table-wrap">
        <table class="players-table">
          <thead>
            <tr>
              <th>#</th>
              <th>Referente</th>
              <th>K/D</th>
              <th>ACS</th>
              <th>Win%</th>
              <th>Agente</th>
            </tr>
          </thead>
          <tbody>
            ${similarRows || `<tr><td colspan="6">No hay suficientes referentes similares para este rango.</td></tr>`}
          </tbody>
        </table>
      </div>
    </div>

    <div class="glass-card" style="padding:20px;">
      <div class="card-title-wrap" style="padding:0 0 14px;">
        <h3 style="margin:0;">Predicción por partida</h3>
        <span class="mini-badge">${formatNumber(matches.length, 0)} partidas</span>
      </div>

      <div class="table-wrap">
        <table class="players-table">
          <thead>
            <tr>
              <th>#</th>
              <th>Mapa / Agente</th>
              <th>Resultado</th>
              <th>ACS</th>
              <th>K/D/A</th>
              <th>Rendimiento</th>
              <th>Estilo</th>
              <th>Tendencia</th>
            </tr>
          </thead>
          <tbody>
            ${matchRows || `<tr><td colspan="8">No hay partidas recientes disponibles.</td></tr>`}
          </tbody>
        </table>
      </div>
    </div>
  `;
}

function renderSelectedPlayer() {
  if (state.currentAnalysis) {
    const analysisPlayer = mapAnalysisToPlayer(state.currentAnalysis);

    renderPlayerInfo(analysisPlayer);
    renderAnalysisRadar(state.currentAnalysis);
    renderAnalysisComparisonChart(state.currentAnalysis);
    renderAnalysisExtraSections(state.currentAnalysis);
    return;
  }

  if (!state.selectedPlayer) {
    renderEmptyState();
    return;
  }

  renderPlayerInfo(state.selectedPlayer);
  renderPlayerRadar(state.selectedPlayer);
  renderPlayerComparisonChart(state.selectedPlayer);
  clearDynamicAnalysisSection();
}

let loadingTimer = null;
let loadingStartedAt = null;

function ensureLoadingOverlay() {
  let overlay = byId("analysisLoadingOverlay");

  if (overlay) {
    return overlay;
  }

  overlay = document.createElement("div");
  overlay.id = "analysisLoadingOverlay";

  overlay.innerHTML = `
    <div style="
      width:min(560px, calc(100vw - 36px));
      background:linear-gradient(145deg, rgba(18,22,42,0.98), rgba(35,25,48,0.98));
      border:1px solid rgba(255,255,255,0.12);
      box-shadow:0 30px 80px rgba(0,0,0,0.45);
      border-radius:28px;
      padding:30px;
      color:#f5f7ff;
      font-family:Inter, sans-serif;
      text-align:left;
    ">
      <div style="
        width:52px;
        height:52px;
        border-radius:18px;
        display:flex;
        align-items:center;
        justify-content:center;
        background:linear-gradient(135deg, #ff6b6b, #7c83ff);
        font-weight:900;
        font-size:24px;
        margin-bottom:18px;
      ">V</div>

      <p style="
        margin:0 0 8px;
        letter-spacing:0.18em;
        text-transform:uppercase;
        color:#aeb8d3;
        font-size:13px;
        font-weight:800;
      ">Analizando jugador</p>

      <h2 id="loadingTitle" style="
        margin:0 0 12px;
        font-size:30px;
        line-height:1.1;
      ">Procesando partidas recientes</h2>

      <p id="loadingMessage" style="
        margin:0;
        color:#c4cce0;
        font-size:17px;
        line-height:1.6;
      ">
        Extrayendo partidas competitivas desde Tracker.gg y ejecutando los modelos.
      </p>

      <div style="
        margin-top:22px;
        height:10px;
        border-radius:999px;
        background:rgba(255,255,255,0.08);
        overflow:hidden;
      ">
        <div style="
          width:42%;
          height:100%;
          border-radius:999px;
          background:linear-gradient(90deg, #ff7a59, #8b92ff);
          animation:valoLoadingBar 1.2s ease-in-out infinite alternate;
        "></div>
      </div>

      <p id="loadingTime" style="
        margin:16px 0 0;
        color:#9fa9c3;
        font-size:14px;
      ">Tiempo transcurrido: 0s</p>

      <p style="
        margin:10px 0 0;
        color:#8f99b5;
        font-size:13px;
        line-height:1.5;
      ">
        Este proceso puede tardar algunos minutos porque se abren y analizan varias partidas reales.
      </p>
    </div>
  `;

  overlay.style.cssText = `
    position:fixed;
    inset:0;
    z-index:9999;
    background:rgba(3,6,18,0.72);
    backdrop-filter:blur(10px);
    display:none;
    align-items:center;
    justify-content:center;
    padding:24px;
  `;

  const style = document.createElement("style");
  style.textContent = `
    @keyframes valoLoadingBar {
      from { transform: translateX(-45%); }
      to { transform: translateX(145%); }
    }
  `;

  document.head.appendChild(style);
  document.body.appendChild(overlay);

  return overlay;
}

function showLoadingOverlay(message = "Extrayendo partidas competitivas y ejecutando modelos.") {
  const overlay = ensureLoadingOverlay();
  const loadingMessage = byId("loadingMessage");
  const loadingTime = byId("loadingTime");

  overlay.style.display = "flex";

  if (loadingMessage) {
    loadingMessage.textContent = message;
  }

  loadingStartedAt = Date.now();

  if (loadingTimer) {
    clearInterval(loadingTimer);
  }

  loadingTimer = setInterval(() => {
    const elapsedSeconds = Math.floor((Date.now() - loadingStartedAt) / 1000);

    if (loadingTime) {
      loadingTime.textContent = `Tiempo transcurrido: ${elapsedSeconds}s`;
    }
  }, 1000);
}

function hideLoadingOverlay() {
  const overlay = byId("analysisLoadingOverlay");

  if (overlay) {
    overlay.style.display = "none";
  }

  if (loadingTimer) {
    clearInterval(loadingTimer);
    loadingTimer = null;
  }

  loadingStartedAt = null;
}

function setAnalyzeLoading(isLoading, message = "Analizando...") {
  state.isAnalyzing = isLoading;

  const button = byId("analyzeBtn");
  const input = byId("playerSearch");

  if (button) {
    button.disabled = isLoading;
    button.dataset.originalText = button.dataset.originalText || button.textContent;
    button.textContent = isLoading ? message : button.dataset.originalText;
  }

  if (input) {
    input.disabled = isLoading;
  }

  if (isLoading) {
    showLoadingOverlay(
      "Buscando el perfil, extrayendo partidas competitivas recientes y ejecutando predicciones de rendimiento, estilo, tendencia y jugadores similares."
    );

    byId("profileExplanation").textContent =
      "Ejecutando análisis completo. Esto puede demorar algunos minutos porque se procesan partidas reales desde Tracker.gg.";

    byId("recommendationText").innerHTML =
      "Cuando termine el proceso, aparecerán las recomendaciones personalizadas del jugador.";
  } else {
    hideLoadingOverlay();
  }
}

async function loadStaticFinalAnalysis(riotId) {
  const response = await fetch("./final_player_analysis.json");

  if (!response.ok) {
    throw new Error("No se pudo cargar final_player_analysis.json");
  }

  const analysis = await response.json();

  const requested = safeLower(riotId).replace(/\s+/g, "");
  const player = analysis.player || {};
  const storedRiotId = safeLower(
    player.riot_id || `${player.name || ""}#${String(player.tag || "").replace("#", "")}`
  ).replace(/\s+/g, "");

  if (storedRiotId && requested !== storedRiotId) {
    throw new Error(
      `La demo pública tiene cargado ${player.riot_id || storedRiotId}, no ${riotId}.`
    );
  }

  state.currentAnalysis = analysis;
  state.selectedPlayer = null;

  renderSelectedPlayer();

  setTimeout(() => {
    byId("analyzer").scrollIntoView({
      behavior: "smooth",
      block: "start",
    });
  }, 80);
}

async function analyzeRiotIdWithBackend(riotId) {
  if (IS_GITHUB_PAGES) {
    try {
      await loadStaticFinalAnalysis(riotId);
      return;
    } catch (error) {
      alert(
        "Esta versión pública funciona con un jugador precargado. " +
        error.message +
        " Para scraping en vivo se debe ejecutar el backend local."
      );
      return;
    }
  }

  setAnalyzeLoading(true, "Analizando...");

  try {
    const response = await fetch(API_ANALYZE_URL, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        riot_id: riotId,
        skip_scraper: false,
        refresh_reference: false,
      }),
    });

    const payload = await response.json().catch(() => ({}));

    if (!response.ok) {
      const detail = payload.detail || "No se pudo ejecutar el análisis.";
      throw new Error(detail);
    }

    state.currentAnalysis = payload.analysis;
    state.selectedPlayer = null;

    renderSelectedPlayer();

    setTimeout(() => {
      byId("analyzer").scrollIntoView({
        behavior: "smooth",
        block: "start",
      });
    }, 80);
  } finally {
    setAnalyzeLoading(false);
  }
}

function showMainView(viewName) {
  const allSections = document.querySelectorAll(".page-view-section");
  const allTabs = document.querySelectorAll(".nav-tab");

  allSections.forEach((section) => {
    section.classList.add("hidden-view");
  });

  document.querySelectorAll(`.view-${viewName}`).forEach((section) => {
    section.classList.remove("hidden-view");
  });

  allTabs.forEach((tab) => {
    tab.classList.toggle("active", tab.dataset.view === viewName);
  });

  window.scrollTo({
    top: 0,
    behavior: "smooth",
  });
}

function bindViewTabs() {
  document.querySelectorAll(".nav-tab").forEach((tab) => {
    tab.addEventListener("click", () => {
      const viewName = tab.dataset.view;
      showMainView(viewName);
    });
  });
}

function bindEvents() {
  async function runSearchAndFocusAnalysis() {
    if (state.isAnalyzing) {
      return;
    }

    const query = byId("playerSearch").value.trim();

    if (!query) {
      alert("Ingresa un jugador. Para análisis en vivo usa formato Nombre#Tag, por ejemplo PoloGB#LAS.");
      return;
    }

    if (query.includes("#")) {
      try {
        await analyzeRiotIdWithBackend(query);
      } catch (error) {
        console.error(error);
        alert(`No se pudo analizar el jugador: ${error.message}`);
      }

      byId("playerSearch").blur();
      return;
    }

    const player = findPlayer(query);

    if (!player) {
      alert("No se encontró un jugador con ese nombre. Para análisis en vivo usa formato Nombre#Tag.");
      return;
    }

    state.selectedPlayer = player;
    state.currentAnalysis = null;
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

function renderInfoModelCard() {
  const infoSection = byId("methodology") || document.querySelector(".view-info");

  if (!infoSection || byId("infoModelReadingCard")) {
    return;
  }

  const card = document.createElement("div");
  card.id = "infoModelReadingCard";
  card.className = "glass-card";
  card.style.padding = "28px";
  card.style.marginTop = "22px";
  card.style.marginBottom = "22px";

  card.innerHTML = `
    <span class="section-kicker">Lectura del modelo</span>
    <h3 style="margin:8px 0 14px;">Qué está prediciendo</h3>
    <p class="muted" style="margin:0; line-height:1.7;">
      El modelo utiliza las últimas 20 partidas competitivas del jugador para estimar su rendimiento reciente, estilo de juego predominante, tendencia competitiva y similitud con jugadores de referencia. En la versión pública, este análisis se muestra desde un archivo previamente generado.
    </p>
  `;

  const header = infoSection.querySelector(".section-header");

  if (header) {
    header.insertAdjacentElement("afterend", card);
  } else {
    infoSection.prepend(card);
  }
}

async function init() {
  try {
    await loadData();
    fillProfileChips();
    fillSearchOptions();
    pickDefaultPlayer();
    bindEvents();
    bindViewTabs();
    renderSelectedPlayer();
renderTopBoards();
renderInfoModelCard();
  } catch (error) {
    console.error(error);
    document.body.innerHTML = `
      <main style="padding:40px; color:white; font-family:Inter, sans-serif;">
        <h1>Error cargando Valostats</h1>
        <p>No se pudo cargar <code>web_data.json</code>. Abre la página desde <code>http://localhost:8000</code> o desde GitHub Pages.</p>
      </main>
    `;
  }
}

init();
