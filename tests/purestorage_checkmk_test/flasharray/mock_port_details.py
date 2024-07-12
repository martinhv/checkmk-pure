import dataclasses
import re
import typing
from typing import List

from purestorage_checkmk_test.flasharray.mock_controllers import ControllersContainer
from purestorage_checkmk_test.flasharray.mock_route import _AuthenticatedJSONRoute, _AuthTokenStorage, \
    _ContinuationTokenContainer, _JSONRequest, _JSONResponse
from purestorage_checkmk_test.httpmock import Response


@dataclasses.dataclass
class PortThresholds:
    warn_low: float
    warn_high: float
    alarm_low: float
    alarm_high: float


@dataclasses.dataclass
class PortMetric:
    channel: typing.Optional[int]
    status: str
    measurement: float


@dataclasses.dataclass
class PortMetricFlag:
    channel: typing.Optional[int]
    flag: bool


@dataclasses.dataclass
class PortDetailsStatic:
    encoding: str  # "64B/66B"
    identifier: str  # "SFP"
    connector_type: str  # "LC"
    extended_identifier: str  # "GBIC/SFP function is defined by 2-wire interface ID only"
    rate_identifier: str  # "FC-PI-5 (16/8/4G Independent Rx, Tx Rate_select)"
    specifications: typing.Optional[List[str]]  # ["10GBASE-SR"]
    fc_link_lengths: typing.Optional[List[str]]  # ["short distance (S)", "intermediate distance (I)"]
    fc_technology: typing.Optional[List[str]]  # ["Shortwave laser w/o OFC (SN)"]
    cable_technology: typing.Optional[str] # ??
    fc_transmission_media: typing.Optional[List[str]]  # [ "Multimode, 62.5um (M6)", "Multimode, 50um (M5, M5E)" ]
    fc_speeds: typing.Optional[str]  # "4|8|16 Gb/s"
    signaling_rate: str  # "14000 MBd"
    signaling_rate_max: typing.Optional[typing.Any]  # ??
    signaling_rate_min: typing.Optional[typing.Any]  # ??
    wavelength: str  # "850 nm"
    link_length: str  # "OM3: 100 m, OM4: 150 m"
    vendor_name: str  # "FS"
    vendor_oui: str  # "00-aB-21"
    vendor_part_number: str  # "QSFP-..."
    vendor_revision: typing.Optional[str]  # "A"
    vendor_serial_number: str  # "..."
    vendor_date_code: str  # "220310"
    temperature_thresholds: typing.Optional[PortThresholds]
    voltage_thresholds: typing.Optional[PortThresholds]
    tx_bias_thresholds: typing.Optional[PortThresholds]
    tx_power_thresholds: typing.Optional[PortThresholds]
    rx_power_thresholds: typing.Optional[PortThresholds]


@dataclasses.dataclass
class PortDetails:
    name: str
    static: PortDetailsStatic
    interface_type: str  # "eth"
    temperature: List[PortMetric]
    voltage: List[PortMetric]
    tx_bias: List[PortMetric]
    tx_power: List[PortMetric]
    rx_power: List[PortMetric]
    tx_fault: List[PortMetricFlag]
    rx_los: List[PortMetricFlag]

    def get_status(self) -> str:
        metrics = []
        metrics.extend(self.temperature)
        metrics.extend(self.voltage)
        metrics.extend(self.tx_bias)
        metrics.extend(self.tx_power)
        metrics.extend(self.rx_power)

        level = 0
        for metric in metrics:
            if metric.status == "unhealthy":
                if level < 1:
                    level = 1
            elif metric.status == "critical":
                if level < 2:
                    level = 2
        flags = []
        flags.extend(self.tx_fault)
        flags.extend(self.rx_los)
        for flag in flags:
            if flag.flag:
                level = 1
        if level == 0:
            return "ok"
        if level == 1:
            return "unhealthy"
        if level == 2:
            return "critical"
        return "unused"


@dataclasses.dataclass
class _PortDetailsRequest:
    continuation_token: typing.Optional[str] = None
    filter: typing.Optional[str] = None
    limit: int = 100
    offset: int = 0
    sort: typing.List[str] = None
    total_item_count: bool = False


@dataclasses.dataclass
class _PortDetailsResponse:
    more_items_remaining: bool = False
    total_item_count: int = 0
    continuation_token: typing.Optional[str] = None
    items: typing.Optional[List[PortDetails]] = None


