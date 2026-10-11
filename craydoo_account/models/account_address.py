from odoo import _, fields, models
from odoo.exceptions import UserError
from odoo.tools import SQL

_IMMUTABLE_SQL = SQL("""
    CREATE OR REPLACE FUNCTION cd_account_address_immutable()
    RETURNS trigger LANGUAGE plpgsql AS $$
    BEGIN
        RAISE EXCEPTION 'Invoice addresses cannot be changed';
    END;
    $$;
    DROP TRIGGER IF EXISTS cd_account_address_immutable ON cd_account_address;
    CREATE TRIGGER cd_account_address_immutable
        BEFORE UPDATE ON cd_account_address
        FOR EACH ROW EXECUTE FUNCTION cd_account_address_immutable();
""")


class AccountAddress(models.Model):
    """ Frozen snapshot of the subset of a `cd.contact.info`'s fields that
    are relevant to invoicing (shared with it via `cd.contact.address_mixin`
    from craydoo_contact, so the two stay structurally identical). Rows are
    interned by `cd.contact.info.get_address` - find-or-create on the full
    set of fields - so two invoices billed to the same address share one
    row; `_unique` backs that up at the database level. `source_id` records
    which contact the row was created from, but isn't part of that
    dedup key - two contacts that happen to share the exact same address
    details still intern to the same row.

    Only the *content* is immutable (blocked at the ORM level via `write`
    below, and as a backstop against anything that goes around the ORM, by
    a Postgres trigger in `_auto_init`) - unlike `cd.account.transfer`, a
    row can still be deleted once nothing references it any more; whatever
    eventually links to it is expected to do so with `ondelete='restrict'`,
    so deletion is blocked by that foreign key for as long as it's in use.
    """
    _name = 'cd.account.address'
    _description = 'Invoice Address'
    _inherit = ['cd.contact.address_mixin']

    source_id = fields.Many2one('cd.contact.info', readonly=True, index=True)

    _unique = models.Constraint(
        'UNIQUE (name, street, house, address_extra, city, zip, state_id, country_id)',
        'This address already exists.',
    )

    def _auto_init(self):
        result = super()._auto_init()
        self.env.cr.execute(_IMMUTABLE_SQL)
        return result

    def write(self, vals):
        raise UserError(_("Invoice addresses cannot be changed."))
