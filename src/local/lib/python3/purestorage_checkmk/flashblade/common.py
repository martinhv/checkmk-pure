import abc
import dataclasses
import enum
import typing
from typing import Dict

from purestorage_checkmk.common import SpecialAgentResult, AbstractSpecialAgentSection, \
    AbstractSpecialAgentConfiguration, LimitConfiguration, SpecialAgentInventory, Attributes

flashblade_results_section_id = "purestorage_flashblade"
flashblade_inventory_section_id = "purestorage_flashblade_inventory"

default_cert_warn = 90
default_cert_crit = 30
default_closed_alerts_lifetime = 3600
default_alert_crit = 30
default_array_space_warn = 80
default_array_space_crit = 90
default_filesystem_space_warn = 80
default_filesystem_space_crit = 90
default_objectstore_space_warn = 80
default_objectstore_space_crit = 90


@dataclasses.dataclass
class AlertsConfiguration:
    closed_alerts_lifetime: int
    info: bool
    warning: bool
    critical: bool


@dataclasses.dataclass
class FlashBladeHardwareServiceNameCustomization:
    api_type: str
    prefix: str
    suffix: str


@dataclasses.dataclass
class FlashBladeSpecialAgentConfiguration(AbstractSpecialAgentConfiguration):
    """
    This class holds the special agent configuration as it is passed from the invoker to the
    special agent itself.
    """

    host: str = ""
    api_token: str = ""
    verify_tls: bool = True
    cacert: str = ""
    alerts: typing.Optional[AlertsConfiguration] = None
    certificates: LimitConfiguration = dataclasses.field(default_factory=lambda: LimitConfiguration(
        default_cert_warn,
        default_cert_crit
    ))
    array_space: LimitConfiguration = dataclasses.field(default_factory=lambda: LimitConfiguration(
        default_array_space_warn,
        default_array_space_crit
    ))
    filesystem_space: LimitConfiguration = dataclasses.field(default_factory=lambda: LimitConfiguration(
        default_filesystem_space_warn,
        default_array_space_crit
    ))
    hardware: typing.List[FlashBladeHardwareServiceNameCustomization] = dataclasses.field(
        default_factory=list,
    )
    objectstore_space: LimitConfiguration = dataclasses.field(default_factory=lambda: LimitConfiguration(
        default_objectstore_space_warn,
        default_objectstore_space_crit
    ))


@dataclasses.dataclass
class FlashBladeSpecialAgentResultsSection(AbstractSpecialAgentSection):
    hardware: SpecialAgentResult
    alerts: SpecialAgentResult
    certificates: SpecialAgentResult
    space: SpecialAgentResult


@dataclasses.dataclass
class FlashBladeSpecialAgentInventorySection(AbstractSpecialAgentSection):
    hardware: SpecialAgentInventory
    network_interfaces: SpecialAgentInventory
    array: SpecialAgentInventory
    support: SpecialAgentInventory
    apitokens: SpecialAgentInventory
    smtp: SpecialAgentInventory
    dns: SpecialAgentInventory


@dataclasses.dataclass
class FlashBladeSoftwareAttributes(Attributes):
    def __init__(
            self,
            single_sign_on_enabled: typing.Optional[bool] = None,
            min_password_length: typing.Optional[int] = None,
            max_login_attempts: typing.Optional[int] = None,
            lockout_duration: typing.Optional[int] = None,
            array_os: typing.Optional[str] = None,
            array_version: typing.Optional[str] = None,
            ntp_servers: typing.Optional[str] = None,
            smtp_server: typing.Optional[str] = None
    ):
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
