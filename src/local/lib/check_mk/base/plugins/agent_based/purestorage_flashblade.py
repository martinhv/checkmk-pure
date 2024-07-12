#!/usr/bin/env python3

# This file registers the check function that parses and uses the section data from the special agent.
# Since this file is loaded using eval and can't be interactively debugged, it serves as an indirection point to a
# module that can be debugged.

import purestorage_checkmk.flashblade.check
from cmk.base.plugins.agent_based.agent_based_api.v1 import register
from purestorage_checkmk.flashblade.common import flashblade_results_section_id, flashblade_inventory_section_id

register.agent_section(
    name=flashblade_results_section_id,
    parse_function=purestorage_checkmk.flashblade.check.parse_flashblade,
)
register.check_plugin(
    name=flashblade_results_section_id,
    service_name="%s",
    check_function=purestorage_checkmk.flashblade.check.check_purestorage_flashblade,
    discovery_function=purestorage_checkmk.flashblade.check.discover_purestorage_flashblade,
)

register.agent_section(
    name=flashblade_inventory_section_id,
    parse_function=purestorage_checkmk.flashblade.check.parse_flashblade_inventory,
)
register.inventory_plugin(
    name=flashblade_inventory_section_id,
    inventory_function=purestorage_checkmk.flashblade.check.inventory_purestorage_flashblade,
)
