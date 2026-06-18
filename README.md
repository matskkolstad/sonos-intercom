# Sonos Intercom

> **Status: v0.4.0.** Stabil kjerne (TTS, mikrofon-opptak, chimes, kort). 0.4.0 legger
> til egne chimes, stille timer, TTS-stemme/språk, innboks/historikk med svar og
> kvittering, en sensor-entitet og en HA-hendelse. Nye 0.4.0-funksjoner bør bekreftes
> på ekte maskinvare.

En custom Home Assistant-integrasjon som gir deg en **intercom** for Sonos-høyttalerne dine: skriv inn tekst (tekst-til-tale) eller **spill inn en lydmelding via mikrofonen** i nettleseren, og få den annonsert på utvalgte eller alle høyttalere – med volum og «announce» (musikk dempes og gjenopprettes).

## Hva den gjør

- 🎙️ **Mikrofon-opptak fra dashboardet** – det som mangler i HA fra før, med **forhåndslytting** («▶ Lytt») før du sender.
- 🗣️ **Tekst-til-tale** på valgte høyttalere, med valgfri **stemme og språk** (Avansert).
- 🔊 **Volum per annonsering**, felles eller per høyttaler.
- 📣 **Announce / ducking** – pågående musikk dempes og gjenopprettes.
- 🔔 **Chimes** – fem innebygde + dine **egne opplastede chimes**; spill foran melding / alene / forhåndsvis.
- 🌙 **Stille timer / nattmodus** – tak på volum (eller hopp over) i et tidsrom.
- 📥 **Innboks / historikk** – siste meldinger med **gjenspilling**, **svar** og **kvittering** (toveis uten mikrofon).
- 📡 **Sensor + hendelse** – `sensor.sonos_intercom_last_message` og `sonos_intercom_announced`-eventet for automasjoner.
- 🧩 **Lovelace-kort** med opptaks-/tekstmodus, høyttalervalg og innstillinger (som huskes mellom økter).
- ⚙️ **Service-kall** `sonos_intercom.announce`, `replay` og `acknowledge` for automasjoner, scripts og Node-RED.

## Krav

- Home Assistant 2024.6 eller nyere.
- Sonos S2-høyttalere oppsatt via den innebygde Sonos-integrasjonen.
- Mikrofon krever at HA åpnes over **HTTPS** (nettlesere blokkerer mikrofon på usikre tilkoblinger). TTS fungerer uansett.
- Minst én TTS-motor konfigurert i HA (for tekst-til-tale).
- Nettverk: TCP-port 1443 og 1400 på hver Sonos-enhet må være tilgjengelig fra HA-verten.
- Generell `media_player`-støtte: `announce` fungerer nå også mot ikke-Sonos-spillere (Sonos-spesifikke steg hoppes over). Dette er foreløpig ikke testet av vedlikeholderen (kun Sonos-oppsett).

## Installasjon (HACS – custom repository)

1. HACS → ⋮ → **Custom repositories**.
2. Legg til `https://github.com/matskkolstad/sonos-intercom` som kategori **Integration**.
3. Søk opp **Sonos Intercom**, last ned, og start HA på nytt.
4. Innstillinger → Enheter og tjenester → **Legg til integrasjon** → *Sonos Intercom*.

Kortet (`sonos-intercom-card`) registreres automatisk som frontend-ressurs av integrasjonen.

## Bruk i dashboard

```yaml
type: custom:sonos-intercom-card
entities:
  - media_player.kjokken
  - media_player.stue
  - media_player.soverom
```

Hvis `entities` utelates, listes alle `media_player`-enheter.

## Service-kall

```yaml
# Tekst-til-tale
action: sonos_intercom.announce
data:
  message: "Middagen er klar"
  targets:
    - media_player.kjokken
    - media_player.stue
  volume: 35
  announce: true
```

```yaml
# Ferdig lydfil / opptak
action: sonos_intercom.announce
data:
  audio_url: "http://<ha>/local/sonos_intercom/intercom_123.mp3"
  targets:
    - media_player.soverom
  volume:
    media_player.soverom: 20
    media_player.bad: 40
  announce: true
```

```yaml
# TTS med språk, stemme og kilde (vises i innboksen)
action: sonos_intercom.announce
data:
  message: "Middagen er klar"
  language: nb
  voice: "nb-NO-Standard-A"
  source: "Kjøkkenet"
  targets:
    - media_player.stue
```

```yaml
# Spill av igjen fra historikken (index 0 = nyeste)
action: sonos_intercom.replay
data:
  index: 0
  targets: [media_player.stue]   # valgfritt; gjenbruker lagrede mål hvis utelatt
```

```yaml
# Kvitter på siste melding ("Mottatt")
action: sonos_intercom.acknowledge
data:
  message: "Mottatt"             # valgfritt
  chime: soft_ping               # valgfritt, standard soft_ping
  targets: [media_player.kjokken] # valgfritt; standard er siste meldings kilde/mål
```

## Innstillinger

Settes via integrasjonens *Konfigurer*-skjerm:

