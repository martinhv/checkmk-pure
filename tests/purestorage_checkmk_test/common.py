import typing
import unittest

from purestorage_checkmk.common import SpecialAgentInventory, Attributes, TableRow, Result, State


class SpecialAgentTestCase(unittest.TestCase):
    def assert_inventory_attributes(
            self,
            inventory: SpecialAgentInventory,
            path: typing.List[str]
    ) -> Attributes:
        for attribute in inventory.inventory_attributes:
            if attribute.path == path:
                return attribute
        self.fail(f"No inventory attribute with path {path} found.")

    def assert_inventory_table_rows(
            self,
            inventory: SpecialAgentInventory,
            path: typing.List[str],
            count: typing.Optional[int] = None,
    ) -> typing.List[TableRow]:
        result = []
        for rows in inventory.inventory_table_rows:
            if rows.path == path:
                result.append(rows)
        if count is not None and len(result) != count:
            self.fail(f"Not enough table rows with path {path} found ({len(result)} instead of {count}).")
        return result

    def assert_named_item_service_state(
            self,
            named_items,
            services: typing.Dict[str, Result],
            expected_state: typing.Optional[State] = None
    ):
        self.assertGreaterEqual(len(named_items), 1)
        for named_item in named_items:
            found = False
            for name, service in services.items():
                if named_item.name.lower() == name.lower():
                    found = True
                    if expected_state is not None:
                        self.assertEqual(service.state, expected_state)
                    break
            if not found:
                for name, service in services.items():
                    if named_item.name.lower() in name.lower():
                        found = True
                        if expected_state is not None:
                            self.assertEqual(service.state, expected_state)
                        break
            self.assertTrue(found)
