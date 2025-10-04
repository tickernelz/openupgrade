# Copyright 2021 ForgeFlow S.L.  <https://www.forgeflow.com>
# Copyright 2021 Tecnativa - Pedro M. Baeza
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from openupgradelib import openupgrade


def update_follow_recurrence_field(env):
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE calendar_event ce
        SET follow_recurrence = True
        WHERE recurrency = True
        """,
    )


def map_calendar_event_byday(env):
    openupgrade.map_values(
        env.cr,
        openupgrade.get_legacy_name("byday"),
        "byday",
        [("5", "-1")],
        table="calendar_event",
    )


def fill_calendar_recurrence_table(env):
    openupgrade.logged_query(
        env.cr,
        """
        WITH recur AS (
            INSERT INTO calendar_recurrence (base_event_id,
                event_tz,rrule,rrule_type,end_type,interval,count,
                mo,tu,we,th,fr,sa,su,month_by,day,weekday,byday,until,
                create_uid,create_date,write_uid,write_date)
            SELECT id,event_tz,rrule,rrule_type,end_type,interval,count,
                mo,tu,we,th,fr,sa,su,month_by,day,week_list,byday,final_date,
                create_uid,create_date,write_uid,write_date
            FROM calendar_event
            WHERE recurrency AND recurrence_id IS NULL
                AND (recurrent_id IS NULL OR recurrent_id = 0)
                AND (
                    rrule_type != 'weekly'
                    OR (
                        rrule_type = 'weekly' AND
                        (mo OR tu OR we OR th OR fr OR sa OR su)
                    )
                )
            RETURNING id,base_event_id
        )
        UPDATE calendar_event ce
        SET recurrence_id = recur.id
        FROM recur
        WHERE recur.base_event_id = ce.id
        """,
    )
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE calendar_event ce
        SET recurrence_id = ce2.recurrence_id, recurrency = True
        FROM calendar_event ce2
        WHERE ce.recurrence_id IS NULL AND ce.recurrent_id = ce2.id
        """,
    )


@openupgrade.logging()
def create_recurrent_events(env):
    """In v14, now all occurrences of recurrent events are created as real records, not
    virtual ones, so we need to regenerate them for all the existing ones.
    But we do not create an activity on the real records.
    """
    recs = env["calendar.recurrence"].search([("base_event_id", "!=", False)])
    env.cr.execute(
        """
        SELECT id, recurrent_id, recurrent_id_date
        FROM calendar_event
        WHERE recurrent_id > 0
        """
    )
    result = env.cr.fetchall()

    for recurrence in recs:
        duration = recurrence.base_event_id.stop - recurrence.base_event_id.start
        ranges = set(recurrence._get_ranges(recurrence.base_event_id.start, duration))
        # Remove range that contains start < event's start to avoid create past events
        for event_range in list(ranges):
            if event_range[0] <= recurrence.base_event_id.start:
                ranges.remove(event_range)
            else:
                break
        # Remove range that contains detach events
        for event_id, recurrent_id, recurrent_id_date in result:
            if recurrence.base_event_id.id == recurrent_id:
                result.remove((event_id, recurrent_id, recurrent_id_date))
                if (recurrent_id_date, recurrent_id_date + duration) in ranges:
                    ranges.remove((recurrent_id_date, recurrent_id_date + duration))

        values = {}
        for start, stop in ranges:
            values[(recurrence.id, start, stop)] = dict(
                start=start,
                stop=stop,
                recurrence_id=recurrence.id,
            )
        if values:
            recurrence.with_context(
                default_activity_ids=[(6, 0, [])]
            )._apply_recurrence(
                specific_values_creation=values,
            )


@openupgrade.migrate()
def migrate(env, version):
    update_follow_recurrence_field(env)
    map_calendar_event_byday(env)
    fill_calendar_recurrence_table(env)
    create_recurrent_events(env)
    openupgrade.load_data(env.cr, "calendar", "14.0.1.0/noupdate_changes.xml")
    openupgrade.delete_record_translations(
        env.cr,
        "calendar",
        [
            "calendar_template_meeting_changedate",
            "calendar_template_meeting_invitation",
            "calendar_template_meeting_reminder",
        ],
    )
