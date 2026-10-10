from odoo import api, fields, models

from ..fields import BigInteger, UBigInteger


class AccountFiscalYearAccountBalance(models.Model):
    _name = 'cd.account.fiscal.year.account.balance'
    _description = 'Fiscal Year Account Balance'
    _order = 'fiscal_year_id'

    fiscal_year_id = fields.Many2one(
        'cd.account.fiscal.year', required=True, readonly=True, ondelete='cascade')
    account_id = fields.Many2one('cd.account.account', required=True, readonly=True, ondelete='cascade')
    opening_debit = UBigInteger(required=True, readonly=True, default=0)
    opening_credit = UBigInteger(required=True, readonly=True, default=0)
    opening_balance = BigInteger(compute='_compute_opening_balance')
    debit_total = UBigInteger(required=True, readonly=True, default=0)
    credit_total = UBigInteger(required=True, readonly=True, default=0)
    closing_debit = BigInteger(compute='_compute_closing')
    closing_credit = BigInteger(compute='_compute_closing')
    closing_balance = BigInteger(compute='_compute_closing')

    _fiscal_year_account_unique = models.Constraint(
        'UNIQUE(fiscal_year_id, account_id)', 'Only one record per fiscal year per account.')

    @api.depends('opening_debit', 'opening_credit')
    def _compute_opening_balance(self):
        for rec in self:
            rec.opening_balance = rec.opening_credit - rec.opening_debit

    @api.depends('opening_debit', 'opening_credit', 'debit_total', 'credit_total')
    def _compute_closing(self):
        for rec in self:
            rec.closing_debit = rec.opening_debit + rec.debit_total
            rec.closing_credit = rec.opening_credit + rec.credit_total
            rec.closing_balance = rec.closing_credit - rec.closing_debit

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            fiscal_year = self.env['cd.account.fiscal.year'].browse(vals['fiscal_year_id'])
            prev = self.search([
                ('account_id', '=', vals['account_id']),
                ('fiscal_year_id.year', '=', fiscal_year.year - 1),
            ])
            vals['opening_debit'] = prev.closing_debit  # empty recordset -> 0
            vals['opening_credit'] = prev.closing_credit  # empty recordset -> 0
        return super().create(vals_list)
