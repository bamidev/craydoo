from odoo import api, fields, models

from ..fields import UBigInteger


class AccountAccount(models.Model):
    """ An accounting account.

    Creatable and `active` is freely writable, but `ledger_id`/`code` can't
    be changed once set (both are `readonly`). Deleting one is only
    blocked once a transfer actually references it - see
    `debit_account_id`/`credit_account_id`'s `ondelete` on
    `cd.account.transfer`.
    """
    _name = 'cd.account.account'
    _description = 'Account'
    _rec_name = 'name'

    active = fields.Boolean(default=True)
    name = fields.Char(required=True, translate=True)

    code = fields.Char(required=True, readonly=True, size=8)
    ledger_id = fields.Many2one('cd.account.ledger', required=True, readonly=True)

    fiscal_year_balance_ids = fields.One2many('cd.account.fiscal.year.account.balance', 'account_id')
    debit_total = UBigInteger(compute='_compute_totals', store=True)
    credit_total = UBigInteger(compute='_compute_totals', store=True)
    debit_year_total = UBigInteger(compute='_compute_totals', store=True)
    credit_year_total = UBigInteger(compute='_compute_totals', store=True)

    @api.depends('fiscal_year_balance_ids.debit_total', 'fiscal_year_balance_ids.credit_total')
    def _compute_totals(self):
        year = fields.Date.today().year
        for account in self:
            account.debit_total = sum(account.fiscal_year_balance_ids.mapped('debit_total'))
            account.credit_total = sum(account.fiscal_year_balance_ids.mapped('credit_total'))
            current = account.fiscal_year_balance_ids.filtered(lambda r: r.fiscal_year_id.year == year)
            account.debit_year_total = current.debit_total  # defaults to 0
            account.credit_year_total = current.credit_total  # defaults to 0
