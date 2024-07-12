import abc
import logging
import os
import time
import typing
import unittest
import uuid

import pypureclient
from pypureclient.flashblade.FB_2_9 import models

import purestorage_checkmk_test.flashblade.mock_blades
from purestorage_checkmk.common import State, LimitConfiguration
from purestorage_checkmk.flashblade.common import FlashBladeSpecialAgentConfiguration, AlertsConfiguration, \
    default_closed_alerts_lifetime, default_array_space_warn, default_array_space_crit, default_cert_warn, \
    default_cert_crit
from purestorage_checkmk.flashblade.special_agent import FlashBladeSpecialAgent
from purestorage_checkmk_test.common import SpecialAgentTestCase
from purestorage_checkmk_test.flashblade import mock
from purestorage_checkmk_test.flashblade.mock_alerts import AlertsContainer
from purestorage_checkmk_test.flashblade.mock_apitokens_container import APITokensContainer
from purestorage_checkmk_test.flashblade.mock_array import ArraysContainer
from purestorage_checkmk_test.flashblade.mock_arrays_space import ArraysSpaceContainer
from purestorage_checkmk_test.flashblade.mock_certificates import CertificatesContainer
from purestorage_checkmk_test.flashblade.mock_dns import DNSServersContainer
from purestorage_checkmk_test.flashblade.mock_hardware import HardwareContainer
from purestorage_checkmk_test.flashblade.mock_network import NetworkInterfaceContainer
from purestorage_checkmk_test.flashblade.mock_smtp import SMTPServersContainer
from purestorage_checkmk_test.flashblade.mock_support import SupportContainer


class FlashBladeSpecialAgentContext:
    _cfg: FlashBladeSpecialAgentConfiguration
    _sa: typing.Optional[FlashBladeSpecialAgent]

    def __init__(self, cfg: FlashBladeSpecialAgentConfiguration):
        self._cfg = cfg
        self._sa = None

    def __enter__(self) -> FlashBladeSpecialAgent:
        self._sa = FlashBladeSpecialAgent(self._cfg)
        return self._sa

    def __exit__(self, *args):
        del self._sa


class FlashBladeClientContext:
    def __init__(self, hostname, api_token, cert_file):
        self._hostname = hostname
        self._api_token = api_token
        self._cert_file = cert_file

    def __enter__(self) -> pypureclient.flashblade.client.Client:
        self._cli = pypureclient.flashblade.client.Client(
            self._hostname,
            api_token=self._api_token,
            ssl_cert=self._cert_file
        )
        return self._cli

    def __exit__(self, *args):
        del self._cli


class FlashBladeSpecialAgentTest(SpecialAgentTestCase, abc.ABC):
    @abc.abstractmethod
    def special_agent(
            self,
            cfg: typing.Optional[FlashBladeSpecialAgentConfiguration] = None
    ) -> FlashBladeSpecialAgentContext:
        pass


