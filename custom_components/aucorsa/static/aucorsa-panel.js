const AUCORSA_LOGO_URL = "https://cdn.aucorsa.es/wp-content/uploads/2023/05/logo-aucorsa.svg";
const LEGACY_PANEL_SUBTITLES = new Set([
  "Tiempos de llegada desde los sensores ya cargados",
  "Visual panel based on the integration sensors",
  "Panel visual basado en los sensores de la integracion",
  "Panel visual basado en los sensores de la integración",
]);

const DEFAULT_LINE_COLORS = {
  "1": "#1f7a57",
  "2": "#e41019",
  "3": "#9d6bb1",
  "4": "#e993c5",
  "5": "#11589d",
  "6": "#54b8e8",
  "7": "#f58220",
  "8": "#ffca1c",
  "9": "#e61d7f",
  "10": "#e8de49",
  "11": "#2f95d0",
  "12": "#65b147",
  "13": "#b3722a",
  "14": "#764615",
  "C2": "#f39473",
  "46": "#f59a00",
};

const lineSorter = new Intl.Collator("es", { numeric: true, sensitivity: "base" });

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function normalizeMinutes(value) {
  if (value === null || value === undefined) {
    return null;
  }

  const text = String(value).trim();
  if (!text || text === "unknown" || text === "unavailable") {
    return null;
  }

  const parsed = Number.parseInt(text, 10);
  return Number.isNaN(parsed) ? null : parsed;
}

function minutesLabel(value, labels) {
  if (value === null) {
    return `<span class="aucorsa-missing">${labels.noEstimate}</span>`;
  }

  if (value === 1) {
    return `<strong>1 ${labels.minute}</strong>`;
  }

  return `<strong>${value} ${labels.minutes}</strong>`;
}

function parseDate(rawValue) {
  if (!rawValue) {
    return null;
  }

  const parsed = new Date(rawValue);
  return Number.isNaN(parsed.getTime()) ? null : parsed;
}

function getLanguage(hass) {
  return (
    hass?.locale?.language ||
    hass?.language ||
    document.documentElement.lang ||
    navigator.language ||
    "es"
  );
}

function isSpanish(language) {
  return String(language || "").toLowerCase().startsWith("es");
}

function getTexts(language) {
  if (!isSpanish(language)) {
    return {
      title: "Aucorsa",
      subtitle: "Arrival times by stop",
      emptyTitle: "No Aucorsa data available",
      emptyBody:
        "Add one or more Aucorsa integration entries to generate sensors and this view will fill automatically.",
      noRoute: "No route available",
      nextArrival: "Next bus",
      followingArrival: "Following bus",
      refreshNow: "Refresh now",
      refreshing: "Refreshing...",
      noEstimate: "No estimate",
      minute: "minute",
      minutes: "minutes",
      updatedPrefix: "Updated",
      notUpdated: "Not updated yet",
      createdBy: "Created by",
      githubLabel: "@rafasanz",
      cardTitleDefault: "Aucorsa stop",
      chooseStop: "Stop",
      showHeader: "Show header",
      showRefresh: "Show refresh button",
      titleLabel: "Title",
      subtitleLabel: "Subtitle",
      noStops: "No Aucorsa stops available yet.",
    };
  }

  return {
    title: "Aucorsa",
    subtitle: "Tiempos de llegada por parada",
    emptyTitle: "No hay datos de Aucorsa disponibles",
    emptyBody:
      "Añade una o más entradas de la integración Aucorsa para generar sensores y esta vista se rellenará automáticamente.",
    noRoute: "Sin ruta disponible",
    nextArrival: "Próximo autobús",
    followingArrival: "Siguiente autobús",
    refreshNow: "Actualizar ahora",
    refreshing: "Actualizando...",
    noEstimate: "Sin estimación",
    minute: "minuto",
    minutes: "minutos",
    updatedPrefix: "Actualizado",
    notUpdated: "Sin actualizar todavía",
    createdBy: "Creado por",
    githubLabel: "@rafasanz",
    cardTitleDefault: "Parada Aucorsa",
    chooseStop: "Parada",
    showHeader: "Mostrar cabecera",
    showRefresh: "Mostrar botón de actualización",
    titleLabel: "Título",
    subtitleLabel: "Subtítulo",
    noStops: "Aún no hay paradas de Aucorsa disponibles.",
  };
}

function formatRelativeTime(date, language, labels) {
  if (!date) {
    return labels.notUpdated;
  }

  const diffSeconds = Math.round((date.getTime() - Date.now()) / 1000);
  const absSeconds = Math.abs(diffSeconds);

  let value = diffSeconds;
  let unit = "second";

  if (absSeconds >= 86400) {
    value = Math.round(diffSeconds / 86400);
    unit = "day";
  } else if (absSeconds >= 3600) {
    value = Math.round(diffSeconds / 3600);
    unit = "hour";
  } else if (absSeconds >= 60) {
    value = Math.round(diffSeconds / 60);
    unit = "minute";
  }

  return new Intl.RelativeTimeFormat(language, { numeric: "auto" }).format(value, unit);
}