@dataclasses.dataclass
class PortContainer:
    ports: List[PortDetails]

    def __init__(self, controllers: ControllersContainer):
        self.ports = []

        for controller in controllers.controllers:
            self.ports.append(PortDetails(
                name=f"{controller.name}.ETH10",
                static=PortDetailsStatic(
                    encoding="64B/66B",
                    identifier="QSFP+",
                    connector_type="MPO 1x12",
                    extended_identifier="Power Class 1 (1.5 W max.), No CDR in Tx, No CDR in Rx",
                    rate_identifier="No Rate Selection Support",
                    specifications=[
                        "40GBASE-SR4"
                    ],
                    fc_link_lengths=None,
                    fc_technology=None,
                    cable_technology=None,
                    fc_transmission_media = None,
                    fc_speeds = None,
                    signaling_rate="10300 MBd",
                    signaling_rate_max=None,
                    signaling_rate_min=None,
                    wavelength="850 nm",
                    link_length="OM3: 100 m, OM4: 150 m",
                    vendor_name="FS",
                    vendor_oui="00-1B-21",
                    vendor_part_number="QSFP-SR4-40G",
                    vendor_revision="A",
                    vendor_serial_number="F123456",
                    vendor_date_code="220310",
                    temperature_thresholds=PortThresholds(
                        alarm_low=-5.0,
                        warn_high=70.0,
                        alarm_high=75.0,
                        warn_low=0.0,
                    ),
                    voltage_thresholds=PortThresholds(
                        alarm_low=2.97,
                        warn_high=3.465,
                        alarm_high=3.63,
                        warn_low=3.135,
                    ),
                    tx_bias_thresholds=PortThresholds(
                        alarm_low=0.0,
                        warn_high=12.0,
                        alarm_high=15.0,
                        warn_low=2.0
                    ),
                    tx_power_thresholds=PortThresholds(
                        alarm_low=0.1122,
                        warn_high=1.5849,
                        alarm_high=1.9953,
                        warn_low=0.1778,
                    ),
                    rx_power_thresholds=PortThresholds(
                        alarm_low=0.0389,
                        warn_high=1.7378,
                        alarm_high=2.1878,
                        warn_low=0.0776
                    )
                ),
                interface_type="eth",
                temperature=[
                    PortMetric(
                        channel=None,
                        status="ok",
                        measurement=36.1234,
                    )
                ],
                voltage=[
                    PortMetric(
                        channel=None,
                        status="ok",
                        measurement=3.2654
                    )
                ],
                tx_bias=[
                    PortMetric(
                        channel=1,
                        status="ok",
                        measurement=6.96
                    ),
                    PortMetric(
                        channel=2,
                        status="ok",
                        measurement=7.2
                    ),
                    PortMetric(
                        channel=3,
                        status="ok",
                        measurement=6.8
                    ),
                    PortMetric(
                        channel=4,
                        status="ok",
                        measurement=6.82
                    ),
                ],
                tx_power=[
                    PortMetric(
                        channel=1,
                        status="ok",
                        measurement=0.9765
                    ),
                    PortMetric(
                        channel=2,
                        status="ok",
                        measurement=0.8352
                    ),
                    PortMetric(
                        channel=3,
                        status="ok",
                        measurement=0.888
                    ),
                    PortMetric(
                        channel=4,
                        status="ok",
                        measurement=0.7926
                    ),
                ],
                rx_power=[
                    PortMetric(
                        channel=1,
                        status="ok",
                        measurement=1.07
                    ),
                    PortMetric(
                        channel=2,
                        status="ok",
                        measurement=1.143
                    ),
                    PortMetric(
                        channel=3,
                        status="ok",
                        measurement=1.05
                    ),
                    PortMetric(
                        channel=4,
                        status="ok",
                        measurement=1.03
                    ),
                ],
                tx_fault=[
                    PortMetricFlag(
                        channel=1,
                        flag=False
                    ),
                    PortMetricFlag(
                        channel=2,
                        flag=False
                    ),
                    PortMetricFlag(
                        channel=3,
                        flag=False
                    ),
                    PortMetricFlag(
                        channel=4,
                        flag=False
                    )
                ],
                rx_los = [
                    PortMetricFlag(
                        channel=1,
                        flag=False
                    ),
                    PortMetricFlag(
                        channel=2,
                        flag=False
                    ),
                    PortMetricFlag(
                        channel=3,
                        flag=False
                    ),
                    PortMetricFlag(
                        channel=4,
                        flag=False
                    )
                ]
            ))
            self.ports.append(
                PortDetails(
                    name=f"{controller.name}.FC1",
                    static=PortDetailsStatic(
                        encoding="64B/66B",
                        identifier="SFP",
                        connector_type="LC",
                        extended_identifier="GBIC/SFP function is defined by 2-wire interface ID only",
                        rate_identifier="FC-PI-5 (16/8/4G Independent Rx, Tx Rate_select)",
                        specifications=None,
                        fc_link_lengths=[
                            "short distance (S)",
                            "intermediate distance (I)"
                        ],
                        fc_technology=[
                            "Shortwave laser w/o OFC (SN)"
                        ],
                        cable_technology=None,
                        fc_transmission_media=[
                            "Multimode, 62.5um (M6)",
                            "Multimode, 50um (M5, M5E)"
                        ],
                        fc_speeds="4|8|16 Gb/s",
                        signaling_rate="14000 MBd",
                        signaling_rate_max=None,
                        signaling_rate_min=None,
                        wavelength="850 nm",
                        link_length="OM2: 40 m, OM1: 20 m, OM3: 100 m",
                        vendor_name="EMULEX",
                        vendor_oui="00-17-6A",
                        vendor_part_number="AFBR-57F5MZ-ELX",
                        vendor_revision=None,
                        vendor_serial_number="AD12345",
                        vendor_date_code="210613",
                        temperature_thresholds=PortThresholds(
                            alarm_low=-5.0,
                            warn_high=80.0,
                            alarm_high=80.0,
                            warn_low=0.0,
                        ),
                        voltage_thresholds=PortThresholds(
                            alarm_low=3.0,
                            warn_high=3.45,
                            alarm_high=3.6,
                            warn_low=3.13,
                        ),
                        tx_bias_thresholds=PortThresholds(
                            alarm_low=2.5,
                            warn_high=10.5,
                            alarm_high=10.5,
                            warn_low=2.5,
                        ),
                        tx_power_thresholds=PortThresholds(
                            alarm_low=0.126,
                            warn_high=0.79,
                            alarm_high=2.0,
                            warn_low=0.317,
                        ),
                        rx_power_thresholds=PortThresholds(
                            alarm_low=0.03,
                            warn_high=2.0,
                            alarm_high=2.0,
                            warn_low=0.031
                        )
                    ),
                    interface_type="fc",
                    temperature=[
                        PortMetric(
                            channel=None,
                            status="ok",
                            measurement=44.0,
                        ),
                    ],
                    voltage=[
                        PortMetric(
                            channel=None,
                            status="ok",
                            measurement=3.3
                        )
                    ],
                    tx_bias=[
                        PortMetric(
                            channel=None,
                            status="ok",
                            measurement=7.25
                        )
                    ],
                    tx_power=[PortMetric(
                        channel=None,
                        status="ok",
                        measurement=0.5
                    )],
                    rx_power=[PortMetric(
                        channel=None,
                        status="ok",
                        measurement=0.49
                    )],
                    tx_fault=[PortMetricFlag(
                        channel=None,
                        flag=False,
                    )],
                    rx_los=[PortMetricFlag(
                        channel=None,
                        flag=False,
                    )]
                )
            )


