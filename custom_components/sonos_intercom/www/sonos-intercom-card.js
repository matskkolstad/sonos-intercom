/*
 * Sonos Intercom Card (v0.4)
 * Record a voice message or type text, optionally prepend a chime, and announce
 * it on selected speakers via sonos_intercom.announce. Also: preview recordings,
 * custom chime upload, TTS language/voice, an inbox/history with replay + reply +
 * acknowledge, persisted settings, and dimming of unavailable speakers.
 *
 * Reads sensor.sonos_intercom_last_message for the dynamic chime list, the
 * inbox/history and quiet-hours state.
 */

const SENSOR_ID = "sensor.sonos_intercom_last_message";
const CHIME_BASE = "/sonos_intercom_static/chimes/";
const PREFS_KEY = "sonos-intercom";

// Fallback chime list used before the sensor is available.
const STATIC_CHIMES = [
  { id: "airport", label: "Flyplass", url: CHIME_BASE + "airport.mp3" },
  { id: "ding_dong", label: "Ding-dong", url: CHIME_BASE + "ding_dong.mp3" },
  { id: "soft_ping", label: "Mykt pling", url: CHIME_BASE + "soft_ping.mp3" },
  { id: "marimba", label: "Marimba", url: CHIME_BASE + "marimba.mp3" },
  { id: "gong", label: "Gong", url: CHIME_BASE + "gong.mp3" },
];

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
  .quiet { font-size:11.5px; font-weight:650; color:var(--si-coral);
           margin-top:2px; }
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
  textarea:focus, input[type=text]:focus { outline:none; border-color:var(--si-indigo); }
  select, input[type=text] { width:100%; border:1.5px solid var(--si-line);
           border-radius:12px; padding:10px 12px; font-family:inherit; font-size:14px;
           box-sizing:border-box; background:var(--secondary-background-color,#fbfbfe);
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
  .adv { display:flex; gap:8px; } .adv > div { flex:1; }
  .chips { display:flex; flex-wrap:wrap; gap:8px; }
  .chip { font-size:13px; font-weight:550; padding:8px 13px; border-radius:11px;
          cursor:pointer; background:rgba(131,137,207,.10); color:var(--si-soft);
          border:1.5px solid transparent; transition:.15s; }
  .chip.on { background:rgba(131,137,207,.18); color:var(--si-indigo);
             border-color:rgba(131,137,207,.45); }
  .chip.off { opacity:.4; cursor:not-allowed; text-decoration:line-through; }
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
  .inbox { display:flex; flex-direction:column; gap:8px; }
  .msg { display:flex; align-items:center; gap:10px; padding:10px 12px;
         border:1.5px solid var(--si-line); border-radius:12px; }
  .msg .meta { flex:1; min-width:0; }
  .msg .who { font-size:13px; font-weight:600; }
  .msg .txt { font-size:12.5px; color:var(--si-soft); overflow:hidden;
              text-overflow:ellipsis; white-space:nowrap; }
  .msg .acts { display:flex; gap:6px; flex:none; }
  .iconbtn { border:1.5px solid var(--si-line); background:transparent; cursor:pointer;
             border-radius:10px; padding:6px 9px; font-size:13px; color:var(--si-soft); }
  .iconbtn:hover { border-color:var(--si-indigo); color:var(--si-indigo); }
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
    this._chimeVolume = 100;
    this._language = "";
    this._voice = "";
    this._recording = false;
    this._recorder = null;
    this._chunks = [];
    this._blob = null;
    this._timerId = null;
    this._seconds = 0;
    this._previewAudio = null;
    this._rendered = false;
    this._chimeSig = "";
    this._inboxSig = "";
  }

  setConfig(config) {
    this._config = config || {};
    if (typeof this._config.default_volume === "number") {
      this._volume = this._config.default_volume;
    }
    this._loadPrefs();
    this._rendered = false;
  }

  set hass(hass) {
    this._hass = hass;
    if (!this._rendered) this._render();
    else this._updateDynamic();
  }

  getCardSize() { return 8; }

  // --- preferences -------------------------------------------------------
  _prefsKey() { return PREFS_KEY + ":" + (this._config.title || "default"); }

  _loadPrefs() {
    try {
      const raw = window.localStorage.getItem(this._prefsKey());
      if (!raw) return;
      const p = JSON.parse(raw);
      if (typeof p.volume === "number") this._volume = p.volume;
      if (typeof p.chimeVolume === "number") this._chimeVolume = p.chimeVolume;
      if (typeof p.chime === "string") this._chime = p.chime;
      if (typeof p.announce === "boolean") this._announce = p.announce;
      if (typeof p.mode === "string") this._mode = p.mode;
      if (typeof p.language === "string") this._language = p.language;
      if (typeof p.voice === "string") this._voice = p.voice;
    } catch (err) { /* ignore */ }
  }

  _savePrefs() {
    try {
      window.localStorage.setItem(this._prefsKey(), JSON.stringify({
        volume: this._volume, chimeVolume: this._chimeVolume, chime: this._chime,
        announce: this._announce, mode: this._mode,
        language: this._language, voice: this._voice,
      }));
    } catch (err) { /* ignore */ }
  }

  // --- data helpers ------------------------------------------------------
  _sensor() {
    const st = this._hass && this._hass.states;
    if (!st) return null;
    if (st[SENSOR_ID]) return st[SENSOR_ID];
    const id = Object.keys(st).find((k) => k.startsWith("sensor.sonos_intercom"));
    return id ? st[id] : null;
  }

  _availableChimes() {
    const s = this._sensor();
    const list = s && Array.isArray(s.attributes.chimes) ? s.attributes.chimes : null;
    const chimes = [{ id: "none", label: "Ingen", url: null }];
    (list && list.length ? list : STATIC_CHIMES).forEach((c) =>
      chimes.push({ id: c.id, label: c.label, url: c.url }));
    return chimes;
  }

  _chimeUrl(id) {
    const c = this._availableChimes().find((x) => x.id === id);
    return c ? c.url : null;
  }

  _messages() {
    const s = this._sensor();
    return s && Array.isArray(s.attributes.messages) ? s.attributes.messages : [];
  }

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

  _available(entity) {
    const st = this._hass && this._hass.states[entity];
    return !!st && st.state !== "unavailable" && st.state !== "unknown";
  }

  _sourceLabel() {
    return this._config.source || this._config.title || "Intercom";
  }

  // --- render ------------------------------------------------------------
  _render() {
    if (!this._hass) return;
    const speakers = this._speakers();
    if (this._selected.size === 0 && speakers.length) {
      const first = speakers.find((s) => this._available(s.entity)) || speakers[0];
      this._selected.add(first.entity);
    }
    const isRec = this._mode === "record";

    this.shadowRoot.innerHTML = `
      <style>${STYLES}</style>
      <div class="card">
        <div class="top">
          <div class="badge">${MIC_SVG}</div>
          <div><div class="title">${this._config.title || "Intercom"}</div>
            <div class="sub">Send en melding til høyttalerne</div>
            <div class="quiet hidden" id="quiet">🌙 Stille timer aktiv</div></div>
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
            <button class="ghostbtn hidden" id="preview">▶ Lytt på opptaket</button>
          </div>
        </div>

        <div class="ttsblock ${isRec ? "hidden" : ""}">
          <textarea id="ttstext" placeholder="Skriv en melding som leses opp..."></textarea>
          <div style="margin-top:10px">
            <div class="rowhead"><div class="sec">Avansert (stemme/språk)</div></div>
            <div class="adv">
              <div><input type="text" id="lang" placeholder="Språk, f.eks. nb" value="${this._language}"></div>
              <div><input type="text" id="voice" placeholder="Stemme (valgfri)" value="${this._voice}"></div>
            </div>
          </div>
        </div>

        <div>
          <div class="rowhead"><div class="sec">Chime</div>
            <span class="link" id="cpreview">▶ Forhåndsvis</span></div>
          <div class="chimerow">
            <select id="chime"></select>
            <button class="ghostbtn" id="cspk" title="Spill chimen på høyttalerne">🔊</button>
            <button class="ghostbtn" id="cup" title="Last opp egen chime">➕</button>
          </div>
          <div id="cvolwrap" class="${this._chime === "none" ? "hidden" : ""}" style="margin-top:12px">
            <div class="rowhead"><div class="sec">Chime-volum</div>
              <div class="link" id="cvolval">${this._chimeVolume}%</div></div>
            <input type="range" id="cvol" min="0" max="100" value="${this._chimeVolume}">
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
        <button class="ghostbtn" id="replay" style="width:100%">🔁 Spill av igjen</button>

        <div id="inboxwrap">
          <div class="rowhead"><div class="sec">Innboks / historikk</div></div>
          <div class="inbox" id="inbox"></div>
        </div>

        <div class="status" id="status"></div>
      </div>
    `;

    const $ = (id) => this.shadowRoot.getElementById(id);
    this._renderChips();
    this._refreshChimeOptions(true);
    this._renderInbox(true);
    this._refreshQuiet();

    this.shadowRoot.querySelectorAll(".mode").forEach((el) =>
      el.addEventListener("click", () => {
        this._mode = el.dataset.mode; this._savePrefs(); this._render();
      })
    );
    $("rec").addEventListener("click", () => this._toggleRecord());
    $("preview").addEventListener("click", () => this._previewRecording());
    $("selall").addEventListener("click", () => this._toggleAll());
    $("vol").addEventListener("input", (e) => {
      this._volume = Number(e.target.value);
      $("volval").textContent = this._volume + "%"; this._savePrefs();
    });
    $("ann").addEventListener("change", (e) => { this._announce = e.target.checked; this._savePrefs(); });
    $("chime").addEventListener("change", (e) => {
      this._chime = e.target.value;
      const wrap = $("cvolwrap");
      if (wrap) wrap.classList.toggle("hidden", this._chime === "none");
      this._savePrefs();
    });
    $("cvol").addEventListener("input", (e) => {
      this._chimeVolume = Number(e.target.value);
      $("cvolval").textContent = this._chimeVolume + "%"; this._savePrefs();
    });
    $("lang").addEventListener("change", (e) => { this._language = e.target.value.trim(); this._savePrefs(); });
    $("voice").addEventListener("change", (e) => { this._voice = e.target.value.trim(); this._savePrefs(); });
    $("cpreview").addEventListener("click", () => this._previewChime());
    $("cspk").addEventListener("click", () => this._playChimeOnSpeakers());
    $("cup").addEventListener("click", () => this._uploadChime());
    $("send").addEventListener("click", () => this._send());
    $("replay").addEventListener("click", () => this._replay());

    this._rendered = true;
  }

  _updateDynamic() {
    if (!this.shadowRoot.getElementById("chips")) return;
    this._renderChips();
    this._refreshChimeOptions(false);
    this._renderInbox(false);
    this._refreshQuiet();
  }

  _refreshQuiet() {
    const el = this.shadowRoot.getElementById("quiet");
    const s = this._sensor();
    if (el) el.classList.toggle("hidden", !(s && s.attributes.quiet_active));
  }

  _refreshChimeOptions(force) {
    const sel = this.shadowRoot.getElementById("chime");
    if (!sel) return;
    const chimes = this._availableChimes();
    const sig = chimes.map((c) => c.id).join(",");
    if (!force && sig === this._chimeSig) return;
    this._chimeSig = sig;
    sel.innerHTML = chimes.map(
      (c) => `<option value="${c.id}" ${c.id === this._chime ? "selected" : ""}>${c.label}</option>`
    ).join("");
    sel.value = this._chime;
  }

  _renderChips() {
    const wrap = this.shadowRoot.getElementById("chips");
    if (!wrap) return;
    wrap.innerHTML = "";
    this._speakers().forEach((sp) => {
      const ok = this._available(sp.entity);
      const chip = document.createElement("div");
      chip.className = "chip" + (this._selected.has(sp.entity) ? " on" : "") + (ok ? "" : " off");
      chip.textContent = sp.name || this._name(sp.entity);
      if (ok) {
        chip.addEventListener("click", () => {
          if (this._selected.has(sp.entity)) this._selected.delete(sp.entity);
          else this._selected.add(sp.entity);
          this._renderChips();
        });
      } else {
        chip.title = "Utilgjengelig";
      }
      wrap.appendChild(chip);
    });
  }

  _renderInbox(force) {
    const wrap = this.shadowRoot.getElementById("inbox");
    const box = this.shadowRoot.getElementById("inboxwrap");
    if (!wrap || !box) return;
    const msgs = this._messages();
    const sig = msgs.length + "|" + (msgs[0] ? msgs[0].time : "");
    if (!force && sig === this._inboxSig) return;
    this._inboxSig = sig;
    box.classList.toggle("hidden", msgs.length === 0);
    wrap.innerHTML = "";
    msgs.slice(0, 8).forEach((m, i) => {
      const summary = m.message ? m.message
        : m.kind === "recording" ? "[Opptak]" : "[Chime]";
      const who = m.source || (Array.isArray(m.targets) ? m.targets.map((t) => this._name(t)).join(", ") : "—");
      const when = this._fmtTime(m.time);
      const row = document.createElement("div");
      row.className = "msg";
      row.innerHTML = `
        <div class="meta">
          <div class="who">${this._esc(who)}${when ? ` · ${when}` : ""}</div>
          <div class="txt">${this._esc(summary)}</div>
        </div>
        <div class="acts">
          <button class="iconbtn" data-act="play" title="Spill av igjen">▶</button>
          <button class="iconbtn" data-act="reply" title="Svar">↩︎</button>
          <button class="iconbtn" data-act="ack" title="Kvitter mottatt">✔</button>
        </div>`;
      row.querySelector('[data-act="play"]').addEventListener("click", () => this._replayIndex(i));
      row.querySelector('[data-act="reply"]').addEventListener("click", () => this._reply(m));
      row.querySelector('[data-act="ack"]').addEventListener("click", () => this._acknowledge(m));
      wrap.appendChild(row);
    });
  }

  _fmtTime(iso) {
    try {
      return new Date(iso).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
    } catch (err) { return ""; }
  }

  _esc(s) {
    return String(s == null ? "" : s)
      .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  }

  _toggleAll() {
    const speakers = this._speakers().filter((s) => this._available(s.entity));
    const allOn = speakers.length && speakers.every((s) => this._selected.has(s.entity));
    if (allOn) speakers.forEach((s) => this._selected.delete(s.entity));
    else speakers.forEach((s) => this._selected.add(s.entity));
    this._renderChips();
  }

  _setStatus(msg, isErr) {
    const el = this.shadowRoot.getElementById("status");
    if (el) { el.textContent = msg || ""; el.className = "status" + (isErr ? " err" : ""); }
  }

  // --- chime preview / upload -------------------------------------------
  _previewChime() {
    const url = this._chimeUrl(this._chime);
    if (!url) { this._setStatus("Velg en chime for å forhåndsvise."); return; }
    try {
      if (this._previewAudio) this._previewAudio.pause();
      this._previewAudio = new Audio(url);
      this._previewAudio.play();
      this._setStatus("Forhåndsviser i nettleseren ♪");
    } catch (err) {
      this._setStatus("Kunne ikke spille av forhåndsvisning.", true);
    }
  }

  async _playChimeOnSpeakers() {
    if (this._chime === "none") { this._setStatus("Velg en chime først."); return; }
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

  _uploadChime() {
    const input = document.createElement("input");
    input.type = "file";
    input.accept = "audio/*";
    input.addEventListener("change", async () => {
      const file = input.files && input.files[0];
      if (!file) return;
      try {
        this._setStatus("Laster opp chime...");
        const audio = await this._blobToBase64(file);
        const ext = (file.name.split(".").pop() || "mp3").toLowerCase();
        const name = file.name.replace(/\.[^.]+$/, "");
        const resp = await this._hass.callApi("POST", "sonos_intercom/chime_upload", {
          audio, format: ext, name,
        });
        if (resp && resp.id) {
          this._chime = resp.id; this._savePrefs();
          this._refreshChimeOptions(true);
          this._setStatus("Chime lastet opp ✓");
        } else {
          this._setStatus("Opplasting feilet.", true);
        }
      } catch (err) {
        this._setStatus("Noe gikk galt: " + (err.message || err), true);
      }
    });
    input.click();
  }

  // --- recording ---------------------------------------------------------
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
        const preview = this.shadowRoot.getElementById("preview");
        if (preview) preview.classList.remove("hidden");
        this._setStatus("Opptak klart - lytt eller send.");
      };
      this._recorder.start();
      this._recording = true;
      this._seconds = 0;
      const btn = this.shadowRoot.getElementById("rec");
      const timer = this.shadowRoot.getElementById("timer");
      const hint = this.shadowRoot.getElementById("rechint");
      const preview = this.shadowRoot.getElementById("preview");
      if (preview) preview.classList.add("hidden");
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

  _previewRecording() {
    if (!this._blob) { this._setStatus("Ingen opptak å lytte på."); return; }
    try {
      if (this._previewAudio) this._previewAudio.pause();
      this._previewAudio = new Audio(URL.createObjectURL(this._blob));
      this._previewAudio.play();
      this._setStatus("Spiller av opptaket ♪");
    } catch (err) {
      this._setStatus("Kunne ikke spille av opptaket.", true);
    }
  }

  _blobToBase64(blob) {
    return new Promise((resolve, reject) => {
      const r = new FileReader();
      r.onloadend = () => resolve(String(r.result).split(",")[1]);
      r.onerror = reject;
      r.readAsDataURL(blob);
    });
  }

  // --- send / replay / reply / acknowledge -------------------------------
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
          audio_url: resp.url, targets, volume: this._volume,
          announce: this._announce, source: this._sourceLabel(),
        };
        if (chime) { data.chime = chime; data.chime_volume = this._chimeVolume; }
        await this._hass.callService("sonos_intercom", "announce", data);
        this._blob = null;
        const preview = this.shadowRoot.getElementById("preview");
        if (preview) preview.classList.add("hidden");
        this._setStatus("Melding sendt ✓");
      } else {
        const text = this.shadowRoot.getElementById("ttstext").value.trim();
        if (!text) { this._setStatus("Skriv en melding først.", true); return; }
        const data = {
          message: text, targets, volume: this._volume,
          announce: this._announce, source: this._sourceLabel(),
        };
        if (chime) { data.chime = chime; data.chime_volume = this._chimeVolume; }
        if (this._language) data.language = this._language;
        if (this._voice) data.voice = this._voice;
        await this._hass.callService("sonos_intercom", "announce", data);
        this._setStatus("Melding sendt ✓");
      }
    } catch (err) {
      this._setStatus("Noe gikk galt: " + (err.message || err), true);
    } finally {
      sendBtn.disabled = false;
    }
  }

  async _replay() {
    const targets = Array.from(this._selected);
    const data = { volume: this._volume, index: 0 };
    if (targets.length) data.targets = targets;
    try {
      await this._hass.callService("sonos_intercom", "replay", data);
      this._setStatus("Spiller av forrige melding ✓");
    } catch (err) {
      this._setStatus("Noe gikk galt: " + (err.message || err), true);
    }
  }

  async _replayIndex(index) {
    try {
      await this._hass.callService("sonos_intercom", "replay", { index });
      this._setStatus("Spiller av melding ✓");
    } catch (err) {
      this._setStatus("Noe gikk galt: " + (err.message || err), true);
    }
  }

  _reply(msg) {
    const targets = Array.isArray(msg.targets) ? msg.targets : [];
    if (targets.length) {
      this._selected = new Set(targets);
      this._renderChips();
    }
    const who = msg.source || (targets.map((t) => this._name(t)).join(", "));
    this._setStatus("Svarer til " + (who || "avsender") + " – skriv eller spill inn.");
  }

  async _acknowledge(msg) {
    const data = {};
    if (Array.isArray(msg.targets) && msg.targets.length) data.targets = msg.targets;
    try {
      await this._hass.callService("sonos_intercom", "acknowledge", data);
      this._setStatus("Kvittering sendt ✓");
    } catch (err) {
      this._setStatus("Noe gikk galt: " + (err.message || err), true);
    }
  }
}

if (!customElements.get("sonos-intercom-card")) {
  customElements.define("sonos-intercom-card", SonosIntercomCard);
}

window.customCards = window.customCards || [];
window.customCards.push({
  type: "sonos-intercom-card",
  name: "Sonos Intercom Card",
  description: "Spill inn eller skriv en melding, legg på en chime, og annonser på Sonos.",
});

console.info("%c SONOS-INTERCOM-CARD %c v0.4.0 ",
  "color:#fff;background:#8389cf;border-radius:4px 0 0 4px;padding:2px 6px",
  "color:#8389cf;background:#eef0fb;border-radius:0 4px 4px 0;padding:2px 6px");
