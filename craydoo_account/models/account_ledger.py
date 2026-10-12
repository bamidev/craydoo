from odoo import fields, models


class AccountLedger(models.Model):
    """ A named grouping of accounts - e.g. one company's books."""
    _name = 'cd.account.ledger'
    _description = 'Ledger'
    _order = 'name'

    name = fields.Char(required=True)
    currency_id = fields.Many2one(
        'res.currency', required=True, default=lambda self: self.env.company.currency_id)
    company_ids = fields.One2many('res.company', 'account_ledger_id')
