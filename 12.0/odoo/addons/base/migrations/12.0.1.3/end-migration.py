# © 2018 Opener B.V. (stefan@opener.amsterdam)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from openupgradelib import openupgrade, openupgrade_merge_records


def update_model_terms_translations(env):
    """ Adapt to changes in https://github.com/odoo/odoo/pull/26925, that
    introduces a separate translation type for xml structured fields. First,
    deduplicate existing model translations with new model_terms translations
    that were loaded during the migration. """
    openupgrade.logged_query(
        env.cr, """ DELETE FROM ir_translation WHERE id IN (
        SELECT it2.id FROM ir_translation it1
        JOIN ir_translation it2 ON it1.type in ('model', 'model_terms')
            AND it2.type in ('model', 'model_terms')
            AND it1.name = it2.name
            AND it1.res_id = it2.res_id
            AND it1.lang = it2.lang
            AND it1.id < it2.id); """)
    names = []
    for rec in env['ir.model.fields'].search([('translate', '=', True)]):
        try:
            field = env[rec.model]._fields[rec.name]
        except KeyError:
            continue
        if callable(field.translate):
            names.append('%s,%s' % (rec.model, rec.name))
    if names:
        openupgrade.logged_query(
            env.cr,
            """ UPDATE ir_translation
            SET type = 'model_terms'
            WHERE type = 'model' AND name IN %s """,
            (tuple(names),))


def fork_off_system_user(env):
    """ Fork user admin off from user system. User admin keeps the original
    partner, and user system gets a new partner. """
    user_root = env.ref('base.user_root')
    partner_admin = env.ref('base.partner_admin')
    partner_root = env.ref('base.partner_admin').copy({'name': 'System'})
    login = user_root.login
    user_root.login = '__system__'
    user_admin = env.ref('base.user_root').copy({
        'partner_id': partner_admin.id,
        'login': login,
    })
    # copy old passwords for not losing them on new admin user
    crypt = openupgrade.column_exists(env.cr, 'res_users', 'password_crypt')
    set_query = "SET password = ru2.password "
    if crypt:
        set_query += ", password_crypt = ru2.password_crypt "
    env.cr.execute(
        "UPDATE res_users ru " + set_query +
        "FROM res_users ru2 WHERE ru2.id = %s AND ru.id = %s",
        (user_root.id, user_admin.id),
    )
    user_root.write({
        'partner_id': partner_root.id,
        'email': partner_admin.email,
    })
    partner_admin.email = 'root@example.com'
    env.cr.execute(
        """ UPDATE ir_model_data SET res_id = %s
        WHERE module = 'base' AND name = 'user_admin'""", (user_admin.id,))
    env.cr.execute(
        """ UPDATE ir_model_data SET res_id = %s
        WHERE module = 'base' AND name = 'partner_root'""", (partner_root.id,))
    openupgrade.logged_query(
        env.cr,
        """ UPDATE ir_model_data SET res_id = %(user_admin)s
        WHERE model = 'res.users' AND res_id = %(user_root)s
        AND (module != 'base' OR name != 'user_root') """,
        {'user_admin': user_admin.id, 'user_root': user_root.id})
    # Get create_uid and write_uid columns to ignore
    env.cr.execute(
        """ SELECT tc.table_name, kcu.column_name
            FROM information_schema.table_constraints AS tc
            JOIN information_schema.key_column_usage AS kcu
                ON tc.constraint_name = kcu.constraint_name
                AND tc.table_schema = kcu.table_schema
            JOIN information_schema.constraint_column_usage AS ccu
                ON ccu.constraint_name = tc.constraint_name
                AND ccu.table_schema = tc.table_schema
            WHERE constraint_type = 'FOREIGN KEY'
            AND ccu.table_name = 'res_users' and ccu.column_name = 'id'
            AND kcu.column_name IN ('create_uid', 'write_uid')
        """)
    exclude_columns = env.cr.fetchall() + [
        ('ir_cron', 'user_id'),
        ('queue_job', 'user_id'),
        ('res_groups_users_rel', 'uid'),
        ('res_company_users_rel', 'user_id'),
    ]

    openupgrade_merge_records.merge_records(
        env, 'res.users', [user_root.id], user_admin.id,
        method='sql', delete=False, exclude_columns=exclude_columns)
    # Circumvent ORM when setting root user inactive, because
    # "You cannot deactivate the user you're currently logged in as."
    set_query = "SET active = FALSE, password = NULL"
    if crypt:
        set_query += ", password_crypt = NULL"
    env.cr.execute(
        "UPDATE res_users " + set_query + " WHERE id = %s",
        (user_root.id, ),
    )
    # Ensure also partner_root is inactive
    env.cr.execute(
        """ UPDATE res_partner
            SET active = FALSE WHERE id = %s """,
        (partner_root.id,))


def fill_res_users_password_from_password_crypt(cr):
    openupgrade.logged_query(
        cr,
        """UPDATE res_users
        SET password = password_crypt
        WHERE password_crypt IS NOT NULL
        """,
    )


@openupgrade.migrate()
def migrate(env, version):
    openupgrade.disable_invalid_filters(env)
    update_model_terms_translations(env)
    fork_off_system_user(env)
    if openupgrade.column_exists(env.cr, 'res_users', 'password_crypt'):
        fill_res_users_password_from_password_crypt(env.cr)
