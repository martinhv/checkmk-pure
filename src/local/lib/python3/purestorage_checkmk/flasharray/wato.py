import re

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.special_agents.common import RulespecGroupDatasourceProgramsHardware
from cmk.gui.plugins.wato.utils import HostRulespec
from cmk.gui.utils.html import HTML
from cmk.gui.valuespec import (Dictionary, PasswordSpec, Checkbox, TextAreaUnicode, ValueSpec, NetworkPort, Percentage,
                               Integer, Age, ListOf, TextInput, Tuple)
from cmk.gui.watolib.rulespecs import RulespecRegistry
from purestorage_checkmk.flasharray.common import default_array_crit, default_array_warn, default_cert_warn, \
    default_cert_crit, default_closed_alerts_lifetime


def _valuespec_special_agents_purestorage_flasharray() -> ValueSpec:
    """
    This function produces the form fields required for the special agent configuration.
    """
    return Dictionary(
        title=_("Pure Storage FlashArray"),
        optional_keys=["alerts"],
        render="form_part",
        help="This section configures the credentials for your FlashArray.",
        elements=[
            ("apitoken", PasswordSpec(
                title=_("API token"),
                allow_empty=False,
                help="""
                    For details, see the
                    “<a href=\"https://support.purestorage.com/FlashArray/PurityFA/Purity_FA_REST_API/REST_API_-_Quick_Setup_Guide\">FlashArray REST API Quick Setup Guide</a>”.
                    """,
            )),
            ("verifytls", Checkbox(
                title=_("Verify TLS certificate"),
                label=_("verify that the connection to the FlashArray is secure (strongly recommended)"),
                default_value=True,
                help="If this option is turned off, an attacker can perform a Man-in-the-Middle (MITM) attack and obtain your FlashArray API tokens.",
            )),
            ("cert", TextAreaUnicode(
                title=_("TLS certificate"),
                allow_empty=True,
                regex=re.compile(
                    '-----BEGIN CERTIFICATE-----\\n.*?\\n-----END CERTIFICATE-----',
                    re.DOTALL
                ),
                cols=80,
                regex_error="This doesn't look like a certificate in PEM format. It should contain a section with BEGIN CERTIFICATE / END CERTIFICATE.",
                help=HTML("""
                Provide a CA or server TLS certificate for the FlashArray in PEM format. It should look like this:<br/><br />
                <code>-----BEGIN CERTIFICATE-----<br />
                MIID...<br />
                -----END CERTIFICATE-----</code><br /><br />
                You can obtain the certificate of a FlashArray by running this command on a Linux machine:<br /><br />
                <code>openssl s_client -connect ip-of-your-flash-array:443</code>
                """)
            )),
            ("port", NetworkPort(
                title=_("Port"),
                default_value=443,
                help=_(
                    "You can change the port number Checkmk connects the FlashArray on. This is normally not necessary, but may be helpful when using an SSH tunnel or a reverse proxy. For best results, make sure the check runs against the FlashArray directly."
                )
            )),
            ("array", Dictionary(
                title=_("Array checks"),
                elements=[
                    ("used_warn", Percentage(
                        title=_(f"Custom warning threshold (default: {default_array_warn}%)"),
                        default_value=default_array_warn,
                        unit="% full",
                        label="Warn if the array is",
                        help="If the array is more than the specified percentage full, Checkmk will issue a warning.",
                    )),
                    ("used_crit", Percentage(
                        title=_(f"Custom critical threshold (default: {default_array_crit}%)"),
                        default_value=default_array_crit,
                        unit="% full",
                        label="Critical if the array is",
                        help="If the array is more than the specified percentage full, Checkmk will issue a critical alert.",
                    )),
                ],
                help=_(
                    "Array checks report the percentage of disk space filled. You can customize the reporting thresholds here.")
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
                            "This plugin can create a temporary service for each alert the FlashArray issues. You can use this in combination with frequent automatic service discovery to create notifications for FlashArray alerts. Keeping the service in OK status after the alert is closed allows you to send out OK notifications. Make sure this interval is larger than your service discovery interval."
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
                            ("hidden", Checkbox(
                                title="hidden",
                                default_value=True,
                            )),
                        ],
                        required_keys=["info", "warning", "critical", "hidden"],
                    )),
                ]
            )),
        ],
        show_more_keys=[
            "port",
            "array",
            "certificates",
            "alerts",
            "hardware"
        ],
    )


def init(rulespec_registry: RulespecRegistry):
    rulespec_registry.register(
        HostRulespec(
            group=RulespecGroupDatasourceProgramsHardware,
            name="special_agents:purestorage_flasharray",
            valuespec=_valuespec_special_agents_purestorage_flasharray,
        ))