function refreshIconMarkup() {
  return `
    <svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">
      <path d="M12 6V3L8 7l4 4V8c2.76 0 5 2.24 5 5a5 5 0 0 1-8.66 3.54l-1.42 1.42A7 7 0 0 0 19 13c0-3.87-3.13-7-7-7Zm-5 5a5 5 0 0 1 8.66-3.54l1.42-1.42A7 7 0 0 0 5 11c0 3.87 3.13 7 7 7v3l4-4-4-4v3c-2.76 0-5-2.24-5-5Z"/>
    </svg>
  `;
}

function configuredStopIds(config) {
  if (config?.stop_id) {
    return new Set([String(config.stop_id)]);
  }

  return new Set((config?.stop_ids || []).map((stopId) => String(stopId)));
}

function collectAvailableStops(hass) {
  if (!hass) {
    return [];
  }

  const stops = new Map();
  for (const stateObj of Object.values(hass.states)) {
    const attrs = stateObj.attributes || {};
    if (!attrs.aucorsa_managed) {
      continue;
    }

    const stopId = String(attrs.stop_id || "").trim();
    if (!stopId) {
      continue;
    }

    const stopLabel = String(attrs.stop_label || stateObj.state || `Parada ${stopId}`).trim();
    if (!stops.has(stopId) || stopLabel.length > String(stops.get(stopId).label).length) {
      stops.set(stopId, {
        value: stopId,
        label: stopLabel || `Parada ${stopId}`,
      });
    }
  }

  return Array.from(stops.values()).sort((left, right) =>
    lineSorter.compare(left.value, right.value)
  );
}

function collectViewModel(hass, config) {
  if (!hass) {
    return {
      integrationVersion: "",
      lastUpdated: null,
      refreshEntityIds: [],
      stops: [],
    };
  }

  const allowedStopIds = configuredStopIds(config);
  const stops = new Map();
  const refreshEntityIds = [];
  let integrationVersion = "";
  let lastUpdated = null;

  for (const [entityId, stateObj] of Object.entries(hass.states)) {
    const attrs = stateObj.attributes || {};
    if (!attrs.aucorsa_managed) {
      continue;
    }

    const stopId = String(attrs.stop_id || "").trim();
    if (!stopId) {
      continue;
    }

    if (allowedStopIds.size > 0 && !allowedStopIds.has(stopId)) {
      continue;
    }

    const version = String(attrs.integration_version || "").trim();
    if (!integrationVersion && version) {
      integrationVersion = version;
    }

    if (entityId.startsWith("button.") && attrs.aucorsa_button_type === "refresh") {
      refreshEntityIds.push(entityId);
      continue;
    }

    if (!entityId.startsWith("sensor.")) {
      continue;
    }

    const sensorType = String(attrs.aucorsa_sensor_type || "").trim();
    const line = String(attrs.line || "").trim();
    const timestamp = parseDate(stateObj.last_updated || stateObj.last_changed);
    if (timestamp && (!lastUpdated || timestamp > lastUpdated)) {
      lastUpdated = timestamp;
    }

    if (!stops.has(stopId)) {
      stops.set(stopId, {
        stopId,
        stopLabel: String(attrs.stop_label || stateObj.state || `Parada ${stopId}`),
        lines: new Map(),
      });
    }

    const stop = stops.get(stopId);
    if (sensorType === "stop_name") {
      stop.stopLabel = String(stateObj.state || attrs.stop_label || stop.stopLabel);
      continue;
    }

    if (!line || !sensorType) {
      continue;
    }

    const lineKey = `${stopId}::${line}`;
    if (!stop.lines.has(lineKey)) {
      stop.lines.set(lineKey, {
        line,
        route: String(attrs.route || ""),
        lineColor:
          String(attrs.line_color || "").trim() ||
          DEFAULT_LINE_COLORS[line.toUpperCase()] ||
          "#3e8f56",
        next: null,
        following: null,
      });
    }

    const lineEntry = stop.lines.get(lineKey);
    const minutes = normalizeMinutes(stateObj.state);
    if (sensorType === "next") {
      lineEntry.next = minutes;
    } else if (sensorType === "following") {
      lineEntry.following = minutes;
    }
  }

  return {
    integrationVersion,
    lastUpdated,
    refreshEntityIds,
    stops: Array.from(stops.values())
      .map((stop) => ({
        ...stop,
        lines: Array.from(stop.lines.values()).sort((left, right) =>
          lineSorter.compare(left.line, right.line)
        ),
      }))
      .sort((left, right) => lineSorter.compare(left.stopId, right.stopId)),
  };
}

