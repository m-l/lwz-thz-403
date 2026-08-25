/**
 * thz-heating-curve-card.js
 *
 * A Lovelace custom card for the `thz` Stiebel Eltron / Tecalor LWZ/THZ
 * integration. Plots the weather-compensated HC1 flow-temperature curve
 * (from the live p13Gradient / p14LowEnd / p15RoomInfluence parameters)
 * and drops a marker at the device's actual current outside-temp /
 * heat_set_temp reading, so you can see at a glance how far real behaviour
 * has drifted from the theoretical curve before nudging a parameter.
 *
 * The curve formula is ported from the FHEM THZ.pm project's
 * `function_heatSetTemp`, which reverse-engineered it from real device
 * behaviour -- it is not an official Stiebel Eltron formula, but the best
 * verified approximation publicly available. See docs/legacy/00_THZ.pm in
 * this repo for the original Perl.
 *
 * --- Example Lovelace card config -----------------------------------
 * type: custom:thz-heating-curve-card
 * title: HC1 Heating Curve
 * entities:
 *   gradient: number.lwz403_p13_gradient_hc1
 *   low_end: number.lwz403_p14_low_end_hc1
 *   room_influence: number.lwz403_p15_room_influence_hc1
 *   room_set: climate.lwz403_heating_circuit   # reads target_temperature
 *   inside_temp: sensor.lwz403_inside_temp
 *   outside_temp: sensor.lwz403_outside_temp_filtered
 *   heat_set_temp: sensor.lwz403_heat_set_temp
 * nudge_step:
 *   gradient: 0.05
 *   low_end: 0.5
 *   room_influence: 5
 * -----------------------------------------------------------------------
 */

const DEFAULT_ENTITIES = {
  gradient: "number.lwz403_p13_gradient_hc1",
  low_end: "number.lwz403_p14_low_end_hc1",
  room_influence: "number.lwz403_p15_room_influence_hc1",
  room_set: "climate.lwz403_heating_circuit",
  inside_temp: "sensor.lwz403_inside_temp",
  outside_temp: "sensor.lwz403_outside_temp_filtered",
  heat_set_temp: "sensor.lwz403_heat_set_temp",
};

const DEFAULT_STEP = { gradient: 0.05, low_end: 0.5, room_influence: 5 };

const X_MIN = -20, X_MAX = 25;
const PAD = { l: 52, r: 18, t: 14, b: 32 };
const W = 620, H = 300;
const PLOT_W = W - PAD.l - PAD.r, PLOT_H = H - PAD.t - PAD.b;

function curveValue(T, gradient, lowEnd, roomInf, roomSet, inside, withRoom) {
  const roomTerm = withRoom ? (roomInf * gradient * (roomSet - inside)) / 10 : 0;
  const a = 0.7 + roomSet * (1 + gradient * 0.87) + lowEnd + roomTerm;
  const b = (-14 * gradient) / roomSet;
  const c = (-1 * gradient) / 75;
  return Math.max(5, c * T * T + b * T + a);
}

function niceStep(range) {
  if (range <= 20) return 5;
  if (range <= 40) return 10;
  return 20;
}

function fmt(v, d = 1) {
  return typeof v === "number" && !Number.isNaN(v) ? v.toFixed(d) : "--";
}

class THZHeatingCurveCard extends HTMLElement {
  setConfig(config) {
    if (!config) throw new Error("Invalid configuration");
    this._config = config;
    this._entities = { ...DEFAULT_ENTITIES, ...(config.entities || {}) };
    this._step = { ...DEFAULT_STEP, ...(config.nudge_step || {}) };
    this._title = config.title || "Heating Curve";
    if (!this.shadowRoot) this.attachShadow({ mode: "open" });
    this._buildStaticDom();
  }

  getCardSize() {
    return 6;
  }

  static getStubConfig() {
    return { type: "custom:thz-heating-curve-card", title: "HC1 Heating Curve", entities: DEFAULT_ENTITIES };
  }

  set hass(hass) {
    this._hass = hass;
    this._render();
  }

  _num(entityId, attr) {
    const st = this._hass && this._hass.states[entityId];
    if (!st) return null;
    const raw = attr ? st.attributes[attr] : st.state;
    const v = parseFloat(raw);
    return Number.isNaN(v) ? null : v;
  }

