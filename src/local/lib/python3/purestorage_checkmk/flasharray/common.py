import dataclasses
import typing
from typing import Optional, List

from purestorage_checkmk.common import SpecialAgentResult, AbstractSpecialAgentSection, \
    AbstractSpecialAgentConfiguration, LimitConfiguration, SpecialAgentInventory, Attributes, TableRow

flasharray_results_section_id = "purestorage_flasharray"
flasharray_inventory_section_id = "purestorage_flasharray_inventory"

default_array_warn = 80
default_array_crit = 90
default_cert_warn = 90
default_cert_crit = 30
default_closed_alerts_lifetime = 3600


@dataclasses.dataclass
class AlertsConfiguration:
    closed_alerts_lifetime: int
    info: bool
    warning: bool
    critical: bool
    hidden: bool


@dataclasses.dataclass
class FlashArrayHardwareServiceNameCustomization:
    api_type: str
    prefix: str
    suffix: str


@dataclasses.dataclass
class FlashArraySpecialAgentConfiguration(AbstractSpecialAgentConfiguration):
    """
    This class holds the special agent configuration as it is passed from the invoker to the
    special agent itself.
    """

    host: str = ""
    api_token: str = ""
    verify_tls: bool = True
    cacert: str = ""
    alerts: Optional[AlertsConfiguration] = None
    array: LimitConfiguration = dataclasses.field(
        default_factory=lambda: LimitConfiguration(default_array_warn, default_array_crit)
    )
    certificates: LimitConfiguration = dataclasses.field(
        default_factory=lambda: LimitConfiguration(default_cert_warn, default_cert_crit)
    )
    hardware: typing.List[FlashArrayHardwareServiceNameCustomization] = dataclasses.field(
        default_factory=list,
    )


@dataclasses.dataclass
class FlashArraySpecialAgentResultsSection(AbstractSpecialAgentSection):
    """
    This class holds the data the special agent extracted from the FlashArray. It is passed in a section to Checkmk as
    JSON. The check plugin then reads this and converts it into services and their corresponding statuses.
    """
    hardware: SpecialAgentResult
    certificates: SpecialAgentResult
    drives: SpecialAgentResult
    array: SpecialAgentResult
    alerts: SpecialAgentResult
    arrayconnections: SpecialAgentResult
    portdetails: SpecialAgentResult


@dataclasses.dataclass
class SupportAttributes(Attributes):
    def __init__(self, name: Optional[str] = None, id: Optional[str] = None, phonehome_enabled: Optional[bool] = None,
                 remote_assist_active: Optional[bool] = None):
        super().__init__(
            path=["software", "support"],
            inventory_attributes={
                "Name": name,
                "ID": id,
                "PhoneHome": phonehome_enabled,
                "RemoteAssistActive": remote_assist_active
            }
        )


class NIC(TableRow):
    def __init__(self, name: str, subtype: Optional[str] = None, address: Optional[str] = None,
                 netmask: Optional[str] = None, subinterfaces: Optional[str] = None, wwn: Optional[str] = None,
                 gateway: Optional[str] = None, mac_address: Optional[str] = None, vlan: Optional[int] = None,
                 mtu: Optional[int] = None, speed: Optional[int] = None, interface_type: Optional[str] = None,
                 services: Optional[str] = None):
        super().__init__(
            path=["hardware", "array", "network"],
            key_columns={
                "name": name,
            },
            inventory_columns={
                "subtype": subtype,
                "subinterfaces": subinterfaces,
                "address": address,
                "netmask": netmask,
                "gateway": gateway,
                "mac_address": mac_address,
                "vlan": vlan,
                "mtu": mtu,
                "speed": speed,
                "type": interface_type,
                "wwn": wwn
            }
        )


