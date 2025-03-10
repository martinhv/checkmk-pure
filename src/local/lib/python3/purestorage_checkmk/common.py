from __future__ import annotations

import abc
import base64
import dataclasses
import enum
import inspect
import json
import pprint
import re
import typing
from datetime import datetime
from typing import Optional, Sequence, NamedTuple, Dict, List

from pypureclient import ErrorResponse


class SpecialAgentConfiguration(NamedTuple):
    """
    This class is copied from cmk/base/config.py because the original improperly depends on a base class that is
    elsewhere referenced as CMK-3812. However, this issue is nowhere to be found and has probably been forgotten about.
    """

    args: Sequence[str]
    stdin: str | None


class State(int, enum.Enum):
    OK = 0
    WARN = 1
    CRIT = 2
    UNKNOWN = 3

    def toJSON(self):
        return json.dumps(self.value)


@dataclasses.dataclass
class Result:
    state: State
    summary: Optional[str] = None
    details: Optional[str] = None
    notice: Optional[str] = None

    def __init__(
            self,
            state: State,
            summary: Optional[str] = None,
            details: Optional[str] = None,
            notice: Optional[str] = None,
    ):
        super().__init__()
        assert summary is not None or notice is not None
        self.state = state
        self.summary = summary
        self.notice = notice
        self.details = details

    def toJSON(self):
        return json.dumps(dataclasses.asdict(self))

    @staticmethod
    def from_dict(data: Dict[str, any]) -> Result:
        return Result(**data)


@dataclasses.dataclass
class Metric:
    """
    A metric is a graphable value in Checkmk.
    """
    value: float
    """The value to display on the graph."""
    levels: typing.Tuple[Optional[float], Optional[float]] = (None, None)
    """The warn and crit levels of this value."""
    boundaries: typing.Tuple[Optional[float], Optional[float]] = (None, None)
    """The lower and upper bounds of the graph (e.g. (0,1) or (0,100)"""

    def toJSON(self):
        return json.dumps(dataclasses.asdict(self))

    @staticmethod
    def from_dict(data: Dict[str, any]) -> Metric:
        return Metric(**data)


@dataclasses.dataclass
class Attributes:
    """
    This class represents the data of a single item in a key-value fashion. If you have more of the same item, use
    TableRow.
    """
    path: typing.List[str]
    inventory_attributes: Dict[str, str] = dataclasses.field(default_factory=dict)
    status_attributes: Dict[str, int] = dataclasses.field(default_factory=dict)

    def toJSON(self):
        return json.dumps(dataclasses.asdict(self))

    @staticmethod
    def from_dict(data: Dict[str, any]) -> Attributes:
        return Attributes(**data)


@dataclasses.dataclass
class TableRow:
    path: typing.List[str]
    key_columns: Dict[str, any] = dataclasses.field(default_factory=dict)
    inventory_columns: Optional[Dict[str, any]] = None
    status_columns: Optional[Dict[str, any]] = None

    def toJSON(self):
        return json.dumps(dataclasses.asdict(self))

    @classmethod
    def from_dict(cls, data: Dict[str, any]) -> TableRow:
        return cls(**data)


ipv4_regex = re.compile("^[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}$")


@dataclasses.dataclass
class NetworkAddressTableRow(TableRow):

    def __init__(self, address: str, device: str, subnet: str):
        ip_type = "IPv4"
        if not ipv4_regex.match(address):
            ip_type = "IPv6"
        super().__init__(
            path=["networking", "addresses"],
            key_columns={
                "device": device
            },
            inventory_columns={
                "address": address,
                "type": ip_type,
                "subnet": subnet
            }
        )


class NetworkInterfaceStatus(enum.Enum):
    UP = 1
    DOWN = 2
    TESTING = 3
    UNKONWN = 4
    DORMANT = 5
    NOT_PRESENT = 6
    LOWER_LAYER_DOWN = 7