function renderStopsMarkup(stops, labels) {
  if (stops.length === 0) {
    return `
      <section class="aucorsa-empty">
        <h2>${escapeHtml(labels.emptyTitle)}</h2>
        <p>${escapeHtml(labels.emptyBody)}</p>
      </section>
    `;
  }

  return stops
    .map(
      (stop) => `
        <section class="aucorsa-stop-card">
          <header class="aucorsa-stop-header">
            ${escapeHtml(stop.stopLabel).toUpperCase()}
          </header>
          <div class="aucorsa-lines">
            ${stop.lines
              .map(
                (line) => `
                  <article class="aucorsa-line-row" style="--line-color: ${escapeHtml(
                    line.lineColor
                  )}">
                    <div class="aucorsa-line-badge-wrap">
                      <div class="aucorsa-line-badge">${escapeHtml(line.line)}</div>
                      <div class="aucorsa-line-stem"></div>
                    </div>
                    <div class="aucorsa-line-content">
                      <div class="aucorsa-line-route">
                        ${escapeHtml(line.route || labels.noRoute)}
                      </div>
                      <div class="aucorsa-line-estimation">
                        ${escapeHtml(labels.nextArrival)}: ${minutesLabel(line.next, labels)}
                      </div>
                      <div class="aucorsa-line-estimation">
                        ${escapeHtml(labels.followingArrival)}: ${minutesLabel(
                          line.following,
                          labels
                        )}
                      </div>
                    </div>
                  </article>
                `
              )
              .join("")}
          </div>
        </section>
      `
    )
    .join("");
}

