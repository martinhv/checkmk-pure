import abc
import logging
import os
import time
import typing
import unittest
import uuid

import pypureclient
from pypureclient.flasharray.FA_2_24 import models

import purestorage_checkmk_test.flasharray.mock_admin_settings
import purestorage_checkmk_test.flasharray.mock_alerts
import purestorage_checkmk_test.flasharray.mock_array
import purestorage_checkmk_test.flasharray.mock_array_connection
import purestorage_checkmk_test.flasharray.mock_certificates
import purestorage_checkmk_test.flasharray.mock_controllers
import purestorage_checkmk_test.flasharray.mock_dns
import purestorage_checkmk_test.flasharray.mock_drives
import purestorage_checkmk_test.flasharray.mock_hardware
import purestorage_checkmk_test.flasharray.mock_hosts
import purestorage_checkmk_test.flasharray.mock_network_interfaces
import purestorage_checkmk_test.flasharray.mock_smtp
import purestorage_checkmk_test.flasharray.mock_support
import purestorage_checkmk_test.flasharray.mock_volumes
from purestorage_checkmk.common import State, CheckResponse, LimitConfiguration
from purestorage_checkmk.flasharray.common import FlashArraySpecialAgentConfiguration, default_closed_alerts_lifetime, \
    AlertsConfiguration, default_array_warn, default_array_crit, default_cert_warn, default_cert_crit
from purestorage_checkmk.flasharray.special_agent import FlashArraySpecialAgent
from purestorage_checkmk_test.common import SpecialAgentTestCase
from purestorage_checkmk_test.flasharray import mock
from purestorage_checkmk_test.flasharray.mock_apitokens_container import APITokensContainer
from purestorage_checkmk_test.flasharray.mock_port_details import PortContainer


class FlashArraySpecialAgentContext:
    _cfg: FlashArraySpecialAgentConfiguration
    _sa: typing.Optional[FlashArraySpecialAgent]

    def __init__(self, cfg: FlashArraySpecialAgentConfiguration):
        self._cfg = cfg
        self._sa = None

    def __enter__(self) -> FlashArraySpecialAgent:
        self._sa = FlashArraySpecialAgent(self._cfg)
        return self._sa

    def __exit__(self, *args):
        del self._sa


class FlashArrayClientContext:
    def __init__(self, hostname, api_token, cert_file):
        self._hostname = hostname
        self._api_token = api_token
        self._cert_file = cert_file

    def __enter__(self) -> pypureclient.flasharray.client.Client:
        self._cli = pypureclient.flasharray.client.Client(
            self._hostname,
            api_token=self._api_token,
            ssl_cert=self._cert_file
        )
        return self._cli

    def __exit__(self, *args):
        del self._cli


class FlashArraySpecialAgentTest(SpecialAgentTestCase, abc.ABC):
    @abc.abstractmethod
    def special_agent(
            self,
            cfg: typing.Optional[FlashArraySpecialAgentConfiguration] = None
    ) -> FlashArraySpecialAgentContext:
        pass


class FlashArraySpecialAgentIntegrationTest(FlashArraySpecialAgentTest, abc.ABC):

    def client(self) -> FlashArrayClientContext:
        return FlashArrayClientContext(self.hostname, self.api_token, self.cert_file)

    def setUp(self):
        self.hostname = os.getenv("LIVE_FA_HOSTNAME")
        self.api_token = os.getenv("LIVE_FA_APITOKEN")
        self.cert_file = os.getenv("LIVE_FA_CERT_FILE")

        if self.hostname is None or self.hostname == "" or self.api_token is None or self.api_token == "":
            self.skipTest("No live credentials present.")

        if self.cert_file is not None:
            try:
                with open(self.cert_file) as f:
                    self.cert = f.read()
            except Exception as e:
                self.fail(f"Failed to load certificate file {self.cert_file} due to {type(e).__name__}: {str(e)}")
        else:
            self.cert = None

        # noinspection PyBroadException
        try:
            with self.client():
                pass
        except Exception as e:
            self.fail(f"Live connection failed due to {type(e).__name__}: {str(e)}")

    def special_agent(
            self,
            cfg: typing.Optional[FlashArraySpecialAgentConfiguration] = None
    ) -> FlashArraySpecialAgentContext:
        if cfg is None:
            cfg = FlashArraySpecialAgentConfiguration(
                host="",
                api_token="",
                verify_tls=False,
                cacert="",
            )
        if cfg.host is None or cfg.host == "":
            cfg.host = self.hostname
        if cfg.api_token is None or cfg.api_token == "":
            cfg.api_token = self.api_token
        if (cfg.cacert is None or cfg.cacert == "") and cfg.verify_tls:
            cfg.cacert = self.cert_file
            cfg.verify_tls = cfg.cacert is not None
        return FlashArraySpecialAgentContext(cfg)

    def hardware_items_by_type(self, item_type) -> typing.List[models.Hardware]:
        with self.client() as cli:
            return list(filter(lambda hw: hw.type == item_type, cli.get_hardware().items))

    def assert_hardware_items_have_services(self, agent, item_type):
        hardware_items = self.hardware_items_by_type(item_type)
        hardware_services = agent.results().hardware.services
        self.assert_named_item_service_state(hardware_items, hardware_services)


