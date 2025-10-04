# Copyright 2024 Viindoo Technology Joint Stock Company (Viindoo)
# Copyright 2024 Hunki enterprises - Holger Brunn
# Copyright 2024,2025 Tecnativa - Pedro M. Baeza
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from openupgradelib import openupgrade

_deleted_xml_records = ["analytic.analytic_plan_comp_rule"]


def _adjust_analytic_plan_sequence(env):
    """As now the order is by sequence, and on v16 it was the id, we have to assign the
    sequence numbers to preserve the previous order by default, for not having any
    undesired modification. Once in v17, you can redefine the order to your
    choice if desired.
    """
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE account_analytic_plan aap
        SET sequence = sub.row_number
        FROM (
            SELECT id, row_number()
            OVER (PARTITION BY True order by id)
            FROM account_analytic_plan
        ) as sub
        WHERE sub.id = aap.id
        """,
    )


def _analytic_line_create_x_plan_column(env):
    """
    This method set system parameter for project analytic plan
    and create dynamic field on analytic items using
    '_sync_plan_column' method
    """
    project_plan = env["ir.config_parameter"].get_param("analytic.project_plan", False)
    plans_to_create_fields = env["account.analytic.plan"].search(
        [("id", "!=", int(project_plan))]
    )
    plans_to_create_fields._sync_plan_column()
    for plan in plans_to_create_fields:
        if plan.parent_id:
            continue
        column = plan._strict_column_name()
        openupgrade.logged_query(
            env.cr,
            f"""
            UPDATE account_analytic_line
            SET {column} = account_id,
                account_id = NULL
            WHERE plan_id = {plan.id};
            """,
        )


def _analytic_plan_update_applicability_into_property(env):
    """
    Create ir.property for default_applicability of account.analytic.plan
    in all companies as the company_id field was shifted from account.analytic.plan
    to account.analytic.applicability
    """
    openupgrade.convert_to_company_dependent(
        env,
        "account.analytic.plan",
        openupgrade.get_legacy_name("default_applicability"),
        "default_applicability",
    )


@openupgrade.migrate()
def migrate(env, version):
    _adjust_analytic_plan_sequence(env)
    openupgrade.load_data(env, "analytic", "17.0.1.2/noupdate_changes.xml")
    openupgrade.delete_records_safely_by_xml_id(
        env,
        _deleted_xml_records,
    )
    _analytic_line_create_x_plan_column(env)
    _analytic_plan_update_applicability_into_property(env)