function renderPanelMarkup({ hass, config, narrow, refreshing }) {
  const language = getLanguage(hass);
  const labels = getTexts(language);
  const viewModel = collectViewModel(hass, config);
  const refreshDisabled = refreshing || viewModel.refreshEntityIds.length === 0;
  const title = escapeHtml(config?.title || labels.title);
  const subtitle = escapeHtml(
    LEGACY_PANEL_SUBTITLES.has(String(config?.subtitle || "").trim())
      ? labels.subtitle
      : config?.subtitle || labels.subtitle
  );
  const updatedLabel = escapeHtml(formatRelativeTime(viewModel.lastUpdated, language, labels));
  const refreshLabel = refreshing ? labels.refreshing : labels.refreshNow;

  return `
    <style>
      :host {
        color: var(--primary-text-color);
        display: block;
      }

      * {
        box-sizing: border-box;
      }

      .aucorsa-shell {
        min-height: 100vh;
        padding: ${narrow ? "20px 12px 28px" : "32px 24px 40px"};
        background:
          radial-gradient(circle at top left, rgba(101, 177, 71, 0.14), transparent 28%),
          linear-gradient(180deg, #fbfcf7 0%, #eef4ea 100%);
      }

      .aucorsa-inner {
        max-width: 1120px;
        margin: 0 auto;
        min-height: calc(100vh - ${narrow ? "48px" : "72px"});
        display: flex;
        flex-direction: column;
      }

      .aucorsa-head {
        display: flex;
        justify-content: space-between;
        gap: 18px;
        align-items: flex-start;
      }

      .aucorsa-head-copy {
        min-width: 0;
      }

      .aucorsa-title {
        margin: 0;
        font-size: ${narrow ? "30px" : "42px"};
        line-height: 1;
        letter-spacing: -0.03em;
        font-weight: 800;
        color: #1e6f3d;
      }

      .aucorsa-subtitle {
        margin: 10px 0 0;
        color: #5b6a58;
        font-size: 15px;
      }

      .aucorsa-toolbar {
        display: flex;
        flex-direction: column;
        align-items: flex-end;
        gap: 8px;
      }

      .aucorsa-refresh-button {
        border: 0;
        border-radius: 999px;
        background: #1e6f3d;
        color: #fff;
        width: 52px;
        height: 52px;
        padding: 0;
        cursor: pointer;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        box-shadow: 0 12px 24px rgba(30, 111, 61, 0.18);
        transition: transform 140ms ease, opacity 140ms ease, background 140ms ease;
      }

      .aucorsa-refresh-button svg {
        width: 24px;
        height: 24px;
        fill: currentColor;
      }

      .aucorsa-refresh-button:hover {
        transform: translateY(-1px);
        background: #185b32;
      }

      .aucorsa-refresh-button:disabled {
        cursor: default;
        opacity: 0.6;
        transform: none;
        box-shadow: none;
      }

      .aucorsa-updated {
        color: #58705e;
        font-size: 13px;
        font-weight: 700;
      }

      .aucorsa-main {
        flex: 1;
      }

      .aucorsa-grid {
        margin-top: 24px;
        display: grid;
        gap: 18px;
      }

      .aucorsa-footer {
        margin-top: 28px;
        padding: 12px 4px 0;
        display: flex;
        justify-content: space-between;
        gap: 16px;
        align-items: center;
        color: #58705e;
        font-size: 13px;
        font-weight: 700;
      }

      .aucorsa-footer a {
        color: #1e6f3d;
        text-decoration: none;
      }

      .aucorsa-footer a:hover {
        text-decoration: underline;
      }

      .aucorsa-stop-card,
      .aucorsa-empty {
        background: rgba(255, 255, 255, 0.94);
        border: 1px solid rgba(61, 112, 70, 0.1);
        border-radius: 26px;
        box-shadow: 0 18px 50px rgba(37, 68, 45, 0.08);
        overflow: hidden;
      }

      .aucorsa-stop-header {
        padding: 22px 24px 0;
        color: #2c9e32;
        font-size: ${narrow ? "24px" : "34px"};
        line-height: 1.1;
        font-weight: 900;
        text-transform: uppercase;
      }

      .aucorsa-lines {
        padding: 20px 18px 22px;
        display: grid;
        gap: 12px;
      }

      .aucorsa-line-row {
        display: grid;
        grid-template-columns: 78px minmax(0, 1fr);
        gap: 14px;
        align-items: start;
        padding: 8px 10px;
        border-radius: 20px;
      }

      .aucorsa-line-row:hover {
        background: rgba(46, 84, 55, 0.04);
      }

      .aucorsa-line-badge-wrap {
        display: flex;
        flex-direction: column;
        align-items: center;
      }

      .aucorsa-line-badge {
        width: 48px;
        min-height: 48px;
        padding: 6px 8px;
        border-radius: 4px;
        background: var(--line-color);
        color: #fff;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 24px;
        line-height: 1;
        font-weight: 800;
        box-shadow: 0 10px 20px color-mix(in srgb, var(--line-color) 28%, transparent);
      }

      .aucorsa-line-stem {
        width: 2px;
        min-height: 90px;
        background: var(--line-color);
        opacity: 0.9;
      }

      .aucorsa-line-content {
        padding-top: 8px;
      }

      .aucorsa-line-route {
        color: #111;
        font-size: ${narrow ? "24px" : "31px"};
        line-height: 1.05;
        font-weight: 900;
        letter-spacing: -0.03em;
        text-transform: uppercase;
      }

      .aucorsa-line-estimation {
        margin-top: 20px;
        color: #0f1720;
        font-size: ${narrow ? "20px" : "28px"};
        line-height: 1.12;
      }

      .aucorsa-line-estimation strong {
        font-weight: 900;
      }

      .aucorsa-missing {
        opacity: 0.66;
        font-weight: 700;
      }

      .aucorsa-empty {
        padding: 28px;
      }

      .aucorsa-empty h2 {
        margin: 0;
        font-size: 28px;
        color: #1d6a3c;
      }

      .aucorsa-empty p {
        margin: 12px 0 0;
        color: #4c5b4c;
        font-size: 16px;
        max-width: 56ch;
      }

      @media (max-width: 900px) {
        .aucorsa-head {
          flex-direction: column;
          align-items: stretch;
        }

        .aucorsa-toolbar {
          align-items: stretch;
        }

        .aucorsa-updated {
          text-align: right;
        }

        .aucorsa-stop-header {
          padding: 18px 18px 0;
        }

        .aucorsa-lines {
          padding: 16px 14px 18px;
        }

        .aucorsa-line-row {
          grid-template-columns: 60px minmax(0, 1fr);
          gap: 12px;
          padding: 4px 6px;
        }

        .aucorsa-line-badge {
          width: 42px;
          min-height: 42px;
          font-size: 22px;
        }

        .aucorsa-line-stem {
          min-height: 72px;
        }
      }
    </style>

    <div class="aucorsa-shell">
      <div class="aucorsa-inner">
        <div class="aucorsa-head">
          <div class="aucorsa-head-copy">
            <h1 class="aucorsa-title">${title}</h1>
            <p class="aucorsa-subtitle">${subtitle}</p>
          </div>
          <div class="aucorsa-toolbar">
            <button class="aucorsa-refresh-button" type="button" ${
              refreshDisabled ? "disabled" : ""
            } title="${escapeHtml(labels.refreshNow)}" aria-label="${escapeHtml(labels.refreshNow)}">
              ${refreshIconMarkup()}
            </button>
            <div class="aucorsa-updated">
              ${escapeHtml(labels.updatedPrefix)} ${updatedLabel}
            </div>
          </div>
        </div>
        <div class="aucorsa-main">
          <div class="aucorsa-grid">${renderStopsMarkup(viewModel.stops, labels)}</div>
        </div>
        <footer class="aucorsa-footer">
          <a href="https://github.com/rafasanz" target="_blank" rel="noreferrer">
            ${escapeHtml(labels.createdBy)} ${escapeHtml(labels.githubLabel)}
          </a>
          ${viewModel.integrationVersion ? `<span>v${escapeHtml(viewModel.integrationVersion)}</span>` : ""}
        </footer>
      </div>
    </div>
  `;
}