class NIC(TableRow):
    def __init__(
            self,
            name: str,
            address: Optional[str] = None,
            netmask: Optional[str] = None,
            gateway: Optional[str] = None,
            mac_address: Optional[str] = None,
            vlan: Optional[int] = None,
            mtu: Optional[int] = None,
            speed: Optional[int] = None,
            interface_type: Optional[str] = None,
            services: Optional[str] = None,
    ):
        """
        :param name:
        :param address:
        :param netmask:
        :param gateway:
        :param mac_address:
        :param vlan:
        :param mtu:
        :param speed:
        :param interface_type:
        :param services:
        """
        super().__init__(
            path=["networking", "nics"],
            key_columns={
                "name": name,
                "interface_type": interface_type,
            },
            inventory_columns={
                "address": address,
                "netmask": netmask,
                "gateway": gateway,
                "mac_address": mac_address,
                "vlan": vlan,
                "mtu": mtu,
                "speed": speed,
                "services": services
            }
        )


@dataclasses.dataclass
class NetworkInterfaceTableRow(TableRow):
    def __init__(
            self,
            description: str,
            alias: str,
            snmp_type: Optional[int] = None,
            speed: typing.Optional[int] = None,
            mac: typing.Optional[str] = None,
            vlans: typing.Optional[List[int]] = None,
            administrative_status: Optional[NetworkInterfaceStatus] = None,
            operational_status: Optional[NetworkInterfaceStatus] = None,
            model: Optional[str] = None,
            serial: Optional[str] = None
    ):
        """
        :param description:
        :param alias:
        :param snmp_type: See https://www.iana.org/assignments/ianaiftype-mib/ianaiftype-mib
        :param speed:
        :param mac:
        :param vlans:
        :param administrative_status:
        :param operational_status:
        :param model:
        :param serial:
        """
        super().__init__(
            path=["networking", "interfaces"],
            key_columns={
                "port_type": snmp_type,
                "description": description,
                "alias": alias,
            },
            inventory_columns={
                "model": model,
                "serial": serial,
                "speed": speed,
                "phys_address": mac,
                "oper_status": operational_status.value if operational_status is not None else None,
                "admin_status": administrative_status.value if administrative_status is not None else None,
                "vlans": (','.join(str(vlan) for vlan in vlans)) if vlans is not None else None
            }
        )


@dataclasses.dataclass
class NetworkRouteTableRow(TableRow):
    def __init__(self, target: str, gateway: str, type: Optional[str] = None, device: Optional[str] = None):
        super().__init__(
            path=["networking", "routes"],
            key_columns={
                "target": target,
                "gateway": gateway,
            },
            inventory_columns={
                "type": type,
                "device": device,
            },
            status_columns={},
        )


@dataclasses.dataclass
class HardwareModuleTableRow(TableRow):
    def __init__(self, index: int, name: str, model: Optional[str] = None, serial: Optional[str] = None,
                 type: Optional[str] = None, capacity: Optional[int] = None):
        super().__init__(
            path=["hardware", "components", "modules"],
            key_columns={
                "index": index,
                "name": name,
            },
            inventory_columns={
                "model": model,
                "serial": serial,
                "type": type,
                "capacity": capacity,
            }
        )


@dataclasses.dataclass
class ChassisTableRow(TableRow):
    def __init__(self, name: str, manufacturer: Optional[str] = None, type: Optional[str] = None,
                 serial: Optional[str] = None,
                 model: Optional[str] = None, bootloader: Optional[str] = None, firmware: Optional[str] = None):
        super().__init__(
            path=["hardware", "chassis"],
            key_columns={
                "name": name,
                "Manufacturer": manufacturer,
                "model": model,
            },
            inventory_columns={
                "serial": serial,
                "Type": type,
                "bootloader": bootloader,
                "firmware": firmware,
            }
        )


@dataclasses.dataclass
class ChassisAttributes(Attributes):
    def __init__(self, manufacturer: Optional[str] = None, type: Optional[str] = None, serial: Optional[str] = None,
                 model: Optional[str] = None, bootloader: Optional[str] = None, firmware: Optional[str] = None):
        super().__init__(
            path=["hardware", "chassis"],
            inventory_attributes={
                "Manufacturer": manufacturer,
                "model": model,
                "serial": serial,
                "Type": type,
                "bootloader": bootloader,
                "firmware": firmware,
            }
        )


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


