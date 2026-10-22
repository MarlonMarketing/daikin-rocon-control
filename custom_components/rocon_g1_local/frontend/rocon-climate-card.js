/* Original Lovelace card. No external libraries, network requests or services. */
const ROConStyle = `
:host{display:block;--rc-ink:#e9f4f3;--rc-muted:#a5b9bb;--rc-line:#ffffff16;font-family:var(--paper-font-body1_-_font-family,system-ui,sans-serif)}
*{box-sizing:border-box}ha-card{display:block;overflow:hidden;border:1px solid #ffffff18;border-radius:28px;background:#10282d;color:var(--rc-ink);box-shadow:0 16px 48px #0002}
.wrap{padding:28px}.top,.line,.metric-head,.foot{display:flex;align-items:center;justify-content:space-between;gap:12px}.identity{display:flex;gap:12px;align-items:center}.mark{display:grid;place-items:center;width:42px;height:42px;border:1px solid #a9e5d044;border-radius:14px;color:#b4f5db;font-size:23px}.eyebrow{font-size:10px;letter-spacing:2.3px;font-weight:750;color:#a4c6c4}.brand{font-size:19px;letter-spacing:-.6px;margin-top:3px}.pill{font-size:10px;font-weight:750;border:1px solid #ffffff20;border-radius:30px;padding:8px 11px;color:#c7d9d8;white-space:nowrap}.pill[data-state=ready]{background:#b7f4d716;color:#b7f4d7;border-color:#b7f4d733}.dot{display:inline-block;width:6px;height:6px;border-radius:50%;background:currentColor;margin-right:6px}
.intro{margin:29px 0 22px}.intro h1{font-size:clamp(27px,5vw,39px);font-weight:500;line-height:1.13;letter-spacing:-1.5px;margin:0 0 10px}.intro p{font-size:13px;line-height:1.6;color:var(--rc-muted);margin:0;max-width:480px}.tabs{display:flex;gap:4px;border-bottom:1px solid var(--rc-line);margin-bottom:22px;overflow:auto}.tabs button{cursor:pointer;background:none;border:0;border-bottom:2px solid transparent;color:var(--rc-muted);padding:11px 13px;font:inherit;font-size:12px;white-space:nowrap}.tabs button[aria-selected=true]{color:#b7f4d7;border-color:#b7f4d7}.tabs button:focus-visible{outline:2px solid #b7f4d7;outline-offset:-3px;border-radius:5px}
.metrics{display:grid;grid-template-columns:1.2fr 1fr;gap:12px}.metric{border:1px solid var(--rc-line);border-radius:20px;padding:20px;background:#193238;min-width:0}.metric.hero{background:linear-gradient(135deg,#c5eddc,#a7d8ce);color:#113e36;border:0;grid-row:span 2;display:flex;flex-direction:column;justify-content:space-between;min-height:260px}.label{font-size:12px;letter-spacing:.1px}.symbol{font-size:22px;line-height:1}.value{font-size:36px;letter-spacing:-1.5px;font-weight:450;line-height:1.1;margin-top:19px}.value small{font-size:17px;letter-spacing:0;margin-left:3px;opacity:.7}.hero .value{font-size:66px;letter-spacing:-3px;margin:34px 0 17px}.caption{font-size:10px;line-height:1.5;color:var(--rc-muted);margin-top:10px}.hero .caption{color:#35665a}.hero .tag{display:inline-flex;align-items:center;gap:6px;border-radius:20px;background:#1d594614;padding:6px 9px;font-size:10px;align-self:flex-start}.metric:not(.hero) .value{font-size:29px;margin-top:16px}.metric.warm .symbol{color:#ecc397}.hero .symbol{color:#235c4e}
.subhead{font-size:11px;color:#a7c4c4;font-weight:700;letter-spacing:1.7px;text-transform:uppercase;margin:26px 0 13px}.panel{padding:18px 20px;border:1px solid var(--rc-line);border-radius:18px;background:#122b30}.line{font-size:12px;padding:11px 0;border-bottom:1px solid var(--rc-line)}.line:first-child{padding-top:0}.line:last-child{padding-bottom:0;border:0}.line span:first-child{color:var(--rc-muted)}.line b{font-weight:500;text-align:right;overflow-wrap:anywhere}.notice{font-size:11px;line-height:1.65;color:#b3c5c6;padding:15px 0 0}.notice strong{color:#d3e9e5;font-weight:600}.foot{font-size:10px;letter-spacing:.6px;color:#a8bebf;margin-top:24px;padding-top:16px;border-top:1px solid var(--rc-line)}.foot .tiny{color:#badaca}.empty{border:1px dashed #8bbab555;border-radius:18px;padding:25px 20px;line-height:1.7;font-size:13px;color:#b9cecd}.empty strong{display:block;font-size:17px;color:#e7f4ee;margin-bottom:8px}.hidden{display:none!important}.count{color:#b7f4d7}.list{max-height:340px;overflow:auto}.list .line{gap:20px}.list .line span{overflow-wrap:anywhere;min-width:0}.list .line b{min-width:65px}.status-note{color:#ecc397;font-size:11px;margin:0 0 16px;line-height:1.6}
@media(max-width:420px){.wrap{padding:20px}.pill{font-size:9px;padding:7px 8px}.brand{font-size:17px}.metrics{gap:9px}.metric{padding:15px;border-radius:17px}.metric.hero{min-height:245px}.hero .value{font-size:49px;letter-spacing:-2px}.metric:not(.hero) .value{font-size:24px}.label{font-size:11px}.tabs button{padding:10px}.foot{font-size:9px}.eyebrow{font-size:9px}}
@media(prefers-reduced-motion:no-preference){ha-card{animation:appear .35s ease-out}@keyframes appear{from{opacity:.4;transform:translateY(5px)}to{opacity:1;transform:none}}}
`;

