import abc
import logging
import tempfile
import time
from typing import TextIO, TypeVar, Generic, List, Optional

import pypureclient
from purestorage_checkmk.common import CheckmkSection, Result, State, CheckResponse, SpecialAgentResult, Metric, \
    Compare, SpecialAgentInventory, DriveController, OtherHardwareComponentTableRow, FanTableRow, ChassisTableRow, \
    PSUTableRow, SensorTableRow, BackplaneTableRow, NetworkInterfaceStatus, NetworkInterfaceTableRow, APIToken, \
    NetworkAddressTableRow, ipv4_regex, NetworkRouteTableRow, format_bytes
from purestorage_checkmk.flasharray.common import FlashArraySpecialAgentConfiguration, \
    FlashArraySpecialAgentResultsSection, \
    flasharray_results_section_id, flasharray_inventory_section_id, FlashArraySpecialAgentInventorySection, DNSServer, \
    FlashArraySoftwareAttributes, ArrayConnection, Hosts, Volumes, SupportAttributes, NIC
from purestorage_checkmk.version import __version__
from pypureclient.flasharray.FA_2_32 import models

T = TypeVar("T")


class FlashArraySpecialAgentDataSource(Generic[T], abc.ABC):
    @abc.abstractmethod
    def query(self) -> List[T]:
        pass


class CachingFlashArraySpecialAgentDataSource(FlashArraySpecialAgentDataSource[T]):
    _cache: Optional[List[T]] = None

    def __init__(self, backend: FlashArraySpecialAgentDataSource[T]):
        self._backend = backend

    def query(self) -> List[T]:
        if self._cache is None:
            result = []
            for item in self._backend.query():
                result.append(item)
            self._cache = result
        return self._cache


class PyPureClientFlashArraySpecialAgentDataSource(FlashArraySpecialAgentDataSource[T], abc.ABC):
    def __init__(self, cli: pypureclient.flasharray.client.Client):
        self._cli = cli


class PyPureClientFlashArraySpecialAgentPaginatedDataSource(PyPureClientFlashArraySpecialAgentDataSource[T]):
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


class PyPureClientFlashArrayHardwareDataSource(PyPureClientFlashArraySpecialAgentDataSource[models.Hardware]):
    def query(self) -> List[models.Hardware]:
        return CheckResponse(self._cli.get_hardware()).items

class PyPureClientFlashArrayPortDetailsDataSource(PyPureClientFlashArraySpecialAgentDataSource[models.NetworkInterfacesPortDetails]):
    def query(self) -> List[models.NetworkInterfacesPortDetails]:
        return CheckResponse(self._cli.get_network_interfaces_port_details()).items

class PyPureClientFlashArrayArraysDataSource(PyPureClientFlashArraySpecialAgentDataSource[models.Array]):
    def query(self) -> List[models.Array]:
        return CheckResponse(self._cli.get_arrays()).items


class PyPureClientFlashArrayCertificatesDataSource(PyPureClientFlashArraySpecialAgentDataSource[models.Certificate]):
    def query(self) -> List[models.Certificate]:
        return CheckResponse(self._cli.get_certificates()).items


class PyPureClientFlashArrayDrivesDataSource(PyPureClientFlashArraySpecialAgentPaginatedDataSource[models.Hardware]):
    def _query(self, continuation_token):
        return self._cli.get_drives(continuation_token=continuation_token)


class PyPureClientFlashArrayAdminSettingsDataSource(PyPureClientFlashArraySpecialAgentDataSource[models.AdminSettings]):
    def query(self) -> List[models.AdminSettings]:
        return CheckResponse(self._cli.get_admins_settings()).items


class PyPureClientFlashArrayArraysSettingsDataSource(PyPureClientFlashArraySpecialAgentDataSource[models.Array]):
    def query(self) -> List[models.Arrays]:
        return CheckResponse(self._cli.get_arrays()).items


class PyPureClientFlashArrayDNSSettingsDataSource(PyPureClientFlashArraySpecialAgentDataSource[models.Dns]):
    def query(self) -> List[models.Dns]:
        return CheckResponse(self._cli.get_dns()).items


