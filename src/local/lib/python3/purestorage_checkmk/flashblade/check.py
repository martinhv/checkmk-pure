from dataclasses import fields
from typing import Optional

from cmk.base.api.agent_based.checking_classes import DiscoveryResult, CheckResult, Service
from cmk.base.api.agent_based.inventory_classes import InventoryResult
from cmk.base.api.agent_based.type_defs import StringTable
from purestorage_checkmk.checkmk import result_to_checkmk, result_to_metric, result_to_attributes, result_to_table_row
from purestorage_checkmk.flashblade.common import FlashBladeSpecialAgentResultsSection, \
    FlashBladeSpecialAgentInventorySection


def parse_flashblade(string_table: StringTable) -> FlashBladeSpecialAgentResultsSection:
    return FlashBladeSpecialAgentResultsSection.from_section(string_table[0][0])


def parse_flashblade_inventory(
        string_table: StringTable
) -> FlashBladeSpecialAgentInventorySection:
    return FlashBladeSpecialAgentInventorySection.from_section(string_table[0][0])


def discover_purestorage_flashblade(section: Optional[FlashBladeSpecialAgentResultsSection] = None) -> DiscoveryResult:
    """
    This function discovers the services of the FlashBlade.
    :param section: Data from the special agent.
    :return:
    """
    if section is None:
        return
    for field in fields(FlashBladeSpecialAgentResultsSection):
        for name in getattr(section, field.name).services.keys():
            yield Service(item=name)
        for name in getattr(section, field.name).metrics.keys():
            yield Service(item=name)


def check_purestorage_flashblade(
        item: str = "",
        section: Optional[FlashBladeSpecialAgentResultsSection] = None,
) -> CheckResult:
    """
    This function parses the section from the special agent and returns the result. It will be invoked
    once per discovered item.
    :param item: The item being checked.
    :param section: The section received from the special agent.
    :return: The check result.
    """
    if section is None:
        return
    for field in fields(FlashBladeSpecialAgentResultsSection):
        if item in getattr(section, field.name).services:
            yield result_to_checkmk(getattr(section, field.name).services[item])
        if item in getattr(section, field.name).metrics:
            yield result_to_metric(item, getattr(section, field.name).metrics[item])


def inventory_purestorage_flashblade(
        section: Optional[FlashBladeSpecialAgentInventorySection] = None,
) -> InventoryResult:
    for field in fields(FlashBladeSpecialAgentInventorySection):
        for attributes in getattr(section, field.name).inventory_attributes:
            yield result_to_attributes(attributes)
        for table_row in getattr(section, field.name).inventory_table_rows:
            yield result_to_table_row(table_row)
