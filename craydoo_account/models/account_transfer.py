from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools import SQL

from ..fields import UInteger

TRANSFER_TYPES = [
    ('invoice', 'Invoice'),
]

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

    amount = UInteger(required=True, readonly=True)
    date = fields.Date(required=True, readonly=True, default=fields.Date.context_today)
    ledger_id = fields.Many2one('cd.account.ledger', required=True, readonly=True)
    type = fields.Selection(TRANSFER_TYPES, required=True, readonly=True)
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

    def _bump_fiscal_year_balance(self, account_id, year, field, amount):
        """ `sudo()` throughout - regular users can only read
        `cd.account.fiscal.year`/`cd.account.fiscal.year.account.balance`,
        but still need to be able to post invoices, which bumps them.
        """
        FiscalYear = self.env['cd.account.fiscal.year'].sudo()
        fiscal_year = FiscalYear.search([('year', '=', year)])
        if not fiscal_year:
            fiscal_year = FiscalYear.create({'year': year})

        Balance = self.env['cd.account.fiscal.year.account.balance'].sudo()
        balance = Balance.search([
            ('fiscal_year_id', '=', fiscal_year.id), ('account_id', '=', account_id),
        ])
        if not balance:
            balance = Balance.create({'fiscal_year_id': fiscal_year.id, 'account_id': account_id})
        balance[field] = balance[field] + amount

    @api.model_create_multi
    def create(self, vals_list):
        transfers = super().create(vals_list)
        for transfer in transfers:
            year = transfer.date.year
            self._bump_fiscal_year_balance(transfer.debit_account_id.id, year, 'debit_total', transfer.amount)
            self._bump_fiscal_year_balance(transfer.credit_account_id.id, year, 'credit_total', transfer.amount)
        return transfers

    def _auto_init(self):
        result = super()._auto_init()
        self.env.cr.execute(_IMMUTABLE_SQL)
        return result

    def write(self, vals):
        raise UserError(_("Accounting history cannot be changed."))

    def unlink(self):
        raise UserError(_("Accounting history cannot be deleted."))