  _buildStaticDom() {
    const root = this.shadowRoot;
    root.innerHTML = `
      <style>
        :host { display: block; }
        ha-card { padding: 16px 16px 10px; }
        .head { display: flex; justify-content: space-between; align-items: baseline; margin-bottom: 6px; }
        .head h1 { font-size: 16px; font-weight: 600; margin: 0; color: var(--primary-text-color); }
        .legend { display: flex; gap: 12px; font-size: 11.5px; color: var(--secondary-text-color); }
        .legend span.sw { display:inline-block; width:10px; height:2px; margin-right:4px; vertical-align:middle; }
        svg { display: block; width: 100%; height: auto; }
        .grid { stroke: var(--divider-color, #444); stroke-width: 1; opacity: 0.5; }
        .grid.strong { opacity: 0.9; }
        .axis { fill: var(--secondary-text-color); font-size: 9.5px; font-family: var(--paper-font-common-base_-_font-family, inherit); }
        .curve-a { stroke: #cf6f34; stroke-width: 2.25; fill: none; stroke-linecap: round; }
        .curve-b { stroke: #149bb0; stroke-width: 1.75; fill: none; stroke-linecap: round; stroke-dasharray: 1 5; }
        .marker-ring { fill: rgba(240,193,75,0.20); stroke: none; }
        .marker-dot { fill: #f0c14b; stroke: var(--card-background-color, #1c1c1c); stroke-width: 2; }
        .stats { display: flex; gap: 18px; flex-wrap: wrap; margin-top: 6px; padding-top: 10px; border-top: 1px solid var(--divider-color); }
        .stat { display: flex; flex-direction: column; gap: 1px; }
        .stat .l { font-size: 10px; text-transform: uppercase; letter-spacing: .05em; color: var(--secondary-text-color); }
        .stat .v { font-size: 14px; font-weight: 600; color: var(--primary-text-color); font-variant-numeric: tabular-nums; }
        .stat .v.warn { color: #d68a1c; }
        .params { display: flex; flex-direction: column; gap: 8px; margin-top: 12px; }
        .param-row { display: flex; align-items: center; gap: 8px; }
        .param-row .name { flex: 1; font-size: 12.5px; color: var(--primary-text-color); }
        .param-row .val { font-size: 13px; font-weight: 600; min-width: 3.6em; text-align: right; font-variant-numeric: tabular-nums; color: var(--primary-text-color); }
        .param-row button {
          width: 26px; height: 26px; border-radius: 6px; border: 1px solid var(--divider-color);
          background: var(--card-background-color); color: var(--primary-text-color);
          font-size: 15px; line-height: 1; cursor: pointer; display:flex; align-items:center; justify-content:center;
        }
        .param-row button:hover { background: var(--secondary-background-color, rgba(127,127,127,0.15)); }
        .param-row button:active { transform: scale(0.94); }
        .unavailable { color: var(--secondary-text-color); font-size: 12.5px; padding: 8px 0; }
      </style>
      <ha-card>
        <div class="head">
          <h1></h1>
          <div class="legend">
            <span><span class="sw" style="background:#cf6f34"></span>with room infl.</span>
            <span><span class="sw" style="background:#149bb0"></span>simplified</span>
          </div>
        </div>
        <div class="chart-slot"></div>
        <div class="stats"></div>
        <div class="params"></div>
      </ha-card>
    `;
    root.querySelector("h1").textContent = this._title;
  }

  _svgSkeleton(yMin, yMax, step) {
    let grid = "";
    for (let v = yMin; v <= yMax; v += step) {
      const y = PAD.t + (1 - (v - yMin) / (yMax - yMin)) * PLOT_H;
      grid += `<line class="grid${v === 0 ? " strong" : ""}" x1="${PAD.l}" y1="${y}" x2="${W - PAD.r}" y2="${y}"/>`;
      grid += `<text class="axis" x="${PAD.l - 8}" y="${y + 3}" text-anchor="end">${v}</text>`;
    }
    for (let t = Math.ceil(X_MIN / 5) * 5; t <= X_MAX; t += 5) {
      const x = PAD.l + ((t - X_MIN) / (X_MAX - X_MIN)) * PLOT_W;
      grid += `<line class="grid${t === 0 ? " strong" : ""}" x1="${x}" y1="${PAD.t}" x2="${x}" y2="${H - PAD.b}"/>`;
      grid += `<text class="axis" x="${x}" y="${H - PAD.b + 14}" text-anchor="middle">${t}°</text>`;
    }
    return grid;
  }

