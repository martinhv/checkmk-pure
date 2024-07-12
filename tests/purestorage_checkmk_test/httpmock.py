import abc
import dataclasses
import http.server
import ipaddress
import logging
import re
import ssl
import tempfile
import threading
import time
import typing
import unittest
from datetime import datetime, timedelta
from socketserver import ThreadingMixIn
from typing import Dict, List

import requests
from cryptography import x509
from cryptography.hazmat._oid import NameOID
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa

PORT = 8000


@dataclasses.dataclass
class Request:
    method: str
    path: str
    headers: Dict[str, List[str]]
    body: bytes

    def query(self) -> Dict[str, List[str]]:
        query_string = {}
        parts = self.path.split('?', 1)
        if len(parts) == 1:
            return query_string
        for component in parts[1].split("&"):
            component_parts = component.split("=", 1)
            if len(component_parts) == 2:
                if component_parts[0] not in query_string:
                    query_string[component_parts[0]] = []
                query_string[component_parts[0]].append(component_parts[1])
        return query_string

    def query_to_dataclass(self, target: typing.Any):
        qs = self.query()
        fields = dataclasses.fields(target)
        for field in fields:
            try:
                value = qs[field.name]
                if field.type == str:
                    value = str(value[0])
                elif field.type == int:
                    value = int(value[0])
                elif field.type == float:
                    value = float(value[0])
                elif field.type == list:
                    value = value
                else:
                    value = str(value[0])
                setattr(target, field.name, value)
            except KeyError:
                pass


@dataclasses.dataclass
class Response:
    status: int = 200
    headers: Dict[str, List[str]] = dataclasses.field(default_factory=dict)
    body: bytes = ''


class Route(abc.ABC):
    path: re.Pattern

    @abc.abstractmethod
    def handle(self, req: Request) -> Response:
        pass


def _create_handler(routes: List[Route]) -> typing.Type[http.server.BaseHTTPRequestHandler]:
    class RouteHandler(http.server.BaseHTTPRequestHandler):
        def route(self) -> None:
            headers = {}
            for header in self.headers.keys():
                headers[header] = self.headers.get_all(header)
            # noinspection PyBroadException
            try:
                content_length = int(headers['Content-Length'][0])
            except Exception:
                content_length = 0
            body = self.rfile.read(content_length)
            req = Request(
                self.command,
                self.path,
                headers,
                body,
            )
            for route in routes:
                if route.path.match(self.path.split('?')[0]):
                    # noinspection PyBroadException
                    try:
                        resp = route.handle(req)
                        self.send_response_only(resp.status)
                        for header, values in resp.headers.items():
                            for value in values:
                                self.send_header(header, value)
                        self.end_headers()
                        self.wfile.write(resp.body)
                    except Exception as e:
                        logging.error(e)
                        self.send_response_only(500)
                        self.end_headers()
                    return
            logging.warning(f"URL not found: {self.path}")
            self.send_response_only(404)
            self.end_headers()

        def do_GET(self):
            self.route()

        def do_POST(self):
            self.route()

        def do_PUT(self):
            self.route()

        def do_HEAD(self):
            self.route()

    return RouteHandler


class _HTTPServerThread(threading.Thread):
    def __init__(self, server: http.server.HTTPServer):
        super().__init__()
        self._server = server

    def run(self) -> None:
        self._server.serve_forever()


def _generate_self_signed_certificate(
        hostnames: typing.Set[str] = frozenset(["localhost"]),
        ips: typing.Set[str] = frozenset(["127.0.0.1"]),
) -> typing.Tuple[bytes, bytes]:
    key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )
    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.COUNTRY_NAME, u"US"),
        x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, u"California"),
        x509.NameAttribute(NameOID.LOCALITY_NAME, u"Mountain View"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, u"Pure Storage"),
        x509.NameAttribute(NameOID.COMMON_NAME, list(hostnames)[0]),
    ])
    sans = []
    for hostname in hostnames:
        sans.append(x509.DNSName(hostname))
    for ip in ips:
        if ":" in ip:
            sans.append(x509.IPAddress(ipaddress.IPv6Address(ip)))
        else:
            sans.append(x509.IPAddress(ipaddress.IPv4Address(ip)))

    cert = x509.CertificateBuilder().subject_name(
        subject
    ).issuer_name(
        issuer
    ).public_key(
        key.public_key()
    ).serial_number(
        x509.random_serial_number()
    ).not_valid_before(
        datetime.utcnow()
    ).not_valid_after(
        datetime.utcnow() + timedelta(days=365)
    ).add_extension(
        x509.SubjectAlternativeName(sans),
        critical=False,
    ).sign(key, hashes.SHA256())
    return key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    ), cert.public_bytes(serialization.Encoding.PEM)


