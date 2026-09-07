"""Tests for the THZ climate platform."""
from unittest.mock import AsyncMock, MagicMock

import pytest

from homeassistant.components.climate import HVACMode


class TestClimateModule:
    """Test that climate module imports and has the expected structure."""

    def test_import_climate_module(self):
        """Test that climate module can be imported."""
        from custom_components.thz import climate
        assert climate is not None

    def test_climate_has_async_setup_entry(self):
        """Test that climate module has async_setup_entry function."""
        from custom_components.thz.climate import async_setup_entry
        assert callable(async_setup_entry)

    def test_climate_has_entity_class(self):
        """Test that climate module has THZClimate class."""
        from custom_components.thz.climate import THZClimate
        assert THZClimate is not None


class TestClimateHelpers:
    """Test module-level helper functions."""

    def test_get_step_from_step_key(self):
        """_get_step returns float from 'step' key."""
        from custom_components.thz.climate import _get_step
        assert _get_step({"step": 0.1}) == pytest.approx(0.1)

    def test_get_step_from_factor_key(self):
        """_get_step falls back to 'factor' key."""
        from custom_components.thz.climate import _get_step
        assert _get_step({"factor": "0.1"}) == pytest.approx(0.1)

    def test_get_step_default(self):
        """_get_step returns 1.0 when neither key is present."""
        from custom_components.thz.climate import _get_step
        assert _get_step({}) == pytest.approx(1.0)

    def test_find_entry_returns_first_match(self):
        """_find_entry returns first entry with a command field."""
        from custom_components.thz.climate import _find_entry
        regs = {
            "p01RoomTempDayHC1": {"command": "0B0005", "step": 0.1},
            "p01RoomTempDay":    {"command": "0B0006", "step": 1.0},
        }
        result = _find_entry(regs, ["p01RoomTempDayHC1", "p01RoomTempDay"])
        assert result is not None
        assert result["command"] == "0B0005"

    def test_find_entry_skips_missing_command(self):
        """_find_entry skips entries without a 'command' field."""
        from custom_components.thz.climate import _find_entry
        regs = {
            "p01RoomTempDay":    {"step": 1.0},          # no command
            "p01RoomTempDayHC1": {"command": "0B0005"},
        }
        result = _find_entry(regs, ["p01RoomTempDay", "p01RoomTempDayHC1"])
        assert result is not None
        assert result["command"] == "0B0005"

    def test_find_entry_returns_none_when_not_found(self):
        """_find_entry returns None when no candidate matches."""
        from custom_components.thz.climate import _find_entry
        assert _find_entry({}, ["p01RoomTempDayHC1"]) is None

    def test_read_temp_valid(self):
        """_read_temp decodes a signed 16-bit temperature correctly."""
        from custom_components.thz.climate import _read_temp
        # 215 big-endian → 21.5 °C (factor 10)
        data = bytes(10) + bytes([0x00, 0xD7]) + bytes(10)
        result = _read_temp(data, 10, 2)
        assert result == pytest.approx(21.5)

    def test_read_temp_too_short(self):
        """_read_temp returns None when data is too short."""
        from custom_components.thz.climate import _read_temp
        assert _read_temp(b"\x00", 5, 2) is None

    def test_read_op_mode_normal(self):
        """_read_op_mode maps opmodehc 'normal' (1) to HEAT."""
        from custom_components.thz.climate import _read_op_mode
        # value 1 → "normal" → HEAT
        data = bytes(24) + bytes([0x01]) + bytes(5)
        assert _read_op_mode(data, 24, 1) == HVACMode.HEAT

    def test_read_op_mode_standby(self):
        """_read_op_mode maps opmodehc 'standby' (3) to OFF."""
        from custom_components.thz.climate import _read_op_mode
        data = bytes(24) + bytes([0x03]) + bytes(5)
        assert _read_op_mode(data, 24, 1) == HVACMode.OFF

    def test_cooling_active_bit_set(self):
        """_cooling_active returns True when cooling bit is set."""
        from custom_components.thz.climate import (
            _A176_COOLING_BIT,
            _A176_COOLING_BYTE,
            _cooling_active,
        )
        data = bytearray(10)
        data[_A176_COOLING_BYTE] = 1 << _A176_COOLING_BIT
        assert _cooling_active(bytes(data)) is True

    def test_cooling_active_bit_clear(self):
        """_cooling_active returns False when cooling bit is clear."""
        from custom_components.thz.climate import _cooling_active
        assert _cooling_active(bytes(10)) is False

    def test_cooling_active_short_data(self):
        """_cooling_active returns False for data shorter than byte index."""
        from custom_components.thz.climate import _cooling_active
        assert _cooling_active(b"\x00") is False


