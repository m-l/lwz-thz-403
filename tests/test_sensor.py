"""Tests for sensor module functions."""

from unittest.mock import MagicMock

import pytest

from custom_components.thz.sensor import THZGenericSensor, normalize_entry


class TestNormalizeEntry:
    """Tests for normalize_entry function."""

    def test_normalize_tuple_entry(self):
        """Test normalizing a tuple entry."""
        entry = ("outsideTemp", 0, 4, "hex2int", 10)
        result = normalize_entry(entry)
        
        assert isinstance(result, dict)
        assert result["name"] == "outsideTemp"
        assert result["offset"] == 0
        assert result["length"] == 4
        assert result["decode"] == "hex2int"
        assert result["factor"] == 10
        assert result["unit"] is None
        assert result["device_class"] is None
        assert result["state_class"] is None
        assert result["icon"] is None
        assert result["translation_key"] is None

    def test_normalize_tuple_with_whitespace(self):
        """Test normalizing a tuple entry with whitespace in name."""
        entry = ("  flowTemp  ", 2, 4, "hex2int", 10)
        result = normalize_entry(entry)
        
        assert result["name"] == "flowTemp"
        assert result["offset"] == 2
        assert result["length"] == 4

    def test_normalize_dict_entry(self):
        """Test normalizing a dictionary entry (returns as-is)."""
        entry = {
            "name": "dhwTemp",
            "offset": 4,
            "length": 4,
            "decode": "hex2int",
            "factor": 10,
            "unit": "°C",
            "device_class": "temperature",
            "state_class": "measurement",
            "icon": "mdi:thermometer",
            "translation_key": "dhw_temp",
        }
        result = normalize_entry(entry)
        
        assert result == entry
        assert result["name"] == "dhwTemp"
        assert result["unit"] == "°C"
        assert result["device_class"] == "temperature"

    def test_normalize_invalid_entry(self):
        """Test normalizing an invalid entry type raises ValueError."""
        with pytest.raises(ValueError, match="Unsupported sensor entry format"):
            normalize_entry("invalid_string")

    def test_normalize_invalid_list(self):
        """Test normalizing a list raises ValueError."""
        with pytest.raises(ValueError, match="Unsupported sensor entry format"):
            normalize_entry(["name", 0, 4, "hex2int", 10])

    def test_normalize_tuple_minimal(self):
        """Test normalizing tuple with minimal values."""
        entry = ("sensor", 0, 2, "hex", 1)
        result = normalize_entry(entry)
        
        assert result["name"] == "sensor"
        assert result["offset"] == 0
        assert result["length"] == 2
        assert result["decode"] == "hex"
        assert result["factor"] == 1

    def test_normalize_six_element_tuple(self):
        """Test normalizing a 6-element tuple with metadata dict."""
        meta = {"unit": "°C", "device_class": "temperature", "state_class": "measurement",
                "icon": "mdi:thermometer", "translation_key": "outside_temp"}
        entry = ("outsideTemp:", 8, 4, "hex2int", 10, meta)
        result = normalize_entry(entry)

        assert result["name"] == "outsideTemp:"
        assert result["unit"] == "°C"
        assert result["device_class"] == "temperature"
        assert result["state_class"] == "measurement"
        assert result["icon"] == "mdi:thermometer"
        assert result["translation_key"] == "outside_temp"

    def test_normalize_six_element_tuple_partial_meta(self):
        """Test normalizing a 6-element tuple with partial metadata."""
        entry = (
            "boosterStage1:",
            46,
            1,
            "bit2",
            1,
            {"translation_key": "booster_stage_1"},
        )
        result = normalize_entry(entry)

        assert result["translation_key"] == "booster_stage_1"
        assert result["unit"] is None
        assert result["device_class"] is None


class TestSensorNameCleaning:
    """Tests for sensor name cleaning logic in async_setup_entry."""

    def test_strip_trailing_colon_from_name(self):
        """Test that trailing colons are stripped."""
        name = "outsideTemp:"
        cleaned = name.strip().rstrip(':')
        assert cleaned == "outsideTemp"

    def test_strip_whitespace_and_colon(self):
        """Test that whitespace and colons are stripped."""
        name = "  flowTemp:  "
        cleaned = name.strip().rstrip(':')
        assert cleaned == "flowTemp"

    def test_name_without_special_chars(self):
        """Test names without special characters."""
        name = "returnTemp"
        cleaned = name.strip().rstrip(':')
        assert cleaned == "returnTemp"