class FlashArraySpecialAgentUnitTest(FlashArraySpecialAgentTest, abc.ABC):

    def setUp(self) -> None:
        self.api_token = str(uuid.uuid4())
        self.drives = purestorage_checkmk_test.flasharray.mock_drives.DrivesContainer()
        self.controllers = purestorage_checkmk_test.flasharray.mock_controllers.ControllersContainer()
        self.ports = purestorage_checkmk_test.flasharray.mock_port_details.PortContainer(self.controllers)
        self.hardwares = purestorage_checkmk_test.flasharray.mock_hardware.HardwaresContainer(
            self.drives,
            self.controllers,
            self.ports,
        )
        self.arrays = purestorage_checkmk_test.flasharray.mock_array.ArraysContainer()
        self.certificates = purestorage_checkmk_test.flasharray.mock_certificates.CertificatesContainer()
        self.alerts = purestorage_checkmk_test.flasharray.mock_alerts.AlertsContainer()
        self.admin_settings = purestorage_checkmk_test.flasharray.mock_admin_settings.AdminSettingsContainer()
        self.smtp_servers = purestorage_checkmk_test.flasharray.mock_smtp.SMTPServersContainer()
        self.dns_servers = purestorage_checkmk_test.flasharray.mock_dns.DNSServersContainer()
        self.array_connections = purestorage_checkmk_test.flasharray.mock_array_connection.ArrayConnectionContainer()
        self.network_interfaces = purestorage_checkmk_test.flasharray.mock_network_interfaces.NetworkInterfaceContainer()
        self.volumes = purestorage_checkmk_test.flasharray.mock_volumes.VolumesContainer()
        self.hosts = purestorage_checkmk_test.flasharray.mock_hosts.HostsContainer()
        self.support = purestorage_checkmk_test.flasharray.mock_support.SupportContainer()
        self.api_tokens = APITokensContainer({self.api_token})
        self.mock_server = mock.FlashArray(
            api_tokens_container=self.api_tokens,
            drives_container=self.drives,
            controllers_container=self.controllers,
            hardwares_container=self.hardwares,
            arrays_container=self.arrays,
            alerts_container=self.alerts,
            certificates_container=self.certificates,
            admin_settings_container=self.admin_settings,
            smtp_servers_container=self.smtp_servers,
            dns_servers_container=self.dns_servers,
            array_connections_container=self.array_connections,
            network_interfaces_container=self.network_interfaces,
            volumes_container=self.volumes,
            hosts_container=self.hosts,
            support_container=self.support,
            port_container=self.ports,
        )
        self.mock_server.start()

    def tearDown(self) -> None:
        self.mock_server.stop()

    def special_agent(
            self,
            cfg: typing.Optional[FlashArraySpecialAgentConfiguration] = None
    ) -> FlashArraySpecialAgentContext:
        if cfg is None:
            cfg = FlashArraySpecialAgentConfiguration(
                host="",
                api_token="",
                verify_tls=False,
                cacert="",
            )
        if cfg.host is None or cfg.host == "":
            cfg.host = f"127.0.0.1:{self.mock_server.port()}"
        if cfg.api_token is None or cfg.api_token == "":
            cfg.api_token = self.api_token
        if (cfg.cacert is None or cfg.cacert == "") and cfg.verify_tls:
            cfg.cacert = self.mock_server.cert().decode('ascii')
            cfg.verify_tls = cfg.cacert is not None
        return FlashArraySpecialAgentContext(cfg)

    def assert_hardware_service_state(self, agent, item_type, state: State):
        hardware_items = self.hardwares.basic_items_by_type(item_type)
        hardware_services = agent.results().hardware.services
        self.assert_named_item_service_state(hardware_items, hardware_services, state)


class FlashArrayLoginUnitTest(FlashArraySpecialAgentUnitTest):
    def test_login(self):
        """
        Basic login test

        This function tests the FlashArray mock itself to make sure the basic login works with pypureclient. This
        ensures that all subsequent tests don't fail due to basic incompatibilities.
        """

        cli = pypureclient.flasharray.client.Client(
            f"127.0.0.1:{self.mock_server.port()}",
            api_token=self.api_token,
            ssl_cert=self.mock_server.cert()
        )
        self.assertIsNotNone(cli)
        logging.info("Successful login against the PureStorage FlashArray mock.")


class FlashArrayDrivesUnitTest(FlashArraySpecialAgentUnitTest):
    def test_services(self):
        """
        Drive status unittest
        """

        with self.special_agent() as agent:
            results = agent.results().drives.services
            self.assertEqual(0, len(results))

        with self.special_agent() as agent:
            self.drives.add(1)
            results = agent.results().drives.services
            self.assertEqual(1, len(results))
            drive_result = results.get(self.drives.drives[0].name)
            self.assertEqual(State.OK, drive_result.state)

        with self.special_agent() as agent:
            self.drives.drives[0].status = "unhealthy"
            results = agent.results().drives.services
            self.assertEqual(list(results.values())[0].state, State.WARN)

    def test_inventory(self):
        """
        Drive inventory unittest
        """
        with self.special_agent() as agent:
            backplanes = self.assert_inventory_table_rows(
                agent.inventory().hardware,
                ["hardware", "components", "backplanes"]
            )
            self.assertEqual(
                len(backplanes),
                len(self.drives.drives)
            )
            non_empty_backplanes = list(filter(
                lambda backplane: backplane.inventory_columns["serial"] is not None,
                backplanes
            ))
            self.assertEqual(
                len(non_empty_backplanes),
                len(list(filter(
                    lambda drive: drive.status != "unused",
                    self.drives.drives
                )))
            )

        with self.special_agent() as agent:
            self.drives.add(1)
            backplanes = self.assert_inventory_table_rows(
                agent.inventory().hardware,
                ["hardware", "components", "backplanes"]
            )
            non_empty_backplanes = list(filter(
                lambda backplane: backplane.inventory_columns["serial"] is not None,
                backplanes
            ))
            self.assertEqual(
                len(non_empty_backplanes),
                len(list(filter(
                    lambda drive: drive.status != "unused",
                    self.drives.drives
                )))
            )