function resolveCardConfig(hass, config) {
  const availableStops = collectAvailableStops(hass);
  const selectedStopId =
    String(config?.stop_id || "").trim() || String(availableStops[0]?.value || "").trim();

  return {
    ...config,
    stop_id: selectedStopId,
  };
}

function renderCardStopMarkup(stop, labels) {
  if (!stop) {
    return `
      <section class="aucorsa-card-empty">
        <p>${escapeHtml(labels.noStops)}</p>
      </section>
    `;
  }

  return `
    <section class="aucorsa-card-stop">
      <header class="aucorsa-card-stop-label">${escapeHtml(stop.stopLabel).toUpperCase()}</header>
      <div class="aucorsa-card-lines">
        ${stop.lines
          .map(
            (line) => `
              <article class="aucorsa-card-line" style="--line-color: ${escapeHtml(
                line.lineColor
              )}">
                <div class="aucorsa-card-line-side">
                  <div class="aucorsa-card-line-badge">${escapeHtml(line.line)}</div>
                  <div class="aucorsa-card-line-stem"></div>
                </div>
                <div class="aucorsa-card-line-main">
                  <div class="aucorsa-card-line-route">
                    ${escapeHtml(line.route || labels.noRoute)}
                  </div>
                  <div class="aucorsa-card-line-time">
                    ${escapeHtml(labels.nextArrival)}: ${minutesLabel(line.next, labels)}
                  </div>
                  <div class="aucorsa-card-line-time">
                    ${escapeHtml(labels.followingArrival)}: ${minutesLabel(
                      line.following,
                      labels
                    )}
                  </div>
                </div>
              </article>
            `
          )
          .join("")}
      </div>
    </section>
  `;
}

