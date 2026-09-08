"""Tests for write-register entities' handling of unsupported registers.

Regression coverage for a bug where a device's clean "register not
supported" response (THZRegisterNotSupportedError) was left uncaught in
THZSelect/THZSwitch/THZNumber/THZTime/THZScheduleTime's async_update(),
unlike the coordinator-based block reads (see test_async_update_block.py,
which already covers _async_update_block()'s equivalent fix). Because these
write-register entities poll their own register directly rather than
through a coordinator, an unsupported register raised straight out of
async_update() -- shown to the user as an ERROR-level "Error on device
update!" traceback from entity_platform.py the moment the entity was first
added, once per Home Assistant startup, for any select/switch/number/time
entity whose register a given device firmware doesn't support.

async_update() now catches THZRegisterNotSupportedError, logs a single INFO
line, and returns -- leaving the entity's previous value (or its initial
default) rather than raising.
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.thz.thz_device import THZRegisterNotSupportedError


def _make_hass_raising(exc: Exception):
    """Mock hass whose async_add_executor_job always raises `exc`."""
    hass = MagicMock()
    hass.async_add_executor_job = AsyncMock(side_effect=exc)
    return hass


def _make_device():
    """Minimal mock THZDevice with a real asyncio lock."""
    device = MagicMock()
    device.lock = asyncio.Lock()
    return device


class TestSelectRegisterNotSupported:
    @pytest.mark.asyncio
    async def test_async_update_swallows_not_supported_error(self):
        from custom_components.thz.select import THZSelect

        device = _make_device()
        entity = THZSelect(
            name="pOpMode",
            entry={"command": "0A0900", "decode_type": "opmode"},
            device=device,
            device_id="test_device",
        )
        entity.hass = _make_hass_raising(
            THZRegisterNotSupportedError("not supported")
        )

        # Must not raise.
        await entity.async_update()

        assert entity.current_option is None


class TestSwitchRegisterNotSupported:
    @pytest.mark.asyncio
    async def test_async_update_swallows_not_supported_error(self):
        from custom_components.thz.switch import THZSwitch

        device = _make_device()
        entity = THZSwitch(
            name="pOpMode",
            entry={"command": "0A0700"},
            device=device,
            device_id="test_device",
        )
        entity.hass = _make_hass_raising(
            THZRegisterNotSupportedError("not supported")
        )

        await entity.async_update()

        # THZSwitch's _is_on starts False and is only ever flipped by a
        # successful decode -- verify the exception path left it untouched
        # (didn't raise) rather than asserting a specific sentinel value.
        assert entity.is_on is False


class TestNumberRegisterNotSupported:
    @pytest.mark.asyncio
    async def test_async_update_swallows_not_supported_error(self):
        from custom_components.thz.number import THZNumber

        device = _make_device()
        entity = THZNumber(
            name="p01RoomTempDayHC1",
            entry={
                "command": "0A0800",
                "min": 0,
                "max": 100,
                "step": 1,
                "unit": "",
                "device_class": "",
                "decode_type": "0clean",
            },
            device=device,
            device_id="test_device",
        )
        entity.hass = _make_hass_raising(
            THZRegisterNotSupportedError("not supported")
        )

        await entity.async_update()

        assert entity.native_value is None


class TestTimeRegisterNotSupported:
    @pytest.mark.asyncio
    async def test_async_update_swallows_not_supported_error(self):
        from custom_components.thz.time import THZTime

        device = _make_device()
        entity = THZTime(
            name="pHolidayBeginTime",
            entry={"command": "0A0600"},
            device=device,
            device_id="test_device",
        )
        entity.hass = _make_hass_raising(
            THZRegisterNotSupportedError("not supported")
        )

        await entity.async_update()

        assert entity.native_value is None


class TestScheduleTimeRegisterNotSupported:
    @pytest.mark.asyncio
    async def test_async_update_swallows_not_supported_error(self):
        from custom_components.thz.time import THZScheduleTime

        device = _make_device()
        entity = THZScheduleTime(
            name="programHC1_Mo_0 Start",
            base_name="programHC1_Mo_0",
            entry={"command": "0A0500", "type": "schedule"},
            device=device,
            device_id="test_device",
            time_type="start",
        )
        entity.hass = _make_hass_raising(
            THZRegisterNotSupportedError("not supported")
        )

        await entity.async_update()

        assert entity.native_value is None