@dataclasses.dataclass
class DNSAttributes(Attributes):
    def __init__(self, name: [str], domain: Optional[str] = None, nameservers: Optional[str] = None):
        super().__init__(
            path=["software", "os", "DNS"],
            inventory_attributes={
                "name": name,
                "domain": domain,
                "nameservers": nameservers,
            }
        )


class SMTPAttributes(Attributes):
    def __init__(self, name: Optional[str] = None, relay_host: Optional[str] = None,
                 sender_domain: Optional[str] = None):
        super().__init__(
            path=["software", "smtp"],
            inventory_attributes={
                "name": name if not None else None,
                "Sender Domain": sender_domain if not None else None,
                "Relay Host": relay_host if not None else None,
            }
        )


@dataclasses.dataclass
class DriveController(TableRow):
    def __init__(self, name: str, manufacturer: Optional[str] = None, type: Optional[str] = None,
                 serial: Optional[str] = None,
                 model: Optional[str] = None, bootloader: Optional[str] = None, firmware: Optional[str] = None):
        super().__init__(
            path=["hardware", "storage", "controller"],
            key_columns={
                "name": name,
            },
            inventory_columns={
                "Manufacturer": manufacturer,
                "model": model,
                "serial": serial,
                "Type": type,
                "bootloader": bootloader,
                "firmware": firmware,
            }
        )


@dataclasses.dataclass
class BackplaneTableRow(TableRow):
    def __init__(self, index: int, name: str, model: Optional[str] = None, serial: Optional[str] = None,
                 type: Optional[str] = None):
        super().__init__(
            path=["hardware", "components", "backplanes"],
            key_columns={
                "index": index,
                "name": name,
            },
            inventory_columns={
                "model": model,
                "serial": serial,
                "type": type,
            }
        )


@dataclasses.dataclass
class FanTableRow(TableRow):
    def __init__(self, index: int, name: str, model: Optional[str] = None, serial: Optional[str] = None,
                 type: Optional[str] = None):
        super().__init__(
            path=["hardware", "components", "fans"],
            key_columns={
                "index": index,
                "name": name,
            },
            inventory_columns={
                "model": model,
                "serial": serial,
                "type": type,
            }
        )


@dataclasses.dataclass
class SensorTableRow(TableRow):
    def __init__(self, index: int, name: str, model: Optional[str] = None, serial: Optional[str] = None,
                 type: Optional[str] = None, temperature: Optional[float] = None):
        super().__init__(
            path=["hardware", "components", "snsors"],
            key_columns={
                "index": index,
                "name": name,
            },
            inventory_columns={
                "model": model,
                "serial": serial,
                "type": type,
            },
            status_columns={
                "temperature": temperature
            }
        )


@dataclasses.dataclass
class ManagementPortTableRow(TableRow):
    def __init__(self, name: str, model: Optional[str] = None, serial: Optional[str] = None,
                 type: Optional[str] = None):
        super().__init__(
            path=["hardware", "management_interface"],
            key_columns={
                "name": name,
            },
            inventory_columns={
                "model": model,
                "serial": serial,
                "type": type,
            }
        )


@dataclasses.dataclass
class OtherHardwareComponentTableRow(TableRow):
    def __init__(self, name: str, model: Optional[str] = None, serial: Optional[str] = None,
                 type: Optional[str] = None):
        super().__init__(
            path=["hardware", "components", "others"],
            key_columns={
                "name": name,
            },
            inventory_columns={
                "model": model,
                "serial": serial,
                "type": type,
            }
        )


@dataclasses.dataclass
class PSUTableRow(TableRow):
    def __init__(
            self,
            index: int,
            description: str,
            model: str,
            serial: str,
            voltage: Optional[int] = None
    ):
        super().__init__(
            path=["hardware", "components", "psus"],
            key_columns={
                "index": index
            },
            inventory_columns={
                "description": description,
                "model": model,
                "serial": serial,
            },
            status_columns={
                "voltage": voltage
            }
        )


@dataclasses.dataclass
class APIToken(TableRow):
    def __init__(self, name: str, created_at: Optional[int] = None, expires_at: Optional[int] = None):
        super().__init__(
            path=["software", "os", "API_tokens"],
            key_columns={
                "name": name,
            },
            inventory_columns={
                "created_at": str(datetime.fromtimestamp(created_at)) if created_at is not None else None,
                "expires_at": str(datetime.fromtimestamp(expires_at)) if expires_at is not None else None,
            }
        )


