# Copyright 2019 Tecnativa - Sergio Teruel
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from openupgradelib import openupgrade


@openupgrade.migrate(use_env=False)
def migrate(cr, version):
    openupgrade.load_data(cr, 'website_sale_wishlist',
                          'migrations/12.0.1.0/noupdate_changes.xml')
