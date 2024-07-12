import re
import typing

from purestorage_checkmk_test import httpmock
from purestorage_checkmk_test.flasharray.mock_admin_settings import _AdminSettingsRoute, AdminSettingsContainer
from purestorage_checkmk_test.flasharray.mock_alerts import AlertsContainer, _AlertsRoute
from purestorage_checkmk_test.flasharray.mock_apitokens import _APITokensRoute
from purestorage_checkmk_test.flasharray.mock_apitokens_container import APITokensContainer
from purestorage_checkmk_test.flasharray.mock_array import ArraysContainer, _ArraysRoute
from purestorage_checkmk_test.flasharray.mock_array_connection import ArrayConnectionContainer, _ArrayConnectionRoute
from purestorage_checkmk_test.flasharray.mock_certificates import CertificatesContainer, _CertificatesRoute
from purestorage_checkmk_test.flasharray.mock_controllers import ControllersContainer, _ControllersRoute
from purestorage_checkmk_test.flasharray.mock_dns import DNSServersContainer, _DNSServersRoute
from purestorage_checkmk_test.flasharray.mock_drives import DrivesContainer, \
    _DrivesRoute
from purestorage_checkmk_test.flasharray.mock_hardware import HardwaresContainer, _HardwaresRoute
from purestorage_checkmk_test.flasharray.mock_hosts import HostsContainer, _HostsRoute
from purestorage_checkmk_test.flasharray.mock_network_interfaces import _NetworkInterfaceRoute, \
    NetworkInterfaceContainer
from purestorage_checkmk_test.flasharray.mock_port_details import PortContainer, _PortDetailsRoute
from purestorage_checkmk_test.flasharray.mock_route import _AuthTokenStorage, _LoginRoute, _JSONRequest, _JSONResponse, \
    _JSONRoute
from purestorage_checkmk_test.flasharray.mock_smtp import _SMTPServersRoute, SMTPServersContainer
from purestorage_checkmk_test.flasharray.mock_support import SupportContainer, _SupportRoute
from purestorage_checkmk_test.flasharray.mock_volumes import VolumesContainer, _VolumesRoute
from purestorage_checkmk_test.httpmock import Response


class _VersionRoute(_JSONRoute):
    path = re.compile('^/api/api_version$')

    def handle_json(self, req: _JSONRequest) -> Response | _JSONResponse:
        return _JSONResponse(
            200,
            {},
            {
                "version": [
                    "2.21"
                ]
            }
        )


class FlashArray(httpmock.MockHTTPServer):
    """
    This class creates a new FlashArray mock running on a random port that can be used for testing. The port can be
    queried using the port() method.
    """

    def __init__(
            self,
            api_tokens_container: APITokensContainer,
            drives_container: DrivesContainer,
            controllers_container: ControllersContainer,
            hardwares_container: HardwaresContainer,
            arrays_container: ArraysContainer,
            alerts_container: AlertsContainer,
            certificates_container: CertificatesContainer,
            admin_settings_container: AdminSettingsContainer,
            smtp_servers_container: SMTPServersContainer,
            dns_servers_container: DNSServersContainer,
            array_connections_container: ArrayConnectionContainer,
            network_interfaces_container: NetworkInterfaceContainer,
            hosts_container: HostsContainer,
            volumes_container: VolumesContainer,
            support_container: SupportContainer,
            port_container: PortContainer,
            cert_hostnames: typing.Set[str] = frozenset(["localhost"]),
            cert_ips: typing.Set[str] = frozenset(["127.0.0.1", "::1"]),
    ):
        auth_token_storage = _AuthTokenStorage()
        super().__init__([
            _VersionRoute(),
            _LoginRoute(api_tokens_container, auth_token_storage),
            _APITokensRoute(api_tokens_container, auth_token_storage),
            _DrivesRoute(drives_container, auth_token_storage),
            _ControllersRoute(controllers_container, auth_token_storage),
            _HardwaresRoute(hardwares_container, auth_token_storage),
            _ArraysRoute(arrays_container, auth_token_storage),
            _AlertsRoute(alerts_container, auth_token_storage),
            _CertificatesRoute(certificates_container, auth_token_storage),
            _AdminSettingsRoute(admin_settings_container, auth_token_storage),
            _SMTPServersRoute(smtp_servers_container, auth_token_storage),
            _DNSServersRoute(dns_servers_container, auth_token_storage),
            _ArrayConnectionRoute(array_connections_container, auth_token_storage),
            _NetworkInterfaceRoute(network_interfaces_container, auth_token_storage),
            _HostsRoute(hosts_container, auth_token_storage),
            _VolumesRoute(volumes_container, auth_token_storage),
            _SupportRoute(support_container, auth_token_storage),
            _PortDetailsRoute(port_container, auth_token_storage),
        ],
            cert_hostnames,
            cert_ips,
        )


if __name__ == "__main__":
    drives = DrivesContainer()
    drives.add(10)
    controllers = ControllersContainer()
    controllers.add()
    ports = PortContainer(controllers)
    hardwares = HardwaresContainer(drives, controllers, ports)
    arrays = ArraysContainer()
    alerts = AlertsContainer()
    certificates = CertificatesContainer()
    admin_settings = AdminSettingsContainer()
    smtp_servers = SMTPServersContainer()
    dns_servers = DNSServersContainer()
    array_connection = ArrayConnectionContainer()
    network_interfaces = NetworkInterfaceContainer()
    hosts = HostsContainer()
    volumes = VolumesContainer()
    support = SupportContainer()
    fb = FlashArray(
        api_tokens_container=APITokensContainer({"asdf"}),
        drives_container=drives,
        controllers_container=controllers,
        hardwares_container=hardwares,
        arrays_container=arrays,
        alerts_container=alerts,
        certificates_container=certificates,
        admin_settings_container=admin_settings,
        smtp_servers_container=smtp_servers,
        dns_servers_container=dns_servers,
        array_connections_container=array_connection,
        network_interfaces_container=network_interfaces,
        hosts_container=hosts,
        volumes_container=volumes,
        support_container=support,
        port_container=ports,
        cert_hostnames={"localhost"},
        cert_ips={"192.168.199.1"}
    )
    fb.start()
    print(f"Running on port {fb.port()}")
    while True:
        pass
