# CHARX 3100 for Home Assistant

Community integration for the **CHARX SEC-3100** AC charging controller over **Modbus/TCP**.
Reads status and energy-meter data for every charging point and lets you control the
charging release and the maximum charging current — locally, without MQTT or Node-RED.

> **Disclaimer** — This is an independent community project. It is **not** an official
> product of, and is not endorsed or supported by, Phoenix Contact. "CHARX" and
> "Phoenix Contact" are trademarks of their respective owner. Use at your own risk.

*Nederlandse samenvatting onderaan.*

## Features

- Set-up from the UI: enter the IP address, the integration finds the charging points itself.
- One device per charging point, linked to the controller.
- **Self-healing after a controller reset**: the last charging release and max current you set
  from Home Assistant are remembered (also across HA restarts) and written back as soon as the
  controller reports different values. It only writes when something differs, so the controller
  is not flooded with writes.
- One Modbus read per charging point per poll (registers x232–x308 in a single request).

## Entities (per charging point)

| Entity | Type | Register |
|---|---|---|
| Charging state (not connected / connected / charging / error …) | sensor (enum) | x299 |
| IEC 61851 status (A1, B2, C2 …) | sensor, diagnostic | x299 |
| Power | sensor, W | x244 |
| Energy total | sensor, kWh, `total_increasing` (energy dashboard) | x250 |
| Energy session | sensor, kWh | x289 |
| Current L1/L2/L3 | sensor, A | x238–x243 |
| Voltage L1/L2/L3 | sensor, V (disabled by default) | x232–x237 |
| Reactive / apparent power | sensor (disabled by default) | x246, x248 |
| Charging time, connection time | sensor, duration | x287, x285 |
| Offered current (PWM), duty cycle | sensor | x297, x296 |
| Cable capacity | sensor, diagnostic | x298 |
| Error code | sensor, diagnostic | x293 |
| Vehicle connected, charging, error | binary sensor | derived from x299 / x293 |
| **Charging release** | switch | x300 |
| **Max charging current** | number, 6 A – configurable limit | x301 |

The charging point with number *n* uses registers `n × 1000 + offset`
(charging point 1 → 1232…, charging point 2 → 2232…). The number of charging points is read
from register 114.

## Requirements on the controller

1. **Enable the Modbus server**: web interface → *System Control* → *Status* → Modbus Server: enable.
2. **For the charging release switch**: per charging point → *Configuration* → *Release Mode*: **Modbus**.
   The max current and all sensors work in any release mode.

## Installation

### HACS / Marketplace (custom repository)
1. Add `https://github.com/wilcostienezen/ha-charx3100` as a custom repository (category *Integration*).
2. Download **CHARX 3100** and restart Home Assistant.
3. *Settings → Devices & services → Add integration → CHARX 3100*, enter the IP address.

### Manual
Copy `custom_components/charx3100` into your `config/custom_components` folder and restart.

## Options

| Option | Default | Meaning |
|---|---|---|
| Poll interval | 15 s | How often every charging point is read |
| Maximum current that can be set | 32 A | Upper limit of the max current control — match your cable and fuse |
| Restore settings after a controller reset | on | Writes the last values set from HA back when the controller differs |

## Tips

- Keep load balancing logic (fuse protection, dynamic prices) in your own automations and let
  them change the *Max charging current* and *Charging release* entities. Avoid writing every
  few seconds: change the current at most about once a minute.
- Do not use this integration together with another Modbus master (Node-RED, YAML `modbus:`)
  that writes the same registers.

## Nederlands

Community-integratie (geen officieel Phoenix Contact-product) voor de CHARX SEC-3100 via Modbus/TCP.
Per laadpunt: laadstatus, vermogen, energie (geschikt voor het energiedashboard), stroom en spanning
per fase, laadtijd, plus een schakelaar *Laden toegestaan* en een instelling *Max. laadstroom*.
Na een reset van de controller zet de integratie je laatste instellingen automatisch terug.
Zet op de controller de Modbus-server aan en, voor de schakelaar, per laadpunt de Release Mode op *Modbus*.

## License

MIT