class DNSServer(TableRow):
    def __init__(self, name: str, domain: Optional[str] = None, services: Optional[List[str]] = None,
                 nameservers: Optional[List[str]] = None):
        if isinstance(services, list):
            services_new = ','.join(services)
        else:
            services_new = services
        super().__init__(
            path=["software", "os", "DNS"],
            key_columns={
                "name": name,
            },
            inventory_columns={
                "domain": domain,
                "nameservers": ','.join(nameservers),
                "services": services_new,
            }
        )


class Volumes(TableRow):
    def __init__(self, name: str, id: Optional[str], connection_count: Optional[int] = None):
        super().__init__(
            path=["hardware", "array", "volumes"],
            key_columns={
                "name": name,
            },
            inventory_columns={
                "id": id if id is not None else None,
                "connection_count": connection_count if connection_count is not None else None,
            }
        )


class ArrayConnection(TableRow):
    def __init__(self, name: str, management_address: Optional[str] = None, connection_type: Optional[str] = None):
        super().__init__(
            path=["software", "array", "connections"],
            key_columns={
                "name": name,
            },
            inventory_columns={
                "management_address": management_address if management_address is not None else None,
                "type": connection_type if connection_type is not None else None
            }
        )


class Hosts(TableRow):
    def __init__(self, name: str, connection_count: Optional[int] = None, iqns: Optional[str] = None):
        super().__init__(
            path=["hardware", "array", "connections"],
            key_columns={
                "name": name,
            },
            inventory_columns={
                "connection_count": connection_count if connection_count is not None else None,
                "iqns": iqns if iqns is not None else None,
            }
        )


class NetworkInterface(TableRow):
    def __init__(self, name: str, enabled: Optional[str] = None, interface_type: Optional[str] = None,
                 services: Optional[str] = None, speed: Optional[int] = None, address: Optional[str] = None,
                 gateway: Optional[str] = None, mac_address: Optional[str] = None, mtu: Optional[int] = None,
                 netmask: Optional[str] = None, subtype: Optional[str] = None, subinterfaces: Optional[str] = None,
                 subnet: Optional[str] = None, vlan: Optional[int] = None, wwn: Optional[str] = None):
        super().__init__(
            path=["hardware", "array", "network"],
            key_columns={
                "name": name,
            },
            inventory_columns={
                "enabled": enabled if not None else None,
                "services": services if not None else None,
                "speed": speed if not None else None,
                "address": address if not None else None,
                "gateway": gateway if not None else None,
                "mac_address": mac_address if not None else None,
                "mtu": mtu if not None else None,
                "netmask": netmask if not None else None,
                "subtype": subtype if not None else None,
                "subinterfaces": subinterfaces if not None else None,
                "subnet": subnet if not None else None,
                "vlan": vlan if not None else None,
                "wwn": wwn if not None else None
            }
        )


@dataclasses.dataclass
class FlashArraySoftwareAttributes(Attributes):
    def __init__(self, single_sign_on_enabled: Optional[bool] = None, min_password_length: Optional[int] = None,
                 max_login_attempts: Optional[int] = None, lockout_duration: Optional[int] = None,
                 array_os: Optional[str] = None, array_version: Optional[str] = None,
                 ntp_servers: Optional[str] = None, smtp_server: Optional[str] = None,
                 id: Optional[str] = None):
        super().__init__(
            path=["software", "os"],
            inventory_attributes={
                "name": array_os,
                "version": array_version,
                "SingleSignOn Enabled": single_sign_on_enabled,
                "Minimum Password Length": min_password_length,
                "Maximum Login Attempts": max_login_attempts,
                "Lockout Duration": lockout_duration,
                "NTP Servers": ntp_servers,
                "SMTP Server": smtp_server,
            }
        )


@dataclasses.dataclass
class FlashArraySpecialAgentInventorySection(AbstractSpecialAgentSection):
    hardware: SpecialAgentInventory
    software: SpecialAgentInventory
    dns: SpecialAgentInventory
    apitokens: SpecialAgentInventory
    network_interfaces: SpecialAgentInventory
    hosts: SpecialAgentInventory
    volumes: SpecialAgentInventory
    support: SpecialAgentInventory
    nics: SpecialAgentInventory
