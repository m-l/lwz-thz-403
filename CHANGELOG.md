# Changelog

All notable changes to the THZ integration are documented here.

---

## [Unreleased]

### New Features

- **Solar circuit and live fan status for firmware 4.39/5.39** (`pxx16` / `sSol`,
  command `16`, and `pxxE8` / `sFan`, command `E8`): Ports two more FHEM blocks that
  had no equivalent in this fork at all. `pxx16` adds `collector_temp`, `dhw_temp`,
  and `flow_temp` (solar circuit temperatures), `ed_sol_pump` (solar pump runtime
  counter), plus the raw `out`/`status` fields FHEM itself never decodes further.
  `pxxE8` adds live `input_fan_speed`/`output_fan_speed`,
  `p_fanstage_x_airflow_inlet`/`_outlet` (m³/h), and `input_fan_power`/
  `output_fan_power` — distinct from the existing `p07`-`p12`/`p43`-`p46`/`p99`
  fan-stage *setting* write entities, and from firmware 2.06's own differently-laid-out
  `E8fan206` block. Found via a systematic pass comparing every read block against
  FHEM's `00_THZ.pm`; the write side had no equivalent gaps. Like the fault log, these
  are new register blocks: existing config entries need to go through Reconfigure again
  to add "Solar Circuit" / "Fan Status & Air Flow" to the polled blocks before the new
  sensors appear.

- **Firmware profile override** (`firmware_override` config option): Lets you force a
  specific FHEM-style register-map profile regardless of what the device reports —
  including the `"439technician"` / `"539technician"` variants, matching the technician
  profile some users already run under FHEM. Configurable via the integration's
  Reconfigure flow ("Firmware profile" dropdown: Auto-detect, 2.06, 2.14, 2.14j, 4.39,
  4.39 Technician, 5.39, 5.39 Technician). The detected firmware value shown in
  diagnostics/`firmware_version` is unaffected — the override only changes which
  register maps get loaded. Selecting a technician profile additionally exposes
  `zResetLast10errors` (button), and `zPumpHC` / `zPumpDHW` / `zControlValveDHW`
  (manual pump/valve force, for testing).

- **Fault log sensors for firmware 4.39 / 5.39** (`pxxD1` block, command `D1`): Adds
  `number_of_faults` plus `fault0CODE`/`fault0TIME`/`fault0DATE` through
  `fault3CODE`/`fault3TIME`/`fault3DATE`, decoded to human-readable fault names and
  `HH:MM` / `DD.MM` strings. Ported from FHEM's `D1last` parsing table — like the
  reference implementation, only the 4 most recent entries are available, not 10
  despite the name. Firmware 4.39/5.39 encode fault codes as 1 byte (vs. 2 bytes on
  2.06) and encode fault times/dates with their two bytes swapped relative to the
  2.06 encoding, requiring two new decode types (`turnhex2time`, `turnhexdate`) added
  to `value_codec.py`. This is a new register block, so existing config entries need
  to go through Reconfigure again to add "Fault Log" to the polled blocks before the
  new sensors appear.

### Correction

- **"Live pump-running status for firmware 4.39/5.39" (previously listed above as a New
  Feature) was a false alarm and has been removed.** A user report of the `zPumpHC`/
  `zPumpDHW` technician "force" selects showing `unknown` was correctly diagnosed as
  expected (those are one-shot write-only commands with no readable state, matching
  FHEM's own model), but the follow-up assumption — that 4.39/5.39 lacked read-only
  `dhw_pump`/`heating_circuit_pump`/`solar_pump` status entirely — was wrong. A later,
  broader audit against FHEM's `00_THZ.pm` found that `register_map_all.py` (a universal
  base register map already merged in for every firmware family) has defined identical
  `pxxFB` entries for all three pumps at the same offsets all along. The sensors were
  already there; the "fix" duplicated existing entries with no behavioural difference.
  The duplicate block has been removed from `readings_map_439.py` again. If you added
  these to your polled blocks via Reconfigure, no action is needed — the entities keep
  working exactly the same, now sourced from the pre-existing base map instead of the
  short-lived duplicate.

### Bug Fixes

- **Firmware "438" (and other off-point-release 4.3x builds) incorrectly used 5.39-style
  register maps**: Any firmware string not explicitly listed in `FIRMWARE_MAPS`
  (`register_map_manager.py`) fell through to a `"default"` entry that was really just
  the 5.39 configuration, pulling in register offsets/fields that don't exist on 4.3x
  hardware and causing garbage or wrong readings. `"539"` now has its own explicit entry,
  and unrecognized firmware strings fall back to the 4.39-style maps instead — matching
  FHEM's own `00_THZ.pm` fallback behavior ("in all other cases I assume firmware
  4.39"). Affects, for example, LWZ 403 units reporting firmware `"438"`.

