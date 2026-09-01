# Changelog

All notable changes to the THZ integration are documented here.

---

## [Unreleased]

---

## [0.4.3] – 2026-09-01

### Bug Fixes

- **`enable_hc2` not applied on upgrade**: entries that predate the hc2/advanced
  category split (where HC2 was previously enabled under the "Extended"/"All" tiers)
  had no recorded HC2 reconciliation state, so the change-detection defaulted the
  "previous" HC2 state to `False` -- coincidentally matching the checkbox's own
  default. Explicitly setting "Enable HC2 entities" to off via Reconfigure, with the
  tier left unchanged, was then wrongly treated as a no-op, leaving already-enabled
  HC2 entities visible. Now infers the effective prior HC2 state from the
  previously-applied tier when no HC2 reconciliation has run yet, so this case is
  correctly detected and reconciled.

---

## [0.4.2] – 2026-09-01

### New Features

- **Entity visibility tiers** (`entity_visibility` config option, set at setup or via
  Reconfigure): replaces the old all-or-nothing hiding of HC2, schedule/program, and
  advanced parameter entities behind manual enable clicks. Three tiers: "Default" hides
  HC2, schedules, and advanced parameters (gradients, hysteresis, booster timing, etc.)
  — the previous behavior. "Extended" enables everything except schedules. "All"
  enables everything. Changing tiers via Reconfigure is retroactive — it bulk
  enables/disables entities on your existing install, no re-add needed — and never
  touches entities you've manually toggled; only ones this option itself disabled get
  re-enabled.

- **`enable_hc2` config option**: A separate checkbox for showing Heating Circuit 2
  entities, independent of the `entity_visibility` tier above. Previously HC2 was
  lumped into the same category as advanced technical parameters, so there was no way
  to show one without the other — even the "All" tier enabled HC2 whether you wanted it
  or not. HC2 now defaults to hidden regardless of tier, including under "All", until
  this is explicitly checked. Same retroactive Reconfigure behavior as the tier option.

- **FHEM/technical entity_id naming style** (`entity_id_style` config option, set at
  setup or via Reconfigure): an alternative to this integration's descriptive entity_id
  naming. Choosing "FHEM/technical" derives each `entity_id` from the raw
  register-map/parameter name instead — e.g. `dhwPump`, `collectorTemp`,
  `p01RoomTempDayHC1` — which for most entities already matches FHEM's own `00_THZ.pm`
  field name or Stiebel Eltron's parameter number, since this integration was ported
  from those tables. Meant to ease dashboard/automation porting for FHEM users migrating
  over. Rejected using the shorter aliases some FHEM users see (`PumpDHW`, `Compress`,
  `dhw_temp`) — those aren't published by the FHEM module itself, only by that user's
  local `userReadings` config, so they're not a stable target. This only changes HA's
  `suggested_object_id` for a **brand-new** entity — never `unique_id` or the friendly
  name — so switching it doesn't rename or break existing entities, only new ones.

  Fixed a follow-up gap: on "Default" style, HA's `has_entity_name` fallback prepends
  the *full* device name/alias to every entity_id (e.g.
  `number.heating_clima_water_control_lwz_start_unscheduled_ventilation`), which
  "FHEM/technical" style didn't account for. Added an optional **alias** field (now
  settable at initial setup too) that, when set, prefixes the FHEM-style entity_id
  instead — e.g. alias `lwz` + `p99startUnschedVent` →
  `number.lwz_p99start_unsched_vent`. No prefix if no alias is set.