class _Comparison(abc.ABC):
    @abc.abstractmethod
    def compare(self, a: float, b: float) -> bool:
        pass


class _LTEComparison(_Comparison):
    def compare(self, a: float, b: float) -> bool:
        return a <= b


class _GTEComparison(_Comparison):
    def compare(self, a: float, b: float) -> bool:
        return a >= b


class Compare(enum.Enum):
    LTE = _LTEComparison()
    GTE = _GTEComparison()

    @property
    def value(self) -> _Comparison:
        return super().value


@dataclasses.dataclass
class SpecialAgentResult:
    services: Dict[str, Result] = dataclasses.field(default_factory=dict)
    metrics: Dict[str, Metric] = dataclasses.field(default_factory=dict)

    def add_service(self, name: str, service: Result) -> SpecialAgentResult:
        self.services[name] = service
        return self

    def add_metric_with_service(
            self,
            name: str,
            metric: Metric,
            details: typing.Optional[str] = None,
            summary: typing.Optional[str] = None,
            comparison: Compare = Compare.GTE
    ) -> SpecialAgentResult:
        self.add_metric(name, metric)
        state = State.OK
        if metric.levels is not None:
            if metric.levels[1] is not None and comparison.value.compare(metric.value, metric.levels[1]):
                state = State.CRIT
            elif metric.levels[0] is not None and comparison.value.compare(metric.value, metric.levels[0]):
                state = State.WARN
        if details is None:
            details = str(metric.value)
        self.add_service(name, Result(
            state,
            details=details,
            summary=summary
        ))
        return self

    def add_metric(self, name: str, metric: Metric) -> SpecialAgentResult:
        self.metrics[name] = metric
        return self

    def to_dict(self):
        return dataclasses.asdict(self)


@dataclasses.dataclass
class SpecialAgentInventory:
    inventory_attributes: List[Attributes] = dataclasses.field(default_factory=list)
    inventory_table_rows: List[TableRow] = dataclasses.field(default_factory=list)

    def add_attributes(self, attributes: Attributes) -> SpecialAgentInventory:
        self.inventory_attributes.append(attributes)
        return self

    def add_table_row(self, table_row: TableRow) -> SpecialAgentInventory:
        self.inventory_table_rows.append(table_row)
        return self

    def to_dict(self):
        return dataclasses.asdict(self)


@dataclasses.dataclass
class CheckmkSection:
    """
    CheckmkSection holds and produces one section output.

    Example:

    >>> section = CheckmkSection("linux_usbstick", "Hello world!")
    >>> print(str(section))
    <<<linux_usbstick>>>
    Hello world!
    <BLANKLINE>
    """

    """
    This field is the section identifier. Plugins will be called based on this ID so it must match any processing
    plugins.
    """
    id: str
    """
    This field can hold any data structure as long as it can be converted to a string.
    """
    data: any

    def __str__(self):
        """
        This function produces a string in the Checkmk format.
        """
        nl = '\n'
        return f"<<<{self.id}>>>{nl}{str(self.data)}{nl}"


@dataclasses.dataclass
class LimitConfiguration:
    warn: float
    crit: float

    @classmethod
    def default(cls, params: Dict, default_warn: float, default_crit: float, prefix: str = "") -> LimitConfiguration:
        warn = default_warn
        if f"{prefix}warn" in params:
            warn = params[f"{prefix}warn"]
        crit = default_crit
        if f"{prefix}crit" in params:
            crit = params[f"{prefix}crit"]
        return cls(warn, crit)


@dataclasses.dataclass
class AbstractSpecialAgentConfiguration(abc.ABC):
    def to_json(self) -> str:
        return json.dumps(dataclasses.asdict(self))

    @classmethod
    def from_json(cls, data: str):
        # noinspection PyArgumentList
        return from_dict(json.loads(data), cls)

    def __str__(self):
        return self.to_json()