class PyPureClientFlashArrayPerformanceDataSource(
    PyPureClientFlashArraySpecialAgentDataSource[models.array_performance]):
    def query(self) -> List[models.ArrayPerformance]:
        return CheckResponse(self._cli.get_arrays_performance()).items


class PyPureClientFlashArrayApiTokenDataSource(PyPureClientFlashArraySpecialAgentDataSource[models.AdminApiToken]):
    def query(self) -> List[models.AdminApiToken]:
        return CheckResponse(self._cli.get_admins_api_tokens()).items


class PyPureClientFlashArraySNMPServersDataSource(PyPureClientFlashArraySpecialAgentDataSource[models.SmtpServer]):
    def query(self) -> List[models.SmtpServer]:
        return CheckResponse(self._cli.get_smtp_servers()).items


class PyPureClientFlashArrayArrayConnectionDataSource(
    PyPureClientFlashArraySpecialAgentDataSource[models.ArrayConnection]):
    def query(self) -> List[models.ArrayConnection]:
        return CheckResponse(self._cli.get_array_connections()).items


class PyPureClientFlashArrayNetworkInterfacesDataSource(
    PyPureClientFlashArraySpecialAgentDataSource[models.NetworkInterface]):
    def query(self) -> List[models.NetworkInterface]:
        return CheckResponse(self._cli.get_network_interfaces()).items


class PyPureClientFlashArrayHostsDataSource(
    PyPureClientFlashArraySpecialAgentDataSource[models.Host]):
    def query(self) -> List[models.Host]:
        return CheckResponse(self._cli.get_hosts()).items


class PyPureClientFlashArrayVolumesDataSource(
    PyPureClientFlashArraySpecialAgentDataSource[models.Volume]):
    def query(self) -> List[models.Volume]:
        return CheckResponse(self._cli.get_volumes()).items


class PyPureClientFlashArraySupportDataSource(
    PyPureClientFlashArraySpecialAgentDataSource[models.Support]):
    def query(self) -> List[models.Support]:
        return CheckResponse(self._cli.get_support()).items


class PyPureClientFlashArrayControllerDataSource(
    PyPureClientFlashArraySpecialAgentDataSource[models.Controller]):
    def query(self) -> List[models.Controller]:
        return CheckResponse(self._cli.get_controllers()).items


class PyPureClientFlashArrayNICDataSource(
    PyPureClientFlashArraySpecialAgentDataSource[models.NetworkInterface]):
    def query(self) -> List[models.NetworkInterface]:
        return CheckResponse(self._cli.get_network_interfaces()).items


def _safe(object: any, attribute: str):
    try:
        return getattr(object, attribute)
    except AttributeError:
        return None


