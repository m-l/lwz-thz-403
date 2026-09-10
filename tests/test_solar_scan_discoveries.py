"""Tests for pSolarHysteresis and pDHWVaporizationDelay number entities.

Both registers were previously undocumented anywhere -- FHEM's 00_THZ.pm
only ever exposed these values as byte offsets inside the firmware-206-only
"08pxx206" bulk diagnostic block (which times out on 4.3x/5.3x firmware).
They were found by brute-force scanning the unmapped 0A05xx address range
with the read_raw_register debug service, and confirmed against values read
directly off the LWZ 403 SOL control panel's service menu:
    HISTEREZA SOLAR  = 1.8 K   -> command 0A058F, raw 0x0012 (18 * 0.1)
    OPOZN.PAROWN.CW  = 60 min  -> command 0A058E, raw 0x003C (60 * 1)
"""

from custom_components.thz.register_maps.write_map_439_539 import WRITE_MAP
from custom_components.thz.entity_translations import get_translation_key
from custom_components.thz.const import _classify_hidden_category, should_hide_entity


class TestSolarHysteresisRegistered:
    def test_present_in_write_map(self):
        assert "pSolarHysteresis" in WRITE_MAP

    def test_command_matches_confirmed_register(self):
        assert WRITE_MAP["pSolarHysteresis"]["command"] == "0A058F"

    def test_decodes_to_confirmed_panel_value(self):
        entry = WRITE_MAP["pSolarHysteresis"]
        raw_value = 0x0012
        step = entry["step"]
        assert round(raw_value * step, 1) == 1.8

    def test_config_sane_bounds(self):
        entry = WRITE_MAP["pSolarHysteresis"]
        assert float(entry["min"]) <= 1.8 <= float(entry["max"])
        assert entry["unit"].strip() == "K"
        assert entry["type"] == "number"


class TestSolarHysteresisTranslation:
    def test_translation_key_resolves(self):
        assert get_translation_key("pSolarHysteresis") == "solar_hysteresis"


class TestSolarHysteresisVisibility:
    def test_classified_as_advanced_category(self):
        assert _classify_hidden_category("pSolarHysteresis") == "advanced"

    def test_hidden_by_default(self):
        assert should_hide_entity("pSolarHysteresis") is True


class TestDHWVaporizationDelayRegistered:
    def test_present_in_write_map(self):
        assert "pDHWVaporizationDelay" in WRITE_MAP

    def test_command_matches_confirmed_register(self):
        assert WRITE_MAP["pDHWVaporizationDelay"]["command"] == "0A058E"

    def test_decodes_to_confirmed_panel_value(self):
        entry = WRITE_MAP["pDHWVaporizationDelay"]
        raw_value = 0x003C
        step = entry["step"]
        assert raw_value * step == 60

    def test_config_sane_bounds(self):
        entry = WRITE_MAP["pDHWVaporizationDelay"]
        assert float(entry["min"]) <= 60 <= float(entry["max"])
        assert entry["unit"].strip() == "min"
        assert entry["type"] == "number"


class TestDHWVaporizationDelayTranslation:
    def test_translation_key_resolves(self):
        assert (
            get_translation_key("pDHWVaporizationDelay")
            == "dhw_vaporization_delay"
        )


class TestDHWVaporizationDelayVisibility:
    def test_classified_as_advanced_category(self):
        assert _classify_hidden_category("pDHWVaporizationDelay") == "advanced"

    def test_hidden_by_default(self):
        assert should_hide_entity("pDHWVaporizationDelay") is True
