import abc
import logging
import tempfile
import time
from typing import TextIO, TypeVar, Generic, List, Optional

import pypureclient
from pypureclient.flashblade.FB_2_13 import models

from purestorage_checkmk.common import SpecialAgentResult, State, Result, Metric, CheckmkSection, CheckResponse, \
    NetworkAddressTableRow, NetworkInterfaceTableRow, SpecialAgentInventory, ChassisAttributes, PSUTableRow, \
    OtherHardwareComponentTableRow, FanTableRow, ManagementPortTableRow, NetworkRouteTableRow, ipv4_regex, \
    NetworkInterfaceStatus, HardwareModuleTableRow, DriveController, Compare, SupportAttributes, DNSAttributes, \
    SMTPAttributes, format_bytes, APIToken
from purestorage_checkmk.flashblade.common import FlashBladeSpecialAgentConfiguration, \
    FlashBladeSpecialAgentResultsSection, \
    flashblade_results_section_id, FlashBladeSpecialAgentInventorySection, flashblade_inventory_section_id, \
    FlashBladeSoftwareAttributes
from purestorage_checkmk.version import __version__

T = TypeVar("T")


class FlashBladeSpecialAgentDataSource(Generic[T], abc.ABC):
    @abc.abstractmethod
    def query(self) -> List[T]:
        pass


class CachingFlashBladeSpecialAgentDataSource(FlashBladeSpecialAgentDataSource[T]):
    _cache: Optional[List[T]] = None

    def __init__(self, backend: FlashBladeSpecialAgentDataSource[T]):
        self._backend = backend

    def query(self) -> List[T]:
        if self._cache is None:
            result = []
            for item in self._backend.query():
                result.append(item)
            self._cache = result
        return self._cache


class PyPureClientFlashBladeSpecialAgentDataSource(FlashBladeSpecialAgentDataSource[T], abc.ABC):

    def __init__(self, cli: pypureclient.flashblade.client.Client):
        self._cli = cli

    @abc.abstractmethod
    def _query(self, continuation_token: str):
        pass

    def query(self) -> List[T]:
        result = []
        finished = False
        continuation_token = None
        while not finished:
            resp = CheckResponse(self._query(continuation_token=continuation_token))
            if resp.continuation_token is None:
                finished = True
            else:
                continuation_token = resp.continuation_token
            for item in resp.items:
                result.append(item)
        return result


class PyPureClientFlashBladeHardwareDataSource(PyPureClientFlashBladeSpecialAgentDataSource[models.Hardware]):
    def _query(self, continuation_token):
        return self._cli.get_hardware(continuation_token=continuation_token)


class PyPureClientFlashBladeNetworkInterfacesDataSource(
    PyPureClientFlashBladeSpecialAgentDataSource[models.NetworkInterface]):
    def _query(self, continuation_token):
        return self._cli.get_network_interfaces(continuation_token=continuation_token)


class PyPureClientFlashBladeCertificatesDataSource(PyPureClientFlashBladeSpecialAgentDataSource[models.Certificate]):
    def _query(self, continuation_token):
        return self._cli.get_certificates(continuation_token=continuation_token)


class PyPureClientFlashBladeBladesDataSource(PyPureClientFlashBladeSpecialAgentDataSource[models.Blade]):
    def _query(self, continuation_token):
        return self._cli.get_blades(continuation_token=continuation_token)


class PyPureClientFlashBladeArraySpaceDataSource(PyPureClientFlashBladeSpecialAgentDataSource[models.ArraySpace]):
    def _query(self, continuation_token: str):
        return self._cli.get_arrays_space(type="array")


class PyPureClientFlashBladeFileSystemSpaceDataSource(PyPureClientFlashBladeSpecialAgentDataSource[models.ArraySpace]):
    def _query(self, continuation_token: str):
        return self._cli.get_arrays_space(type="file-system")


class PyPureClientFlashBladeObjectStorageSpaceDataSource(
    PyPureClientFlashBladeSpecialAgentDataSource[models.ArraySpace]):
    def _query(self, continuation_token: str):
        return self._cli.get_arrays_space(type="object-store")


