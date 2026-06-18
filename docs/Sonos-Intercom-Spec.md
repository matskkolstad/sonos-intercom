# Sonos Intercom — Design- og spesifikasjonsdokument

**Arbeidstittel:** Sonos Intercom
**Type:** Custom integrasjon for Home Assistant (installeres via HACS) + tilhørende Lovelace-kort
**Versjon:** Utkast 0.1 (designfase)
**Sist oppdatert:** 2026-06-18

---

## 1. Mål og konsept

Sonos Intercom skal gi Home Assistant-brukere en «intercom»-opplevelse for Sonos-høyttalerne sine: muligheten til å enten skrive inn tekst (tekst-til-tale) eller spille inn en lydmelding via mikrofonen i nettleseren/enheten, og få meldingen annonsert på enten alle eller utvalgte høyttalere.

Det som finnes i Home Assistant fra før dekker TTS og «announce» (ducking), men ingen samler dette til én pakke, og ingen løser mikrofon-innspilling fra et dashboard. Sonos Intercom fyller dette hullet.

Kjerneprinsipper for designet:

- **Lokalt først.** Ingen avhengighet av Sonos sitt sky-API i v1. Alt går gjennom Home Assistant sin innebygde Sonos-integrasjon (lokal UPnP).
- **Ingen eksterne avhengigheter i v1.** Vi bygger oppå det som allerede finnes i HA, ikke oppå Chime TTS eller andre tredjeparts-integrasjoner. (Chime TTS kan bli et valgfritt backend senere.)
- **Service-kallet er hjertet.** Kortet er bare en frontend. All logikk eksponeres som et service-kall slik at automasjoner, scripts og Node-RED kan bruke det samme.
- **Generisk på innsiden, Sonos-spesifikt i praksis.** Service-API-et utformes slik at det senere kan utvides til andre `media_player` uten å bryte eksisterende oppsett.

---

## 2. Bakgrunn — hva finnes, hva mangler

| Behov | Finnes i HA i dag? | Kommentar |
|-------|--------------------|-----------|
| Tekst-til-tale på Sonos | Ja | Via `tts.*` + `media_player.play_media` |
| «Announce» / ducking (demp musikk, spill melding oppå, gjenopprett) | Ja | Via `announce: true` på Sonos S2 |
| Volum per annonsering | Ja | Via `extra: { volume: ... }` |
| Velge én eller flere høyttalere | Ja (delvis) | Synk på grupper er svak — gir «ekko» ved flere mål |
| Snapshot/restore av pågående avspilling | Ja | Via `sonos.snapshot` / `sonos.restore` |
| **Spille inn lydmelding via mikrofon fra dashboard** | **Nei** | Dette er det reelle hullet |
| Samlet kort + service for hele intercom-flyten | Nei | Finnes bare som løse biter |

Konklusjon: Vi gjenbruker TTS og announce, og bygger det nye laget (mikrofon, kort, samlet service, synk-håndtering) rundt det.

---

## 3. Arkitektur

Løsningen består av tre lag.

```
┌──────────────────────────────────────────────────────────────┐
│  1. FRONTEND (nettleser)                                        │
│     Lovelace-kort: opptaksknapp, TTS-felt, høyttalervelger,    │
│     volum, announce-toggle                                      │
│     - MediaRecorder API tar opp lyd (krever HTTPS i nettleser) │
└───────────────┬──────────────────────────────┬────────────────┘
                │ lyd-blob (opptak)             │ service-kall (TTS / klar fil)
                ▼                                ▼
┌──────────────────────────────────────────────────────────────┐
│  2. BACKEND (custom_component i Home Assistant)                 │
│     - HTTP-endepunkt mottar opptak → ffmpeg → MP3 → lagres     │
│     - Service `sonos_intercom.announce`                         │
│     - Snapshot → grupper → annonser → opphev → restore         │
└───────────────┬──────────────────────────────────────────────┘
                │ media_player.play_media (announce: true)
                ▼
┌──────────────────────────────────────────────────────────────┐
│  3. AVSPILLING (HA innebygd Sonos-integrasjon → høyttalere)    │
│     Sonos-høyttaleren henter selv MP3-fila fra HA over LAN     │
└──────────────────────────────────────────────────────────────┘
```

**Viktig nyanse:** Mikrofontilgang i nettleseren krever HTTPS (sikker kontekst). Men selve lydfila hentes av Sonos-høyttaleren fra Home Assistant over det lokale nettet (intern URL). Disse to tingene er uavhengige — du kan derfor betjene kortet over HTTPS-domenet og likevel servere fila lokalt til høyttalerne.

---

## 4. Komponenter

### 4.1 Backend — custom_component

En vanlig Home Assistant custom integrasjon skrevet i Python. Ansvar:

