# Copyright 2024- Le Filament (https://le-filament.com)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from openupgradelib import openupgrade


@openupgrade.migrate()
def migrate(env, version):
    openupgrade.load_data(env, "hr_recruitment", "17.0.1.1/noupdate_changes.xml")
    openupgrade.delete_record_translations(
        env.cr, "hr_recruitment", ["applicant_hired_template"]
    )
    openupgrade.delete_records_safely_by_xml_id(
        env,
        [
            "hr_recruitment.mail_message_interviewer_rule",
            "hr_recruitment.mail_alias_jobs",
        ],
    )