class RoConClimateCard extends HTMLElement {
  constructor() { super(); this.attachShadow({mode: "open"}); this._tab = "overview"; }
  setConfig(config) {
    if (!config || typeof config !== "object") throw new Error("Configurazione scheda richiesta");
    if (config.entities && (typeof config.entities !== "object" || Array.isArray(config.entities))) throw new Error("entities deve essere una mappa");
    this._config = {...config}; this._render();
  }
  set hass(hass) { this._hass = hass; this._render(); }
  getCardSize() { return 10; }
  getGridOptions() { return {columns: 12, rows: 10, min_columns: 6, min_rows: 7}; }
  static getStubConfig() { return {type: "custom:rocon-climate-card", title: "Il clima, a colpo d’occhio."}; }
  static getConfigElement() { return document.createElement("rocon-climate-card-editor"); }

  _data() {
    const states = this._hass?.states || {};
    let local = Object.entries(states).filter(([, e]) => ["g1_local_cache", "rocon_cloud"].includes(e.attributes?.source)).map(([entity_id,e]) => ({...e,entity_id}));
    const gateways = new Set(local.map(e => e.attributes.rocon_gateway).filter(Boolean));
    const ambiguous = gateways.size > 1 && !this._config.gateway;
    if (this._config.gateway) local = local.filter(e => e.attributes.rocon_gateway === this._config.gateway);
    if (ambiguous) local = [];
    const find = (role, device, field, section = "status") => {
      const override = this._config.entities?.[role];
      if (override) return states[override];
      const aliases = {dhwTemperature:"actualTemperature", boilerTemperature:"boilerActualTemperature", dhwSetpoint:"profile_1"};
      return local.find(e => e.attributes.rocon_device === device && (e.attributes.rocon_field === field || e.attributes.source === "rocon_cloud" && e.attributes.rocon_field === aliases[field]) && e.attributes.rocon_section === section);
    };
    const mapped = {
      acs:find("acs","water","dhwTemperature"), outside:find("outside","direct","outsideTemperature"),
      boiler:find("boiler","direct","boilerTemperature"), target:find("target","water","dhwSetpoint","setting")
    };
    const all = [...new Map([...local, ...Object.values(mapped).filter(Boolean)].map(e=>[e.entity_id,e])).values()];
    const cloud = local.some(e=>e.attributes.source === "rocon_cloud");
    return {local, mapped, all, ambiguous, cloud, ready:all.filter(e => this._valid(e)).length};
  }
  _valid(entity) { return entity && !["unknown","unavailable","",null,undefined].includes(entity.state); }
  _temp(entity) {
    if (!this._valid(entity) || !Number.isFinite(Number(entity.state))) return ["—", ""];
    // Units belong to the selected entity; never relabel Fahrenheit as Celsius.
    const number = new Intl.NumberFormat(this._hass?.locale?.language || "it", {maximumFractionDigits:1}).format(Number(entity.state));
    return [number, entity.attributes?.unit_of_measurement || ""];
  }
  _text(selector, value) { this.shadowRoot.querySelector(selector).textContent = value; }
  _render() {
    if (!this._config) return;
    if (!this.shadowRoot.querySelector("ha-card")) {
      this.shadowRoot.innerHTML = `<style>${ROConStyle}</style><ha-card><div class="wrap">
        <header class="top"><div class="identity"><div class="mark" aria-hidden="true">≈</div><div><div class="eyebrow">CLIMATE STUDIO</div><div class="brand">RoCon <span style="color:#b7f4d7">Control</span></div></div></div><div class="pill"><span class="dot"></span><span class="connection"></span></div></header>
        <div class="intro"><h1></h1><p>Acqua calda e riscaldamento, in uno spazio chiaro.<br>Misure, profili e stato dei tuoi circuiti.</p></div>
        <nav class="tabs" role="tablist" aria-label="Viste RoCon"><button role="tab" data-tab="overview" aria-controls="rc-panel">Panoramica</button><button role="tab" data-tab="settings" aria-controls="rc-panel">Impostazioni lette</button><button role="tab" data-tab="controls" aria-controls="rc-panel">Controlli cloud</button><button role="tab" data-tab="diagnostics" aria-controls="rc-panel">Diagnostica</button></nav>
        <div id="rc-panel" role="tabpanel"><div class="empty hidden"></div><div class="overview">
          <div class="metrics"><div class="metric hero"><div class="metric-head"><span class="label">Acqua calda sanitaria</span><span class="symbol" aria-hidden="true">♨</span></div><div><div class="value" data-role="acs"></div><div class="tag">ACS · Temperatura letta</div><div class="caption">Dato visualizzato dalla sorgente.<br>Non è una conferma di misura recente.</div></div></div>
          <div class="metric"><div class="metric-head"><span class="label">All’esterno</span><span class="symbol" aria-hidden="true">☀</span></div><div class="value" data-role="outside"></div></div>
          <div class="metric warm"><div class="metric-head"><span class="label">Caldaia</span><span class="symbol" aria-hidden="true">≋</span></div><div class="value" data-role="boiler"></div></div></div>
          <div class="subhead">Il tuo impianto</div><div class="panel"><div class="line"><span>ACS · Profilo 1 letto</span><b data-role="target"></b></div><div class="line"><span>Sensori disponibili</span><b class="count"></b></div><div class="line"><span>Accesso</span><b class="source-label"></b></div></div>
        </div><div class="controls hidden"><p class="status-note">I controlli usano le entità native di Home Assistant. La modifica può avviare il riscaldamento: consulta valore richiesto, confermato e stato ultimo comando. La modalità è condivisa con ACS. Party prolunga il riscaldamento ambiente e non modifica il programma ACS.</p><div class="native-controls"></div></div><div class="detail hidden"><p class="status-note"></p><div class="panel list"></div></div></div>
        <div class="notice">Le letture cloud e LAN non includono un timestamp della misura: un dato disponibile non dimostra freschezza del bus. I controlli sono esposti soltanto per il cloud e richiedono abilitazione nella configurazione.</div>
        <footer class="foot"><span>ROCON G1 · PROGETTO INDIPENDENTE</span><span class="tiny">LAN / CLOUD</span></footer>
      </div></ha-card>`;
      for (const button of this.shadowRoot.querySelectorAll("[data-tab]")) {
        button.addEventListener("click", () => { this._tab = button.dataset.tab; this._render(); });
        button.addEventListener("keydown", event => {
          if (!["ArrowLeft","ArrowRight","Home","End"].includes(event.key)) return;
          const buttons = [...this.shadowRoot.querySelectorAll("[data-tab]")];
          const current = buttons.indexOf(button);
          const next = event.key === "Home" ? 0 : event.key === "End" ? buttons.length-1 : (current + (event.key === "ArrowRight" ? 1 : buttons.length-1)) % buttons.length;
          event.preventDefault(); this._tab = buttons[next].dataset.tab; this._render(); buttons[next].focus();
        });
      }
    }
    const data = this._data();
    this._text("h1",this._config.title || "Il clima, a colpo d’occhio.");
    this._text(".connection", data.ready ? "Dati disponibili" : "In attesa di dati");
    this.shadowRoot.querySelector(".pill").dataset.state = data.ready ? "ready" : "waiting";
    this._text(".count", `${data.ready} / ${data.all.length}`);
    this._text(".source-label", Object.keys(this._config.entities || {}).length ? "Sensori selezionati" : (data.cloud ? "Daikin Control cloud" : "Cache API LAN G1"));
    for (const [role,entity] of Object.entries(data.mapped)) {
      const element = this.shadowRoot.querySelector(`[data-role="${role}"]`);
      const [value,unit] = this._temp(entity); element.textContent = value;
      const small = document.createElement("small"); small.textContent = unit; element.append(small);
    }
    for (const button of this.shadowRoot.querySelectorAll("[data-tab]")) {
      const selected = button.dataset.tab === this._tab; button.setAttribute("aria-selected", String(selected)); button.tabIndex = selected ? 0 : -1;
    }
    const empty = this.shadowRoot.querySelector(".empty");
    empty.classList.toggle("hidden", data.all.length > 0);
    empty.replaceChildren();
    if (!data.all.length) {
      const title = document.createElement("strong"); title.textContent = data.ambiguous ? "Più gateway rilevati" : "Il tuo G1 deve ancora collegarsi";
      empty.append(title, document.createTextNode(data.ambiguous ? "Seleziona un gateway nell’editor per evitare di combinare impianti diversi." : "Configura RoCon G1 Local con una API key locale oppure seleziona i tuoi sensori nell’editor della scheda. Nessun valore viene simulato in questa vista."));
    }
    this.shadowRoot.querySelector(".overview").classList.toggle("hidden", !data.all.length || this._tab !== "overview");
    this.shadowRoot.querySelector(".detail").classList.toggle("hidden", !data.all.length || ["overview","controls"].includes(this._tab));
    this.shadowRoot.querySelector(".controls").classList.toggle("hidden", this._tab !== "controls" || !data.all.length);
    const controls = data.local.filter(e => /^(number|select|switch|text)\./.test(e.entity_id));
    const native = this.shadowRoot.querySelector(".native-controls");
    if (this._tab === "controls") this._nativeControls(native, controls);
    const settings = this._tab === "settings";
    this._text(".detail .status-note", settings ? "Valori letti dalla cache, consultabili senza controlli di modifica. Abilita i sensori delle impostazioni in Home Assistant se desideri visualizzarli." : "Stato delle entità esposte. Disponibile significa che l’entità ha un valore; non conferma l’assenza di errori o la freschezza della misura.");
    const list = this.shadowRoot.querySelector(".list"); list.replaceChildren();
    const rows = settings ? data.local.filter(e => e.attributes.rocon_section === "setting") : data.all;
    for (const entity of rows) {
      const line = document.createElement("div"); line.className = "line";
      const name = document.createElement("span"); name.textContent = entity.attributes?.friendly_name || entity.attributes?.rocon_field || "Sensore";
      const value = document.createElement("b"); value.textContent = settings ? (this._valid(entity) ? `${entity.state} ${entity.attributes?.unit_of_measurement || ""}` : "Non disponibile") : (this._valid(entity) ? "Disponibile" : "Non disponibile");
      line.append(name,value); list.append(line);
    }
    if (!rows.length) list.textContent = "Nessuna impostazione esposta o abilitata.";
  }
  async _nativeControls(container, entities) {
    if (!entities.length || !window.loadCardHelpers) {
      container.textContent = "I controlli richiedono l’integrazione cloud configurata in Home Assistant. La LAN sperimentale e questa demo non inviano comandi.";
      return;
    }
    const keys = entities.map(e=>e.entity_id).sort().join("|");
    if (this._nativeCard && this._nativeKey === keys) { this._nativeCard.hass=this._hass; return; }
    this._nativeKey=keys;
    try {
      const helpers=await window.loadCardHelpers();
      if (this._nativeKey !== keys || this._tab !== "controls") return;
      const card=helpers.createCardElement({type:"entities",entities:entities.map(e=>({entity:e.entity_id})),show_header_toggle:false});
      card.hass=this._hass; container.replaceChildren(card); this._nativeCard=card;
    } catch { container.textContent="Impossibile caricare i controlli nativi. Apri il dispositivo in Impostazioni → Dispositivi e servizi."; }
  }

}

