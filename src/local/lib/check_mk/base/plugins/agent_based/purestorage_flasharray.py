#!/usr/bin/env python3

# This file registers the check function that parses and uses the section data from the special agent.
# Since this file is loaded using eval and can't be interactively debugged, it serves as an indirection point to a
# module that can be debugged.

import purestorage_checkmk.flasharray.check
from cmk.base.plugins.agent_based.agent_based_api.v1 import register
from purestorage_checkmk.flasharray.common import flasharray_results_section_id, flasharray_inventory_section_id

register.agent_section(
    name=flasharray_results_section_id,
    parse_function=purestorage_checkmk.flasharray.check.parse_flasharray,
)
register.check_plugin(
    name=flasharray_results_section_id,
    service_name="%s",
    check_function=purestorage_checkmk.flasharray.check.check_purestorage_flasharray,
    discovery_function=purestorage_checkmk.flasharray.check.discover_purestorage_flasharray,
)

register.agent_section(
    name=flasharray_inventory_section_id,
    parse_function=purestorage_checkmk.flasharray.check.parse_flasharray_inventory,
)
register.inventory_plugin(
    name=flasharray_inventory_section_id,
    inventory_function=purestorage_checkmk.flasharray.check.inventory_purestorage_flasharray,
)