  _render() {
    const root = this.shadowRoot;
    if (!root || !this._hass) return;
    const e = this._entities;

    const gradient = this._num(e.gradient);
    const lowEnd = this._num(e.low_end);
    const roomInf = this._num(e.room_influence);
    const roomSetEntity = this._hass.states[e.room_set];
    const roomSet = roomSetEntity
      ? (e.room_set.startsWith("climate.")
          ? parseFloat(roomSetEntity.attributes.temperature)
          : parseFloat(roomSetEntity.state))
      : null;
    const inside = this._num(e.inside_temp);
    const outsideNow = this._num(e.outside_temp);
    const flowNow = this._num(e.heat_set_temp);

    const missing = [
      ["gradient", gradient], ["low_end", lowEnd], ["room_influence", roomInf],
      ["room_set", roomSet], ["inside_temp", inside],
    ].filter(([, v]) => v === null || Number.isNaN(v)).map(([k]) => k);

    const chartSlot = root.querySelector(".chart-slot");
    const statsSlot = root.querySelector(".stats");
    const paramsSlot = root.querySelector(".params");

    if (missing.length) {
      chartSlot.innerHTML = `<div class="unavailable">Waiting on: ${missing.map((k) => e[k]).join(", ")}</div>`;
      statsSlot.innerHTML = "";
    } else {
      const N = 70;
      const ptsA = [], ptsB = [];
      let yMin = Infinity, yMax = -Infinity;
      for (let i = 0; i <= N; i++) {
        const T = X_MIN + ((X_MAX - X_MIN) * i) / N;
        const vA = curveValue(T, gradient, lowEnd, roomInf, roomSet, inside, true);
        const vB = curveValue(T, gradient, lowEnd, roomInf, roomSet, inside, false);
        ptsA.push([T, vA]); ptsB.push([T, vB]);
        yMin = Math.min(yMin, vA, vB); yMax = Math.max(yMax, vA, vB);
      }
      if (flowNow !== null) { yMin = Math.min(yMin, flowNow); yMax = Math.max(yMax, flowNow); }
      const step = niceStep(yMax - yMin);
      let yLo = Math.max(0, Math.floor((yMin - step * 0.6) / step) * step);
      let yHi = Math.ceil((yMax + step * 0.6) / step) * step;
      if (yHi - yLo < step * 3) yHi = yLo + step * 4;

      const xToPx = (t) => PAD.l + ((t - X_MIN) / (X_MAX - X_MIN)) * PLOT_W;
      const yToPx = (v) => PAD.t + (1 - (v - yLo) / (yHi - yLo)) * PLOT_H;

      const pathA = "M " + ptsA.map(([t, v]) => `${xToPx(t).toFixed(1)},${yToPx(v).toFixed(1)}`).join(" L ");
      const pathB = "M " + ptsB.map(([t, v]) => `${xToPx(t).toFixed(1)},${yToPx(v).toFixed(1)}`).join(" L ");

      let markerSvg = "";
      let deltaHtml = "";
      if (outsideNow !== null && flowNow !== null) {
        const mx = xToPx(Math.max(X_MIN, Math.min(X_MAX, outsideNow)));
        const my = yToPx(Math.max(yLo, Math.min(yHi, flowNow)));
        markerSvg = `<circle class="marker-ring" cx="${mx}" cy="${my}" r="11"/><circle class="marker-dot" cx="${mx}" cy="${my}" r="4.5"/>`;
        const expected = curveValue(outsideNow, gradient, lowEnd, roomInf, roomSet, inside, true);
        const delta = flowNow - expected;
        deltaHtml = `
          <div class="stat"><span class="l">Outside</span><span class="v">${fmt(outsideNow)}&deg;C</span></div>
          <div class="stat"><span class="l">Curve says</span><span class="v">${fmt(expected)}&deg;C</span></div>
          <div class="stat"><span class="l">Device reads</span><span class="v">${fmt(flowNow)}&deg;C</span></div>
          <div class="stat"><span class="l">Difference</span><span class="v${Math.abs(delta) >= 1.5 ? " warn" : ""}">${delta >= 0 ? "+" : ""}${fmt(delta)} K</span></div>
        `;
      }

      chartSlot.innerHTML = `
        <svg viewBox="0 0 ${W} ${H}">
          <g>${this._svgSkeleton(yLo, yHi, step)}</g>
          <path class="curve-b" d="${pathB}"></path>
          <path class="curve-a" d="${pathA}"></path>
          ${markerSvg}
        </svg>
      `;
      statsSlot.innerHTML = deltaHtml;
    }

    const paramDefs = [
      { key: "gradient", entity: e.gradient, label: "Gradient (P13)", value: gradient, digits: 2 },
      { key: "low_end", entity: e.low_end, label: "Low end (P14)", value: lowEnd, digits: 1 },
      { key: "room_influence", entity: e.room_influence, label: "Room influence (P15)", value: roomInf, digits: 0 },
    ];
    paramsSlot.innerHTML = "";
    for (const p of paramDefs) {
      const row = document.createElement("div");
      row.className = "param-row";
      row.innerHTML = `
        <button data-key="${p.key}" data-dir="-1" aria-label="Decrease ${p.label}">&minus;</button>
        <span class="name">${p.label}</span>
        <span class="val">${p.value === null ? "--" : fmt(p.value, p.digits)}</span>
        <button data-key="${p.key}" data-dir="1" aria-label="Increase ${p.label}">+</button>
      `;
      row.querySelectorAll("button").forEach((btn) => {
        btn.addEventListener("click", () => this._nudge(p.key, parseInt(btn.dataset.dir, 10)));
      });
      paramsSlot.appendChild(row);
    }
  }

  _nudge(key, dir) {
    const entityId = this._entities[key];
    const current = this._num(entityId);
    if (current === null || !this._hass) return;
    const step = this._step[key] || 1;
    const next = Math.round((current + dir * step) * 100) / 100;
    this._hass.callService("number", "set_value", { entity_id: entityId, value: next });
  }
}

customElements.define("thz-heating-curve-card", THZHeatingCurveCard);

window.customCards = window.customCards || [];
window.customCards.push({
  type: "thz-heating-curve-card",
  name: "THZ Heating Curve Card",
  description: "Live HC1 weather-compensated heating curve for Stiebel Eltron / Tecalor THZ heat pumps, with a working-point marker and inline parameter nudges.",
});
