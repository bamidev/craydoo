from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools import SQL

from ..fields import UInteger

TRANSFER_TYPES = [
    ('invoice', 'Invoice'),
]

TRANSFER_IMMUTABLE_COLUMNS = [
    'name', 'date', 'ledger_id', 'type', 'debit_account_id', 'credit_account_id',
    'billing_contact_id', 'backward_link_id',
]
TRANSFER_POSTED_IMMUTABLE_COLUMNS = ['transfer_id', 'amount']


def _immutable_sql(table, immutable_columns):
    """ A trigger that rejects DELETE, and rejects UPDATE of any column
    named in `immutable_columns` - shared by every transfer-related table
    that needs to be immutable once created, as a backstop against
    anything that goes around the ORM. Columns not listed (e.g.
    `cd.account.transfer`'s `reconciled_amount`/`residual_amount`, which
    legitimately keep changing as a transfer gets reconciled over time)
    stay freely writable.
    `table`/`immutable_columns` are always this module's own hardcoded
    names, never external input, so plain string formatting is fine here.
    """
    function = f'{table}_immutable'
    old_row = ', '.join(f'OLD.{column}' for column in immutable_columns)
    new_row = ', '.join(f'NEW.{column}' for column in immutable_columns)
    return SQL(f"""
        CREATE OR REPLACE FUNCTION {function}()
        RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            IF TG_OP = 'DELETE' THEN
                RAISE EXCEPTION 'Accounting history cannot be deleted';
            ELSIF ROW({new_row}) IS DISTINCT FROM ROW({old_row}) THEN
                RAISE EXCEPTION 'Accounting history cannot be changed';
            END IF;
            RETURN NEW;
        END;
        $$;
        DROP TRIGGER IF EXISTS {function} ON {table};
        CREATE TRIGGER {function}
            BEFORE UPDATE OR DELETE ON {table}
            FOR EACH ROW EXECUTE FUNCTION {function}();
    """)


def _convert_to_ledger_amount(amount, currency, ledger_currency, company):
    """ `amount` (minor units of `currency`) converted to `ledger_currency`
    at today's rate, in `ledger_currency`'s own minor units.
    """
    converted = currency._convert(
        amount / 10 ** currency.decimal_places, ledger_currency, company,
        fields.Date.context_today(currency))
    return round(converted * 10 ** ledger_currency.decimal_places)


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
    _rec_name = 'name'

    name = fields.Char(required=True, readonly=True, copy=False, unique=True)

    date = fields.Date(required=True, readonly=True, default=fields.Date.context_today)
    ledger_id = fields.Many2one('cd.account.ledger', required=True, readonly=True)
    type = fields.Selection(TRANSFER_TYPES, required=True, readonly=True)
    debit_account_id = fields.Many2one(
        'cd.account.account', required=True, readonly=True, ondelete='restrict')
    credit_account_id = fields.Many2one(
        'cd.account.account', required=True, readonly=True, ondelete='restrict')
    billing_contact_id = fields.Many2one('cd.contact.info', readonly=True, index=True)

    backward_link_id = fields.Many2one(
        'cd.account.transfer', readonly=True, ondelete='restrict')
    forward_link_ids = fields.One2many(
        'cd.account.transfer', 'backward_link_id', readonly=True)
    linked_ids = fields.Many2many('cd.account.transfer', compute='_compute_linked_ids')

    posted_id = fields.One2many('cd.account.transfer.posted', 'transfer_id')
    pending_id = fields.One2many('cd.account.transfer.pending', 'transfer_id')

    debit_reconcile_part_ids = fields.One2many('cd.account.reconcile.part', 'debit_transfer_id')
    credit_reconcile_part_ids = fields.One2many('cd.account.reconcile.part', 'credit_transfer_id')
    reconciled_amount = fields.Integer(compute='_compute_residual_amount', store=True)
    residual_amount = fields.Integer(compute='_compute_residual_amount', store=True)

    def _auto_init(self):
        result = super()._auto_init()
        self.env.cr.execute(_immutable_sql(self._table, TRANSFER_IMMUTABLE_COLUMNS))
        return result

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            vals['name'] = self.env['ir.sequence'].next_by_code('cd.account.transfer') or '/'
        return super().create(vals_list)

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

    @api.depends(
        'posted_id.amount', 'debit_reconcile_part_ids.amount', 'credit_reconcile_part_ids.amount')
    def _compute_residual_amount(self):
        for transfer in self:
            reconciled = (
                sum(transfer.debit_reconcile_part_ids.mapped('amount'))
                + sum(transfer.credit_reconcile_part_ids.mapped('amount')))
            transfer.reconciled_amount = reconciled
            transfer.residual_amount = sum(transfer.posted_id.mapped('amount')) - reconciled

    def unlink(self):
        raise UserError(_("Accounting history cannot be deleted."))

    def write(self, vals):
        raise UserError(_("Accounting history cannot be changed."))