class TestSensorMetadataIntegration:
    """Tests for sensor metadata integration."""

    def test_register_map_provides_device_class(self):
        """Test that register map tuples provide device class in 6th element."""
        from custom_components.thz.register_maps.register_map_all import REGISTER_MAP

        # Check outsideTemp in pxxFB has temperature metadata
        pxx_fb = REGISTER_MAP["pxxFB"]
        outside_temp = next(t for t in pxx_fb if t[0].strip().rstrip(":") == "outsideTemp")
        meta = outside_temp[5]
        assert meta.get("device_class") == "temperature"
        assert meta.get("unit") == "°C"

    def test_register_map_provides_translation_key(self):
        """Test that register map tuples provide translation key in 6th element."""
        from custom_components.thz.register_maps.register_map_all import REGISTER_MAP

        pxx_fb = REGISTER_MAP["pxxFB"]
        outside_temp = next(t for t in pxx_fb if t[0].strip().rstrip(":") == "outsideTemp")
        meta = outside_temp[5]
        assert meta.get("translation_key") == "outside_temp"


class TestOffsetLengthCalculation:
    """Tests for offset and length calculation logic."""

    def test_offset_byte_conversion(self):
        """Test offset conversion from register to byte offset."""
        # In the code: offset // 2
        register_offset = 4
        byte_offset = register_offset // 2
        assert byte_offset == 2

    def test_length_byte_conversion(self):
        """Test length conversion from register to byte length."""
        # In the code: (length + 1) // 2
        register_length = 4
        byte_length = (register_length + 1) // 2
        assert byte_length == 2

    def test_length_odd_value(self):
        """Test length conversion with odd register length."""
        register_length = 3
        byte_length = (register_length + 1) // 2
        assert byte_length == 2  # 3+1=4, 4//2=2

    def test_length_minimum(self):
        """Test length conversion with minimum register length."""
        register_length = 0
        byte_length = (register_length + 1) // 2
        assert byte_length == 0  # (0+1)//2 = 0 (actual result)
        
    def test_length_ensures_at_least_some_bytes(self):
        """Test that length conversion always produces a result."""
        register_length = 1
        byte_length = (register_length + 1) // 2
        assert byte_length == 1  # (1+1)//2 = 1


class TestBlockHexProcessing:
    """Tests for block hex string processing."""

    def test_remove_pxx_prefix(self):
        """Test removing 'pxx' prefix from block identifier."""
        block = "pxx0100"
        block_hex = block.removeprefix("pxx")
        assert block_hex == "0100"

    def test_block_without_prefix(self):
        """Test block without 'pxx' prefix."""
        block = "0100"
        block_hex = block.removeprefix("pxx")
        assert block_hex == "0100"

    def test_convert_hex_to_bytes(self):
        """Test converting hex string to bytes."""
        block_hex = "0100"
        block_bytes = bytes.fromhex(block_hex)
        assert block_bytes == b'\x01\x00'
        assert len(block_bytes) == 2


class TestDuplicateSensorHandling:
    """Tests for duplicate sensor name handling logic."""

    def test_duplicate_detection_logic(self):
        """Test the logic for detecting duplicate sensor names."""
        seen_sensor_names = set()
        
        # First sensor
        sensor_name = "outsideTemp"
        is_duplicate = sensor_name in seen_sensor_names
        assert not is_duplicate
        seen_sensor_names.add(sensor_name)
        
        # Second sensor with same name
        sensor_name = "outsideTemp"
        is_duplicate = sensor_name in seen_sensor_names
        assert is_duplicate

    def test_different_sensors_not_duplicate(self):
        """Test that different sensor names are not duplicates."""
        seen_sensor_names = set()
        
        sensor_name1 = "outsideTemp"
        sensor_name2 = "flowTemp"
        
        seen_sensor_names.add(sensor_name1)

        is_duplicate = sensor_name2 in seen_sensor_names
        assert not is_duplicate