function renderCardMarkup({ hass, config, refreshing }) {
  const language = getLanguage(hass);
  const labels = getTexts(language);
  const resolvedConfig = resolveCardConfig(hass, config);
  const viewModel = collectViewModel(hass, resolvedConfig);
  const stop = viewModel.stops[0] || null;
  const showHeader = config?.show_header !== false;
  const showRefresh = config?.show_refresh !== false;
  const refreshDisabled = refreshing || viewModel.refreshEntityIds.length === 0;
  const rawTitle = String(config?.title || "").trim();
  const hasCustomTitle = rawTitle && rawTitle !== labels.title;
  const title = escapeHtml(hasCustomTitle ? rawTitle : labels.title);
  const subtitle = escapeHtml(
    LEGACY_PANEL_SUBTITLES.has(String(config?.subtitle || "").trim())
      ? labels.subtitle
      : config?.subtitle || labels.subtitle
  );
  const updatedLabel = escapeHtml(formatRelativeTime(viewModel.lastUpdated, language, labels));
  const refreshLabel = refreshing ? labels.refreshing : labels.refreshNow;

  return `
    <style>
      :host {
        display: block;
      }

      * {
        box-sizing: border-box;
      }

      ha-card {
        background: none;
        border: 0;
        box-shadow: none;
        overflow: visible;
      }

      .aucorsa-card {
        padding: 0;
      }

      .aucorsa-card-head,
      .aucorsa-card-toolbar-solo {
        margin-bottom: 16px;
      }

      .aucorsa-card-head {
        display: flex;
        justify-content: space-between;
        gap: 16px;
        align-items: flex-start;
      }

      .aucorsa-card-title {
        margin: 0;
        color: #1e6f3d;
        font-size: 28px;
        line-height: 1;
        letter-spacing: -0.03em;
        font-weight: 800;
      }

      .aucorsa-card-logo {
        display: block;
        width: auto;
        max-width: min(220px, 100%);
        height: 52px;
        object-fit: contain;
      }

      .aucorsa-card-subtitle {
        margin: 8px 0 0;
        color: var(--secondary-text-color, #5b6a58);
        font-size: 14px;
      }

      .aucorsa-card-toolbar,
      .aucorsa-card-toolbar-solo {
        display: flex;
        flex-direction: column;
        align-items: flex-end;
        gap: 8px;
      }

      .aucorsa-card-refresh {
        border: 0;
        border-radius: 999px;
        background: #1e6f3d;
        color: #fff;
        width: 44px;
        height: 44px;
        padding: 0;
        cursor: pointer;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        transition: opacity 140ms ease, transform 140ms ease;
      }

      .aucorsa-card-refresh svg {
        width: 20px;
        height: 20px;
        fill: currentColor;
      }

      .aucorsa-card-refresh:hover {
        transform: translateY(-1px);
      }

      .aucorsa-card-refresh:disabled {
        opacity: 0.6;
        cursor: default;
        transform: none;
      }

      .aucorsa-card-updated {
        color: var(--secondary-text-color, #58705e);
        font-size: 12px;
        font-weight: 700;
      }

      .aucorsa-card-stop-label {
        margin: 0 0 20px;
        color: #2c9e32;
        font-size: 24px;
        line-height: 1.08;
        font-weight: 900;
        text-transform: uppercase;
      }

      .aucorsa-card-lines {
        display: grid;
        gap: 12px;
      }

      .aucorsa-card-line {
        display: grid;
        grid-template-columns: 64px minmax(0, 1fr);
        gap: 16px;
        align-items: start;
      }

      .aucorsa-card-line-side {
        display: flex;
        flex-direction: column;
        align-items: center;
      }

      .aucorsa-card-line-badge {
        width: 50px;
        min-height: 50px;
        padding: 6px 8px;
        border-radius: 6px;
        background: var(--line-color);
        color: #fff;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 22px;
        line-height: 1;
        font-weight: 800;
        box-shadow: 0 10px 20px color-mix(in srgb, var(--line-color) 26%, transparent);
      }

      .aucorsa-card-line-stem {
        width: 3px;
        min-height: 112px;
        background: var(--line-color);
        opacity: 0.92;
      }

      .aucorsa-card-line-main {
        padding-top: 4px;
      }

      .aucorsa-card-line-route {
        color: var(--primary-text-color, #111);
        font-size: 26px;
        line-height: 1.02;
        font-weight: 900;
        letter-spacing: -0.03em;
        text-transform: uppercase;
      }

      .aucorsa-card-line-time {
        margin-top: 18px;
        color: var(--primary-text-color, #0f1720);
        font-size: 20px;
        line-height: 1.12;
      }

      .aucorsa-card-line-time strong {
        font-weight: 900;
      }

      .aucorsa-missing {
        opacity: 0.7;
        font-weight: 700;
      }

      .aucorsa-card-empty {
        color: var(--secondary-text-color, #4c5b4c);
        font-size: 14px;
      }

      .aucorsa-card-empty p {
        margin: 0;
      }

      @media (max-width: 700px) {
        .aucorsa-card-head {
          flex-direction: column;
        }

        .aucorsa-card-toolbar,
        .aucorsa-card-toolbar-solo {
          align-items: stretch;
        }

        .aucorsa-card-updated {
          text-align: right;
        }

        .aucorsa-card-stop-label {
          font-size: 20px;
          margin-bottom: 16px;
        }

        .aucorsa-card-line {
          grid-template-columns: 54px minmax(0, 1fr);
          gap: 12px;
        }

        .aucorsa-card-line-badge {
          width: 42px;
          min-height: 42px;
          font-size: 20px;
        }

        .aucorsa-card-line-stem {
          min-height: 86px;
        }

        .aucorsa-card-line-route {
          font-size: 18px;
        }

        .aucorsa-card-line-time {
          font-size: 16px;
          margin-top: 12px;
        }
      }
    </style>

    <ha-card>
      <div class="aucorsa-card">
        ${
          showHeader
            ? `
              <div class="aucorsa-card-head">
                <div>
                  ${
                    hasCustomTitle
                      ? `<h2 class="aucorsa-card-title">${title}</h2>`
                      : `<img class="aucorsa-card-logo" src="${AUCORSA_LOGO_URL}" alt="${escapeHtml(
                          labels.title
                        )}" />`
                  }
                  <p class="aucorsa-card-subtitle">${subtitle}</p>
                </div>
                ${
                  showRefresh
                    ? `
                      <div class="aucorsa-card-toolbar">
                        <button class="aucorsa-card-refresh" type="button" ${
                          refreshDisabled ? "disabled" : ""
                        } title="${escapeHtml(labels.refreshNow)}" aria-label="${escapeHtml(
                          labels.refreshNow
                        )}">
                          ${refreshIconMarkup()}
                        </button>
                        <div class="aucorsa-card-updated">
                          ${escapeHtml(labels.updatedPrefix)} ${updatedLabel}
                        </div>
                      </div>
                    `
                    : ""
                }
              </div>
            `
            : showRefresh
            ? `
              <div class="aucorsa-card-toolbar-solo">
                <button class="aucorsa-card-refresh" type="button" ${
                  refreshDisabled ? "disabled" : ""
                } title="${escapeHtml(labels.refreshNow)}" aria-label="${escapeHtml(
                  labels.refreshNow
                )}">
                  ${refreshIconMarkup()}
                </button>
                <div class="aucorsa-card-updated">
                  ${escapeHtml(labels.updatedPrefix)} ${updatedLabel}
                </div>
              </div>
            `
            : ""
        }
        ${renderCardStopMarkup(stop, labels)}
      </div>
    </ha-card>
  `;
}