class TestTHZClimateEntity:
    """Tests for THZClimate entity instantiation and properties."""

    @staticmethod
    def _make_coordinator(data: bytes | None = None):
        """Create a minimal mock coordinator."""
        coord = MagicMock()
        coord.data = data
        coord.async_add_listener = MagicMock(return_value=lambda: None)
        return coord

    @staticmethod
    def _make_device():
        """Create a minimal mock THZDevice."""
        device = MagicMock()
        device.lock = MagicMock()
        device.lock.__aenter__ = AsyncMock(return_value=None)
        device.lock.__aexit__ = AsyncMock(return_value=None)
        return device

    @staticmethod
    def _make_hc1_entity(
        heat_entry=None,
        cool_switch_entry=None,
        cool_setpoint_entry=None,
        coord_data: bytes | None = None,
    ):
        """Instantiate an HC1-style THZClimate entity with minimal config."""
        from custom_components.thz.climate import (
            THZClimate,
            _F4_INSIDE_TEMP_OFFSET, _F4_INSIDE_TEMP_LEN,
            _F4_ROOM_SET_TEMP_OFFSET, _F4_ROOM_SET_TEMP_LEN,
            _F4_HC_OP_MODE_OFFSET, _F4_HC_OP_MODE_LEN,
        )
        coordinator = TestTHZClimateEntity._make_coordinator(coord_data)
        device = TestTHZClimateEntity._make_device()
        return THZClimate(
            coordinator=coordinator,
            cooling_coordinator=None,
            device=device,
            device_id="test_device",
            translation_key="heating_circuit",
            current_temp_offset=_F4_INSIDE_TEMP_OFFSET,
            current_temp_length=_F4_INSIDE_TEMP_LEN,
            target_temp_offset=_F4_ROOM_SET_TEMP_OFFSET,
            target_temp_length=_F4_ROOM_SET_TEMP_LEN,
            op_mode_offset=_F4_HC_OP_MODE_OFFSET,
            op_mode_length=_F4_HC_OP_MODE_LEN,
            heat_setpoint_entry=heat_entry,
            cool_switch_entry=cool_switch_entry,
            cool_setpoint_entry=cool_setpoint_entry,
        )

    # ── hvac_modes ──────────────────────────────────────────────────────────

    def test_hvac_modes_heat_only_without_cooling(self):
        """Entity without cooling entries supports only HEAT and OFF."""
        entity = self._make_hc1_entity()
        assert HVACMode.COOL not in entity.hvac_modes
        assert HVACMode.HEAT in entity.hvac_modes
        assert HVACMode.OFF in entity.hvac_modes

    def test_hvac_modes_includes_cool_when_entries_provided(self):
        """Entity with both cool switch and setpoint entries supports COOL."""
        cool_switch = {"command": "0B0287", "decode_type": "1clean"}
        cool_setpoint = {
            "command": "0B0582", "step": 0.1, "decode_type": "5temp",
            "min": "12", "max": "27",
        }
        entity = self._make_hc1_entity(
            cool_switch_entry=cool_switch,
            cool_setpoint_entry=cool_setpoint,
        )
        assert HVACMode.COOL in entity.hvac_modes

    def test_cooling_not_supported_when_only_switch_missing(self):
        """Cooling requires both switch AND setpoint entries."""
        cool_setpoint = {"command": "0B0582", "step": 0.1, "decode_type": "5temp"}
        entity = self._make_hc1_entity(cool_setpoint_entry=cool_setpoint)
        assert HVACMode.COOL not in entity.hvac_modes

    # ── unique_id ────────────────────────────────────────────────────────────

    def test_unique_id_contains_device_and_key(self):
        """Unique ID incorporates device_id and translation_key."""
        entity = self._make_hc1_entity()
        assert "test_device" in entity.unique_id
        assert "heating_circuit" in entity.unique_id

    # ── current_temperature ─────────────────────────────────────────────────

    def test_current_temperature_none_when_no_data(self):
        """current_temperature is None when coordinator has no data."""
        entity = self._make_hc1_entity(coord_data=None)
        assert entity.current_temperature is None

    def test_current_temperature_decoded_correctly(self):
        """current_temperature decodes insideTempRC from coordinator data.

        insideTempRC is at byte offset 34, length 2, hex2int factor 10.
        Value 0x00CD = 205 → 20.5 °C.
        """
        from custom_components.thz.climate import _F4_INSIDE_TEMP_OFFSET
        data = bytearray(60)
        data[_F4_INSIDE_TEMP_OFFSET] = 0x00
        data[_F4_INSIDE_TEMP_OFFSET + 1] = 0xCD   # 205 / 10 = 20.5
        entity = self._make_hc1_entity(coord_data=bytes(data))
        assert entity.current_temperature == pytest.approx(20.5)

    # ── target_temperature ───────────────────────────────────────────────────

    def test_target_temperature_decoded_correctly(self):
        """target_temperature decodes roomSetTemp from coordinator data.

        roomSetTemp is at byte offset 28, length 2, hex2int factor 10.
        Value 0x00D2 = 210 → 21.0 °C.
        """
        from custom_components.thz.climate import _F4_ROOM_SET_TEMP_OFFSET
        data = bytearray(60)
        data[_F4_ROOM_SET_TEMP_OFFSET] = 0x00
        data[_F4_ROOM_SET_TEMP_OFFSET + 1] = 0xD2   # 210 / 10 = 21.0
        entity = self._make_hc1_entity(coord_data=bytes(data))
        assert entity.target_temperature == pytest.approx(21.0)

    # ── hvac_mode ────────────────────────────────────────────────────────────

    def test_hvac_mode_heat_from_normal_opmode(self):
        """hvac_mode is HEAT when hcOpMode is 'normal' (1)."""
        from custom_components.thz.climate import _F4_HC_OP_MODE_OFFSET
        data = bytearray(60)
        data[_F4_HC_OP_MODE_OFFSET] = 0x01  # 1 = normal → HEAT
        entity = self._make_hc1_entity(coord_data=bytes(data))
        assert entity.hvac_mode == HVACMode.HEAT

    def test_hvac_mode_off_from_standby_opmode(self):
        """hvac_mode is OFF when hcOpMode is 'standby' (3)."""
        from custom_components.thz.climate import _F4_HC_OP_MODE_OFFSET
        data = bytearray(60)
        data[_F4_HC_OP_MODE_OFFSET] = 0x03  # 3 = standby → OFF
        entity = self._make_hc1_entity(coord_data=bytes(data))
        assert entity.hvac_mode == HVACMode.OFF

    def test_hvac_mode_cool_when_cooling_active(self):
        """hvac_mode is COOL when the cooling coordinator reports cooling active."""
        from custom_components.thz.climate import (
            THZClimate,
            _F4_INSIDE_TEMP_OFFSET, _F4_INSIDE_TEMP_LEN,
            _F4_ROOM_SET_TEMP_OFFSET, _F4_ROOM_SET_TEMP_LEN,
            _F4_HC_OP_MODE_OFFSET, _F4_HC_OP_MODE_LEN,
            _A176_COOLING_BYTE, _A176_COOLING_BIT,
        )
        cool_switch = {"command": "0B0287", "decode_type": "1clean"}
        cool_setpoint = {
            "command": "0B0582", "step": 0.1, "decode_type": "5temp",
            "min": "12", "max": "27",
        }

        hc1_data = bytearray(60)
        # normal = HEAT (would win without cooling coordinator)
        hc1_data[_F4_HC_OP_MODE_OFFSET] = 0x01

        a176_data = bytearray(10)
        a176_data[_A176_COOLING_BYTE] = 1 << _A176_COOLING_BIT

        coordinator = self._make_coordinator(bytes(hc1_data))
        cooling_coordinator = self._make_coordinator(bytes(a176_data))
        device = self._make_device()

        entity = THZClimate(
            coordinator=coordinator,
            cooling_coordinator=cooling_coordinator,
            device=device,
            device_id="test_device",
            translation_key="heating_circuit",
            current_temp_offset=_F4_INSIDE_TEMP_OFFSET,
            current_temp_length=_F4_INSIDE_TEMP_LEN,
            target_temp_offset=_F4_ROOM_SET_TEMP_OFFSET,
            target_temp_length=_F4_ROOM_SET_TEMP_LEN,
            op_mode_offset=_F4_HC_OP_MODE_OFFSET,
            op_mode_length=_F4_HC_OP_MODE_LEN,
            heat_setpoint_entry=None,
            cool_switch_entry=cool_switch,
            cool_setpoint_entry=cool_setpoint,
        )
        assert entity.hvac_mode == HVACMode.COOL

    # ── min/max_temp ─────────────────────────────────────────────────────────

    def test_min_max_temp_from_heat_entry(self):
        """min/max temp come from the heat setpoint entry bounds."""
        heat_entry = {"command": "0B0005", "min": "12", "max": "32", "step": 0.1,
                      "decode_type": "5temp"}
        entity = self._make_hc1_entity(heat_entry=heat_entry)
        assert entity.min_temp == pytest.approx(12.0)
        assert entity.max_temp == pytest.approx(32.0)

    def test_min_max_temp_default_when_no_entry(self):
        """min/max temp fall back to defaults when no heat entry provided."""
        from custom_components.thz.climate import _DEFAULT_MIN_TEMP, _DEFAULT_MAX_TEMP
        entity = self._make_hc1_entity()
        assert entity.min_temp == pytest.approx(_DEFAULT_MIN_TEMP)
        assert entity.max_temp == pytest.approx(_DEFAULT_MAX_TEMP)

    def test_min_max_temp_from_cool_entry_in_cool_mode(self):
        """In COOL mode min/max come from the cooling setpoint bounds."""
        from custom_components.thz.climate import (
            THZClimate,
            _F4_INSIDE_TEMP_OFFSET, _F4_INSIDE_TEMP_LEN,
            _F4_ROOM_SET_TEMP_OFFSET, _F4_ROOM_SET_TEMP_LEN,
            _F4_HC_OP_MODE_OFFSET, _F4_HC_OP_MODE_LEN,
            _A176_COOLING_BYTE, _A176_COOLING_BIT,
        )
        cool_switch = {"command": "0B0287", "decode_type": "1clean"}
        cool_setpoint = {
            "command": "0B0582", "step": 0.1, "decode_type": "5temp",
            "min": "12", "max": "27",
        }
        heat_entry = {
            "command": "0B0005", "min": "14", "max": "32",
            "step": 0.1, "decode_type": "5temp",
        }

        # Trigger COOL mode via cooling coordinator
        a176_data = bytearray(10)
        a176_data[_A176_COOLING_BYTE] = 1 << _A176_COOLING_BIT

        coordinator = self._make_coordinator(bytes(60))
        cooling_coordinator = self._make_coordinator(bytes(a176_data))
        device = self._make_device()

        entity = THZClimate(
            coordinator=coordinator,
            cooling_coordinator=cooling_coordinator,
            device=device,
            device_id="test_device",
            translation_key="heating_circuit",
            current_temp_offset=_F4_INSIDE_TEMP_OFFSET,
            current_temp_length=_F4_INSIDE_TEMP_LEN,
            target_temp_offset=_F4_ROOM_SET_TEMP_OFFSET,
            target_temp_length=_F4_ROOM_SET_TEMP_LEN,
            op_mode_offset=_F4_HC_OP_MODE_OFFSET,
            op_mode_length=_F4_HC_OP_MODE_LEN,
            heat_setpoint_entry=heat_entry,
            cool_switch_entry=cool_switch,
            cool_setpoint_entry=cool_setpoint,
        )
        assert entity.hvac_mode == HVACMode.COOL
        assert entity.min_temp == pytest.approx(12.0)
        assert entity.max_temp == pytest.approx(27.0)

    # ── device_info ──────────────────────────────────────────────────────────

    def test_device_info_uses_domain_and_device_id(self):
        """device_info links the entity to the correct device."""
        from custom_components.thz.const import DOMAIN
        entity = self._make_hc1_entity()
        assert (DOMAIN, "test_device") in entity.device_info["identifiers"]

    # ── DHW entity ───────────────────────────────────────────────────────────

    def test_dhw_entity_no_cooling_modes(self):
        """DHW climate entity never supports COOL mode."""
        from custom_components.thz.climate import (
            THZClimate,
            _F3_DHW_TEMP_OFFSET, _F3_DHW_TEMP_LEN,
            _F3_DHW_SET_TEMP_OFFSET, _F3_DHW_SET_TEMP_LEN,
            _F3_DHW_OP_MODE_OFFSET, _F3_DHW_OP_MODE_LEN,
        )
        entity = THZClimate(
            coordinator=self._make_coordinator(bytes(40)),
            cooling_coordinator=None,
            device=self._make_device(),
            device_id="test_device",
            translation_key="dhw_heating",
            current_temp_offset=_F3_DHW_TEMP_OFFSET,
            current_temp_length=_F3_DHW_TEMP_LEN,
            target_temp_offset=_F3_DHW_SET_TEMP_OFFSET,
            target_temp_length=_F3_DHW_SET_TEMP_LEN,
            op_mode_offset=_F3_DHW_OP_MODE_OFFSET,
            op_mode_length=_F3_DHW_OP_MODE_LEN,
            heat_setpoint_entry=None,
            cool_switch_entry=None,
            cool_setpoint_entry=None,
        )
        assert HVACMode.COOL not in entity.hvac_modes
        assert HVACMode.HEAT in entity.hvac_modes