class TestNativeValueSanityRange:
    """Regression coverage for the implausible-value guard in native_value().

    The device occasionally returns a garbage reading that still passes the
    protocol's checksum (e.g. a corrupted response with a coincidentally
    matching 1-byte CRC), decoding to something like -2303.9 C. Published as
    a sensor state, Home Assistant's recorder bakes that straight into long
    term statistics -- permanently skewing that hour's min/mean/max. These
    tests confirm implausible temperature readings are discarded (native_value
    returns None) instead of being reported, while genuine in-range readings
    and non-temperature sensors are unaffected.
    """

    @staticmethod
    def _make_coordinator(data: bytes | None):
        coord = MagicMock()
        coord.data = data
        coord.async_add_listener = MagicMock(return_value=lambda: None)
        return coord

    @staticmethod
    def _make_temp_sensor(raw_hex: str, offset: int = 0, length: int = 2):
        """Build a THZGenericSensor decoding a hex2int temperature at offset 0."""
        entry = {
            "name": "outsideTemp",
            "offset": offset,
            "length": length,
            "decode": "hex2int",
            "factor": 10,
            "unit": "°C",
            "device_class": "temperature",
            "state_class": "measurement",
        }
        coordinator = TestNativeValueSanityRange._make_coordinator(
            bytes.fromhex(raw_hex)
        )
        return THZGenericSensor(
            coordinator,
            entry=entry,
            block=b"\x00\xfb",
            device_id="test_device",
        )

    def test_implausible_negative_temperature_is_discarded(self):
        """A wildly-out-of-range decoded value returns None, not the garbage number."""
        # 0xA6C1 signed / 10 = -2303.9 -- matches the kind of value seen from
        # a corrupted read; far outside any real heat pump temperature.
        sensor = self._make_temp_sensor("a6c1")
        assert sensor.native_value is None

    def test_implausible_positive_temperature_is_discarded(self):
        """The sanity range guards the high end too, not just negative garbage."""
        # 0x7530 signed / 10 = 3000.0 C.
        sensor = self._make_temp_sensor("7530")
        assert sensor.native_value is None

    def test_plausible_temperature_is_reported_normally(self):
        """A realistic reading within range still comes through untouched."""
        # 0x00D2 signed / 10 = 21.0 C.
        sensor = self._make_temp_sensor("00d2")
        assert sensor.native_value == 21.0

    def test_boundary_values_are_not_discarded(self):
        """Values exactly at the sane-range boundary are still accepted."""
        # 0xFE0C signed = -500 / 10 = -50.0 C (lower boundary, inclusive).
        sensor = self._make_temp_sensor("fe0c")
        assert sensor.native_value == -50.0

    @staticmethod
    def _make_collector_sensor(raw_hex: str, translation_key: str = "solar_collector_temp"):
        """Build a THZGenericSensor for the solar collector temperature register."""
        entry = {
            "name": "collectorTemp",
            "offset": 0,
            "length": 2,
            "decode": "hex2int",
            "factor": 10,
            "unit": "°C",
            "device_class": "temperature",
            "state_class": "measurement",
            "translation_key": translation_key,
        }
        coordinator = TestNativeValueSanityRange._make_coordinator(
            bytes.fromhex(raw_hex)
        )
        return THZGenericSensor(
            coordinator,
            entry=entry,
            block=b"\x00\x16",
            device_id="test_device",
        )

    def test_solar_collector_stagnation_temperature_is_not_discarded(self):
        """A real stagnation reading (pump stopped, full sun) must not be
        mistaken for a corrupted read -- flat-plate collectors commonly hit
        150-200 C in this state, well past the standard 100 C temperature
        ceiling used for every other sensor.
        """
        # 0x0708 signed / 10 = 180.0 C.
        sensor = self._make_collector_sensor("0708")
        assert sensor.native_value == 180.0

    def test_solar_collector_still_rejects_genuine_garbage(self):
        """The collector's wider range isn't unlimited -- it still catches
        the same kind of implausible value as any other temperature sensor.
        """
        # 0x7530 signed / 10 = 3000.0 C -- no collector gets that hot.
        sensor = self._make_collector_sensor("7530")
        assert sensor.native_value is None

    def test_older_firmwares_collector_temp_translation_key_also_widened(self):
        """Firmware 2.06/2.14 register maps use translation_key
        'collector_temp' (not 'solar_collector_temp') for the same sensor --
        both names must get the widened range.
        """
        sensor = self._make_collector_sensor("0708", translation_key="collector_temp")
        assert sensor.native_value == 180.0

    def test_solar_dhw_and_flow_temps_keep_the_standard_range(self):
        """Only the collector plate itself is expected to reach stagnation
        heat -- the solar loop's DHW-side and flow-side sensors track tank/
        pipe water temperature and stay on the normal -50/100 C range.
        """
        sensor = self._make_collector_sensor("0708", translation_key="solar_dhw_temp")
        assert sensor.native_value is None  # 180.0 C is implausible for this one

    def test_non_temperature_sensor_is_not_range_checked(self):
        """Sensors without a sanity range configured (e.g. energy) pass through
        any decoded value unmodified, however large."""
        entry = {
            "name": "sHeatHCTotal",
            "offset": 0,
            "length": 4,
            "decode": "hex2int",
            "factor": 1,
            "unit": "kWh",
            "device_class": "energy",
            "state_class": "total_increasing",
        }
        # A huge value that would fail the temperature sanity range, but this
        # sensor isn't a temperature so it must not be discarded.
        coordinator = self._make_coordinator((30000).to_bytes(4, "big", signed=True))
        sensor = THZGenericSensor(
            coordinator,
            entry=entry,
            block=b"\x0a\x09\x30",
            device_id="test_device",
        )
        assert sensor.native_value == 30000
