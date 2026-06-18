# Sonos Intercom

> ⚠️ **Status: tidlig utvikling (v0.1).** Fungerer som et fungerende skjelett – API og oppførsel kan endre seg.

En custom Home Assistant-integrasjon som gir deg en **intercom** for Sonos-høyttalerne dine: skriv inn tekst (tekst-til-tale) eller **spill inn en lydmelding via mikrofonen** i nettleseren, og få den annonsert på utvalgte eller alle høyttalere – med volum og «announce» (musikk dempes og gjenopprettes).

## Hva den gjør

- 🎙️ **Mikrofon-opptak fra dashboardet** – det som mangler i HA fra før.
- 🗣️ **Tekst-til-tale** på valgte høyttalere.
- 🔊 **Volum per annonsering**, felles eller per høyttaler.
- 📣 **Announce / ducking** – pågående musikk dempes og gjenopprettes.
- 🧩 **Lovelace-kort** med opptaks-/tekstmodus, høyttalervalg og innstillinger.
- ⚙️ **Service-kall** `sonos_intercom.announce` for automasjoner, scripts og Node-RED.

## Krav

- Home Assistant 2024.6 eller nyere.
- Sonos S2-høyttalere oppsatt via den innebygde Sonos-integrasjonen.
- Mikrofon krever at HA åpnes over **HTTPS** (nettlesere blokkerer mikrofon på usikre tilkoblinger). TTS fungerer uansett.
- Minst én TTS-motor konfigurert i HA (for tekst-til-tale).
- Nettverk: TCP-port 1443 og 1400 på hver Sonos-enhet må være tilgjengelig fra HA-verten.

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

## Innstillinger

Settes via integrasjonens *Konfigurer*-skjerm: standardvolum, standard TTS-motor og lagringsmappe for opptak.

## Veikart

- **v1:** opptak + TTS + kort + service (Sonos).
- **v2:** chime foran melding, hurtigmeldinger, soner, replay, historikk.
- **v3:** toveis intercom, generell `media_player`-støtte.

## Lisens

MIT – se [LICENSE](LICENSE).
