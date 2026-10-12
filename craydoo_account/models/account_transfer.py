from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools import SQL

from ..fields import UInteger

TRANSFER_TYPES = [
    ('invoice', 'Invoice'),
]


def _immutable_sql(table):
    """ A trigger that unconditionally rejects UPDATE/DELETE on `table` -
    shared by every transfer-related table that needs to be immutable once
    created, as a backstop against anything that goes around the ORM.
    `table` is always one of this module's own hardcoded table names, never
    external input, so plain string formatting is fine here.
    """
    function = f'{table}_immutable'
    return SQL(f"""
        CREATE OR REPLACE FUNCTION {function}()
        RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            IF TG_OP = 'DELETE' THEN
                RAISE EXCEPTION 'Accounting history cannot be deleted';
            ELSE
                RAISE EXCEPTION 'Accounting history cannot be changed';
            END IF;
        END;
        $$;
        DROP TRIGGER IF EXISTS {function} ON {table};
        CREATE TRIGGER {function}
            BEFORE UPDATE OR DELETE ON {table}
            FOR EACH ROW EXECUTE FUNCTION {function}();
    """)


class AccountTransfer(models.Model):
    """ One leg of a double-entry transfer between two `cd.account.account`
    records. Immutable once created - a transfer is a historical fact, not
    something to revise after posting. Blocked at both the ORM level
    (`write`/`unlink` below) and, as a backstop against anything that goes
    around the ORM, by a Postgres trigger (`_auto_init`) that rejects every
    update/delete unconditionally.

    Its amount lives on a separate record, not here, because the amount
    isn't always known for sure in the ledger's own currency yet when the
    transfer itself is created:
    - `cd.account.transfer.posted` holds the final, immutable amount, in
      the ledger's own currency.
    - `cd.account.transfer.pending` holds a mutable amount in some other
      currency (e.g. an invoice issued in a currency other than its
      ledger's), until it gets reconciled and its `posted` counterpart can
      be created - see `cd.account.transfer.pending._action_post`.
    A transfer is created with exactly one of the two (`posted_id`/
    `pending_id` below); `pending` can later turn into `posted`, but never
    the other way around.
    """
    _name = 'cd.account.transfer'
    _description = 'Transfer'
    _order = 'id'

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

    posted_id = fields.One2many('cd.account.transfer.posted', 'transfer_id')
    pending_id = fields.One2many('cd.account.transfer.pending', 'transfer_id')

    debit_reconcile_part_ids = fields.One2many('cd.account.reconcile.part', 'debit_transfer_id')
    credit_reconcile_part_ids = fields.One2many('cd.account.reconcile.part', 'credit_transfer_id')
    reconciled_amount = fields.Integer(compute='_compute_residual_amount', store=True)
    residual_amount = fields.Integer(compute='_compute_residual_amount', store=True)

    def _auto_init(self):
        result = super()._auto_init()
        self.env.cr.execute(_immutable_sql(self._table))
        return result

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

    @api.depends(
        'posted_id.amount', 'debit_reconcile_part_ids.amount', 'credit_reconcile_part_ids.amount')
    def _compute_residual_amount(self):
        for transfer in self:
            reconciled = (
                sum(transfer.debit_reconcile_part_ids.mapped('amount'))
                + sum(transfer.credit_reconcile_part_ids.mapped('amount')))
            transfer.reconciled_amount = reconciled
            transfer.residual_amount = sum(transfer.posted_id.mapped('amount')) - reconciled

    @api.model_create_multi
    def create(self, vals_list):
        # Held until this transaction commits/rolls back, so every create()
        # within it - even across several separate calls - sees a table no
        # one else is concurrently inserting into, keeping `is_linked`'s
        # "previous id" assumption valid for the whole batch.
        self.env.cr.execute(SQL("LOCK TABLE cd_account_transfer IN EXCLUSIVE MODE"))
        return super().create(vals_list)

    def unlink(self):
        raise UserError(_("Accounting history cannot be deleted."))

    def write(self, vals):
        raise UserError(_("Accounting history cannot be changed."))