class FlashArrayDrivesIntegrationTest(FlashArraySpecialAgentIntegrationTest):
    def test_services(self):
        with self.special_agent() as agent, self.client() as cli:
            results = agent.results().drives.services
            drives = list(filter(lambda drive: drive.status != "unused", CheckResponse(cli.get_drives()).items))
            self.assertEqual(len(results), len(drives))

    def test_inventory(self):
        with self.special_agent() as agent, self.client() as cli:
            backplanes = self.assert_inventory_table_rows(
                agent.inventory().hardware,
                ["hardware", "components", "backplanes"]
            )
            self.assertEqual(
                len(backplanes),
                len(CheckResponse(cli.get_drives()).items)
            )


class FlashArrayControllerUnitTest(FlashArraySpecialAgentUnitTest):
    def test_services(self):
        with self.special_agent() as agent:
            hardware_services = agent.results().hardware.services
            found_controller = False
            for name, service in hardware_services.items():
                if name == "CT0":
                    found_controller = True
                    self.assertEqual(service.state, State.OK)
            self.assertTrue(found_controller)

        with self.special_agent() as agent:
            self.controllers.controllers[0].status = "not ready"
            hardware_services = agent.results().hardware.services
            found_controller = False
            for name, service in hardware_services.items():
                if name == "CT0":
                    found_controller = True
                    self.assertEqual(service.state, State.WARN)
            self.assertTrue(found_controller)

    def test_inventory(self):
        with self.special_agent() as agent:
            controller_rows = self.assert_inventory_table_rows(
                agent.inventory().hardware,
                ["hardware", "storage", "controller"]
            )
            controller_found = False
            for controller_row in controller_rows:
                if controller_row.inventory_columns.get("Type") == "controller":
                    controller_found = True
            self.assertTrue(controller_found, "No controller found in inventory")


class FlashArrayControllerIntegrationTest(FlashArraySpecialAgentIntegrationTest):
    def test_services(self):
        with self.special_agent() as agent:
            hardware_services = agent.results().hardware.services
            found_controller = False
            for name, service in hardware_services.items():
                if name == "CT0":
                    found_controller = True
            self.assertTrue(found_controller)

    def test_inventory(self):
        with self.special_agent() as agent:
            controller_rows = self.assert_inventory_table_rows(
                agent.inventory().hardware,
                ["hardware", "storage", "controller"]
            )
            controller_found = False
            for controller_row in controller_rows:
                if controller_row.inventory_columns.get("Type") == "controller":
                    controller_found = True
            self.assertTrue(controller_found, "No controller found in inventory")


class FlashArrayNetworkInterfaceUnitTest(FlashArraySpecialAgentUnitTest):
    def test_services(self):
        with self.special_agent() as agent:
            services = agent.results().hardware.services
            eth_hardware = list(filter(lambda hardware: hardware.type == "eth_port", self.hardwares.hardwares))
            self.assert_named_item_service_state(eth_hardware, services, State.OK)

        with self.special_agent() as agent:
            for i in range(0, len(self.ports.ports)):
                if self.ports.ports[i].interface_type == "eth":
                    self.ports.ports[i].tx_fault[0].flag = True

            eth_hardware = list(filter(lambda hardware: hardware.type == "eth_port", self.hardwares.hardwares))
            services = agent.results().hardware.services
            self.assert_named_item_service_state(eth_hardware, services, State.WARN)

    def test_inventory(self):
        with self.special_agent() as agent:
            network_interfaces = agent.inventory().network_interfaces
            self.assert_inventory_table_rows(
                network_interfaces,
                ["networking", "interfaces"],
                len(self.network_interfaces.network_interface)
            )
            self.assert_inventory_table_rows(
                network_interfaces,
                ["networking", "addresses"],
                len(list(filter(lambda interface: interface.enabled and interface.interface_type == "eth",
                                self.network_interfaces.network_interface)))
            )