- Registrere service-kallet `sonos_intercom.announce`.
- Registrere et HTTP-view som tar imot innspilt lyd fra kortet.
- Konvertere opptak til MP3 med ffmpeg (følger med HA) og lagre i et tilgjengelig område.
- Håndtere snapshot, midlertidig gruppering, annonsering og gjenoppretting for synkron avspilling på flere høyttalere.
- Config-flow for standardinnstillinger.

### 4.2 HTTP-endepunkt for opptak

Kortet sender lyd-bloben (WebM/Opus fra `MediaRecorder`) til et endepunkt registrert av integrasjonen, f.eks. `/api/sonos_intercom/upload`. Backend:

1. Tar imot bloben (autentisert via HA sin innebygde auth).
2. Konverterer til MP3 med ffmpeg (announce fungerer best med MP3 — FLAC har kjente problemer).
3. Lagrer fila i `/media` eller `/config/www` (konfigurerbart), evt. med opprydding av gamle opptak.
4. Returnerer en intern URL som Sonos kan hente fra.

### 4.3 Service: `sonos_intercom.announce`

Det sentrale service-kallet. Designet generisk slik at det dekker både TTS og ferdig lydfil.

| Parameter | Type | Påkrevd | Beskrivelse |
|-----------|------|---------|-------------|
| `message` | string | Enten denne eller `audio_url` | Tekst som leses opp via TTS |
| `audio_url` | string | Enten denne eller `message` | URL til ferdig lydfil (f.eks. fra opptak) |
| `targets` | liste | Ja | Høyttalere meldingen skal spilles på |
| `volume` | number / objekt | Nei | Felles volum, eller per-høyttaler volum |
| `announce` | bool | Nei (default `true`) | Om musikk skal dempes og gjenopprettes |
| `tts_engine` | string | Nei | Hvilken TTS-motor som skal brukes for `message` |
| `chime` | string | Nei (v2) | Valgfri lyd som spilles foran meldingen |

Eksempel (TTS):

```yaml
action: sonos_intercom.announce
data:
  message: "Middagen er klar"
  targets:
    - media_player.kjokken
    - media_player.stue
  volume: 35
  announce: true
```

Eksempel (ferdig lydfil / opptak):

```yaml
action: sonos_intercom.announce
data:
  audio_url: "http://192.168.x.x:8123/media/intercom/opptak_123.mp3"
  targets:
    - media_player.alle_oppe
  volume:
    media_player.soverom: 20
    media_player.bad: 40
  announce: true
```

### 4.4 Synkron avspilling på flere høyttalere

For å unngå «ekko»-effekten ved annonsering til flere mål samtidig, gjør backend følgende sekvens:

1. `sonos.snapshot` på de valgte høyttalerne (lagrer tilstand).
2. `media_player.join` — grupper de valgte høyttalerne midlertidig under én koordinator.
3. Sett volum (felles eller per-høyttaler).
4. `media_player.play_media` med `announce: true` mot koordinatoren — spilles i synk.
5. Vent til meldingen er ferdig.
6. `media_player.unjoin` — opphev midlertidig gruppe.
7. `sonos.restore` — gjenopprett opprinnelig tilstand og avspilling.

Dette gir ekte synkron annonsering uten ekstern avhengighet.

### 4.5 Lovelace-kort

En frontend-modul (lit/JavaScript) som ligger i samme HACS-repo. Kortet er en ren frontend som til slutt kaller `sonos_intercom.announce`. Funksjoner i v1:

- Modusvelger: **Opptak** (mikrofon) / **Tekst** (TTS).
- Stor opptaksknapp med tydelig opptak-pågår-tilstand (timer + visualisering).
- Tekstfelt for TTS.
- Høyttalervelger med «velg alle» og mulighet for å huke av enkelthøyttalere.
- Volum: felles slider, med mulighet for å folde ut per-høyttaler-volum.
- Announce-toggle (demp/gjenopprett pågående lyd).
- Send/spill-knapp.
- Liten statuslinje / siste melding.

### 4.6 Config-flow

Standard HA-innstillingsskjerm for integrasjonen, som dekker:

- Standardvolum.
- Standard-høyttalere.
- Lagringssti for opptak (`/media` vs `/config/www`).
- Oppbevaringstid / opprydding av gamle opptak.
- (Senere) valg av backend: innebygd announce vs. Chime TTS.

Et fullt eget admin-panel er **ikke** nødvendig for v1 — config-flow dekker behovet.

---

## 5. Dataflyt steg for steg

**Mikrofon-flyt:**

1. Bruker trykker opptaksknappen i kortet (nettleser ber om mikrofontilgang — krever HTTPS).
2. `MediaRecorder` tar opp → lyd-blob.
3. Kortet sender bloben til `/api/sonos_intercom/upload`.
4. Backend konverterer til MP3, lagrer fila, returnerer intern URL.
5. Kortet kaller `sonos_intercom.announce` med `audio_url` + valgte høyttalere/volum/announce.
6. Backend kjører snapshot → grupper → annonser → opphev → restore.
7. Sonos-høyttalerne henter MP3-fila lokalt og spiller den i synk.