class AucorsaViewBase extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._hass = undefined;
    this._refreshing = false;
    this._ticker = undefined;
  }

  connectedCallback() {
    if (!this._ticker) {
      this._ticker = window.setInterval(() => {
        if (this.isConnected) {
          this._render();
        }
      }, 1000);
    }
  }

  disconnectedCallback() {
    if (this._ticker) {
      window.clearInterval(this._ticker);
      this._ticker = undefined;
    }
  }

  async _handleRefreshClick() {
    if (!this._hass || this._refreshing) {
      return;
    }

    const viewModel = collectViewModel(this._hass, this._viewConfig());
    if (viewModel.refreshEntityIds.length === 0) {
      return;
    }

    this._refreshing = true;
    this._render();

    try {
      await this._hass.callService("button", "press", {}, { entity_id: viewModel.refreshEntityIds });
    } catch (error) {
      // eslint-disable-next-line no-console
      console.error("Aucorsa refresh failed", error);
    } finally {
      this._refreshing = false;
      this._render();
    }
  }

  _bindRefreshButton(selector) {
    const refreshButton = this.shadowRoot.querySelector(selector);
    if (refreshButton) {
      refreshButton.addEventListener("click", () => this._handleRefreshClick());
    }
  }

  _viewConfig() {
    return {};
  }
}

class AucorsaPanel extends AucorsaViewBase {
  constructor() {
    super();
    this._panel = undefined;
    this._narrow = false;
    this._route = undefined;
  }

  set hass(value) {
    this._hass = value;
    this._render();
  }

  set panel(value) {
    this._panel = value;
    this._render();
  }

  set narrow(value) {
    this._narrow = Boolean(value);
    this._render();
  }

  set route(value) {
    this._route = value;
  }

  _viewConfig() {
    return this._panel?.config || {};
  }

  _render() {
    this.shadowRoot.innerHTML = renderPanelMarkup({
      hass: this._hass,
      config: this._viewConfig(),
      narrow: this._narrow,
      refreshing: this._refreshing,
    });
    this._bindRefreshButton(".aucorsa-refresh-button");
  }
}