class FlashArrayNetworkInterfaceIntegrationTest(FlashArraySpecialAgentIntegrationTest):
    def test_services(self):
        with self.special_agent() as agent, self.client() as cli:
            eth_interfaces = cli.get_network_interfaces().items

            # Note: the network interface list returns virtual interfaces (e.g. vir0) too, so we need to filter that out
            # because it doesn't report a status.
            def get_eth_subtype(interface):
                try:
                    return interface.eth.subtype
                except AttributeError:
                    return None

            eth_interfaces = list(filter(
                lambda
                    interface: interface.enabled and interface.interface_type == "eth" and get_eth_subtype(
                    interface) == "physical",
                eth_interfaces
            ))
            self.assert_named_item_service_state(eth_interfaces, agent.results().hardware.services)

    def test_inventory(self):
        with self.special_agent() as agent, self.client() as cli:
            network_interfaces = agent.inventory().network_interfaces
            real_network_interfaces = cli.get_network_interfaces().items
            self.assert_inventory_table_rows(
                network_interfaces,
                ["networking", "interfaces"],
                len(real_network_interfaces)
            )
            real_network_interfaces = cli.get_network_interfaces().items
            self.assert_inventory_table_rows(
                network_interfaces,
                ["networking", "addresses"],
                len(list(filter(lambda interface: interface.enabled and interface.interface_type == "eth",
                                real_network_interfaces)))
            )
            real_network_interfaces = cli.get_network_interfaces().items
            interfaces_with_gateway = list(
                filter(
                    lambda
                        interface: interface.enabled and interface.interface_type == "eth" and interface.eth.gateway is not None,
                    real_network_interfaces
                )
            )
            self.assert_inventory_table_rows(
                network_interfaces,
                ["networking", "routes"],
                len(interfaces_with_gateway)
            )


class FlashArrayChassisUnitTest(FlashArraySpecialAgentUnitTest):

    def test_services(self):
        with self.special_agent() as agent:
            hardware_services = agent.results().hardware
            chassis = [self.hardwares.hardware_items[0]]
            self.assert_named_item_service_state(chassis, hardware_services.services, State.OK)

        self.hardwares.hardware_items[0].status = "unhealthy"
        with self.special_agent() as agent:
            hardware_services = agent.results().hardware
            chassis = [self.hardwares.hardware_items[0]]
            self.assert_named_item_service_state(chassis, hardware_services.services, State.WARN)

    def test_inventory(self):
        with self.special_agent() as agent:
            chassis = self.hardwares.hardware_items[0]
            hardware_inventory = agent.inventory().hardware
            chassis_inventory_rows = self.assert_inventory_table_rows(
                hardware_inventory,
                ["hardware", "chassis"]
            )
            self.assertEqual(chassis_inventory_rows[0].key_columns["name"], chassis.name)
            self.assertEqual(chassis_inventory_rows[0].key_columns["model"], chassis.model)
            self.assertEqual(chassis_inventory_rows[0].inventory_columns["serial"], chassis.serial)


class FlashArrayChassisIntegrationTest(FlashArraySpecialAgentIntegrationTest):

    def test_services(self):
        with self.special_agent() as agent, self.client() as cli:
            hardware_services = agent.results().hardware
            chassis = list(filter(lambda hw: hw.type == "chassis", cli.get_hardware().items))
            self.assert_named_item_service_state(chassis, hardware_services.services)

    def test_inventory(self):
        with self.special_agent() as agent, self.client() as cli:
            chassis = list(filter(lambda hw: hw.type == "chassis", cli.get_hardware().items))[0]
            hardware_inventory = agent.inventory().hardware
            chassis_inventory_rows = self.assert_inventory_table_rows(
                hardware_inventory,
                ["hardware", "chassis"]
            )
            self.assertEqual(chassis_inventory_rows[0].key_columns["name"], chassis.name)
            self.assertEqual(chassis_inventory_rows[0].key_columns["model"], chassis.model)
            self.assertEqual(chassis_inventory_rows[0].inventory_columns["serial"], chassis.serial)


class FlashArrayPowerUnitTest(FlashArraySpecialAgentUnitTest):
    def test_services(self):
        with self.special_agent() as agent:
            self.assert_hardware_service_state(agent, "power_supply", State.OK)

        with self.special_agent() as agent:
            for power_supply in self.hardwares.basic_items_by_type("power_supply"):
                power_supply.status = "unhealthy"
            self.assert_hardware_service_state(agent, "power_supply", State.WARN)

    def test_inventory(self):
        with self.special_agent() as agent:
            power_supplies = self.hardwares.basic_items_by_type("power_supply")
            hardware_inventory = agent.inventory().hardware
            self.assert_inventory_table_rows(
                hardware_inventory,
                ["hardware", "components", "psus"],
                len(power_supplies)
            )


class FlashArrayPowerIntegrationTest(FlashArraySpecialAgentIntegrationTest):
    def test_services(self):
        with self.special_agent() as agent, self.client() as cli:
            hardware_services = agent.results().hardware.services
            power_supplies = list(filter(lambda hw: hw.type == "power_supply", cli.get_hardware().items))
            self.assert_named_item_service_state(power_supplies, hardware_services)

    def test_inventory(self):
        with self.special_agent() as agent, self.client() as cli:
            power_supplies = list(filter(lambda hw: hw.type == "power_supply", cli.get_hardware().items))
            hardware_inventory = agent.inventory().hardware
            self.assert_inventory_table_rows(
                hardware_inventory,
                ["hardware", "components", "psus"],
                len(power_supplies)
            )


