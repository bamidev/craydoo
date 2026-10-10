from odoo import api, fields, models

from ..fields import BigInteger, UBigInteger


class AccountFiscalYearAccount(models.Model):
    _name = 'cd.account.fiscal.year.account'
    _description = 'Fiscal Year Account'
    _order = 'fiscal_year_id'

    fiscal_year_id = fields.Many2one(
        'cd.account.fiscal.year', required=True, readonly=True, ondelete='cascade')
    account_id = fields.Many2one('cd.account.account', required=True, readonly=True, ondelete='cascade')
    opening_balance = BigInteger(required=True, readonly=True, default=0)
    debit_total = UBigInteger(required=True, readonly=True, default=0)
    credit_total = UBigInteger(required=True, readonly=True, default=0)
    closing_balance = BigInteger(compute='_compute_closing_balance')

    _fiscal_year_account_unique = models.Constraint(
        'UNIQUE(fiscal_year_id, account_id)', 'Only one record per fiscal year per account.')

    @api.depends('opening_balance', 'debit_total', 'credit_total')
    def _compute_closing_balance(self):
        for rec in self:
            rec.closing_balance = rec.opening_balance - rec.debit_total + rec.credit_total

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if 'opening_balance' not in vals:
                fiscal_year = self.env['cd.account.fiscal.year'].browse(vals['fiscal_year_id'])
                prev = self.search([
                    ('account_id', '=', vals['account_id']),
                    ('fiscal_year_id.year', '=', fiscal_year.year - 1),
                ])
                vals['opening_balance'] = prev.closing_balance if prev else 0
        return super().create(vals_list)
