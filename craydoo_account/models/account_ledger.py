from odoo import fields, models


class AccountLedger(models.Model):
    """ A named grouping of accounts - e.g. one company's books."""
    _name = 'cd.account.ledger'
    _description = 'Ledger'
    _order = 'name'

    name = fields.Char(required=True)
    company_ids = fields.One2many('res.company', 'account_ledger_id')