class AucorsaCardEditor extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._hass = undefined;
    this._stopsSignature = "";
    this._config = {
      type: "custom:aucorsa-card",
      show_header: true,
      show_refresh: true,
    };
  }

  set hass(value) {
    this._hass = value;
    const nextSignature = collectAvailableStops(this._hass)
      .map((stop) => `${stop.value}:${stop.label}`)
      .join("|");
    const shouldRender = this._stopsSignature !== nextSignature || !this.shadowRoot.innerHTML;
    this._stopsSignature = nextSignature;
    if (this._ensureDefaultStop()) {
      this._notifyConfigChanged();
    }
    if (shouldRender) {
      this._render();
    }
  }

  setConfig(config) {
    this._config = {
      type: "custom:aucorsa-card",
      show_header: true,
      show_refresh: true,
      ...(config || {}),
    };
    if (this._ensureDefaultStop()) {
      this._notifyConfigChanged();
    }
    this._render();
  }

  _ensureDefaultStop() {
    if (String(this._config?.stop_id || "").trim()) {
      return false;
    }

    const availableStops = collectAvailableStops(this._hass);
    const firstStopId = String(availableStops[0]?.value || "").trim();
    if (!firstStopId) {
      return false;
    }

    this._config = {
      ...this._config,
      stop_id: firstStopId,
    };
    return true;
  }

  _notifyConfigChanged() {
    this.dispatchEvent(
      new CustomEvent("config-changed", {
        detail: { config: this._config },
        bubbles: true,
        composed: true,
      })
    );
  }

  _handleFieldChange(event) {
    const target = event.target;
    if (!target) {
      return;
    }

    const nextConfig = {
      ...this._config,
      type: "custom:aucorsa-card",
    };

    const field = target.dataset.field;
    if (field === "stop_id") {
      const value = String(target.value || "").trim();
      if (value) {
        nextConfig.stop_id = value;
      } else {
        delete nextConfig.stop_id;
      }
    } else if (field === "title" || field === "subtitle") {
      const value = String(target.value || "").trim();
      if (value) {
        nextConfig[field] = value;
      } else {
        delete nextConfig[field];
      }
    } else if (field === "show_header" || field === "show_refresh") {
      nextConfig[field] = Boolean(target.checked);
    }

    this._config = nextConfig;
    this._notifyConfigChanged();
  }

  _render() {
    const language = getLanguage(this._hass);
    const labels = getTexts(language);
    const availableStops = collectAvailableStops(this._hass);
    const selectedStopId = String(this._config?.stop_id || "").trim();
    const title = escapeHtml(this._config?.title || "");
    const subtitle = escapeHtml(this._config?.subtitle || "");

    this.shadowRoot.innerHTML = `
      <style>
        :host {
          display: block;
        }

        * {
          box-sizing: border-box;
        }

        .aucorsa-editor {
          display: grid;
          gap: 16px;
          padding: 8px 0 0;
        }

        .aucorsa-editor-field {
          display: grid;
          gap: 6px;
        }

        .aucorsa-editor-label {
          color: var(--primary-text-color);
          font-size: 14px;
          font-weight: 600;
        }

        .aucorsa-editor-input,
        .aucorsa-editor-select {
          width: 100%;
          min-height: 40px;
          padding: 10px 12px;
          border: 1px solid var(--divider-color);
          border-radius: 10px;
          background: var(--card-background-color);
          color: var(--primary-text-color);
          font: inherit;
        }

        .aucorsa-editor-check {
          display: flex;
          align-items: center;
          gap: 10px;
          color: var(--primary-text-color);
          font-size: 14px;
        }

        .aucorsa-editor-help {
          color: var(--secondary-text-color);
          font-size: 13px;
        }
      </style>

      <div class="aucorsa-editor">
        <label class="aucorsa-editor-field">
          <span class="aucorsa-editor-label">${escapeHtml(labels.chooseStop)}</span>
          <select class="aucorsa-editor-select" data-field="stop_id" ${
            availableStops.length === 0 ? "disabled" : ""
          }>
            ${
              availableStops.length === 0
                ? `<option value="">${escapeHtml(labels.noStops)}</option>`
                : availableStops
                    .map(
                      (stop) => `
                        <option value="${escapeHtml(stop.value)}" ${
                          stop.value === selectedStopId ? "selected" : ""
                        }>
                          ${escapeHtml(stop.label)}
                        </option>
                      `
                    )
                    .join("")
            }
          </select>
        </label>

        <label class="aucorsa-editor-field">
          <span class="aucorsa-editor-label">${escapeHtml(labels.titleLabel)}</span>
          <input
            class="aucorsa-editor-input"
            data-field="title"
            type="text"
            value="${title}"
            placeholder="${escapeHtml(labels.title)}"
          />
        </label>

        <label class="aucorsa-editor-field">
          <span class="aucorsa-editor-label">${escapeHtml(labels.subtitleLabel)}</span>
          <input
            class="aucorsa-editor-input"
            data-field="subtitle"
            type="text"
            value="${subtitle}"
            placeholder="${escapeHtml(labels.subtitle)}"
          />
        </label>

        <label class="aucorsa-editor-check">
          <input
            data-field="show_header"
            type="checkbox"
            ${this._config?.show_header !== false ? "checked" : ""}
          />
          <span>${escapeHtml(labels.showHeader)}</span>
        </label>

        <label class="aucorsa-editor-check">
          <input
            data-field="show_refresh"
            type="checkbox"
            ${this._config?.show_refresh !== false ? "checked" : ""}
          />
          <span>${escapeHtml(labels.showRefresh)}</span>
        </label>

        ${
          availableStops.length === 0
            ? `<div class="aucorsa-editor-help">${escapeHtml(labels.noStops)}</div>`
            : ""
        }
      </div>
    `;

    this.shadowRoot.querySelectorAll("[data-field]").forEach((element) => {
      const eventName = "change";
      element.addEventListener(eventName, (event) => this._handleFieldChange(event));
    });
  }
}

class AucorsaCard extends AucorsaViewBase {
  constructor() {
    super();
    this._config = {};
  }

  static async getConfigElement() {
    return document.createElement("aucorsa-card-editor");
  }

  static getStubConfig() {
    return {
      type: "custom:aucorsa-card",
      show_header: true,
      show_refresh: true,
    };
  }

  set hass(value) {
    this._hass = value;
    this._render();
  }

  setConfig(config) {
    this._config = config || {};
    this._render();
  }

  getCardSize() {
    return 3;
  }

  _viewConfig() {
    return resolveCardConfig(this._hass, this._config || {});
  }

  _render() {
    this.shadowRoot.innerHTML = renderCardMarkup({
      hass: this._hass,
      config: this._viewConfig(),
      refreshing: this._refreshing,
    });
    this._bindRefreshButton(".aucorsa-card-refresh");
  }
}

if (!customElements.get("aucorsa-panel")) {
  customElements.define("aucorsa-panel", AucorsaPanel);
}

if (!customElements.get("aucorsa-card-editor")) {
  customElements.define("aucorsa-card-editor", AucorsaCardEditor);
}

if (!customElements.get("aucorsa-card")) {
  customElements.define("aucorsa-card", AucorsaCard);
}

window.customCards = window.customCards || [];
if (!window.customCards.some((card) => card.type === "aucorsa-card")) {
  window.customCards.push({
    type: "aucorsa-card",
    name: "Aucorsa",
    description: "Muestra una parada de Aucorsa con selector visual y refresco manual.",
  });
}
