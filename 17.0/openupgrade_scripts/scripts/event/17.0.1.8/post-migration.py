# Copyright 2024-2025 Tecnativa - Víctor Martínez
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from openupgradelib import openupgrade

_deleted_xml_records = [
    "event.event_type_data_conference",
    "event.event_type_data_ticket",
]


@openupgrade.logging()
def _event_registration_barcode(env):
    """Assign a new barcode per record, as if not, Odoo assigns the same to old."""
    for record in env["event.registration"].search([]):
        record.barcode = record._get_random_barcode()


@openupgrade.migrate()
def migrate(env, version):
    openupgrade.load_data(env, "event", "17.0.1.8/noupdate_changes.xml")
    openupgrade.delete_record_translations(
        env.cr,
        "event",
        [
            "event_registration_mail_template_badge",
            "event_reminder",
            "event_subscription",
        ],
    )
    openupgrade.delete_records_safely_by_xml_id(
        env,
        _deleted_xml_records,
    )
    _event_registration_barcode(env)
    openupgrade.logged_query(env.cr, "UPDATE event_event_ticket SET sequence = id")
    openupgrade.logged_query(env.cr, "UPDATE event_type_ticket SET sequence = id")