- **Solar circuit and live fan status for firmware 4.39/5.39** (`pxx16`/`sSol`, command
  `16`, and `pxxE8`/`sFan`, command `E8`): ports two FHEM blocks with no prior
  equivalent in this fork. `pxx16` adds `collector_temp`, `dhw_temp`, `flow_temp` (solar
  circuit temps), `ed_sol_pump` (solar pump runtime), plus raw `out`/`status` fields
  FHEM never decodes further. `pxxE8` adds live `input_fan_speed`/`output_fan_speed`,
  `p_fanstage_x_airflow_inlet`/`_outlet` (m³/h), and `input_fan_power`/
  `output_fan_power` — distinct from the existing `p07`-`p12`/`p43`-`p46`/`p99`
  fan-stage *setting* entities and firmware 2.06's own `E8fan206` layout. Found via a
  systematic pass against FHEM's `00_THZ.pm`; write side had no gaps. New register
  blocks — existing config entries need Reconfigure to add "Solar Circuit"/"Fan Status &
  Air Flow" to polled blocks before sensors appear.

- **Firmware profile override** (`firmware_override` config option): forces a specific
  FHEM-style register-map profile regardless of what the device reports, including
  `"439technician"`/`"539technician"`, matching the technician profile some users run
  under FHEM. Set via Reconfigure ("Firmware profile" dropdown: Auto-detect, 2.06, 2.14,
  2.14j, 4.39, 4.39 Technician, 5.39, 5.39 Technician). Diagnostics/`firmware_version` is
  unaffected — the override only changes which register maps load. A technician profile
  also exposes `zResetLast10errors` (button) and `zPumpHC`/`zPumpDHW`/
  `zControlValveDHW` (manual force, for testing).

- **Fault log sensors for firmware 4.39/5.39** (`pxxD1` block, command `D1`): adds
  `number_of_faults` plus `fault0`-`fault3` `CODE`/`TIME`/`DATE`, decoded to
  human-readable fault names and `HH:MM`/`DD.MM` strings. Ported from FHEM's `D1last`
  table — like the reference, only 4 recent entries are available, not 10 despite the
  name. 4.39/5.39 encode fault codes as 1 byte (vs. 2 on 2.06) with swapped time/date
  byte order, requiring two new decode types (`turnhex2time`, `turnhexdate`) in
  `value_codec.py`. New register block — existing entries need Reconfigure to add
  "Fault Log" to polled blocks before sensors appear.

- **`p99CoolingHC1AreaFan` switch** (register `0B0613`, firmware 5.39/5.39 Technician
  only, `write_map_539.py`): a cooling-related area-fan control discovered via an FHEM
  forum thread (mwuerr/immi), proposed there but not yet merged into upstream
  `00_THZ.pm`. Added following the exact pattern of the existing `p99CoolingHC1Switch`
  (`0B0287`) — same `"switch"` type, `decode_type: "1clean"`, added to
  `_COOLING_WRITE_KEYS` (`register_map_manager.py`) so it's excluded on firmware without
  cooling, plus a `cooling_hc1_area_fan` translation key/string. Only reachable on
  `"539"`/`"539technician"` — `FIRMWARE_MAPS` never includes `write_map_539` for
  `"439"`/`"439technician"`, so 4.39-profile users (including technician) will not see
  this entity, same as they don't see `p99CoolingHC1Switch` today.

### Bug Fixes

- **`zPumpHC`/`zPumpDHW` (technician-profile manual pump-override entities, commands
  `0A0052`/`0A0056`) were non-functional on every install that exposed them**: both were
  typed `"select"` with `decode_type: "0clean"`, but `"0clean"` isn't a key in
  `SELECT_MAP` (`value_maps.py`) — it's FHEM's plain single-byte integer encoding, not a
  named-option enum. Confirmed against `00_THZ.pm`, which defines both as `argMin => "0",
  argMax => "1", type => "0clean"`, the same encoding it uses for other plain
  0-100/1-31/etc. numeric writes — there was never a richer option set to model. In
  practice this meant `select.py` fell back to an empty options list (nothing selectable
  in the UI), and any read or write that did reach `value_codec.py` raised `ValueError:
  Unknown decode_type: 0clean` from `decode_select`/`encode_select`. Fixed by changing
  both entries' `"type"` from `"select"` to `"number"` (min `0`/max `1`/step `1`),
  matching the existing pattern for other binary write registers (e.g. `p80EnableSolar`).
  `decode_type: "0clean"` needed no change — `THZValueCodec.decode_number`/`encode_number`
  already special-case it as a single-byte 0/1 read/write, exactly matching the command's
  wire format.

