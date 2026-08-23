"""Integration tests: entity_id_style threads through to _attr_suggested_object_id.

Verifies the full path from each platform's entity class -> THZBaseEntity /
THZGenericSensor / THZBinarySensor -> entity_id_style.resolve_suggested_object_id(),
for both the write-entity platforms (number/switch/select/time) and the
read-entity platforms (sensor/binary_sensor).
"""
from unittest.mock import MagicMock

import pytest

from custom_components.thz.entity_id_style import fhem_style_object_id


def _make_mock_device():
    device = MagicMock()
    device.lock = MagicMock()
    return device


class TestWriteEntityIdStyle:
    """number/switch/select/time entities honour entity_id_style."""

    def test_switch_default_style_leaves_suggested_object_id_unset(self):
        from custom_components.thz.switch import THZSwitch

        entity = THZSwitch(
            name="zPumpHC",
            entry={"command": "0A0052", "type": "switch", "icon": ""},
            device=_make_mock_device(),
            device_id="test_device",
            entity_id_style="default",
        )
        assert getattr(entity, "_attr_suggested_object_id", None) is None

    def test_switch_fhem_style_sets_suggested_object_id(self):
        from custom_components.thz.switch import THZSwitch

        entity = THZSwitch(
            name="zPumpHC",
            entry={"command": "0A0052", "type": "switch", "icon": ""},
            device=_make_mock_device(),
            device_id="test_device",
            entity_id_style="fhem",
        )
        assert entity._attr_suggested_object_id == fhem_style_object_id("zPumpHC")

    def test_number_fhem_style_sets_suggested_object_id(self):
        from custom_components.thz.number import THZNumber

        entity = THZNumber(
            name="p01RoomTempDayHC1",
            entry={
                "command": "0A0800",
                "type": "number",
                "icon": "",
                "min": 0,
                "max": 100,
                "step": 1,
                "unit": "",
                "device_class": "",
                "decode_type": "0clean",
            },
            device=_make_mock_device(),
            device_id="test_device",
            entity_id_style="fhem",
        )
        assert entity._attr_suggested_object_id == "p01_room_temp_day_hc1"

    def test_select_fhem_style_sets_suggested_object_id(self):
        from custom_components.thz.select import THZSelect

        entity = THZSelect(
            name="pOpMode",
            entry={"command": "0A0900", "type": "select", "icon": "", "decode_type": "opmode"},
            device=_make_mock_device(),
            device_id="test_device",
            entity_id_style="fhem",
        )
        assert entity._attr_suggested_object_id == "p_op_mode"

    def test_time_fhem_style_sets_suggested_object_id(self):
        from custom_components.thz.time import THZTime

        entity = THZTime(
            name="pHolidayBeginTime",
            entry={"command": "0A0600", "type": "time", "icon": "mdi:clock"},
            device=_make_mock_device(),
            device_id="test_device",
            entity_id_style="fhem",
        )
        assert entity._attr_suggested_object_id == fhem_style_object_id(
            "pHolidayBeginTime"
        )

    def test_schedule_time_fhem_style_includes_start_end_suffix(self):
        from custom_components.thz.time import THZScheduleTime

        entry = {"command": "0A0500", "type": "schedule", "icon": "mdi:calendar-clock"}
        start_entity = THZScheduleTime(
            name="programHC1_Mo_0 Start",
            base_name="programHC1_Mo_0",
            entry=entry,
            device=_make_mock_device(),
            device_id="test_device",
            time_type="start",
            entity_id_style="fhem",
        )
        end_entity = THZScheduleTime(
            name="programHC1_Mo_0 End",
            base_name="programHC1_Mo_0",
            entry=entry,
            device=_make_mock_device(),
            device_id="test_device",
            time_type="end",
            entity_id_style="fhem",
        )
        assert start_entity._attr_suggested_object_id == "program_hc1_mo_0_start"
        assert end_entity._attr_suggested_object_id == "program_hc1_mo_0_end"

    def test_default_entity_id_style_is_backward_compatible(self):
        """Omitting entity_id_style entirely still works (defaults to "default")."""
        from custom_components.thz.switch import THZSwitch

        entity = THZSwitch(
            name="zPumpHC",
            entry={"command": "0A0052", "type": "switch", "icon": ""},
            device=_make_mock_device(),
            device_id="test_device",
        )
        assert getattr(entity, "_attr_suggested_object_id", None) is None