class _PortDetailsRoute(_AuthenticatedJSONRoute):
    _container: PortContainer
    path = re.compile("^/api/2.21/network-interfaces/port-details$")

    def __init__(self, port_container: PortContainer, auth_token_storage: _AuthTokenStorage):
        super().__init__(auth_token_storage)
        self._container = port_container
        self._continuation_token_container = _ContinuationTokenContainer[PortDetails]()

    def handle_json(self, req: _JSONRequest) -> Response | _JSONResponse:
        query = _PortDetailsRequest()
        req.query_to_dataclass(query)

        if query.sort is not None:
            return Response(
                400,
                {},
                "The sort parameter is not supported by the mock.".encode('ascii')
            )
        if query.filter is not None:
            return Response(
                400,
                {},
                "The filter parameter is not supported by the mock.".encode('ascii')
            )

        if query.continuation_token:
            items, remaining_items, total = self._continuation_token_container.get(
                query.continuation_token,
                query.limit,
                query.offset
            )
            if len(remaining_items) > 0:
                continuation_token = query.continuation_token
            else:
                continuation_token = None
        else:
            continuation_token, items, remaining_items, total = self._continuation_token_container.create(
                self._container.ports, None, query.limit, query.offset
            )

        return _JSONResponse(
            body=_PortDetailsResponse(
                continuation_token=continuation_token,
                total_item_count=len(self._container.ports),
                items=items
            )
        )
