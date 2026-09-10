"""Tests for p20FlowProportionHC2, a previously-unmapped write register.

p20FlowProportionHC2's name and translation_key ("flow_proportion_hc2")
were already scaffolded in entity_translations.py and strings.json, but
no write map ever had a command for it, so it was silently absent -- never
skipped with a warning, just never created as an entity at all -- unlike
its HC1 sibling p19FlowProportionHC1 (command 0B059D), which has always
worked.

The two heating-circuit register blocks otherwise mirror each other
byte-for-byte (see p16GradientHC2/p18RoomInfluenceHC2 sitting at the same
offsets as p13GradientHC1/p15RoomInfluenceHC1, one block down), and
p17LowEndHC2 sits at 0C059E -- exactly where p14LowEndHC1 sits at 0B059E
relative to p19's 0B059D. That made 0C059D a strong candidate, confirmed
live via the read_raw_register debug service (firmware 4.38, LWZ 403 SOL):
it returned a clean, in-range value (30, i.e. 30%) using the same decode
convention as p19 -- not a timeout, not a "not supported" response.
"""

from custom_components.thz.register_maps.write_map_439_539 import WRITE_MAP
from custom_components.thz.entity_translations import get_translation_key
from custom_components.thz.const import _classify_hidden_category, should_hide_entity


class TestP20FlowProportionHC2Registered:
    """p20FlowProportionHC2 must now have a real write-map entry."""

    def test_present_in_write_map(self):
        assert "p20FlowProportionHC2" in WRITE_MAP

    def test_command_matches_confirmed_register(self):
        assert WRITE_MAP["p20FlowProportionHC2"]["command"] == "0C059D"

    def test_config_mirrors_hc1_sibling(self):
        """Same decode convention as p19FlowProportionHC1, just a different command."""
        hc1 = WRITE_MAP["p19FlowProportionHC1"]
        hc2 = WRITE_MAP["p20FlowProportionHC2"]
        for key in ("min", "max", "unit", "step", "type", "device_class", "decode_type"):
            assert hc2[key] == hc1[key], f"{key} differs from p19FlowProportionHC1"
        assert hc2["command"] != hc1["command"]


class TestP20FlowProportionHC2Translation:
    """The translation_key was already scaffolded before this fix."""

    def test_translation_key_resolves(self):
        assert get_translation_key("p20FlowProportionHC2") == "flow_proportion_hc2"


class TestP20FlowProportionHC2Visibility:
    """Must be gated by enable_hc2, like every other HC2 entity."""

    def test_classified_as_hc2_category(self):
        assert _classify_hidden_category("p20FlowProportionHC2") == "hc2"

    def test_hidden_when_hc2_disabled(self):
        assert should_hide_entity("p20FlowProportionHC2", enable_hc2=False) is True

    def test_visible_when_hc2_enabled(self):
        assert should_hide_entity("p20FlowProportionHC2", enable_hc2=True) is False
