# Copyright 2025 Hunki Enterprises BV
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from openupgradelib import openupgrade


def discuss_channel_last_interest(env):
    """
    Set last interest date of channel from newest message posted
    """
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE discuss_channel
        SET last_interest_dt=mail_message.create_date
        FROM
        (
            SELECT res_id, max(create_date) create_date
            FROM mail_message
            WHERE model='discuss.channel'
            GROUP BY res_id
        ) mail_message
        WHERE mail_message.res_id=discuss_channel.id
        """,
    )


def discuss_channel_member_new_message_separator(env):
    """
    Set new_message_separator to the id of the first message after last_interest_id
    """
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE discuss_channel_member
        SET new_message_separator=COALESCE(mail_message.id, 0)
        FROM
        (
            SELECT res_id, min(mail_message.id) id
            FROM mail_message
            JOIN discuss_channel
            ON discuss_channel.id=mail_message.res_id
                AND mail_message.model='discuss.channel'
            JOIN discuss_channel_member
                ON discuss_channel_member.channel_id=discuss_channel.id
            WHERE
                mail_message.create_date >= discuss_channel_member.last_interest_dt
            GROUP BY mail_message.res_id
        ) mail_message
        WHERE
            discuss_channel_member.channel_id=mail_message.res_id
        """,
    )


def discuss_channel_member_unpin_dt(env):
    """
    Set to now if v17 is_pinned has been unset
    """
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE discuss_channel_member
        SET unpin_dt=CURRENT_TIMESTAMP
        WHERE not is_pinned
        """,
    )


@openupgrade.migrate()
def migrate(env, version):
    openupgrade.load_data(env, "mail", "18.0.1.18/noupdate_changes.xml")
    discuss_channel_last_interest(env)
    discuss_channel_member_new_message_separator(env)
    discuss_channel_member_unpin_dt(env)
