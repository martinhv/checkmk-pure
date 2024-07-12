#!/usr/bin/env python3

from typing import Mapping, Sequence, Union

from cmk.base.config import SpecialAgentInfoFunction
from purestorage_checkmk.common import SpecialAgentConfiguration, LimitConfiguration
from purestorage_checkmk.flashblade.common import FlashBladeSpecialAgentConfiguration, flashblade_results_section_id, \
    default_cert_warn, default_cert_crit, AlertsConfiguration, default_array_space_warn, default_array_space_crit, \
    default_filesystem_space_warn, default_filesystem_space_crit, default_objectstore_space_warn, \
    default_objectstore_space_crit, FlashBladeHardwareServiceNameCustomization


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
            params["alerts"]["severities"]["critical"]
        )

    hardware = []
    if "hardware" in params:
        for hardware_config in params["hardware"]:
            hardware.append(
                FlashBladeHardwareServiceNameCustomization(
                    hardware_config[0],
                    hardware_config[1],
                    hardware_config[2]
                )
            )

    cfg = FlashBladeSpecialAgentConfiguration(
        str(host_ip),
        str(params["apitoken"]),
        bool(params["verifytls"]),
        str(params["cert"]),
        alerts,
        LimitConfiguration.default(
            params["certificates"] if "certificates" in params else {},
            default_warn=default_cert_warn,
            default_crit=default_cert_crit,
            prefix="days_"
        ),
        LimitConfiguration.default(
            params["space"] if "space" in params else {},
            default_warn=default_array_space_warn,
            default_crit=default_array_space_crit,
            prefix="array_used_"
        ),
        LimitConfiguration.default(
            params["space"] if "space" in params else {},
            default_warn=default_filesystem_space_warn,
            default_crit=default_filesystem_space_crit,
            prefix="filesystem_used_"
        ),
        hardware,
        LimitConfiguration.default(
            params["space"] if "space" in params else {},
            default_warn=default_objectstore_space_warn,
            default_crit=default_objectstore_space_crit,
            prefix="objectstore_used_"
        ),
    )

    return SpecialAgentConfiguration(
        [],
        cfg.to_json()
    )


def register(special_agent_info: dict[str, SpecialAgentInfoFunction]):
    special_agent_info[flashblade_results_section_id] = _build_parameters