class AccountTransferChildMixin(models.AbstractModel):
    """ Shared by `cd.account.transfer.posted`/`.pending`: related fields
    mirroring their parent `cd.account.transfer`'s important fields, so a
    view on either can show them without reaching through `transfer_id`.
    """
    _name = 'cd.account.transfer.child.mixin'
    _description = 'Transfer Detail'

    transfer_id = fields.Many2one(
        'cd.account.transfer', required=True, readonly=True, ondelete='cascade', index=True)

    name = fields.Char(related='transfer_id.name')
    date = fields.Date(related='transfer_id.date')
    ledger_id = fields.Many2one(related='transfer_id.ledger_id')
    type = fields.Selection(related='transfer_id.type')
    debit_account_id = fields.Many2one(related='transfer_id.debit_account_id')
    credit_account_id = fields.Many2one(related='transfer_id.credit_account_id')
    billing_contact_id = fields.Many2one(related='transfer_id.billing_contact_id')

    @api.depends('amount', 'currency_id')
    def _compute_amount_currency(self):
        for rec in self:
            rec.amount_currency = (
                rec.amount / 10 ** rec.currency_id.decimal_places if rec.currency_id else 0)


class AccountTransferPosted(models.Model):
    """ The final, immutable amount of a `cd.account.transfer`, in the
    ledger's own currency. Bumps the fiscal year balance at the moment it's
    created, since that's the moment the transfer's amount actually
    becomes part of the books.
    """
    _name = 'cd.account.transfer.posted'
    _inherit = ['cd.account.transfer.child.mixin']
    _description = 'Posted Transfer Amount'

    amount = UInteger(required=True, readonly=True)
    currency_id = fields.Many2one(related='ledger_id.currency_id')
    amount_currency = fields.Monetary(
        compute='_compute_amount_currency', currency_field='currency_id', store=True)

    def _auto_init(self):
        result = super()._auto_init()
        self.env.cr.execute(_immutable_sql(self._table, TRANSFER_POSTED_IMMUTABLE_COLUMNS))
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
    _inherit = ['cd.account.transfer.child.mixin']
    _description = 'Pending Transfer Amount'

    amount = UInteger(required=True)
    currency_id = fields.Many2one('res.currency', required=True)
    amount_currency = fields.Monetary(
        compute='_compute_amount_currency', currency_field='currency_id')
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
        return _convert_to_ledger_amount(
            self.amount, self.currency_id, self.transfer_id.ledger_id.currency_id, self.env.company)


class AccountTransferDraft(models.TransientModel):
    """ A manually-entered transfer, not yet backed by any
    `cd.account.transfer` - mutable, holding its own copies of the fields
    `cd.account.transfer` would otherwise hold, since that record doesn't
    exist until this draft is posted. Transient, since nothing about it
    needs to outlive the request that posts it (or Odoo's usual
    wizard-vacuuming if it never gets posted at all).

    Posting creates the real transfer, then either:
    - amount's currency already matches the ledger's: its
      `cd.account.transfer.posted` directly, same as always.
    - it doesn't, and `craydoo_account.transfer_convert_immediately` is
      disabled (the default): a `cd.account.transfer.pending`, settled
      later - see `cd.account.transfer.pending._action_post`.
    - it doesn't, but that setting is enabled: its
      `cd.account.transfer.posted` right away too, pre-converted at
      today's rate instead of waiting for reconciliation.
    Either way this draft then deletes itself - once posted there's
    nothing left for it to represent, so no `transfer_id` back-reference
    is kept.
    """
    _name = 'cd.account.transfer.draft'
    _description = 'Draft Transfer'

    date = fields.Date(required=True, default=fields.Date.context_today)
    ledger_id = fields.Many2one('cd.account.ledger', required=True)
    type = fields.Selection(TRANSFER_TYPES, required=True)
    debit_account_id = fields.Many2one('cd.account.account', required=True, ondelete='restrict')
    credit_account_id = fields.Many2one('cd.account.account', required=True, ondelete='restrict')
    billing_contact_id = fields.Many2one('cd.contact.info', index=True)
    backward_link_id = fields.Many2one('cd.account.transfer')

    amount = UInteger(required=True)
    currency_id = fields.Many2one('res.currency', required=True)

    def _ledger_amount(self):
        """ This draft's amount converted to its ledger's currency at
        today's rate.
        """
        self.ensure_one()
        return _convert_to_ledger_amount(
            self.amount, self.currency_id, self.ledger_id.currency_id, self.env.company)

    def action_post(self):
        """ Posts every draft in `self`, in order, and returns the
        `cd.account.transfer`s created for them (one per draft, same
        order) - the caller's hook into the real records once this
        transient draft has deleted itself.
        """
        convert_immediately = self.env['ir.config_parameter'].sudo().get_bool(
            'craydoo_account.transfer_convert_immediately')
        transfer_ids = []
        for draft in self:
            transfer = self.env['cd.account.transfer'].create({
                'date': draft.date,
                'ledger_id': draft.ledger_id.id,
                'type': draft.type,
                'debit_account_id': draft.debit_account_id.id,
                'credit_account_id': draft.credit_account_id.id,
                'billing_contact_id': draft.billing_contact_id.id,
                'backward_link_id': draft.backward_link_id.id,
            })
            same_currency = draft.currency_id == draft.ledger_id.currency_id
            if same_currency or convert_immediately:
                self.env['cd.account.transfer.posted'].create({
                    'transfer_id': transfer.id,
                    'amount': draft.amount if same_currency else draft._ledger_amount(),
                })
            else:
                self.env['cd.account.transfer.pending'].create({
                    'transfer_id': transfer.id,
                    'amount': draft.amount,
                    'currency_id': draft.currency_id.id,
                })
            transfer_ids.append(transfer.id)
            draft.unlink()
        return self.env['cd.account.transfer'].browse(transfer_ids)