class FlashArrayFanUnitTest(FlashArraySpecialAgentUnitTest):
    def test_services(self):
        with self.special_agent() as agent:
            self.assert_hardware_service_state(agent, "cooling", State.OK)

        with self.special_agent() as agent:
            for power_supply in self.hardwares.basic_items_by_type("cooling"):
                power_supply.status = "unhealthy"
            self.assert_hardware_service_state(agent, "cooling", State.WARN)

    def test_inventory(self):
        with self.special_agent() as agent:
            power_supplies = self.hardwares.basic_items_by_type("cooling")
            hardware_inventory = agent.inventory().hardware
            self.assert_inventory_table_rows(
                hardware_inventory,
                ["hardware", "components", "fans"],
                len(power_supplies)
            )


class FlashArrayFanIntegrationTest(FlashArraySpecialAgentIntegrationTest):
    def test_services(self):
        with self.special_agent() as agent:
            self.assert_hardware_items_have_services(agent, "cooling")

    def test_inventory(self):
        with self.special_agent() as agent:
            hardware_inventory = agent.inventory().hardware
            fans = self.hardware_items_by_type("cooling")
            self.assert_inventory_table_rows(
                hardware_inventory,
                ["hardware", "components", "fans"],
                len(fans)
            )


class FlashArrayAlertUnitTest(FlashArraySpecialAgentUnitTest):
    def test_services(self):
        cfg = FlashArraySpecialAgentConfiguration(
            alerts=AlertsConfiguration(
                closed_alerts_lifetime=default_closed_alerts_lifetime,
                info=True,
                warning=True,
                critical=True,
                hidden=True,
            )
        )

        with self.special_agent(cfg) as agent:
            self.assertEqual(len(agent.results().alerts.services), 0)

        self.alerts.alerts.append(purestorage_checkmk_test.flasharray.mock_alerts.Alert(
            name="270",
            id=uuid.uuid4().__str__(),
            actual="95%",
            category="array",
            component_type="blade",
            created=1000 * (int(time.time()) - cfg.alerts.closed_alerts_lifetime - 1),
            state="open",
            description="Description of the Alert",
            code=168,
            severity="warning",
            flagged=True,
            updated=1000 * (int(time.time()) - 60),
            component_name="GSE-Blade10",
            notified=0,
            issue="boot drive overutilization",
            knowledge_base_url="https: // support.purestorage.com /?cid = Alert_0168",
            summary="(array: GSE-ARRAY10): Eula not accepted"
        ))

        with self.special_agent() as agent:
            # Default configuration shouldn't report alerts
            self.assertEqual(len(agent.results().alerts.services), 0)

        with self.special_agent(cfg) as agent:
            alert_services = agent.results().alerts.services
            self.assertEqual(len(alert_services), 1)
            service = list(alert_services.values())[0]
            self.assertEqual(service.state, State.WARN)

        self.alerts.alerts[0].state = "closed"

        with self.special_agent(cfg) as agent:
            alert_services = agent.results().alerts.services
            self.assertEqual(len(alert_services), 1)
            service = list(alert_services.values())[0]
            self.assertEqual(service.state, State.OK)

        self.alerts.alerts[0].updated = 1000 * (int(time.time()) - cfg.alerts.closed_alerts_lifetime - 1)

        with self.special_agent(cfg) as agent:
            self.assertEqual(len(agent.results().alerts.services), 0)


class FlashArrayAlertIntegrationTest(FlashArraySpecialAgentIntegrationTest):
    def test_services(self):
        cfg = FlashArraySpecialAgentConfiguration(
            alerts=AlertsConfiguration(
                closed_alerts_lifetime=default_closed_alerts_lifetime,
                info=True,
                warning=True,
                critical=True,
                hidden=True,
            )
        )

        with self.special_agent() as agent:
            self.assertEqual(len(agent.results().alerts.services), 0)

        with self.special_agent(cfg) as agent, self.client() as cli:
            alert_services = agent.results().alerts.services
            time_limit = 1000 * (int(time.time()) - cfg.alerts.closed_alerts_lifetime)
            alerts = list(filter(
                lambda alert: alert.state == "open" or alert.state == "closed" and alert.updated > time_limit,
                cli.get_alerts().items
            ))
            for alert in alerts:
                if alert.state == "open":
                    expected_state = State.WARN
                else:
                    expected_state = State.OK
                self.assert_named_item_service_state(alerts, alert_services, expected_state)


class FlashArrayCapacityUnitTest(FlashArraySpecialAgentUnitTest):
    def test_service(self):
        cfg = FlashArraySpecialAgentConfiguration(
            array=LimitConfiguration(
                default_array_warn,
                default_array_crit
            )
        )

        svc_count_per_array = 10

        with self.special_agent(cfg) as agent:
            mock_arrays = self.arrays.arrays
            mock_arrays[0].capacity = 10000
            mock_arrays[0].space.total_physical = int(mock_arrays[0].capacity * cfg.array.warn / 100 - 1)
            array_services = agent.results().array.services

            self.assertIn("used capacity", array_services)
            self.assertIn("total physical", array_services)
            self.assertIn("shared", array_services)
            self.assertIn("snapshots", array_services)
            self.assertIn("system", array_services)
            self.assertIn("total provisioned", array_services)
            self.assertIn("total capacity", array_services)
            self.assertIn("total reduction", array_services)
            self.assertIn("data reduction", array_services)
            self.assertIn("thin provisioning", array_services)
            self.assertEqual(len(array_services), len(mock_arrays) * svc_count_per_array)
            first_array_service = list(array_services.values())[0]
            self.assertEqual(first_array_service.state, State.OK)

        with self.special_agent(cfg) as agent:
            mock_arrays = self.arrays.arrays
            mock_arrays[0].capacity = 10000
            mock_arrays[0].space.total_physical = int(mock_arrays[0].capacity * cfg.array.warn / 100)
            array_services = agent.results().array.services
            self.assertEqual(len(array_services), len(mock_arrays) * svc_count_per_array)
            self.assertEqual(array_services["used capacity"].state, State.WARN)

        with self.special_agent(cfg) as agent:
            mock_arrays = self.arrays.arrays
            mock_arrays[0].capacity = 10000
            mock_arrays[0].space.total_physical = int(mock_arrays[0].capacity * cfg.array.crit / 100)
            array_services = agent.results().array.services
            self.assertEqual(len(array_services), len(mock_arrays) * 10)
            self.assertEqual(array_services["used capacity"].state, State.CRIT)