class _ThreadingSimpleServer(ThreadingMixIn, http.server.HTTPServer):
    pass


class MockHTTPServer:
    _running = False

    def __init__(
            self,
            routes: List[Route],
            cert_hostnames: typing.Set[str] = frozenset(["localhost"]),
            cert_ips: typing.Set[str] = frozenset(["127.0.0.1"])
    ):

        class HealthzHandler(Route):
            path = re.compile("^/.well-known/healthz$")

            def handle(self, req: Request) -> Response:
                return Response(
                    200,
                    {},
                    "OK".encode('ascii')
                )

        new_routes: List[Route] = [HealthzHandler()]
        self._server = _ThreadingSimpleServer(("", 0), _create_handler(new_routes + routes[:]))
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        key, cert = _generate_self_signed_certificate(cert_hostnames, cert_ips)
        self._cert = cert
        with tempfile.NamedTemporaryFile() as cert_file:
            with tempfile.NamedTemporaryFile() as key_file:
                cert_file.write(cert)
                cert_file.flush()
                key_file.write(key)
                key_file.flush()
                ctx.load_cert_chain(cert_file.name, key_file.name)
        self._plain_socket = self._server.socket
        self._server.socket = ctx.wrap_socket(self._plain_socket, server_side=True)
        self._thread = _HTTPServerThread(self._server)

    def port(self) -> int:
        sock_name = self._server.socket.getsockname()
        return sock_name[1]

    @staticmethod
    def cert_hostname() -> str:
        return "localhost"

    def cert(self) -> bytes:
        """
        This function returns the PEM-encoded certificate for this server.
        """
        return self._cert

    def start(self):
        logging.debug("Starting mock HTTP server...")
        if self._running:
            return
        self._running = True
        self._thread.daemon = True
        self._thread.start()
        for i in range(1, 30):
            if self.healthcheck():
                logging.debug("Mock HTTP server is up.")
                return
            logging.debug("Mock HTTP server not yet up...")
            time.sleep(1)
        raise Exception("HTTP server failed to come up")

    def healthcheck(self) -> bool:
        # noinspection PyBroadException
        try:
            with tempfile.NamedTemporaryFile() as cert_file:
                cert_file.write(self._cert)
                cert_file.flush()
                port = self.port()
                response = requests.get(f"https://localhost:{port}/.well-known/healthz", verify=cert_file.name)
                if response.status_code == 200:
                    logging.debug("Health check successful.")
                    return True
                logging.debug(f"Health check failed (invalid status code {response.status_code})")
            return False
        except Exception as e:
            logging.debug(f"Health check failed ({str(e)})")
            return False

    def stop(self):
        if not self._running:
            return
        self._server.shutdown()
        self._server.socket.close()
        self._plain_socket.close()
        self._thread.join()
        self._running = False


class MockHTTPServerTest(unittest.TestCase):
    @staticmethod
    def test_http_server():
        class TestRoute(Route):
            path = re.compile('^/test/$')

            def handle(self, req: Request) -> Response:
                if req.body.decode('ascii') != "world":
                    return Response(
                        400,
                    )

                @dataclasses.dataclass
                class TestQuery:
                    foo: typing.Optional[str] = None

                query = TestQuery()
                req.query_to_dataclass(query)
                if query.foo != "bar":
                    return Response(400)
                return Response(
                    200,
                    {
                        "X-Hello": ["world"]
                    },
                    "Hello world!".encode('ascii')
                )

        mock = MockHTTPServer([TestRoute()])
        mock.start()
        try:
            with tempfile.NamedTemporaryFile() as cert_file:
                cert_file.write(mock.cert())
                cert_file.flush()
                try:
                    response = requests.post(
                        f"https://localhost:{mock.port()}/test/?foo=bar", "world",
                        verify=cert_file.name
                    )
                    if response.status_code != 200:
                        raise AssertionError(f"Invalid status code returned: {response.status_code}")
                except OSError as e:
                    raise AssertionError(f"Failed to query test endpoint: {str(e)}") from e

                try:
                    if response.headers["X-Hello"] != "world":
                        raise AssertionError(f"Invalid X-Hello header returned: {response.headers['X-Hello'][0]}")
                except KeyError as e:
                    raise AssertionError(f"No X-Hello header returned.")
                if response.text != "Hello world!":
                    raise AssertionError(f"Invalid body returned: {response.text}")

                try:
                    response = requests.post(
                        f"https://localhost:{mock.port()}/",
                        "world",
                        verify=cert_file.name,
                    )
                    if response.status_code != 404:
                        raise AssertionError(f"Invalid status code returned: {response.status_code}")
                except OSError as e:
                    raise AssertionError(f"Failed to query 404 endpoint: {str(e)}") from e
        finally:
            mock.stop()


if __name__ == "__main__":
    unittest.main()
