/*
 * Sonos Intercom Card (v0.2)
 * Record a voice message or type text, optionally prepend a chime, and
 * announce it on selected Sonos speakers via sonos_intercom.announce.
 */

const CHIMES = [
  { id: "none", label: "Ingen", file: null },
  { id: "airport", label: "Flyplass", file: "airport.mp3" },
  { id: "ding_dong", label: "Ding-dong", file: "ding_dong.mp3" },
  { id: "soft_ping", label: "Mykt pling", file: "soft_ping.mp3" },
  { id: "marimba", label: "Marimba", file: "marimba.mp3" },
  { id: "gong", label: "Gong", file: "gong.mp3" },
];
const CHIME_BASE = "/sonos_intercom_static/chimes/";

const STYLES = `
  :host { --si-indigo:#8389cf; --si-coral:#e2998b; --si-sage:#84b6a6;
          --si-ink:#34343f; --si-soft:#7d7d92; --si-line:#ecebf3; }
  .card { background: var(--card-background-color, #fff);
          border-radius: 22px; padding: 20px;
          box-shadow: var(--ha-card-box-shadow, 0 10px 30px rgba(80,80,130,.10));
          font-family: var(--paper-font-body1_-_font-family, "Segoe UI", sans-serif);
          color: var(--primary-text-color, var(--si-ink)); display:flex;
          flex-direction:column; gap:16px; }
  .top { display:flex; align-items:center; gap:12px; }
  .badge { width:42px; height:42px; border-radius:13px; flex:none; display:grid;
           place-items:center; color:#fff;
           background:linear-gradient(140deg,var(--si-indigo),#a6abe0); }
  .title { font-size:16px; font-weight:650; }
  .sub { font-size:12.5px; color:var(--si-soft); }
  .modes { display:flex; background:rgba(131,137,207,.10); border-radius:13px;
           padding:4px; gap:4px; }
  .mode { flex:1; text-align:center; font-size:13.5px; font-weight:600;
          color:var(--si-soft); padding:9px 0; border-radius:10px; cursor:pointer; }
  .mode.active { background:var(--card-background-color,#fff);
                 color:var(--primary-text-color,var(--si-ink));
                 box-shadow:0 2px 8px rgba(90,90,140,.10); }
  .reczone { display:flex; flex-direction:column; align-items:center; gap:10px; }
  .recbtn { width:84px; height:84px; border-radius:50%; border:none; cursor:pointer;
            color:#fff; display:grid; place-items:center;
            background:linear-gradient(145deg,var(--si-coral),#ecb1a5);
            box-shadow:0 10px 24px rgba(226,153,139,.45); transition:transform .15s; }
  .recbtn:hover { transform:translateY(-2px) scale(1.02); }
  .recbtn.live { animation:si-pulse 1.4s infinite; }
  @keyframes si-pulse { 0%{box-shadow:0 0 0 0 rgba(217,125,108,.45)}
    70%{box-shadow:0 0 0 18px rgba(217,125,108,0)}
    100%{box-shadow:0 0 0 0 rgba(217,125,108,0)} }
  .hint { font-size:13px; color:var(--si-soft); }
  .timer { font-size:20px; font-weight:650; font-variant-numeric:tabular-nums; }
  textarea { width:100%; border:1.5px solid var(--si-line); border-radius:14px;
             padding:12px 14px; font-family:inherit; font-size:14px; resize:none;
             min-height:84px; box-sizing:border-box;
             background:var(--secondary-background-color,#fbfbfe);
             color:var(--primary-text-color,var(--si-ink)); }
  textarea:focus { outline:none; border-color:var(--si-indigo); }
  select { width:100%; border:1.5px solid var(--si-line); border-radius:12px;
           padding:10px 12px; font-family:inherit; font-size:14px; box-sizing:border-box;
           background:var(--secondary-background-color,#fbfbfe);
           color:var(--primary-text-color,var(--si-ink)); }
  .sec { font-size:12px; font-weight:650; color:var(--si-soft);
         text-transform:uppercase; letter-spacing:.05em; }
  .rowhead { display:flex; justify-content:space-between; align-items:center;
             margin-bottom:8px; }
  .link { font-size:12.5px; font-weight:600; color:var(--si-indigo); cursor:pointer; }
  .chimerow { display:flex; gap:8px; align-items:center; }
  .chimerow select { flex:1; }
  .ghostbtn { border:1.5px solid var(--si-line); background:transparent;
              color:var(--si-soft); border-radius:12px; padding:10px 12px;
              font-family:inherit; font-size:13px; font-weight:600; cursor:pointer;
              white-space:nowrap; }
  .ghostbtn:hover { border-color:var(--si-indigo); color:var(--si-indigo); }
  .chips { display:flex; flex-wrap:wrap; gap:8px; }
  .chip { font-size:13px; font-weight:550; padding:8px 13px; border-radius:11px;
          cursor:pointer; background:rgba(131,137,207,.10); color:var(--si-soft);
          border:1.5px solid transparent; transition:.15s; }
  .chip.on { background:rgba(131,137,207,.18); color:var(--si-indigo);
             border-color:rgba(131,137,207,.45); }
  input[type=range] { width:100%; accent-color:var(--si-indigo); }
  .togglerow { display:flex; align-items:center; justify-content:space-between;
               background:rgba(132,182,166,.16); border-radius:14px; padding:12px 14px; }
  .togglerow strong { font-size:13.5px; } .togglerow small { display:block;
               font-size:11.5px; color:var(--si-soft); margin-top:2px; }
  .send { border:none; cursor:pointer; width:100%; padding:14px; border-radius:15px;
          font-family:inherit; font-size:15px; font-weight:650; color:#fff;
          background:linear-gradient(135deg,var(--si-indigo),#9b9fdb);
          box-shadow:0 8px 20px rgba(131,137,207,.4); transition:transform .15s; }
  .send:hover { transform:translateY(-2px); }
  .send:disabled { opacity:.5; cursor:default; transform:none; }
  .status { font-size:12px; color:var(--si-soft); text-align:center; min-height:16px; }
  .status.err { color:var(--si-coral); }
  .hidden { display:none; }
`;