class FlashArrayCapacityIntegrationTest(FlashArraySpecialAgentIntegrationTest):
    def test_service(self):
        with self.special_agent() as agent, self.client() as cli:
            arrays = cli.get_arrays().items
            self.assertEqual(len(agent.results().array.services), len(arrays))


class FlashArrayCertificateUnitTest(FlashArraySpecialAgentUnitTest):
    def test_service(self):
        cfg = FlashArraySpecialAgentConfiguration(
            certificates=LimitConfiguration(
                default_cert_warn,
                default_cert_crit,
            )
        )
        self._check_certificate_services(cfg, State.OK)

        for cert in self.certificates.certificates:
            cert.valid_to = (int(time.time()) + default_cert_warn * 86400 - 1) * 1000
        self._check_certificate_services(cfg, State.WARN)
        for cert in self.certificates.certificates:
            cert.valid_to = (int(time.time()) + default_cert_crit * 86400 - 1) * 1000
        self._check_certificate_services(cfg, State.CRIT)

    def _check_certificate_services(self, cfg, state):
        with self.special_agent(cfg) as agent:
            certificate_services = agent.results().certificates.services
            self.assertEqual(len(certificate_services), len(self.certificates.certificates))
            self.assert_named_item_service_state(self.certificates.certificates, certificate_services, state)


class FlashArrayCertificateIntegrationTest(FlashArraySpecialAgentIntegrationTest):
    def test_service(self):
        cfg = FlashArraySpecialAgentConfiguration(
            certificates=LimitConfiguration(
                default_cert_warn,
                default_cert_crit,
            )
        )
        with self.special_agent(cfg) as agent, self.client() as cli:
            certificates: typing.List[models.Certificate] = cli.get_certificates().items
            certificate_services = agent.results().certificates.services
            for certificate in certificates:
                days_remaining = int((certificate.valid_to / 1000 - int(time.time())) / 86400)
                expected_state = State.OK
                if days_remaining < cfg.certificates.crit:
                    expected_state = State.CRIT
                elif days_remaining < cfg.certificates.warn:
                    expected_state = State.WARN
                self.assert_named_item_service_state(certificates, certificate_services, expected_state)


class FlashArrayOSUnitTest(FlashArraySpecialAgentUnitTest):
    def test_inventory(self):
        with self.special_agent() as agent:
            software_attributes = self.assert_inventory_attributes(
                agent.inventory().software,
                ["software", "os"]
            )
            self.assertEqual(software_attributes.inventory_attributes["name"], self.arrays.arrays[0].os)
            self.assertEqual(software_attributes.inventory_attributes["version"], self.arrays.arrays[0].version)


class FlashArrayOSIntegrationTest(FlashArraySpecialAgentIntegrationTest):
    def test_inventory(self):
        with self.special_agent() as agent, self.client() as cli:
            software_attributes = self.assert_inventory_attributes(
                agent.inventory().software,
                ["software", "os"]
            )
            arrays = list(cli.get_arrays().items)
            self.assertEqual(software_attributes.inventory_attributes["name"], arrays[0].os)
            self.assertEqual(software_attributes.inventory_attributes["version"], arrays[0].version)


class FlashArraySSOUnitTest(FlashArraySpecialAgentUnitTest):
    def test_inventory(self):
        with self.special_agent() as agent:
            software_attributes = self.assert_inventory_attributes(
                agent.inventory().software,
                ["software", "os"]
            )
            self.assertEqual(
                software_attributes.inventory_attributes["SingleSignOn Enabled"],
                self.admin_settings.admin_settings[0].single_sign_on_enabled
            )


class FlashArraySSOIntegrationTest(FlashArraySpecialAgentIntegrationTest):
    def test_inventory(self):
        with self.special_agent() as agent, self.client() as cli:
            software_attributes = self.assert_inventory_attributes(
                agent.inventory().software,
                ["software", "os"]
            )
            admin_settings = list(cli.get_admins_settings().items)
            self.assertEqual(
                software_attributes.inventory_attributes["SingleSignOn Enabled"],
                admin_settings[0].single_sign_on_enabled
            )


class FlashArrayPhoneHomeUnitTest(FlashArraySpecialAgentUnitTest):
    def test_inventory(self):
        for val in [True, False]:
            self.support.support[0].phonehome_enabled = val
            with self.special_agent() as agent:
                support_attributes = self.assert_inventory_attributes(
                    agent.inventory().support,
                    ["software", "support"]
                )
                self.assertEqual(
                    support_attributes.inventory_attributes["PhoneHome"],
                    val
                )