- **`default_volume`** – standardvolum for annonseringer.
- **`default_tts_engine`** – standard TTS-motor (f.eks. `tts.home_assistant_cloud`).
- **`storage_dir`** – lagringsmappe for opptak/genererte filer.
- **`retention_hours`** – hvor lenge genererte filer beholdes før de ryddes automatisk (standard 24; 0 slår av).
- **`quiet_start` / `quiet_end`** – stille timer (HH:MM, tom = av). Se «Stille timer» under.
- **`quiet_max_volume`** – maks volum i stille timer (0-100, standard 20; 0 = hopp over annonseringer).
- **`custom_chime_dir`** – mappe for egne chimes (standard `www/sonos_intercom_chimes`, relativ til config). Må ligge under `www/` slik at Sonos kan hente dem via `/local/`.
- **`history_size`** – antall meldinger som beholdes i innboksen/historikken (standard 20; nullstilles ved omstart av HA).

## Chimes

Integrasjonen kommer med fem innebygde chimes som kan spilles foran meldingen, alene, eller forhåndsvises i nettleseren:

- **Flyplass** – PA-aktig nedadgående treklang
- **Ding-dong** – klassisk dørklokke
- **Mykt pling** – enkel, dempet bjelle
- **Marimba** – stigende treklang
- **Gong** – lav, fyldig gong

I kortet velger du chime fra nedtrekksmenyen, trykker **▶ Forhåndsvis** for å høre den i nettleseren, eller **🔊 Høyttalere** for å spille den på de valgte Sonos-høyttalerne. Når du sender en melding med en chime valgt, kombineres chime + melding til én sømløs lydfil (via ffmpeg) før avspilling.

I service-kall legger du til `chime: airport` (eller `ding_dong`, `soft_ping`, `marimba`, `gong`). Med kun `chime` og `targets` spilles chimen alene.

### Egne chimes (opplasting)

Du kan bruke dine egne lyder som chimes:

- I kortet: trykk **➕ Last opp chime** og velg en lydfil. Den konverteres til MP3 (ffmpeg) og lagres i `custom_chime_dir` (standard `www/sonos_intercom_chimes`).
- Manuelt: legg MP3-filer rett i `custom_chime_dir`.

Egne chimes dukker opp i nedtrekksmenyen sammen med de fem innebygde. I service-kall bruker du filnavnet uten filendelse som `chime`-verdi (f.eks. en fil `dorklokke.mp3` blir `chime: dorklokke`).

## Stille timer / nattmodus

Sett `quiet_start` og `quiet_end` (HH:MM) for å definere et tidsrom hvor annonseringer skal dempes. I dette tidsrommet kappes volumet til `quiet_max_volume` (standard 20). Settes `quiet_max_volume` til 0, hoppes annonseringer over helt. Sensoren `sensor.sonos_intercom_last_message` har attributtet `quiet_active` som viser om stille timer er aktive akkurat nå.

## TTS-stemme og språk

I tekstmodus finner du en **Avansert**-seksjon i kortet hvor du kan sette TTS-språk (f.eks. `nb`, `en`) og stemme. I service-kall sendes disse som `language` og `voice` på `announce`. `voice` er motoravhengig.

## Innboks / historikk og toveis

De siste meldingene beholdes i minnet (`history_size`, standard 20) og vises i kortets **Innboks / Historikk**-seksjon. For hvert element kan du:

- **▶** – spille meldingen av igjen.
- **↩︎ Svar** – forhåndsvelger avsenderens høyttalere (`source`/`targets`) så du raskt kan svare tilbake.
- **✔ Kvitter** – sender en kort kvittering («Mottatt») tilbake via `sonos_intercom.acknowledge`.

> **Toveis uten mikrofon:** Sonos-høyttalere har ingen mikrofon, så «toveis intercom» er her løst som en **meldingsinnboks med svar/kvittering** – du skriver/sender tilbake til avsenderens sone – og **ikke** som levende tale.

Historikken nullstilles ved omstart av Home Assistant.

## Sensor: `sensor.sonos_intercom_last_message`

Integrasjonen oppretter en sensor-entitet som kortet (og dine automasjoner) leser:

- **Tilstand:** siste meldingstekst (`[Opptak]` for opptak, `[Chime]` for chime alene, `Ingen` hvis ingen).
- **Attributter:** `messages` (liste over siste elementer: tid, type, melding, audio_url, chime, mål, kilde, volum), `chimes` (tilgjengelige chimes inkl. egne: id, etikett, custom, url), `quiet_active`, `last_source`, `last_targets`.

## Hendelse: `sonos_intercom_announced`

Ved hver annonsering (og hver kvittering) sendes HA-hendelsen `sonos_intercom_announced` med data `{message, audio_url, chime, targets, volume, source}`. Bruk den som utløser i egne automasjoner (f.eks. blink lys, logg, push-varsel).

## Veikart

- **v1 (ferdig):** opptak + TTS + kort + service (Sonos).
- **v2 (ferdig / pågår):** chimes (foran melding / alene / forhåndsvis) ✔, chime-volum ✔, replay ✔, historikk/innboks ✔, egne chimes ✔, stille timer ✔, lagringsopprydding ✔, TTS-stemme/språk ✔, første toveis (svar/kvittering) ✔. **Pågår/igjen:** hurtigmeldinger (preset-knapper), soner/mål-grupper, per-høyttaler-volum i kortet.
- **v3 (igjen):** ekte toveis med tale, full verifisering av generell `media_player`-støtte (grunnstøtte finnes nå, men er ikke testet av vedlikeholderen).

## Lisens

MIT – se [LICENSE](LICENSE).
