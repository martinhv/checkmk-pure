import re

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.special_agents.common import RulespecGroupDatasourceProgramsHardware
from cmk.gui.plugins.wato.utils import HostRulespec
from cmk.gui.valuespec import (Dictionary, PasswordSpec, Checkbox, TextAreaUnicode, ValueSpec, NetworkPort, Integer,
                               Age, Percentage, ListOf, Tuple, TextInput)
from cmk.gui.watolib.rulespecs import RulespecRegistry
from purestorage_checkmk.flashblade.common import default_cert_warn, default_cert_crit, default_closed_alerts_lifetime, \
    default_array_space_warn, default_array_space_crit, default_filesystem_space_warn, default_filesystem_space_crit, \
    default_objectstore_space_warn, default_objectstore_space_crit


def _valuespec_special_agents_purestorage_flashblade() -> ValueSpec:
    """
    This function produces the form fields required for the special agent configuration.
    """
    # noinspection HttpUrlsUsage
    return Dictionary(
        title=_("Pure Storage FlashBlade"),
        optional_keys=False,
        render="form_part",
        elements=[
            ("apitoken", PasswordSpec(
                title=_("API token"),
                allow_empty=False,
                help="""
                    For details, see 
                    “<a href=\"https://support.purestorage.com/FlashBlade/Purity_FB/PurityFB_REST_API/Management_REST_API/FlashBlade_REST_API_FAQ#Ways_to_access_the_FlashBlade_REST_API\">Creating an API token</a>”
                    in the FlashBlade User Guide.
                    """,
            )),
            ("verifytls", Checkbox(
                title=_("TLS certificate verification"),
                label=_("verify that the connection to the FlashBlade is secure (strongly recommended)"),
                default_value=True,
                help="Enable TLS certificate verification. If no certificate is provided below, the Checkmk server must trust the certificate of the FlashBlade.",
            )),
            ("cert", TextAreaUnicode(
                title=_("TLS certificate"),
                allow_empty=True,
                autocomplete=False,
                regex=re.compile(
                    '-----BEGIN CERTIFICATE-----\\n.*?\\n-----END CERTIFICATE-----',
                    re.DOTALL
                ),
                cols=80,
                regex_error="This doesn't look like a certificate in PEM format. It should contain a section with BEGIN CERTIFICATE / END CERTIFICATE.",
                help="Provide a CA or server TLS certificate for the FlashBlade in PEM format."
            )),
            ("port", NetworkPort(
                title=_("Port"),
                default_value=443
            )),
            ("certificates", Dictionary(
                title=_("Certificate expiration checks"),
                elements=[
                    ("days_warn", Integer(
                        title=_(f"Custom warning threshold (default: {default_cert_warn} days)"),
                        default_value=default_cert_warn,
                        unit="days",
                        label="Warn if the certificate expires in less than",
                        minvalue=1,
                        help="If the certificate of the array expires in less than the specified number of days, Checkmk will issue a warning.",
                    )),
                    ("days_crit", Integer(
                        title=_(f"Custom critical threshold (default: {default_cert_crit} days)"),
                        default_value=default_cert_crit,
                        unit="days",
                        label="Critical if the certificate expires in less than",
                        minvalue=1,
                        help="If the certificate of the array expires in less than the specified number of days, Checkmk will issue a critical alert.",
                    ))
                ],
                help=_(
                    "Certificate checks report the number of days remaining until the certificate expires. You can customize the reporting thresholds here."
                )
            )),
            ("hardware", ListOf(
                title=_("Hardware service name customization"),
                valuespec=Tuple(
                    elements=[
                        TextInput(label="API hardware type:"),
                        TextInput(label="Service name prefix:"),
                        TextInput(label="Service name suffix:")
                    ],
                ),
                help=_(
                    "Customize the reported hardware services by adding a prefix or a suffix to specific hardware types based on their reported hardware type in the API."
                )
            )),
            ("space", Dictionary(
                title=_("Disk space checks"),
                elements=[
                    ("array_used_warn", Percentage(
                        title=_(f"Custom warning threshold for arrays (default: {default_array_space_warn}%)"),
                        default_value=default_array_space_warn,
                        unit="% full",
                        label="Warn if the array is",
                        help="If the array is more than the specified percentage full, Checkmk will issue a warning.",
                    )),
                    ("array_used_crit", Percentage(
                        title=_(f"Custom critical threshold for arrays (default: {default_array_space_crit}%)"),
                        default_value=default_array_space_crit,
                        unit="% full",
                        label="Critical if the array is",
                        help="If the array is more than the specified percentage full, Checkmk will issue a critical alert.",
                    )),
                    ("filesystem_used_warn", Percentage(
                        title=_(
                            f"Custom warning threshold for filesystems (default: {default_filesystem_space_warn}%)"),
                        default_value=default_filesystem_space_warn,
                        unit="% full",
                        label="Warn if the filesystem is",
                        help="If the filesystem is more than the specified percentage full, Checkmk will issue a warning.",
                    )),
                    ("filesystem_used_crit", Percentage(
                        title=_(
                            f"Custom critical threshold for filesystems (default: {default_filesystem_space_crit}%)"),
                        default_value=default_filesystem_space_crit,
                        unit="% full",
                        label="Critical if the filesystem is",
                        help="If the filesystem is more than the specified percentage full, Checkmk will issue a critical alert.",
                    )),
                    ("filesystem_used_warn", Percentage(
                        title=_(
                            f"Custom warning threshold for object store (default: {default_objectstore_space_warn}%)"),
                        default_value=default_objectstore_space_warn,
                        unit="% full",
                        label="Warn if the object store is",
                        help="If the object store is more than the specified percentage full, Checkmk will issue a warning.",
                    )),
                    ("objectstore_used_crit", Percentage(
                        title=_(
                            f"Custom critical threshold for object store (default: {default_objectstore_space_crit}%)"),
                        default_value=default_objectstore_space_crit,
                        unit="% full",
                        label="Critical if the object store is",
                        help="If the object store is more than the specified percentage full, Checkmk will issue a critical alert.",
                    )),
                ],
                help=_(
                    "Disk space checks report the percentage of disk space filled. You can customize the reporting thresholds here.")
            )),
            ("alerts", Dictionary(
                title=_("Report alerts as temporary services"),
                optional_keys=False,
                elements=[
                    ("closed_alerts_lifetime", Age(
                        display=["minutes"],
                        default_value=default_closed_alerts_lifetime,
                        minvalue=0,
                        title="Once the alert is closed, keep the service for",
                        help=_(
                            "This plugin can create a temporary service for each alert the FlashBlade issues. You can use this in combination with frequent automatic service discovery to create notifications for FlashArray alerts. Keeping the service in OK status after the alert is closed allows you to send out OK notifications. Make sure this interval is larger than your service discovery interval."
                        )
                    )),
                    ("severities", Dictionary(
                        title="Report the following alert severities:",
                        render="form_part",
                        indent=False,
                        elements=[
                            ("info", Checkbox(
                                title="info",
                                default_value=True,
                            )),
                            ("warning", Checkbox(
                                title="warning",
                                default_value=True,
                            )),
                            ("critical", Checkbox(
                                title="critical",
                                default_value=True,
                            )),
                        ],
                        required_keys=["info", "warning", "critical"],
                    )),
                ]
            )),
        ],
        show_more_keys=[
            "port",
            "certificates",
            "alerts",
            "space",
            "hardware"
        ]
    )


def init(rulespec_registry: RulespecRegistry):
    rulespec_registry.register(
        HostRulespec(
            group=RulespecGroupDatasourceProgramsHardware,
            name="special_agents:purestorage_flashblade",
            valuespec=_valuespec_special_agents_purestorage_flashblade,
        ))
