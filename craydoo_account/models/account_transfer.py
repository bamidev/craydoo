from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools import SQL

from ..fields import UInt128

_IMMUTABLE_SQL = SQL("""
    CREATE OR REPLACE FUNCTION cd_account_transfer_immutable()
    RETURNS trigger LANGUAGE plpgsql AS $$
    BEGIN
        IF TG_OP = 'DELETE' THEN
            RAISE EXCEPTION 'Accounting history cannot be deleted';
        ELSE
            RAISE EXCEPTION 'Accounting history cannot be changed';
        END IF;
    END;
    $$;
    DROP TRIGGER IF EXISTS cd_account_transfer_immutable ON cd_account_transfer;
    CREATE TRIGGER cd_account_transfer_immutable
        BEFORE UPDATE OR DELETE ON cd_account_transfer
        FOR EACH ROW EXECUTE FUNCTION cd_account_transfer_immutable();
""")


class AccountTransfer(models.Model):
    """ A posted double-entry transfer between two `cd.account.account`
    records. Immutable once created - a transfer is a historical fact, not
    something to revise after posting. Blocked at both the ORM level
    (`write`/`unlink` below) and, as a backstop against anything that goes
    around the ORM, by a Postgres trigger (`_auto_init`) that rejects every
    update/delete unconditionally.

    `backward_link_id`/`forward_link_ids` chain transfers that were posted
    together as one atomic unit (e.g. every line of one invoice), so the
    whole batch can still be walked as a group after the fact. `linked_ids`
    is the full chain in both directions, for display.
    """
    _name = 'cd.account.transfer'
    _description = 'Transfer'
    _order = 'id'

    ledger_id = fields.Many2one('cd.account.ledger', required=True, readonly=True)
    code = fields.Integer(required=True, readonly=True)
    amount = UInt128(required=True, readonly=True)
    debit_account_id = fields.Many2one(
        'cd.account.account', required=True, readonly=True, ondelete='restrict')
    credit_account_id = fields.Many2one(
        'cd.account.account', required=True, readonly=True, ondelete='restrict')

    backward_link_id = fields.Many2one(
        'cd.account.transfer', readonly=True, ondelete='restrict')
    forward_link_ids = fields.One2many(
        'cd.account.transfer', 'backward_link_id', readonly=True)
    linked_ids = fields.Many2many('cd.account.transfer', compute='_compute_linked_ids')

    @api.depends('backward_link_id', 'forward_link_ids')
    def _compute_linked_ids(self):
        for transfer in self:
            linked = self.env['cd.account.transfer']
            cur = transfer.backward_link_id
            while cur:
                linked |= cur
                cur = cur.backward_link_id
            cur = transfer.forward_link_ids
            while cur:
                linked |= cur
                cur = cur.forward_link_ids
            transfer.linked_ids = linked

    def _auto_init(self):
        result = super()._auto_init()
        self.env.cr.execute(_IMMUTABLE_SQL)
        return result

    def write(self, vals):
        raise UserError(_("Accounting history cannot be changed."))

    def unlink(self):
        raise UserError(_("Accounting history cannot be deleted."))
