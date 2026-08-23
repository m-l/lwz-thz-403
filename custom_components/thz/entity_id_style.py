"""FHEM/technical-style entity_id slug generation.

This module implements the "fhem" entity_id naming style (see
``CONF_ENTITY_ID_STYLE`` in const.py). It converts a raw internal
register-map/parameter name -- e.g. "dhwPump", "collectorTemp",
"p01RoomTempDayHC1" -- into a lowercase, underscore-separated slug suitable
for Home Assistant's ``suggested_object_id`` mechanism.

Why this works without a hand-built name table: the vast majority of this
integration's internal names were already ported verbatim from FHEM's own
00_THZ.pm parsing tables (read side) or ARE the official Stiebel Eltron
parameter identifiers (write side, e.g. "p01RoomTempDayHC1"). So producing
an "FHEM-flavoured" entity_id mostly just means slugifying a name that is
already FHEM's/Stiebel's own name -- no separate alias table is needed for
these. (Short aliases like "PumpDHW" or "dhw_temp" seen in some FHEM user's
own dashboard are *not* module-native names -- they come from that user's own
``userReadings`` configuration in fhem.cfg, not from 00_THZ.pm itself, so
they aren't a stable target to design against.)

The slug algorithm deliberately uses a single, simple rule -- split only at a
lowercase-or-digit-to-uppercase transition -- rather than a more "thorough"
two-pass camelCase splitter. This keeps multi-letter runs like "STB", "HC1",
"DHWset" glued together as one recognisable token instead of being split
mid-acronym, which better matches how these names actually read in FHEM's
own source and in Stiebel's documentation.
"""

from __future__ import annotations

import re

from .const import ENTITY_ID_STYLE_FHEM

# Matches the boundary between a lowercase letter/digit and an uppercase
# letter, e.g. the "w|P" in "dhwPump" or the "1|R" in "p01RoomTempDayHC1".
# Deliberately does NOT split runs of consecutive uppercase letters (e.g.
# "STB", the "HC1"/"DHW" in "p01RoomTempDayHC1"/"p04DHWsetDayTemp") -- those
# stay together as a single token.
_CAMEL_BOUNDARY = re.compile(r"(?<=[a-z0-9])(?=[A-Z])")
_INVALID_CHARS = re.compile(r"[^0-9a-zA-Z]+")
_MULTI_UNDERSCORE = re.compile(r"_+")


def fhem_style_object_id(raw_name: str) -> str:
    """Convert a raw register-map/parameter name into an entity_id-safe slug.

    Args:
        raw_name: The internal name as it appears in a register-map tuple or
            write-map entry (may have leading/trailing whitespace and/or a
            trailing colon, e.g. " heatingCircuitPump: ").

    Returns:
        A lowercase slug containing only ``[a-z0-9_]``, with no leading,
        trailing, or repeated underscores. Falls back to ``"thz_entity"`` for
        a name that contains no alphanumeric characters at all (defensive;
        should not happen with real register-map data).

    Examples:
        >>> fhem_style_object_id("dhwPump:")
        'dhw_pump'
        >>> fhem_style_object_id(" p01RoomTempDayHC1 ")
        'p01_room_temp_day_hc1'
        >>> fhem_style_object_id("STB")
        'stb'
        >>> fhem_style_object_id("p04DHWsetDayTemp")
        'p04_dhwset_day_temp'
    """
    name = raw_name.strip().rstrip(":").strip()
    name = _CAMEL_BOUNDARY.sub("_", name)
    name = _INVALID_CHARS.sub("_", name)
    name = name.lower()
    name = _MULTI_UNDERSCORE.sub("_", name).strip("_")
    return name or "thz_entity"


def resolve_suggested_object_id(raw_name: str, entity_id_style: str) -> str | None:
    """Return the HA ``suggested_object_id`` for the given naming style.

    Args:
        raw_name: The internal register-map/parameter name for this entity.
        entity_id_style: One of the ``ENTITY_ID_STYLE_*`` values from const.py.

    Returns:
        ``None`` for the default style (HA falls back to its own normal
        name-derived entity_id, i.e. no override), or the FHEM-style slug
        for :data:`ENTITY_ID_STYLE_FHEM`. Note this only affects a
        brand-new entity's *first* entity_id assignment -- it does not
        rename an entity that already exists in the entity registry.
    """
    if entity_id_style != ENTITY_ID_STYLE_FHEM:
        return None
    return fhem_style_object_id(raw_name)