**TTS-flyt:**

1. Bruker skriver tekst, velger høyttalere/volum/announce.
2. Kortet kaller `sonos_intercom.announce` med `message`.
3. Backend genererer TTS-URL via valgt TTS-motor.
4. Samme snapshot/grupper/annonser/restore-sekvens som over.

---

## 6. Repo-struktur

```
sonos-intercom/
├── custom_components/
│   └── sonos_intercom/
│       ├── __init__.py          # oppsett, registrering av service + HTTP-view
│       ├── manifest.json        # metadata, avhengigheter
│       ├── config_flow.py       # innstillingsskjerm
│       ├── const.py             # konstanter
│       ├── services.yaml        # service-definisjon (UI-skjema)
│       ├── http.py              # endepunkt for opptak (mottak + ffmpeg)
│       ├── announce.py          # snapshot/grupper/annonser/restore-logikk
│       └── strings.json         # oversettelser
├── www/                         # eller eget frontend-repo
│   └── sonos-intercom-card.js   # Lovelace-kortet
├── hacs.json                    # HACS-metadata
├── README.md
└── LICENSE
```

> Merk: HACS kan distribuere både integrasjon og kort. Kortet kan ligge i samme repo eller i et eget «plugin»-repo. For enkelhet i starten kan vi ha alt i ett repo.

---

## 7. Tekniske krav og forutsetninger

- **HTTPS for mikrofon.** Nettleseren gir kun mikrofontilgang i sikker kontekst (HTTPS eller `localhost`). Testing skjer over HTTPS-domenet i første omgang.
- **Lokal mikrofon over HTTP (senere).** Den reneste løsningen blir split-horizon DNS: la domenet peke til lokal IP når man er hjemme → HTTPS + lokal trafikk samtidig. Parkeres til etter v1.
- **Sonos S2.** v1 retter seg mot S2-høyttalere (announce/ducking fungerer godt). S1 er ikke i scope.
- **Nettverksporter.** Announce krever at TCP-port 1443 på hver Sonos-enhet er tilgjengelig fra HA-verten; port 1400 for push-oppdateringer.
- **Filformat.** Bruk MP3 for annonsering — FLAC har kjente problemer med `announce: true`.
- **Intern URL.** HA sin interne URL må være satt riktig slik at Sonos kan hente lydfila lokalt.
- **ffmpeg.** Følger med Home Assistant OS / Container — brukes til konvertering av opptak.

---

## 8. Faseplan

### v1 — Kjernefunksjonalitet (Sonos-spesifikk)

- Custom integrasjon med `sonos_intercom.announce` (tekst *eller* lyd-URL, høyttalervalg, volum, announce).
- HTTP-endepunkt for opptak + ffmpeg-konvertering til MP3.
- Snapshot/grupper/restore-logikk for synkron avspilling på flere høyttalere.
- Lovelace-kort: opptak + TTS + høyttalervelger + volum + announce-toggle.
- Config-flow for standardverdier.
- HACS-klar (manifest, hacs.json, README).

### v2 — Utvidelser (backlog)

- **Chime / gong foran melding** (valgfritt backend mot Chime TTS).
- **Forhåndsdefinerte hurtigmeldinger** som knapper («Middagen er klar», «Leggetid»).
- **Soner / mål-grupper** («Oppe», «Nede», «Alle») i stedet for enkelthøyttalere.
- **Replay** — spill siste melding på nytt.
- **Meldingshistorikk** — lagre og gjenspill tidligere opptak.
- **TTS-stemme per melding** hvis flere motorer er konfigurert.
- **Lokal mikrofon over HTTP** via split-horizon DNS-veiledning.

### v3 — Lengre sikt

- **Toveis intercom** — annonser fra ett rom, svar tilbake fra et annet.
- **Generell media_player-støtte** (Google, Music Assistant, m.fl.).

---

## 9. Åpne spørsmål og risiko

- **Synk-presisjon ved gruppering.** Vi bør teste at join/announce/restore-sekvensen faktisk gir tett nok synk på dine høyttalere.
- **Lagringssted for opptak.** `/media` vs `/config/www` — avveiing mellom tilgjengelighet og rydding. Bør avklares ved testing.
- **Opprydding.** Hvor lenge skal opptak ligge? Auto-sletting etter X timer/dager.
- **Forsinkelse.** Opptak → konvertering → henting fra Sonos kan gi noen sekunders forsinkelse. Bør måles.
- **Restore-pålitelighet.** Edge-caser: hva skjer hvis en høyttaler var i en gruppe fra før, eller spilte fra en strømmetjeneste? Snapshot/restore må håndtere dette.

---

*Dette er et levende dokument i designfasen. Neste steg etter godkjenning er å sette opp repo-skjelettet og implementere v1-kjernen.*