class AccountTransferPosted(models.Model):
    """ The final, immutable amount of a `cd.account.transfer`, in the
    ledger's own currency. Bumps the fiscal year balance at the moment it's
    created, since that's the moment the transfer's amount actually
    becomes part of the books.
    """
    _name = 'cd.account.transfer.posted'
    _description = 'Posted Transfer Amount'

    transfer_id = fields.Many2one(
        'cd.account.transfer', required=True, readonly=True, ondelete='cascade', index=True)
    amount = UInteger(required=True, readonly=True)

    def _auto_init(self):
        result = super()._auto_init()
        self.env.cr.execute(_immutable_sql(self._table))
        return result

    @api.model_create_multi
    def create(self, vals_list):
        posted = super().create(vals_list)
        for rec in posted:
            transfer = rec.transfer_id
            year = transfer.date.year
            transfer._bump_fiscal_year_balance(
                transfer.debit_account_id.id, year, 'debit_total', rec.amount)
            transfer._bump_fiscal_year_balance(
                transfer.credit_account_id.id, year, 'credit_total', rec.amount)
        return posted

    def unlink(self):
        raise UserError(_("Accounting history cannot be deleted."))

    def write(self, vals):
        raise UserError(_("Accounting history cannot be changed."))


class AccountTransferPending(models.Model):
    """ A `cd.account.transfer` leg whose amount is only known in some
    currency other than its ledger's so far - mutable, since there's
    nothing final about it yet. `posted_id` gets set once this pending
    amount is converted to its transfer's ledger currency and posted
    (currently: when it gets reconciled, via `_action_post`); `active` is
    computed off it, so posted-away records quietly drop out of the
    default views/domains while still being kept around as a record of
    what the original, pre-conversion amount was.
    """
    _name = 'cd.account.transfer.pending'
    _description = 'Pending Transfer Amount'

    transfer_id = fields.Many2one(
        'cd.account.transfer', required=True, readonly=True, ondelete='cascade', index=True)
    amount = UInteger(required=True)
    currency_id = fields.Many2one('res.currency', required=True)
    posted_id = fields.Many2one('cd.account.transfer.posted', readonly=True, copy=False)
    active = fields.Boolean(compute='_compute_active', store=True)

    def _action_post(self):
        for rec in self:
            if rec.posted_id:
                continue
            posted = self.env['cd.account.transfer.posted'].create({
                'transfer_id': rec.transfer_id.id,
                'amount': rec._ledger_amount(),
            })
            rec.posted_id = posted.id

    @api.depends('posted_id')
    def _compute_active(self):
        for rec in self:
            rec.active = not rec.posted_id

    def _ledger_amount(self):
        """ This pending amount converted to its transfer's ledger
        currency at today's rate - the amount it would be posted at if it
        got reconciled right now.
        """
        self.ensure_one()
        ledger_currency = self.transfer_id.ledger_id.currency_id
        converted = self.currency_id._convert(
            self.amount / 10 ** self.currency_id.decimal_places,
            ledger_currency, self.env.company, fields.Date.context_today(self))
        return round(converted * 10 ** ledger_currency.decimal_places)


class AccountTransferDraft(models.Model):
    """ An account transfer draft.
    """
    _name = 'cd.account.transfer.draft'
    _description = 'Draft Transfer'

    date = fields.Date(required=True, default=fields.Date.context_today)
    ledger_id = fields.Many2one('cd.account.ledger', required=True)
    type = fields.Selection(TRANSFER_TYPES, required=True)
    debit_account_id = fields.Many2one('cd.account.account', required=True, ondelete='restrict')
    credit_account_id = fields.Many2one('cd.account.account', required=True, ondelete='restrict')
    contact_source_id = fields.Many2one('cd.contact.info', index=True)

    amount = UInteger(required=True)
    currency_id = fields.Many2one('res.currency', required=True)

    def action_post(self):
        for draft in self:
            transfer = self.env['cd.account.transfer'].create({
                'date': draft.date,
                'ledger_id': draft.ledger_id.id,
                'type': draft.type,
                'debit_account_id': draft.debit_account_id.id,
                'credit_account_id': draft.credit_account_id.id,
                'contact_source_id': draft.contact_source_id.id,
            })
            if draft.currency_id == draft.ledger_id.currency_id:
                self.env['cd.account.transfer.posted'].create({
                    'transfer_id': transfer.id,
                    'amount': draft.amount,
                })
            else:
                self.env['cd.account.transfer.pending'].create({
                    'transfer_id': transfer.id,
                    'amount': draft.amount,
                    'currency_id': draft.currency_id.id,
                })
            draft.unlink()