@dataclasses.dataclass
class AbstractSpecialAgentSection(abc.ABC):
    """
    This is the abstract base class for the special agent sections.
    """

    def to_dict(self) -> Dict[str, any]:
        result = {}
        for field in dataclasses.fields(self):
            result[field.name] = getattr(self, field.name).to_dict()
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, any]):
        return from_dict(data, cls)

    def toJSON(self):
        return json.dumps(self.to_dict())

    def to_section(self) -> str:
        return base64.b64encode(self.toJSON().encode('ascii')).decode('ascii')

    @classmethod
    def from_section(cls, data: str):
        data = json.loads(base64.b64decode(data))
        return cls.from_dict(data)

    def __str__(self):
        return self.to_section()


class ErrorResponseException(Exception):
    """
    This is an exception that gets raised when the response from the pypureclient library is an
    ErrorResponse.
    """

    response: ErrorResponse

    def __init__(self, response: ErrorResponse):
        self.response = response

    def __str__(self):
        return f"Pure Storage API query failed: {self.response}"


T = typing.TypeVar('T')


class CheckResponse(typing.Generic[T]):
    """
    CheckResponse makes sure that the response returned from the pypureclient is not an ErrorResponse. If it is, it
    turns the response into an exception.

    Note: this class acts as a function and can be used as such.

    Example:

        import pypureclient
        _cli = pypureclient.flashblade.client.Client(
            "localhost",
            api_token="my-api-token",
        )
        hardware = CheckResponse(_cli.get_hardware())
    """

    def __new__(cls, response):
        if isinstance(response, ErrorResponse):
            raise ErrorResponseException(response)
        return response


def _from_type(data, target: typing.Type, origin, args):
    if origin == dict:
        # Dict
        value_type = args[1]
        origin = typing.get_origin(value_type)
        args = typing.get_args(value_type)
        result = {}
        for key in data:
            result[key] = _from_type(data[key], value_type, origin, args)
        return result
    elif origin == list:
        # List
        value_type = args[0]
        origin = typing.get_origin(value_type)
        args = typing.get_args(value_type)
        result = []
        for value in data:
            result.append(_from_type(value, value_type, origin, args))
        return result
    elif origin == tuple:
        i = 0
        result = []
        for arg in args:
            new_origin = typing.get_origin(arg)
            new_args = typing.get_args(arg)
            result.append(_from_type(data[i], arg, new_origin, new_args))
            i += 1
        return tuple(result)
    elif origin == typing.Union:
        # Optional, we don't support union
        new_target = args[0]
        origin = typing.get_origin(new_target)
        args = typing.get_args(new_target)
        if data is None:
            return None
        return _from_type(data, new_target, origin, args)
    elif inspect.isclass(target) and issubclass(target, enum.Enum):
        # Enums
        for key in target:
            if data == key.value:
                return key
        raise Exception("Invalid value %v for %T", data, target)
    elif target not in [str, int, bool, float, any]:
        # Dataclass
        result = {}
        # noinspection PyDataclass
        try:
            fs = dataclasses.fields(target)
            type_hints = typing.get_type_hints(target)
        except TypeError as e:
            raise Exception(f"{pprint.pformat(target)} is not a dataclass") from e
        for field in fs:
            if field.name in data:
                type_hint = type_hints[field.name]
                if field.type not in [str, int, bool, float]:
                    origin = typing.get_origin(type_hint)
                    args = typing.get_args(type_hint)
                    data[field.name] = _from_type(data[field.name], type_hint, origin, args)
                result[field.name] = data[field.name]
        return target(**result)
    else:
        return data


def from_dict(data: dict, target: typing.Type[dataclasses.dataclass]):
    origin = typing.get_origin(target)
    args = typing.get_args(target)
    return _from_type(data, target, origin, args)


_byte_dividers = {
    1024 * 1024 * 1024 * 1024 * 1024: "PB",
    1024 * 1024 * 1024 * 1024: "TB",
    1024 * 1024 * 1024: "GB",
    1024 * 1024: "MB",
    1024: "kB",
}


def format_bytes(bytes: int) -> str:
    for divider, name in _byte_dividers.items():
        if bytes / divider > 1:
            return f"{int(bytes / divider)} {name}"
    return f"{bytes} B"


if __name__ == "__main__":
    import doctest

    doctest.testmod()