class TestReadEntityIdStyle:
    """sensor/binary_sensor entities honour entity_id_style."""

    def test_generic_sensor_default_style_leaves_suggested_object_id_unset(self):
        from custom_components.thz.sensor import THZGenericSensor

        coordinator = MagicMock()
        coordinator.data = bytes(10)
        entity = THZGenericSensor(
            coordinator,
            entry={
                "name": "collectorTemp",
                "offset": 4,
                "length": 2,
                "decode": "hex2int",
                "factor": 10,
            },
            block=bytes.fromhex("16"),
            device_id="test_device",
            entity_id_style="default",
        )
        assert getattr(entity, "_attr_suggested_object_id", None) is None

    def test_generic_sensor_fhem_style_sets_suggested_object_id(self):
        from custom_components.thz.sensor import THZGenericSensor

        coordinator = MagicMock()
        coordinator.data = bytes(10)
        entity = THZGenericSensor(
            coordinator,
            entry={
                "name": "collectorTemp",
                "offset": 4,
                "length": 2,
                "decode": "hex2int",
                "factor": 10,
            },
            block=bytes.fromhex("16"),
            device_id="test_device",
            entity_id_style="fhem",
        )
        assert entity._attr_suggested_object_id == "collector_temp"

    def test_binary_sensor_default_style_leaves_suggested_object_id_unset(self):
        from custom_components.thz.binary_sensor import THZBinarySensor

        coordinator = MagicMock()
        coordinator.data = bytes([0x08])
        entity = THZBinarySensor(
            coordinator,
            entry={
                "name": "compressor",
                "offset": 0,
                "length": 1,
                "decode": "bit3",
                "icon": "mdi:engine",
                "translation_key": "compressor",
            },
            block=bytes.fromhex("FB"),
            device_id="test_device",
            entity_id_style="default",
        )
        assert getattr(entity, "_attr_suggested_object_id", None) is None

    def test_binary_sensor_fhem_style_sets_suggested_object_id(self):
        from custom_components.thz.binary_sensor import THZBinarySensor

        coordinator = MagicMock()
        coordinator.data = bytes([0x08])
        entity = THZBinarySensor(
            coordinator,
            entry={
                "name": "dhwPump",
                "offset": 22,
                "length": 1,
                "decode": "bit0",
                "icon": "mdi:pump",
                "translation_key": "dhw_pump",
            },
            block=bytes.fromhex("FB"),
            device_id="test_device",
            entity_id_style="fhem",
        )
        assert entity._attr_suggested_object_id == "dhw_pump"


class TestPlatformSetupPassesEntityIdStyle:
    """async_setup_write_platform reads entity_id_style from entry_data."""

    @pytest.mark.asyncio
    async def test_write_platform_defaults_to_default_style_when_absent(self):
        """entry_data without 'entity_id_style' key doesn't crash and defaults safely."""
        from custom_components.thz.platform_setup import async_setup_write_platform
        from custom_components.thz.switch import THZSwitch
        from custom_components.thz.const import DOMAIN

        hass = MagicMock()
        entry_id = "test_entry"
        hass.data = {
            DOMAIN: {
                entry_id: {
                    "write_manager": MagicMock(
                        get_all_registers=MagicMock(
                            return_value={
                                "zPumpHC": {
                                    "command": "0A0052",
                                    "type": "switch",
                                    "icon": "",
                                }
                            }
                        )
                    ),
                    "device": _make_mock_device(),
                    "device_id": "test_device",
                    # deliberately no "entity_id_style" key
                }
            }
        }
        config_entry = MagicMock()
        config_entry.entry_id = entry_id
        config_entry.data = {}

        added = []
        async_add_entities = MagicMock(side_effect=lambda entities, *_a, **_kw: added.extend(entities))

        await async_setup_write_platform(
            hass, config_entry, async_add_entities, THZSwitch, "switch"
        )

        assert len(added) == 1
        assert getattr(added[0], "_attr_suggested_object_id", None) is None