- **`THZRegisterNotSupportedError` silently downgraded to a generic decode failure,
  crashing config entry setup**: When a device cleanly reports "register not supported"
  (a `01 04` response) for a register that genuinely doesn't exist on its firmware (e.g.
  the 5.39-only `pxx0A033B` "Flow Rate" register on 4.3x hardware), `decode_response()`
  deliberately raised `THZRegisterNotSupportedError` — but its own blanket
  `except Exception` caught that same exception a few lines later and downgraded it to a
  plain `None`, indistinguishable from a real communication failure. That surfaced as
  "Failed setup, will retry: Error reading `<block>`: Failed to decode device response"
  and aborted the whole config entry instead of just skipping the one unsupported block
  (the existing `unsupported_blocks` handling in `async_setup_entry` was already written
  for exactly this case, but never got the chance to run). Fixed by letting
  `THZRegisterNotSupportedError` propagate cleanly out of `decode_response()`, and by
  having `_async_update_block()` catch it and return `None` for that block instead of
  raising `UpdateFailed`.

---

## [0.4.1] – 2026-06-29

### Bug Fixes

- **`NameError: unsupported_blocks` in sensor platform**: The `unsupported_blocks` set
  was stored in `entry_data` by the integration setup but never retrieved in `sensor.py`,
  causing the sensor platform to fail on startup. Fixed by reading it from `entry_data`
  with an empty-set fallback.

- **UTF-8 BOM in `__init__.py`**: A byte-order mark (`EF BB BF`) at the start of the
  file caused `hassfest` to fail with `SyntaxError` on Python 3.14. Windows git with
  `core.autocrlf=true` silently stripped it on checkout so it was invisible locally.
  File committed as plain UTF-8 with LF line endings.

- **Climate platform `KeyError: write_manager`**: `async_setup_entry` in `climate.py`
  was reading `write_manager`, `register_manager`, and `device_id` from the domain-level
  dict instead of from the per-entry dict (`hass.data[DOMAIN][entry_id]`).

---

## [0.4.0] – 2026-06-28

### New Features

- **Compressor/booster runtime hours** (firmware 4.39 / 5.39): Added `sHistory`
  (command `09`) sensors reporting cumulative operating hours in `h` —
  `compressor_runtime_heating`, `compressor_runtime_cooling`, `compressor_runtime_dhw`,
  `booster_runtime_dhw`, and `booster_runtime_heating`.
  ⚠️ **Breaking change for users who already have these sensors**: entity names and
  unique IDs have changed from `*_starts_*` to `*_runtime_*`. Existing history,
  automations, or dashboards referencing the old names will need to be updated.

- **Climate entity — Heating Circuit 2 (HC2)**: A second `climate` entity is now created
  for HC2 when `p01RoomTempDayHC2` is present in the write-register map. It reads the
  setpoint and operating mode from the `pxxF5` coordinator.

- **`thz.refresh_block` service**: Force an immediate re-read of any coordinator block
  from the device without waiting for the next poll interval. Accepts the block name in
  any form (`"FB"`, `"pxxFB"`, `"0xFB"`). Returns `{success, block}`. Also available as
  `async_refresh_block(hass, block, entry_id)` for use by other platforms.

- **`thz.set_diverter_valve` service**: Manual control of the 3-way diverter valve motor.
  Accepts `position: heating | dhw | off`.
  - Both `heating` and `dhw` are guarded by the `diverterValve` bit in `pxxF2` — the
    command is refused if the heat pump is currently pressurising the opposite circuit,
    preventing valve movement against live flow.
  - After activating the motor the service waits 3 seconds then automatically stops it
    (sends `00 00` to both motor commands).
  - The stop is verified by reading back both registers; if either is non-zero the stop
    is retried once and a warning is logged.
  - `off` stops the motor immediately with the same read-back verification.
  - Returns `{success, position, confirmed_off}`.

### Improvements

- **Climate field layouts derived from the register map**: Byte offsets and lengths for
  all climate readings (`roomSetTemp`, `insideTempRC`, `hcOpMode`, `dhwTemp`, etc.) are
  now looked up from the active firmware's merged register map at startup instead of
  being hardcoded. This automatically picks up firmware-specific offsets. If a required
  field is absent the entity is skipped with an error log rather than using a stale
  hardcoded value.