class FlashBladeSpecialAgentIntegrationTest(FlashBladeSpecialAgentTest, abc.ABC):

    def client(self) -> FlashBladeClientContext:
        return FlashBladeClientContext(self.hostname, self.api_token, self.cert_file)

    def setUp(self):
        hostname = os.getenv("LIVE_FB_HOSTNAME")
        api_token = os.getenv("LIVE_FB_APITOKEN")
        cert_file = os.getenv("LIVE_FB_CERT_FILE")

        if hostname is None or hostname == "" or api_token is None or api_token == "":
            self.skipTest("No live credentials present.")

        if cert_file is not None:
            try:
                with open(cert_file) as f:
                    cert = f.read()
            except Exception as e:
                self.fail(f"Failed to load certificate file {cert_file} due to {type(e).__name__}: {str(e)}")
        else:
            cert = None

        # noinspection PyBroadException
        try:
            pypureclient.flashblade.client.Client(
                hostname,
                api_token=api_token,
                ssl_cert=cert_file
            )

            self.hostname = hostname
            self.api_token = api_token
            self.cert_file = cert_file
            self.cert = cert
        except Exception as e:
            self.fail(f"Live connection failed due to {type(e).__name__}: {str(e)}")

    def special_agent(
            self,
            cfg: typing.Optional[FlashBladeSpecialAgentConfiguration] = None
    ) -> FlashBladeSpecialAgentContext:
        if cfg is None:
            cfg = FlashBladeSpecialAgentConfiguration(
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
        return FlashBladeSpecialAgentContext(cfg)


class FlashBladeSpecialAgentUnitTest(FlashBladeSpecialAgentTest, abc.ABC):

    def assert_hardware_service_state(self, agent, item_type, state: State):
        hardware_items = self.hardware.basic_items_by_type(item_type)
        hardware_services = agent.results().hardware.services
        self.assert_named_item_service_state(hardware_items, hardware_services, state)

    def setUp(self) -> None:
        self.api_token = str(uuid.uuid4())
        self.blades = purestorage_checkmk_test.flashblade.mock_blades.BladesContainer()
        self.hardware = HardwareContainer(self.blades)
        self.certificates = CertificatesContainer()
        self.alerts = AlertsContainer()
        self.network_interfaces = NetworkInterfaceContainer()
        self.arrays_space = ArraysSpaceContainer()
        self.arrays = ArraysContainer()
        self.support = SupportContainer()
        self.dns = DNSServersContainer()
        self.smtp = SMTPServersContainer()
        self.api_tokens = APITokensContainer({self.api_token})
        self.mock_server = mock.FlashBlade(
            api_tokens_container=self.api_tokens,
            blades_container=self.blades,
            hardware_container=self.hardware,
            certificates_container=self.certificates,
            alerts_container=self.alerts,
            network_interfaces_container=self.network_interfaces,
            arrays_space_container=self.arrays_space,
            support_container=self.support,
            arrays_container=self.arrays,
            dns_container=self.dns,
            smtp_container=self.smtp,
        )
        self.mock_server.start()

    def tearDown(self) -> None:
        self.mock_server.stop()

    def special_agent(
            self,
            cfg: typing.Optional[FlashBladeSpecialAgentConfiguration] = None
    ) -> FlashBladeSpecialAgentContext:
        if cfg is None:
            cfg = FlashBladeSpecialAgentConfiguration(
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
        return FlashBladeSpecialAgentContext(cfg)


class FlashBladeSpecialAgentLoginUnitTest(FlashBladeSpecialAgentUnitTest):
    def test_login(self):
        """
        Basic login test

        This function tests the FlashBlade mock itself to make sure the basic login works with pypureclient. This
        ensures that all subsequent tests don't fail due to basic incompatibilities.
        """
        cli = pypureclient.flashblade.client.Client(
            f"localhost:{self.mock_server.port()}",
            api_token=self.api_token,
            ssl_cert=self.mock_server.cert()
        )
        self.assertIsNotNone(cli)
        logging.info("Successful login against the PureStorage FlashBlade mock.")


class FlashBladeBladesUnitTest(FlashBladeSpecialAgentUnitTest):
    def test_services(self):
        """
        Blade status unittest
        """

        with self.special_agent() as agent:
            hardware_services = agent.results().hardware.services
            blades = list(filter(lambda blade: blade.status != "unused", self.blades.blades))
            self.assertEqual(0, len(blades))
            self.assertEqual(0, len(list(filter(lambda name: "FB" in name, hardware_services))))

        with self.special_agent() as agent:
            hardware_services = agent.results().hardware.services
            self.assert_named_item_service_state(
                list(filter(lambda hw: hw.type == "fm", self.hardware.base_hardware_items)),
                hardware_services,
                State.OK
            )

        with self.special_agent() as agent:
            self.blades.add(1)
            hardware_services = agent.results().hardware.services
            blades = list(filter(lambda blade: blade.status != "unused", self.blades.blades))
            self.assert_named_item_service_state(blades, hardware_services, State.OK)
            self.assertEqual(1, len(list(filter(lambda name: "FB" in name, hardware_services))))

        with self.special_agent() as agent:
            self.blades.blades[0].status = "unhealthy"
            hardware_services = agent.results().hardware.services
            blades = list(filter(lambda blade: blade.status != "unused", self.blades.blades))
            self.assert_named_item_service_state(blades, hardware_services, State.WARN)
            self.assertEqual(1, len(list(filter(lambda name: "FB" in name, hardware_services))))

    def test_inventory(self):
        with self.special_agent() as agent:
            modules = self.assert_inventory_table_rows(
                agent.inventory().hardware,
                ["hardware", "components", "modules"]
            )
            non_empty_blades = list(filter(
                lambda module: module.inventory_columns["serial"] is not None,
                modules
            ))
            self.assertEqual(
                len(non_empty_blades),
                len(list(filter(
                    lambda drive: drive.status != "unused",
                    self.blades.blades
                )))
            )

        with self.special_agent() as agent:
            self.blades.add(1)
            modules = self.assert_inventory_table_rows(
                agent.inventory().hardware,
                ["hardware", "components", "modules"]
            )
            non_empty_blades = list(filter(
                lambda module: module.inventory_columns["serial"] is not None,
                modules
            ))
            self.assertEqual(
                len(non_empty_blades),
                len(list(filter(
                    lambda drive: drive.status != "unused",
                    self.blades.blades
                )))
            )


class FlashBladeBladesIntegrationTest(FlashBladeSpecialAgentIntegrationTest):
    def test_services(self):
        with self.special_agent() as agent:
            blade_services = agent.results().hardware.services
            found_fm = False
            for name, service in blade_services.items():
                if name == "CH1.FM1":
                    found_fm = True
            self.assertTrue(found_fm)

    def test_inventory(self):
        with self.special_agent() as agent:
            blade_rows = self.assert_inventory_table_rows(
                agent.inventory().hardware,
                ["hardware", "components", "modules"]
            )
            found_fb = False
            for blade_row in blade_rows:
                if blade_row.inventory_columns.get("type") == "fb":
                    found_fb = True
            self.assertTrue(found_fb, "No FB found in inventory")


class FlashBladeControllersUnitTest(FlashBladeBladesUnitTest):
    def test_services(self):
        """
        Controller status unittest
        """
        with self.special_agent() as agent:
            controller_services = agent.results().hardware.services
            controllers = list(filter(lambda hw: hw.type == "ch", self.hardware.base_hardware_items))
            self.assert_named_item_service_state(controllers, controller_services, State.OK)

        with self.special_agent() as agent:
            controllers = list(filter(lambda hw: hw.type == "ch", self.hardware.base_hardware_items))
            for controller in controllers:
                controller.status = "unhealthy"
            controller_services = agent.results().hardware.services
            controllers = list(filter(lambda hw: hw.type == "ch", self.hardware.base_hardware_items))
            self.assert_named_item_service_state(controllers, controller_services, State.WARN)

    def test_inventory(self):
        """
        Controller inventory test
        """
        with self.special_agent() as agent:
            attributes = self.assert_inventory_attributes(agent.inventory().hardware, ["hardware", "chassis"])
            chassis = list(filter(lambda hw: hw.type == "ch", self.hardware.base_hardware_items))
            self.assertEqual(attributes.inventory_attributes["serial"], chassis[0].serial)
            self.assertEqual(attributes.inventory_attributes["model"], chassis[0].model)


class FlashBladeControllersIntegrationTest(FlashBladeSpecialAgentIntegrationTest):
    def test_services(self):
        with self.special_agent() as agent, self.client() as cli:
            controllers = list(filter(lambda hw: hw.type == "ch", cli.get_hardware().items))
            controller_services = agent.results().hardware.services
            self.assert_named_item_service_state(controllers, controller_services)

    def test_inventory(self):
        with self.special_agent() as agent, self.client() as cli:
            controller_attributes = self.assert_inventory_attributes(
                agent.inventory().hardware,
                ["hardware", "chassis"]
            )
            controllers = list(filter(lambda hw: hw.type == "ch", cli.get_hardware().items))
            controller = controllers[0]
            self.assertEqual(controller.model, controller_attributes.inventory_attributes["model"])


class FlashBladeNetworkInterfaceUnitTest(FlashBladeBladesUnitTest):
    def test_hardware_services(self):
        with self.special_agent() as agent:
            services = agent.results().hardware.services
            eth_hardware = list(filter(lambda hardware: hardware.type == "eth" and hardware.status != "unused",
                                       self.hardware.base_hardware_items))
            self.assert_named_item_service_state(eth_hardware, services, State.OK)
        with self.special_agent() as agent:
            for i in range(0, len(self.hardware.base_hardware_items)):
                if self.hardware.base_hardware_items[i].type == "eth" and self.hardware.base_hardware_items[
                    i].status != "unused":
                    self.hardware.base_hardware_items[i].status = "unhealthy"

            eth_hardware = list(filter(lambda hardware: hardware.type == "eth" and hardware.status != "unused",
                                       self.hardware.base_hardware_items))
            services = agent.results().hardware.services
            self.assert_named_item_service_state(eth_hardware, services, State.WARN)

    def test_hardware_inventory(self):
        """
        Inventory test for physical interfaces
        """
        with self.special_agent() as agent:
            network_interfaces = agent.inventory().hardware
            self.assert_inventory_table_rows(
                network_interfaces,
                ["networking", "interfaces"],
                len(list(filter(lambda hardware: hardware.type == "eth", self.hardware.base_hardware_items)))
            )

    def test_vip_inventory(self):
        """
        Inventory test for VIPs
        """
        with self.special_agent() as agent:
            network_interfaces = agent.inventory().network_interfaces
            self.assert_inventory_table_rows(
                network_interfaces,
                ["networking", "interfaces"],
                len(self.network_interfaces.network_interfaces)
            )
            self.assert_inventory_table_rows(
                network_interfaces,
                ["networking", "addresses"],
                len(self.network_interfaces.network_interfaces)
            )


class FlashBladeNetworkInterfaceIntegrationTest(FlashBladeSpecialAgentIntegrationTest):
    def test_services(self):
        with self.special_agent() as agent, self.client() as cli:
            network_interfaces = list(
                filter(lambda hw: hw.type == "eth" and hw.status != "unused", cli.get_hardware().items))
            services = agent.results().hardware.services
            self.assert_named_item_service_state(network_interfaces, services)

    def test_hardware_inventory(self):
        with self.special_agent() as agent, self.client() as cli:
            network_interfaces = list(filter(lambda hw: hw.type == "eth", cli.get_hardware().items))
            hardware_inventory = agent.inventory().hardware
            rows = self.assert_inventory_table_rows(
                hardware_inventory,
                ["networking", "interfaces"],
            )
            self.assertEqual(len(network_interfaces), len(rows))

    def test_vip_inventory(self):
        with self.special_agent() as agent, self.client() as cli:
            network_interfaces = agent.inventory().network_interfaces
            self.assert_inventory_table_rows(
                network_interfaces,
                ["networking", "interfaces"],
                len(list(cli.get_network_interfaces().items))
            )
            self.assert_inventory_table_rows(
                network_interfaces,
                ["networking", "addresses"],
                len(list(cli.get_network_interfaces().items))
            )


class FlashBladeFanUnitTest(FlashBladeSpecialAgentUnitTest):
    def test_services(self):
        with self.special_agent() as agent:
            hardware_services = agent.results().hardware.services
            fans = list(filter(lambda hw: hw.type == "fan", self.hardware.base_hardware_items))
            self.assert_named_item_service_state(fans, hardware_services, State.OK)

        for fan in fans:
            fan.status = "unhealthy"

        with self.special_agent() as agent:
            hardware_services = agent.results().hardware.services
            fans = list(filter(lambda hw: hw.type == "fan", self.hardware.base_hardware_items))
            self.assert_named_item_service_state(fans, hardware_services, State.WARN)

    def test_inventory(self):
        with self.special_agent() as agent:
            hardware_inventory = agent.inventory().hardware
            fans = list(filter(lambda hw: hw.type == "fan", self.hardware.base_hardware_items))
            self.assert_inventory_table_rows(hardware_inventory, ["hardware", "components", "fans"], len(fans))


class FlashBladeFanIntegrationTest(FlashBladeSpecialAgentIntegrationTest):
    def test_services(self):
        with self.special_agent() as agent, self.client() as cli:
            hardware_services = agent.results().hardware.services
            fans = list(filter(lambda hw: hw.type == "fan", cli.get_hardware().items))
            self.assert_named_item_service_state(fans, hardware_services)

    def test_inventory(self):
        with self.special_agent() as agent, self.client() as cli:
            hardware_inventory = agent.inventory().hardware
            fans = list(filter(lambda hw: hw.type == "fan", cli.get_hardware().items))
            self.assert_inventory_table_rows(hardware_inventory, ["hardware", "components", "fans"], len(fans))


class FlashBladeAlertUnitTest(FlashBladeSpecialAgentUnitTest):
    def test_services(self):
        cfg = FlashBladeSpecialAgentConfiguration(
            alerts=AlertsConfiguration(
                closed_alerts_lifetime=default_closed_alerts_lifetime,
                info=True,
                warning=True,
                critical=True,
            )
        )

        with self.special_agent(cfg) as agent:
            self.assertEqual(len(agent.results().alerts.services), 0)

        self.alerts.alerts.append(purestorage_checkmk_test.flashblade.mock_alerts.Alert(
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


class FlashBladeAlertIntegrationTest(FlashBladeSpecialAgentIntegrationTest):
    def test_services(self):
        cfg = FlashBladeSpecialAgentConfiguration(
            alerts=AlertsConfiguration(
                closed_alerts_lifetime=default_closed_alerts_lifetime,
                info=True,
                warning=True,
                critical=True,
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


class FlashBladeCapacityUnitTest(FlashBladeSpecialAgentUnitTest):
    def test_service(self):
        cfg = FlashBladeSpecialAgentConfiguration(
            array_space=LimitConfiguration(
                warn=default_array_space_warn,
                crit=default_array_space_crit
            ),
        )

        warn = cfg.array_space.warn
        crit = cfg.array_space.crit
        for item in [
            (self.arrays_space.blade, "Array space", "Blade"),
            (self.arrays_space.filesystem, "Filesystem space", "Filesystem"),
            (self.arrays_space.objectstore, "Objectstore space", "Objectstore")
        ]:
            with self.subTest(item[2]):
                with self.special_agent(cfg) as agent:
                    item[0].capacity = 10000
                    item[0].space.total_physical = int(item[0].capacity * warn / 100 - 1)
                    array_services = agent.results().space.services
                    svc = array_services.get(item[1])
                    self.assertEqual(svc.state, State.OK)

                with self.special_agent(cfg) as agent:
                    item[0].capacity = 10000
                    item[0].space.total_physical = int(item[0].capacity * warn / 100)
                    array_services = agent.results().space.services
                    svc = array_services.get(item[1])
                    self.assertEqual(svc.state, State.WARN)

                with self.special_agent(cfg) as agent:
                    item[0].capacity = 10000
                    item[0].space.total_physical = int(item[0].capacity * crit / 100)
                    array_services = agent.results().space.services

                    svc = array_services.get(item[1])
                    self.assertEqual(svc.state, State.CRIT)


class FlashBladeCapacityIntegrationTest(FlashBladeSpecialAgentIntegrationTest):
    def test_service(self):
        for item in [
            ("array", "array_space"),
            ("filesystem", "filesystem_space"),
            ("objecstore", "objectstore_space")
        ]:
            with self.subTest(item[0]):
                with self.special_agent() as agent, self.client() as cli:
                    space_services = agent.results().space.services
                    svc = space_services.get(item[1])
                    self.assertIsNotNone(svc)


class FlashBladeCertificateUnitTest(FlashBladeSpecialAgentUnitTest):
    def _check_certificate_services(self, cfg, state):
        with self.special_agent(cfg) as agent:
            certificate_services = agent.results().certificates.services
            self.assertEqual(len(certificate_services), len(self.certificates.certificates))
            self.assert_named_item_service_state(self.certificates.certificates, certificate_services, state)

    def test_service(self):
        cfg = FlashBladeSpecialAgentConfiguration(
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


class FlashBladeCertificateIntegrationTest(FlashBladeSpecialAgentIntegrationTest):
    def test_service(self):
        cfg = FlashBladeSpecialAgentConfiguration(
            certificates=LimitConfiguration(
                default_cert_warn,
                default_cert_crit,
            )
        )
        with self.special_agent(cfg) as agent, self.client() as cli:
            certificates: typing.List[models.Certificate] = cli.get_certificates().items
            certificate_services = agent.results().certificates.services
            for certificate in certificates:
                days_remaining = int((int(certificate.valid_to) / 1000 - int(time.time())) / 86400)
                expected_state = State.OK
                if days_remaining < cfg.certificates.crit:
                    expected_state = State.CRIT
                elif days_remaining < cfg.certificates.warn:
                    expected_state = State.WARN
                self.assert_named_item_service_state(certificates, certificate_services, expected_state)


class FlashBladeOSUnitTest(FlashBladeSpecialAgentUnitTest):
    def test_inventory(self):
        with self.special_agent() as agent:
            software_attributes = self.assert_inventory_attributes(
                agent.inventory().array,
                ["software", "os"]
            )
            self.assertEqual(software_attributes.inventory_attributes["name"], self.arrays.arrays[0].os)
            self.assertEqual(software_attributes.inventory_attributes["version"], self.arrays.arrays[0].version)


class FlashBladeOSIntegrationTest(FlashBladeSpecialAgentIntegrationTest):
    def test_inventory(self):
        with self.special_agent() as agent, self.client() as cli:
            software_attributes = self.assert_inventory_attributes(
                agent.inventory().array,
                ["software", "os"]
            )
            arrays = list(cli.get_arrays().items)
            self.assertEqual(software_attributes.inventory_attributes["name"], arrays[0].os)
            self.assertEqual(software_attributes.inventory_attributes["version"], arrays[0].version)


class FlashBladePowerUnitTest(FlashBladeSpecialAgentUnitTest):
    def test_services(self):
        with self.special_agent() as agent:
            self.assert_hardware_service_state(agent, "pwr", State.OK)

        with self.special_agent() as agent:
            for power_supply in self.hardware.basic_items_by_type("pwr"):
                power_supply.status = "unhealthy"
            self.assert_hardware_service_state(agent, "pwr", State.WARN)

    def test_inventory(self):
        with self.special_agent() as agent:
            power_supplies = self.hardware.basic_items_by_type("pwr")
            hardware_inventory = agent.inventory().hardware
            self.assert_inventory_table_rows(
                hardware_inventory,
                ["hardware", "components", "psus"],
                len(power_supplies)
            )


class FlashBladePowerIntegrationTest(FlashBladeSpecialAgentIntegrationTest):
    def test_services(self):
        with self.special_agent() as agent, self.client() as cli:
            hardware_services = agent.results().hardware.services
            power_supplies = list(filter(lambda hw: hw.type == "pwr", cli.get_hardware().items))
            self.assert_named_item_service_state(power_supplies, hardware_services)

    def test_inventory(self):
        with self.special_agent() as agent, self.client() as cli:
            power_supplies = list(filter(lambda hw: hw.type == "pwr", cli.get_hardware().items))
            hardware_inventory = agent.inventory().hardware
            self.assert_inventory_table_rows(
                hardware_inventory,
                ["hardware", "components", "psus"],
                len(power_supplies)
            )


class FlashBladeChassisUnitTest(FlashBladeSpecialAgentUnitTest):

    def test_services(self):
        with self.special_agent() as agent:
            hardware_services = agent.results().hardware
            chassis = [self.hardware.base_hardware_items[0]]
            self.assert_named_item_service_state(chassis, hardware_services.services, State.OK)

        self.hardware.base_hardware_items[0].status = "unhealthy"
        with self.special_agent() as agent:
            hardware_services = agent.results().hardware
            chassis = [self.hardware.base_hardware_items[0]]
            self.assert_named_item_service_state(chassis, hardware_services.services, State.WARN)

    def test_inventory(self):
        with self.special_agent() as agent:
            chassis = self.hardware.base_hardware_items[0]
            hardware_inventory = agent.inventory().hardware
            chassis_attributes = self.assert_inventory_attributes(
                hardware_inventory,
                ["hardware", "chassis"]
            )
            self.assertEqual(chassis_attributes.inventory_attributes["model"], chassis.model)
            self.assertEqual(chassis_attributes.inventory_attributes["serial"], chassis.serial)


class FlashBladeChassisIntegrationTest(FlashBladeSpecialAgentIntegrationTest):

    def test_services(self):
        with self.special_agent() as agent, self.client() as cli:
            hardware_services = agent.results().hardware
            chassis = list(filter(lambda hw: hw.type == "ch", cli.get_hardware().items))
            self.assert_named_item_service_state(chassis, hardware_services.services)

    def test_inventory(self):
        with self.special_agent() as agent, self.client() as cli:
            chassis = list(filter(lambda hw: hw.type == "ch", cli.get_hardware().items))[0]
            hardware_inventory = agent.inventory().hardware
            chassis_attributes = self.assert_inventory_attributes(
                hardware_inventory,
                ["hardware", "chassis"]
            )
            self.assertEqual(chassis_attributes.inventory_attributes["model"], chassis.model)
            self.assertEqual(chassis_attributes.inventory_attributes["serial"], chassis.serial)


class FlashBladePhoneHomeUnitTest(FlashBladeSpecialAgentUnitTest):
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


class FlashBladePhoneHomeIntegrationTest(FlashBladeSpecialAgentIntegrationTest):
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


class FlashBladeDNSUnitTest(FlashBladeSpecialAgentUnitTest):
    def test_inventory(self):
        with self.special_agent() as agent:
            dns_inventory = agent.inventory().dns
            dns_attributes = self.assert_inventory_attributes(
                dns_inventory,
                ["software", "os", "DNS"]
            )
            self.assertEqual(
                dns_attributes.inventory_attributes["domain"],
                self.dns.dns_servers[0].domain
            )
            self.assertEqual(
                dns_attributes.inventory_attributes["nameservers"],
                ','.join(self.dns.dns_servers[0].nameservers)
            )


class FlashBladeDNSIntegrationTest(FlashBladeSpecialAgentIntegrationTest):
    def test_inventory(self):
        with self.special_agent() as agent, self.client() as cli:
            dns_attributes = self.assert_inventory_attributes(
                agent.inventory().dns,
                ["software", "os", "DNS"]
            )
            dns_servers = list(cli.get_dns().items)[0]
            self.assertEqual(
                dns_attributes.inventory_attributes["name"],
                dns_servers.name
            )
            self.assertEqual(
                dns_attributes.inventory_attributes["nameservers"],
                ','.join(dns_servers.nameservers)
            )


class FlashBladeNTPUnitTest(FlashBladeSpecialAgentUnitTest):
    def test_inventory(self):
        with self.special_agent() as agent:
            attributes = self.assert_inventory_attributes(agent.inventory().array, ["software", "os"])
            self.assertEqual(
                attributes.inventory_attributes["NTP Servers"],
                ','.join(self.arrays.arrays[0].ntp_servers)
            )


class FlashBladeNTPIntegrationTest(FlashBladeSpecialAgentIntegrationTest):
    def test_inventory(self):
        with self.special_agent() as agent, self.client() as cli:
            attributes = self.assert_inventory_attributes(agent.inventory().array, ["software", "os"])
            self.assertEqual(
                attributes.inventory_attributes["NTP Servers"],
                ','.join(list(cli.get_arrays().items)[0].ntp_servers)
            )


class FlashBladeAPITokensUnitTest(FlashBladeSpecialAgentUnitTest):
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
                    if api_token_row.key_columns["name"] == api_token.admin.name:
                        found = True
                self.assertTrue(found, f"API token {api_token.admin.name} not found in inventory")


class FlashBladeAPITokensIntegrationTest(FlashBladeSpecialAgentIntegrationTest):
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
                    if api_token_row.key_columns["name"] == api_token.admin.name:
                        found = True
                self.assertTrue(found, f"API token {api_token.admin.name} not found in inventory")


class FlashBladeSystemSettingsUnitTest(FlashBladeSpecialAgentUnitTest):
    def test_inventory(self):
        with self.special_agent() as agent:
            smtp_attributes = self.assert_inventory_attributes(
                agent.inventory().smtp,
                ["software", "smtp"]
            )
            self.assertEqual(
                smtp_attributes.inventory_attributes["Relay Host"],
                ','.join(map(lambda srv: srv.relay_host, self.smtp.smtp_servers))
            )


class FlashBladeSystemSettingsIntegrationTest(FlashBladeSpecialAgentIntegrationTest):
    def test_inventory(self):
        with self.special_agent() as agent, self.client() as cli:
            software_attributes = self.assert_inventory_attributes(
                agent.inventory().smtp,
                ["software", "smtp"]
            )
            smtp_servers = None
            for smtp_server in cli.get_smtp_servers().items:
                try:
                    if smtp_server.relay_host is not None:
                        if smtp_servers is None:
                            smtp_servers = []
                        smtp_servers.append(smtp_server.relay_host)
                except AttributeError:
                    pass
            self.assertEqual(
                software_attributes.inventory_attributes["Relay Host"],
                ','.join(smtp_servers) if smtp_servers is not None else None
            )


if __name__ == "__main__":
    unittest.main()
