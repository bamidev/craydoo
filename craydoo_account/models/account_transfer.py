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

    `is_linked` means this transfer is linked to the one immediately before
    it by `id` (the two were posted together as one atomic unit, e.g. two
    legs of one invoice) - so chains only ever reference adjacent ids, with
    no explicit foreign key. That only holds up if nothing else can insert
    a row in between while a multi-transfer batch is being created, which
    is why `create` takes a table lock for the rest of the transaction
    before inserting anything.
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
    contact_source_id = fields.Many2one('cd.contact.info', readonly=True, index=True)

    is_linked = fields.Boolean(default=False, readonly=True)
    linked_ids = fields.Many2many('cd.account.transfer', compute='_compute_linked_ids')

    debit_reconcile_part_ids = fields.One2many('cd.account.reconcile.part', 'debit_transfer_id')
    credit_reconcile_part_ids = fields.One2many('cd.account.reconcile.part', 'credit_transfer_id')
    reconciled_amount = fields.Integer(compute='_compute_residual_amount', store=True)
    residual_amount = fields.Integer(compute='_compute_residual_amount', store=True)

    @api.depends(
        'amount', 'debit_reconcile_part_ids.amount', 'credit_reconcile_part_ids.amount')
    def _compute_residual_amount(self):
        for transfer in self:
            reconciled = (
                sum(transfer.debit_reconcile_part_ids.mapped('amount'))
                + sum(transfer.credit_reconcile_part_ids.mapped('amount')))
            transfer.reconciled_amount = reconciled
            transfer.residual_amount = transfer.amount - reconciled

    @api.depends('is_linked')
    def _compute_linked_ids(self):
        for transfer in self:
            linked = self.env['cd.account.transfer']

            cur = transfer
            while cur.is_linked:
                cur = self.browse(cur.id - 1)
                if not cur.exists():
                    break
                linked |= cur

            cur = transfer
            while True:
                nxt = self.browse(cur.id + 1)
                if not (nxt.exists() and nxt.is_linked):
                    break
                linked |= nxt
                cur = nxt

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
        # Held until this transaction commits/rolls back, so every create()
        # within it - even across several separate calls - sees a table no
        # one else is concurrently inserting into, keeping `is_linked`'s
        # "previous id" assumption valid for the whole batch.
        self.env.cr.execute(SQL("LOCK TABLE cd_account_transfer IN EXCLUSIVE MODE"))

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