class PyPureClientFlashBladeSupportDataSource(PyPureClientFlashBladeSpecialAgentDataSource[models.Support]):
    def _query(self, continuation_token):
        return self._cli.get_support()


class PyPureClientFlashBladeArrayDataSource(PyPureClientFlashBladeSpecialAgentDataSource[models.Array]):
    def _query(self, continuation_token):
        return self._cli.get_arrays()


class PyPureClientFlashBladeDNSDataSource(PyPureClientFlashBladeSpecialAgentDataSource[models.Dns]):
    def _query(self, continuation_token):
        return self._cli.get_dns()


class PyPureClientFlashBladeSMTPDataSource(PyPureClientFlashBladeSpecialAgentDataSource[models.SmtpServer]):
    def _query(self, continuation_token):
        return self._cli.get_smtp_servers()


class PyPureClientFlashBladeAPITokensDataSource(PyPureClientFlashBladeSpecialAgentDataSource[models.AdminApiToken]):
    def _query(self, continuation_token):
        return self._cli.get_admins_api_tokens()


class FlashBladeSpecialAgent:
    _cert_file = None

    def __init__(self, cfg: FlashBladeSpecialAgentConfiguration):
        self._cfg = cfg
        ssl_cert = None
        if cfg.verify_tls:
            self._cert_file = tempfile.NamedTemporaryFile()
            self._cert_file.write(cfg.cacert.encode('ascii'))
            self._cert_file.flush()
            ssl_cert = self._cert_file.name

        self._cli = pypureclient.flashblade.client.Client(
            cfg.host,
            api_token=cfg.api_token,
            ssl_cert=ssl_cert,
            user_agent=f"checkmk-purefa-{__version__}"

        )
        self._hardware = CachingFlashBladeSpecialAgentDataSource(
            PyPureClientFlashBladeHardwareDataSource(self._cli)
        )
        self._network_interfaces = CachingFlashBladeSpecialAgentDataSource(
            PyPureClientFlashBladeNetworkInterfacesDataSource(self._cli)
        )
        self._certificates = CachingFlashBladeSpecialAgentDataSource(
            PyPureClientFlashBladeCertificatesDataSource(self._cli)
        )
        self._blades = CachingFlashBladeSpecialAgentDataSource(
            PyPureClientFlashBladeBladesDataSource(self._cli)
        )
        self._array = CachingFlashBladeSpecialAgentDataSource(
            PyPureClientFlashBladeArrayDataSource(self._cli)
        )
        self._array_space = CachingFlashBladeSpecialAgentDataSource(
            PyPureClientFlashBladeArraySpaceDataSource(self._cli)
        )
        self._filesystem_space = CachingFlashBladeSpecialAgentDataSource(
            PyPureClientFlashBladeFileSystemSpaceDataSource(self._cli)
        )
        self._object_storage_space = CachingFlashBladeSpecialAgentDataSource(
            PyPureClientFlashBladeObjectStorageSpaceDataSource(self._cli)
        )
        self._support = CachingFlashBladeSpecialAgentDataSource(
            PyPureClientFlashBladeSupportDataSource(self._cli)
        )
        self._dns = CachingFlashBladeSpecialAgentDataSource(
            PyPureClientFlashBladeDNSDataSource(self._cli)
        )
        self._smtp = CachingFlashBladeSpecialAgentDataSource(
            PyPureClientFlashBladeSMTPDataSource(self._cli)
        )
        self._api_tokens = CachingFlashBladeSpecialAgentDataSource(
            PyPureClientFlashBladeAPITokensDataSource(self._cli)
        )

    def __del__(self):
        if self._cert_file is not None:
            self._cert_file.close()

    def results(self) -> FlashBladeSpecialAgentResultsSection:
        return FlashBladeSpecialAgentResultsSection(
            self._check_hardware(),
            self._collect_alerts(),
            self._collect_certificates(),
            self._collect_space(),
        )

    def inventory(self) -> FlashBladeSpecialAgentInventorySection:
        return FlashBladeSpecialAgentInventorySection(
            self._inventorize_hardware(),
            self._inventorize_interfaces(),
            self._inventorize_array(),
            self._inventorize_support(),
            self._inventorize_api_tokens(),
            self._inventorize_smtp(),
            self._inventorize_dns(),
        )

    def _inventorize_api_tokens(self):
        result = SpecialAgentInventory()
        for apitoken_item in self._api_tokens.query():
            if apitoken_item.admin is not None and apitoken_item.admin.name is not None:
                created_at = None
                expires_at = None
                if apitoken_item.api_token.created_at is not None:
                    created_at = apitoken_item.api_token.created_at / 1000
                if apitoken_item.api_token.expires_at is not None:
                    expires_at = apitoken_item.api_token.expires_at / 1000
                result.add_table_row(APIToken(
                    name=apitoken_item.admin.name,
                    created_at=created_at,
                    expires_at=expires_at
                ))
        return result

    def _inventorize_array(self):
        result = SpecialAgentInventory()
        arrays = self._array.query()
        if len(arrays) > 0:
            array = arrays[0]
            result.add_attributes(FlashBladeSoftwareAttributes(
                array_os=array.os,
                array_version=array.version,
                ntp_servers=','.join(array.ntp_servers),
            ))
        return result

    def _inventorize_smtp(self) -> SpecialAgentInventory:
        result = SpecialAgentInventory()
        smtp_server = self._smtp.query()
        for smtp_item in smtp_server:
            result.add_attributes(SMTPAttributes(
                name=smtp_item.name if smtp_item.name is not None else None,
                relay_host=smtp_item.relay_host if smtp_item.relay_host is not None else None,
                sender_domain=smtp_item.sender_domain if smtp_item.sender_domain is not None else None,
            ))
        return result

    def _inventorize_interfaces(self) -> SpecialAgentInventory:
        result = SpecialAgentInventory()
        for interface in self._network_interfaces.query():
            if interface.enabled:
                result.add_table_row(NetworkAddressTableRow(
                    interface.address,
                    interface.name,
                    interface.netmask
                ))
            speed = None
            result.add_table_row(NetworkInterfaceTableRow(
                description=interface.name,
                alias=interface.name,
                speed=speed,
                administrative_status=NetworkInterfaceStatus.UP if interface.enabled else NetworkInterfaceStatus.DORMANT,
                vlans=[interface.vlan],
                snmp_type=112 if interface.type == "vip" else None
            ))
            if interface.gateway is not None:
                result.add_table_row(NetworkRouteTableRow(
                    "0.0.0.0" if ipv4_regex.match(interface.gateway) else "::",
                    interface.gateway,
                    None,
                    interface.name,
                ))
        return result

    def _inventorize_support(self) -> SpecialAgentInventory:
        result = SpecialAgentInventory()
        for support_item in self._support.query():
            if support_item.name is not None:
                result.add_attributes(SupportAttributes(
                    name=support_item.name if not None else None,
                    id=support_item.id if not None else None,
                    phonehome_enabled=support_item.phonehome_enabled if not None else None,
                    remote_assist_active=support_item.remote_assist_active if not None else None,
                ))
        return result

    def _inventorize_dns(self) -> SpecialAgentInventory:
        result = SpecialAgentInventory()
        for dns_item in self._dns.query():
            if dns_item.name is not None:
                if dns_item.nameservers is not None:
                    nameservers = ",".join(dns_item.nameservers)
                else:
                    nameservers = None
                result.add_attributes(DNSAttributes(
                    name=dns_item.name,
                    domain=dns_item.domain if not None else None,
                    nameservers=nameservers
                ))
        return result

    def _inventorize_hardware(self) -> SpecialAgentInventory:
        result = SpecialAgentInventory()
        for hardware_item in self._hardware.query():
            if hardware_item.type == "ch":
                result.add_attributes(ChassisAttributes(
                    manufacturer="Pure Storage",
                    serial=hardware_item.serial,
                    model=hardware_item.model,
                ))
            elif hardware_item.type == "pwr":
                result.add_table_row(PSUTableRow(
                    index=hardware_item.slot,
                    description=hardware_item.name,
                    model=hardware_item.model,
                    serial=hardware_item.serial
                ))
            elif hardware_item.type == "fan":
                result.add_table_row(FanTableRow(
                    index=hardware_item.slot,
                    name=hardware_item.name,
                    model=hardware_item.model,
                    serial=hardware_item.serial,
                    type=hardware_item.type
                ))
            elif hardware_item.type == "mgmt_port":
                result.add_table_row(ManagementPortTableRow(
                    name=hardware_item.name,
                    model=hardware_item.model,
                    serial=hardware_item.serial,
                    type=hardware_item.type
                ))
            elif hardware_item.type == "eth":
                speed = None
                try:
                    if hardware_item.speed is not None:
                        speed = hardware_item.speed
                except AttributeError:
                    pass
                status = None
                if hardware_item.status != "unused":
                    if hardware_item.status == "healthy":
                        status = NetworkInterfaceStatus.UP
                    elif hardware_item.status in ["unhealthy", "critical"]:
                        status = NetworkInterfaceStatus.DOWN
                    else:
                        status = NetworkInterfaceStatus.UNKONWN
                result.add_table_row(NetworkInterfaceTableRow(
                    alias=hardware_item.name,
                    description=hardware_item.name,
                    administrative_status=NetworkInterfaceStatus.UP if hardware_item.status != "unused" else NetworkInterfaceStatus.DORMANT,
                    speed=speed,
                    operational_status=status,
                    mac=None,
                    vlans=None,
                    model=hardware_item.model,
                    serial=hardware_item.serial,
                    snmp_type=6 if hardware_item.type == "eth" else None
                ))
            elif hardware_item.type == "fb":
                if hardware_item.status != "unused":
                    blades = self._blades.query()
                    raw_capacity = None
                    for blade in blades:
                        if blade.name == hardware_item.name:
                            raw_capacity = blade.raw_capacity
                            break

                    result.add_table_row(HardwareModuleTableRow(
                        index=hardware_item.slot,
                        name=hardware_item.name,
                        serial=hardware_item.serial,
                        model=hardware_item.model,
                        type=hardware_item.type,
                        capacity=raw_capacity,
                    ))
            elif hardware_item.type == "fm":
                if hardware_item.status != "unused":
                    result.add_table_row(DriveController(
                        name=hardware_item.name,
                        serial=hardware_item.serial,
                        model=hardware_item.model,
                        type=hardware_item.type
                    ))
            else:
                if hardware_item.status != "unused":
                    result.add_table_row(OtherHardwareComponentTableRow(
                        name=hardware_item.name,
                        model=hardware_item.model,
                        serial=hardware_item.serial,
                        type=hardware_item.type
                    ))

        return result

    def _collect_certificates(self) -> SpecialAgentResult:
        result = SpecialAgentResult()
        for item in self._certificates.query():
            details = item.status
            now = time.time()
            valid_to = int(item.valid_to) / 1000
            ttl = ((valid_to - now) / 86400)
            result.add_metric_with_service(
                item.name + " certificate",
                Metric(
                    value=ttl,
                    levels=(self._cfg.certificates.warn, self._cfg.certificates.crit),
                ),
                details=details,
                summary=f"%.1f days left until expiration" % ttl,
                comparison=Compare.LTE,
            )
        return result

    def _collect_alerts(self) -> SpecialAgentResult:
        result = SpecialAgentResult()
        if self._cfg.alerts is None:
            return result
        finished = False
        continuation_token = None
        while not finished:
            resp = CheckResponse(self._cli.get_alerts(continuation_token=continuation_token))
            if resp.continuation_token is None:
                finished = True
            else:
                continuation_token = resp.continuation_token
            for item in resp.items:
                state = State.UNKNOWN
                create = False
                if item.state == "open" or item.state == "closing":
                    create = True
                    if item.severity == "info" or item.severity == "warning":
                        state = state.WARN
                    if item.severity == "critical":
                        state = state.CRIT
                elif item.state == "closed":
                    now = time.time()
                    age = (now - (item.updated / 1000))
                    if age < self._cfg.alerts.closed_alerts_lifetime:
                        create = True
                        state = state.OK
                if create and (
                        item.severity not in ["info", "warning", "critical"] or
                        (item.severity == "info" and self._cfg.alerts.info) or
                        (item.severity == "warning" and self._cfg.alerts.warning) or
                        (item.severity == "critical" and self._cfg.alerts.critical)
                ):
                    result.add_service(f"Alert {item.name}", Result(
                        state=state,
                        summary=item.summary,
                        details=item.description
                    ))
        return result

    def _collect_space(self) -> SpecialAgentResult:
        result = SpecialAgentResult()

        def add_service_space(
                name: str,
                query_space: List[models.ArraySpace],
                warn_threshold: int = 80,
                crit_threshold: int = 90
        ):
            if len(query_space) > 0 and query_space[0].capacity > 0:
                space = query_space[0]
                used_pct = int(100 * space.space.total_physical / space.capacity)
                result.add_metric_with_service(
                    name,
                    Metric(
                        value=used_pct,
                        levels=(warn_threshold, crit_threshold),
                        boundaries=(0, 100),
                    ),
                    summary=f"{used_pct}% used ({format_bytes(space.space.total_physical)} of {format_bytes(space.capacity)})"
                )
                for n, v in {
                    name + " total physical": space.space.total_physical,
                    name + " capacity": space.capacity,
                    name + " snapshots": space.space.snapshots,
                    name + " unique": space.space.unique,
                    name + " virtual": space.space.virtual,
                }.items():
                    result.add_metric_with_service(
                        n,
                        Metric(
                            value=v,
                        ),
                        summary=format_bytes(v)
                    )
                result.add_metric_with_service(
                    name + " parity",
                    Metric(
                        value=space.parity,
                    ),
                    summary=str(space.parity)
                )
                result.add_metric_with_service(
                    name + " data reduction",
                    Metric(
                        value=space.space.data_reduction,
                    ),
                    summary=str("%.1f to 1" % space.space.data_reduction)
                )

        add_service_space("Array space", self._array_space.query())
        add_service_space("Filesystem space", self._filesystem_space.query())
        add_service_space("Objectstore space", self._object_storage_space.query())
        return result

    def _check_hardware(self) -> SpecialAgentResult:
        customizations = {}
        for item in self._cfg.hardware:
            customizations[item.api_type] = item

        result = SpecialAgentResult()
        for item in self._hardware.query():
            if item.status == "healthy" or item.status == "identifying":
                state = State.OK
            elif item.status == "unhealthy":
                state = State.WARN
            elif item.status == "critical":
                state = State.CRIT
            elif item.status == "unused":
                continue
            else:
                state = State.UNKNOWN
            name = item.name
            if item.type in customizations:
                name = str(customizations[item.type].prefix) + str(name) + str(customizations[item.type].suffix)
            result.add_service(name, Result(
                state=state,
                summary=item.status,
                details=item.details
            ))
            try:
                if item.temperature is not None:
                    result.add_metric(f"{name}", Metric(
                        value=item.temperature,
                    ))
            except AttributeError:
                pass
            try:
                if item.speed is not None:
                    result.add_metric(f"{name}", Metric(
                        value=item.speed,
                    ))
            except AttributeError:
                pass
        return result


def run(stdin: TextIO, stdout: TextIO) -> int:
    """
    This function runs the special agent and produces the output data.
    :param stdin: The standard input to read the configuration from.
    :param stdout: The standard output to write the section to.
    :return: The return code.
    """
    stdin_data = stdin.read()
    cfg = FlashBladeSpecialAgentConfiguration.from_json(stdin_data)
    try:
        cli = FlashBladeSpecialAgent(cfg)
    except Exception as e:
        logging.fatal(f"Invalid FlashBlade configuration or FlashBlade not reachable at {cfg.host} ({e.__str__()}")
        return 1
    section = CheckmkSection(
        flashblade_results_section_id,
        cli.results()
    )
    stdout.write(str(section))
    section = CheckmkSection(
        flashblade_inventory_section_id,
        cli.inventory()
    )
    stdout.write(str(section))
    return 0
