from odoo import fields, models


class AccountTaxTag(models.Model):
    _name = 'cd.account.tax.tag'
    _description = 'Tax Tag'
    _order = 'name'

    name = fields.Char(required=True, translate=True)
    applicability = fields.Selection([
        ('taxes', 'Taxes'),
        ('accounts', 'Accounts'),
    ], required=True, default='taxes')
    tax_negate = fields.Boolean(string='Negate Tax Balance')
    color = fields.Integer()
    active = fields.Boolean(default=True)