class FlashArraySpecialAgent:
    _cert_file = None

    def __init__(self, cfg: FlashArraySpecialAgentConfiguration):
        self._cfg = cfg
        ssl_cert = None
        agent = f'checkmk-purefa-'
        if cfg.verify_tls:
            self._cert_file = tempfile.NamedTemporaryFile()
            self._cert_file.write(cfg.cacert.encode('ascii'))
            self._cert_file.flush()
            ssl_cert = self._cert_file.name

        self._cli = pypureclient.flasharray.client.Client(
            cfg.host,
            api_token=cfg.api_token,
            ssl_cert=ssl_cert,
            user_agent=f"checkmk-purefa-{__version__}"
        )
        self._hardware = CachingFlashArraySpecialAgentDataSource(
            PyPureClientFlashArrayHardwareDataSource(self._cli)
        )
        self._drives = CachingFlashArraySpecialAgentDataSource(
            PyPureClientFlashArrayDrivesDataSource(self._cli)
        )
        self._arrays = CachingFlashArraySpecialAgentDataSource(
            PyPureClientFlashArrayArraysDataSource(self._cli)
        )
        self._certificates = CachingFlashArraySpecialAgentDataSource(
            PyPureClientFlashArrayCertificatesDataSource(self._cli)
        )
        self._adminsettings = CachingFlashArraySpecialAgentDataSource(
            PyPureClientFlashArrayAdminSettingsDataSource(self._cli)
        )
        self._arraysettings = CachingFlashArraySpecialAgentDataSource(
            PyPureClientFlashArrayArraysSettingsDataSource(self._cli)
        )
        self._dnssettings = CachingFlashArraySpecialAgentDataSource(
            PyPureClientFlashArrayDNSSettingsDataSource(self._cli)
        )
        self._performance = CachingFlashArraySpecialAgentDataSource(
            PyPureClientFlashArrayPerformanceDataSource(self._cli)
        )
        self._apitokens = CachingFlashArraySpecialAgentDataSource(
            PyPureClientFlashArrayApiTokenDataSource(self._cli)
        )
        self._smtpservers = CachingFlashArraySpecialAgentDataSource(
            PyPureClientFlashArraySNMPServersDataSource(self._cli)
        )
        self._arrayconnections = CachingFlashArraySpecialAgentDataSource(
            PyPureClientFlashArrayArrayConnectionDataSource(self._cli)
        )
        self._networkinterfaces = CachingFlashArraySpecialAgentDataSource(
            PyPureClientFlashArrayNetworkInterfacesDataSource(self._cli)
        )
        self._port_details = CachingFlashArraySpecialAgentDataSource(
            PyPureClientFlashArrayPortDetailsDataSource(self._cli)
        )
        self._hosts = CachingFlashArraySpecialAgentDataSource(
            PyPureClientFlashArrayHostsDataSource(self._cli)
        )
        self._volumes = CachingFlashArraySpecialAgentDataSource(
            PyPureClientFlashArrayVolumesDataSource(self._cli)
        )
        self._support = CachingFlashArraySpecialAgentDataSource(
            PyPureClientFlashArraySupportDataSource(self._cli)
        )
        self._controllers = CachingFlashArraySpecialAgentDataSource(
            PyPureClientFlashArrayControllerDataSource(self._cli)
        )
        self._nics = CachingFlashArraySpecialAgentDataSource(
            PyPureClientFlashArrayNICDataSource(self._cli)
        )

    def __del__(self):
        if self._cert_file is not None:
            self._cert_file.close()

    def results(self) -> FlashArraySpecialAgentResultsSection:
        return FlashArraySpecialAgentResultsSection(
            hardware=self._collect_hardware_components(),
            certificates=self._collect_certificates(),
            drives=self._collect_drives(),
            array=self._collect_array(),
            alerts=self._collect_alerts(),
            arrayconnections=self._collect_arrayconnections(),
            portdetails=self._collect_portdetails(),
        )

    def inventory(self) -> FlashArraySpecialAgentInventorySection:
        return FlashArraySpecialAgentInventorySection(
            hardware=self._inventorize_hardware(),
            software=self._inventorize_software(),
            dns=self._inventorize_dns(),
            apitokens=self._inventorize_apitokens(),
            network_interfaces=self._inventorize_network_interfaces(),
            hosts=self._inventorize_hosts(),
            volumes=self._inventorize_volumes(),
            support=self._inventorize_support(),
            nics=self._inventorize_nics(),
        )

    def _collect_portdetails(self) -> SpecialAgentResult:
        result = SpecialAgentResult()

        port_details = self._port_details.query()
        for port in port_details:
            for metric in ["temperature", "voltage", "tx_bias", "tx_power", "rx_power"]:
                for val in getattr(port, metric):
                    if hasattr(val, "channel") and val.channel is None:
                        name = f"Port {port.name} {metric} (channel {val.channel})"
                    else:
                        name = f"Port {port.name} {metric}"
                    state = State.UNKNOWN
                    if val.status in ["ok", "healthy","empty"]:
                        state = State.OK
                    elif val.status in [
                        "unhealthy", "identifying", "recovering", "unadmitted", "unrecognized", "updating", "warn low",
                        "warn high"
                    ]:
                        state = State.WARN,
                    elif val.status in ["failed", "missing", "alarm low", "alarm high"]:
                        state = State.CRIT
                    elif val.status in ["unused"]:
                        continue

                    result.add_service(name, Result(
                        state = state,
                        summary = str(val.measurement)
                    ))
                    result.add_metric(name, Metric(
                        value=val.measurement,
                        # We can't represent both an upper and a lower bound in checkmk, so we won't be showing that.
                    ))
            for flag in ["tx_fault", "rx_los"]:
                for val in getattr(port, flag):
                    if hasattr(val, "channel") and val.channel is not None:
                        name = f"Port {port.name} {flag} (channel {val.channel})"
                    else:
                        name = f"Port {port.name} {flag}"
                    if not val.flag:
                        state = State.OK
                        summary = "Not flagged"
                    else:
                        state = State.CRIT
                        summary = "Flagged"

                    result.add_service(name, Result(
                        state=state,
                        summary=summary
                    ))
        return result

    def _collect_drives(self) -> SpecialAgentResult:
        result = SpecialAgentResult()
        finished = False
        continuation_token = None
        while not finished:
            resp = CheckResponse(self._cli.get_drives(continuation_token=continuation_token))
            if resp.continuation_token is None:
                finished = True
            else:
                continuation_token = resp.continuation_token
            for item in resp.items:
                state = State.UNKNOWN
                if item.status in ["healthy", "empty"]:
                    state = State.OK
                elif item.status in [
                    "unhealthy", "identifying", "recovering", "unadmitted", "unrecognized", "updating"
                ]:
                    state = State.WARN
                elif item.status in ["failed", "missing"]:
                    state = State.CRIT
                elif item.status in ["unused"]:
                    continue
                result.add_service(item.name, Result(
                    state=state,
                    summary=item.status,
                    # details=item.details # API lies, it is not returning details
                ))
        return result

    def _collect_arrayconnections(self) -> SpecialAgentResult:
        result = SpecialAgentResult()
        finished = False
        continuation_token = None
        while not finished:
            resp = CheckResponse(self._cli.get_array_connections(continuation_token=continuation_token))
            if resp.continuation_token is None:
                finished = True
            else:
                continuation_token = resp.continuation_token
            for item in resp.items:
                state = State.UNKNOWN
                if item.status == "connected":
                    state = State.OK
                if item.status == "connecting" or item.status == "partially_connected" or item.status == "unbalanced":
                    state = State.WARN
                result.add_service(item.name, Result(
                    state=state,
                    summary=item.status,
                    details=None
                ))
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
                    if item.severity == "info" or item.severity == "warning" or item.severity == "hidden":
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
                        item.severity not in ["info", "warning", "critical", "hidden"] or
                        (item.severity == "info" and self._cfg.alerts.info) or
                        (item.severity == "warning" and self._cfg.alerts.warning) or
                        (item.severity == "critical" and self._cfg.alerts.critical) or
                        (item.severity == "hidden" and self._cfg.alerts.hidden)
                ):
                    result.add_service(f"Alert {item.name}", Result(
                        state=state,
                        summary=item.summary,
                        details=item.description
                    ))
        return result

    def _collect_performance(self) -> SpecialAgentResult:
        pass

    def _collect_hardware_components(self) -> SpecialAgentResult:
        customizations = {}
        for item in self._cfg.hardware:
            customizations[item.api_type] = item

        result = SpecialAgentResult()
        for item in self._hardware.query():
            state = State.UNKNOWN
            if item.status == "ok" or item.status == "healthy":
                state = State.OK
            elif item.status == "unknown" or item.status == "unhealthy":
                state = State.WARN
            elif item.status == "critical":
                state = State.CRIT
            elif item.status == "unused" or item.status == "not_installed":
                continue
            if item.type == "controller":
                for controller in self._controllers.query():
                    if controller.name == item.name:
                        item.status = controller.status
                        item.details = controller.mode
            name = item.name
            if item.type in customizations:
                name = str(customizations[item.type].prefix) + str(name) + str(customizations[item.type].suffix)
            try:
                result.add_service(name, Result(
                    state=state,
                    summary=item.status,
                    details=item.details
                ))
            except AttributeError:
                result.add_service(name, Result(
                    state=state,
                    summary=item.status,
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

    def _inventorize_nics(self) -> SpecialAgentInventory:
        result = SpecialAgentInventory()
        for nic_item in self._nics.query():
            name = self._resolve_attr(nic_item, ["name"])
            speed = self._resolve_attr(nic_item, ["speed"])
            interface_type = self._resolve_attr(nic_item, ["interface_type"])
            if name is not None:
                result.add_table_row(NIC(
                    name=str(nic_item.name),
                    speed=nic_item.speed,
                    interface_type=nic_item.interface_type
                ))
            # services=nic_item.services
            # differentiate between type eth and type fc
            if nic_item.interface_type == "eth":
                eth = nic_item.eth
                address = self._resolve_attr(eth, ["address"])
                netmask = self._resolve_attr(eth, ["netmask"])
                gateway = self._resolve_attr(eth, ["gateway"])
                mac_address = self._resolve_attr(eth, ["mac_address"])
                subtype = self._resolve_attr(eth, ["subtype"])
                subinterfaces = self._resolve_attr(eth, ["subinterfaces"])
                if subinterfaces is not None:
                    if isinstance(subinterfaces, list):
                        res = []
                        for subinterface in subinterfaces:
                            res.append(subinterface.name)
                        subinterfaces = ', '.join(res)
                vlan = self._resolve_attr(eth, ["vlan"])
                mtu = self._resolve_attr(eth, ["mtu"])
                result.add_table_row(NIC(
                    name=name,
                    speed=speed,
                    interface_type=interface_type,
                    address=address,
                    gateway=gateway,
                    mac_address=mac_address,
                    subtype=subtype,
                    subinterfaces=subinterfaces,
                    vlan=vlan,
                    mtu=mtu,
                ))
            if nic_item.interface_type == "fc":
                fc = nic_item.fc
                wwn = self._resolve_attr(nic_item, ["wwn"])
                result.add_table_row(NIC(
                    name=name,
                    speed=speed,
                    interface_type=interface_type,
                    wwn=wwn
                ))
        return result

    def _inventorize_software(self) -> SpecialAgentInventory:
        result = SpecialAgentInventory()
        ntp_servers = ""
        single_sign_on_enabled = False
        min_password_length = None
        max_login_attempts = None
        array_os = None
        array_version = None
        smtp_server = None
        lockout_duration = None
        for adminsettings_item in self._adminsettings.query():
            try:
                if adminsettings_item.single_sign_on_enabled is not None:
                    single_sign_on_enabled = adminsettings_item.single_sign_on_enabled
            except AttributeError:
                pass
            try:
                if adminsettings_item.min_password_length is not None:
                    min_password_length = adminsettings_item.min_password_length
            except AttributeError:
                pass
            try:
                if adminsettings_item.max_login_attempts is not None:
                    max_login_attempts = adminsettings_item.max_login_attempts
            except AttributeError:
                pass
            try:
                if adminsettings_item.lockout_duration is not None:
                    lockout_duration = adminsettings_item.lockout_duration
            except AttributeError:
                pass
        for arraysettings_item in self._arraysettings.query():
            try:
                if arraysettings_item.os is not None:
                    array_os = arraysettings_item.os
            except AttributeError:
                pass
            try:
                if arraysettings_item.version is not None:
                    array_version = arraysettings_item.version
            except AttributeError:
                pass
            try:
                if arraysettings_item.ntp_servers is not None:
                    ntp_servers = ','.join(arraysettings_item.ntp_servers)
            except AttributeError:
                pass
        smtp_servers = []
        for smtpservers_item in self._smtpservers.query():
            try:
                if smtpservers_item.relay_host is not None:
                    smtp_servers.append(smtpservers_item.relay_host)
            except AttributeError:
                pass

        result.add_attributes(FlashArraySoftwareAttributes(
            single_sign_on_enabled=single_sign_on_enabled,
            array_os=array_os,
            array_version=array_version,
            ntp_servers=ntp_servers,
            smtp_server=','.join(smtp_servers),
            lockout_duration=lockout_duration,
            max_login_attempts=max_login_attempts,
            min_password_length=min_password_length,
        ))
        return result

    def _inventorize_apitokens(self) -> SpecialAgentInventory:
        result = SpecialAgentInventory()
        for apitoken_item in self._apitokens.query():
            if apitoken_item.name is not None:
                created_at = None
                expires_at = None
                try:
                    created_at = apitoken_item.api_token.created_at / 1000
                except AttributeError:
                    pass
                try:
                    expires_at = apitoken_item.api_token.expires_at / 1000
                except AttributeError:
                    pass
                result.add_table_row(APIToken(
                    name=apitoken_item.name,
                    created_at=created_at,
                    expires_at=expires_at
                ))
        return result

    def _inventorize_support(self) -> SpecialAgentInventory:
        result = SpecialAgentInventory()
        for support_item in self._support.query():
            if support_item is not None:
                result.add_attributes(SupportAttributes(
                    id=self._arrays.query()[0].id,
                    name=self._arrays.query()[0].name,
                    phonehome_enabled=support_item.phonehome_enabled if not None else None,
                    remote_assist_active=support_item.remote_assist_active if not None else None,
                ))
        return result

    def _inventorize_dns(self) -> SpecialAgentInventory:
        result = SpecialAgentInventory()
        for dns_item in self._dnssettings.query():
            result.add_table_row(DNSServer(
                name=self._resolve_attr(dns_item, ["name"]),
                nameservers=self._resolve_attr(dns_item, ["nameservers"]),
                services=self._resolve_attr(dns_item, ["services"]),
                domain=self._resolve_attr(dns_item, ["domain"]),
            ))
        return result

    def _inventorize_arrayconnections(self) -> SpecialAgentInventory:
        result = SpecialAgentInventory()
        for arrayconnection_item in self._arrayconnections.query():
            if arrayconnection_item.name is not None:
                result.add_table_row(ArrayConnection(
                    name=arrayconnection_item.name,
                    management_address=arrayconnection_item.management_address,
                    connection_type=arrayconnection_item.type,
                ))
        return result

    def _inventorize_hosts(self) -> SpecialAgentInventory:
        result = SpecialAgentInventory()
        for host_item in self._hosts.query():
            if host_item.name is not None:
                result.add_table_row(Hosts(
                    name=host_item.name,
                    connection_count=host_item.connection_count,
                    iqns=','.join(host_item.iqns)
                ))
        return result

    def _inventorize_volumes(self) -> SpecialAgentInventory:
        result = SpecialAgentInventory()
        for volume_item in self._volumes.query():
            if volume_item.name is not None:
                result.add_table_row(Volumes(
                    name=volume_item.name,
                    connection_count=volume_item.connection_count,
                    id=volume_item.id
                ))
        return result

    def _inventorize_network_interfaces(self) -> SpecialAgentInventory:
        result = SpecialAgentInventory()
        for networkinterface_item in self._networkinterfaces.query():
            vlans = []
            vlan = self._resolve_attr(networkinterface_item, ["eth", "vlan"])
            if vlan is not None:
                vlans.append(vlan)
            speed = None
            status = None
            administrative_status = None
            networkinterface_item_name = self._resolve_attr(networkinterface_item, ["name"])
            for hardware_item in self._hardware.query():
                hardware_item_type = self._resolve_attr(hardware_item, ["type"])
                hardware_item_name = self._resolve_attr(hardware_item, ["name"])
                if (
                        (hardware_item_type == "eth_port" or hardware_item_type == "fc") and
                        hardware_item_name is not None and
                        networkinterface_item_name is not None and
                        hardware_item_name.lower() == networkinterface_item_name.lower()
                ):
                    try:
                        if hardware_item.speed is not None:
                            speed = hardware_item.speed
                    except AttributeError:
                        pass

                    if hardware_item.status not in ["unused", "not_installed"]:
                        if hardware_item.status in ["healthy", "ok"]:
                            status = NetworkInterfaceStatus.UP
                        elif hardware_item.status in ["unhealthy", "critical"]:
                            status = NetworkInterfaceStatus.DOWN
                        else:
                            status = NetworkInterfaceStatus.UNKONWN
                    administrative_status = NetworkInterfaceStatus.UP if hardware_item.status != "unused" and hardware_item.status != "not_installed" else NetworkInterfaceStatus.DORMANT

            result.add_table_row(NetworkInterfaceTableRow(
                alias=networkinterface_item_name,
                description=networkinterface_item_name,
                administrative_status=administrative_status,
                speed=speed,
                operational_status=status,
                model=None,
                serial=None,
                snmp_type=(
                    6 if self._resolve_attr(networkinterface_item, ["subtype"]) != "vif" else 53
                ) if networkinterface_item.interface_type == "eth" else 56,
                vlans=vlans,
                mac=self._resolve_attr(networkinterface_item, ["eth", "mac_address"])
            ))
            address = self._resolve_attr(networkinterface_item, ["eth", "address"])
            if address is not None:
                result.add_table_row(NetworkAddressTableRow(
                    address,
                    networkinterface_item.name,
                    self._resolve_attr(networkinterface_item, ["eth", "netmask"])
                ))
            gateway = self._resolve_attr(networkinterface_item, ["eth", "gateway"])
            if gateway is not None:
                result.add_table_row(NetworkRouteTableRow(
                    "0.0.0.0" if ipv4_regex.match(gateway) else "::",
                    gateway,
                    None,
                    networkinterface_item.name,
                ))
        return result

    @staticmethod
    def _resolve_attr(obj, attrs: List[str]):
        for attr in attrs:
            try:
                obj = getattr(obj, attr, None)
                if obj is None:
                    return None
            except AttributeError:
                return None
        return obj

    def _inventorize_hardware(self) -> SpecialAgentInventory:
        result = SpecialAgentInventory()
        for hardware_item in self._hardware.query():
            if hardware_item.type == "controller":
                if hardware_item.status != "unused":
                    result.add_table_row(DriveController(
                        name=hardware_item.name,
                        serial=hardware_item.serial,
                        model=hardware_item.model,
                        type=hardware_item.type
                    ))
            elif hardware_item.type == "temp_sensor":
                result.add_table_row(SensorTableRow(
                    index=hardware_item.index,
                    name=hardware_item.name,
                    model=None,
                    serial=None,
                    type=hardware_item.type,
                    temperature=hardware_item.temperature
                ))
            elif hardware_item.type == "cooling":
                result.add_table_row(FanTableRow(
                    index=hardware_item.index,
                    name=hardware_item.name,
                    model=None,
                    serial=None,
                    type=hardware_item.type
                ))
            elif hardware_item.type == "drive_bay":
                result.add_table_row(BackplaneTableRow(
                    index=hardware_item.index,
                    name=hardware_item.name,
                    model=None,
                    serial=hardware_item.serial if hardware_item.status != "not_installed" else None,
                    type=hardware_item.type
                ))
            elif hardware_item.type == "nvram_bay":
                result.add_table_row(BackplaneTableRow(
                    index=hardware_item.index,
                    name=hardware_item.name,
                    model=None,
                    serial=None,
                    type=hardware_item.type
                ))
            elif hardware_item.type == "chassis":
                result.add_table_row(ChassisTableRow(
                    name=hardware_item.name,
                    serial=hardware_item.serial,
                    model=hardware_item.model
                ))
            elif hardware_item.type == "direct_compress_accelerator":
                result.add_table_row(OtherHardwareComponentTableRow(
                    name=hardware_item.name,
                ))
            elif hardware_item.type == "eth_port":
                # Inventorized through the interfaces call
                continue
            elif hardware_item.type == "fc_port":
                speed = None
                try:
                    if hardware_item.speed is not None:
                        speed = hardware_item.speed
                except AttributeError:
                    pass
                status = None
                if hardware_item.status not in ["unused", "not_installed"]:
                    if hardware_item.status in ["healthy", "ok"]:
                        status = NetworkInterfaceStatus.UP
                    elif hardware_item.status in ["unhealthy", "critical"]:
                        status = NetworkInterfaceStatus.DOWN
                    else:
                        status = NetworkInterfaceStatus.UNKONWN
                result.add_table_row(NetworkInterfaceTableRow(
                    alias=hardware_item.name,
                    description=hardware_item.name,
                    administrative_status=NetworkInterfaceStatus.UP if hardware_item.status != "unused" and hardware_item.status != "not_installed" else NetworkInterfaceStatus.DORMANT,
                    speed=speed,
                    operational_status=status,
                    model=None,
                    serial=None,
                    snmp_type=56
                ))
            elif hardware_item.type == "power_supply":
                result.add_table_row(PSUTableRow(
                    index=hardware_item.index,
                    description=hardware_item.name,
                    model=hardware_item.model,
                    serial=hardware_item.serial,
                    voltage=hardware_item.voltage,
                ))
            else:
                if hardware_item.status != "unused" and hardware_item.status != "not_installed":
                    result.add_table_row(OtherHardwareComponentTableRow(
                        name=hardware_item.name,
                        model=hardware_item.model,
                        serial=hardware_item.serial,
                        type=hardware_item.type
                    ))
        return result

    def _collect_array(self) -> SpecialAgentResult:
        result = SpecialAgentResult()
        for item in self._arrays.query():
            id = item.id
            space = item.space
            physical = space.total_physical
            capacity = item.capacity
            ratio = 100 * (physical / capacity)
            result.add_metric_with_service(
                "used capacity",
                Metric(
                    value=ratio,
                    levels=(self._cfg.array.warn, self._cfg.array.crit),
                    boundaries=(0, 100),
                ),
                details=id,
                summary="%.1f%% full (%s of %s)" % (ratio, format_bytes(physical), format_bytes(capacity))
            )
            for name, value in {
                "total physical": lambda: space.total_physical,
                "shared": lambda: space.shared,
                "snapshots": lambda: space.snapshots,
                "system": lambda: space.system,
                "total provisioned": lambda: space.total_provisioned,
                "used provisioned": lambda: space.used_provisioned,
                "total capacity": lambda: item.capacity
            }.items():
                try:
                    result.add_metric_with_service(
                        name,
                        Metric(
                            value=value(),
                        ),
                        summary=format_bytes(value()),
                    )
                except AttributeError:
                    pass
            for name, value in {
                "total reduction": lambda: space.total_reduction,
                "data reduction": lambda: space.data_reduction,
            }.items():
                try:
                    result.add_metric_with_service(
                        name,
                        Metric(
                            value=value(),
                        ),
                        summary=str("%.1f to 1" % value()),
                    )
                except AttributeError:
                    pass
            try:
                thin_provisioning = space.thin_provisioning * 100
                result.add_metric_with_service(
                    "thin provisioning",
                    Metric(
                        value=thin_provisioning
                    ),
                    summary="%.1f%%" % thin_provisioning
                )
            except AttributeError:
                pass
        return result

    def _collect_certificates(self) -> SpecialAgentResult:
        result = SpecialAgentResult()
        for item in self._certificates.query():
            details = item.status
            now = time.time()
            valid_to = item.valid_to / 1000
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


def run(stdin: TextIO, stdout: TextIO) -> int:
    """
    This function runs the special agent and produces the output data.
    :param stdin: The standard input to read the configuration from.
    :param stdout: The standard output to write the section to.
    :return: The return code.
    """
    stdin_data = stdin.read()
    cfg: FlashArraySpecialAgentConfiguration = FlashArraySpecialAgentConfiguration.from_json(stdin_data)
    try:
        cli = FlashArraySpecialAgent(cfg)
    except Exception as e:
        logging.fatal(f"Invalid FlashArray configuration or FlashArray not reachable at {cfg.host} ({e.__str__()}")
        return 1
    section = CheckmkSection(
        flasharray_results_section_id,
        cli.results()
    )
    stdout.write(str(section))
    section = CheckmkSection(
        flasharray_inventory_section_id,
        cli.inventory()
    )
    stdout.write(str(section))
    return 0