- **Climate writes trigger an immediate coordinator refresh**: Setting temperature, HVAC
  mode, preset, or fan mode now requests a coordinator refresh immediately after the
  write so HA reflects the actual device value without waiting for the next poll.

### Bug Fixes

- **Relative Humidity HC2 mapped as Dew Point** (PR #127): The sensor at nibble 82 in
  the `pxxFB` block was incorrectly labelled `dewPoint` with temperature metadata. It
  carries relative humidity for HC2 (room controller). Renamed to `relHumidityHC2` with
  humidity metadata and `rel_humidity_hc2` translation key (EN + DE).

- **Switches and selects revert in the UI after a few seconds**: Toggling a switch or
  changing a select option updated the internal state but never pushed it to Home
  Assistant (`async_write_ha_state()` was missing), so the UI fell back to the stale
  value until the next poll. The same issue affected number and time entities. All of
  these now write the new state immediately for instant UI feedback.

- **Passive cooling select value always reads as "Unknown"** (#122): Fixed a byte-order
  encoding bug where the `passive_cooling` select type was decoded as big-endian
  (returning value 256 instead of 1). Now uses the same single-byte encoding as
  `2opmode`, matching the actual device protocol.

- **HA 2026.05 hang / serial reconnect on protocol error** (#118): A `RuntimeError`
  from a stale TCP socket (e.g. ser2net) previously raised immediately without
  attempting to reconnect. The integration now tries to reconnect and retry on
  `RuntimeError` the same way it does for `ConnectionError`.

- **Ventilator speed sensors show Hz instead of %** (#106): All ventilator speed sensors
  (`outputVentilatorSpeed`, `inputVentilatorSpeed`, `mainVentilatorSpeed`) now correctly
  report their unit as `%` to match the FHEM source. The `device_class: frequency` has
  been removed. ⚠️ **Breaking change for users with long-term statistics on these
  sensors** — HA may require manually migrating or clearing the old statistics.

### Bug Fixes

- **Switches and selects revert in the UI after a few seconds**: Toggling a switch or
  changing a select option updated the internal state but never pushed it to Home
  Assistant (`async_write_ha_state()` was missing), so the UI fell back to the stale
  value until the next poll. The same issue affected number and time entities. All of
  these now write the new state immediately for instant UI feedback.

- **Passive cooling select value always reads as "Unknown"** (#122): Fixed a byte-order
  encoding bug where the `passive_cooling` select type was decoded as big-endian
  (returning value 256 instead of 1). Now uses the same single-byte encoding as
  `2opmode`, matching the actual device protocol.

- **HA 2026.05 hang / serial reconnect on protocol error** (#118): A `RuntimeError`
  from a stale TCP socket (e.g. ser2net) previously raised immediately without
  attempting to reconnect. The integration now tries to reconnect and retry on
  `RuntimeError` the same way it does for `ConnectionError`.

- **Ventilator speed sensors show Hz instead of %** (#106): All ventilator speed sensors
  (`outputVentilatorSpeed`, `inputVentilatorSpeed`, `mainVentilatorSpeed`) now correctly
  report their unit as `%` to match the FHEM source. The `device_class: frequency` has
  been removed. ⚠️ **Breaking change for users with long-term statistics on these
  sensors** — HA may require manually migrating or clearing the old statistics.

---

## [0.3.0-alpha] – 2026-03-02

> **Alpha release** — tested on firmware 4.39 and 5.39. Please report any regressions
> or unexpected behaviour in the [issue tracker](https://github.com/bigbadoooff/thz/issues).

### New Features

#### Passive Cooling Support (firmware 4.39 / 5.39)
- New **select entity** `p75passiveCooling` for devices running firmware 4.39 or 5.39.
- Supports modes: `off`, `exhaust_air`, `supply_air`, `bypass`, and `sommerkassette`.
- Fully translated in English and German.
- Cooling energy sensor `sCoolHCTotal` (paired-block read) added for firmware 5.39.

#### Diagnostics Support
- The integration now exposes a **Download Diagnostics** option in the Home Assistant UI.
- The diagnostics file includes firmware version, connection type, coordinator status,
  last update timestamps, and redacted hex dumps of all currently-polled register
  blocks.
- Sensitive data (host, device path, serial number) is automatically redacted.

#### COP (Coefficient of Performance) Sensors
- Automatically created for devices with energy-monitoring support (firmware ≥ 4.39).
- Sensors cover **daily**, **monthly**, **yearly**, and **lifetime** COP for DHW,
  heating circuit, and combined total.
- Monthly and yearly sensors reset at the start of each new period and persist
  across Home Assistant restarts.

#### Energy Sensors via Paired-Block Reads (firmware 4.39 / 5.39)
- Heat-output and electricity-consumption sensors are now read using a two-command
  ("paired block") protocol that combines a high-word and a low-word to produce
  accurate 32-bit energy values in Wh.
- Sensors: `sHeatDHWDay`, `sHeatDHWTotal`, `sHeatHCDay`, `sHeatHCTotal`,
  `sElectrDHWDay`, `sElectrDHWTotal`, `sElectrHCDay`, `sElectrHCTotal`,
  `sCoolHCTotal` (5.39 only).

#### `thz.read_raw_register` Service
- New developer/debug service to read any raw register block directly from the
  heat pump.
- Returns results as a service response (usable in automations), a persistent
  notification, and an INFO-level log entry.
- See [docs/read-raw-register-service.md](docs/read-raw-register-service.md) for
  full documentation.

#### Per-Block Configurable Polling Intervals
- Each register block now has its own poll interval, configurable in the
  **Reconfigure** dialog.
- Fast-changing blocks (e.g., temperatures) can be polled frequently while
  slow-changing settings blocks can be polled less often.
- Default interval: 600 seconds.

#### Sensor Metadata in Register Maps
- Register map tuples now support an optional 6th element (a metadata dict)
  providing `unit`, `device_class`, `state_class`, `icon`, and `translation_key`
  inline.
- Module-level helpers (`_TEMP`, `_POWER`, `_ENERGY_TOTAL`, etc.) reduce
  repetition across firmware maps.

#### Smart Entity Visibility
- Advanced, rarely-needed entities are hidden by default to reduce initial clutter:
  - HC2 (heating circuit 2) entities
  - Time programme entities (`programDHW_*`, `programHC1_*`, `programHC2_*`)
  - Technical parameters p13 and above (gradient, hysteresis, integral, etc.)
- Hidden entities remain visible in the entity registry and can be re-enabled
  individually via **Settings → Devices & Services**.
- A one-time migration automatically hides these entities for users upgrading
  from older versions.

### Changes

- **Manifest version bumped to `0.3.0`.**
- `sensor_meta.py` is now a backward-compatibility stub. All sensor metadata lives
  inline in the register-map tuples. Do **not** add new entries to `sensor_meta.py`.
- `decode_value()` in `sensor.py` is now a thin wrapper around the canonical
  `decode_raw_value()` from `value_codec.py`. The `cop_sensor.py` module imports
  `decode_raw_value` directly.
- Write entities no longer use Home Assistant's class-level `SCAN_INTERVAL`
  polling. Instead they register a `async_track_time_interval` timer in
  `async_added_to_hass` (default 600 s) and cancel it in
  `async_will_remove_from_hass`.
- Updated firmware detection: `214j` variant is now recognised separately from
  `214`.
- Register map manager uses a data-driven `FIRMWARE_MAPS` dict; unknown firmware
  versions fall back gracefully to the `default` (5.39-like) configuration.

### Breaking Changes

> If you are upgrading from 0.2.x, read these carefully.

1. **Entity unique_id format has changed.**  
   Sensor unique IDs now follow the pattern `thz_{block}_{offset}_{name}`.  
   Write-entity unique IDs follow `thz_set_{command}_{name}`.  
   Upgrading will re-create any sensor or write entity whose name was previously
   stored under a different unique ID. You may need to update any automations or
   dashboards that reference those entities.

2. **`sensor_meta.py` is a stub.**  
   Any third-party extension that imported `SENSOR_META` from `sensor_meta` to
   add custom metadata must be updated to use the 6th-element dict in the
   register-map tuple instead.

3. **Calendar platform has been removed.**  
   Any existing `calendar.thz_*` entities from previous versions will no
   longer be available. Update or remove any automations, scripts, or
   dashboards that reference these calendar entities.

### Bug Fixes

- Fixed nibble-offset decoding for `length=1` registers at even offsets (FHEM
  compatibility): bit numbers are now shifted by +4 for the HIGH nibble.
- Fixed paired-block energy reads where the high word was incorrectly combined
  as `low*1000 + high` instead of `high*1000 + low`.
- Improved connection-timeout handling: TCP socket is now closed and re-opened
  on timeout rather than accumulating stale data.

---

## [0.2.2] – prior release

See the [0.2.x README note](README.md) for a summary of changes introduced in
the 0.2 series.