class FlashArrayPhoneHomeIntegrationTest(FlashArraySpecialAgentIntegrationTest):
    def test_inventory(self):
        with self.special_agent() as agent, self.client() as cli:
            support_attributes = self.assert_inventory_attributes(
                agent.inventory().support,
                ["software", "support"]
            )
            support = list(cli.get_support().items)[0]
            self.assertEqual(
                support_attributes.inventory_attributes["PhoneHome"],
                support.phonehome_enabled
            )


class FlashArraySystemSettingsUnitTest(FlashArraySpecialAgentUnitTest):
    def test_inventory(self):
        with self.special_agent() as agent:
            software_attributes = self.assert_inventory_attributes(
                agent.inventory().software,
                ["software", "os"]
            )
            self.assertEqual(
                software_attributes.inventory_attributes["Minimum Password Length"],
                self.admin_settings.admin_settings[0].min_password_length
            )
            self.assertEqual(
                software_attributes.inventory_attributes["Maximum Login Attempts"],
                self.admin_settings.admin_settings[0].max_login_attempts
            )
            self.assertEqual(
                software_attributes.inventory_attributes["Lockout Duration"],
                self.admin_settings.admin_settings[0].lockout_duration
            )
            self.assertEqual(
                software_attributes.inventory_attributes["SMTP Server"],
                ','.join(map(lambda srv: srv.relay_host, self.smtp_servers.smtp_servers))
            )


class FlashArraySystemSettingsIntegrationTest(FlashArraySpecialAgentIntegrationTest):
    def test_inventory(self):
        with self.special_agent() as agent, self.client() as cli:
            software_attributes = self.assert_inventory_attributes(
                agent.inventory().software,
                ["software", "os"]
            )
            admin_settings = list(cli.get_admins_settings().items)[0]
            try:
                min_password_length = admin_settings.min_password_length
            except AttributeError:
                min_password_length = None
            self.assertEqual(
                software_attributes.inventory_attributes["Minimum Password Length"],
                min_password_length
            )
            try:
                max_login_attempts = admin_settings.max_login_attempts
            except AttributeError:
                max_login_attempts = None
            self.assertEqual(
                software_attributes.inventory_attributes["Maximum Login Attempts"],
                max_login_attempts
            )
            try:
                lockout_duration = admin_settings.lockout_duration
            except AttributeError:
                lockout_duration = None
            self.assertEqual(
                software_attributes.inventory_attributes["Lockout Duration"],
                lockout_duration
            )
            smtp_servers = []
            for smtp_server in cli.get_smtp_servers().items:
                try:
                    if smtp_server.relay_host is not None:
                        smtp_servers.append(smtp_server.relay_host)
                except AttributeError:
                    pass
            self.assertEqual(
                software_attributes.inventory_attributes["SMTP Server"],
                ','.join(smtp_servers)
            )


class FlashArrayDNSUnitTest(FlashArraySpecialAgentUnitTest):
    def test_inventory(self):
        with self.special_agent() as agent:
            dns_attributes = self.assert_inventory_table_rows(
                agent.inventory().dns,
                ["software", "os", "DNS"]
            )
            self.assertEqual(
                dns_attributes[0].key_columns["name"],
                self.dns_servers.dns_servers[0].name
            )
            self.assertEqual(
                dns_attributes[0].inventory_columns["nameservers"],
                ','.join(self.dns_servers.dns_servers[0].nameservers)
            )


class FlashArrayDNSIntegrationTest(FlashArraySpecialAgentIntegrationTest):
    def test_inventory(self):
        with self.special_agent() as agent, self.client() as cli:
            dns_attributes = self.assert_inventory_table_rows(
                agent.inventory().dns,
                ["software", "os", "DNS"]
            )
            dns_servers = list(cli.get_dns().items)
            self.assertEqual(
                dns_attributes[0].key_columns["name"],
                dns_servers[0].name
            )
            self.assertEqual(
                dns_attributes[0].inventory_columns["nameservers"],
                ','.join(dns_servers[0].nameservers)
            )


class FlashArrayNTPUnitTest(FlashArraySpecialAgentUnitTest):
    def test_inventory(self):
        with self.special_agent() as agent:
            attributes = self.assert_inventory_attributes(agent.inventory().software, ["software", "os"])
            self.assertEqual(attributes.inventory_attributes["NTP Servers"],
                             ','.join(self.arrays.arrays[0].ntp_servers))


class FlashArrayNTPIntegrationTest(FlashArraySpecialAgentIntegrationTest):
    def test_inventory(self):
        with self.special_agent() as agent, self.client() as cli:
            attributes = self.assert_inventory_attributes(agent.inventory().software, ["software", "os"])
            self.assertEqual(
                attributes.inventory_attributes["NTP Servers"],
                ','.join(list(cli.get_arrays().items)[0].ntp_servers)
            )