- **`entity_id_style: "fhem"` never actually worked, for any entity, on any install**
  (you always got HA's default naming — device name and often area name glued on, e.g.
  `number.heating_clima_water_control_lwz_start_unscheduled_ventilation` instead of
  `number.lwz_p99start_unsched_vent`). Root cause: **`_attr_suggested_object_id` isn't a
  real Home Assistant attribute.** `Entity.suggested_object_id` is a read-only
  `@property` computed from `self.name`/translations — it never reads any `_attr_*`
  attribute. Every entity class here set `self._attr_suggested_object_id = ...`, a
  silent no-op HA never looked at, so every entity fell through to HA's
  `has_entity_name`/device/area naming regardless of `entity_id_style` or `alias` — the
  whole feature was built on an API that doesn't exist. Our tests missed it because they
  only checked our own made-up attribute, never HA's real entity_id path. Fixed by
  setting `self.entity_id` (the full `"domain.object_id"` string) directly before the
  entity is added to hass — the mechanism `entity_platform.py` actually honors. Updated
  tests to assert `entity.entity_id`, and gave the mock `Entity` an `entity_id = None`
  default to match real HA.

  **If you're hitting this**: the fix only applies to entities HA creates fresh —
  `entity_id` is only consulted the first time a registry row exists for a given
  `unique_id`, so any entity with an existing row (all of them) keeps its long
  entity_id until that row is removed. With HA fully stopped, back up and edit
  `.storage/core.entity_registry` to remove entries with `"platform":"thz"` (or just
  ones matching your old name prefix), then start HA — the existing config entry
  recreates every entity fresh, no re-add needed.

- **Entity IDs stayed permanently frozen from first setup, no matter how many times you
  removed/re-added the integration or changed `entity_id_style`/`alias`**: confirmed
  against a live install's `.storage/core.entity_registry`/`core.config_entries` (a
  current entry correctly had `"entity_id_style":"fhem"` and `"alias":"lwz"`, yet a row
  showed `"suggested_object_id":null` with a `created_at` predating that entry —
  expected per the `_attr_suggested_object_id` fix above, but this fix targets the
  separate *dangling-`config_entry_id`* case). HA's config-entry deletion doesn't
  reliably null an entity's `config_entry_id` — it can leave it pointing at the deleted
  entry's id. `_async_cleanup_orphaned_entities()` only checked for
  `config_entry_id is None`, missing this case, so stale rows silently reattached on
  every setup. Fixed by also treating an entity as orphaned when its `config_entry_id`
  matches no existing entry. Added test coverage, previously nonexistent.

- **Solar circuit and live fan sensors displayed only the device name** (every
  "fan"/"airflow" row repeating the device name instead of "Input Fan Speed", etc.): the
  solar/fan-status feature (`pxx16`/`pxxE8`, above) referenced 12 `translation_key`
  values never added to `strings.json`/`translations/en.json`. With
  `has_entity_name=True` and no translation match, HA fell back to the device name. A
  full sweep of `register_maps/*.py` against `translations/en.json` confirmed these were
  the only 12 missing read-side keys (write-side `entity_translations.py` had none).
  Fixed by adding all 12.

- **Button entities (`zResetLast10errors`) failed to load** when a technician firmware
  profile was selected: `async_setup_write_platform()` (shared by every write platform)
  unconditionally passes `entity_id_style`, `entity_visibility`, and `entity_id_prefix`
  to the constructor, but `THZButton.__init__()` was missed when those params were added
  elsewhere and never accepted them. This raised `TypeError: THZButton.__init__() got an
  unexpected keyword argument 'entity_id_style'`, which HA logged and silently swallowed
  for that platform — every other platform set up fine, but no buttons were ever
  created. Fixed by adding the same three params to `THZButton.__init__()`, matching the
  other write entities. Added a regression test through `async_setup_write_platform()`
  itself, since that's the path that broke and nothing previously exercised it.

