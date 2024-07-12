import re
import typing

from purestorage_checkmk_test import httpmock
from purestorage_checkmk_test.flashblade.mock_alerts import AlertsContainer, _AlertsRoute
from purestorage_checkmk_test.flashblade.mock_apitokens import _APITokensRoute
from purestorage_checkmk_test.flashblade.mock_apitokens_container import APITokensContainer
from purestorage_checkmk_test.flashblade.mock_array import ArraysContainer, _ArraysRoute
from purestorage_checkmk_test.flashblade.mock_arrays_space import _ArraysSpaceRoute, ArraysSpaceContainer
from purestorage_checkmk_test.flashblade.mock_blades import BladesContainer, _BladesRoute
from purestorage_checkmk_test.flashblade.mock_certificates import CertificatesContainer, _CertificatesRoute
from purestorage_checkmk_test.flashblade.mock_dns import DNSServersContainer, _DNSServersRoute
from purestorage_checkmk_test.flashblade.mock_hardware import _HardwareRoute, HardwareContainer
from purestorage_checkmk_test.flashblade.mock_network import _NetworkInterfacesRoute, NetworkInterfaceContainer
from purestorage_checkmk_test.flashblade.mock_route import _AuthTokenStorage, _LoginRoute, _JSONRequest, _JSONResponse, \
    _JSONRoute
from purestorage_checkmk_test.flashblade.mock_smtp import _SMTPServersRoute, SMTPServersContainer
from purestorage_checkmk_test.flashblade.mock_support import SupportContainer, _SupportRoute
from purestorage_checkmk_test.httpmock import Response


class _VersionRoute(_JSONRoute):
    path = re.compile('^/api/api_version$')

    def handle_json(self, req: _JSONRequest) -> Response | _JSONResponse:
        return _JSONResponse(
            200,
            {},
            {
                "versions": [
                    "2.9"
                ]
            }
        )


class FlashBlade(httpmock.MockHTTPServer):
    """
    This class creates a new FlashBlade mock running on a random port that can be used for testing. The port can be
    queried using the port() method.
    """

    def __init__(
            self,
            api_tokens_container: APITokensContainer,
            blades_container: BladesContainer,
            hardware_container: HardwareContainer,
            certificates_container: CertificatesContainer,
            network_interfaces_container: NetworkInterfaceContainer,
            alerts_container: AlertsContainer,
            arrays_space_container: ArraysSpaceContainer,
            support_container: SupportContainer,
            arrays_container: ArraysContainer,
            dns_container: DNSServersContainer,
            smtp_container: SMTPServersContainer,
            cert_hostnames: typing.Set[str] = frozenset(["localhost"]),
            cert_ips: typing.Set[str] = frozenset(["127.0.0.1", "::1"])
    ):
        auth_token_storage = _AuthTokenStorage()
        super().__init__([
            _VersionRoute(),
            _LoginRoute(api_tokens_container, auth_token_storage),
            _BladesRoute(blades_container, auth_token_storage),
            _HardwareRoute(hardware_container, auth_token_storage),
            _CertificatesRoute(certificates_container, auth_token_storage),
            _NetworkInterfacesRoute(network_interfaces_container, auth_token_storage),
            _AlertsRoute(alerts_container, auth_token_storage),
            _ArraysSpaceRoute(arrays_space_container, auth_token_storage),
            _SupportRoute(support_container, auth_token_storage),
            _ArraysRoute(arrays_container, auth_token_storage),
            _DNSServersRoute(dns_container, auth_token_storage),
            _SMTPServersRoute(smtp_container, auth_token_storage),
            _APITokensRoute(api_tokens_container, auth_token_storage)
        ], cert_hostnames, cert_ips)


if __name__ == "__main__":
    blades = BladesContainer()
    blades.add(10)
    hardware = HardwareContainer(blades)
    certificates = CertificatesContainer()
    network_interfaces = NetworkInterfaceContainer()
    arrays_space_container = ArraysSpaceContainer()
    alerts_container = AlertsContainer()
    support_container = SupportContainer()
    arrays_container = ArraysContainer()
    dns_container = DNSServersContainer()
    smtp_container = SMTPServersContainer()
    fb = FlashBlade(
        api_tokens_container=APITokensContainer({"asdf"}),
        blades_container=blades,
        hardware_container=hardware,
        certificates_container=certificates,
        network_interfaces_container=network_interfaces,
        arrays_space_container=arrays_space_container,
        alerts_container=alerts_container,
        support_container=support_container,
        arrays_container=arrays_container,
        dns_container=dns_container,
        smtp_container=smtp_container,
        cert_hostnames={"localhost"},
        cert_ips={"192.168.199.1"}
    )
    fb.start()
    print(f"Running on port {fb.port()}")
    while True:
        pass
