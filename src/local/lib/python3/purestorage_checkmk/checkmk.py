from cmk.base.api.agent_based import checking_classes, inventory_classes
from cmk.utils import pnp_cleanup as quote_pnp_string
from purestorage_checkmk.common import Result, Metric, Attributes, TableRow


def result_to_checkmk(result: Result) -> checking_classes.Result:
    """
    This function turns an internal result into a CheckMK structure.
    :param result: The internal structure.
    :return: A CheckMK result.
    """

    if result.summary is not None and result.summary != "":
        if result.details is None or result.details == "":
            return checking_classes.Result(
                state=checking_classes.State(result.state),
                summary=result.summary,
            )
        return checking_classes.Result(
            state=checking_classes.State(result.state),
            summary=result.summary,
            details=result.details,
        )
    if result.details is None or result.details == "":
        return checking_classes.Result(
            state=checking_classes.State(result.state),
            notice=result.notice
        )
    return checking_classes.Result(
        state=checking_classes.State(result.state),
        details=result.details,
        notice=result.notice
    )


def result_to_metric(name: str, metric: Metric) -> checking_classes.Metric:
    return checking_classes.Metric(
        name=quote_pnp_string(name),
        value=metric.value,
        levels=metric.levels,
        boundaries=metric.boundaries,
    )


def result_to_attributes(attributes: Attributes) -> inventory_classes.Attributes:
    return inventory_classes.Attributes(
        path=attributes.path,
        inventory_attributes=attributes.inventory_attributes,
        status_attributes=attributes.status_attributes,
    )


def result_to_table_row(table_row: TableRow) -> inventory_classes.TableRow:
    return inventory_classes.TableRow(
        path=table_row.path,
        key_columns=table_row.key_columns,
        inventory_columns=table_row.inventory_columns,
        status_columns=table_row.status_columns,
    )