class TestTHZClimateOptionalOpMode:
    """HC2 entities may have no per-circuit status field to decode: pxxF5
    (unlike pxxF4 for HC1) has no mapped hcOpMode field on this firmware.
    hvac_mode should gracefully report a fixed HEAT instead of raising or
    guessing at an offset, and everything else (target temperature) should
    keep working normally. Uses literal offsets rather than the module's
    _F4_*/_F3_* constants -- see TestTHZClimateEntity's own helpers, which
    are currently broken (ImportError) because those constants no longer
    exist in climate.py; unrelated to this fix, not addressed here.
    """

    @staticmethod
    def _make_entity_without_opmode(coord_data: bytes | None = None):
        """Instantiate a THZClimate with op_mode_offset/length = None, as
        HC2 entities do when pxxF5 has no hcOpMode field."""
        from custom_components.thz.climate import THZClimate

        coordinator = TestTHZClimateEntity._make_coordinator(coord_data)
        device = TestTHZClimateEntity._make_device()
        return THZClimate(
            coordinator=coordinator,
            cooling_coordinator=None,
            device=device,
            device_id="test_device",
            translation_key="heating_circuit_2",
            current_temp_offset=None,
            current_temp_length=None,
            target_temp_offset=10,
            target_temp_length=2,
            op_mode_offset=None,
            op_mode_length=None,
            heat_setpoint_entry={"command": "0B0005", "step": 0.1},
            cool_switch_entry=None,
            cool_setpoint_entry=None,
        )

    def test_hvac_mode_is_heat_when_op_mode_offset_is_none(self):
        """hvac_mode reports HEAT when there's no op-mode field to decode,
        even though coordinator data is present."""
        entity = self._make_entity_without_opmode(coord_data=bytes(60))
        assert entity.hvac_mode == HVACMode.HEAT

    def test_hvac_mode_is_heat_without_op_mode_regardless_of_data_content(self):
        """A None op_mode_offset short-circuits before any byte decoding --
        short/unexpected data must not raise."""
        entity = self._make_entity_without_opmode(coord_data=b"\x01")
        assert entity.hvac_mode == HVACMode.HEAT

    def test_hvac_mode_is_heat_without_op_mode_and_without_data(self):
        """Also HEAT when the coordinator hasn't received data yet."""
        entity = self._make_entity_without_opmode(coord_data=None)
        assert entity.hvac_mode == HVACMode.HEAT

    def test_hvac_modes_list_unaffected_by_missing_op_mode(self):
        """hvac_modes is still just [HEAT] -- determined by cooling support,
        not by whether op_mode_offset is set."""
        entity = self._make_entity_without_opmode(coord_data=bytes(60))
        assert entity.hvac_modes == [HVACMode.HEAT]

    def test_current_temperature_unaffected_by_missing_op_mode(self):
        """current_temperature is None because HC2 has no room-temperature
        sensor (current_temp_offset=None) -- unrelated to op_mode, and no
        exception is raised getting there."""
        entity = self._make_entity_without_opmode(coord_data=bytes(60))
        assert entity.current_temperature is None

    def test_target_temperature_still_decoded_without_op_mode(self):
        """target_temperature decodes normally: reading it calls hvac_mode
        internally (to pick heat vs. cool setpoint), which must not blow up
        with op_mode_offset=None.

        Byte offset 10, length 2, hex2int factor 10: 0x00D7 = 215 -> 21.5.
        """
        data = bytearray(60)
        data[10] = 0x00
        data[11] = 0xD7
        entity = self._make_entity_without_opmode(coord_data=bytes(data))
        assert entity.target_temperature == pytest.approx(21.5)
