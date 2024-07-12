#!/usr/bin/env python3

from typing import Mapping, Sequence, Union, Dict

from cmk.base.config import SpecialAgentInfoFunction
from purestorage_checkmk.common import SpecialAgentConfiguration, LimitConfiguration
from purestorage_checkmk.flasharray.common import FlashArraySpecialAgentConfiguration, flasharray_results_section_id, \
    default_array_warn, default_array_crit, default_cert_warn, default_cert_crit, AlertsConfiguration, \
    FlashArrayHardwareServiceNameCustomization


def _build_parameters(
        params: Mapping[str, any],
        hostname: str,
        ipaddress: str | None
) -> str | Sequence[Union[str, int, float, tuple[str, str, str]]] | SpecialAgentConfiguration:
    host = hostname
    if ipaddress is not None:
        host = ipaddress

    host_ip = host
    if params["port"] is not None and params["port"] != 443:
        port = params["port"]
        host_ip += f":{port}"

    alerts = None
    if "alerts" in params:
        alerts = AlertsConfiguration(
            params["alerts"]["closed_alerts_lifetime"],
            params["alerts"]["severities"]["info"],
            params["alerts"]["severities"]["warning"],
            params["alerts"]["severities"]["critical"],
            params["alerts"]["severities"]["hidden"]
        )

    hardware = []
    if "hardware" in params:
        for hardware_config in params["hardware"]:
            hardware.append(
                FlashArrayHardwareServiceNameCustomization(
                    hardware_config[0],
                    hardware_config[1],
                    hardware_config[2]
                )
            )

    cfg = FlashArraySpecialAgentConfiguration(
        str(host_ip),
        str(params["apitoken"]),
        bool(params["verifytls"]),
        str(params["cert"]),
        alerts,
        LimitConfiguration.default(
            params["array"] if "array" in params else {},
            default_warn=default_array_warn,
            default_crit=default_array_crit,
            prefix="used_"),
        LimitConfiguration.default(
            params["certificates"] if "certificates" in params else {},
            default_warn=default_cert_warn,
            default_crit=default_cert_crit,
            prefix="days_"
        ),
        hardware,
    )
    return SpecialAgentConfiguration(
        [],
        cfg.to_json()
    )


def register(special_agent_info: Dict[str, SpecialAgentInfoFunction]):
    special_agent_info[flasharray_results_section_id] = _build_parameters