class RoConClimateCardEditor extends HTMLElement {
  setConfig(config) { this._config = {...config}; this._render(); }
  set hass(hass) { this._hass = hass; if (!this.firstChild) this._render(); else for(const picker of this.querySelectorAll("ha-entity-picker")) picker.hass = hass; }
  _change(key, value, role) {
    const config = {...this._config};
    if (role) { config.entities = {...config.entities}; if (value) config.entities[role]=value; else delete config.entities[role]; }
    else if (value) config[key]=value; else delete config[key];
    this._config=config; this.dispatchEvent(new CustomEvent("config-changed", {detail:{config},bubbles:true,composed:true}));
  }
  _render() {
    if (!this._config || !this._hass) return;
    this.replaceChildren();
    const label = document.createElement("p"); label.textContent = "Rilevamento automatico RoCon cloud o LAN. I sensori aggiunti manualmente restano consultabili; i comandi sono disponibili solo per le entità cloud originali."; this.append(label);
    const title = document.createElement("ha-textfield"); title.label="Titolo"; title.value=this._config.title || "";
    title.addEventListener("input",e=>this._change("title",e.target.value)); this.append(title);
    const gateways = [...new Set(Object.values(this._hass.states).filter(e=>["g1_local_cache","rocon_cloud"].includes(e.attributes?.source)).map(e=>e.attributes.rocon_gateway).filter(Boolean))];
    if (gateways.length>1) {
      const select=document.createElement("select"); select.setAttribute("aria-label","Gateway G1");
      const placeholder=document.createElement("option"); placeholder.value=""; placeholder.textContent="Seleziona gateway"; select.append(placeholder);
      gateways.forEach((gateway,index)=>{const option=document.createElement("option"); option.value=gateway; option.textContent=`Gateway G1 ${index+1}`; select.append(option);});
      select.value=this._config.gateway || ""; select.addEventListener("change",e=>this._change("gateway",e.target.value)); this.append(select);
    }
    for (const [role,name] of [["acs","Temperatura ACS"],["outside","Temperatura esterna"],["boiler","Temperatura caldaia"],["target","Setpoint ACS letto"]]) {
      const picker=document.createElement("ha-entity-picker"); picker.hass=this._hass; picker.label=name; picker.includeDomains=["sensor"]; picker.value=this._config.entities?.[role] || "";
      picker.style.display="block"; picker.style.marginTop="12px";
      picker.addEventListener("value-changed",e=>this._change("entities",e.detail.value,role)); this.append(picker);
    }
  }
}
if (!customElements.get("rocon-climate-card")) customElements.define("rocon-climate-card", RoConClimateCard);
if (!customElements.get("rocon-climate-card-editor")) customElements.define("rocon-climate-card-editor", RoConClimateCardEditor);
window.customCards = window.customCards || [];
if (!window.customCards.some(card=>card.type==="rocon-climate-card")) window.customCards.push({type:"rocon-climate-card",name:"RoCon Climate Studio",description:"ACS, riscaldamento, controlli cloud e diagnostica",preview:true});