- **`ResetErrors` (firmware 2.14, command `F8`) created no entity at all**: it was typed
  `"type": "0clean"` in `write_map_214.py` — a decode-type token, not a real platform
  type. `platform_setup.py` dispatches entries by matching `entry["type"]` against the
  literal platform strings each `async_setup_entry()` passes in (`"number"`, `"switch"`,
  `"select"`, `"button"`); `"0clean"` matches none of them, so the entry silently
  vanished from setup instead of erroring. Confirmed against `00_THZ.pm`
  (`argMin => "0", argMax => "0", type => "0clean"`, cmd2 `F8`) — a fixed-value,
  no-range write, the same shape as `zResetLast10errors` (`argMin`/`argMax` both `"0"`),
  which this fork already models as a `"button"`. Fixed by changing `"type"` to
  `"button"` and `decode_type` from `""` to `"0clean"` (matching FHEM's own type for
  this entry — `button.py` always writes a fixed `\x00` payload regardless, so this
  only affects readability of the map, not behavior), plus the `mdi:trash-can-outline`
  icon used for the equivalent D1 button. A `reset_errors` translation key/string was
  already present and unused — no translation changes needed.

- **~100 firmware 2.06 writable parameters created no entities at all** — essentially
  every writable setting on 2.06 (`p01RoomTempDay` through `p80EnableSolar`, plus the
  DHW/HC1/HC2/FAN1/FAN2 schedule enable and day-of-week flags): all 101 entries in
  `write_map_206.py` were typed `"type": "pclean"`, the same class of bug as
  `ResetErrors` above — `"pclean"` is `write_map_206.py`'s decode-type-flavored label
  (its `decode_type` field is separately, correctly, `"pClean"` throughout) but isn't
  one of `platform_setup.py`'s real platform strings, so none of them ever matched a
  dispatch and the entire firmware-2.06 writable surface silently disappeared from
  setup. Every one of these entries has an explicit, meaningful `min`/`max` numeric
  range (temperatures, fan stages, hysteresis, pump-cycle counts, and 0/1 enable/weekday
  flags with a real range rather than a fixed value) and none map to an existing
  `SELECT_MAP` entry, so — consistent with how every comparable numeric parameter is
  typed elsewhere in this codebase (`write_map_214.py`, `write_map_X39tech.py`,
  `write_map_439_539.py`) — all 101 were changed from `"pclean"` to `"number"`.
  `"switch"` was intentionally not used for the 0/1 entries: this codebase's only two
  existing `"switch"` entries (`p99CoolingHC1Switch`/`p99CoolingHC2Switch`) are
  standalone on/off toggles, not part of a numeric range family like these
  schedule-flag parameters. `decode_type: "pClean"` needed no change —
  `THZValueCodec.decode_number`/`encode_number` treat any decode_type other than
  `"0clean"` as standard 2-byte scaled encoding, which is what these registers already
  expect. (2.06's `"ptime"`-typed schedule start/end-time entries are a separate,
  pre-existing gap — not a real platform type either — but out of scope for this fix.)

- **Climate entities' Mode selector (Heat/Off) did nothing on any firmware without
  active-cooling support** (i.e. every install except 5.39 with cooling entries
  present): `async_set_hvac_mode()`'s `HEAT`/`OFF` branch only ever toggled the cooling
  switch, so with no cooling switch to toggle, selecting "Off" silently changed
  nothing on the device -- the heat pump kept heating regardless. There is no
  per-circuit "off" register on this hardware; the device's real off is the global
  `pOpMode` standby state. Fixed by dropping `OFF` from `hvac_modes` entirely
  (`[HEAT]`, or `[HEAT, COOL]` when cooling is supported) and pointing the docstring
  at `preset_mode`'s new `"standby"` option instead.

