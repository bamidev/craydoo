from odoo import fields, models


class AccountFiscalYear(models.Model):
    _name = 'cd.account.fiscal.year'
    _description = 'Fiscal Year'
    _order = 'year'

    year = fields.Integer(required=True, readonly=True)
    balance_ids = fields.One2many('cd.account.fiscal.year.account.balance', 'fiscal_year_id')

    _year_unique = models.Constraint('UNIQUE(year)', 'Only one record per fiscal year.')