class FlashArrayAPITokensUnitTest(FlashArraySpecialAgentUnitTest):
    def test_inventory(self):
        with self.special_agent() as agent:
            inventory = agent.inventory()
            api_token_rows = self.assert_inventory_table_rows(
                inventory.apitokens,
                ["software", "os", "API_tokens"]
            )
            for api_token in self.api_tokens.api_tokens:
                found = False
                for api_token_row in api_token_rows:
                    if api_token_row.key_columns["name"] == api_token.name:
                        found = True
                self.assertTrue(found, f"API token {api_token.name} not found in inventory")


class FlashArrayAPITokensIntegrationTest(FlashArraySpecialAgentIntegrationTest):
    def test_inventory(self):
        with self.special_agent() as agent, self.client() as cli:
            inventory = agent.inventory()
            api_token_rows = self.assert_inventory_table_rows(
                inventory.apitokens,
                ["software", "os", "API_tokens"]
            )

            for api_token in cli.get_admins_api_tokens().items:
                found = False
                for api_token_row in api_token_rows:
                    if api_token_row.key_columns["name"] == api_token.name:
                        found = True
                self.assertTrue(found, f"API token {api_token.name} not found in inventory")


class FlashArrayHostsUnitTest(FlashArraySpecialAgentUnitTest):
    def test_inventory(self):
        with self.special_agent() as agent:
            inventory = agent.inventory()
            array_connections_rows = self.assert_inventory_table_rows(
                inventory.hosts,
                ["hardware", "array", "connections"],
                len(self.hosts.hosts)
            )
            self.assertGreater(len(self.hosts.hosts), 0)
            for host in self.hosts.hosts:
                found = False
                for row in array_connections_rows:
                    if row.key_columns["name"] == host.name:
                        found = True
                        self.assertEqual(row.inventory_columns["connection_count"], host.connection_count)
                self.assertTrue(found, f"Host {host.name} not found in inventory.")


class FlashArrayHostsIntegrationTest(FlashArraySpecialAgentIntegrationTest):
    def test_inventory(self):
        with self.special_agent() as agent, self.client() as cli:
            inventory = agent.inventory()
            hosts = list(cli.get_hosts().items)
            array_connections_rows = self.assert_inventory_table_rows(
                inventory.hosts,
                ["hardware", "array", "connections"],
                len(hosts)
            )
            self.assertGreater(len(hosts), 0)
            for host in hosts:
                found = False
                for row in array_connections_rows:
                    if row.key_columns["name"] == host.name:
                        found = True
                        self.assertEqual(row.inventory_columns["connection_count"], host.connection_count)
                self.assertTrue(found, f"Host {host.name} not found in inventory.")


class FlashArrayLUNUnitTest(FlashArraySpecialAgentUnitTest):
    def test_inventory(self):
        with self.special_agent() as agent:
            inventory = agent.inventory()
            volume_rows = self.assert_inventory_table_rows(
                inventory.volumes,
                ["hardware", "array", "volumes"],
                len(self.volumes.volumes)
            )
            self.assertGreater(len(self.volumes.volumes), 0)
            for volume in self.volumes.volumes:
                found = False
                for row in volume_rows:
                    if row.key_columns["name"] == volume.name:
                        found = True
                        self.assertEqual(row.inventory_columns["connection_count"], volume.connection_count)
                self.assertTrue(found, f"LUN {volume.name} not found in inventory.")


class FlashArrayLUNIntegrationTest(FlashArraySpecialAgentIntegrationTest):
    def test_inventory(self):
        with self.special_agent() as agent, self.client() as cli:
            inventory = agent.inventory()
            volumes = list(cli.get_volumes().items)
            volume_rows = self.assert_inventory_table_rows(
                inventory.volumes,
                ["hardware", "array", "volumes"],
                len(volumes)
            )
            self.assertGreater(len(volumes), 0)
            for volume in volumes:
                found = False
                for row in volume_rows:
                    if row.key_columns["name"] == volume.name:
                        found = True
                        self.assertEqual(row.inventory_columns["connection_count"], volume.connection_count)
                self.assertTrue(found, f"LUN {volume.name} not found in inventory.")


class FlashArrayPortDetailsUnitTest(FlashArraySpecialAgentUnitTest):
    def test_inventory(self):
        with self.special_agent() as agent:
            services = agent.results().portdetails.services
            for metric in ["Port CT1.ETH10 temperature", "Port CT1.ETH10 voltage", "Port CT1.ETH10 tx_bias", "Port CT1.ETH10 tx_power"]:
                self.assertIn(metric, services)
                self.assertEqual(services[metric].state, State.OK)
            self.assertIn("Port CT1.ETH10 tx_fault (channel 1)", services)
            self.assertIn("Port CT1.ETH10 tx_fault (channel 2)", services)
            self.assertIn("Port CT1.ETH10 tx_fault (channel 3)", services)
            self.assertIn("Port CT1.ETH10 tx_fault (channel 4)", services)
            self.assertIn("Port CT1.ETH10 rx_los (channel 1)", services)
            self.assertIn("Port CT1.ETH10 rx_los (channel 2)", services)
            self.assertIn("Port CT1.ETH10 rx_los (channel 3)", services)
            self.assertIn("Port CT1.ETH10 rx_los (channel 4)", services)


class FlashArrayPortDetailsIntegrationTest(FlashArraySpecialAgentIntegrationTest):
    def test_inventory(self):
        with self.special_agent() as agent:
            self.assertGreater(len(agent.results().portdetails.services), 0)

if __name__ == "__main__":
    unittest.main()