- **Preset selector only exposed 3 of the device's 7 real operating modes, and read
  from the wrong register**: `preset_mode` inferred HA's `comfort`/`sleep`/`away`
  presets from each circuit's own `hcOpMode`/`dhwOpMode` readback (`normal`/
  `setback`/`standby`/`restart`), while `async_set_preset_mode()` actually wrote the
  separate global `pOpMode` register (`0A0112`, decode_type `"2opmode"`, 7 real
  options -- `automatic`/`DAYmode`/`DHWmode`/`emergency`/`manual`/`setback`/`standby`,
  matching FHEM's `%OpMode` in `docs/legacy/00_THZ.pm`). Reading and writing different
  registers meant the displayed preset couldn't reliably reflect what a write had
  actually set, and 4 of the 7 real modes (`automatic`, `DHWmode`, `manual`,
  `emergency`) were never reachable at all. Fixed by reading/writing `pOpMode`
  directly on both sides -- `preset_mode` now returns the device's own mode name
  (cached via a new `_async_read_op_mode()`, mirroring the existing fan-stage-cache
  pattern) and all 7 real options are exposed, using the device's own names instead
  of HA's generic comfort/sleep/away vocabulary.

### Correction

- **"Live pump-running status for firmware 4.39/5.39" (previously a New Feature above)
  was a false alarm and has been removed.** A user report of `zPumpHC`/`zPumpDHW`
  technician "force" selects showing `unknown` was correctly diagnosed as expected
  (one-shot write-only commands, no readable state, matching FHEM), but the follow-up
  assumption — that 4.39/5.39 lacked read-only `dhw_pump`/`heating_circuit_pump`/
  `solar_pump` status — was wrong. A broader audit against FHEM's `00_THZ.pm` found
  `register_map_all.py` (already merged for every firmware) had identical `pxxFB`
  entries for all three pumps all along. The sensors already existed; the "fix" just
  duplicated them. Removed the duplicate from `readings_map_439.py`. If you added these
  via Reconfigure, no action needed — entities keep working, now sourced from the
  pre-existing base map.

### Investigated, not fixed

- **`solarPump` (2.06), `boosterStage3` (2.14), and `evuRelease`/`STB` (2.06, 2.14) show
  a raw hex value instead of on/off.** Checked against FHEM's `00_THZ.pm`: these are
  marked `"n.a."` in FHEM's own `FBglob206`/`FBglob214` tables too — the byte was
  repurposed on these firmware revisions and no bit position has ever been
  reverse-engineered, in FHEM or here. No correct value exists without new hardware
  capture data, so these stay as-is. Added comments at each of the four entries so a
  future contributor doesn't mistake it for an easy fix.

### Bug Fixes

- **Firmware "438" (and other off-point-release 4.3x builds) incorrectly used 5.39-style
  register maps**: any firmware string not listed in `FIRMWARE_MAPS`
  (`register_map_manager.py`) fell through to a `"default"` entry that was really the
  5.39 config, pulling in offsets/fields that don't exist on 4.3x hardware. `"539"` now
  has its own entry, and unrecognized strings fall back to 4.39-style maps — matching
  FHEM's own fallback ("in all other cases I assume firmware 4.39"). Affects, e.g., LWZ
  403 units reporting `"438"`.

- **`THZRegisterNotSupportedError` silently downgraded to a generic decode failure,
  crashing config entry setup**: when a device cleanly reports "register not supported"
  (`01 04`) for a register that doesn't exist on its firmware (e.g. the 5.39-only
  `pxx0A033B` "Flow Rate" on 4.3x hardware), `decode_response()` raised
  `THZRegisterNotSupportedError` — but its own blanket `except Exception` caught it
  again and downgraded it to `None`, indistinguishable from a real failure. That
  surfaced as "Failed setup, will retry: ... Failed to decode device response" and
  aborted the whole entry instead of skipping just the unsupported block (existing
  `unsupported_blocks` handling in `async_setup_entry` never got the chance to run).
  Fixed by letting the error propagate out of `decode_response()`, with
  `_async_update_block()` catching it and returning `None` for that block instead of
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