const MIC_SVG = '<svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"/><path d="M19 10v2a7 7 0 0 1-14 0v-2"/><line x1="12" y1="19" x2="12" y2="23"/><line x1="8" y1="23" x2="16" y2="23"/></svg>';
const STOP_SVG = '<svg width="26" height="26" viewBox="0 0 24 24" fill="currentColor"><rect x="6" y="6" width="12" height="12" rx="2.5"/></svg>';

class SonosIntercomCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._mode = "record";
    this._selected = new Set();
    this._announce = true;
    this._volume = 40;
    this._chime = "none";
    this._recording = false;
    this._recorder = null;
    this._chunks = [];
    this._blob = null;
    this._timerId = null;
    this._seconds = 0;
    this._previewAudio = null;
    this._rendered = false;
  }

  setConfig(config) {
    this._config = config || {};
    if (typeof this._config.default_volume === "number") {
      this._volume = this._config.default_volume;
    }
    this._rendered = false;
  }

  set hass(hass) {
    this._hass = hass;
    if (!this._rendered) this._render();
  }

  getCardSize() { return 6; }

  _speakers() {
    const cfg = this._config.entities;
    if (Array.isArray(cfg) && cfg.length) {
      return cfg.map((e) => (typeof e === "string" ? { entity: e } : e));
    }
    if (!this._hass) return [];
    return Object.keys(this._hass.states)
      .filter((id) => id.startsWith("media_player."))
      .map((id) => ({ entity: id }));
  }

  _name(entity) {
    const st = this._hass && this._hass.states[entity];
    return (st && st.attributes.friendly_name) || entity.split(".")[1];
  }

  _render() {
    if (!this._hass) return;
    const speakers = this._speakers();
    if (this._selected.size === 0 && speakers.length) {
      this._selected.add(speakers[0].entity);
    }
    const isRec = this._mode === "record";
    const chimeOptions = CHIMES.map(
      (c) => `<option value="${c.id}" ${c.id === this._chime ? "selected" : ""}>${c.label}</option>`
    ).join("");

    this.shadowRoot.innerHTML = `
      <style>${STYLES}</style>
      <div class="card">
        <div class="top">
          <div class="badge">${MIC_SVG}</div>
          <div><div class="title">${this._config.title || "Intercom"}</div>
            <div class="sub">Send en melding til høyttalerne</div></div>
        </div>
        <div class="modes">
          <div class="mode ${isRec ? "active" : ""}" data-mode="record">Opptak</div>
          <div class="mode ${isRec ? "" : "active"}" data-mode="tts">Tekst</div>
        </div>

        <div class="recblock ${isRec ? "" : "hidden"}">
          <div class="reczone">
            <button class="recbtn" id="rec">${MIC_SVG}</button>
            <div class="hint" id="rechint">Trykk for å spille inn</div>
            <div class="timer hidden" id="timer">00:00</div>
          </div>
        </div>

        <div class="ttsblock ${isRec ? "hidden" : ""}">
          <textarea id="ttstext" placeholder="Skriv en melding som leses opp..."></textarea>
        </div>

        <div>
          <div class="rowhead"><div class="sec">Chime</div>
            <span class="link" id="cpreview">▶ Forhåndsvis</span></div>
          <div class="chimerow">
            <select id="chime">${chimeOptions}</select>
            <button class="ghostbtn" id="cspk" title="Spill chimen på høyttalerne">🔊 Høyttalere</button>
          </div>
        </div>

        <div>
          <div class="rowhead"><div class="sec">Høyttalere</div>
            <div class="link" id="selall">Velg alle</div></div>
          <div class="chips" id="chips"></div>
        </div>

        <div>
          <div class="rowhead"><div class="sec">Volum</div>
            <div class="link" id="volval">${this._volume}%</div></div>
          <input type="range" id="vol" min="0" max="100" value="${this._volume}">
        </div>

        <div class="togglerow">
          <div><strong>Announce</strong><small>Demp musikken og gjenopprett etterpå</small></div>
          <ha-switch id="ann" ${this._announce ? "checked" : ""}></ha-switch>
        </div>

        <button class="send" id="send">${isRec ? "Spill av melding" : "Les opp melding"}</button>
        <div class="status" id="status"></div>
      </div>
    `;

    this._renderChips();
    const $ = (id) => this.shadowRoot.getElementById(id);

    this.shadowRoot.querySelectorAll(".mode").forEach((el) =>
      el.addEventListener("click", () => { this._mode = el.dataset.mode; this._render(); })
    );
    $("rec").addEventListener("click", () => this._toggleRecord());
    $("selall").addEventListener("click", () => this._toggleAll());
    $("vol").addEventListener("input", (e) => {
      this._volume = Number(e.target.value);
      $("volval").textContent = this._volume + "%";
    });
    $("ann").addEventListener("change", (e) => { this._announce = e.target.checked; });
    $("chime").addEventListener("change", (e) => { this._chime = e.target.value; });
    $("cpreview").addEventListener("click", () => this._previewChime());
    $("cspk").addEventListener("click", () => this._playChimeOnSpeakers());
    $("send").addEventListener("click", () => this._send());

    this._rendered = true;
  }

  _renderChips() {
    const wrap = this.shadowRoot.getElementById("chips");
    if (!wrap) return;
    wrap.innerHTML = "";
    this._speakers().forEach((sp) => {
      const chip = document.createElement("div");
      chip.className = "chip" + (this._selected.has(sp.entity) ? " on" : "");
      chip.textContent = sp.name || this._name(sp.entity);
      chip.addEventListener("click", () => {
        if (this._selected.has(sp.entity)) this._selected.delete(sp.entity);
        else this._selected.add(sp.entity);
        this._renderChips();
      });
      wrap.appendChild(chip);
    });
  }

  _toggleAll() {
    const speakers = this._speakers();
    if (this._selected.size === speakers.length) this._selected.clear();
    else speakers.forEach((s) => this._selected.add(s.entity));
    this._renderChips();
  }

  _setStatus(msg, isErr) {
    const el = this.shadowRoot.getElementById("status");
    if (el) { el.textContent = msg || ""; el.className = "status" + (isErr ? " err" : ""); }
  }

  _chimeFile(id) {
    const c = CHIMES.find((x) => x.id === id);
    return c ? c.file : null;
  }

  _previewChime() {
    const file = this._chimeFile(this._chime);
    if (!file) { this._setStatus("Velg en chime for å forhåndsvise."); return; }
    try {
      if (this._previewAudio) { this._previewAudio.pause(); }
      this._previewAudio = new Audio(CHIME_BASE + file);
      this._previewAudio.play();
      this._setStatus("Forhåndsviser i nettleseren ♪");
    } catch (err) {
      this._setStatus("Kunne ikke spille av forhåndsvisning.", true);
    }
  }

  async _playChimeOnSpeakers() {
    const file = this._chimeFile(this._chime);
    if (!file) { this._setStatus("Velg en chime først."); return; }
    const targets = Array.from(this._selected);
    if (!targets.length) { this._setStatus("Velg minst én høyttaler.", true); return; }
    try {
      await this._hass.callService("sonos_intercom", "announce", {
        chime: this._chime, targets, volume: this._volume, announce: this._announce,
      });
      this._setStatus("Chime spilt på høyttalerne ✓");
    } catch (err) {
      this._setStatus("Noe gikk galt: " + (err.message || err), true);
    }
  }

  async _toggleRecord() {
    if (this._recording) { this._stopRecord(); return; }
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      this._setStatus("Mikrofon krever HTTPS-tilkobling til HA.", true);
      return;
    }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mime = MediaRecorder.isTypeSupported("audio/webm") ? "audio/webm" : "";
      this._recorder = new MediaRecorder(stream, mime ? { mimeType: mime } : undefined);
      this._chunks = [];
      this._recorder.ondataavailable = (e) => { if (e.data.size) this._chunks.push(e.data); };
      this._recorder.onstop = () => {
        this._blob = new Blob(this._chunks, { type: "audio/webm" });
        stream.getTracks().forEach((t) => t.stop());
        this._setStatus("Opptak klart - trykk for å sende.");
      };
      this._recorder.start();
      this._recording = true;
      this._seconds = 0;
      const btn = this.shadowRoot.getElementById("rec");
      const timer = this.shadowRoot.getElementById("timer");
      const hint = this.shadowRoot.getElementById("rechint");
      btn.classList.add("live"); btn.innerHTML = STOP_SVG;
      hint.classList.add("hidden"); timer.classList.remove("hidden");
      this._timerId = setInterval(() => {
        this._seconds += 1;
        const m = String(Math.floor(this._seconds / 60)).padStart(2, "0");
        const s = String(this._seconds % 60).padStart(2, "0");
        if (timer) timer.textContent = `${m}:${s}`;
      }, 1000);
      this._setStatus("Spiller inn...");
    } catch (err) {
      this._setStatus("Fikk ikke tilgang til mikrofon.", true);
    }
  }

  _stopRecord() {
    if (this._recorder && this._recorder.state !== "inactive") this._recorder.stop();
    this._recording = false;
    clearInterval(this._timerId);
    const btn = this.shadowRoot.getElementById("rec");
    if (btn) { btn.classList.remove("live"); btn.innerHTML = MIC_SVG; }
  }

  _blobToBase64(blob) {
    return new Promise((resolve, reject) => {
      const r = new FileReader();
      r.onloadend = () => resolve(String(r.result).split(",")[1]);
      r.onerror = reject;
      r.readAsDataURL(blob);
    });
  }

  async _send() {
    const targets = Array.from(this._selected);
    if (!targets.length) { this._setStatus("Velg minst én høyttaler.", true); return; }
    const sendBtn = this.shadowRoot.getElementById("send");
    sendBtn.disabled = true;
    const chime = this._chime !== "none" ? this._chime : undefined;

    try {
      if (this._mode === "record") {
        if (this._recording) this._stopRecord();
        if (!this._blob) { this._setStatus("Ingen melding spilt inn.", true); return; }
        this._setStatus("Sender opptak...");
        const audio = await this._blobToBase64(this._blob);
        const resp = await this._hass.callApi("POST", "sonos_intercom/upload", {
          audio, format: "webm",
        });
        if (!resp || !resp.url) { this._setStatus("Opplasting feilet.", true); return; }
        const data = {
          audio_url: resp.url, targets, volume: this._volume, announce: this._announce,
        };
        if (chime) data.chime = chime;
        await this._hass.callService("sonos_intercom", "announce", data);
        this._blob = null;
        this._setStatus("Melding sendt ✓");
      } else {
        const text = this.shadowRoot.getElementById("ttstext").value.trim();
        if (!text) { this._setStatus("Skriv en melding først.", true); return; }
        const data = {
          message: text, targets, volume: this._volume, announce: this._announce,
        };
        if (chime) data.chime = chime;
        await this._hass.callService("sonos_intercom", "announce", data);
        this._setStatus("Melding sendt ✓");
      }
    } catch (err) {
      this._setStatus("Noe gikk galt: " + (err.message || err), true);
    } finally {
      sendBtn.disabled = false;
    }
  }
}

customElements.define("sonos-intercom-card", SonosIntercomCard);

window.customCards = window.customCards || [];
window.customCards.push({
  type: "sonos-intercom-card",
  name: "Sonos Intercom Card",
  description: "Spill inn eller skriv en melding, legg på en chime, og annonser på Sonos.",
});

console.info("%c SONOS-INTERCOM-CARD %c v0.2.1 ",
  "color:#fff;background:#8389cf;border-radius:4px 0 0 4px;padding:2px 6px",
  "color:#8389cf;background:#eef0fb;border-radius:0 4px 4px 0;padding:2px 6px");
