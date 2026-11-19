// Kuchnia Vikinga dashboard card: today's meals with 👍/👎 voting.
// Usage: type: custom:kuchnia-vikinga-card (optional: entity, title)

const esc = (s) =>
  String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);

class KuchniaVikingaCard extends HTMLElement {
  setConfig(config) {
    this._config = { entity: "sensor.kuchnia_vikinga_dzisiaj", title: "Kuchnia Vikinga – dziś", ...config };
    this._state = undefined;
    if (!this.shadowRoot) {
      this.attachShadow({ mode: "open" });
      this.shadowRoot.addEventListener("click", (ev) => this._onClick(ev));
    }
  }

  set hass(hass) {
    this._hass = hass;
    const state = hass.states[this._config.entity];
    if (state !== this._state) {
      this._state = state;
      this._render();
    }
  }

  _onClick(ev) {
    const btn = ev.target.closest("button[data-vote]");
    if (!btn) return;
    const meal = this._meals()[Number(btn.dataset.index)];
    // Clicking the active vote again clears it.
    const vote = meal.vote === btn.dataset.vote ? "none" : btn.dataset.vote;
    this._hass.callService("kuchnia_vikinga", "vote", { name: meal.name, vote });
  }

  _meals() {
    return this._state?.attributes?.meals ?? [];
  }

  _render() {
    // Keep expanded rows expanded across re-renders (e.g. after a vote).
    const open = new Set([...this.shadowRoot.querySelectorAll("details[open]")].map((d) => d.dataset.name));
    const meals = this._meals();
    const rows = meals
      .map(
        (m, i) => `
        <div class="row">
          <div class="votes">
            <button data-vote="up" data-index="${i}" class="${m.vote === "up" ? "up" : ""}" title="Smakuje">
              <ha-icon icon="${m.vote === "up" ? "mdi:thumb-up" : "mdi:thumb-up-outline"}"></ha-icon>
            </button>
            <button data-vote="down" data-index="${i}" class="${m.vote === "down" ? "down" : ""}" title="Nie smakuje">
              <ha-icon icon="${m.vote === "down" ? "mdi:thumb-down" : "mdi:thumb-down-outline"}"></ha-icon>
            </button>
          </div>
          <details data-name="${esc(m.name)}" ${open.has(m.name) ? "open" : ""}>
            <summary><b>${esc(m.meal)}</b> — ${esc(m.name)} <small>(${esc(m.kcal)} kcal)</small></summary>
            <div class="ingredients">${(m.ingredients ?? []).map(esc).join(" · ")}</div>
          </details>
        </div>`
      )
      .join("");
    this.shadowRoot.innerHTML = `
      <style>
        .row { display: flex; align-items: flex-start; gap: 12px; padding: 8px 0; }
        .row + .row { border-top: 1px solid var(--divider-color); }
        .votes { flex: 0 0 80px; display: flex; gap: 4px; }
        button { all: unset; cursor: pointer; width: 36px; height: 36px; display: flex;
                 align-items: center; justify-content: center; border-radius: 50%;
                 color: var(--secondary-text-color); }
        button:hover { background: var(--secondary-background-color); }
        button.up { color: var(--success-color, #4caf50); }
        button.down { color: var(--error-color, #f44336); }
        details { flex: 1; min-width: 0; padding-top: 8px; }
        summary { cursor: pointer; }
        .ingredients { margin-top: 8px; font-size: 0.85em; color: var(--secondary-text-color); }
        .empty { font-style: italic; color: var(--secondary-text-color); }
      </style>
      <ha-card header="${esc(this._config.title)}">
        <div class="card-content">
          ${this._state ? rows || '<div class="empty">Brak dostawy dzisiaj.</div>' : `<div class="empty">Brak encji ${esc(this._config.entity)}</div>`}
        </div>
      </ha-card>`;
  }

  getCardSize() {
    return 1 + this._meals().length;
  }

  getGridOptions() {
    return { columns: "full" };
  }
}

customElements.define("kuchnia-vikinga-card", KuchniaVikingaCard);
window.customCards = window.customCards || [];
window.customCards.push({
  type: "kuchnia-vikinga-card",
  name: "Kuchnia Vikinga",
  description: "Dzisiejsze posiłki z ocenami 👍/👎",
});
